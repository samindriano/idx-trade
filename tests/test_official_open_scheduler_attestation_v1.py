from __future__ import annotations

from datetime import datetime, timezone

import pytest

from idx_trade.official_open_scheduler_attestation_v1 import (
    NATIVE_SCHEDULE_AUTHORITY,
    TRUSTED_EXTERNAL_AUTHORITY,
    OfficialOpenSchedulerAttestationError,
    sign_external_scheduler_attestation,
    trusted_runner_provenance,
    verify_external_scheduler_attestation,
)


SESSION = "2026-09-02"
SLOT = "0902"
ISSUED = "2026-09-02T02:05:00+00:00"
NONCE = "abcdef0123456789abcdef0123456789"
SECRET = "test-only-secret"


def _github_env(event: str) -> dict[str, str]:
    return {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "samindriano/idx-trade",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_WORKFLOW": "Official Open prospective cloud archive",
        "GITHUB_EVENT_NAME": event,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "OFFICIAL_OPEN_CAPTURE_CODE_REF": "b" * 40,
    }


def _trusted_dispatch_env() -> dict[str, str]:
    signature = sign_external_scheduler_attestation(
        secret=SECRET,
        session_date=SESSION,
        slot=SLOT,
        issued_at=ISSUED,
        nonce=NONCE,
    )
    return {
        **_github_env("workflow_dispatch"),
        "OFFICIAL_OPEN_SCHEDULER_HMAC_KEY": SECRET,
        "OFFICIAL_OPEN_SCHEDULER_ISSUED_AT": ISSUED,
        "OFFICIAL_OPEN_SCHEDULER_NONCE": NONCE,
        "OFFICIAL_OPEN_SCHEDULER_SIGNATURE": signature,
    }


def test_native_schedule_is_trusted_without_external_secret():
    provenance = trusted_runner_provenance(
        env=_github_env("schedule"), session_date=SESSION, slot=SLOT
    )
    assert provenance["trigger_authority"] == NATIVE_SCHEDULE_AUTHORITY
    assert provenance["github_event_name"] == "schedule"
    assert provenance["logical_slot"] == SLOT
    assert provenance["session_date"] == SESSION
    assert "scheduler_attestation_sha256" not in provenance


def test_signed_workflow_dispatch_is_trusted_and_signature_not_persisted():
    env = _trusted_dispatch_env()
    provenance = trusted_runner_provenance(
        env=env, session_date=SESSION, slot=SLOT
    )
    assert provenance["trigger_authority"] == TRUSTED_EXTERNAL_AUTHORITY
    assert provenance["github_event_name"] == "workflow_dispatch"
    assert provenance["scheduler_issued_at_utc"] == datetime.fromisoformat(
        ISSUED
    ).astimezone(timezone.utc).isoformat()
    assert len(provenance["scheduler_nonce_sha256"]) == 64
    assert len(provenance["scheduler_attestation_sha256"]) == 64
    assert env["OFFICIAL_OPEN_SCHEDULER_SIGNATURE"] not in str(provenance)
    assert SECRET not in str(provenance)
    assert NONCE not in str(provenance)


def test_arbitrary_manual_workflow_dispatch_is_rejected_before_capture():
    with pytest.raises(
        OfficialOpenSchedulerAttestationError,
        match="SCHEDULER_SIGNATURE_INVALID|SCHEDULER_HMAC_KEY_MISSING",
    ):
        trusted_runner_provenance(
            env=_github_env("workflow_dispatch"), session_date=SESSION, slot=SLOT
        )


@pytest.mark.parametrize(
    ("changed", "value"),
    [
        ("session_date", "2026-09-03"),
        ("slot", "0912"),
        ("issued_at", "2026-09-02T02:06:00+00:00"),
        ("nonce", "fedcba9876543210fedcba9876543210"),
    ],
)
def test_signature_is_bound_to_exact_attestation_fields(changed, value):
    signature = sign_external_scheduler_attestation(
        secret=SECRET,
        session_date=SESSION,
        slot=SLOT,
        issued_at=ISSUED,
        nonce=NONCE,
    )
    kwargs = {
        "secret": SECRET,
        "session_date": SESSION,
        "slot": SLOT,
        "issued_at": ISSUED,
        "nonce": NONCE,
        "signature": signature,
    }
    kwargs[changed] = value
    with pytest.raises(
        OfficialOpenSchedulerAttestationError,
        match="SCHEDULER_SIGNATURE_MISMATCH",
    ):
        verify_external_scheduler_attestation(**kwargs)


def test_non_production_runner_and_unrelated_event_are_rejected():
    local = _github_env("schedule")
    local["GITHUB_ACTIONS"] = "false"
    with pytest.raises(
        OfficialOpenSchedulerAttestationError,
        match="TRIGGER_RUNNER_NOT_PRODUCTION_GITHUB",
    ):
        trusted_runner_provenance(env=local, session_date=SESSION, slot=SLOT)

    event = _github_env("push")
    with pytest.raises(
        OfficialOpenSchedulerAttestationError,
        match="TRIGGER_EVENT_NOT_ADMITTED",
    ):
        trusted_runner_provenance(env=event, session_date=SESSION, slot=SLOT)
