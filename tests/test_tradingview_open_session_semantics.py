import json
from pathlib import Path

import pandas as pd

from idx_trade.tradingview_open_session_semantics import (
    REQUIRED_PANEL_SHA256,
    build_session_forensics,
    classify_live_probe,
    inspect_market_info,
)
from scripts.run_tradingview_open_session_semantics import live_plan


def _write_raw(root: Path) -> None:
    raw = root / "raw" / "mathieu"
    raw.mkdir(parents=True)
    payload = {
        "request": {"ticker": "BBCA", "phase": "fixed_60m", "era": "y2021", "timeframe": "60", "server": "prodata"},
        "response": {
            "status": "AVAILABLE",
            "server": "prodata",
            "market_info": {
                "timezone": "Asia/Bangkok",
                "session": "0900-1630",
                "session_display": "0900-1630",
                "subsession_id": "regular",
                "subsessions": [
                    {"id": "premarket", "private": True, "session": "0845-0900"},
                    {"id": "regular", "private": False, "session": "0900-1630"},
                    {"id": "extended", "private": False, "session": "0845-1630"},
                ],
                "has_extended_hours": True,
                "has_intraday": True,
                "bar_source": "trade",
            },
            "periods": [
                {"time": 1625101200, "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
                {"time": 1625104800, "open": 100, "high": 102, "low": 100, "close": 101, "volume": 20},
            ],
            "event_trace": ["connected", "symbol_loaded", "update"],
        },
    }
    (raw / "0001_fixed_60m_BBCA_y2021_60.json").write_text(json.dumps(payload), encoding="utf-8")


def test_market_info_preserves_premarket_and_extended_metadata(tmp_path):
    _write_raw(tmp_path)
    frame = inspect_market_info(tmp_path)
    row = frame.iloc[0]
    assert row["timezone"] == "Asia/Bangkok"
    assert row["session"] == "0900-1630"
    assert bool(row["has_extended_hours"]) is True
    assert "0845-0900" in row["subsessions"]
    assert "0845-1630" in row["subsessions"]


def test_session_forensics_uses_first_two_chronological_bars(tmp_path):
    _write_raw(tmp_path)
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    bars = pd.DataFrame([
        {"ticker": "BBCA", "phase": "fixed_60m", "timeframe": "60", "session_date": "2021-07-01", "in_requested_window": True, "session_admissible": True, "raw_epoch": 1625101200, "timestamp_wib": "2021-07-01T09:00:00+07:00", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
        {"ticker": "BBCA", "phase": "fixed_60m", "timeframe": "60", "session_date": "2021-07-01", "in_requested_window": True, "session_admissible": True, "raw_epoch": 1625104800, "timestamp_wib": "2021-07-01T10:00:00+07:00", "open": 100, "high": 102, "low": 100, "close": 101, "volume": 20},
    ])
    bars.to_csv(normalized / "mathieu_intraday_bars.csv", index=False)
    pd.DataFrame([{"ticker": "BBCA", "session_date": "2021-07-01", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 30, "open_canonical": 100, "high_canonical": 102, "low_canonical": 99, "close_canonical": 101, "volume_canonical": 30, "open_exact": True, "hlc_exact": True, "corporate_action_quarantined": False, "year": 2021}]).to_csv(normalized / "daily_comparison.csv", index=False)
    pd.DataFrame([{"ticker": "BBCA", "session_date": "2021-07-01", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 30, "session_admissible": True}]).to_csv(normalized / "tv1d_comparison.csv", index=False)
    panel = tmp_path / "panel.parquet"
    pd.DataFrame([{"ticker": "BBCA", "date": "2021-06-30", "close": 98}, {"ticker": "BBCA", "date": "2021-07-01", "close": 101}]).to_parquet(panel, index=False)
    frame = build_session_forensics(tmp_path, panel)
    row = frame.iloc[0]
    assert row["tv60_bar_count"] == 2
    assert row["timestamp_wib_bar1"].startswith("2021-07-01T09:00")
    assert row["timestamp_wib_bar2"].startswith("2021-07-01T10:00")
    assert row["first_bar_open_vs_previous_close"] == 2


def test_classifier_requires_consistent_regular_vs_extended_pairs():
    rows = []
    for index in range(3):
        for session, count in (("regular", 0), ("extended", 1)):
            rows.append({"ticker": f"T{index}", "date": "2021-07-01", "timeframe": "1", "session": session, "status": "AVAILABLE", "preopen_bar_count": count})
    assert classify_live_probe(pd.DataFrame(rows), {"decision_rules": {"minimum_consistent_pairs_for_confirmed_exclusion": 3}}) == "TV60_OPEN_AUCTION_EXCLUSION_CONFIRMED"


def test_classifier_does_not_confirm_with_regular_preopen_contradiction():
    rows = []
    for index in range(3):
        for session, count in (("regular", 1 if index == 0 else 0), ("extended", 1)):
            rows.append({"ticker": f"T{index}", "date": "2021-07-01", "timeframe": "1", "session": session, "status": "AVAILABLE", "preopen_bar_count": count})
    assert classify_live_probe(pd.DataFrame(rows), {"decision_rules": {"minimum_consistent_pairs_for_confirmed_exclusion": 3}}) == "TV60_OPEN_BOUNDARY_PATTERN_FOUND_MEANING_UNPROVEN"


def test_live_plan_is_frozen_and_bounded():
    cfg = {"upstream": {"server": "prodata"}, "live_probe": {"tickers": ["BBCA", "BBRI", "BMRI", "TLKM", "ASII"], "dates": ["2021-07-01", "2024-07-01", "2026-07-01"], "timeframes": ["1", "5"], "sessions": ["regular", "extended"], "initial_range": 500, "timeout_ms": 25000, "fetch_more_steps": 0, "fetch_more_batch": 1, "fetch_more_wait_ms": 8000, "adjustment": "none"}}
    plan = live_plan(cfg)
    assert len(plan) == 60
    assert {row["symbol"] for row in plan} == {"IDX:BBCA", "IDX:BBRI", "IDX:BMRI", "IDX:TLKM", "IDX:ASII"}
    assert {row["session"] for row in plan} == {"regular", "extended"}
    assert {row["timeframe"] for row in plan} == {"1", "5"}
    assert all(row["adjustment"] == "none" and row["fetch_more_steps"] == 0 for row in plan)


def test_required_panel_hash_is_frozen():
    assert REQUIRED_PANEL_SHA256 == "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
