from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade.forward_100_evaluator import (
    O2_FEATURE_ORDER_SHA256,
    O2_MODEL_SHA256,
    O2_REQUIRED_METRICS,
    PROTOCOL_SHA256,
    RELIABILITY_METRICS,
    SYNTHETIC_MARKER,
    ForwardEvaluationBlocked,
    classify_o2_decision,
    classify_reliability_decision,
    joint_interpretation,
    local_pairwise_quality,
    materialize_outcome_frame,
    reliability_session_metrics,
    run_synthetic_forward_evaluation,
    validate_named_artifacts,
    validate_o2_scores,
    validate_session_inventory,
)
from idx_trade.provenance import sha256_file


PROTOCOL = Path(__file__).parents[1] / "docs" / "checkpoints" / "2026-08-13_FORWARD_100_SESSION_EVALUATION_PROTOCOL_V1.md"


def _metric_block(*, pr: float = 0.10, roc: float = 0.60, spread: float = 0.10) -> dict[str, float]:
    return {
        "rows": 100.0,
        "positive_rate": 0.40,
        "pr_auc": 0.40 + pr,
        "pr_auc_delta_vs_base": pr,
        "roc_auc": roc,
        "q1_tp_rate": 0.30,
        "q5_tp_rate": 0.30 + spread,
        "q5_minus_q1": spread,
        "top_decile_tp_rate": 0.50,
        "top_decile_lift": 0.10,
    }


def _reliability_block(value: float = 0.1) -> dict[str, float]:
    return {name: value for name in RELIABILITY_METRICS}


def _fixture_bundle(
    tmp_path: Path,
) -> tuple[Path, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, dict[str, str]]]:
    root = tmp_path / "non_protected_fixtures"
    root.mkdir()
    files: dict[str, tuple[Path, str]] = {}
    for name in ("o2_score", "reliability"):
        path = root / f"{name}.fixture"
        path.write_text(f"synthetic {name}\n", encoding="utf-8")
        files[name] = (path, sha256_file(path))
    shared_path = root / "shared_artifact.fixture"
    shared_path.write_text("synthetic shared provenance\n", encoding="utf-8")
    shared = {
        role: {"path": str(shared_path), "sha256": sha256_file(shared_path)}
        for role in (
            "o2_model",
            "o2_model_manifest",
            "o2_feature_order",
            "official_calendar",
            "security_master",
            "tradability",
            "corporate_actions",
            "source_snapshot",
        )
    }

    dates = pd.bdate_range("2020-01-02", periods=100)
    inventory_rows: list[dict[str, object]] = []
    protected_flags = {
        "provider_call": False,
        "outcome_access": False,
        "o2_refit": False,
        "o2_rescore": False,
        "counter_change": False,
        "tiering_or_filtering": False,
    }
    for date, session_index in zip(dates, range(2000, 2100), strict=True):
        session_key = date.date().isoformat()
        o2_manifest_path = root / f"o2_manifest_{session_index}.json"
        o2_manifest_path.write_text(
            json.dumps(
                {
                    "status": "DONE",
                    "session_date": session_key,
                    "official_session_index": session_index,
                    "score_artifact_sha256": files["o2_score"][1],
                    "model_sha256": O2_MODEL_SHA256,
                    "feature_order_sha256": O2_FEATURE_ORDER_SHA256,
                    "outcome_blind": True,
                    "fresh_forward_outcomes_accessed": False,
                    "forward_outcome_access_marker_written": False,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        o2_manifest_sha = sha256_file(o2_manifest_path)
        reliability_manifest_path = root / f"reliability_manifest_{session_index}.json"
        reliability_manifest_path.write_text(
            json.dumps(
                {
                    "status": "READY",
                    "session_date": session_key,
                    "official_session_index": session_index,
                    "reliability_artifact_sha256": files["reliability"][1],
                    "o2_source_score_artifact_sha256": files["o2_score"][1],
                    "o2_source_session_manifest_sha256": o2_manifest_sha,
                    "o2_model_sha256": O2_MODEL_SHA256,
                    "o2_feature_order_sha256": O2_FEATURE_ORDER_SHA256,
                    "outcome_access": "LOCKED",
                    "runtime_flags": protected_flags,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        inventory_rows.append(
            {
                "session_date": date,
                "session_index": session_index,
                "o2_score_path": str(files["o2_score"][0]),
                "o2_score_sha256": files["o2_score"][1],
                "o2_manifest_path": str(o2_manifest_path),
                "o2_manifest_sha256": o2_manifest_sha,
                "reliability_path": str(files["reliability"][0]),
                "reliability_sha256": files["reliability"][1],
                "reliability_manifest_path": str(reliability_manifest_path),
                "reliability_manifest_sha256": sha256_file(reliability_manifest_path),
                "protected": False,
            }
        )
    inventory = pd.DataFrame(inventory_rows)

    score_rows: list[dict[str, object]] = []
    outcome_rows: list[dict[str, object]] = []
    reliability_rows: list[dict[str, object]] = []
    for offset, (date, session_index) in enumerate(zip(dates, range(2000, 2100), strict=True)):
        for rank in range(50):
            ticker = f"T{rank:03d}"
            score = float(rank)
            target = int(rank >= 25)
            score_rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "session_index": session_index,
                    "o2_eligible": True,
                    "score": score,
                }
            )
            outcome_rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "binary_target": target,
                    "unresolved_reason": "",
                    "source_ref": f"synthetic://outcomes/{offset}",
                    "source_sha256": "a" * 64,
                }
            )
            reliability_rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "score_margin_reliability": float((rank % 7) + rank / 100.0),
                }
            )
    return (
        root,
        inventory,
        pd.DataFrame(score_rows),
        pd.DataFrame(outcome_rows),
        pd.DataFrame(reliability_rows),
        shared,
    )


def test_exact_100_session_and_fixed_50_50_inventory_boundaries(tmp_path: Path) -> None:
    root, inventory, scores, _, _, _ = _fixture_bundle(tmp_path)
    validated = validate_session_inventory(inventory, fixture_root=root)
    assert len(validated) == 100
    assert len(validated.iloc[:50]) == len(validated.iloc[50:]) == 50
    validate_o2_scores(scores, validated)

    with pytest.raises(ForwardEvaluationBlocked, match="exactly 100"):
        validate_session_inventory(inventory.iloc[:-1], fixture_root=root)
    broken = inventory.copy()
    broken.loc[50, "session_index"] += 1
    with pytest.raises(ForwardEvaluationBlocked, match="duplicate|consecutive"):
        validate_session_inventory(broken, fixture_root=root)


def test_all_inventory_hashes_and_protection_fail_closed(tmp_path: Path) -> None:
    root, inventory, _, _, _, shared = _fixture_bundle(tmp_path)
    changed = inventory.copy()
    changed.loc[0, "o2_score_sha256"] = "0" * 64
    with pytest.raises(ForwardEvaluationBlocked, match="hash mismatch"):
        validate_session_inventory(changed, fixture_root=root)
    protected = inventory.copy()
    protected.loc[0, "protected"] = True
    with pytest.raises(ForwardEvaluationBlocked, match="refuses protected"):
        validate_session_inventory(protected, fixture_root=root)
    partial = inventory.copy()
    partial.loc[0, "reliability_manifest_sha256"] = ""
    with pytest.raises(ForwardEvaluationBlocked, match="partial Reliability"):
        validate_session_inventory(partial, fixture_root=root)

    semantic = inventory.copy()
    manifest_path = Path(str(semantic.loc[0, "o2_manifest_path"]))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["model_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    semantic.loc[0, "o2_manifest_sha256"] = sha256_file(manifest_path)
    with pytest.raises(ForwardEvaluationBlocked, match="model_sha"):
        validate_session_inventory(semantic, fixture_root=root)

    missing_shared = dict(shared)
    missing_shared.pop("official_calendar")
    with pytest.raises(ForwardEvaluationBlocked, match="official_calendar"):
        validate_named_artifacts(missing_shared, fixture_root=root)


def test_o2_pass_mixed_and_fail_boundaries() -> None:
    positive = _metric_block()
    decision, _ = classify_o2_decision(positive, positive, positive, provenance_and_maturity_pass=True)
    assert decision == "O2_FORWARD_PASS"

    weak_half = _metric_block(pr=0.0)
    decision, _ = classify_o2_decision(positive, weak_half, positive, provenance_and_maturity_pass=True)
    assert decision == "O2_FORWARD_MIXED"

    nonpositive_core = _metric_block(spread=0.0)
    decision, _ = classify_o2_decision(nonpositive_core, positive, positive, provenance_and_maturity_pass=True)
    assert decision == "O2_FORWARD_FAIL"
    decision, _ = classify_o2_decision(positive, positive, positive, provenance_and_maturity_pass=False)
    assert decision == "O2_FORWARD_FAIL"

    nonfinite = dict(positive)
    nonfinite[O2_REQUIRED_METRICS[0]] = float("nan")
    decision, _ = classify_o2_decision(nonfinite, positive, positive, provenance_and_maturity_pass=True)
    assert decision == "O2_FORWARD_FAIL"


def test_local_pairwise_quality_ties_get_half_credit() -> None:
    target = np.array([1, 1, 0, 0])
    score = np.array([0.8, 0.5, 0.5, 0.2])
    quality = local_pairwise_quality(target, score)
    assert quality.tolist() == pytest.approx([1.0, 0.75, 0.75, 1.0])


def test_reliability_bucket_top40_and_quintile_metrics_are_deterministic() -> None:
    rows = []
    for rank in range(40):
        rows.append(
            {
                "ticker": f"T{rank:03d}",
                "binary_target": int((rank % 5) < (rank // 8 + 1)),
                "score": float(rank // 2),  # deliberate score ties
                "score_margin_reliability": float((rank % 9) + rank / 100.0),
            }
        )
    frame = pd.DataFrame(rows)
    row_a, metric_a = reliability_session_metrics(frame)
    row_b, metric_b = reliability_session_metrics(frame.sample(frac=1.0, random_state=7))
    assert metric_a == pytest.approx(metric_b)
    assert row_a.set_index("ticker")["reliability_quartile"].to_dict() == row_b.set_index("ticker")["reliability_quartile"].to_dict()
    assert set(row_a["reliability_quartile"]) == {1, 2, 3, 4}
    assert set(row_a["score_quintile"]) == {1, 2, 3, 4, 5}


def test_reliability_readiness_and_decision_boundaries() -> None:
    positive = _reliability_block()
    negative_half = _reliability_block()
    negative_half["mean_conditional_lift"] = 0.0
    negative_full = _reliability_block()
    negative_full["median_spearman"] = 0.0

    decision, checks = classify_reliability_decision(
        positive,
        positive,
        positive,
        sidecars_valid_and_complete=True,
        eligible_sessions=80,
        eligible_first_50=40,
        eligible_last_50=40,
    )
    assert decision == "RELIABILITY_FORWARD_PASS"
    assert checks["readiness_pass"] is True

    decision, _ = classify_reliability_decision(
        positive,
        positive,
        negative_half,
        sidecars_valid_and_complete=True,
        eligible_sessions=80,
        eligible_first_50=40,
        eligible_last_50=40,
    )
    assert decision == "RELIABILITY_FORWARD_INCONCLUSIVE"

    decision, _ = classify_reliability_decision(
        negative_full,
        positive,
        positive,
        sidecars_valid_and_complete=True,
        eligible_sessions=80,
        eligible_first_50=40,
        eligible_last_50=40,
    )
    assert decision == "RELIABILITY_FORWARD_FAIL"

    for counts in ((79, 40, 40), (80, 39, 41), (80, 40, 39)):
        decision, _ = classify_reliability_decision(
            positive,
            positive,
            positive,
            sidecars_valid_and_complete=True,
            eligible_sessions=counts[0],
            eligible_first_50=counts[1],
            eligible_last_50=counts[2],
        )
        assert decision == "RELIABILITY_FORWARD_INCONCLUSIVE_DATA"


def test_reliability_never_rescues_o2_and_o21_is_excluded() -> None:
    joint = joint_interpretation("O2_FORWARD_FAIL", "RELIABILITY_FORWARD_PASS")
    assert joint["controlling_alpha_decision"] == "O2_FORWARD_FAIL"
    assert joint["reliability_can_rescue_o2"] is False
    assert joint["o2_1_evaluated"] is False
    assert not any("o2_1" in key and key != "o2_1_evaluated" for key in joint)


def test_malformed_or_incomplete_outcomes_fail_closed(tmp_path: Path) -> None:
    root, inventory, scores, outcomes, _, _ = _fixture_bundle(tmp_path)
    sessions = validate_session_inventory(inventory, fixture_root=root)
    valid_scores = validate_o2_scores(scores, sessions)
    with pytest.raises(ForwardEvaluationBlocked, match="exactly match"):
        materialize_outcome_frame(valid_scores, outcomes.iloc[:-1])
    invalid = outcomes.copy()
    invalid.loc[0, "binary_target"] = np.nan
    invalid.loc[0, "unresolved_reason"] = ""
    with pytest.raises(ForwardEvaluationBlocked, match="explicit reason"):
        materialize_outcome_frame(valid_scores, invalid)
    invalid = outcomes.copy()
    invalid.loc[0, "source_sha256"] = "not-a-hash"
    with pytest.raises(ForwardEvaluationBlocked, match="source SHA"):
        materialize_outcome_frame(valid_scores, invalid)


def test_synthetic_one_shot_orders_manifest_marker_then_loader_and_is_deterministic(tmp_path: Path) -> None:
    root, inventory, scores, outcomes, reliability, shared = _fixture_bundle(tmp_path)
    events: list[str] = []

    def loader() -> pd.DataFrame:
        assert events == ["pre_outcome_manifest_written", "synthetic_marker_written"]
        return outcomes

    result = run_synthetic_forward_evaluation(
        output_dir=tmp_path / "output",
        marker_root=tmp_path / "marker",
        fixture_root=root,
        protocol_path=PROTOCOL,
        session_inventory=inventory,
        shared_artifacts=shared,
        o2_scores=scores,
        reliability=reliability,
        outcome_loader=loader,
        code_commit="synthetic-test-commit",
        event_hook=events.append,
    )
    assert events == ["pre_outcome_manifest_written", "synthetic_marker_written", "outcome_loader_returned"]
    assert result["status"] == "SYNTHETIC_FORWARD_100_EVALUATION_COMPLETE"
    assert result["o2"]["decision"] == "O2_FORWARD_PASS"
    assert Path(result["synthetic_marker_path"]).name == SYNTHETIC_MARKER
    assert not (tmp_path / "marker" / "FORWARD_OUTCOME_ACCESS_STARTED").exists()
    manifest = json.loads(Path(result["artifact_manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["runtime_flags"]["protected_forward_outcomes_accessed"] is False
    assert manifest["runtime_flags"]["o2_1_evaluated"] is False
    assert sha256_file(PROTOCOL) == PROTOCOL_SHA256

    with pytest.raises(ForwardEvaluationBlocked, match="already consumed"):
        run_synthetic_forward_evaluation(
            output_dir=tmp_path / "output",
            marker_root=tmp_path / "marker",
            fixture_root=root,
            protocol_path=PROTOCOL,
            session_inventory=inventory,
            shared_artifacts=shared,
            o2_scores=scores,
            reliability=reliability,
            outcome_loader=lambda: outcomes,
            code_commit="synthetic-test-commit",
        )


def test_crash_after_marker_leaves_synthetic_block_consumed(tmp_path: Path) -> None:
    root, inventory, scores, _, reliability, shared = _fixture_bundle(tmp_path)

    def crashing_loader() -> pd.DataFrame:
        raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError, match="synthetic crash"):
        run_synthetic_forward_evaluation(
            output_dir=tmp_path / "first-output",
            marker_root=tmp_path / "marker",
            fixture_root=root,
            protocol_path=PROTOCOL,
            session_inventory=inventory,
            shared_artifacts=shared,
            o2_scores=scores,
            reliability=reliability,
            outcome_loader=crashing_loader,
            code_commit="synthetic-test-commit",
        )
    marker = tmp_path / "marker" / SYNTHETIC_MARKER
    assert marker.is_file()

    with pytest.raises(ForwardEvaluationBlocked, match="already consumed"):
        run_synthetic_forward_evaluation(
            output_dir=tmp_path / "second-output",
            marker_root=tmp_path / "marker",
            fixture_root=root,
            protocol_path=PROTOCOL,
            session_inventory=inventory,
            shared_artifacts=shared,
            o2_scores=scores,
            reliability=reliability,
            outcome_loader=lambda: pytest.fail("loader must not be called"),
            code_commit="synthetic-test-commit",
        )


def test_protocol_hash_mismatch_blocks_before_loader(tmp_path: Path) -> None:
    root, inventory, scores, outcomes, reliability, shared = _fixture_bundle(tmp_path)
    called = False

    def loader() -> pd.DataFrame:
        nonlocal called
        called = True
        return outcomes

    with pytest.raises(ForwardEvaluationBlocked, match="protocol hash"):
        run_synthetic_forward_evaluation(
            output_dir=tmp_path / "output",
            marker_root=tmp_path / "marker",
            fixture_root=root,
            protocol_path=PROTOCOL,
            session_inventory=inventory,
            shared_artifacts=shared,
            o2_scores=scores,
            reliability=reliability,
            outcome_loader=loader,
            code_commit="synthetic-test-commit",
            expected_protocol_sha256="0" * 64,
        )
    assert called is False
