import pandas as pd

from idx_trade.history_ladder import (
    DEFAULT_SESSION_HORIZONS,
    DIAGNOSTIC_SESSION_HORIZONS,
    run_history_certification_ladder,
)
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
)


def test_default_history_strategy_uses_large_primary_jumps():
    assert DEFAULT_SESSION_HORIZONS == (43, 126, 504, 1260)
    assert DIAGNOSTIC_SESSION_HORIZONS == (252, 756)


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
    assert (tmp_path / "1_sessions" / "full_universe_gate_summary.json").exists()
    assert (tmp_path / "2_sessions" / "full_universe_gate_summary.json").exists()
    assert (tmp_path / "3_sessions" / "full_universe_gate_summary.json").exists()
    assert not (tmp_path / "5_sessions").exists()


def test_history_ladder_preserves_authoritative_non_common_scope_exclusion(tmp_path):
    sessions = pd.to_datetime(["2026-06-02", "2026-06-03"])
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
                "ticker": ["AAAA", "AAAA", "PREF", "PREF"],
                "market": ["REGULAR"] * 4,
                "as_of_date": [
                    "2026-06-02",
                    "2026-06-03",
                    "2026-06-02",
                    "2026-06-03",
                ],
                "state": ["ACTIVE", "ACTIVE", "NO_TRADE", "NO_TRADE"],
                "source": ["IDX_STOCK_SUMMARY"] * 4,
                "source_ref": ["idx://2", "idx://3", "idx://2", "idx://3"],
                "evidence_type": [
                    "IDX_STOCK_SUMMARY_REGULAR_EXECUTION_OBSERVATION",
                ]
                * 4,
            }
        )
    )
    prices = {
        "AAAA": pd.DataFrame(
            {
                "date": sessions,
                "raw_open": [100.0, 100.0],
                "raw_high": [101.0, 101.0],
                "raw_low": [99.0, 99.0],
                "raw_close": [100.0, 100.0],
                "raw_volume": [1000.0, 1000.0],
            }
        )
    }
    exclusions = pd.DataFrame(
        {
            "ticker": ["PREF"],
            "reason": ["NON_COMMON_SHARE"],
            "source": ["KSEI_REGISTERED_SECURITIES"],
            "source_ref": ["ksei://PREF"],
            "security_type": ["Saham Preference"],
        }
    )

    result = run_history_certification_ladder(
        pd.DatetimeIndex(sessions),
        prices,
        master,
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        tradability_anchors=anchors,
        split_history_verified={"AAAA": True},
        price_semantics_verified={"AAAA": True},
        security_scope_exclusions=exclusions,
        session_horizons=[2],
        output_dir=tmp_path,
    )

    row = result["ladder"][0]
    assert row["passed"] is True
    assert row["discovered_tickers_before_scope"] == 2
    assert row["scope_excluded_tickers"] == ["PREF"]
    assert row["required_tickers"] == 1
    saved_exclusions = pd.read_csv(
        tmp_path / "2_sessions" / "full_universe_scope_exclusions.csv"
    )
    assert saved_exclusions.loc[0, "ticker"] == "PREF"
