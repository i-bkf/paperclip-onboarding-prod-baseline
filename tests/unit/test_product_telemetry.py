from __future__ import annotations

from datetime import date
import tempfile
import unittest

from app.db import connect, migrate
from app.repository import Repository
from app.services import signup_user
from app.telemetry import (
    FUNNEL_EVENT_SEQUENCE,
    TELEMETRY_EVENT_ACTIVATION_COMPLETED,
    TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED,
)


class ProductTelemetryUnitTests(unittest.TestCase):
    def test_signup_and_activation_funnel_counts(self) -> None:
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

                first_access_key = (
                    f"{TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED}:"
                    f"{signup.workspace.id}:{signup.user.id}"
                )
                inserted_first = repo.record_product_event(
                    event_name=TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED,
                    source="backend",
                    actor_user_id=signup.user.id,
                    workspace_id=signup.workspace.id,
                    dedupe_key=first_access_key,
                    ignore_duplicates=True,
                )
                inserted_second = repo.record_product_event(
                    event_name=TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED,
                    source="backend",
                    actor_user_id=signup.user.id,
                    workspace_id=signup.workspace.id,
                    dedupe_key=first_access_key,
                    ignore_duplicates=True,
                )
                repo.record_product_event(
                    event_name=TELEMETRY_EVENT_ACTIVATION_COMPLETED,
                    source="frontend",
                    actor_user_id=signup.user.id,
                    workspace_id=signup.workspace.id,
                    properties={"trigger": "unit-test"},
                )
                conn.commit()

                today = date.today()
                daily = repo.list_workspace_funnel_daily(
                    workspace_id=signup.workspace.id,
                    start_date=today,
                    end_date=today,
                    funnel_events=FUNNEL_EVENT_SEQUENCE,
                )
            finally:
                conn.close()

        self.assertTrue(inserted_first)
        self.assertFalse(inserted_second)
        self.assertEqual(1, len(daily))

        steps = {step["eventName"]: step for step in daily[0]["steps"]}
        self.assertEqual(1, steps["onboarding.signup_completed"]["count"])
        self.assertEqual(1, steps["onboarding.workspace_first_accessed"]["count"])
        self.assertEqual(1, steps["onboarding.activation_completed"]["count"])
        self.assertEqual(100.0, steps["onboarding.activation_completed"]["conversionFromSignupPct"])


if __name__ == "__main__":
    unittest.main()
