from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.provenance import sha256_file
from idx_trade.ranking_v4_participation_audit import (
    AUDIT_COLUMNS,
    V3_PARTICIPATION_CONTEXT_COLUMNS,
    audit_v4a_cache,
)
from idx_trade.ranking_v4_participation_prepare import V4_A_CACHE_STATUS
from idx_trade.research_v4_participation import V4_A_FEATURE_COLUMNS


def _audit_cache(tmp_path: Path) -> tuple[Path, Path]:
    rows = 120
    signal_index = np.arange(100, 100 + rows, dtype=int)
    frame = pd.DataFrame(
        {
            "ticker": [f"T{i:03d}" for i in range(rows)],
            "date": pd.date_range("2025-01-02", periods=rows, freq="D"),
            "signal_session_index": signal_index,
            "binary_target": np.arange(rows) % 2,
            "label_status": ["TP_FIRST"] * rows,
        }
    )
    base = np.linspace(-1.0, 1.0, rows)
    for offset, column in enumerate(V3_PARTICIPATION_CONTEXT_COLUMNS, start=1):
        frame[column] = base + offset * 0.01
    for offset, column in enumerate(V4_A_FEATURE_COLUMNS, start=1):
        frame[column] = np.sin(base * (offset + 1)) + offset * 0.001

    cache = tmp_path / "cache.parquet"
    frame.to_parquet(cache, index=False)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "status": V4_A_CACHE_STATUS,
                "cache_sha256": sha256_file(cache),
                "outcome_metrics_computed": False,
                "fresh_forward_accessed": False,
                "post_1224_materialized": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return cache, manifest


def test_outcome_blind_audit_projects_only_frozen_feature_columns(tmp_path: Path) -> None:
    cache, manifest = _audit_cache(tmp_path)
    output_dir = tmp_path / "audit"
    result = audit_v4a_cache(
        cache_path=cache,
        manifest_path=manifest,
        output_dir=output_dir,
    )

    assert result["status"] == "RANKING_V4_A_PARTICIPATION_OUTCOME_BLIND_AUDIT_COMPLETE"
    assert result["columns_loaded"] == list(AUDIT_COLUMNS)
    assert "binary_target" not in result["columns_loaded"]
    assert "label_status" not in result["columns_loaded"]
    assert result["binary_target_loaded"] is False
    assert result["outcome_columns_loaded"] is False
    assert result["fresh_forward_accessed"] is False
    assert result["post_1224_materialized"] is False
    assert result["rows"] == 120
    assert result["last_signal_session_index"] == 219
    assert set(result["feature_summary"]) == set(V4_A_FEATURE_COLUMNS)
    assert (output_dir / "ranking_v4_a_participation_outcome_blind_audit.json").is_file()
