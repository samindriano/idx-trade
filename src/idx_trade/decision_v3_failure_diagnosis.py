from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .decision_v3_structural_source import sha256_file


EXPECTED_PARENT_STATUS = "DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_REJECT"
EXPECTED_PLAN_DIGEST = "1759d1b21849197257c638f6ac23ae0d3cdd320e34da820b4cc188d533931579"
EXPECTED_SESSIONS = 600
EXPECTED_SOURCE_MANIFEST_SHA256 = "6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205"
EXPECTED_SOURCE_SCORE_SHA256 = "48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b"
EXPECTED_ARTIFACT_SHA256 = {
    "summary.json": "62259398f18d5e92fce9160b32ec4697a852fbfe49fbafbdd25cdd92d9524bda",
    "decision_intent_ledger.csv": "e3f45b9881ef1bd3ca750e18150de7b4f2d3c22e86257f0b6ab12c0175b4d82a",
    "decision_membership_ledger.csv": "710b1b5a6bb77deaff6d3de4d09f83d655065050ddeda651d616732224a7198f",
    "decision_session_ledger.csv": "9d4c5f1d62d15701c1491631a90eba48b8dfba04e5d1d14bd871db819a015cba",
    "decision_state_ledger.csv": "44dd3bd39815fb0c02fe3987a73f71531212dc8a8a6aedbff73d57e624ae9e73",
    "fold_boundary_transitions.csv": "1e711a3a7d55903bf224c203db13437b475b165a78e29c970e9bbcb5506918fa",
    "holding_spells.csv": "20e358e0b9b4a95359bd89157b67cb41a5fe43602576c789a8eb954d49854552",
}

ENTRY_TIER_BY_REASON = {
    "TIER_A_VACANCY_FILL": "A",
    "TIER_B_VACANCY_FILL": "B",
    "TIER_C_RESIDUAL_VACANCY_FILL": "C",
    "SOFT_RANK_GAP_REPLACEMENT": "A_SOFT",
}
MANDATORY_EXIT_REASONS = {
    "SEVERE_DETERIORATION_EXIT",
    "CONFIRMED_MILD_DETERIORATION_EXIT",
    "UNIVERSE_EXIT",
}
VACANCY_FILL_REASONS = {
    "TIER_A_VACANCY_FILL",
    "TIER_B_VACANCY_FILL",
    "TIER_C_RESIDUAL_VACANCY_FILL",
}


class DecisionV3FailureDiagnosisError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrozenV3StructuralLedgers:
    root: Path
    manifest: dict[str, Any]
    summary: dict[str, Any]
    sessions: pd.DataFrame
    memberships: pd.DataFrame
    intents: pd.DataFrame
    states: pd.DataFrame
    holding_spells: pd.DataFrame
    fold_boundaries: pd.DataFrame


@dataclass(frozen=True)
class DecisionV3FailureDiagnosisResult:
    summary: dict[str, Any]
    severe_exit_sessions: pd.DataFrame
    entry_lifecycle: pd.DataFrame
    block_summary: pd.DataFrame


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3FailureDiagnosisError(f"INVALID_JSON:{path}") from exc
    if not isinstance(payload, dict):
        raise DecisionV3FailureDiagnosisError(f"JSON_NOT_OBJECT:{path}")
    return payload


def _safe_rate(series: pd.Series) -> float | None:
    return None if len(series) == 0 else float(series.astype(bool).mean())


def _numeric_summary(series: pd.Series) -> dict[str, float | int | None]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if values.empty:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "max": None,
        }
    return {
        "count": int(len(values)),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "p75": float(values.quantile(0.75)),
        "p90": float(values.quantile(0.90)),
        "p95": float(values.quantile(0.95)),
        "max": float(values.max()),
    }


def load_frozen_v3_structural_ledgers(root: str | Path) -> FrozenV3StructuralLedgers:
    root_path = Path(root).expanduser().resolve()
    manifest_path = root_path / "MANIFEST.json"
    if not manifest_path.is_file():
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_MANIFEST_MISSING")
    manifest = _read_json(manifest_path)
    if manifest.get("status") != EXPECTED_PARENT_STATUS:
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_STATUS_CHANGED")
    if manifest.get("plan_digest") != EXPECTED_PLAN_DIGEST:
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_PLAN_DIGEST_CHANGED")

    source = manifest.get("source")
    if not isinstance(source, dict):
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_SOURCE_MAP_MISSING")
    if source.get("manifest_sha256") != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_SOURCE_MANIFEST_CHANGED")
    if source.get("score_sha256") != EXPECTED_SOURCE_SCORE_SHA256:
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_SOURCE_SCORE_CHANGED")
    if int(source.get("sessions", -1)) != EXPECTED_SESSIONS:
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_SOURCE_SESSION_COUNT_CHANGED")

    artifacts = manifest.get("artifacts")
    if artifacts != EXPECTED_ARTIFACT_SHA256:
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_ARTIFACT_MAP_CHANGED")
    for name, expected_sha in EXPECTED_ARTIFACT_SHA256.items():
        path = root_path / name
        if not path.is_file():
            raise DecisionV3FailureDiagnosisError(f"V3_STRUCTURAL_ARTIFACT_MISSING:{name}")
        actual = sha256_file(path)
        if actual != expected_sha:
            raise DecisionV3FailureDiagnosisError(
                f"V3_STRUCTURAL_ARTIFACT_SHA_MISMATCH:{name}:{actual}!={expected_sha}"
            )

    guards = manifest.get("guards")
    if not isinstance(guards, dict):
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_GUARDS_MISSING")
    required_guard_values = {
        "outcome_blind": True,
        "post_replay_independent_integrity_passed": True,
        "network_or_provider_called": False,
        "protected_or_fresh_forward_accessed": False,
        "returns_or_pnl_accessed": False,
        "score_regenerated": False,
        "fold_reset": False,
        "preroll": False,
    }
    if any(guards.get(key) != value for key, value in required_guard_values.items()):
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_GUARD_CHANGED")

    summary = _read_json(root_path / "summary.json")
    if summary.get("status") != EXPECTED_PARENT_STATUS:
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_SUMMARY_STATUS_CHANGED")

    sessions = pd.read_csv(root_path / "decision_session_ledger.csv")
    memberships = pd.read_csv(root_path / "decision_membership_ledger.csv")
    intents = pd.read_csv(root_path / "decision_intent_ledger.csv")
    states = pd.read_csv(root_path / "decision_state_ledger.csv")
    holding_spells = pd.read_csv(root_path / "holding_spells.csv")
    fold_boundaries = pd.read_csv(root_path / "fold_boundary_transitions.csv")

    if len(sessions) != EXPECTED_SESSIONS:
        raise DecisionV3FailureDiagnosisError(
            f"V3_STRUCTURAL_SESSION_COUNT_CHANGED:{len(sessions)}"
        )
    if sessions["session_index"].astype(int).tolist() != list(range(EXPECTED_SESSIONS)):
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_SESSION_INDEX_NOT_EXACT")
    if sessions["date"].duplicated().any():
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_DUPLICATE_SESSION_DATE")
    bootstrap = sessions["bootstrap"].astype(bool).tolist()
    if bootstrap != ([True] + [False] * (EXPECTED_SESSIONS - 1)):
        raise DecisionV3FailureDiagnosisError("V3_STRUCTURAL_BOOTSTRAP_PATH_CHANGED")

    return FrozenV3StructuralLedgers(
        root=root_path,
        manifest=manifest,
        summary=summary,
        sessions=sessions,
        memberships=memberships,
        intents=intents,
        states=states,
        holding_spells=holding_spells,
        fold_boundaries=fold_boundaries,
    )


def build_severe_exit_session_diagnosis(
    ledgers: FrozenV3StructuralLedgers,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for session in ledgers.sessions.loc[~ledgers.sessions["bootstrap"].astype(bool)].itertuples(index=False):
        index = int(session.session_index)
        severe = int(session.severe_exit_count)
        confirmed = int(session.confirmed_mild_exit_count)
        universe = int(session.universe_exit_count)
        tier_a = int(session.tier_a_vacancy_fill_count)
        tier_b = int(session.tier_b_vacancy_fill_count)
        tier_c = int(session.tier_c_vacancy_fill_count)
        soft = int(session.tier_a_soft_replacement_count)
        vacancy_fill = tier_a + tier_b + tier_c
        mandatory = severe + confirmed + universe
        replacement = int(session.replacement_count)
        rows.append(
            {
                "session_index": index,
                "date": str(session.date),
                "block": index // 100 + 1,
                "replacement_count": replacement,
                "high_churn_ge3": replacement >= 3,
                "severe_exit_count": severe,
                "confirmed_mild_exit_count": confirmed,
                "universe_exit_count": universe,
                "mandatory_exit_count": mandatory,
                "tier_a_vacancy_fill_count": tier_a,
                "tier_b_vacancy_fill_count": tier_b,
                "tier_c_vacancy_fill_count": tier_c,
                "vacancy_fill_count": vacancy_fill,
                "soft_replacement_count": soft,
                "severe_exit_session": severe > 0,
                "severe_and_vacancy_fill_overlap": severe > 0 and vacancy_fill > 0,
                "severe_and_soft_replacement_overlap": severe > 0 and soft > 0,
                "mandatory_exit_and_vacancy_fill_overlap": mandatory > 0 and vacancy_fill > 0,
                "target_size": int(session.target_size),
                "target_rank_mean": float(session.target_rank_mean),
                "target_rank_gt20_count": int(session.target_rank_gt20_count),
            }
        )
    return pd.DataFrame(rows)


def build_entry_tier_lifecycle_diagnosis(
    ledgers: FrozenV3StructuralLedgers,
) -> pd.DataFrame:
    sessions_by_index = ledgers.sessions.set_index(ledgers.sessions["session_index"].astype(int))
    state_lookup: dict[tuple[int, str, str], Any] = {}
    state_rank_lookup: dict[tuple[int, str, str], tuple[Any, Any]] = {}
    for row in ledgers.states.itertuples(index=False):
        key = (int(row.session_index), str(row.ticker), str(row.kind))
        state_lookup[key] = str(row.state)
        state_rank_lookup[key] = (row.current_rank, row.previous_rank)

    sell_reason_lookup: dict[tuple[int, str], str] = {}
    sells = ledgers.intents.loc[ledgers.intents["side"].eq("SELL_INTENT")]
    for row in sells.itertuples(index=False):
        key = (int(row.session_index), str(row.ticker))
        if key in sell_reason_lookup:
            raise DecisionV3FailureDiagnosisError(f"V3_DIAGNOSIS_DUPLICATE_SELL_INTENT:{key}")
        sell_reason_lookup[key] = str(row.reason)

    rows: list[dict[str, Any]] = []
    for spell in ledgers.holding_spells.itertuples(index=False):
        reason = str(spell.entry_reason)
        tier = ENTRY_TIER_BY_REASON.get(reason)
        if tier is None:
            continue
        entry_index = int(spell.entry_index)
        ticker = str(spell.ticker)
        duration = int(spell.duration_sessions)
        completed = bool(spell.completed)
        right_censored = bool(spell.right_censored)
        exit_index = None if pd.isna(spell.exit_index) else int(spell.exit_index)
        exit_reason = "RIGHT_CENSORED" if right_censored else sell_reason_lookup.get((exit_index, ticker), "MISSING_SELL_INTENT")
        if completed and exit_reason == "MISSING_SELL_INTENT":
            raise DecisionV3FailureDiagnosisError(
                f"V3_DIAGNOSIS_COMPLETED_SPELL_WITHOUT_SELL:{ticker}:{exit_index}"
            )

        challenger_key = (entry_index, ticker, "CHALLENGER")
        challenger_state = state_lookup.get(challenger_key)
        entry_current_rank, entry_previous_rank = state_rank_lookup.get(challenger_key, (None, None))

        next_index = entry_index + 1
        next_key = (next_index, ticker, "INCUMBENT")
        if next_index >= EXPECTED_SESSIONS:
            next_state = "RIGHT_CENSORED_END_OF_REPLAY"
            next_rank = None
        else:
            next_state = state_lookup.get(next_key, "NOT_HELD_AT_NEXT_SESSION_START")
            next_rank = state_rank_lookup.get(next_key, (None, None))[0]

        entry_session = sessions_by_index.loc[entry_index]
        exit_replacement = None
        exit_high_churn = None
        if exit_index is not None and exit_index in sessions_by_index.index:
            exit_session = sessions_by_index.loc[exit_index]
            exit_replacement = int(exit_session["replacement_count"])
            exit_high_churn = exit_replacement >= 3

        rows.append(
            {
                "ticker": ticker,
                "entry_index": entry_index,
                "entry_date": str(spell.entry_date),
                "entry_block": entry_index // 100 + 1,
                "entry_reason": reason,
                "entry_tier": tier,
                "challenger_state": challenger_state,
                "entry_current_rank": None if pd.isna(entry_current_rank) else int(entry_current_rank),
                "entry_previous_rank": None if pd.isna(entry_previous_rank) else int(entry_previous_rank),
                "duration_sessions": duration,
                "one_session_holding": duration == 1,
                "completed": completed,
                "right_censored": right_censored,
                "exit_index": exit_index,
                "exit_date": None if pd.isna(spell.exit_date) else str(spell.exit_date),
                "exit_reason": exit_reason,
                "eventual_severe_exit": exit_reason == "SEVERE_DETERIORATION_EXIT",
                "next_session_state": next_state,
                "next_session_rank": None if pd.isna(next_rank) else int(next_rank),
                "next_session_severe_exit": next_state == "SEVERE_DETERIORATION_EXIT",
                "entry_session_replacement_count": int(entry_session["replacement_count"]),
                "entry_session_high_churn_ge3": int(entry_session["replacement_count"]) >= 3,
                "exit_session_replacement_count": exit_replacement,
                "exit_session_high_churn_ge3": exit_high_churn,
            }
        )
    return pd.DataFrame(rows)


def _tier_lifecycle_summary(frame: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for tier in ("A", "B", "C", "A_SOFT"):
        part = frame.loc[frame["entry_tier"].eq(tier)].copy()
        if part.empty:
            result[tier] = {"entries": 0}
            continue
        completed = part.loc[part["completed"].astype(bool)]
        result[tier] = {
            "entries": int(len(part)),
            "completed_spells": int(len(completed)),
            "duration_sessions": _numeric_summary(part["duration_sessions"]),
            "one_session_holding_share": _safe_rate(completed["one_session_holding"]) if len(completed) else None,
            "next_session_severe_exit_count": int(part["next_session_severe_exit"].sum()),
            "next_session_severe_exit_rate": _safe_rate(part["next_session_severe_exit"]),
            "eventual_severe_exit_count": int(part["eventual_severe_exit"].sum()),
            "eventual_severe_exit_rate": _safe_rate(part["eventual_severe_exit"]),
            "entry_high_churn_share": _safe_rate(part["entry_session_high_churn_ge3"]),
        }
    return result


def _max_consecutive_true(values: list[bool]) -> int:
    best = 0
    current = 0
    for value in values:
        if value:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _exit_refill_summary(frame: pd.DataFrame) -> dict[str, Any]:
    severe = frame.loc[frame["severe_exit_session"].astype(bool)].copy()
    nonsevere = frame.loc[~frame["severe_exit_session"].astype(bool)].copy()
    total_replacements = int(frame["replacement_count"].sum())
    severe_replacements = int(severe["replacement_count"].sum())
    return {
        "transitions": int(len(frame)),
        "severe_exit_total": int(frame["severe_exit_count"].sum()),
        "severe_exit_sessions": int(len(severe)),
        "severe_exit_session_share": float(len(severe) / len(frame)) if len(frame) else None,
        "severe_exit_count_on_severe_sessions": _numeric_summary(severe["severe_exit_count"]),
        "sessions_with_severe_exit_count_ge2": int(severe["severe_exit_count"].ge(2).sum()),
        "sessions_with_severe_exit_count_ge3": int(severe["severe_exit_count"].ge(3).sum()),
        "max_consecutive_severe_exit_sessions": _max_consecutive_true(frame["severe_exit_session"].astype(bool).tolist()),
        "high_churn_share_on_severe_exit_sessions": _safe_rate(severe["high_churn_ge3"]) if len(severe) else None,
        "high_churn_share_without_severe_exit": _safe_rate(nonsevere["high_churn_ge3"]) if len(nonsevere) else None,
        "severe_and_vacancy_fill_overlap_sessions": int(severe["severe_and_vacancy_fill_overlap"].sum()),
        "share_severe_sessions_with_vacancy_fill": _safe_rate(severe["severe_and_vacancy_fill_overlap"]) if len(severe) else None,
        "severe_and_soft_replacement_overlap_sessions": int(severe["severe_and_soft_replacement_overlap"].sum()),
        "share_severe_sessions_with_soft_replacement": _safe_rate(severe["severe_and_soft_replacement_overlap"]) if len(severe) else None,
        "vacancy_fill_count_on_severe_exit_sessions": int(severe["vacancy_fill_count"].sum()),
        "soft_replacement_count_on_severe_exit_sessions": int(severe["soft_replacement_count"].sum()),
        "replacement_count_on_severe_exit_sessions": severe_replacements,
        "share_observed_replacements_on_severe_exit_sessions": (
            float(severe_replacements / total_replacements) if total_replacements else None
        ),
        "interpretation": "Overlap/incidence only; counts do not estimate a counterfactual causal effect of removing severe exits.",
    }


def _group_transition_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"transitions": 0}
    return {
        "transitions": int(len(frame)),
        "mean_replacements": float(frame["replacement_count"].mean()),
        "high_churn_share": _safe_rate(frame["high_churn_ge3"]),
        "severe_exits_per_transition": float(frame["severe_exit_count"].mean()),
        "severe_exit_session_share": _safe_rate(frame["severe_exit_session"]),
        "vacancy_fills_per_transition": float(frame["vacancy_fill_count"].mean()),
        "soft_replacements_per_transition": float(frame["soft_replacement_count"].mean()),
        "severe_refill_overlap_share": _safe_rate(frame["severe_and_vacancy_fill_overlap"]),
    }


def build_block_mechanism_summary(
    ledgers: FrozenV3StructuralLedgers,
    severe_sessions: pd.DataFrame,
    lifecycle: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for block in range(1, 7):
        transitions = severe_sessions.loc[severe_sessions["block"].eq(block)].copy()
        sessions = ledgers.sessions.loc[((ledgers.sessions["session_index"].astype(int) // 100) + 1).eq(block)]
        entries = lifecycle.loc[lifecycle["entry_block"].eq(block)].copy()
        row: dict[str, Any] = {
            "block": block,
            "sessions": int(len(sessions)),
            "transitions": int(len(transitions)),
            "mean_replacements": float(transitions["replacement_count"].mean()) if len(transitions) else None,
            "high_churn_share": _safe_rate(transitions["high_churn_ge3"]) if len(transitions) else None,
            "severe_exit_total": int(transitions["severe_exit_count"].sum()),
            "severe_exit_session_share": _safe_rate(transitions["severe_exit_session"]) if len(transitions) else None,
            "severe_refill_overlap_sessions": int(transitions["severe_and_vacancy_fill_overlap"].sum()),
            "vacancy_fill_total": int(transitions["vacancy_fill_count"].sum()),
            "soft_replacement_total": int(transitions["soft_replacement_count"].sum()),
            "mean_target_rank": float(sessions["target_rank_mean"].mean()) if len(sessions) else None,
            "mean_target_size": float(sessions["target_size"].mean()) if len(sessions) else None,
        }
        for tier in ("A", "B", "C", "A_SOFT"):
            part = entries.loc[entries["entry_tier"].eq(tier)]
            prefix = tier.lower().replace("_", "_")
            row[f"tier_{prefix}_entries"] = int(len(part))
            row[f"tier_{prefix}_one_session_share"] = _safe_rate(part.loc[part["completed"].astype(bool), "one_session_holding"]) if len(part.loc[part["completed"].astype(bool)]) else None
            row[f"tier_{prefix}_next_severe_rate"] = _safe_rate(part["next_session_severe_exit"]) if len(part) else None
        rows.append(row)
    return pd.DataFrame(rows)


def _stress_block_summary(
    severe_sessions: pd.DataFrame,
    lifecycle: pd.DataFrame,
) -> dict[str, Any]:
    stress = severe_sessions.loc[severe_sessions["block"].isin([3, 6])]
    reference = severe_sessions.loc[severe_sessions["block"].isin([1, 2, 4, 5])]
    stress_life = lifecycle.loc[lifecycle["entry_block"].isin([3, 6])]
    ref_life = lifecycle.loc[lifecycle["entry_block"].isin([1, 2, 4, 5])]

    def tier_c_metrics(frame: pd.DataFrame) -> dict[str, Any]:
        part = frame.loc[frame["entry_tier"].eq("C")]
        return {
            "tier_c_entries": int(len(part)),
            "tier_c_next_severe_rate": _safe_rate(part["next_session_severe_exit"]) if len(part) else None,
            "tier_c_one_session_share": _safe_rate(part.loc[part["completed"].astype(bool), "one_session_holding"]) if len(part.loc[part["completed"].astype(bool)]) else None,
        }

    return {
        "stress_blocks_3_6": {**_group_transition_metrics(stress), **tier_c_metrics(stress_life)},
        "reference_blocks_1_2_4_5": {**_group_transition_metrics(reference), **tier_c_metrics(ref_life)},
        "interpretation": "Side-by-side descriptive mechanism intensity only; no regime rule or block-specific policy is authorized.",
    }


def run_failure_mechanism_diagnosis(
    structural_root: str | Path,
) -> DecisionV3FailureDiagnosisResult:
    ledgers = load_frozen_v3_structural_ledgers(structural_root)
    severe_sessions = build_severe_exit_session_diagnosis(ledgers)
    lifecycle = build_entry_tier_lifecycle_diagnosis(ledgers)
    blocks = build_block_mechanism_summary(ledgers, severe_sessions, lifecycle)

    summary = {
        "schema_version": "decision_v3_failure_mechanism_diagnosis_v1",
        "status": "COMPLETE_OUTCOME_BLIND_DECISION_V3_FAILURE_MECHANISM_DIAGNOSIS",
        "source": {
            "parent_status": EXPECTED_PARENT_STATUS,
            "parent_plan_digest": EXPECTED_PLAN_DIGEST,
            "parent_artifact_sha256": EXPECTED_ARTIFACT_SHA256,
            "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
            "source_score_sha256": EXPECTED_SOURCE_SCORE_SHA256,
            "sessions": EXPECTED_SESSIONS,
        },
        "guards": {
            "decision_v3_structural_replay_rerun": False,
            "alternative_decision_rule_simulated": False,
            "alternative_thresholds_tested": False,
            "decision_parameter_sweep": False,
            "counterfactual_policy_simulated": False,
            "historical_alpha_source_accessed": False,
            "realized_returns_loaded": False,
            "historical_pnl_computed": False,
            "protected_or_fresh_forward_access": False,
            "model_refit_or_retune": False,
            "provider_or_network_calls": False,
            "successor_decision_implemented": False,
            "paper_or_live_activation": False,
        },
        "severe_exit_clustering_and_refill_overlap": _exit_refill_summary(severe_sessions),
        "entry_tier_lifecycle": _tier_lifecycle_summary(lifecycle),
        "block_mechanism_summary": blocks.to_dict(orient="records"),
        "block_3_6_vs_reference": _stress_block_summary(severe_sessions, lifecycle),
        "interpretation_boundary": (
            "Descriptive mechanism diagnosis only. Existing rank/tier/churn labels are inherited reporting strata, not successor Decision thresholds or tuning gates."
        ),
    }
    return DecisionV3FailureDiagnosisResult(
        summary=summary,
        severe_exit_sessions=severe_sessions,
        entry_lifecycle=lifecycle,
        block_summary=blocks,
    )


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def write_failure_diagnosis_artifacts(
    result: DecisionV3FailureDiagnosisResult,
    output_dir: str | Path,
) -> Path:
    destination = Path(output_dir).expanduser().resolve()
    if destination.exists():
        raise DecisionV3FailureDiagnosisError(f"OUTPUT_ALREADY_EXISTS:{destination}")
    staging = destination.with_name(destination.name + ".staging")
    if staging.exists():
        raise DecisionV3FailureDiagnosisError(f"STAGING_ALREADY_EXISTS:{staging}")
    staging.mkdir(parents=True, exist_ok=False)

    outputs: dict[str, bytes] = {
        "summary.json": (json.dumps(result.summary, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        "severe_exit_session_diagnosis.csv": _csv_bytes(result.severe_exit_sessions),
        "entry_tier_lifecycle_diagnosis.csv": _csv_bytes(result.entry_lifecycle),
        "block_mechanism_summary.csv": _csv_bytes(result.block_summary),
    }
    hashes: dict[str, str] = {}
    for name, content in outputs.items():
        (staging / name).write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()

    manifest = {
        "schema_version": "decision_v3_failure_mechanism_diagnosis_manifest_v1",
        "status": result.summary["status"],
        "source": result.summary["source"],
        "guards": result.summary["guards"],
        "artifacts": hashes,
    }
    manifest_path = staging / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(destination)
    return destination / "MANIFEST.json"
