import pandas as pd

from idx_trade.history_ladder import run_history_certification_ladder
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
)


def test_history_ladder_finds_longest_passing_trailing_window(tmp_path):
    sessions = pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03"])
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
                "ticker": ["AAAA", "AAAA"],
                "market": ["REGULAR", "REGULAR"],
                "as_of_date": ["2026-06-02", "2026-06-03"],
                "state": ["ACTIVE", "ACTIVE"],
                "source": ["IDX_STOCK_SUMMARY", "IDX_STOCK_SUMMARY"],
                "source_ref": ["idx://2", "idx://3"],
                "evidence_type": [
                    "IDX_STOCK_SUMMARY_REGULAR_EXECUTION_OBSERVATION",
                    "IDX_STOCK_SUMMARY_REGULAR_EXECUTION_OBSERVATION",
                ],
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
                "raw_volume": [1000.0] * 3,
            }
        )
    }

    result = run_history_certification_ladder(
        pd.DatetimeIndex(sessions),
        prices,
        master,
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        tradability_anchors=anchors,
        split_history_verified={"AAAA": True},
        price_semantics_verified={"AAAA": True},
        session_horizons=[1, 2, 3, 5],
        output_dir=tmp_path,
    )

    ladder = {row["requested_sessions"]: row for row in result["ladder"]}
    assert ladder[1]["passed"] is True
    assert ladder[2]["passed"] is True
    assert ladder[3]["passed"] is False
    assert ladder[3]["unknown_sessions"] == 1
    assert ladder[5]["status"] == "INSUFFICIENT_CALENDAR_HISTORY"
    assert result["summary"]["longest_passing_window"]["sessions"] == 2
    assert result["summary"]["longest_passing_window"]["window_start"] == "2026-06-02"
    assert (tmp_path / "history_certification_ladder.csv").exists()
    assert (tmp_path / "history_certification_summary.json").exists()
