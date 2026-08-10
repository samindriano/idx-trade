from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade import ranking_v3_recency as recency
from idx_trade.research_v2_features import V2_FULL_FEATURE_COLUMNS
from idx_trade.research_v2_models import HGB_XS_MARKET, pointwise_model
from idx_trade.research_v2_validation import fold_by_name


def test_recency_weight_formula_newest_row_age_zero_and_half_life_ratio() -> None:
    weights = recency.recency_weights([252, 504], train_end=504, half_life=252)
    assert weights[1] / weights[0] == pytest.approx(2.0, rel=0.0, abs=1e-12)
    assert float(weights.mean()) == pytest.approx(1.0, rel=0.0, abs=1e-12)


def test_same_session_rows_receive_identical_weight() -> None:
    weights = recency.recency_weights([500, 500, 504], train_end=504, half_life=504)
    assert weights[0] == pytest.approx(weights[1], rel=0.0, abs=0.0)


@pytest.mark.parametrize("half_life", [252, 504])
def test_recency_weights_finite_positive_and_fold_normalized(half_life: int) -> None:
    sessions = np.arange(1, 505, dtype=int)
    weights = recency.recency_weights(sessions, train_end=504, half_life=half_life)
    assert np.isfinite(weights).all()
    assert (weights > 0.0).all()
    assert float(weights.mean()) == pytest.approx(1.0, rel=0.0, abs=1e-12)


def test_recency_weights_reject_row_after_training_end() -> None:
    with pytest.raises(ValueError, match="after the frozen training end"):
        recency.recency_weights([505], train_end=504, half_life=252)


def test_v3_a_uses_exact_v2_feature_order_and_hgb_parameters() -> None:
    assert tuple(recency.candidate_feature_columns(HGB_XS_MARKET)) == tuple(V2_FULL_FEATURE_COLUMNS)
    model = pointwise_model(HGB_XS_MARKET)
    estimator = model.named_steps["model"]
    assert estimator.learning_rate == 0.05
    assert estimator.max_iter == 200
    assert estimator.max_leaf_nodes == 31
    assert estimator.l2_regularization == 1.0
    assert estimator.random_state == 42


def test_discovery_folds_are_exactly_v2_f1_to_f4_and_f5_f6_are_blocked() -> None:
    assert [fold.name for fold in recency.DISCOVERY_FOLDS] == ["V2F1", "V2F2", "V2F3", "V2F4"]
    for name in ["V2F1", "V2F2", "V2F3", "V2F4"]:
        recency.assert_discovery_fold_allowed(fold_by_name(name))
    for name in ["V2F5", "V2F6"]:
        with pytest.raises(PermissionError, match="sealed"):
            recency.assert_discovery_fold_allowed(fold_by_name(name))


def test_fit_candidate_passes_sample_weight_only_to_recency_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeModel:
        def fit(self, frame, target, **kwargs):
            calls.append(kwargs)
            return self

    monkeypatch.setattr(recency, "pointwise_model", lambda candidate: FakeModel())
    train = pd.DataFrame({"signal_session_index": [500, 504], "binary_target": [0, 1]})
    fold = fold_by_name("V2F1")
    recency._fit_candidate(train, fold, recency.V3_A_CONTROL)
    recency._fit_candidate(train, fold, recency.V3_A_HL252)

    assert calls[0] == {}
    assert set(calls[1]) == {"model__sample_weight"}
    weights = np.asarray(calls[1]["model__sample_weight"], dtype=float)
    assert float(weights.mean()) == pytest.approx(1.0, rel=0.0, abs=1e-12)


def test_contract_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    prepared = tmp_path / "prepared.parquet"
    manifest = tmp_path / "manifest.json"
    spec = tmp_path / "spec.md"
    addendum = tmp_path / "addendum.md"
    for path in [prepared, manifest, spec, addendum]:
        path.write_text("not frozen", encoding="utf-8")
    with pytest.raises(RuntimeError, match="prepared cache hash mismatch"):
        recency._assert_contract_files(
            prepared_table_path=prepared,
            prepared_manifest_path=manifest,
            spec_path=spec,
            addendum_path=addendum,
        )


def test_candidate_order_is_frozen_and_tie_prefers_hl504() -> None:
    assert recency.V3_A_CANDIDATES == (
        recency.V3_A_CONTROL,
        recency.V3_A_HL252,
        recency.V3_A_HL504,
    )
    equal = {
        "promoted": True,
        "paired_aggregate": {
            "median_pr_auc_delta_improvement": 0.002,
            "q25_pr_auc_delta_improvement": 0.001,
            "worst_pr_auc_delta_improvement": 0.0,
            "median_q5_minus_q1_change": 0.0,
        },
    }
    selected = recency._select_promoted(
        {
            recency.V3_A_HL252: dict(equal),
            recency.V3_A_HL504: dict(equal),
        }
    )
    assert selected == recency.V3_A_HL504


def test_preregistered_ledger_rows_cannot_fabricate_viewed_results() -> None:
    rows = recency.preregistered_ledger_rows()
    assert len(rows) == 3
    assert [row["candidate_ordinal"] for row in rows] == [1, 2, 3]
    assert all(row["result_status"] == "SPECIFIED_NOT_RUN" for row in rows)
    assert all(row["result_viewed"] is False for row in rows)
    assert all(row["cumulative_candidate_count"] == 0 for row in rows)


def _toy_prediction_block() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for fold_number, fold_name in enumerate(["V2F1", "V2F2", "V2F3", "V2F4"], start=1):
        date = pd.Timestamp("2025-01-01") + pd.Timedelta(days=fold_number)
        for i in range(10):
            rows.append(
                {
                    "candidate": recency.V3_A_CONTROL,
                    "fold": fold_name,
                    "ticker": f"T{i:02d}",
                    "date": date,
                    "signal_session_index": 500 + fold_number,
                    "binary_target": i % 2,
                    "score": float(i),
                }
            )
    return pd.DataFrame(rows)


def test_control_equivalence_accepts_identical_reference_and_rejects_score_change() -> None:
    predictions = _toy_prediction_block()
    metrics_rows = []
    for fold in recency.DISCOVERY_FOLDS:
        block = predictions[predictions["fold"].eq(fold.name)].copy().reset_index(drop=True)
        metrics_rows.append(
            {
                "candidate": recency.V3_A_CONTROL,
                "fold": fold.name,
                **recency.evaluate_v2_scores(block, block["score"].to_numpy(dtype=float)),
            }
        )
    metrics = pd.DataFrame(metrics_rows)
    report = recency.prove_control_equivalence(
        control_metrics=metrics,
        control_predictions=predictions,
        reference_metrics=metrics.copy(),
        reference_predictions=predictions.copy(),
        reference_hashes={"predictions": "a", "summary": "b", "fold_metrics": "c"},
    )
    assert report["status"] == "V3_A_CONTROL_EQUIVALENCE_PASS"

    changed = predictions.copy()
    changed.loc[0, "score"] += 1e-6
    with pytest.raises(RuntimeError, match="score equivalence failed"):
        recency.prove_control_equivalence(
            control_metrics=metrics,
            control_predictions=changed,
            reference_metrics=metrics,
            reference_predictions=predictions,
            reference_hashes={"predictions": "a", "summary": "b", "fold_metrics": "c"},
        )
