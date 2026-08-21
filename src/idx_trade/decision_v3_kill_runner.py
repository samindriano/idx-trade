from __future__ import annotations

from pathlib import Path

from .decision_v2_failure_diagnosis import load_frozen_structural_ledgers
from .decision_v3_kill_diagnosis import (
    EXPECTED_HISTORICAL_MANIFEST_SHA256,
    EXPECTED_HISTORICAL_SCORE_SHA256,
    EXPECTED_SCORE_ROWS,
    EXPECTED_STRUCTURAL_PLAN_DIGEST,
    EXPECTED_UNDERFILLED_SESSIONS,
    EXPECTED_VACANCY_DAYS,
    DecisionV3KillDiagnosisError,
    DecisionV3KillDiagnosisResult,
    build_block_summary,
    build_global_fresh_top10,
    build_severe_collapse_context,
    build_underfill_supply_decomposition,
    summarize_kill_diagnosis,
)
from .decision_v3_kill_source import load_consensus_only_pinned_source


def run_kill_diagnosis_safe(
    *,
    structural_root: str | Path,
    historical_root: str | Path,
) -> DecisionV3KillDiagnosisResult:
    ledgers = load_frozen_structural_ledgers(structural_root)
    source = load_consensus_only_pinned_source(historical_root)

    if ledgers.manifest.get("plan_digest") != EXPECTED_STRUCTURAL_PLAN_DIGEST:
        raise DecisionV3KillDiagnosisError("STRUCTURAL_PLAN_DIGEST_CHANGED")
    if len(source.frame) != EXPECTED_SCORE_ROWS:
        raise DecisionV3KillDiagnosisError("HISTORICAL_SCORE_ROWS_CHANGED")

    global_fresh = build_global_fresh_top10(source.frame, ledgers)
    severe_context = build_severe_collapse_context(source.frame, ledgers)
    underfill_supply = build_underfill_supply_decomposition(source.frame, ledgers)

    if len(underfill_supply) != EXPECTED_UNDERFILLED_SESSIONS:
        raise DecisionV3KillDiagnosisError(
            "UNDERFILLED_SESSION_COUNT_CHANGED:"
            f"{len(underfill_supply)}!={EXPECTED_UNDERFILLED_SESSIONS}"
        )
    vacancy_days = int(underfill_supply["vacancies"].sum())
    if vacancy_days != EXPECTED_VACANCY_DAYS:
        raise DecisionV3KillDiagnosisError(
            "UNDERFILL_VACANCY_DAYS_CHANGED:"
            f"{vacancy_days}!={EXPECTED_VACANCY_DAYS}"
        )

    block_summary = build_block_summary(
        global_fresh, severe_context, underfill_supply
    )
    summary = summarize_kill_diagnosis(
        global_fresh, severe_context, underfill_supply, block_summary
    )
    source_summary = summary["source"]
    if source_summary["historical_manifest_sha256"] != EXPECTED_HISTORICAL_MANIFEST_SHA256:
        raise DecisionV3KillDiagnosisError("SUMMARY_HISTORICAL_MANIFEST_CHANGED")
    if source_summary["historical_score_sha256"] != EXPECTED_HISTORICAL_SCORE_SHA256:
        raise DecisionV3KillDiagnosisError("SUMMARY_HISTORICAL_SCORE_CHANGED")

    return DecisionV3KillDiagnosisResult(
        summary=summary,
        global_fresh=global_fresh,
        severe_context=severe_context,
        underfill_supply=underfill_supply,
        block_summary=block_summary,
    )
