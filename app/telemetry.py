from __future__ import annotations

TELEMETRY_EVENT_SIGNUP_COMPLETED = "onboarding.signup_completed"
TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED = "onboarding.workspace_first_accessed"
TELEMETRY_EVENT_ACTIVATION_COMPLETED = "onboarding.activation_completed"

FUNNEL_EVENT_SEQUENCE = (
    TELEMETRY_EVENT_SIGNUP_COMPLETED,
    TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED,
    TELEMETRY_EVENT_ACTIVATION_COMPLETED,
)

CLIENT_EVENT_NAMES = frozenset(
    {
        TELEMETRY_EVENT_ACTIVATION_COMPLETED,
    }
)

ONBOARDING_CHECKLIST_STEPS = (
    "profile_completed",
    "workspace_customized",
    "first_feedback_shared",
)

FEEDBACK_CATEGORIES = frozenset(
    {
        "bug",
        "ux",
        "feature_request",
        "general",
    }
)
