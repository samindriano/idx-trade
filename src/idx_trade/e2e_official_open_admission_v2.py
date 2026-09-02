"""Official Open consumer admission with explicit trusted trigger authority.

This is a successor to the V1 cloud materializer.  Source/timing/hash/archive
semantics are unchanged.  The only trigger change is that execution admission
recognises either:

* a native GitHub schedule produced by the accepted producer; or
* a workflow_dispatch whose accepted producer already verified the
  ``idx_official_open_external_scheduler_attestation_v1`` HMAC contract.

Arbitrary/manual workflow_dispatch remains forbidden.  The consumer does not
recreate or weaken producer authentication: it requires the exact producer code
pin, validates the persisted attestation identity/hashes, and still requires the
actual source capture timestamp to be inside the prospective execution window.
"""

from __future__ import annotations

from datetime import date, datetime
import math
from pathlib import Path
from typing import Any

from . import e2e_paper_cloud_runtime_v1 as v1


NATIVE_SCHEDULE_AUTHORITY = "NATIVE_GITHUB_SCHEDULE"
TRUSTED_EXTERNAL_AUTHORITY = "TRUSTED_EXTERNAL_SCHEDULER_V1"
SCHEDULER_ATTESTATION_SCHEMA = "idx_official_open_external_scheduler_attestation_v1"
PRODUCTION_REPOSITORY = "samindriano/idx-trade"


def _verify_trigger_provenance(
    runner: object,
    *,
    session: str,
    slot: str,
    scheduled: datetime,
    captured: datetime,
) -> dict[str, object]:
    if not isinstance(runner, dict):
        raise v1.CloudPaperRuntimeError(
            "OFFICIAL_OPEN_CLOUD_ADMISSION_TRIGGER_PROVENANCE_INVALID"
        )
    if (
        runner.get("runner") != "GITHUB_ACTIONS"
        or runner.get("github_repository") != PRODUCTION_REPOSITORY
        or runner.get("logical_slot") != slot
        or runner.get("session_date") != session
    ):
        raise v1.CloudPaperRuntimeError(
            "OFFICIAL_OPEN_CLOUD_ADMISSION_TRIGGER_IDENTITY_INVALID"
        )

    event = str(runner.get("github_event_name") or "")
    authority = str(runner.get("trigger_authority") or "")
    if event == "schedule":
        if authority != NATIVE_SCHEDULE_AUTHORITY:
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_NATIVE_AUTHORITY_INVALID"
            )
        return {
            "producer_github_event_name": event,
            "producer_trigger_authority": authority,
        }

    if event != "workflow_dispatch" or authority != TRUSTED_EXTERNAL_AUTHORITY:
        raise v1.CloudPaperRuntimeError(
            "OFFICIAL_OPEN_CLOUD_ADMISSION_MANUAL_CAPTURE_FORBIDDEN"
        )
    if runner.get("scheduler_attestation_schema") != SCHEDULER_ATTESTATION_SCHEMA:
        raise v1.CloudPaperRuntimeError(
            "OFFICIAL_OPEN_CLOUD_ADMISSION_SCHEDULER_SCHEMA_INVALID"
        )
    issued = v1._aware_timestamp(
        runner.get("scheduler_issued_at_utc"),
        label="OFFICIAL_OPEN_CLOUD_SCHEDULER_ISSUED_AT",
    ).astimezone(scheduled.tzinfo)
    if issued.date().isoformat() != session or issued < scheduled or issued > captured:
        raise v1.CloudPaperRuntimeError(
            "OFFICIAL_OPEN_CLOUD_ADMISSION_SCHEDULER_TIME_INVALID"
        )
    nonce_sha = v1._required_sha(
        runner.get("scheduler_nonce_sha256"),
        label="OFFICIAL_OPEN_CLOUD_SCHEDULER_NONCE",
    )
    attestation_sha = v1._required_sha(
        runner.get("scheduler_attestation_sha256"),
        label="OFFICIAL_OPEN_CLOUD_SCHEDULER_ATTESTATION",
    )
    return {
        "producer_github_event_name": event,
        "producer_trigger_authority": authority,
        "scheduler_issued_at_utc": issued.isoformat(),
        "scheduler_nonce_sha256": nonce_sha,
        "scheduler_attestation_sha256": attestation_sha,
    }


def materialize_official_open_from_cloud_v2(
    store: v1.CloudObjectStore,
    *,
    session_date: str,
    target_root: str | Path,
    eligibility_now: datetime,
    expected_capture_code_ref: str,
) -> dict[str, Any] | None:
    """Admit one exact prospective Open observation from trusted producer evidence."""

    from .official_open_cloud_archive_v1 import (
        AUTHORITY as OPEN_AUTHORITY,
        EXECUTION_ADMISSION as OPEN_EXECUTION_ADMISSION,
        FIELD_SEMANTICS as OPEN_FIELD_SEMANTICS,
        SCHEMA_VERSION as OPEN_SCHEMA_VERSION,
        SLOT_TIMES as OPEN_SLOT_TIMES,
        TRANSPORT_POLICY as OPEN_TRANSPORT_POLICY,
        UPSTREAM_PATH as OPEN_UPSTREAM_PATH,
    )
    from .official_open_evidence_v1 import JAKARTA as OPEN_JAKARTA

    expected_producer_ref = v1._required_git_sha(
        expected_capture_code_ref,
        label="OFFICIAL_OPEN_CLOUD_EXPECTED_CAPTURE_CODE_REF",
    )
    session = date.fromisoformat(session_date).isoformat()
    current = v1._aware_timestamp(
        eligibility_now, label="OFFICIAL_OPEN_ELIGIBILITY_NOW"
    ).astimezone(OPEN_JAKARTA)
    if current.date().isoformat() != session:
        raise v1.CloudPaperRuntimeError("OFFICIAL_OPEN_CLOUD_ELIGIBILITY_DATE_MISMATCH")
    hard_deadline = datetime.combine(
        date.fromisoformat(session), v1.OFFICIAL_OPEN_EXECUTION_END, tzinfo=OPEN_JAKARTA
    )
    if current > hard_deadline:
        raise v1.CloudPaperRuntimeError("OFFICIAL_OPEN_CLOUD_EXECUTION_WINDOW_CLOSED")

    admitted: list[tuple[bytes, dict[str, bytes], dict[str, Any]]] = []
    for slot in ("0902", "0912", "0922"):
        commit_key = f"session_date={session}/slot={slot}/slot_manifest.json"
        raw_commit = store.read(commit_key)
        if raw_commit is None:
            continue
        commit = v1._json_object(raw_commit, label="OFFICIAL_OPEN_CLOUD_COMMIT")
        expected_outer = {
            "schema_version": OPEN_SCHEMA_VERSION,
            "commit_state": "COMMITTED",
            "session_date": session,
            "slot": slot,
            "execution_admission": OPEN_EXECUTION_ADMISSION,
            "authority": OPEN_AUTHORITY,
            "upstream_path": OPEN_UPSTREAM_PATH,
            "field_semantics": OPEN_FIELD_SEMANTICS,
            "source_execution_grade": True,
        }
        for field, expected in expected_outer.items():
            if commit.get(field) != expected:
                raise v1.CloudPaperRuntimeError(
                    f"OFFICIAL_OPEN_CLOUD_ADMISSION_INVALID:{field}"
                )
        capture_id = commit.get("capture_id")
        if not isinstance(capture_id, str) or not capture_id.strip():
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_CAPTURE_ID_INVALID"
            )
        scheduled = v1._aware_timestamp(
            commit.get("scheduled_capture_timestamp_jakarta"),
            label="OFFICIAL_OPEN_CLOUD_SCHEDULED_CAPTURE",
        ).astimezone(OPEN_JAKARTA)
        expected_scheduled = datetime.combine(
            date.fromisoformat(session), OPEN_SLOT_TIMES[slot], tzinfo=OPEN_JAKARTA
        )
        if scheduled != expected_scheduled:
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_SCHEDULE_MISMATCH"
            )
        captured = v1._aware_timestamp(
            commit.get("source_capture_timestamp_jakarta"),
            label="OFFICIAL_OPEN_CLOUD_SOURCE_CAPTURE",
        ).astimezone(OPEN_JAKARTA)
        if captured.date().isoformat() != session:
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_SOURCE_SESSION_MISMATCH"
            )
        if captured < scheduled or captured > hard_deadline:
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_OUTSIDE_PROSPECTIVE_WINDOW"
            )
        if captured > current:
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_FUTURE_CAPTURE"
            )
        try:
            declared_lag = float(commit.get("capture_lag_seconds"))
        except (TypeError, ValueError) as exc:
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_CAPTURE_LAG_INVALID"
            ) from exc
        actual_lag = (captured - scheduled).total_seconds()
        if (
            not math.isfinite(declared_lag)
            or declared_lag < 0
            or abs(declared_lag - actual_lag) > 1e-6
        ):
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_CAPTURE_LAG_MISMATCH"
            )
        if commit.get("source_transport_policy") != OPEN_TRANSPORT_POLICY:
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_TRANSPORT_POLICY_INVALID"
            )

        runner = commit.get("runner_provenance")
        trigger = _verify_trigger_provenance(
            runner,
            session=session,
            slot=slot,
            scheduled=scheduled,
            captured=captured,
        )
        assert isinstance(runner, dict)
        capture_code_ref = v1._required_git_sha(
            runner.get("capture_code_ref"),
            label="OFFICIAL_OPEN_CLOUD_CAPTURE_CODE_REF",
        )
        if capture_code_ref != expected_producer_ref:
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_CAPTURE_CODE_REF_MISMATCH"
            )

        guards = commit.get("guards")
        required_false = (
            "model_accessed",
            "outcome_accessed",
            "paper_state_mutated",
            "forward_counter_mutated",
            "order_created",
            "fill_created",
            "retroactive_execution_authorized",
        )
        if not isinstance(guards, dict) or any(
            guards.get(key) is not False for key in required_false
        ):
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_GUARDS_INVALID"
            )
        artifacts = commit.get("artifacts")
        if not isinstance(artifacts, dict):
            raise v1.CloudPaperRuntimeError("OFFICIAL_OPEN_CLOUD_ARTIFACT_REFS_MISSING")
        loaded: dict[str, bytes] = {}
        loaded_keys: list[str] = []
        for name in ("raw_response", "open_prices", "source_manifest"):
            ref = artifacts.get(name)
            if not isinstance(ref, dict):
                raise v1.CloudPaperRuntimeError(
                    "OFFICIAL_OPEN_CLOUD_ARTIFACT_REF_INVALID:" + name
                )
            key = v1._safe_key(str(ref.get("key") or ""))
            prefix = f"session_date={session}/slot={slot}/captures/"
            if not key.startswith(prefix):
                raise v1.CloudPaperRuntimeError(
                    "OFFICIAL_OPEN_CLOUD_ARTIFACT_SESSION_OR_SLOT_MISMATCH:" + name
                )
            expected = v1._required_sha(
                ref.get("sha256"), label="OFFICIAL_OPEN_CLOUD_ARTIFACT"
            )
            payload = store.read(key)
            if payload is None or v1.sha256_bytes(payload) != expected:
                raise v1.CloudPaperRuntimeError(
                    "OFFICIAL_OPEN_CLOUD_ARTIFACT_SHA_MISMATCH:" + name
                )
            loaded[name] = payload
            loaded_keys.append(key)
        capture_roots = {key.rsplit("/", 1)[0] for key in loaded_keys}
        if len(capture_roots) != 1:
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ARTIFACT_CAPTURE_ID_MISMATCH"
            )
        source = v1._json_object(
            loaded["source_manifest"], label="OFFICIAL_OPEN_SOURCE_MANIFEST"
        )
        if (
            source.get("session_date") != session
            or source.get("execution_grade") is not True
            or source.get("authority") != OPEN_AUTHORITY
            or source.get("upstream_path") != OPEN_UPSTREAM_PATH
            or source.get("field_semantics") != OPEN_FIELD_SEMANTICS
            or source.get("transport_policy") != OPEN_TRANSPORT_POLICY
            or commit.get("source_transport") != source.get("transport")
            or commit.get("source_transport_policy") != source.get("transport_policy")
        ):
            raise v1.CloudPaperRuntimeError("OFFICIAL_OPEN_SOURCE_MANIFEST_INVALID")
        source_captured = v1._aware_timestamp(
            source.get("capture_timestamp_jakarta"),
            label="OFFICIAL_OPEN_CLOUD_SOURCE_CAPTURE",
        ).astimezone(OPEN_JAKARTA)
        if source_captured != captured:
            raise v1.CloudPaperRuntimeError(
                "OFFICIAL_OPEN_CLOUD_ADMISSION_SOURCE_CAPTURE_MISMATCH"
            )
        admitted.append(
            (
                raw_commit,
                loaded,
                {
                    "session_date": session,
                    "slot": slot,
                    "slot_manifest_sha256": v1.sha256_bytes(raw_commit),
                    "source_manifest_sha256": v1.sha256_bytes(
                        loaded["source_manifest"]
                    ),
                    "expected_producer_capture_code_ref": expected_producer_ref,
                    "actual_producer_capture_code_ref": capture_code_ref,
                    "producer_runner": runner["runner"],
                    **trigger,
                    "scheduled_capture_timestamp_jakarta": scheduled.isoformat(),
                    "source_capture_timestamp_jakarta": captured.isoformat(),
                    "capture_lag_seconds": declared_lag,
                    "producer_execution_admission": OPEN_EXECUTION_ADMISSION,
                    "execution_admitted": True,
                    "admission_window_start_jakarta": scheduled.isoformat(),
                    "admission_window_end_jakarta": hard_deadline.isoformat(),
                },
            )
        )

    if not admitted:
        return None
    _, loaded, admission = admitted[0]
    # Validate every present slot before materialising the first admissible one,
    # preserving V1's malformed-later-slot fail-closed behaviour.
    target = Path(target_root).expanduser().resolve() / session
    target.mkdir(parents=True, exist_ok=True)
    filenames = {
        "raw_response": "raw_response.json",
        "open_prices": "open_prices.parquet",
        "source_manifest": "manifest.json",
    }
    for name, filename in filenames.items():
        destination = target / filename
        payload = loaded[name]
        if destination.exists() and destination.read_bytes() != payload:
            raise v1.CloudPaperRuntimeError("OFFICIAL_OPEN_LOCAL_COLLISION:" + name)
        if not destination.exists():
            destination.write_bytes(payload)
    try:
        from .official_open_cloud_archive_v1 import _verify_source_bundle

        _verify_source_bundle(target / "manifest.json", expected_session=session)
    except Exception as exc:
        raise v1.CloudPaperRuntimeError("OFFICIAL_OPEN_SOURCE_BUNDLE_INVALID") from exc
    admission["local_manifest"] = str((target / "manifest.json").resolve())
    return admission


__all__ = [
    "NATIVE_SCHEDULE_AUTHORITY",
    "SCHEDULER_ATTESTATION_SCHEMA",
    "TRUSTED_EXTERNAL_AUTHORITY",
    "materialize_official_open_from_cloud_v2",
]
