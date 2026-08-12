import pandas as pd

from idx_trade.research_baselines import FoldModelResult
from idx_trade.research_reporting import (
    candidate_counts_by_date,
    drop_reason_summary,
    pooled_oof_summary,
    primary_drop_reason_ledger,
    reliability_bins,
)


def test_candidate_counts_and_drop_ledger_are_explicit():
    features = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "AAA", "BBB"],
            "date": pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"]),
            "universe_history_qualified": [True, True, True, True],
            "universe_primary_liquid": [True, False, True, True],
            "universe_top100": [True, True, True, True],
            "universe_top300": [True, True, True, True],
        }
    )
    labels = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "AAA", "BBB"],
            "signal_date": pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"]),
            "label_status": ["TP_FIRST", "SL_FIRST", "AMBIGUOUS_SAME_BAR", "SL_FIRST"],
        }
    )
    counts = candidate_counts_by_date(features)
    assert counts.loc[0, "primary_liquid"] == 1
    assert counts.loc[1, "primary_liquid"] == 2

    ledger = primary_drop_reason_ledger(features, labels)
    reasons = dict(zip(zip(ledger["ticker"], ledger["date"]), ledger["drop_reason"]))
    assert reasons[("BBB", pd.Timestamp("2024-01-02"))] == "NOT_PRIMARY_LIQUID_UNIVERSE"
    assert reasons[("AAA", pd.Timestamp("2024-01-03"))] == "AMBIGUOUS_SAME_BAR"
    summary = drop_reason_summary(ledger).set_index("drop_reason")
    assert summary.loc["ADMITTED", "rows"] == 2


def _result(fold, probabilities):
    prediction = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "DDD"],
            "date": pd.date_range("2024-01-01", periods=4),
            "target": [0, 1, 0, 1],
            "probability": probabilities,
        }
    )
    return FoldModelResult(
        fold=fold,
        model_name="logistic_compact",
        metrics={"ece": 0.10, "rows": 4.0},
        predictions=prediction,
        calibration_bin_edges=(0.0, 0.25, 0.5, 0.75, 1.0),
    )


def test_reliability_bins_and_pooled_oof_use_only_supplied_predictions():
    f1 = _result("F1", [0.1, 0.8, 0.2, 0.7])
    f2 = _result("F2", [0.2, 0.7, 0.3, 0.8])
    reliability = reliability_bins(f1)
    assert reliability["rows"].sum() == 4
    assert set(reliability["fold"]) == {"F1"}

    pooled = pooled_oof_summary([f1, f2]).iloc[0]
    assert pooled["model_name"] == "logistic_compact"
    assert pooled["rows"] == 8
    assert 0.0 <= pooled["pr_auc"] <= 1.0
    assert pooled["folds"] == "F1,F2"
