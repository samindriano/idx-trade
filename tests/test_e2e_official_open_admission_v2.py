from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from idx_trade.e2e_official_open_admission_v2 import (
    NATIVE_SCHEDULE_AUTHORITY,
    PRODUCTION_REPOSITORY,
    SCHEDULER_ATTESTATION_SCHEMA,
    TRUSTED_EXTERNAL_AUTHORITY,
    _verify_trigger_provenance,
)
from idx_trade.e2e_paper_cloud_runtime_v1 import CloudPaperRuntimeError


JAKARTA = ZoneInfo("Asia/Jakarta")
SESSION = "2026-09-02"
SLOT = "0902"
SCHEDULED = datetime(2026, 9, 2, 9, 2, tzinfo=JAKARTA)
CAPTURED = datetime(2026, 9, 2, 9, 4, tzinfo=JAKARTA)


def _base_runner(**overrides):
    runner = {
        "runner": "GITHUB_ACTIONS",
        "github_repository": PRODUCTION_REPOSITORY,
        "logical_slot": SLOT,
        "session_date": SESSION,
        "github_event_name": "schedule",
        "trigger_authority": NATIVE_SCHEDULE_AUTHORITY,
    }
    runner.update(overrides)
    return runner


def _trusted_runner(**overrides):
    runner = _base_runner(
        github_event_name="workflow_dispatch",
        trigger_authority=TRUSTED_EXTERNAL_AUTHORITY,
        scheduler_attestation_schema=SCHEDULER_ATTESTATION_SCHEMA,
        scheduler_issued_at_utc=datetime(2026, 9, 2, 2, 3, tzinfo=timezone.utc).isoformat(),
        scheduler_nonce_sha256="a" * 64,
        scheduler_attestation_sha256="b" * 64,
    )
    runner.update(overrides)
    return runner


def _verify(runner):
    return _verify_trigger_provenance(
        runner,
        session=SESSION,
        slot=SLOT,
        scheduled=SCHEDULED,
        captured=CAPTURED,
    )


def test_native_schedule_is_explicitly_admitted():
    result = _verify(_base_runner())
    assert result == {
        "producer_github_event_name": "schedule",
        "producer_trigger_authority": NATIVE_SCHEDULE_AUTHORITY,
    }


def test_native_schedule_cannot_claim_external_authority():
    with pytest.raises(CloudPaperRuntimeError, match="NATIVE_AUTHORITY_INVALID"):
        _verify(_base_runner(trigger_authority=TRUSTED_EXTERNAL_AUTHORITY))


def test_plain_manual_workflow_dispatch_is_forbidden():
    with pytest.raises(CloudPaperRuntimeError, match="MANUAL_CAPTURE_FORBIDDEN"):
        _verify(
            _base_runner(
                github_event_name="workflow_dispatch",
                trigger_authority="MANUAL_WORKFLOW_DISPATCH",
            )
        )


def test_trusted_external_dispatch_requires_exact_attestation_identity():
    result = _verify(_trusted_runner())
    assert result["producer_github_event_name"] == "workflow_dispatch"
    assert result["producer_trigger_authority"] == TRUSTED_EXTERNAL_AUTHORITY
    assert result["scheduler_nonce_sha256"] == "a" * 64
    assert result["scheduler_attestation_sha256"] == "b" * 64


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("github_repository", "someone/else", "TRIGGER_IDENTITY_INVALID"),
        ("logical_slot", "0912", "TRIGGER_IDENTITY_INVALID"),
        ("session_date", "2026-09-01", "TRIGGER_IDENTITY_INVALID"),
        ("scheduler_attestation_schema", "other", "SCHEDULER_SCHEMA_INVALID"),
        ("scheduler_nonce_sha256", "not-a-sha", "SCHEDULER_NONCE_SHA_INVALID"),
        ("scheduler_attestation_sha256", "not-a-sha", "SCHEDULER_ATTESTATION_SHA_INVALID"),
    ],
)
def test_tampered_external_dispatch_fails_closed(field, value, error):
    with pytest.raises(CloudPaperRuntimeError, match=error):
        _verify(_trusted_runner(**{field: value}))


def test_external_attestation_cannot_predate_logical_slot():
    issued = datetime(2026, 9, 2, 2, 1, 59, tzinfo=timezone.utc).isoformat()
    with pytest.raises(CloudPaperRuntimeError, match="SCHEDULER_TIME_INVALID"):
        _verify(_trusted_runner(scheduler_issued_at_utc=issued))


def test_external_attestation_cannot_be_created_after_capture():
    issued = datetime(2026, 9, 2, 2, 4, 1, tzinfo=timezone.utc).isoformat()
    with pytest.raises(CloudPaperRuntimeError, match="SCHEDULER_TIME_INVALID"):
        _verify(_trusted_runner(scheduler_issued_at_utc=issued))
