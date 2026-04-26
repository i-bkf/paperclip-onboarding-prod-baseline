#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta
import json
import math
from pathlib import Path
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
from urllib import request
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.auth import create_access_token
from app.config import Settings
from app.db import connect, migrate
from app.repository import Repository
from app.server import create_server
from app.services import signup_user
from app.telemetry import (
    FUNNEL_EVENT_SEQUENCE,
    ONBOARDING_CHECKLIST_STEPS,
    TELEMETRY_EVENT_ACTIVATION_COMPLETED,
    TELEMETRY_EVENT_SIGNUP_COMPLETED,
    TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED,
)


@dataclass(frozen=True)
class MetricSummary:
    average_ms: float
    p95_ms: float


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    rank = int(math.ceil((percentile / 100.0) * len(sorted_values))) - 1
    rank = max(0, min(rank, len(sorted_values) - 1))
    return sorted_values[rank]


def _benchmark(function: callable, *, iterations: int, warmup: int = 5) -> MetricSummary:
    for _ in range(warmup):
        function()

    values: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        function()
        values.append((time.perf_counter() - started) * 1000)

    return MetricSummary(average_ms=statistics.fmean(values), p95_ms=_percentile(values, 95.0))


def _legacy_auth_lookup(repo: Repository, workspace_id: str, user_id: str) -> tuple[object | None, object | None]:
    workspace = repo.get_workspace(workspace_id)
    if workspace is None:
        return None, None
    membership = repo.get_membership(workspace_id, user_id)
    return workspace, membership


def _legacy_onboarding_by_cohort(
    conn: sqlite3.Connection,
    *,
    workspace_id: str,
    checklist_steps: tuple[str, ...],
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT cohort,
               step_key,
               COUNT(DISTINCT user_id) AS completed_count
        FROM onboarding_checklist_progress
        WHERE workspace_id = ?
        GROUP BY cohort, step_key
        ORDER BY cohort ASC, step_key ASC
        """,
        (workspace_id,),
    ).fetchall()
    completions: dict[str, dict[str, int]] = {}
    for row in rows:
        cohort = str(row["cohort"])
        step_key = str(row["step_key"])
        count = int(row["completed_count"])
        completions.setdefault(cohort, {})[step_key] = count

    member_rows = conn.execute(
        """
        SELECT cohort, COUNT(DISTINCT user_id) AS members_count
        FROM beta_cohort_memberships
        WHERE workspace_id = ?
        GROUP BY cohort
        ORDER BY cohort ASC
        """,
        (workspace_id,),
    ).fetchall()
    members_by_cohort = {str(row["cohort"]): int(row["members_count"]) for row in member_rows}

    all_cohorts = sorted(set(completions.keys()) | set(members_by_cohort.keys()))
    required_steps = len(checklist_steps)
    result: list[dict[str, object]] = []
    for cohort in all_cohorts:
        step_counts = completions.get(cohort, {})
        user_step_counts: dict[str, int] = {}
        completed_rows = conn.execute(
            """
            SELECT user_id, COUNT(DISTINCT step_key) AS completed_steps
            FROM onboarding_checklist_progress
            WHERE workspace_id = ? AND cohort = ?
            GROUP BY user_id
            """,
            (workspace_id, cohort),
        ).fetchall()
        for completed_row in completed_rows:
            user_step_counts[str(completed_row["user_id"])] = int(completed_row["completed_steps"])

        fully_completed_count = sum(
            1 for completed_steps in user_step_counts.values() if completed_steps >= required_steps
        )

        steps = [
            {
                "stepKey": step_key,
                "completedUsers": step_counts.get(step_key, 0),
            }
            for step_key in checklist_steps
        ]

        result.append(
            {
                "cohort": cohort,
                "membersCount": members_by_cohort.get(cohort, 0),
                "fullyCompletedUsers": fully_completed_count,
                "steps": steps,
            }
        )
    return result


def _legacy_funnel_daily(
    conn: sqlite3.Connection,
    *,
    workspace_id: str,
    start_date: date,
    end_date: date,
    funnel_events: tuple[str, ...],
) -> list[dict[str, object]]:
    placeholders = ",".join("?" for _ in funnel_events)
    query_params: list[object] = [
        workspace_id,
        *funnel_events,
        start_date.isoformat(),
        end_date.isoformat(),
    ]

    rows = conn.execute(
        f"""
        SELECT date(emitted_at) AS event_date,
               event_name,
               (
                   COUNT(DISTINCT actor_user_id)
                   + SUM(CASE WHEN actor_user_id IS NULL THEN 1 ELSE 0 END)
               ) AS total
        FROM product_events
        WHERE workspace_id = ?
          AND event_name IN ({placeholders})
          AND date(emitted_at) BETWEEN ? AND ?
        GROUP BY event_date, event_name
        ORDER BY event_date ASC
        """,
        query_params,
    ).fetchall()

    totals: dict[str, dict[str, int]] = {}
    for row in rows:
        event_date = str(row["event_date"])
        event_name = str(row["event_name"])
        count = int(row["total"])
        totals.setdefault(event_date, {})[event_name] = count

    result: list[dict[str, object]] = []
    current_day = start_date
    signup_event = funnel_events[0]
    while current_day <= end_date:
        day_key = current_day.isoformat()
        day_totals = totals.get(day_key, {})
        signup_count = day_totals.get(signup_event, 0)
        steps: list[dict[str, object]] = []
        for event_name in funnel_events:
            count = day_totals.get(event_name, 0)
            conversion = round((count / signup_count) * 100, 2) if signup_count > 0 else 0.0
            steps.append(
                {
                    "eventName": event_name,
                    "count": count,
                    "conversionFromSignupPct": conversion,
                }
            )
        result.append({"date": day_key, "steps": steps})
        current_day = current_day + timedelta(days=1)

    return result


def _http_get_json(url: str, token: str) -> dict[str, object]:
    req = request.Request(url=url, method="GET", headers={"Authorization": f"Bearer {token}"})
    with request.urlopen(req, timeout=5) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def _measure_http_p95(base_url: str, token: str, path: str, *, iterations: int = 80) -> float:
    url = f"{base_url}{path}"

    for _ in range(8):
        _http_get_json(url, token)

    values: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        _http_get_json(url, token)
        values.append((time.perf_counter() - started) * 1000)

    return _percentile(values, 95.0)


def _seed_profile_dataset(
    conn: sqlite3.Connection,
    *,
    auth_secret: str,
) -> tuple[str, str, str]:
    signup = signup_user(
        conn,
        email="owner.profile@acme.test",
        password="owner-password-123",
        workspace_name="Acme Profile Workspace",
        account_name="Acme",
    )
    repo = Repository(conn)

    cohorts = ("wave-1", "wave-2", "wave-3", "wave-4", "wave-5", "wave-6")
    for index in range(900):
        user = repo.create_user(f"member-{index}@acme.test", f"hash-{index}")
        repo.add_membership(signup.workspace.id, user.id, "member")
        cohort = cohorts[index % len(cohorts)]
        repo.upsert_beta_cohort_membership(
            workspace_id=signup.workspace.id,
            user_id=user.id,
            cohort=cohort,
            source_invitation_id=None,
        )

        completed_steps = index % (len(ONBOARDING_CHECKLIST_STEPS) + 1)
        for step_key in ONBOARDING_CHECKLIST_STEPS[:completed_steps]:
            repo.record_onboarding_step_completion(
                workspace_id=signup.workspace.id,
                user_id=user.id,
                cohort=cohort,
                step_key=step_key,
            )

        repo.record_product_event(
            event_name=TELEMETRY_EVENT_SIGNUP_COMPLETED,
            source="backend",
            actor_user_id=user.id,
            workspace_id=signup.workspace.id,
            dedupe_key=f"signup:{user.id}",
        )
        if index % 2 == 0:
            repo.record_product_event(
                event_name=TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED,
                source="backend",
                actor_user_id=user.id,
                workspace_id=signup.workspace.id,
                dedupe_key=f"first_access:{user.id}",
            )
        if index % 3 == 0:
            repo.record_product_event(
                event_name=TELEMETRY_EVENT_ACTIVATION_COMPLETED,
                source="frontend",
                actor_user_id=user.id,
                workspace_id=signup.workspace.id,
                dedupe_key=f"activation:{user.id}",
            )

    for anon_index in range(180):
        repo.record_product_event(
            event_name=TELEMETRY_EVENT_SIGNUP_COMPLETED,
            source="frontend",
            actor_user_id=None,
            workspace_id=signup.workspace.id,
            dedupe_key=f"anon-signup:{anon_index}",
        )

    # Keep a larger historical tail so date() filters force full scans in the legacy path.
    for day_offset in range(30, 210):
        emitted_at = f"{(date.today() - timedelta(days=day_offset)).isoformat()}T12:00:00.000Z"
        for event_index in range(45):
            event_name = FUNNEL_EVENT_SEQUENCE[(event_index + day_offset) % len(FUNNEL_EVENT_SEQUENCE)]
            actor_user_id = signup.user.id if event_index % 5 else None
            conn.execute(
                """
                INSERT INTO product_events (
                    id,
                    event_name,
                    source,
                    actor_user_id,
                    workspace_id,
                    properties_json,
                    dedupe_key,
                    emitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    event_name,
                    "backend",
                    actor_user_id,
                    signup.workspace.id,
                    "{}",
                    None,
                    emitted_at,
                ),
            )
    conn.commit()

    owner_token = create_access_token(
        {
            "sub": signup.user.id,
            "email": signup.user.email,
        },
        secret=auth_secret,
        ttl_seconds=3600,
    )
    target_user_id = f"member-{876}@acme.test"
    target_user = repo.find_user_by_email(target_user_id)
    if target_user is None:
        raise RuntimeError("seeded target user missing")

    return signup.workspace.id, signup.user.id, owner_token


def _write_report(
    *,
    output_path: Path,
    hotspot_rows: list[tuple[str, MetricSummary, MetricSummary]],
    endpoint_rows: list[tuple[str, float, float]],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with output_path.open("w", encoding="utf-8") as report:
        report.write("# M3-S2 Performance and Cost Optimization Report\n\n")
        report.write(f"- Generated at (UTC): {generated_at_utc}\n")
        report.write(
            "- Profile dataset: 1 workspace, 900 members, 6 cohorts, 10,000+ funnel events with 180-day history tail\n"
        )
        report.write("- Measurement method: local synthetic benchmark with p95 latency focus\n\n")

        report.write("## p95 Latency Targets and Measurements\n\n")
        report.write("| Endpoint | p95 target (ms) | Measured p95 (ms) | Status |\n")
        report.write("| --- | --- | --- | --- |\n")
        for endpoint, target_p95, measured_p95 in endpoint_rows:
            status = "pass" if measured_p95 <= target_p95 else "fail"
            report.write(
                f"| `{endpoint}` | {target_p95:.2f} | {measured_p95:.2f} | **{status}** |\n"
            )

        report.write("\n## Top 3 Hotspots: Before vs After\n\n")
        report.write("| Hotspot | Before p95 (ms) | After p95 (ms) | p95 improvement |\n")
        report.write("| --- | --- | --- | --- |\n")
        for hotspot_name, before_metric, after_metric in hotspot_rows:
            if before_metric.p95_ms <= 0:
                improvement_pct = 0.0
            else:
                improvement_pct = ((before_metric.p95_ms - after_metric.p95_ms) / before_metric.p95_ms) * 100
            report.write(
                f"| {hotspot_name} | {before_metric.p95_ms:.2f} | {after_metric.p95_ms:.2f} | {improvement_pct:.2f}% |\n"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate M3-S2 performance profile report")
    parser.add_argument(
        "--output",
        default="logs/performance/m3-s2-performance-profile.md",
        help="Path to markdown report output",
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = str(Path(temp_dir) / "profile.sqlite3")
        auth_secret = "profile-secret"
        settings = Settings(db_path=db_path, auth_secret=auth_secret, token_ttl_seconds=3600)

        migrate(db_path)
        conn = connect(db_path)
        try:
            workspace_id, _, owner_token = _seed_profile_dataset(conn, auth_secret=auth_secret)
            repo = Repository(conn)

            target_user = repo.find_user_by_email("member-876@acme.test")
            if target_user is None:
                raise RuntimeError("target profile user missing")

            range_to = date.today()
            range_from = range_to - timedelta(days=6)

            hotspot_rows = [
                (
                    "Workspace authorization lookup (2 queries -> 1 query)",
                    _benchmark(
                        lambda: _legacy_auth_lookup(repo, workspace_id, target_user.id),
                        iterations=500,
                        warmup=12,
                    ),
                    _benchmark(
                        lambda: repo.get_workspace_with_membership(workspace_id, target_user.id),
                        iterations=500,
                        warmup=12,
                    ),
                ),
                (
                    "Onboarding cohort aggregation (N+1 -> grouped query)",
                    _benchmark(
                        lambda: _legacy_onboarding_by_cohort(
                            conn,
                            workspace_id=workspace_id,
                            checklist_steps=ONBOARDING_CHECKLIST_STEPS,
                        ),
                        iterations=120,
                        warmup=10,
                    ),
                    _benchmark(
                        lambda: repo.list_onboarding_completion_by_cohort(
                            workspace_id=workspace_id,
                            checklist_steps=ONBOARDING_CHECKLIST_STEPS,
                        ),
                        iterations=120,
                        warmup=10,
                    ),
                ),
                (
                    "Funnel analytics date filter/distinct counting rewrite",
                    _benchmark(
                        lambda: _legacy_funnel_daily(
                            conn,
                            workspace_id=workspace_id,
                            start_date=range_from,
                            end_date=range_to,
                            funnel_events=FUNNEL_EVENT_SEQUENCE,
                        ),
                        iterations=180,
                        warmup=12,
                    ),
                    _benchmark(
                        lambda: repo.list_workspace_funnel_daily(
                            workspace_id=workspace_id,
                            start_date=range_from,
                            end_date=range_to,
                            funnel_events=FUNNEL_EVENT_SEQUENCE,
                        ),
                        iterations=180,
                        warmup=12,
                    ),
                ),
            ]
        finally:
            conn.close()

        server = create_server(settings=settings, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            endpoint_rows = [
                (
                    "/api/v1/workspaces/{id}",
                    120.0,
                    _measure_http_p95(base_url, owner_token, f"/api/v1/workspaces/{workspace_id}"),
                ),
                (
                    "/api/v1/workspaces/{id}/onboarding/checklist/cohorts",
                    250.0,
                    _measure_http_p95(
                        base_url,
                        owner_token,
                        f"/api/v1/workspaces/{workspace_id}/onboarding/checklist/cohorts",
                    ),
                ),
                (
                    "/api/v1/workspaces/{id}/telemetry/funnel/daily",
                    300.0,
                    _measure_http_p95(
                        base_url,
                        owner_token,
                        (
                            f"/api/v1/workspaces/{workspace_id}/telemetry/funnel/daily"
                            f"?from={(date.today() - timedelta(days=6)).isoformat()}"
                            f"&to={date.today().isoformat()}"
                        ),
                    ),
                ),
            ]
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    _write_report(output_path=output_path, hotspot_rows=hotspot_rows, endpoint_rows=endpoint_rows)
    print(f"performance profile report generated: {output_path}")


if __name__ == "__main__":
    main()
