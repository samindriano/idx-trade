from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import idx_trade.ranking_v3_true_ranking_erratum as v3e
from idx_trade.research_v2_models import HGB_XS_MARKET, candidate_feature_columns


def _rows() -> pd.DataFrame:
    records = [
        ("2024-01-02", "BBB", 0),
        ("2024-01-02", "AAA", 1),
        ("2024-01-03", "AAA", 0),
        ("2024-01-03", "BBB", 0),
        ("2024-01-04", "AAA", 1),
        ("2024-01-04", "BBB", 1),
    ]
    data = pd.DataFrame(records, columns=["date", "ticker", "binary_target"])
    for index, column in enumerate(v3e.V3_E_FEATURE_COLUMNS):
        data[column] = np.arange(len(data), dtype=float) + index
    return data


def test_candidate_identity_and_feature_contract() -> None:
    assert v3e.V3_E_CONTROL.endswith("010")
    assert v3e.V3_E_LAMBDAMART.endswith("011")
    assert v3e.V3_E_CANDIDATES == (v3e.V3_E_CONTROL, v3e.V3_E_LAMBDAMART)
    assert tuple(v3e.V3_E_FEATURE_COLUMNS) == tuple(candidate_feature_columns(HGB_XS_MARKET))
    assert len(v3e.V3_E_FEATURE_COLUMNS) == 25
    assert not any(
        token in column.lower()
        for column in v3e.V3_E_FEATURE_COLUMNS
        for token in ("structure_", "sector_", "regime_")
    )


def test_xgboost_version_is_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v3e.base.xgb, "__version__", "0.0.0")
    with pytest.raises(RuntimeError, match="xgboost==3.2.0"):
        v3e._assert_xgboost_version()


def test_lambdamart_parameter_contract() -> None:
    assert v3e._assert_xgboost_version() == "3.2.0"
    ranker = v3e.build_lambdamart()
    params = ranker.get_params()
    expected = {
        "objective": "rank:ndcg",
        "n_estimators": 200,
        "learning_rate": 0.05,
        "max_depth": 5,
        "min_child_weight": 1.0,
        "reg_lambda": 1.0,
        "reg_alpha": 0.0,
        "gamma": 0.0,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "tree_method": "hist",
        "random_state": 42,
        "n_jobs": 1,
        "verbosity": 0,
        "ndcg_exp_gain": True,
        "lambdarank_pair_method": "mean",
        "lambdarank_num_pair_per_sample": 8,
        "lambdarank_normalization": True,
    }
    for key, value in expected.items():
        assert params[key] == value


def test_imputer_matches_v2_missing_semantics() -> None:
    imputer = v3e.build_imputer()
    assert imputer.strategy == "median"
    assert imputer.add_indicator is True
    assert imputer.keep_empty_features is True
    assert not hasattr(imputer, "with_mean")


def test_query_grouping_is_exact_date_and_deterministic() -> None:
    data, qid, diagnostics = v3e.build_query_training_frame(_rows())
    assert list(data["ticker"]) == ["AAA", "BBB", "AAA", "BBB", "AAA", "BBB"]
    assert list(data["date"]) == [
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
        pd.Timestamp("2024-01-03"),
        pd.Timestamp("2024-01-04"),
        pd.Timestamp("2024-01-04"),
    ]
    assert qid.tolist() == [0, 0, 1, 1, 2, 2]
    assert np.all(np.diff(qid) >= 0)
    assert diagnostics["query_dates"] == 3
    assert diagnostics["mixed_label_queries"] == 1
    assert diagnostics["all_zero_queries"] == 1
    assert diagnostics["all_one_queries"] == 1
    assert diagnostics["rows"] == len(_rows())
    assert diagnostics["rows_dropped"] == 0


def test_all_zero_and_all_one_query_rows_are_preserved() -> None:
    original = _rows()
    data, _, diagnostics = v3e.build_query_training_frame(original)
    assert len(data) == len(original)
    assert diagnostics["all_zero_queries"] == 1
    assert diagnostics["all_one_queries"] == 1
    assert diagnostics["positive_rows"] == 3
    assert diagnostics["negative_rows"] == 3


def test_query_builder_requires_both_classes_overall() -> None:
    data = _rows()
    data["binary_target"] = 0
    with pytest.raises(RuntimeError, match="both target classes"):
        v3e.build_query_training_frame(data)


def test_v3_e_hard_blocks_f5_f6() -> None:
    for name in ("V2F5", "V2F6"):
        with pytest.raises(PermissionError):
            v3e.assert_discovery_fold_allowed(name)
    for name in ("V2F1", "V2F2", "V2F3", "V2F4"):
        v3e.assert_discovery_fold_allowed(name)


def test_discovery_read_physically_filters_at_984(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "prepared.parquet"
    path.write_bytes(b"placeholder")
    captured: dict[str, object] = {}

    raw = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": [pd.Timestamp("2024-01-02")],
            "signal_session_index": [984],
            "binary_target": [1],
        }
    )

    def fake_read_parquet(file_path, *, filters):
        captured["path"] = file_path
        captured["filters"] = filters
        return raw.copy()

    monkeypatch.setattr(v3e.base.pd, "read_parquet", fake_read_parquet)
    monkeypatch.setattr(v3e.base, "_normalize_candidate_table", lambda frame, candidate: frame)

    result = v3e.read_discovery_table(path)
    assert captured["filters"] == [("signal_session_index", "<=", 984)]
    assert int(result["signal_session_index"].max()) == 984


def test_discovery_read_rejects_materialized_sealed_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "prepared.parquet"
    path.write_bytes(b"placeholder")
    raw = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": [pd.Timestamp("2024-01-02")],
            "signal_session_index": [985],
            "binary_target": [1],
        }
    )
    monkeypatch.setattr(v3e.base.pd, "read_parquet", lambda *args, **kwargs: raw.copy())
    monkeypatch.setattr(v3e.base, "_normalize_candidate_table", lambda frame, candidate: frame)
    with pytest.raises(RuntimeError, match="sealed sessions"):
        v3e.read_discovery_table(path)


def _predictions(scores: list[float], candidate: str) -> pd.DataFrame:
    rows = []
    for fold in ("V2F1", "V2F2", "V2F3", "V2F4"):
        for date_offset in range(2):
            date = pd.Timestamp("2024-01-02") + pd.Timedelta(days=date_offset)
            for i in range(10):
                rows.append(
                    {
                        "candidate": candidate,
                        "fold": fold,
                        "ticker": f"T{i:02d}",
                        "date": date,
                        "signal_session_index": 500 + date_offset,
                        "binary_target": int(i >= 5),
                        "score": scores[i],
                    }
                )
    return pd.DataFrame(rows)


def test_score_diversity_diagnostics_are_deterministic() -> None:
    frame = _predictions([float(i) for i in range(10)], v3e.V3_E_LAMBDAMART)
    result = v3e._score_diversity(frame)
    assert list(result["fold"]) == ["V2F1", "V2F2", "V2F3", "V2F4"]
    assert (result["global_unique_scores"] == 10).all()
    assert (result["unique_score_fraction_median"] == 1.0).all()
    assert (result["all_tied_dates"] == 0).all()


def test_top_decile_overlap_identical_scores_is_one() -> None:
    scores = [float(i) for i in range(10)]
    control = _predictions(scores, v3e.V3_E_CONTROL)
    candidate = _predictions(scores, v3e.V3_E_LAMBDAMART)
    result = v3e._top_decile_overlap(control, candidate)
    assert np.allclose(result["top_decile_jaccard"], 1.0)
    assert (result["top_decile_entrants"] == 0).all()
    assert (result["top_decile_exits"] == 0).all()


def test_top_decile_overlap_detects_changed_names() -> None:
    control = _predictions([float(i) for i in range(10)], v3e.V3_E_CONTROL)
    candidate = _predictions(
        [10.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 0.0],
        v3e.V3_E_LAMBDAMART,
    )
    result = v3e._top_decile_overlap(control, candidate)
    assert (result["top_decile_jaccard"] < 1.0).all()
    assert (result["top_decile_entrants"] > 0).all()
    assert (result["top_decile_exits"] > 0).all()


def test_preregistered_ledger_does_not_fabricate_results() -> None:
    rows = v3e.preregistered_ledger_rows()
    assert [row["candidate_ordinal"] for row in rows] == [10, 11]
    assert all(row["result_viewed"] is False for row in rows)
    assert all(row["result_status"] == "IMPLEMENTED_NOT_RUN" for row in rows)
    assert all(row["cumulative_candidate_count"] == 7 for row in rows)


def test_feature_order_hash_is_stable() -> None:
    first = v3e._feature_order_sha256()
    second = v3e._feature_order_sha256()
    assert first == second
    assert len(first) == 64


def test_contract_hash_constants_are_frozen() -> None:
    assert v3e.TRUE_RANKING_SPEC_SHA256 == "79534d29d414a08b60cca85e68e8781849aabefa1a103d9f43ab0ead47308c55"
    assert v3e.TRUE_RANKING_SPEC_GIT_BLOB == "20df2927b6663ea16955919760db9c1429cff3a5"
    assert v3e.TRUE_RANKING_ADDENDUM_SHA256 == "6652e1f934f58630619a9cab5afb0bdfaa3317894977bad8bfa9ca5ffe980812"
    assert v3e.TRUE_RANKING_ADDENDUM_GIT_BLOB == "01c4dca87ff52fca678c948e4ee23d3e3c82dbcd"
    assert v3e.DEPENDENCY_ERRATUM_SHA256 == "bd029458f7a7cd14424af9b748cb7522f1d23b0fe8eaf20ad8f6b44d48894bea"
    assert v3e.DEPENDENCY_ERRATUM_GIT_BLOB == "327e053c2a1b4270acc4e7de313bba97680eff8b"
    assert v3e.FROZEN_XGBOOST_VERSION == "3.2.0"


def test_existing_v3_gates_are_reused() -> None:
    import idx_trade.ranking_v3_recency as recency

    assert v3e._absolute_sanity is recency._absolute_sanity
    assert v3e._paired_promotion is recency._paired_promotion
    assert v3e._paired_metrics is recency._paired_metrics
