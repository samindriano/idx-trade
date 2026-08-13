from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from idx_trade.tradingview_open_price_path_remediation import (
    bps_difference,
    extract_preopen_reconciliation,
    extract_first_60m_pair_reconciliation,
)
from scripts.run_tradingview_open_price_path_remediation import _load_config
from scripts.run_tradingview_open_session_semantics import live_plan


WIB = ZoneInfo("Asia/Jakarta")


def _epoch(hour: int, minute: int) -> int:
    return int(datetime(2026, 7, 1, hour, minute, tzinfo=WIB).timestamp())


def _write_probe(root: Path) -> None:
    raw = root / "raw" / "live"
    raw.mkdir(parents=True)
    common = {
        "status": "AVAILABLE",
        "market_info": {"timezone": "Asia/Bangkok", "session": "0900-1630"},
    }
    extended = {
        **common,
        "periods": [
            {"time": _epoch(8, 58), "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10},
        ],
    }
    regular = {
        **common,
        "periods": [
            {"time": _epoch(9, 0), "open": 103, "high": 104, "low": 102, "close": 103, "volume": 20},
        ],
    }
    (raw / "0001_BBCA_2026-07-01_60m_extended.json").write_text(json.dumps({"request": {"ticker": "BBCA", "date": "2026-07-01", "timeframe": "60", "session": "extended"}, "response": extended}), encoding="utf-8")
    (raw / "0002_BBCA_2026-07-01_60m_regular.json").write_text(json.dumps({"request": {"ticker": "BBCA", "date": "2026-07-01", "timeframe": "60", "session": "regular"}, "response": regular}), encoding="utf-8")


def test_bps_difference_is_exact_and_non_repairing() -> None:
    assert bps_difference(101, 100) == pytest.approx(100.0)
    assert bps_difference(99, 100) == pytest.approx(-100.0)
    assert bps_difference(100, 0) is None


def test_preopen_extraction_pairs_exact_timeframe_and_compares_official_open(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_probe(session_root)
    admission_root = tmp_path / "admission"
    (admission_root / "normalized").mkdir(parents=True)
    pd.DataFrame([{"ticker": "BBCA", "session_date": "2026-07-01", "open": 101}]).to_csv(admission_root / "normalized" / "tv1d_comparison.csv", index=False)
    panel = tmp_path / "panel.parquet"
    pd.DataFrame([
        {"ticker": "BBCA", "date": "2026-06-30", "open": 95, "close": 98},
        {"ticker": "BBCA", "date": "2026-07-01", "open": 100, "close": 103},
    ]).to_parquet(panel, index=False)

    bars, reconciliation, summary = extract_preopen_reconciliation(session_root, admission_root, panel, ["BBCA"])

    assert len(bars) == 1
    assert bars.iloc[0]["timestamp_wib"].startswith("2026-07-01T08:58")
    assert len(reconciliation) == 1
    row = reconciliation.iloc[0]
    assert row["preopen_open"] == 100
    assert row["regular_first_open"] == 103
    assert bool(row["preopen_open_equals_official_open"]) is True
    assert bool(row["preopen_open_equals_tv1d_open"]) is False
    assert bool(row["official_open_inside_preopen_hl"]) is True
    assert row["regular_open_diff_bps_official"] == pytest.approx(300.0)
    assert summary["preopen_bar_rows"] == 1


def test_remediation_live_plan_is_exactly_thirty_60m_requests() -> None:
    path = Path(__file__).parents[1] / "config" / "tradingview_open_price_path_remediation_v1.json"
    config = _load_config(path)
    plan = live_plan(config)

    assert len(plan) == 30
    assert {row["timeframe"] for row in plan} == {"60"}
    assert {row["session"] for row in plan} == {"regular", "extended"}
    assert {row["ticker"] for row in plan} == {"BBCA", "BBRI", "BMRI", "TLKM", "ASII"}
    assert all(row["adjustment"] == "none" and row["fetch_more_steps"] == 0 for row in plan)


def test_first_60m_pair_reconciliation_preserves_both_session_opens(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    _write_probe(session_root)
    admission_root = tmp_path / "admission"
    (admission_root / "normalized").mkdir(parents=True)
    pd.DataFrame([{"ticker": "BBCA", "session_date": "2026-07-01", "open": 101}]).to_csv(admission_root / "normalized" / "tv1d_comparison.csv", index=False)
    panel = tmp_path / "panel.parquet"
    pd.DataFrame([
        {"ticker": "BBCA", "date": "2026-06-30", "open": 95, "close": 98},
        {"ticker": "BBCA", "date": "2026-07-01", "open": 100, "close": 103},
    ]).to_parquet(panel, index=False)

    pair = extract_first_60m_pair_reconciliation(session_root, admission_root, panel, ["BBCA"], ["2026-07-01"])

    assert len(pair) == 1
    row = pair.iloc[0]
    assert row["extended60_first_timestamp_wib"].startswith("2026-07-01T08:58")
    assert row["regular60_first_timestamp_wib"].startswith("2026-07-01T09:00")
    assert row["extended60_open"] == 100
    assert row["regular60_open"] == 103
    assert bool(row["extended60_open_equals_official_open"]) is True
    assert bool(row["regular60_open_equals_official_open"]) is False
    assert row["regular60_open_diff_bps_official"] == pytest.approx(300.0)


def test_temporary_checkpoint_file_is_absent() -> None:
    assert not (Path(__file__).parents[1] / "docs" / "checkpoints" / "__tmp_should_not_create.md").exists()
