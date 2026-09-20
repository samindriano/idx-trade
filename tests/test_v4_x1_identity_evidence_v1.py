from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from idx_trade.v4_x1_identity_evidence_v1 import (
    IDENTITY_EVIDENCE_SCHEMA,
    IdentityEvidenceError,
    load_identity_evidence,
)


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(
        (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")
    ).hexdigest()


def _write_evidence(tmp_path: Path, **updates: object) -> tuple[Path, str]:
    row = {
        "canonical_security_id": "ISSUER-T00",
        "ticker": "T00",
        "instrument_class": "COMMON_SHARE",
        "effective_from": "2020-01-01",
        "effective_to": None,
        "identity_revision": "R1",
        "source_ref": "IDX_TEST_SECURITY_MASTER:T00",
        "source_evidence_sha256": "a" * 64,
    }
    body: dict[str, object] = {
        "schema_version": IDENTITY_EVIDENCE_SCHEMA,
        "source_reference": "IDX_TEST_SECURITY_MASTER",
        "as_of_session_date": "2026-08-24",
        "identities": [row],
        "outcome_access": False,
    }
    body.update(updates)
    body["payload_sha256"] = _canonical_hash(body)
    path = tmp_path / "identity-evidence.json"
    encoded = (json.dumps(body, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(encoded)
    return path, hashlib.sha256(encoded).hexdigest()


def test_identity_evidence_is_hash_bound_and_resolves_required_ticker(
    tmp_path: Path,
) -> None:
    path, file_sha = _write_evidence(tmp_path)
    rows = load_identity_evidence(
        path,
        file_sha,
        as_of_session_date="2026-08-24",
        required_tickers=("T00",),
    )
    assert len(rows) == 1
    assert rows[0].canonical_security_id == "ISSUER-T00"


def test_identity_evidence_rejects_missing_ticker_and_file_tamper(
    tmp_path: Path,
) -> None:
    path, file_sha = _write_evidence(tmp_path)
    with pytest.raises(IdentityEvidenceError, match="REQUIRED_TICKER_UNRESOLVED"):
        load_identity_evidence(
            path,
            file_sha,
            as_of_session_date="2026-08-24",
            required_tickers=("T99",),
        )
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(IdentityEvidenceError, match="FILE_SHA_MISMATCH"):
        load_identity_evidence(
            path,
            file_sha,
            as_of_session_date="2026-08-24",
            required_tickers=("T00",),
        )


def test_identity_evidence_rejects_outcome_access_and_session_drift(
    tmp_path: Path,
) -> None:
    path, file_sha = _write_evidence(tmp_path, outcome_access=True)
    with pytest.raises(IdentityEvidenceError, match="OUTCOME_ACCESS_INVALID"):
        load_identity_evidence(
            path,
            file_sha,
            as_of_session_date="2026-08-24",
            required_tickers=("T00",),
        )
    path, file_sha = _write_evidence(tmp_path)
    with pytest.raises(IdentityEvidenceError, match="SESSION_MISMATCH"):
        load_identity_evidence(
            path,
            file_sha,
            as_of_session_date="2026-08-25",
            required_tickers=("T00",),
        )


def test_identity_evidence_rejects_hash_valid_noncanonical_extension(
    tmp_path: Path,
) -> None:
    path, file_sha = _write_evidence(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["unexpected_extension"] = "accepted-by-hash-only"
    body = dict(payload)
    body.pop("payload_sha256")
    payload["payload_sha256"] = _canonical_hash(body)
    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(encoded)

    with pytest.raises(IdentityEvidenceError, match="PAYLOAD_NOT_CANONICAL"):
        load_identity_evidence(
            path,
            hashlib.sha256(encoded).hexdigest(),
            as_of_session_date="2026-08-24",
            required_tickers=("T00",),
        )
