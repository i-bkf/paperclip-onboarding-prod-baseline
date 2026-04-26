from __future__ import annotations

from datetime import date
import tempfile
import unittest

from app.db import connect, migrate
from app.repository import Repository
from app.services import signup_user
from app.telemetry import (
    FUNNEL_EVENT_SEQUENCE,
    ONBOARDING_CHECKLIST_STEPS,
    TELEMETRY_EVENT_SIGNUP_COMPLETED,
)


class RepositoryPerformanceOptimizationTests(unittest.TestCase):
    def test_workspace_membership_bundle_preserves_workspace_not_found_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/app.sqlite3"
            migrate(db_path)
            conn = connect(db_path)
            try:
                signup = signup_user(
                    conn,
                    email="owner@example.com",
                    password="secure-pass-123",
                    workspace_name="Acme Workspace",
                    account_name=None,
                )
                repo = Repository(conn)

                self.assertIsNone(
                    repo.get_workspace_with_membership("workspace-does-not-exist", signup.user.id)
                )

                outsider = repo.create_user("outsider@example.com", "hash")
                bundled = repo.get_workspace_with_membership(signup.workspace.id, outsider.id)
                self.assertIsNotNone(bundled)
                workspace, membership = bundled  # type: ignore[misc]
                self.assertEqual(signup.workspace.id, workspace.id)
                self.assertIsNone(membership)
            finally:
                conn.close()

    def test_onboarding_cohort_progress_counts_fully_completed_users(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/app.sqlite3"
            migrate(db_path)
            conn = connect(db_path)
            try:
                signup = signup_user(
                    conn,
                    email="owner@example.com",
                    password="secure-pass-123",
                    workspace_name="Acme Workspace",
                    account_name=None,
                )
                repo = Repository(conn)

                user_full = repo.create_user("full@example.com", "hash")
                user_partial = repo.create_user("partial@example.com", "hash")
                repo.add_membership(signup.workspace.id, user_full.id, "member")
                repo.add_membership(signup.workspace.id, user_partial.id, "member")
                repo.upsert_beta_cohort_membership(
                    workspace_id=signup.workspace.id,
                    user_id=user_full.id,
                    cohort="wave-1",
                    source_invitation_id=None,
                )
                repo.upsert_beta_cohort_membership(
                    workspace_id=signup.workspace.id,
                    user_id=user_partial.id,
                    cohort="wave-1",
                    source_invitation_id=None,
                )

                for step_key in ONBOARDING_CHECKLIST_STEPS:
                    repo.record_onboarding_step_completion(
                        workspace_id=signup.workspace.id,
                        user_id=user_full.id,
                        cohort="wave-1",
                        step_key=step_key,
                    )

                repo.record_onboarding_step_completion(
                    workspace_id=signup.workspace.id,
                    user_id=user_partial.id,
                    cohort="wave-1",
                    step_key=ONBOARDING_CHECKLIST_STEPS[0],
                )
                conn.commit()

                cohorts = repo.list_onboarding_completion_by_cohort(
                    workspace_id=signup.workspace.id,
                    checklist_steps=ONBOARDING_CHECKLIST_STEPS,
                )
            finally:
                conn.close()

        self.assertEqual(1, len(cohorts))
        cohort = cohorts[0]
        self.assertEqual("wave-1", cohort["cohort"])
        self.assertEqual(2, cohort["membersCount"])
        self.assertEqual(1, cohort["fullyCompletedUsers"])

        step_counts = {step["stepKey"]: step["completedUsers"] for step in cohort["steps"]}
        self.assertEqual(2, step_counts["profile_completed"])
        self.assertEqual(1, step_counts["workspace_customized"])
        self.assertEqual(1, step_counts["first_feedback_shared"])

    def test_funnel_daily_counts_distinct_users_and_anonymous_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/app.sqlite3"
            migrate(db_path)
            conn = connect(db_path)
            try:
                signup = signup_user(
                    conn,
                    email="owner@example.com",
                    password="secure-pass-123",
                    workspace_name="Acme Workspace",
                    account_name=None,
                )
                repo = Repository(conn)

                second_user = repo.create_user("member@example.com", "hash")
                repo.add_membership(signup.workspace.id, second_user.id, "member")

                repo.record_product_event(
                    event_name=TELEMETRY_EVENT_SIGNUP_COMPLETED,
                    source="backend",
                    actor_user_id=second_user.id,
                    workspace_id=signup.workspace.id,
                    dedupe_key=f"{TELEMETRY_EVENT_SIGNUP_COMPLETED}:{second_user.id}",
                )
                repo.record_product_event(
                    event_name=TELEMETRY_EVENT_SIGNUP_COMPLETED,
                    source="frontend",
                    actor_user_id=None,
                    workspace_id=signup.workspace.id,
                )
                conn.commit()

                daily = repo.list_workspace_funnel_daily(
                    workspace_id=signup.workspace.id,
                    start_date=date.today(),
                    end_date=date.today(),
                    funnel_events=FUNNEL_EVENT_SEQUENCE,
                )
            finally:
                conn.close()

        steps = {step["eventName"]: step for step in daily[0]["steps"]}
        self.assertEqual(3, steps[TELEMETRY_EVENT_SIGNUP_COMPLETED]["count"])


if __name__ == "__main__":
    unittest.main()
