from __future__ import annotations

import json

import pandas as pd
import pytest

from idx_trade.provenance import sha256_file
from idx_trade import path_risk_v1_discovery_run as run


def _label_frame() -> pd.DataFrame:
    dates = pd.date_range("2026-01-02", periods=3, freq="B")
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "signal_date": dates,
            "signal_session_index": [983, 984, 985],
            "signal_reference_close": [100.0, 100.0, 100.0],
            "atr": [2.0, 2.0, 2.0],
            "horizon": [10, 10, 10],
            "sl_atr_multiple": [1.0, 1.0, 1.0],
            "reward_risk": [1.5, 1.5, 1.5],
            "tp_level": [103.0, 103.0, 103.0],
            "sl_level": [98.0, 98.0, 98.0],
            "label_status": ["NO_BARRIER_HIT", "NO_BARRIER_HIT", "NO_BARRIER_HIT"],
            "first_barrier_date": [pd.NaT, pd.NaT, pd.NaT],
        }
    )


def _write_labels(tmp_path, frame: pd.DataFrame):
    path = tmp_path / "labels.parquet"
    frame.to_parquet(path, index=False)
    return path


def test_discovery_label_read_physically_bounds_session_984(tmp_path, monkeypatch) -> None:
    path = _write_labels(tmp_path, _label_frame())
    monkeypatch.setattr(run, "PATH_RISK_H10_LABEL_SHA256", sha256_file(path))
    labels = run._read_discovery_labels(path)
    assert labels["signal_session_index"].tolist() == [983, 984]
    assert int(labels["signal_session_index"].max()) == 984


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("horizon", 5, "horizon=10"),
        ("sl_atr_multiple", 0.5, "stop ATR multiple=1.0"),
        ("reward_risk", 2.0, "reward:risk=1.5"),
    ],
)
def test_discovery_labels_reject_nonfrozen_barrier_semantics(
    tmp_path, monkeypatch, column: str, value: float, message: str
) -> None:
    frame = _label_frame().iloc[:2].copy()
    frame.loc[0, column] = value
    path = _write_labels(tmp_path, frame)
    monkeypatch.setattr(run, "PATH_RISK_H10_LABEL_SHA256", sha256_file(path))
    with pytest.raises(RuntimeError, match=message):
        run._read_discovery_labels(path)


def test_discovery_folds_are_exact_f1_to_f4() -> None:
    folds = run._folds()
    assert [fold.name for fold in folds] == ["V2F1", "V2F2", "V2F3", "V2F4"]
    assert max(fold.validation_end for fold in folds) == 984


def test_feature_manifest_requires_preoutcome_flags(tmp_path, monkeypatch) -> None:
    feature_columns = list(run.PATH_RISK_FEATURE_COLUMNS)
    row = {
        "ticker": "AAA",
        "date": pd.Timestamp("2026-01-02"),
        "signal_session_index": 984,
        "universe_primary_liquid": True,
        **{column: 1.0 for column in feature_columns},
    }
    cache_path = tmp_path / "cache.parquet"
    pd.DataFrame([row]).to_parquet(cache_path, index=False)
    manifest = {
        "status": "PATH_RISK_V1_DISCOVERY_FEATURE_CACHE_FROZEN_PRE_OUTCOME",
        "cache_sha256": sha256_file(cache_path),
        "last_signal_session_index": 984,
        "feature_order_sha256": run.PATH_RISK_FEATURE_ORDER_SHA256,
        "real_h10_labels_loaded": False,
        "real_path_risk_target_computed": False,
        "pr001_model_fitted": False,
        "path_risk_performance_metrics_computed": False,
        "f5_f6_path_risk_accessed": False,
        "fresh_forward_accessed": False,
        "forward_marker_written": False,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(run, "FROZEN_FEATURE_CACHE_SHA256", sha256_file(cache_path))
    monkeypatch.setattr(run, "FROZEN_FEATURE_MANIFEST_SHA256", sha256_file(manifest_path))

    loaded, _ = run._read_feature_cache(cache_path, manifest_path)
    assert len(loaded) == 1

    manifest["real_h10_labels_loaded"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(run, "FROZEN_FEATURE_MANIFEST_SHA256", sha256_file(manifest_path))
    with pytest.raises(RuntimeError, match="real_h10_labels_loaded"):
        run._read_feature_cache(cache_path, manifest_path)
