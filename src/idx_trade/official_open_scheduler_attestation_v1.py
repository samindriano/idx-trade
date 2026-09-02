"""Cryptographic trigger provenance for Official Open recovery dispatches.

Native GitHub ``schedule`` remains a trusted trigger class.  A
``workflow_dispatch`` is trusted only when it carries an HMAC-SHA256 attestation
bound to the exact repository, session, logical slot, issue time, and nonce.
Arbitrary/manual dispatch therefore cannot write the deterministic production
slot before a legitimate recovery capture.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import hmac
import json
import re
from typing import Mapping


SCHEMA_VERSION = "idx_official_open_external_scheduler_attestation_v1"
REPOSITORY = "samindriano/idx-trade"
TRUSTED_EXTERNAL_AUTHORITY = "TRUSTED_EXTERNAL_SCHEDULER_V1"
NATIVE_SCHEDULE_AUTHORITY = "NATIVE_GITHUB_SCHEDULE"
SLOTS = frozenset({"0902", "0912", "0922"})
_NONCE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_SIGNATURE = re.compile(r"^[0-9a-f]{64}$")


class OfficialOpenSchedulerAttestationError(RuntimeError):
    pass


def _session(value: str) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise OfficialOpenSchedulerAttestationError(
            "OFFICIAL_OPEN_SCHEDULER_SESSION_INVALID"
        ) from exc


def _slot(value: str) -> str:
    slot = str(value).strip()
    if slot not in SLOTS:
        raise OfficialOpenSchedulerAttestationError(
            f"OFFICIAL_OPEN_SCHEDULER_SLOT_INVALID:{slot}"
        )
    return slot


def _issued_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise OfficialOpenSchedulerAttestationError(
            "OFFICIAL_OPEN_SCHEDULER_ISSUED_AT_INVALID"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OfficialOpenSchedulerAttestationError(
            "OFFICIAL_OPEN_SCHEDULER_ISSUED_AT_INVALID"
        )
    return parsed.astimezone(timezone.utc).isoformat()


def canonical_attestation_body(
    *, session_date: str, slot: str, issued_at: str, nonce: str
) -> bytes:
    session = _session(session_date)
    logical_slot = _slot(slot)
    issued = _issued_at(issued_at)
    nonce_value = str(nonce).strip()
    if _NONCE.fullmatch(nonce_value) is None:
        raise OfficialOpenSchedulerAttestationError(
            "OFFICIAL_OPEN_SCHEDULER_NONCE_INVALID"
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "repository": REPOSITORY,
        "session_date": session,
        "slot": logical_slot,
        "issued_at_utc": issued,
        "nonce": nonce_value,
    }
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def sign_external_scheduler_attestation(
    *, secret: str, session_date: str, slot: str, issued_at: str, nonce: str
) -> str:
    key = str(secret or "").encode("utf-8")
    if not key:
        raise OfficialOpenSchedulerAttestationError(
            "OFFICIAL_OPEN_SCHEDULER_HMAC_KEY_MISSING"
        )
    body = canonical_attestation_body(
        session_date=session_date, slot=slot, issued_at=issued_at, nonce=nonce
    )
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def verify_external_scheduler_attestation(
    *,
    secret: str,
    session_date: str,
    slot: str,
    issued_at: str,
    nonce: str,
    signature: str,
) -> dict[str, object]:
    declared = str(signature or "").strip().lower()
    if _SIGNATURE.fullmatch(declared) is None:
        raise OfficialOpenSchedulerAttestationError(
            "OFFICIAL_OPEN_SCHEDULER_SIGNATURE_INVALID"
        )
    expected = sign_external_scheduler_attestation(
        secret=secret,
        session_date=session_date,
        slot=slot,
        issued_at=issued_at,
        nonce=nonce,
    )
    if not hmac.compare_digest(declared, expected):
        raise OfficialOpenSchedulerAttestationError(
            "OFFICIAL_OPEN_SCHEDULER_SIGNATURE_MISMATCH"
        )
    body = canonical_attestation_body(
        session_date=session_date, slot=slot, issued_at=issued_at, nonce=nonce
    )
    body_payload = json.loads(body.decode("utf-8"))
    return {
        "trigger_authority": TRUSTED_EXTERNAL_AUTHORITY,
        "scheduler_attestation_schema": SCHEMA_VERSION,
        "scheduler_issued_at_utc": body_payload["issued_at_utc"],
        "scheduler_nonce_sha256": hashlib.sha256(str(nonce).encode("utf-8")).hexdigest(),
        "scheduler_attestation_sha256": hashlib.sha256(
            body + b"\n" + declared.encode("ascii")
        ).hexdigest(),
    }


def trusted_runner_provenance(
    *, env: Mapping[str, str], session_date: str, slot: str
) -> dict[str, object]:
    event = str(env.get("GITHUB_EVENT_NAME") or "")
    base: dict[str, object] = {
        "runner": "GITHUB_ACTIONS" if env.get("GITHUB_ACTIONS") == "true" else "LOCAL_OR_OTHER",
        "github_repository": env.get("GITHUB_REPOSITORY", ""),
        "github_sha": env.get("GITHUB_SHA", ""),
        "github_workflow": env.get("GITHUB_WORKFLOW", ""),
        "github_event_name": event,
        "github_run_id": env.get("GITHUB_RUN_ID", ""),
        "github_run_attempt": env.get("GITHUB_RUN_ATTEMPT", ""),
        "capture_code_ref": env.get("OFFICIAL_OPEN_CAPTURE_CODE_REF", ""),
        "logical_slot": _slot(slot),
        "session_date": _session(session_date),
    }
    if base["runner"] != "GITHUB_ACTIONS" or base["github_repository"] != REPOSITORY:
        raise OfficialOpenSchedulerAttestationError(
            "OFFICIAL_OPEN_TRIGGER_RUNNER_NOT_PRODUCTION_GITHUB"
        )
    if event == "schedule":
        base["trigger_authority"] = NATIVE_SCHEDULE_AUTHORITY
        return base
    if event != "workflow_dispatch":
        raise OfficialOpenSchedulerAttestationError(
            "OFFICIAL_OPEN_TRIGGER_EVENT_NOT_ADMITTED"
        )

    proof = verify_external_scheduler_attestation(
        secret=env.get("OFFICIAL_OPEN_SCHEDULER_HMAC_KEY", ""),
        session_date=session_date,
        slot=slot,
        issued_at=env.get("OFFICIAL_OPEN_SCHEDULER_ISSUED_AT", ""),
        nonce=env.get("OFFICIAL_OPEN_SCHEDULER_NONCE", ""),
        signature=env.get("OFFICIAL_OPEN_SCHEDULER_SIGNATURE", ""),
    )
    return {**base, **proof}


__all__ = [
    "NATIVE_SCHEDULE_AUTHORITY",
    "OfficialOpenSchedulerAttestationError",
    "REPOSITORY",
    "SCHEMA_VERSION",
    "TRUSTED_EXTERNAL_AUTHORITY",
    "canonical_attestation_body",
    "sign_external_scheduler_attestation",
    "trusted_runner_provenance",
    "verify_external_scheduler_attestation",
]
