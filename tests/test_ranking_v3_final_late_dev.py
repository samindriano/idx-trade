from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import idx_trade.ranking_v3_final_late_dev as finalv3
import idx_trade.ranking_v3_structure_lite as v3b
from idx_trade.research_v2_models import HGB_XS_MARKET


def _metric_frame(
    *,
    pr: tuple[float, float],
    roc: tuple[float, float],
    spread: tuple[float, float],
    top: tuple[float, float] = (0.02, 0.02),
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidate": ["x", "x"],
            "fold": ["V2F5", "V2F6"],
            "positive_rate": [0.4, 0.4],
            "pr_auc": [0.4 + pr[0], 0.4 + pr[1]],
            "pr_auc_delta_vs_base": list(pr),
            "roc_auc": list(roc),
            "q1_tp_rate": [0.35, 0.35],
            "q5_tp_rate": [0.35 + spread[0], 0.35 + spread[1]],
            "q5_minus_q1": list(spread),
            "top_decile_tp_rate": [0.4 + top[0], 0.4 + top[1]],
            "top_decile_lift": list(top),
        }
    )


def _predictions(candidate: str, reverse: bool = False) -> pd.DataFrame:
    rows = []
    for fold in ("V2F5", "V2F6"):
        for day in range(2):
            date = pd.Timestamp("2025-01-02") + pd.Timedelta(days=day)
            for index in range(10):
                score = float(9 - index if reverse else index)
                rows.append(
                    {
                        "candidate": candidate,
                        "fold": fold,
                        "ticker": f"T{index:02d}",
                        "date": date,
                        "signal_session_index": 1005 + day,
                        "binary_target": int(index >= 5),
                        "score": score,
                    }
                )
    return pd.DataFrame(rows)


def test_exact_late_fold_contract() -> None:
    assert finalv3.LATE_FOLD_NAMES == ("V2F5", "V2F6")
    assert [(f.train_end, f.validation_start, f.validation_end) for f in finalv3.LATE_FOLDS] == [
        (984, 1005, 1104),
        (1104, 1125, 1224),
    ]
    assert finalv3.MAX_LATE_SIGNAL_INDEX == 1224


def test_only_f5_f6_are_authorized() -> None:
    for name in ("V2F5", "V2F6"):
        finalv3.assert_late_fold_allowed(name)
    for name in ("V2F1", "V2F2", "V2F3", "V2F4"):
        with pytest.raises(PermissionError):
            finalv3.assert_late_fold_allowed(name)


def test_v2_late_read_physically_caps_session_1224(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "prepared.parquet"
    path.write_bytes(b"placeholder")
    captured: dict[str, object] = {}

    def fake_read_parquet(file_path, *, filters):
        captured["path"] = file_path
        captured["filters"] = filters
        return pd.DataFrame(
            {
                "signal_session_index": [1224],
                "ticker": ["AAA"],
                "date": [pd.Timestamp("2025-01-02")],
                "binary_target": [1],
            }
        )

    monkeypatch.setattr(finalv3.pd, "read_parquet", fake_read_parquet)
    result = finalv3._read_v2_late_subset(path)
    assert captured["filters"] == [("signal_session_index", "<=", 1224)]
    assert int(result["signal_session_index"].max()) == 1224


def test_v2_late_read_rejects_session_1225(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "prepared.parquet"
    path.write_bytes(b"placeholder")
    monkeypatch.setattr(
        finalv3.pd,
        "read_parquet",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "signal_session_index": [1225],
                "ticker": ["AAA"],
                "date": [pd.Timestamp("2025-01-02")],
                "binary_target": [1],
            }
        ),
    )
    with pytest.raises(RuntimeError, match="1225"):
        finalv3._read_v2_late_subset(path)


def test_structure_model_and_feature_bundle_are_exact_v3b() -> None:
    assert finalv3._structure_model is v3b._structure_model
    assert finalv3.V3_B_FEATURE_COLUMNS == v3b.V3_B_FEATURE_COLUMNS
    assert finalv3.V3_B_CONTROL == v3b.V3_B_CONTROL
    assert finalv3.V3_B_CANDIDATE == v3b.V3_B_CANDIDATE


def test_absolute_gate_requires_all_three_metrics_positive_both_folds() -> None:
    passed, detail = finalv3._absolute_gate(
        _metric_frame(pr=(0.01, 0.02), roc=(0.51, 0.52), spread=(0.03, 0.04))
    )
    assert passed is True
    assert all(detail.values())

    failed, detail = finalv3._absolute_gate(
        _metric_frame(pr=(0.01, 0.02), roc=(0.51, 0.49), spread=(0.03, 0.04))
    )
    assert failed is False
    assert detail["roc_gt_half_both"] is False


def test_paired_confirmation_passes_only_when_frozen_rules_all_hold() -> None:
    control = _metric_frame(pr=(0.01, 0.02), roc=(0.52, 0.52), spread=(0.03, 0.04))
    candidate = _metric_frame(pr=(0.012, 0.024), roc=(0.519, 0.523), spread=(0.031, 0.042))
    paired, summary, passed = finalv3._paired_confirmation(candidate, control)
    assert list(paired["fold"]) == ["V2F5", "V2F6"]
    assert passed is True
    assert summary["pr_nonnegative_both"] is True
    assert summary["q5_q1_nonnegative_both"] is True
    assert summary["median_pr_auc_delta_improvement"] >= 0.001


def test_paired_confirmation_fails_if_one_pr_fold_is_negative() -> None:
    control = _metric_frame(pr=(0.01, 0.02), roc=(0.52, 0.52), spread=(0.03, 0.04))
    candidate = _metric_frame(pr=(0.009, 0.026), roc=(0.52, 0.52), spread=(0.031, 0.041))
    _, summary, passed = finalv3._paired_confirmation(candidate, control)
    assert summary["pr_nonnegative_both"] is False
    assert passed is False


def test_paired_confirmation_fails_if_one_q5q1_fold_is_negative() -> None:
    control = _metric_frame(pr=(0.01, 0.02), roc=(0.52, 0.52), spread=(0.03, 0.04))
    candidate = _metric_frame(pr=(0.012, 0.024), roc=(0.52, 0.52), spread=(0.029, 0.045))
    _, summary, passed = finalv3._paired_confirmation(candidate, control)
    assert summary["q5_q1_nonnegative_both"] is False
    assert passed is False


def test_top_decile_overlap_is_deterministic() -> None:
    same = finalv3._top_decile_overlap(
        _predictions(finalv3.V3_B_CONTROL),
        _predictions(finalv3.V3_B_CANDIDATE),
    )
    assert np.allclose(same["jaccard"], 1.0)
    assert (same["entrants"] == 0).all()
    assert (same["exits"] == 0).all()

    changed = finalv3._top_decile_overlap(
        _predictions(finalv3.V3_B_CONTROL),
        _predictions(finalv3.V3_B_CANDIDATE, reverse=True),
    )
    assert (changed["jaccard"] < 1.0).all()
    assert (changed["entrants"] > 0).all()
    assert (changed["exits"] > 0).all()


def test_late_confirmation_does_not_create_new_candidate_count() -> None:
    assert finalv3.V3_B_CONTROL.endswith("004")
    assert finalv3.V3_B_CANDIDATE.endswith("005")
    assert finalv3.MEDIAN_PR_CONFIRM == 0.001
    assert finalv3.ROC_NONINFERIORITY == -0.005


def test_final_contract_hashes_are_frozen() -> None:
    assert finalv3.LATE_SPEC_SHA256 == "c1acbe99656b0a0a0adabc7840ad779ee0553b59b7441a24607a53322d1b369f"
    assert finalv3.LATE_SPEC_GIT_BLOB == "08eba22b5f36efb160cc01abbfb5cb82d079f36e"
    assert finalv3.LATE_ADDENDUM_SHA256 == "fa6c856f6cc45714b8ba5b4817a06fab2f9141fe66be7982c0c2a30ee1fd799e"
    assert finalv3.LATE_ADDENDUM_GIT_BLOB == "8ae7147af61c9aeaf9993576cac198c8ab8c9387"
    assert finalv3.HGB_XS_MARKET == HGB_XS_MARKET
