from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.provenance import sha256_file
from idx_trade.ranking_v3_sector import AUTHORIZATION_STATUS, V3_D_FEATURE_COLUMNS
from idx_trade.ranking_v3_sector_amended import (
    REGIME_MEDIAN_PR_FLOOR,
    REGIME_MEDIAN_Q5_FLOOR,
    REGIME_MEDIAN_ROC_FLOOR,
    REGIME_WORST_PR_FLOOR,
    V3_C_REGIME_CACHE_SHA256,
    _assert_amended_authorization,
    _regime_guard,
)
from idx_trade.research_v3_sector import SECTOR_FEATURE_COLUMNS


def _aggregate(
    *,
    normal_pr: float = 0.0,
    stress_pr: float = 0.0,
    normal_roc: float = 0.0,
    stress_roc: float = 0.0,
    normal_q5: float = 0.0,
    stress_q5: float = 0.0,
    worst_pr: float = 0.0,
) -> dict[str, object]:
    return {
        "states": {
            "NORMAL": {
                "median_pr_delta_improvement": normal_pr,
                "median_roc_change": normal_roc,
                "median_q5_minus_q1_change": normal_q5,
            },
            "STRESS": {
                "median_pr_delta_improvement": stress_pr,
                "median_roc_change": stress_roc,
                "median_q5_minus_q1_change": stress_q5,
            },
        },
        "worst_fold_state_pr_delta_improvement": worst_pr,
    }


def test_post_v3c_amendment_does_not_change_model_feature_count() -> None:
    assert len(V3_D_FEATURE_COLUMNS) == 31
    assert tuple(V3_D_FEATURE_COLUMNS[-len(SECTOR_FEATURE_COLUMNS) :]) == tuple(SECTOR_FEATURE_COLUMNS)
    assert not any("regime" in column.lower() or "stress" in column.lower() for column in V3_D_FEATURE_COLUMNS)


def test_regime_guard_thresholds_are_frozen_non_degradation_floors() -> None:
    assert REGIME_MEDIAN_PR_FLOOR == -0.005
    assert REGIME_MEDIAN_ROC_FLOOR == -0.005
    assert REGIME_MEDIAN_Q5_FLOOR == -0.005
    assert REGIME_WORST_PR_FLOOR == -0.015


def test_regime_guard_passes_at_exact_floors() -> None:
    passed, checks = _regime_guard(
        _aggregate(
            normal_pr=-0.005,
            stress_pr=-0.005,
            normal_roc=-0.005,
            stress_roc=-0.005,
            normal_q5=-0.005,
            stress_q5=-0.005,
            worst_pr=-0.015,
        )
    )
    assert passed is True
    assert all(checks.values())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("normal_pr", -0.0050001),
        ("stress_pr", -0.0050001),
        ("normal_roc", -0.0050001),
        ("stress_roc", -0.0050001),
        ("normal_q5", -0.0050001),
        ("stress_q5", -0.0050001),
        ("worst_pr", -0.0150001),
    ],
)
def test_regime_guard_fails_each_frozen_floor(field: str, value: float) -> None:
    kwargs = {field: value}
    passed, checks = _regime_guard(_aggregate(**kwargs))
    assert passed is False
    assert not all(checks.values())


def test_amended_authorization_requires_exact_amendment_and_v3c_cache_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    amendment = tmp_path / "amendment.md"
    regime_cache = tmp_path / "regime.parquet"
    authorization = tmp_path / "authorization.json"
    amendment.write_text("frozen amendment", encoding="utf-8")
    pd.DataFrame({"x": [1]}).to_parquet(regime_cache, index=False)

    actual_regime_sha = sha256_file(regime_cache)
    monkeypatch.setattr("idx_trade.ranking_v3_sector_amended.V3_C_REGIME_CACHE_SHA256", actual_regime_sha)
    authorization.write_text(
        json.dumps(
            {
                "status": AUTHORIZATION_STATUS,
                "v3_c_reviewed": True,
                "amendment_sha256": sha256_file(amendment),
                "v3_c_regime_cache_sha256": actual_regime_sha,
            }
        ),
        encoding="utf-8",
    )
    result = _assert_amended_authorization(
        authorization_path=authorization,
        amendment_path=amendment,
        v3_c_regime_cache_path=regime_cache,
    )
    assert result["v3_c_reviewed"] is True


def test_amended_authorization_rejects_wrong_amendment_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    amendment = tmp_path / "amendment.md"
    regime_cache = tmp_path / "regime.parquet"
    authorization = tmp_path / "authorization.json"
    amendment.write_text("frozen amendment", encoding="utf-8")
    pd.DataFrame({"x": [1]}).to_parquet(regime_cache, index=False)
    actual_regime_sha = sha256_file(regime_cache)
    monkeypatch.setattr("idx_trade.ranking_v3_sector_amended.V3_C_REGIME_CACHE_SHA256", actual_regime_sha)
    authorization.write_text(
        json.dumps(
            {
                "status": AUTHORIZATION_STATUS,
                "v3_c_reviewed": True,
                "amendment_sha256": "0" * 64,
                "v3_c_regime_cache_sha256": actual_regime_sha,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(PermissionError, match="amendment identity"):
        _assert_amended_authorization(
            authorization_path=authorization,
            amendment_path=amendment,
            v3_c_regime_cache_path=regime_cache,
        )


def test_authoritative_v3c_regime_cache_identity_is_pinned() -> None:
    assert V3_C_REGIME_CACHE_SHA256 == "1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8"
