import pandas as pd
import pytest

from idx_trade.research_features import (
    BASELINE_FEATURE_COLUMNS,
    assert_no_open_dependency,
    build_baseline_features,
    filter_panel_to_listing_domain,
    strict_boolean_series,
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


def _master(listed_from="2024-01-02", listed_to=None):
    return pd.DataFrame(
        {
            "ticker": ["AAAA"],
            "listed_from": [listed_from],
            "listed_to": [listed_to],
        }
    )


def test_listing_domain_excludes_prelisting_and_postdelisting_before_features():
    calendar = pd.bdate_range("2023-12-28", periods=5)
    panel = _panel(periods=5)
    panel["ticker"] = "AAAA"
    panel["date"] = pd.bdate_range("2023-12-28", periods=5)
    master = _master("2024-01-01", "2024-01-04")
    filtered, report = filter_panel_to_listing_domain(panel, master, calendar)
    assert filtered["date"].tolist() == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")]
    assert report["rows_removed"] == 2
    features = build_baseline_features(panel, calendar, security_master=master)
    assert features["date"].tolist() == filtered["date"].tolist()


@pytest.mark.parametrize("value", ["not-a-date", "2024-02-30", float("inf")])
def test_malformed_listing_date_fails_closed(value):
    with pytest.raises(ValueError, match="listed_to.*malformed"):
        filter_panel_to_listing_domain(_panel(periods=2), _master("2024-01-02", value), pd.bdate_range("2024-01-02", periods=2))


def test_conflicting_duplicate_listing_or_panel_identity_fails_closed():
    master = pd.concat([_master(), _master()], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate security-master"):
        filter_panel_to_listing_domain(_panel(periods=2), master, pd.bdate_range("2024-01-02", periods=2))
    duplicate_panel = pd.concat([_panel(periods=2), _panel(periods=2)], ignore_index=True)
    duplicate_panel["ticker"] = "AAAA"
    with pytest.raises(ValueError, match="duplicate panel"):
        filter_panel_to_listing_domain(duplicate_panel, _master(), pd.bdate_range("2024-01-02", periods=2))


def test_koci_like_rows_cannot_inflate_observed_session_count_or_context():
    calendar = pd.bdate_range("2024-01-02", periods=25)
    panel = _panel(periods=25)
    panel["ticker"] = "KOCI"
    master = pd.DataFrame({"ticker": ["KOCI"], "listed_from": [calendar[5]], "listed_to": [None]})
    features = build_baseline_features(panel, calendar, security_master=master)
    assert len(features) == 20
    assert features["observed_session_count"].tolist() == list(range(1, 21))


def test_strict_boolean_rejects_truthy_noncanonical_values():
    assert strict_boolean_series(pd.Series([True, "False", "true"]), field_name="is_complete").tolist() == [True, False, True]
    with pytest.raises(ValueError, match="non-canonical boolean"):
        strict_boolean_series(pd.Series(["yes"]), field_name="is_complete")


def test_listing_filter_is_deterministic_under_input_order_changes():
    calendar = pd.bdate_range("2024-01-02", periods=10)
    panel = _panel(tickers=("AAAA", "BBBB"), periods=10)
    master = pd.DataFrame({"ticker": ["AAAA", "BBBB"], "listed_from": [calendar[1], calendar[2]], "listed_to": [None, None]})
    left, _ = filter_panel_to_listing_domain(panel, master, calendar)
    right, _ = filter_panel_to_listing_domain(panel.sample(frac=1.0, random_state=7), master.iloc[::-1], calendar[::-1])
    pd.testing.assert_frame_equal(left.reset_index(drop=True), right.reset_index(drop=True))
