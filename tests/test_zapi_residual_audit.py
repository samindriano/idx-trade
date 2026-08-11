import numpy as np
import pandas as pd

from idx_trade.zapi_residual_audit import (
    ERROR_OR_SYMBOL_CLASS,
    NO_FACTOR_HLC_CLASS,
    NO_PROVIDER_CLASS,
    build_arbitration,
    build_targeted_sample,
    classify_residual_rows,
    fetch_zapi_date_grouped,
    _write_artifact_manifest,
)
from idx_trade.tier2_open_audit import audit_provider_rows


def _audit_frame():
    rows = []
    for i in range(12):
        ticker = f"M{i:02d}"
        rows.append(
            {
                "ticker": ticker,
                "date": pd.Timestamp("2024-01-02") + pd.Timedelta(days=i),
                "panel_open": None,
                "panel_high": 110.0,
                "panel_low": 90.0,
                "panel_close": 100.0,
                "raw_open": 95.0,
                "raw_high": 111.0,
                "raw_low": 90.0,
                "raw_close": 100.0,
                "provider_row_present": True,
                "hlc_exact": False,
                "known_open_exact": pd.NA,
                "direct_admissible": False,
                "split_admissible": False,
                "split_factor": 1.0,
                "split_factor_status": "NO_FUTURE_SPLIT",
                "split_reconstructed_hlc_exact": False,
            }
        )
    for i in range(8):
        ticker = f"G{i:02d}"
        rows.append(
            {
                "ticker": ticker,
                "date": pd.Timestamp("2023-03-01") + pd.Timedelta(days=i),
                "panel_open": None,
                "panel_high": 210.0,
                "panel_low": 180.0,
                "panel_close": 200.0,
                "raw_open": None,
                "raw_high": None,
                "raw_low": None,
                "raw_close": None,
                "provider_row_present": False,
                "hlc_exact": False,
                "known_open_exact": pd.NA,
                "direct_admissible": False,
                "split_admissible": False,
                "split_factor": None,
                "split_factor_status": None,
                "split_reconstructed_hlc_exact": False,
            }
        )
    for i in range(8):
        ticker = f"C{i:02d}"
        rows.append(
            {
                "ticker": ticker,
                "date": pd.Timestamp("2025-05-01") + pd.Timedelta(days=i),
                "panel_open": 300.0,
                "panel_high": 320.0,
                "panel_low": 290.0,
                "panel_close": 310.0,
                "raw_open": 300.0,
                "raw_high": 320.0,
                "raw_low": 290.0,
                "raw_close": 310.0,
                "provider_row_present": True,
                "hlc_exact": True,
                "known_open_exact": True,
                "direct_admissible": False,
                "split_admissible": False,
                "split_factor": 1.0,
                "split_factor_status": "NO_FUTURE_SPLIT",
                "split_reconstructed_hlc_exact": False,
            }
        )
    return pd.DataFrame(rows)


def test_residual_classification_and_deterministic_sample():
    audit = _audit_frame()
    status = pd.DataFrame(
        [
            {"ticker": "G00", "status": "ERROR"},
            *[{"ticker": ticker, "status": "SUCCESS"} for ticker in audit["ticker"].unique() if ticker != "G00"],
        ]
    )
    classified = classify_residual_rows(audit, status)
    assert classified.loc[classified["ticker"].eq("G00"), "residual_problem_class"].iloc[0] == ERROR_OR_SYMBOL_CLASS
    assert classified.loc[classified["ticker"].eq("G01"), "residual_problem_class"].iloc[0] == NO_PROVIDER_CLASS
    assert classified.loc[classified["ticker"].eq("M00"), "residual_problem_class"].iloc[0] == NO_FACTOR_HLC_CLASS

    first = build_targeted_sample(
        classified,
        status,
        hlc_mismatch_rows=6,
        provider_gap_rows=5,
        control_rows=4,
    )
    second = build_targeted_sample(
        classified,
        status,
        hlc_mismatch_rows=6,
        provider_gap_rows=5,
        control_rows=4,
    )
    pd.testing.assert_frame_equal(first, second)
    assert first["sample_role"].value_counts().to_dict() == {
        "RESIDUAL_HLC_MISMATCH": 6,
        "RESIDUAL_PROVIDER_GAP": 5,
        "KNOWN_CONTROL": 4,
    }
    assert "G00" in set(first.loc[first["sample_role"].eq("RESIDUAL_PROVIDER_GAP"), "ticker"])


def test_fetch_zapi_without_key_fails_closed():
    sample = pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "date": [pd.Timestamp("2025-01-02")],
        }
    )
    result = fetch_zapi_date_grouped(sample, api_key=None)
    assert result["access_status"] == "ZAPI_BLOCKED_CREDENTIAL_ABSENT"
    assert result["requests_made"] == 0
    assert result["rows"].empty


def test_arbitration_distinguishes_panel_yahoo_and_recovery():
    sample = pd.DataFrame(
        [
            {
                "sample_id": "Z2-001",
                "residual_problem_class": NO_FACTOR_HLC_CLASS,
                "yahoo_raw_open": 10.0,
                "yahoo_raw_high": 12.0,
                "yahoo_raw_low": 9.0,
                "yahoo_raw_close": 11.0,
            },
            {
                "sample_id": "Z2-002",
                "residual_problem_class": NO_PROVIDER_CLASS,
                "yahoo_raw_open": None,
                "yahoo_raw_high": None,
                "yahoo_raw_low": None,
                "yahoo_raw_close": None,
            },
        ]
    )
    audit = pd.DataFrame(
        [
            {
                "sample_id": "Z2-001",
                "sample_role": "RESIDUAL_HLC_MISMATCH",
                "diagnostic": "HLC_MISMATCH_HIGH",
                "admission_status": "REJECTED",
                "hlc_exact": False,
                "known_open_exact": None,
                "raw_open": 10.0,
                "raw_high": 12.0,
                "raw_low": 9.0,
                "raw_close": 11.0,
            },
            {
                "sample_id": "Z2-002",
                "sample_role": "RESIDUAL_PROVIDER_GAP",
                "diagnostic": "FROZEN_CONTRACT_PASS",
                "admission_status": "ADMISSIBLE_OPEN_EVIDENCE",
                "hlc_exact": True,
                "known_open_exact": None,
                "raw_open": 100.0,
                "raw_high": 110.0,
                "raw_low": 90.0,
                "raw_close": 105.0,
            },
        ]
    )
    result = build_arbitration(sample, audit)
    classes = dict(zip(result["sample_id"], result["arbitration_class"]))
    assert classes["Z2-001"] == "SOURCE2_SUPPORTS_YAHOO"
    assert classes["Z2-002"] == "SOURCE2_RECOVERY_CANDIDATE"


def test_known_control_numpy_boolean_is_classified_as_exact():
    sample = pd.DataFrame(
        {
            "sample_id": ["CONTROL-1"],
            "residual_problem_class": [None],
            "yahoo_raw_open": [100.0],
            "yahoo_raw_high": [110.0],
            "yahoo_raw_low": [90.0],
            "yahoo_raw_close": [105.0],
        }
    )
    audit = pd.DataFrame(
        {
            "sample_id": ["CONTROL-1"],
            "sample_role": ["KNOWN_CONTROL"],
            "diagnostic": ["KNOWN_OPEN_EXACT"],
            "admission_status": ["EXISTING_OPEN_PRESERVED_EXACT"],
            "hlc_exact": [True],
            "known_open_exact": pd.Series([np.bool_(True)], dtype=object),
            "raw_open": [100.0],
            "raw_high": [110.0],
            "raw_low": [90.0],
            "raw_close": [105.0],
        }
    )
    result = build_arbitration(sample, audit)
    assert result.loc[0, "arbitration_class"] == "CONTROL_PANEL_HLC_OPEN_EXACT"


def test_artifact_manifest_excludes_summary_and_manifest(tmp_path):
    (tmp_path / "zapi_targeted_summary.json").write_text("stale", encoding="utf-8")
    (tmp_path / "sample.csv").write_text("ticker\nBBCA\n", encoding="utf-8")

    manifest_sha = _write_artifact_manifest(tmp_path)

    import hashlib
    import json

    manifest_path = tmp_path / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert set(manifest["files"]) == {"sample.csv"}
    assert manifest_sha == hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def test_known_control_role_is_compared_as_existing_open():
    sample = pd.DataFrame(
        {
            "sample_id": ["CONTROL-1"],
            "sample_role": ["KNOWN_CONTROL"],
            "ticker": ["BBCA"],
            "date": [pd.Timestamp("2025-01-02")],
            "panel_open": [100.0],
            "panel_high": [110.0],
            "panel_low": [90.0],
            "panel_close": [105.0],
        }
    )
    provider = pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "date": [pd.Timestamp("2025-01-02")],
            "raw_open": [100.0],
            "raw_high": [110.0],
            "raw_low": [90.0],
            "raw_close": [105.0],
            "raw_volume": [1.0],
            "source_ref": ["test://zapi"],
        }
    )

    audit, summary = audit_provider_rows(sample, provider, "TEST_ZAPI")

    assert summary["known_open_sample_rows"] == 1
    assert summary["known_open_comparison_rows"] == 1
    assert summary["known_open_exact_count"] == 1
    assert audit.loc[0, "admission_status"] == "PRESERVED_EXISTING_OPEN"
