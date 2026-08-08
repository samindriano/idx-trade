import json

import pandas as pd

from idx_trade.full_universe import (
    required_tickers_for_window,
    run_full_universe_data_gate,
)
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
)


def _master() -> pd.DataFrame:
    active = pd.DataFrame(
        {
            "ticker": ["AAAA", "CCCC"],
            "company_name": ["Active A", "Future IPO"],
            "listed_from": ["2020-01-01", "2026-08-10"],
            "listed_to": [None, None],
            "source": ["IDX", "IDX"],
        }
    )
    delisted = pd.DataFrame(
        {
            "ticker": ["BBBB", "DDDD"],
            "company_name": ["Old Delisted", "Mid Window Delisted"],
            "listed_from": ["2018-01-01", "2019-01-01"],
            "listed_to": ["2025-01-01", "2026-07-15"],
            "source": ["IDX_DELIST", "IDX_DELIST"],
        }
    )
    return build_security_master(active, delisted)


def test_required_tickers_for_window_uses_listing_interval_overlap():
    sessions = pd.to_datetime(["2026-06-02", "2026-07-31"])
    required = required_tickers_for_window(_master(), pd.DatetimeIndex(sessions))
    assert required == ["AAAA", "DDDD"]


def test_full_universe_gate_uses_same_hard_gate_and_writes_artifacts(tmp_path):
    sessions = pd.to_datetime(["2026-06-02", "2026-06-03", "2026-06-04"])
    master = build_security_master(
        pd.DataFrame(
            {
                "ticker": ["AAAA"],
                "company_name": ["Active A"],
                "listed_from": ["2020-01-01"],
                "listed_to": [None],
                "source": ["IDX"],
            }
        ),
        pd.DataFrame(),
    )
    anchors = canonicalize_tradability_anchors(
        pd.DataFrame(
            {
                "ticker": ["AAAA"] * 3,
                "market": ["REGULAR"] * 3,
                "as_of_date": sessions,
                "state": ["ACTIVE"] * 3,
                "source": ["IDX_STOCK_SUMMARY"] * 3,
                "source_ref": ["idx://summary"] * 3,
                "evidence_type": ["IDX_STOCK_SUMMARY_REGULAR_EXECUTION_OBSERVATION"] * 3,
            }
        )
    )
    prices = {
        "AAAA": pd.DataFrame(
            {
                "date": sessions,
                "raw_open": [100.0] * 3,
                "raw_high": [101.0] * 3,
                "raw_low": [99.0] * 3,
                "raw_close": [100.0] * 3,
                "raw_volume": [1_000_000.0] * 3,
            }
        )
    }

    report = run_full_universe_data_gate(
        pd.DatetimeIndex(sessions),
        prices,
        master,
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        tradability_anchors=anchors,
        split_history_verified={"AAAA": True},
        price_semantics_verified={"AAAA": True},
        output_dir=tmp_path,
    )

    summary = report["full_universe_summary"]
    assert summary["passed"] is True
    assert summary["required_tickers"] == 1
    assert summary["passed_tickers"] == 1
    assert summary["unknown_sessions"] == 0
    assert summary["missing_active_prices"] == 0
    assert summary["blocker_counts"] == {}

    saved = json.loads((tmp_path / "full_universe_gate_summary.json").read_text())
    assert saved["passed"] is True
    assert (tmp_path / "full_universe_ticker_gates.csv").exists()
    assert (tmp_path / "full_universe_session_coverage.csv").exists()
