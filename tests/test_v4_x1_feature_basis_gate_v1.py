from __future__ import annotations

from pathlib import Path

import pandas as pd

from idx_trade import v4_x1_population_admission_v1 as gate
from idx_trade.provenance import sha256_file
from idx_trade.ranking_v4_3_features import V4_CONTROL_FEATURE_COLUMNS
from idx_trade.storage import write_parquet_atomic
from idx_trade.ranking_v4_3_preregistration import SESSION_GEOMETRY_FEATURE_COLUMNS


SESSION = "2026-08-28"
OBSERVED_AT = "2026-08-28T18:35:00+07:00"


def test_window_contract_matches_actual_frozen_final_feature_order() -> None:
    assert tuple(feature for feature, _ in gate.FEATURE_BASIS_WINDOW_CONTRACT) == (
        *V4_CONTROL_FEATURE_COLUMNS,
        *SESSION_GEOMETRY_FEATURE_COLUMNS,
    )


def _fixture(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    model_path = tmp_path / "model_input.parquet"
    panel_path = tmp_path / "clean_panel.parquet"
    write_parquet_atomic(
        pd.DataFrame(
            {
                "ticker": ["AAAA"],
                "date": [SESSION],
                "close": [10.0],
            }
        ),
        model_path,
    )
    dates = pd.date_range("2026-06-29", periods=62, freq="D")
    write_parquet_atomic(
        pd.DataFrame(
            {"ticker": ["AAAA"] * len(dates), "date": dates, "close": [10.0] * len(dates)}
        ),
        panel_path,
    )
    record = {
        "ticker": "AAAA",
        "state": "CERTIFIED_SAME_BASIS",
        "field_states": {
            "high": "CERTIFIED_SAME_BASIS",
            "low": "CERTIFIED_SAME_BASIS",
            "close": "CERTIFIED_SAME_BASIS",
            "volume": "CERTIFIED_SAME_BASIS",
            "regular_market_value": "CERTIFIED_SAME_BASIS",
        },
        "transition_dates": [],
        "authority": {
            "name": "IDX_TEST_AUTHORITY",
            "ref": "test://authority",
            "sha256": "d" * 64,
        },
        "source_refs": ["test://feature-basis"],
        "source_hashes": {
            "high": "a" * 64,
            "low": "b" * 64,
            "close": "c" * 64,
            "volume": "d" * 64,
            "regular_market_value": "e" * 64,
        },
    }
    evidence = {
        "schema_version": gate.FEATURE_BASIS_SCHEMA_VERSION,
        "policy_id": gate.FEATURE_BASIS_POLICY_ID,
        "session_date": SESSION,
        "knowledge_at": OBSERVED_AT,
        "model_input_path": str(model_path.resolve()),
        "model_input_sha256": sha256_file(model_path),
        "model_input_set_sha256": gate._set_hash(["AAAA"]),
        "clean_panel_path": str(panel_path.resolve()),
        "clean_panel_sha256": sha256_file(panel_path),
        "scorer_boundary": {
            "source": "MAX_DATE_FROM_CLEAN_PANEL",
            "historical_end": "2026-08-29",
            "clean_panel_sha256": sha256_file(panel_path),
        },
        "identity_attestation": {
            "status": "VERIFIED",
            "ref": "test://identity",
            "sha256": "e" * 64,
        },
        "calendar_attestation": {
            "status": "VERIFIED",
            "ref": "test://calendar",
            "sha256": "f" * 64,
        },
        "revision_attestation": {
            "status": "VERIFIED",
            "ref": "test://revision",
            "sha256": "1" * 64,
        },
        "pit_attestation": {
            "status": "VERIFIED",
            "ref": "test://pit",
            "sha256": "2" * 64,
            "knowledge_at": OBSERVED_AT,
        },
        "window_contract": [
            {"feature": feature, "potential_mixed_basis_span": span}
            for feature, span in gate.FEATURE_BASIS_WINDOW_CONTRACT
        ],
        "window_contract_sha256": gate._feature_basis_window_contract_sha256(),
        "records": [record],
    }
    context = {
        "session_date": SESSION,
        "model_input_tickers": ["AAAA"],
        "model_input_path": model_path,
        "model_input_sha256": sha256_file(model_path),
        "clean_panel_path": panel_path,
        "clean_panel_sha256": sha256_file(panel_path),
        "official_session_dates": dates,
        "evidence": evidence,
        "observed_at": OBSERVED_AT,
    }
    return context, record


def test_explicit_same_basis_whole_population_is_safe(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_SAFE
    assert result["reason_codes"] == []


def test_missing_certificate_is_source_capture_unresolved(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["evidence"] = None
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert result["reason_codes"] == ["FEATURE_BASIS_EVIDENCE_MISSING"]


def test_no_known_transition_is_not_a_certified_no_event(tmp_path: Path) -> None:
    context, record = _fixture(tmp_path)
    record["state"] = "NO_KNOWN_TRANSITION"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_NOT_CERTIFIED:AAAA:NO_KNOWN_TRANSITION" in result[
        "reason_codes"
    ]


def test_transition_inside_longest_feature_window_blocks_whole_session(
    tmp_path: Path,
) -> None:
    context, record = _fixture(tmp_path)
    record["state"] = "CERTIFIED_TRANSITION"
    record["transition_dates"] = ["2026-08-27"]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_TRANSITION_OVERLAP
    assert any(
        reason.startswith("BASIS_TRANSITION_OVERLAP:AAAA:2026-08-27:")
        for reason in result["reason_codes"]
    )


def test_transition_outside_exact_window_can_be_admitted(tmp_path: Path) -> None:
    context, record = _fixture(tmp_path)
    record["state"] = "CERTIFIED_TRANSITION"
    record["transition_dates"] = ["2026-06-29"]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_SAFE


def test_field_basis_mismatch_is_not_hidden_by_top_level_certificate(
    tmp_path: Path,
) -> None:
    context, record = _fixture(tmp_path)
    record["field_states"]["volume"] = "CERTIFIED_TRANSITION"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_FIELD_BASIS_NOT_SAFE:AAAA" in result["reason_codes"]


def test_evidence_hash_and_path_binding_fail_closed(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["evidence"]["clean_panel_sha256"] = "0" * 64
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_CLEAN_PANEL_HASH_MISMATCH" in result["reason_codes"]


def test_partial_attestation_is_not_population_safe(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    del context["evidence"]["pit_attestation"]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_PIT_ATTESTATION_INVALID" in result["reason_codes"]


def test_extra_certificate_record_cannot_be_used_to_filter_the_population(
    tmp_path: Path,
) -> None:
    context, record = _fixture(tmp_path)
    extra = dict(record)
    extra["ticker"] = "BBBB"
    context["evidence"]["records"].append(extra)
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_RECORD_EXTRA:BBBB" in result["reason_codes"]


def test_future_transition_is_not_admitted_or_inferred(tmp_path: Path) -> None:
    context, record = _fixture(tmp_path)
    record["state"] = "CERTIFIED_TRANSITION"
    record["transition_dates"] = ["2026-08-29"]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_TRANSITION_AFTER_SESSION:AAAA:2026-08-29" in result[
        "reason_codes"
    ]
