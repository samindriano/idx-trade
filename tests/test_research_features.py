import pandas as pd

from idx_trade.research_features import (
    BASELINE_FEATURE_COLUMNS,
    assert_no_open_dependency,
    build_baseline_features,
)


def _panel(tickers=("AAA",), periods=80):
    dates = pd.bdate_range("2024-01-02", periods=periods)
    frames = []
    for i, ticker in enumerate(tickers):
        base = 100.0 + i * 10.0
        frames.append(
            pd.DataFrame(
                {
                    "ticker": ticker,
                    "date": dates,
                    "high": [base + 2 + j * 0.1 for j in range(periods)],
                    "low": [base + j * 0.1 for j in range(periods)],
                    "close": [base + 1 + j * 0.1 for j in range(periods)],
                    "volume": [1000.0 + j for j in range(periods)],
                    "regular_market_value": [2_000_000_000.0 + i * 1_000_000_000.0] * periods,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def test_future_rows_do_not_change_past_features():
    panel = _panel(periods=80)
    calendar = pd.bdate_range("2024-01-02", periods=80)
    before = build_baseline_features(panel, calendar)
    mutated = panel.copy()
    cutoff = calendar[59]
    mutated.loc[mutated["date"] > cutoff, ["high", "low", "close", "volume"]] *= 10.0
    after = build_baseline_features(mutated, calendar)
    cols = ["date", *BASELINE_FEATURE_COLUMNS, "median_regular_value_60", "universe_primary_liquid"]
    left = before[before["date"] <= cutoff][cols].reset_index(drop=True)
    right = after[after["date"] <= cutoff][cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right)


def test_primary_liquidity_rule_uses_exact_official_60_session_window():
    panel = _panel(periods=80)
    calendar = pd.bdate_range("2024-01-02", periods=80)
    features = build_baseline_features(panel, calendar)
    assert not features.loc[18, "universe_primary_liquid"]
    assert features.loc[19, "universe_primary_liquid"]
    assert features.loc[19, "liquidity_active_observations_60"] == 20
    assert features.loc[79, "liquidity_active_observations_60"] == 60


def test_causal_top_n_rank_is_recomputed_by_date():
    panel = _panel(tickers=("AAA", "BBB"), periods=25)
    calendar = pd.bdate_range("2024-01-02", periods=25)
    features = build_baseline_features(panel, calendar)
    day = calendar[-1]
    rows = features[features["date"].eq(day)].set_index("ticker")
    assert rows.loc["BBB", "causal_liquidity_rank"] == 1.0
    assert rows.loc["AAA", "causal_liquidity_rank"] == 2.0
    assert rows["universe_top100"].all()


def test_pre_window_listing_age_is_missing_and_explicitly_left_censored():
    panel = _panel(periods=30)
    calendar = pd.bdate_range("2024-01-02", periods=30)
    features = build_baseline_features(panel, calendar, listed_from={"AAA": "2000-01-01"})
    assert features["security_age_left_censored"].all()
    assert features["security_age_sessions_exact"].isna().all()


def test_in_window_listing_has_exact_official_session_age():
    panel = _panel(periods=30)
    calendar = pd.bdate_range("2024-01-02", periods=30)
    listed = calendar[4]
    features = build_baseline_features(panel, calendar, listed_from={"AAA": listed})
    assert not features["security_age_left_censored"].any()
    assert pd.isna(features.iloc[3]["security_age_sessions_exact"])
    assert features.iloc[4]["security_age_sessions_exact"] == 1.0
    assert features.iloc[9]["security_age_sessions_exact"] == 6.0


def test_primary_feature_registry_has_no_open_dependency():
    assert_no_open_dependency(BASELINE_FEATURE_COLUMNS)
