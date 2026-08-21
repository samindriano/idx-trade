from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from idx_trade.decision_v3_structural_source import (
    ALLOWED_SCORE_COLUMNS,
    EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256,
    REPLAY_CONTRACT_RELATIVE_PATH,
    _read_projected_score_frame,
    canonical_json_sha256,
    verify_frozen_replay_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_frozen_replay_contract_has_expected_canonical_hash() -> None:
    path = verify_frozen_replay_contract(REPO_ROOT)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert canonical_json_sha256(payload) == EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256
    assert payload["status"] == "FROZEN_BEFORE_FIRST_REPLAY"
    assert payload["execution_authorized"] is False


def test_contract_hash_is_line_ending_and_formatting_invariant(tmp_path: Path) -> None:
    source = REPO_ROOT / REPLAY_CONTRACT_RELATIVE_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    crlf = tmp_path / "contract.json"
    crlf.write_bytes(
        json.dumps(payload, indent=4, sort_keys=False).replace("\n", "\r\n").encode("utf-8")
    )
    reloaded = json.loads(crlf.read_text(encoding="utf-8"))
    assert canonical_json_sha256(reloaded) == EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256


def test_strict_parquet_projection_does_not_read_head_scores_or_outcomes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scores.parquet"
    frame = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "date": pd.to_datetime(["2026-01-02"] * 3),
            "fold": ["F1"] * 3,
            "mode": ["OOS"] * 3,
            "alpha_consensus": [0.3, 0.2, 0.1],
            "alpha_h5": [999.0, 999.0, 999.0],
            "alpha_h10": [999.0, 999.0, 999.0],
            "realized_return_h5": [123.0, 123.0, 123.0],
            "target_h10": [456.0, 456.0, 456.0],
        }
    )
    frame.to_parquet(path, index=False)

    projected = _read_projected_score_frame(path, expected_rows=3)
    assert tuple(projected.columns) == ALLOWED_SCORE_COLUMNS
    assert "alpha_h5" not in projected.columns
    assert "alpha_h10" not in projected.columns
    assert "realized_return_h5" not in projected.columns
    assert "target_h10" not in projected.columns


def test_machine_contract_projection_matches_code() -> None:
    payload = json.loads(
        (REPO_ROOT / REPLAY_CONTRACT_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    assert payload["source"]["allowed_parquet_columns"] == list(ALLOWED_SCORE_COLUMNS)
    assert payload["source"]["policy_visible_fields"] == ["ticker", "rank_consensus"]
    assert payload["source"]["alpha_consensus_use"] == (
        "RANK_RECONSTRUCTION_ONLY_NOT_POLICY_INPUT"
    )
