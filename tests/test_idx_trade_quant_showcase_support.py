from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "notebooks"))

import pandas as pd

from idx_trade_quant_showcase_support import (
    FORWARD_LIVE,
    FORWARD_MATURED,
    HISTORICAL_REPLAY,
    ShowcaseDataError,
    evaluate_historical_alpha_metrics,
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
            "realized_consensus": [0.5, 0.1, 0.4, 0.3],
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
    boundary = {
        "schema_version": "ranking_v4_x1_clean_historical_oos_access_boundary_v1",
        "status": "CLEAN_HISTORICAL_OOS_TARGET_ACCESS_COMMENCED",
        "generation_id": "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1",
        "measurement_only": True,
        "fresh_forward_accessed": False,
        "protected_forward_accessed": False,
        "network_calls": False,
        "provider_calls": False,
    }
    boundary_path = root / "HISTORICAL_OOS_ACCESS_BOUNDARY.json"
    boundary_path.write_text(
        json.dumps(boundary),
        encoding="utf-8",
    )
    sha256 = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (root / "MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": "ranking_v4_x1_clean_historical_oos_replay_manifest_v1",
                "status": "V4_X1_CLEAN_HISTORICAL_OOS_REPLAY_COMPLETE_REVIEW_REQUIRED",
                "generation_id": "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1",
                "measurement_only": True,
                "deployed_model_mutated": False,
                "forward_counter_mutated": False,
                "fresh_forward_accessed": False,
                "network_calls": False,
                "model_change_authorized": False,
                "protected_forward_accessed": False,
                "provider_calls": False,
                "output_hashes": {
                    "access_boundary": sha256(boundary_path),
                    "scores_challenger": sha256(root / "clean_challenger_validation_scores.parquet"),
                    "target_ledger": sha256(root / "clean_target_ledger.parquet"),
                },
                "input_hashes": {
                    "scores_challenger": sha256(root / "clean_challenger_validation_scores.parquet"),
                    "target_ledger": sha256(root / "clean_target_ledger.parquet"),
                },
            }
        ),
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
    assert bundle.metadata["valid_alpha_rows"] == 3
    assert bundle.sessions.loc[
        bundle.sessions["session_date"].eq(pd.Timestamp("2024-01-03")), "valid_alpha_rows"
    ].item() == 1


def test_historical_rank_summaries_preserve_original_rank_after_filtering() -> None:
    rows = []
    for session_index in range(5):
        session_date = pd.Timestamp("2024-01-02") + pd.Timedelta(days=session_index)
        for rank in range(1, 12):
            rows.append(
                {
                    "session_date": session_date,
                    "ticker": f"T{rank:02d}",
                    "alpha_consensus": float(100 - rank),
                    "canonical_target": float(rank) / 100,
                    "rank": rank,
                }
            )
    frame = pd.DataFrame(rows)
    frame.loc[frame["rank"].eq(10), "canonical_target"] = float("nan")
    frame = frame.loc[frame["canonical_target"].notna()].copy()

    metrics = evaluate_historical_alpha_metrics(frame)

    assert metrics["top_k"]["TOP_10"]["mean"] == sum(range(1, 10)) / 9 / 100
    assert metrics["rank_buckets"]["RANK_11_20"]["row_count"] == 5


def test_historical_adapter_rejects_invalid_authority_boundary(tmp_path: Path) -> None:
    _historical_fixture(tmp_path)
    boundary_path = tmp_path / "HISTORICAL_OOS_ACCESS_BOUNDARY.json"
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    boundary["status"] = "NOT_AUTHORIZED"
    boundary_path.write_text(json.dumps(boundary), encoding="utf-8")

    try:
        load_historical_oos(tmp_path)
    except ShowcaseDataError as exc:
        assert "status is not accepted" in str(exc)
    else:
        raise AssertionError("invalid historical authority boundary was accepted")


def test_forward_live_refuses_outcome_bearing_flat_bundle(tmp_path: Path) -> None:
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / "integrity.json").write_text("{}", encoding="utf-8")
    (tmp_path / "alpha_outcomes.csv").write_text("session_date,ticker\n", encoding="utf-8")

    bundle = load_mode_artifacts(FORWARD_LIVE, showcase_root=tmp_path)

    assert bundle.status == "BLOCKED"
    assert "alpha_outcomes.csv" in bundle.message


def test_forward_live_flat_nav_is_not_exposed_as_portfolio_performance(tmp_path: Path) -> None:
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / "integrity.json").write_text("{}", encoding="utf-8")
    (tmp_path / "nav.csv").write_text(
        "session_date,nav\n2026-08-01,100\n2026-08-02,110\n",
        encoding="utf-8",
    )

    bundle = load_mode_artifacts(FORWARD_LIVE, showcase_root=tmp_path)

    assert bundle.status == "READY"
    assert bundle.nav.empty


def test_forward_live_rejects_outcome_access_in_an_earlier_session_manifest(tmp_path: Path) -> None:
    session_dir = tmp_path / "sessions" / "2026-08-01"
    session_dir.mkdir(parents=True)
    (session_dir / "manifest.json").write_text(
        json.dumps({"session_date": "2026-08-01", "forward_outcomes_accessed": True}),
        encoding="utf-8",
    )

    try:
        load_forward_live(tmp_path)
    except ShowcaseDataError as exc:
        assert "prospective outcome access" in str(exc)
    else:
        raise AssertionError("earlier outcome-bearing session manifest was accepted")


def test_forward_live_rejects_outcome_bearing_score_schema_before_loading(tmp_path: Path) -> None:
    session_dir = tmp_path / "sessions" / "2026-08-01"
    candidate = tmp_path / "model_runs" / "2026-08-01" / "v4_x1_clean_geometry3_prospective_v1"
    session_dir.mkdir(parents=True)
    candidate.mkdir(parents=True)
    (session_dir / "manifest.json").write_text(
        json.dumps({"session_date": "2026-08-01", "outcome_blind": True}),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": ["2026-08-01"],
            "alpha_consensus": [0.5],
            "canonical_target": [0.4],
        }
    ).to_parquet(candidate / "score_artifact.parquet", index=False)
    (candidate / "manifest.json").write_text(
        json.dumps({"session_date": "2026-08-01", "outcome_blind": True}),
        encoding="utf-8",
    )

    try:
        load_forward_live(tmp_path)
    except ShowcaseDataError as exc:
        assert "protected outcome columns" in str(exc)
    else:
        raise AssertionError("outcome-bearing score schema was loaded")


def test_forward_live_normal_manifest_passes(tmp_path: Path) -> None:
    session_dir = tmp_path / "sessions" / "2026-08-01"
    session_dir.mkdir(parents=True)
    (session_dir / "manifest.json").write_text(
        json.dumps(
            {
                "session_date": "2026-08-01",
                "outcome_blind": True,
                "forward_outcomes_accessed": False,
            }
        ),
        encoding="utf-8",
    )

    bundle = load_forward_live(tmp_path)

    assert bundle.status == "READY"
    assert bundle.metadata["forward_outcomes_accessed"] is False


def test_forward_matured_fails_closed_without_explicit_authorization(tmp_path: Path) -> None:
    (tmp_path / "metadata.json").write_text('{"matured_access_granted": true}', encoding="utf-8")
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
