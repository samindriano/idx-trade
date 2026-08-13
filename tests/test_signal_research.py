import pandas as pd
import pytest

from idx_trade.signal_research import (
    EXECUTION_GRADE_OHLCV,
    SIGNAL_RESEARCH_HLCV,
    build_signal_research_hlcv_panel,
    create_signal_research_snapshot_manifest,
    validate_signal_research_hlcv,
    verify_signal_research_snapshot_manifest,
    write_signal_research_hlcv_panel,
)


def _official():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-02", "2026-06-03"]),
            "high": [105.0, 106.0],
            "low": [95.0, 96.0],
            "close": [100.0, 101.0],
            "volume": [1000.0, 1200.0],
            "regular_market_value": [100000.0, 121200.0],
            "source": ["IDX_PUBLIC_STOCK_SUMMARY"] * 2,
        }
    )


def test_signal_contract_is_explicit_and_open_is_nullable(tmp_path):
    assert EXECUTION_GRADE_OHLCV != SIGNAL_RESEARCH_HLCV
    panel = build_signal_research_hlcv_panel(
        {"AAAA": _official()},
        ["AAAA"],
        {"AAAA": pd.to_datetime(["2026-06-02", "2026-06-03"])},
        corporate_action_verified={"AAAA": True},
    )

    assert validate_signal_research_hlcv(panel)
    assert panel["open"].isna().all()
    assert panel["open_available"].eq(False).all()
    assert panel["signal_contract"].eq(SIGNAL_RESEARCH_HLCV).all()

    summary = write_signal_research_hlcv_panel(panel, tmp_path / "signal.parquet")
    assert summary["rows"] == 2
    assert summary["null_open_rows"] == 2
    stored = pd.read_parquet(tmp_path / "signal.parquet")
    pd.testing.assert_frame_equal(
        stored.drop(columns=["open"]), panel.drop(columns=["open"]), check_dtype=False
    )
    assert stored["open"].isna().all()


def test_signal_panel_can_keep_reconciled_optional_provider_open():
    raw = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-02"]),
            "raw_open": [99.0],
        }
    )
    panel = build_signal_research_hlcv_panel(
        {"AAAA": _official().iloc[[0]]},
        ["AAAA"],
        {"AAAA": ["2026-06-02"]},
        raw_price_frames={"AAAA": raw},
        corporate_action_verified={"AAAA": True},
    )
    assert panel.loc[0, "open"] == 99.0
    assert bool(panel.loc[0, "open_available"]) is True
    assert panel.loc[0, "open_evidence_status"] == "YAHOO_RAW_OPTIONAL"


def test_signal_panel_fails_closed_on_missing_hlcv_or_action_integrity():
    with pytest.raises(ValueError, match="Missing official signal HLCV"):
        build_signal_research_hlcv_panel(
            {},
            ["AAAA"],
            {"AAAA": ["2026-06-02"]},
            corporate_action_verified={"AAAA": True},
        )
    with pytest.raises(ValueError, match="Corporate-action integrity"):
        build_signal_research_hlcv_panel(
            {"AAAA": _official()},
            ["AAAA"],
            {"AAAA": ["2026-06-02", "2026-06-03"]},
            corporate_action_verified={"AAAA": False},
        )


def test_signal_research_manifest_hashes_and_verifies(tmp_path):
    artifact = tmp_path / "panel.parquet"
    artifact.write_bytes(b"signal-panel")
    manifest_path = tmp_path / "signal_manifest.json"
    manifest = create_signal_research_snapshot_manifest(
        {
            "signal_research_decision": "GO",
            "unknown_expected_active_intersection": 0,
            "window_start": "2021-04-29",
            "window_end": "2026-07-31",
        },
        {"signal_panel": artifact},
        code_commit="abc123",
        output_path=manifest_path,
    )
    assert manifest["manifest_type"] == "SIGNAL_RESEARCH_1260"
    assert verify_signal_research_snapshot_manifest(manifest)["valid"] is True
