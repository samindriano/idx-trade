import pandas as pd

from idx_trade.market_snapshot import (
    build_model_safe_price_panel,
    write_model_safe_price_panel,
)
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
)


def test_model_safe_panel_excludes_official_nonactive_provider_rows(tmp_path):
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
                "state": ["ACTIVE", "NO_TRADE", "ACTIVE"],
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
                "raw_open": [100.0, 100.0, 101.0],
                "raw_high": [101.0, 101.0, 102.0],
                "raw_low": [99.0, 99.0, 100.0],
                "raw_close": [100.0, 100.0, 101.0],
                "raw_volume": [1000.0, 0.0, 1200.0],
            }
        )
    }

    panel = build_model_safe_price_panel(
        prices,
        ["AAAA"],
        master,
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        tradability_anchors=anchors,
        exchange_sessions=pd.DatetimeIndex(sessions),
    )
    assert panel["date"].tolist() == [sessions[0], sessions[2]]
    assert panel["ticker"].tolist() == ["AAAA", "AAAA"]

    summary = write_model_safe_price_panel(
        prices,
        ["AAAA"],
        master,
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        tmp_path / "model_safe_prices.parquet",
        tradability_anchors=anchors,
        exchange_sessions=pd.DatetimeIndex(sessions),
    )
    assert summary["rows"] == 2
    assert summary["tickers"] == 1
    stored = pd.read_parquet(tmp_path / "model_safe_prices.parquet")
    assert len(stored) == 2
