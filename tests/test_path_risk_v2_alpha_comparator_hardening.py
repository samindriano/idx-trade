from __future__ import annotations

import hashlib
import inspect
import json

import numpy as np
import pandas as pd
import pytest

from idx_trade import path_risk_v2_discovery_run as run
from idx_trade.ranking_v3_structure_lite import V3_B_FEATURE_COLUMNS


def _row(
    row_id: str,
    session: int,
    status: str,
    *,
    score: float | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "row_id": row_id,
        "ticker": f"T{session:04d}",
        "date": pd.Timestamp("2026-01-02") + pd.Timedelta(days=session),
        "signal_session_index": session,
        "label_status": status,
        "first_barrier_date": pd.Timestamp("2026-01-10")
        if status in {"TP_FIRST", "SL_FIRST", "AMBIGUOUS_SAME_BAR"}
        else pd.NaT,
        "adverse_excursion_r": 1.0 if status in {"SL_FIRST", "AMBIGUOUS_SAME_BAR"} else 0.1,
        "stop_touch_h10": int(status in {"SL_FIRST", "AMBIGUOUS_SAME_BAR"}),
        "synthetic_alpha_score": float(session if score is None else score),
        "future_outcome_sentinel": float(10_000 + session),
    }
    row.update(
        {
            column: float((session + offset) % 17) / 17.0
            for offset, column in enumerate(run.PATH_RISK_V2_FEATURE_COLUMNS)
        }
    )
    return row


def _fold_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _row("train-first", 1, "TP_FIRST"),
            _row("train-last", 504, "SL_FIRST"),
            _row("train-ambiguous", 250, "AMBIGUOUS_SAME_BAR"),
            _row("train-none", 251, "NO_BARRIER_HIT"),
            _row("gap-first", 505, "SL_FIRST"),
            _row("gap-last", 524, "TP_FIRST"),
            _row("validation-first", 525, "AMBIGUOUS_SAME_BAR"),
            _row("validation-none", 526, "NO_BARRIER_HIT"),
            _row("validation-last", 624, "TP_FIRST"),
            _row("sealed", 985, "SL_FIRST"),
        ]
    )


class _SpyAlphaModel:
    def __init__(self, registry: list["_SpyAlphaModel"]) -> None:
        self.fit_frame: pd.DataFrame | None = None
        self.fit_target: np.ndarray | None = None
        registry.append(self)

    def fit(self, frame: pd.DataFrame, target: np.ndarray) -> "_SpyAlphaModel":
        self.fit_frame = frame.copy()
        self.fit_target = np.asarray(target, dtype=int).copy()
        return self


class _SpyMapping:
    def __init__(self, registry: list["_SpyMapping"], **kwargs: object) -> None:
        self.kwargs = kwargs
        self.fit_scores: np.ndarray | None = None
        self.fit_target: np.ndarray | None = None
        registry.append(self)

    def fit(self, scores: np.ndarray, target: np.ndarray) -> "_SpyMapping":
        self.fit_scores = np.asarray(scores, dtype=float).copy()
        self.fit_target = np.asarray(target, dtype=int).copy()
        return self

    def predict_proba(self, scores: np.ndarray) -> np.ndarray:
        probability = 1.0 / (1.0 + np.exp(-np.asarray(scores, dtype=float)[:, 0] / 100.0))
        return np.column_stack([1.0 - probability, probability])


def _install_spies(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    models: list[_SpyAlphaModel] = []
    mappings: list[_SpyMapping] = []
    score_calls: list[list[str]] = []

    def model_factory() -> _SpyAlphaModel:
        return _SpyAlphaModel(models)

    def score_model(model: _SpyAlphaModel, frame: pd.DataFrame) -> np.ndarray:
        del model
        score_calls.append(frame["row_id"].tolist())
        return frame["synthetic_alpha_score"].to_numpy(dtype=float)

    def mapping_factory(**kwargs: object) -> _SpyMapping:
        return _SpyMapping(mappings, **kwargs)

    monkeypatch.setattr(run, "_structure_model", model_factory)
    monkeypatch.setattr(run, "pointwise_raw_score", score_model)
    monkeypatch.setattr(run, "LogisticRegression", mapping_factory)
    return {"models": models, "mappings": mappings, "score_calls": score_calls}


def test_alpha_comparator_uses_exact_fold_rows_and_excludes_gap_and_sealed_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _fold_frame()
    fold = run._folds()[0]
    train, validation = run._split(table, fold)

    assert set(train["row_id"]) == {
        "train-first",
        "train-last",
        "train-ambiguous",
        "train-none",
    }
    assert set(validation["row_id"]) == {
        "validation-first",
        "validation-none",
        "validation-last",
    }
    assert not set(train["signal_session_index"]).intersection(range(505, 525))
    assert not set(validation["signal_session_index"]).intersection(range(505, 525))
    assert 985 not in set(train["signal_session_index"]) | set(validation["signal_session_index"])

    spies = _install_spies(monkeypatch)
    probability, bundle = run._fit_alpha_only_baseline(train, validation)
    model = spies["models"][0]
    mapping = spies["mappings"][0]

    assert list(model.fit_frame["row_id"]) == ["train-first", "train-last"]
    np.testing.assert_array_equal(model.fit_target, [1, 0])
    assert spies["score_calls"] == [
        ["train-first", "train-last", "train-ambiguous", "train-none"],
        ["validation-first", "validation-none", "validation-last"],
    ]
    np.testing.assert_allclose(
        mapping.fit_scores,
        train["synthetic_alpha_score"].to_numpy(dtype=float)[:, None],
        rtol=0.0,
        atol=0.0,
    )
    np.testing.assert_array_equal(mapping.fit_target, train["stop_touch_h10"].to_numpy(dtype=int))
    assert len(probability) == len(validation)
    assert bundle["alpha_model"] is model
    assert bundle["stop_mapping"] is mapping


def test_alpha_mapping_is_training_only_and_validation_outcome_mutation_is_inert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _fold_frame()
    train, validation = run._split(table, run._folds()[0])
    spies = _install_spies(monkeypatch)
    baseline_probability, baseline_bundle = run._fit_alpha_only_baseline(train, validation)

    mutated = validation.copy()
    mutated["label_status"] = "SL_FIRST"
    mutated["stop_touch_h10"] = 1
    mutated["first_barrier_date"] = pd.Timestamp("2099-12-31")
    mutated["adverse_excursion_r"] = 999.0
    mutated["future_outcome_sentinel"] = -999.0
    mutated_probability, mutated_bundle = run._fit_alpha_only_baseline(train, mutated)

    baseline_model = baseline_bundle["alpha_model"]
    mutated_model = mutated_bundle["alpha_model"]
    baseline_mapping = baseline_bundle["stop_mapping"]
    mutated_mapping = mutated_bundle["stop_mapping"]
    assert list(baseline_model.fit_frame["row_id"]) == list(mutated_model.fit_frame["row_id"])
    np.testing.assert_array_equal(baseline_model.fit_target, mutated_model.fit_target)
    np.testing.assert_allclose(
        baseline_mapping.fit_scores,
        mutated_mapping.fit_scores,
        rtol=0.0,
        atol=0.0,
    )
    np.testing.assert_array_equal(baseline_mapping.fit_target, mutated_mapping.fit_target)
    np.testing.assert_allclose(baseline_probability, mutated_probability, rtol=0.0, atol=0.0)
    assert spies["score_calls"][-1] == ["validation-first", "validation-none", "validation-last"]


def test_alpha_comparator_scores_unresolved_validation_rows_without_their_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    train = pd.DataFrame(
        [
            _row("train-tp", 1, "TP_FIRST"),
            _row("train-sl", 2, "SL_FIRST"),
            _row("train-none", 3, "NO_BARRIER_HIT"),
            _row("train-ambiguous", 4, "AMBIGUOUS_SAME_BAR"),
        ]
    )
    validation = pd.DataFrame(
        [
            _row("validation-ambiguous", 525, "AMBIGUOUS_SAME_BAR"),
            _row("validation-none", 526, "NO_BARRIER_HIT"),
        ]
    )
    spies = _install_spies(monkeypatch)

    probability, _ = run._fit_alpha_only_baseline(train, validation)

    assert len(probability) == 2
    assert np.isfinite(probability).all()
    assert spies["score_calls"][-1] == ["validation-ambiguous", "validation-none"]


def test_alpha_comparator_fails_closed_when_resolved_training_is_one_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validation = pd.DataFrame(
        [
            _row("validation-stop", 525, "SL_FIRST"),
            _row("validation-safe", 526, "TP_FIRST"),
        ]
    )
    for statuses in (("TP_FIRST", "AMBIGUOUS_SAME_BAR"), ("NO_BARRIER_HIT", "SL_FIRST")):
        train = pd.DataFrame(
            [_row(f"train-{index}", index + 1, status) for index, status in enumerate(statuses)]
        )
        with pytest.raises(RuntimeError, match="requires resolved TP/SL training rows"):
            run._fit_alpha_only_baseline(train, validation)


def test_alpha_comparator_has_one_fresh_model_per_fold_and_never_loads_refit_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_train, first_validation = run._split(_fold_frame(), run._folds()[0])
    second_train = pd.DataFrame(
        [
            _row("second-tp", 1, "TP_FIRST"),
            _row("second-sl", 624, "SL_FIRST"),
            _row("second-none", 300, "NO_BARRIER_HIT"),
        ]
    )
    second_validation = pd.DataFrame(
        [
            _row("second-validation-stop", 645, "SL_FIRST"),
            _row("second-validation-safe", 744, "TP_FIRST"),
        ]
    )
    spies = _install_spies(monkeypatch)
    monkeypatch.setattr(
        run.joblib,
        "load",
        lambda *_args, **_kwargs: pytest.fail("alpha comparator loaded an all-history artifact"),
    )

    run._fit_alpha_only_baseline(first_train, first_validation)
    run._fit_alpha_only_baseline(second_train, second_validation)

    assert len(spies["models"]) == 2
    assert spies["models"][0] is not spies["models"][1]
    assert list(spies["models"][0].fit_frame["row_id"]) == ["train-first", "train-last"]
    assert list(spies["models"][1].fit_frame["row_id"]) == ["second-tp", "second-sl"]
    assert "joblib.load" not in inspect.getsource(run._fit_alpha_only_baseline)


def test_alpha_comparator_is_bound_to_exact_v3b_causal_feature_order_and_no_hidden_drift() -> None:
    assert tuple(run.PATH_RISK_V2_FEATURE_COLUMNS) == tuple(V3_B_FEATURE_COLUMNS)
    assert len(run.PATH_RISK_V2_FEATURE_COLUMNS) == 33
    order_payload = json.dumps(
        list(run.PATH_RISK_V2_FEATURE_COLUMNS), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    assert hashlib.sha256(order_payload).hexdigest() == run.PATH_RISK_V2_FEATURE_ORDER_SHA256

    model = run._structure_model()
    preprocess = model.named_steps["preprocess"]
    selected = tuple(preprocess.transformers[0][2])
    assert selected == tuple(V3_B_FEATURE_COLUMNS)
    assert preprocess.remainder == "drop"
    forbidden_tokens = ("open", "label", "target", "status", "outcome", "adverse", "ticker", "date")
    assert not any(token in column.lower() for column in selected for token in forbidden_tokens)


def test_alpha_model_scores_are_invariant_to_metadata_and_hidden_columns() -> None:
    train = pd.DataFrame(
        [_row(f"train-{index}", index, "TP_FIRST" if index % 2 else "SL_FIRST") for index in range(1, 21)]
    )
    target = train["label_status"].eq("TP_FIRST").astype(int).to_numpy()
    model = run._structure_model().fit(train, target)
    validation = pd.DataFrame(
        [_row(f"validation-{index}", 500 + index, "NO_BARRIER_HIT") for index in range(1, 7)]
    )
    baseline_score = run.pointwise_raw_score(model, validation)

    mutated = validation.copy()
    mutated["label_status"] = "SL_FIRST"
    mutated["first_barrier_date"] = pd.Timestamp("2099-12-31")
    mutated["adverse_excursion_r"] = 999.0
    mutated["stop_touch_h10"] = 1
    mutated["future_outcome_sentinel"] = -999.0
    mutated["synthetic_alpha_score"] = -999.0
    mutated["final_v3b_alpha_probability"] = 999.0
    mutated_score = run.pointwise_raw_score(model, mutated)

    np.testing.assert_allclose(baseline_score, mutated_score, rtol=0.0, atol=0.0)


def test_alpha_comparator_keeps_only_f1_to_f4_fold_boundaries() -> None:
    actual = [
        (
            fold.name,
            fold.train_start,
            fold.train_end,
            fold.gap_start,
            fold.gap_end,
            fold.validation_start,
            fold.validation_end,
        )
        for fold in run._folds()
    ]
    assert actual == [
        ("V2F1", 1, 504, 505, 524, 525, 624),
        ("V2F2", 1, 624, 625, 644, 645, 744),
        ("V2F3", 1, 744, 745, 764, 765, 864),
        ("V2F4", 1, 864, 865, 884, 885, 984),
    ]
    assert max(fold.validation_end for fold in run._folds()) == 984
    assert all(fold.gap_start > fold.train_end for fold in run._folds())
    assert all(fold.validation_start > fold.gap_end for fold in run._folds())
