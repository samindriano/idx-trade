from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from idx_trade import forward_model_runtime
from idx_trade.o2_1_sealed_shadow_runtime import (
    O21_FEATURE_COLUMNS,
    O21_FEATURE_ORDER_SHA256,
    SHADOW_MODEL_ID,
    SHADOW_ROOT_RELATIVE,
    SHADOW_RUN_ROOT,
    V3_FEATURE_ORDER_SHA256,
    _load_frozen_shadow,
    encode_o21_geometry,
    o21_hgb_pipeline,
    shadow_status,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fake_frozen_bundle(root: Path) -> Path:
    bundle = root / SHADOW_ROOT_RELATIVE
    bundle.mkdir(parents=True)
    model_path = bundle / "o2_1_sealed_shadow_model.joblib"
    feature_path = bundle / "feature_manifest.json"
    support_path = bundle / "training_support_manifest.json"
    model_manifest_path = bundle / "model_manifest.json"
    inventory_path = bundle / "artifact_manifest.json"
    model_path.write_bytes(b"sealed-model-fixture")
    feature_path.write_text("{}", encoding="utf-8")
    support_path.write_text("{}", encoding="utf-8")
    model_manifest = {
        "model_id": SHADOW_MODEL_ID,
        "sealed_shadow": True,
        "promotion_eligible": False,
        "independent_official_counter": False,
        "model_sha256": _sha(model_path),
        "feature_order_sha256": O21_FEATURE_ORDER_SHA256,
        "feature_columns": list(O21_FEATURE_COLUMNS),
        "training_support_sha256": "8c6429253d84d1e355c536c0c4b715f00d20ae0344c304aa2d7a218b323c596d",
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
    }
    model_manifest_path.write_text(json.dumps(model_manifest), encoding="utf-8")
    inventory_path.write_text(
        json.dumps(
            {
                "artifact_sha256": {
                    model_path.name: _sha(model_path),
                    feature_path.name: _sha(feature_path),
                    support_path.name: _sha(support_path),
                    model_manifest_path.name: _sha(model_manifest_path),
                }
            }
        ),
        encoding="utf-8",
    )
    return bundle


def _write_shadow_run(root: Path) -> None:
    bundle = _fake_frozen_bundle(root)
    output_dir = root / "forward_monitoring" / SHADOW_RUN_ROOT / "2026-08-12"
    output_dir.mkdir(parents=True)
    artifact = output_dir / "score_artifact.parquet"
    pd.DataFrame(
        {
            "ticker": ["FLAT", "A", "B"],
            "session_date": ["2026-08-12"] * 3,
            "flat_range": [1, 0, 0],
            "score": [0.3, 0.2, 0.1],
        }
    ).to_parquet(artifact, index=False)
    payload = {
        "session_date": "2026-08-12",
        "score_artifact_path": str(artifact),
        "score_artifact_sha256": _sha(artifact),
        "o2_coverage": "2/3",
        "shadow_coverage": "3/3",
        "flat_range_included": 1,
        "flat_share": 1 / 3,
        "sealed_shadow": True,
        "promotion_eligible": False,
        "independent_official_counter": False,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
    }
    (output_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    assert bundle.exists()


def test_flat_row_is_included_by_o21_but_excluded_by_o2() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["NORMAL", "FLAT"],
            "open": [10.0, 50.0],
            "high": [11.0, 50.0],
            "low": [9.0, 50.0],
        }
    )
    original = frame.copy(deep=True)
    geometry, summary = encode_o21_geometry(frame)
    o2_geometry = forward_model_runtime._derive_o2_geometry(frame.assign(session_date="2026-08-12"))

    assert summary["flat_rows"] == 1
    assert geometry.loc[1, ["open_position_o21", "open_to_high", "open_to_low", "flat_range"]].tolist() == [0.5, 0.0, 0.0, 1]
    assert bool(o2_geometry.loc[1, "o2_geometry_valid"]) is False
    assert o2_geometry.loc[1, "o2_geometry_reason"] == "FLAT_RANGE_ZERO_DENOMINATOR"
    pd.testing.assert_frame_equal(frame, original)


def test_normal_o21_score_is_stable_and_uses_frozen_feature_order() -> None:
    assert len(O21_FEATURE_COLUMNS) == 37
    assert V3_FEATURE_ORDER_SHA256 == "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"
    assert O21_FEATURE_ORDER_SHA256 == "f0259e82240f3db76bab8929669082a422e124c8cb37a08cd94c6cff9220b3b3"
    frame = pd.DataFrame(np.tile(np.linspace(0.01, 0.99, 37), (6, 1)), columns=O21_FEATURE_COLUMNS)
    frame.iloc[:, 0] += np.arange(6) * 0.01
    model = o21_hgb_pipeline()
    model.fit(frame, np.array([0, 1, 0, 1, 0, 1]))
    first = forward_model_runtime.pointwise_raw_score(model, frame)
    second = forward_model_runtime.pointwise_raw_score(model, frame.copy())
    np.testing.assert_allclose(first, second, rtol=0, atol=0)


def test_shadow_status_uses_stored_counts_and_never_changes_o2_counter(tmp_path: Path) -> None:
    _write_shadow_run(tmp_path)
    counter = tmp_path / "forward_monitoring" / "o2_forward_counter.json"
    counter.parent.mkdir(parents=True, exist_ok=True)
    counter.write_text('{"session_count": 1, "outcomes_accessed": false}', encoding="utf-8")
    before = counter.read_bytes()

    status = shadow_status(tmp_path)

    assert status["status"] == "SEALED"
    assert status["shadow_sessions_aligned"] == 1
    assert status["o2_coverage"] == "2/3"
    assert status["shadow_coverage"] == "3/3"
    assert status["flat_range_included"] == 1
    assert status["flat_share"] == pytest.approx(1 / 3)
    assert status["promotion_eligible"] is False
    assert status["independent_official_counter"] is False
    assert status["fresh_forward_outcomes_accessed"] is False
    assert counter.read_bytes() == before


def test_shadow_fingerprint_is_immutable(tmp_path: Path) -> None:
    _write_shadow_run(tmp_path)
    _load_frozen_shadow(tmp_path)
    model_path = tmp_path / SHADOW_ROOT_RELATIVE / "o2_1_sealed_shadow_model.joblib"
    model_path.write_bytes(b"tampered-model")
    with pytest.raises(RuntimeError, match="model SHA mismatch"):
        _load_frozen_shadow(tmp_path)


def test_o2_counter_model_set_does_not_contain_shadow() -> None:
    assert SHADOW_MODEL_ID not in {spec.model_id for spec in forward_model_runtime.FROZEN_MODELS}
    assert len(forward_model_runtime.FROZEN_MODELS) == 3


def test_monitoring_has_three_primary_cards_and_o2_detail_has_subordinate_shadow() -> None:
    root = Path(__file__).parents[1]
    monitoring_page = (root / "apps/web/app/monitoring/page.tsx").read_text(encoding="utf-8")
    detail_page = (root / "apps/web/app/monitoring/models/[modelId]/page.tsx").read_text(encoding="utf-8")
    assert monitoring_page.count('className="surface modelCardLink') == 3
    assert "O2.1" not in monitoring_page
    assert "O2.1 FLAT-RANGE SHADOW" in detail_page
    assert 'params.modelId === "o2"' in detail_page
    assert "promotion_eligible" in detail_page
