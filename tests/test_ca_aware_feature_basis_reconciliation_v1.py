from __future__ import annotations

from argparse import Namespace

import pytest

from scripts.run_ca_aware_feature_basis_reconciliation_v1 import (
    _family_verdict,
    require_hash,
    validate_identity_rows,
    run,
)


def test_identity_ledger_rejects_duplicate_ticker_date() -> None:
    rows = [{"ticker": "AAPL", "date": "2022-01-03"}, {"ticker": "AAPL", "date": "2022-01-03"}]
    with pytest.raises(RuntimeError, match="duplicate identity"):
        validate_identity_rows(rows, "synthetic")


def test_input_hash_gate_rejects_mismatch(tmp_path) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"immutable")
    with pytest.raises(RuntimeError, match="SHA256 mismatch"):
        require_hash(path, "0" * 64, "synthetic")


def test_absent_family_does_not_become_no_event_proof() -> None:
    verdict, reason, _ = _family_verdict("REVERSE_SPLIT", 0)
    assert verdict == "UNKNOWN_NO_POSITIVE_EVENT_PROOF"
    assert "absence" in reason


def test_run_refuses_existing_output_or_staging(tmp_path) -> None:
    output = tmp_path / "audit"
    output.mkdir()
    args = Namespace(
        phase_a_root=str(tmp_path / "phase-a"),
        phase_b_root=str(tmp_path / "phase-b"),
        ksei_root=str(tmp_path / "ksei"),
        ca_audit_root=str(tmp_path / "ca"),
        output_dir=str(output),
    )
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        run(args)


def test_run_refuses_existing_staging(tmp_path) -> None:
    output = tmp_path / "audit"
    (tmp_path / "audit.staging").mkdir()
    args = Namespace(
        phase_a_root=str(tmp_path / "phase-a"),
        phase_b_root=str(tmp_path / "phase-b"),
        ksei_root=str(tmp_path / "ksei"),
        ca_audit_root=str(tmp_path / "ca"),
        output_dir=str(output),
    )
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        run(args)
