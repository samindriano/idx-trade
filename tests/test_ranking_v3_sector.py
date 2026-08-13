from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade.ranking_v3_sector import (
    AUTHORIZATION_STATUS,
    V3_D_CANDIDATE,
    V3_D_CONTROL,
    V3_D_FEATURE_COLUMNS,
    _assert_run_authorization,
    _coverage_report,
    _sector_model,
    assert_discovery_fold_allowed,
)
from idx_trade.research_v2_features import V2_FULL_FEATURE_COLUMNS
from idx_trade.research_v3_sector import (
    SECTOR_FEATURE_COLUMNS,
    SECTOR_MIN_FINITE_MEMBERS,
    assign_pit_sector,
    build_sector_relative_features,
    validate_sector_history,
)


def _master(tickers: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"ticker": tickers})


def _history(
    *,
    ticker: str = "AAA",
    sector: str = "FINANCE",
    effective_from: str = "2024-01-01",
    effective_to: str | None = None,
    available_at: str = "2024-01-01T00:00:00Z",
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [ticker],
            "sector_code": [sector],
            "effective_from": [effective_from],
            "effective_to_exclusive": [effective_to],
            "available_at": [available_at],
            "source_id": ["idx-sector-snapshot-1"],
            "source_sha256": ["a" * 64],
        }
    )


def test_sector_feature_contract_appends_exact_six_after_v2() -> None:
    assert tuple(V3_D_FEATURE_COLUMNS[: len(V2_FULL_FEATURE_COLUMNS)]) == tuple(V2_FULL_FEATURE_COLUMNS)
    assert tuple(V3_D_FEATURE_COLUMNS[len(V2_FULL_FEATURE_COLUMNS) :]) == tuple(SECTOR_FEATURE_COLUMNS)
    assert len(V3_D_FEATURE_COLUMNS) == 31
    assert V3_D_CONTROL.endswith("008")
    assert V3_D_CANDIDATE.endswith("009")


def test_available_at_blocks_historical_backfill() -> None:
    history = validate_sector_history(
        _history(effective_from="2024-01-01", available_at="2024-02-01T12:00:00Z"),
        _master(["AAA"]),
    )
    features = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "date": ["2024-01-15", "2024-02-02"],
        }
    )
    assigned = assign_pit_sector(features, history)
    assert pd.isna(assigned.loc[0, "sector_code"])
    assert assigned.loc[1, "sector_code"] == "FINANCE"
    assert assigned.loc[1, "sector_usable_from"] == pd.Timestamp("2024-02-01")


def test_sector_history_rejects_overlapping_usable_intervals() -> None:
    history = pd.concat(
        [
            _history(effective_from="2024-01-01", effective_to="2024-07-01"),
            _history(effective_from="2024-06-01", effective_to=None, available_at="2024-06-01T00:00:00Z"),
        ],
        ignore_index=True,
    )
    with pytest.raises(ValueError, match="overlap"):
        validate_sector_history(history, _master(["AAA"]))


def test_sector_history_rejects_untraceable_ticker() -> None:
    with pytest.raises(ValueError, match="untraceable"):
        validate_sector_history(_history(ticker="ZZZ"), _master(["AAA"]))


def test_sector_history_rejects_bad_source_hash() -> None:
    history = _history()
    history.loc[0, "source_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="source_sha256"):
        validate_sector_history(history, _master(["AAA"]))


def _feature_rows(tickers: list[str], values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": tickers,
            "date": pd.Timestamp("2024-03-01"),
            "universe_primary_liquid": True,
            "close_return_5": values,
            "close_return_20": values,
            "close_position_20": values,
        }
    )


def _multi_history(tickers: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": tickers,
            "sector_code": "SECTOR_A",
            "effective_from": "2024-01-01",
            "effective_to_exclusive": None,
            "available_at": "2024-01-01T00:00:00Z",
            "source_id": "sector-source",
            "source_sha256": "b" * 64,
        }
    )


def test_sector_group_requires_five_finite_members() -> None:
    tickers = ["A", "B", "C", "D"]
    history = validate_sector_history(_multi_history(tickers), _master(tickers))
    result = build_sector_relative_features(_feature_rows(tickers, [1.0, 2.0, 3.0, 4.0]), history)
    assert SECTOR_MIN_FINITE_MEMBERS == 5
    assert result[list(SECTOR_FEATURE_COLUMNS)].isna().all().all()


def test_sector_rank_and_median_use_full_same_date_sector_group() -> None:
    tickers = ["A", "B", "C", "D", "E"]
    history = validate_sector_history(_multi_history(tickers), _master(tickers))
    result = build_sector_relative_features(_feature_rows(tickers, [1.0, 2.0, 3.0, 4.0, 5.0]), history)
    row_c = result[result["ticker"].eq("C")].iloc[0]
    row_e = result[result["ticker"].eq("E")].iloc[0]
    assert row_c["sector_rank_close_return_5"] == pytest.approx(3 / 5)
    assert row_e["sector_rank_close_return_5"] == pytest.approx(1.0)
    assert row_c["sector_relative_close_return_5"] == pytest.approx(0.0)
    assert row_e["sector_relative_close_return_5"] == pytest.approx(2.0)


def test_sector_feature_builder_rejects_outcome_columns() -> None:
    tickers = ["A", "B", "C", "D", "E"]
    history = validate_sector_history(_multi_history(tickers), _master(tickers))
    features = _feature_rows(tickers, [1.0, 2.0, 3.0, 4.0, 5.0])
    features["binary_target"] = 1
    with pytest.raises(ValueError, match="label/outcome"):
        build_sector_relative_features(features, history)


def test_sector_model_preserves_frozen_hgb_parameters() -> None:
    model = _sector_model()
    estimator = model.named_steps["model"]
    assert estimator.learning_rate == 0.05
    assert estimator.max_iter == 200
    assert estimator.max_leaf_nodes == 31
    assert estimator.l2_regularization == 1.0
    assert estimator.random_state == 42
    columns = tuple(model.named_steps["preprocess"].transformers[0][2])
    assert columns == tuple(V3_D_FEATURE_COLUMNS)


def test_v3_d_hard_blocks_f5_f6() -> None:
    for name in ("V2F5", "V2F6"):
        with pytest.raises(PermissionError):
            assert_discovery_fold_allowed(name)
    for name in ("V2F1", "V2F2", "V2F3", "V2F4"):
        assert_discovery_fold_allowed(name)


def test_coverage_gate_fails_when_sector_missing() -> None:
    rows = []
    for session in range(1, 985):
        rows.append(
            {
                "signal_session_index": session,
                "date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=session),
                "ticker": "AAA",
                "sector_code": pd.NA,
                **{column: np.nan for column in SECTOR_FEATURE_COLUMNS},
            }
        )
    report = _coverage_report(pd.DataFrame(rows))
    assert report["gate_pass"] is False


def test_outcome_run_requires_separate_authorization(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    cache = tmp_path / "cache.parquet"
    manifest = tmp_path / "manifest.json"
    auth = tmp_path / "auth.json"
    spec.write_text("spec", encoding="utf-8")
    pd.DataFrame({"x": [1]}).to_parquet(cache, index=False)
    manifest.write_text("{}", encoding="utf-8")
    auth.write_text(json.dumps({"status": "NOT_AUTHORIZED"}), encoding="utf-8")
    with pytest.raises(PermissionError, match="not authorized"):
        _assert_run_authorization(
            authorization_path=auth,
            spec_path=spec,
            cache_path=cache,
            cache_manifest_path=manifest,
            code_commit="abc",
        )


def test_valid_authorization_requires_v3_c_review(tmp_path: Path) -> None:
    from idx_trade.provenance import sha256_file

    spec = tmp_path / "spec.md"
    cache = tmp_path / "cache.parquet"
    manifest = tmp_path / "manifest.json"
    auth = tmp_path / "auth.json"
    spec.write_text("spec", encoding="utf-8")
    pd.DataFrame({"x": [1]}).to_parquet(cache, index=False)
    manifest.write_text("{}", encoding="utf-8")
    auth.write_text(
        json.dumps(
            {
                "status": AUTHORIZATION_STATUS,
                "v3_c_reviewed": False,
                "spec_sha256": sha256_file(spec),
                "cache_sha256": sha256_file(cache),
                "cache_manifest_sha256": sha256_file(manifest),
                "implementation_commit": "abc",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(PermissionError, match="V3-C review"):
        _assert_run_authorization(
            authorization_path=auth,
            spec_path=spec,
            cache_path=cache,
            cache_manifest_path=manifest,
            code_commit="abc",
        )
