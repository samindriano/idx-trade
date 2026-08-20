from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_a_structural_replay.py"


def test_phase_a_runner_has_no_target_model_or_performance_execution_paths() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    forbidden = (
        "materialize_v4_target_ledger",
        "fit_v4_head",
        "score_v4_head",
        "evaluate_head_by_date_ca80",
        "evaluate_absolute_viability_gates",
        "evaluate_incremental_promotion_gates",
        "attach_consensus_alpha",
        "historical_result_root",
        "target_rank_h5",
        "target_rank_h10",
        "raw_return",
    )
    for token in forbidden:
        assert token not in source


def test_phase_a_runner_does_not_import_model_eval_modules() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "ranking_v4_3_model_eval" not in source
    assert "ranking_v4_3r_model_eval" not in source
