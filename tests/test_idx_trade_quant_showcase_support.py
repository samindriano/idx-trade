from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "notebooks"))

import pandas as pd

from idx_trade_quant_showcase_support import (
    FORWARD_LIVE,
    FORWARD_MATURED,
    HISTORICAL_REPLAY,
    load_historical_oos,
    load_mode_artifacts,
    load_forward_live,
)


def _historical_fixture(root: Path) -> None:
    score = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "AAA", "BBB"],
            "date": pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"]),
            "alpha_consensus": [0.9, 0.1, 0.8, 0.2],
        }
    )
    target = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "AAA", "BBB"],
            "date": pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"]),
            "realized_consensus": [0.5, 0.1, 0.4, None],
            "target_state_consensus": [
                "TARGET_BOTH_AVAILABLE",
                "TARGET_BOTH_AVAILABLE",
                "TARGET_BOTH_AVAILABLE",
                "TARGET_DATA_UNOBSERVABLE",
            ],
        }
    )
    score.to_parquet(root / "clean_challenger_validation_scores.parquet", index=False)
    target.to_parquet(root / "clean_target_ledger.parquet", index=False)
    (root / "HISTORICAL_OOS_ACCESS_BOUNDARY.json").write_text(
        json.dumps({"status": "CLEAN_HISTORICAL_OOS_TARGET_ACCESS_COMMENCED", "measurement_only": True}),
        encoding="utf-8",
    )
    (root / "MANIFEST.json").write_text(
        json.dumps({"generation_id": "TEST", "measurement_only": True}),
        encoding="utf-8",
    )


def test_historical_adapter_excludes_unresolved_targets(tmp_path: Path) -> None:
    _historical_fixture(tmp_path)

    bundle = load_historical_oos(tmp_path)

    assert bundle.mode == HISTORICAL_REPLAY
    assert bundle.ready
    assert len(bundle.scores) == 4
    assert len(bundle.alpha_outcomes) == 3
    assert set(bundle.alpha_outcomes["ticker"]) == {"AAA", "BBB"}
    assert bundle.metadata["historical_execution_authority"] is False
    assert bundle.metadata["actual_live_historical_portfolio"] is False


def test_forward_live_refuses_outcome_bearing_flat_bundle(tmp_path: Path) -> None:
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / "integrity.json").write_text("{}", encoding="utf-8")
    (tmp_path / "alpha_outcomes.csv").write_text("session_date,ticker\n", encoding="utf-8")

    bundle = load_mode_artifacts(FORWARD_LIVE, showcase_root=tmp_path)

    assert bundle.status == "BLOCKED"
    assert "alpha_outcomes.csv" in bundle.message


def test_forward_matured_fails_closed_without_explicit_authorization(tmp_path: Path) -> None:
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / "integrity.json").write_text("{}", encoding="utf-8")
    (tmp_path / "alpha_outcomes.csv").write_text(
        "session_date,ticker,alpha_consensus,canonical_target\n",
        encoding="utf-8",
    )

    bundle = load_mode_artifacts(FORWARD_MATURED, matured_root=tmp_path)

    assert bundle.status == "BLOCKED"
    assert "authorized matured" in bundle.message


def test_forward_live_missing_root_is_non_mutating_and_explicit(tmp_path: Path) -> None:
    bundle = load_forward_live(tmp_path / "does-not-exist")

    assert bundle.status == "UNAVAILABLE"
    assert not bundle.ready
    assert set(bundle.field_status["Status"]) >= {"UNAVAILABLE", "BLOCKED"}
