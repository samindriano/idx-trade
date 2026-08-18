from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

import idx_trade.v4_ca_target_continuity_bridge as bridge
from idx_trade.ranking_v4_3_target_execution import prepare_continuity_evidence


def _ledger() -> pd.DataFrame:
    rows = []
    for date in ("2026-01-05", "2026-01-06"):
        for ticker in ("AAAA", "BBBB"):
            for horizon in (5, 10):
                rows.append(
                    {
                        "ticker": ticker,
                        "signal_date": date,
                        "horizon": horizon,
                        "continuity_status": "RESOLVED_NO_MECHANICAL_DISCONTINUITY",
                        "continuity_reason": "NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL",
                        "blocking_event_ids": "",
                        "blocking_transition_dates": "",
                        "policy_id": "TEST_CA_POLICY",
                    }
                )
    return pd.DataFrame(rows)


def _certified_summary() -> dict:
    return {
        "schema_version": bridge.CA_SUMMARY_SCHEMA,
        "verdict": bridge.CA_CERTIFIED_VERDICT,
        "corporate_action_continuity_certified": True,
        "outcome_blind": True,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "frozen_rows": 8,
        "frozen_dates": 2,
        "per_date": {
            "h5_gate_dates": 2,
            "h10_gate_dates": 2,
            "consensus_gate_dates": 2,
            "h5_min_rate": 0.90,
            "h10_min_rate": 0.91,
            "consensus_min_rate": 0.90,
        },
        "output_hashes": {},
    }


def _manifest() -> dict:
    return {
        "schema_version": bridge.CA_MANIFEST_SCHEMA,
        "status": bridge.CA_CERTIFIED_VERDICT,
        "outcome_blind": True,
        "summary_sha256": "",
        "output_hashes": {},
    }


def _patch_shape(monkeypatch):
    monkeypatch.setattr(bridge, "EXPECTED_ROWS", 8)
    monkeypatch.setattr(bridge, "EXPECTED_DATES", 2)


def test_certified_summary_is_required(monkeypatch):
    _patch_shape(monkeypatch)
    summary = _certified_summary()
    summary["verdict"] = "V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED"
    with pytest.raises(RuntimeError, match="CA_CONTINUITY_NOT_CERTIFIED"):
        bridge.validate_certified_summary(summary, _manifest())


def test_h5_h10_base_population_must_match(monkeypatch):
    _patch_shape(monkeypatch)
    frame = _ledger()
    frame = frame[~((frame["ticker"] == "BBBB") & (frame["signal_date"] == "2026-01-05") & (frame["horizon"] == 10))]
    monkeypatch.setattr(bridge, "EXPECTED_ROWS", 7)
    with pytest.raises(RuntimeError, match="H5_H10_POPULATION_MISMATCH"):
        bridge.validate_continuity_ledger(frame)


def test_bridge_is_deterministic_and_target_schema_valid(monkeypatch):
    _patch_shape(monkeypatch)
    frame = _ledger()
    manifest_sha = "a" * 64
    ledger_sha = "b" * 64
    first = bridge.build_target_continuity_evidence(
        frame,
        accepted_ca_manifest_sha256=manifest_sha,
        continuity_ledger_sha256=ledger_sha,
    )
    second = bridge.build_target_continuity_evidence(
        frame.sample(frac=1.0, random_state=7),
        accepted_ca_manifest_sha256=manifest_sha,
        continuity_ledger_sha256=ledger_sha,
    )
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 8
    assert first["evidence_id"].str.startswith("V4_CA_CONTINUITY_ROW:").all()
    assert first["evidence_sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    prepared = prepare_continuity_evidence(first)
    pd.testing.assert_frame_equal(first, prepared)


def test_row_provenance_changes_when_ca_manifest_changes(monkeypatch):
    _patch_shape(monkeypatch)
    frame = _ledger()
    a = bridge.build_target_continuity_evidence(
        frame,
        accepted_ca_manifest_sha256="a" * 64,
        continuity_ledger_sha256="b" * 64,
    )
    b = bridge.build_target_continuity_evidence(
        frame,
        accepted_ca_manifest_sha256="c" * 64,
        continuity_ledger_sha256="b" * 64,
    )
    assert not a["evidence_sha256"].equals(b["evidence_sha256"])


def test_load_bundle_requires_exact_accepted_manifest_pin(tmp_path: Path, monkeypatch):
    _patch_shape(monkeypatch)
    ledger_path = tmp_path / "v4_frozen_continuity_ledger_event_window.csv"
    summary_path = tmp_path / "summary.json"
    manifest_path = tmp_path / "MANIFEST.json"

    _ledger().to_csv(ledger_path, index=False, lineterminator="\n")
    ledger_sha = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    summary = _certified_summary()
    summary["output_hashes"] = {"continuity_ledger": ledger_sha}
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_sha = hashlib.sha256(summary_path.read_bytes()).hexdigest()

    manifest = _manifest()
    manifest["summary_sha256"] = summary_sha
    manifest["output_hashes"] = {"continuity_ledger": ledger_sha}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    with pytest.raises(RuntimeError, match="CA_ACCEPTED_MANIFEST_SHA_MISMATCH"):
        bridge.load_and_verify_certified_bundle(
            tmp_path, expected_manifest_sha256="0" * 64
        )

    loaded, actual_manifest, actual_ledger = bridge.load_and_verify_certified_bundle(
        tmp_path, expected_manifest_sha256=manifest_sha
    )
    assert len(loaded) == 8
    assert actual_manifest == manifest_sha
    assert actual_ledger == ledger_sha
