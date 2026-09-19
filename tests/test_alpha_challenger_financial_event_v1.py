from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.alpha_challenger_financial_event_v1 import build_financial_event_features


def _frame() -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=4, freq="D")
    return pd.DataFrame(
        {
            "ticker": ["BBCA"] * 4,
            "date": dates,
            "bundle_status": ["SELECTED"] * 4,
            "bundle_reporting_version_id": ["v1", "v1", "v2", "v2"],
            "bundle_reporting_attachment_sha256": ["a", "a", "b", "b"],
            "bundle_reporting_knowledge_at_utc": ["2026-01-01T01:00:00Z"] * 4,
            "leverage_liabilities_to_assets__value": [0.50, 0.50, 0.40, 0.40],
            "liquidity_cash_to_assets__value": [0.10, 0.10, 0.15, 0.15],
            "margin_net_income_to_revenue__value": [0.05, 0.05, 0.07, 0.07],
            "core3_available": True,
            "same_bundle_violation": False,
            "selected_knowledge_time_violation": False,
            "selected_bundle_provenance_complete": True,
        }
    )


def test_only_distinct_reporting_state_creates_event_and_delta() -> None:
    result = build_financial_event_features(_frame())
    assert result["financial_update_event"].tolist() == [0.0, 0.0, 1.0, 0.0]
    assert result.loc[2, "delta_leverage"] == pytest.approx(-0.10)
    assert result.loc[2, "delta_liquidity"] == pytest.approx(0.05)
    assert result.loc[2, "delta_margin"] == pytest.approx(0.02)
    assert result.loc[2, "quality_delta"] == pytest.approx(0.17)


def test_future_state_does_not_change_prior_feature_rows() -> None:
    base = build_financial_event_features(_frame())
    extended = _frame().copy()
    extra = _frame().iloc[[-1]].copy()
    extra["date"] = pd.Timestamp("2026-01-05")
    extra["bundle_reporting_version_id"] = "v3"
    extra["bundle_reporting_attachment_sha256"] = "c"
    extra["leverage_liabilities_to_assets__value"] = 0.30
    extended = pd.concat([extended, extra], ignore_index=True)
    later = build_financial_event_features(extended)
    pd.testing.assert_frame_equal(base, later.iloc[: len(base)].reset_index(drop=True))


def test_pit_violation_and_outcome_columns_fail_closed() -> None:
    invalid = _frame()
    invalid.loc[0, "same_bundle_violation"] = True
    with pytest.raises(ValueError, match="PIT violation"):
        build_financial_event_features(invalid)
    invalid = _frame()
    invalid["realized_consensus"] = 0.0
    with pytest.raises(ValueError, match="outcome-like"):
        build_financial_event_features(invalid)
