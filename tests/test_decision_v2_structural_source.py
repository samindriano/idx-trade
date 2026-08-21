from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v2_structural_replay import DecisionV2StructuralReplayError
from idx_trade.decision_v2_structural_source import (
    ALLOWED_SCORE_COLUMNS,
    EXPECTED_REPLAY_CONTRACT_SHA256,
    _read_projected_score_frame,
    verify_frozen_replay_contract,
)


def test_replay_contract_file_is_sha_pinned() -> None:
    path = verify_frozen_replay_contract(Path("."))
    assert path.name == "decision_v2_minimal_structural_replay_contract_v1.json"
    assert len(EXPECTED_REPLAY_CONTRACT_SHA256) == 64


def test_projected_parquet_reader_never_loads_extra_label_or_return_columns(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scores.parquet"
    frame = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": ["2026-01-02", "2026-01-02"],
            "fold": ["F1", "F1"],
            "mode": ["validation", "validation"],
            "alpha_h5": [0.2, 0.1],
            "alpha_h10": [0.3, 0.2],
            "alpha_consensus": [0.25, 0.15],
            "realized_return_h5": [999.0, 999.0],
            "target_h10": [999.0, 999.0],
        }
    )
    frame.to_parquet(path, index=False)

    loaded = _read_projected_score_frame(path, expected_rows=2)

    assert tuple(loaded.columns) == ALLOWED_SCORE_COLUMNS
    assert "realized_return_h5" not in loaded.columns
    assert "target_h10" not in loaded.columns


def test_projected_reader_uses_parquet_metadata_for_row_guard(tmp_path: Path) -> None:
    path = tmp_path / "scores.parquet"
    pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": ["2026-01-02"],
            "fold": ["F1"],
            "mode": ["validation"],
            "alpha_h5": [0.2],
            "alpha_h10": [0.3],
            "alpha_consensus": [0.25],
        }
    ).to_parquet(path, index=False)

    with pytest.raises(
        DecisionV2StructuralReplayError,
        match="SCORE_ROW_COUNT_CHANGED",
    ):
        _read_projected_score_frame(path, expected_rows=2)
