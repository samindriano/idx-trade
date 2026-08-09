from __future__ import annotations

import numpy as np
import pandas as pd

from idx_trade.research_v2_features import (
    V2_FULL_FEATURE_COLUMNS,
    V2_TIME_PROXY_EXCLUSIONS,
    V2_XS_FEATURE_COLUMNS,
    V2_XS_SOURCE_FEATURES,
    build_v2_feature_table,
)


def _toy_features() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for day_offset in range(2):
        date = pd.Timestamp("2026-01-02") + pd.Timedelta(days=day_offset)
        for i, ticker in enumerate(("AAA", "BBB", "CCC", "ZZZ"), start=1):
            primary = ticker != "ZZZ"
            base = float(i + day_offset)
            row: dict[str, object] = {
                "ticker": ticker,
                "date": date,
                "universe_primary_liquid": primary,
                "observed_session_count": 100 + i,
                "security_age_sessions_exact": 50 + i,
            }
            for j, feature in enumerate(V2_XS_SOURCE_FEATURES):
                row[feature] = base + j / 10.0
            rows.append(row)
    return pd.DataFrame(rows)


def test_v2_cross_section_uses_primary_universe_only() -> None:
    result = build_v2_feature_table(_toy_features())
    day = result[result["date"].eq(pd.Timestamp("2026-01-02"))].set_index("ticker")
    feature = "xs_rank_close_return_5"
    assert np.isclose(day.loc["AAA", feature], 1.0 / 3.0)
    assert np.isclose(day.loc["BBB", feature], 2.0 / 3.0)
    assert np.isclose(day.loc["CCC", feature], 1.0)
    assert pd.isna(day.loc["ZZZ", feature])
    assert (day.loc[["AAA", "BBB", "CCC"], "market_primary_liquid_count"] == 3.0).all()


def test_v2_market_relative_feature_uses_same_date_market_median() -> None:
    result = build_v2_feature_table(_toy_features())
    day = result[result["date"].eq(pd.Timestamp("2026-01-02"))].set_index("ticker")
    # Primary close_return_5 values are 1, 2, 3; market median is 2.
    assert np.isclose(day.loc["AAA", "market_median_close_return_5"], 2.0)
    assert np.isclose(day.loc["AAA", "market_relative_close_return_5"], -1.0)
    assert np.isclose(day.loc["CCC", "market_relative_close_return_5"], 1.0)


def test_v2_core_explicitly_excludes_time_proxies_and_open() -> None:
    assert not set(V2_TIME_PROXY_EXCLUSIONS).intersection(V2_XS_FEATURE_COLUMNS)
    assert not set(V2_TIME_PROXY_EXCLUSIONS).intersection(V2_FULL_FEATURE_COLUMNS)
    assert all("open" not in name.lower() for name in V2_FULL_FEATURE_COLUMNS)
    assert len(V2_XS_FEATURE_COLUMNS) == 10
    assert len(V2_FULL_FEATURE_COLUMNS) == 25
