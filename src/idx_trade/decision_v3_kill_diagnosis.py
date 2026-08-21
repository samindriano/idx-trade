from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .decision_v2_failure_diagnosis import (
    FrozenStructuralLedgers,
    load_frozen_structural_ledgers,
)
from .decision_v2_structural_replay import sha256_file
from .decision_v2_structural_source import load_pinned_v4_x1_source_strict


EXPECTED_SESSIONS = 600
EXPECTED_SCORE_ROWS = 172_697
EXPECTED_UNDERFILLED_SESSIONS = 135
EXPECTED_VACANCY_DAYS = 307
EXPECTED_STRUCTURAL_MANIFEST_SHA256 = (
    "a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba"
)
EXPECTED_STRUCTURAL_PLAN_DIGEST = (
    "51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4"
)
EXPECTED_HISTORICAL_MANIFEST_SHA256 = (
    "6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205"
)
EXPECTED_HISTORICAL_SCORE_SHA256 = (
    "48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b"
)
PREREG_RELATIVE_PATH = Path(
    "docs/checkpoints/2026-08-21_DECISION_V3_KILL_DIAGNOSIS_PREREGISTRATION.md"
)
EXPECTED_PREREG_NORMALIZED_SHA256 = (
    "61153d2bf10b29c11c4cc7260da20d0812ac19ac4dc85ccf74665d4f26600434"
)


class DecisionV3KillDiagnosisError(RuntimeError):
    pass


@dataclass(frozen=True)
class DecisionV3KillDiagnosisResult:
    summary: dict[str, Any]
    global_fresh: pd.DataFrame
    severe_context: pd.DataFrame
    underfill_supply: pd.DataFrame
    block_summary: pd.DataFrame


def normalized_text_sha256(path: str | Path) -> str:
    text = Path(path).read_text(encoding="utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def verify_kill_diagnosis_prereg(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser().resolve() / PREREG_RELATIVE_PATH
    if not path.is_file():
        raise DecisionV3KillDiagnosisError(
            f"DECISION_V3_KILL_DIAGNOSIS_PREREG_MISSING:{path}"
        )
    actual = normalized_text_sha256(path)
    if actual != EXPECTED_PREREG_NORMALIZED_SHA256:
        raise DecisionV3KillDiagnosisError(
            "DECISION_V3_KILL_DIAGNOSIS_PREREG_SHA_MISMATCH:"
            f"{actual}!={EXPECTED_PREREG_NORMALIZED_SHA256}"
        )
    if "PREREGISTERED_DIAGNOSIS_NOT_IMPLEMENTED_NOT_RUN" not in path.read_text(
        encoding="utf-8"
    ):
        raise DecisionV3KillDiagnosisError(
            "DECISION_V3_KILL_DIAGNOSIS_PREREG_STATUS_CHANGED"
        )
    return path


def previous_rank_bin(rank: object | None) -> str:
    if rank is None or pd.isna(rank):
        return "ABSENT"
    value = int(rank)
    if value <= 20:
        return "LE20"
    if value <= 30:
        return "21_30"
    if value <= 50:
        return "31_50"
    if value <= 100:
        return "51_100"
    if value <= 200:
        return "101_200"
    return "GT200"


def _rank_lookup(score_frame: pd.DataFrame) -> dict[tuple[int, str], int]:
    dates = sorted(pd.Timestamp(value) for value in score_frame["date"].unique())
    index_by_date = {
        date.date().isoformat(): index for index, date in enumerate(dates)
    }
    return {
        (
            index_by_date[pd.Timestamp(row.date).date().isoformat()],
            str(row.ticker),
        ): int(row.rank_consensus)
        for row in score_frame.loc[
            :, ["date", "ticker", "rank_consensus"]
        ].itertuples(index=False)
    }


def _top10_by_index(score_frame: pd.DataFrame) -> dict[int, tuple[str, ...]]:
    dates = sorted(pd.Timestamp(value) for value in score_frame["date"].unique())
    result: dict[int, tuple[str, ...]] = {}
    for index, date in enumerate(dates):
        block = score_frame.loc[score_frame["date"].eq(date)]
        rows = block.loc[block["rank_consensus"].le(10)].sort_values(
            ["rank_consensus", "ticker"], kind="mergesort"
        )
        result[index] = tuple(rows["ticker"].astype(str).tolist())
    return result


def _held_start_by_index(
    ledgers: FrozenStructuralLedgers,
) -> dict[int, set[str]]:
    membership = ledgers.memberships
    targets_by_index = {
        int(index): set(group["ticker"].astype(str))
        for index, group in membership.groupby("index", sort=True)
    }
    result: dict[int, set[str]] = {0: set()}
    for index in range(1, EXPECTED_SESSIONS):
        result[index] = set(targets_by_index.get(index - 1, set()))
    return result


def _supply_counts(
    index: int,
    *,
    top10_by_index: dict[int, tuple[str, ...]],
    held_start: dict[int, set[str]],
    rank_lookup: dict[tuple[int, str], int],
) -> dict[str, int]:
    counts = {
        "LE20": 0,
        "21_30": 0,
        "31_50": 0,
        "51_100": 0,
        "101_200": 0,
        "GT200": 0,
        "ABSENT": 0,
    }
    for ticker in top10_by_index[index]:
        if ticker in held_start[index]:
            continue
        previous_rank = rank_lookup.get((index - 1, ticker)) if index > 0 else None
        counts[previous_rank_bin(previous_rank)] += 1
    return counts


def build_global_fresh_top10(
    score_frame: pd.DataFrame,
    ledgers: FrozenStructuralLedgers,
) -> pd.DataFrame:
    rank_lookup = _rank_lookup(score_frame)
    top10_by_index = _top10_by_index(score_frame)
    held_start = _held_start_by_index(ledgers)
    date_by_index = {
        int(row.index): str(row.date)
        for row in ledgers.sessions.itertuples(index=False)
    }
    rows: list[dict[str, Any]] = []
    for index in range(1, EXPECTED_SESSIONS):
        for ticker in top10_by_index[index]:
            if ticker in held_start[index]:
                continue
            current_rank = rank_lookup[(index, ticker)]
            previous_rank = rank_lookup.get((index - 1, ticker))
            next_evaluable = index < EXPECTED_SESSIONS - 1
            next_rank = (
                rank_lookup.get((index + 1, ticker)) if next_evaluable else None
            )
            rows.append(
                {
                    "index": index,
                    "date": date_by_index[index],
                    "block": index // 100 + 1,
                    "ticker": ticker,
                    "current_rank": current_rank,
                    "previous_rank": previous_rank,
                    "previous_rank_bin": previous_rank_bin(previous_rank),
                    "next_evaluable": next_evaluable,
                    "next_rank": next_rank,
                    "next_present": next_evaluable and next_rank is not None,
                    "next_top10": (
                        next_evaluable
                        and next_rank is not None
                        and next_rank <= 10
                    ),
                    "next_top20": (
                        next_evaluable
                        and next_rank is not None
                        and next_rank <= 20
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_severe_collapse_context(
    score_frame: pd.DataFrame,
    ledgers: FrozenStructuralLedgers,
) -> pd.DataFrame:
    rank_lookup = _rank_lookup(score_frame)
    top10_by_index = _top10_by_index(score_frame)
    held_start = _held_start_by_index(ledgers)
    sessions = ledgers.sessions.set_index("index", drop=False)
    severe = ledgers.states.loc[
        ledgers.states["kind"].eq("INCUMBENT")
        & ledgers.states["state"].eq("EXIT_PENDING_1")
        & pd.to_numeric(ledgers.states["current_rank"], errors="coerce").gt(50)
    ].copy()

    rows: list[dict[str, Any]] = []
    for row in severe.itertuples(index=False):
        index = int(row.index)
        ticker = str(row.ticker)
        supply = _supply_counts(
            index,
            top10_by_index=top10_by_index,
            held_start=held_start,
            rank_lookup=rank_lookup,
        )
        next_evaluable = index < EXPECTED_SESSIONS - 1
        next_rank = rank_lookup.get((index + 1, ticker)) if next_evaluable else None
        session = sessions.loc[index]
        core_supply = int(supply["LE20"])
        near_supply = int(supply["21_30"] + supply["31_50"])
        rows.append(
            {
                "index": index,
                "date": str(row.date),
                "block": index // 100 + 1,
                "ticker": ticker,
                "previous_rank": int(row.previous_rank),
                "current_rank": int(row.current_rank),
                "next_evaluable": next_evaluable,
                "next_rank": next_rank,
                "recovered_next_to_le20": (
                    next_evaluable
                    and next_rank is not None
                    and next_rank <= 20
                ),
                "v2_replacement_count": int(session["replacement_count"]),
                "v2_high_churn_ge3": int(session["replacement_count"]) >= 3,
                "core_supply": core_supply,
                "near_21_50_supply": near_supply,
                "distant_gt50_supply": int(
                    supply["51_100"]
                    + supply["101_200"]
                    + supply["GT200"]
                ),
                "previous_absent_supply": int(supply["ABSENT"]),
                "core_supply_ge1": core_supply >= 1,
                "core_plus_near_supply_ge1": core_supply + near_supply >= 1,
            }
        )
    return pd.DataFrame(rows)


def build_underfill_supply_decomposition(
    score_frame: pd.DataFrame,
    ledgers: FrozenStructuralLedgers,
) -> pd.DataFrame:
    rank_lookup = _rank_lookup(score_frame)
    top10_by_index = _top10_by_index(score_frame)
    held_start = _held_start_by_index(ledgers)
    underfilled = ledgers.sessions.loc[
        ledgers.sessions["capacity_state"].eq(
            "UNFILLED_NO_QUALIFIED_CHALLENGER"
        )
    ].copy()
    rows: list[dict[str, Any]] = []
    for session in underfilled.itertuples(index=False):
        index = int(session.index)
        supply = _supply_counts(
            index,
            top10_by_index=top10_by_index,
            held_start=held_start,
            rank_lookup=rank_lookup,
        )
        vacancies = int(session.unfilled_slots)
        core = int(supply["LE20"])
        near = int(supply["21_30"] + supply["31_50"])
        rows.append(
            {
                "index": index,
                "date": str(session.date),
                "block": index // 100 + 1,
                "vacancies": vacancies,
                "core_le20_supply": core,
                "previous_21_30_supply": int(supply["21_30"]),
                "previous_31_50_supply": int(supply["31_50"]),
                "previous_51_100_supply": int(supply["51_100"]),
                "previous_101_200_supply": int(supply["101_200"]),
                "previous_gt200_supply": int(supply["GT200"]),
                "previous_absent_supply": int(supply["ABSENT"]),
                "core_plus_21_50_supply": core + near,
                "core_plus_21_50_ge_vacancies": core + near >= vacancies,
            }
        )
    return pd.DataFrame(rows)


def _rate(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty:
        return None
    return float(frame[column].astype(bool).mean())


def _numeric_summary(series: pd.Series) -> dict[str, float | None]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if values.empty:
        return {
            "mean": None,
            "median": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "max": None,
        }
    return {
        "mean": float(values.mean()),
        "median": float(values.median()),
        "p75": float(values.quantile(0.75)),
        "p90": float(values.quantile(0.90)),
        "p95": float(values.quantile(0.95)),
        "max": float(values.max()),
    }


def _fresh_summary(frame: pd.DataFrame) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for label in ("LE20", "21_30", "31_50", "51_100", "101_200", "GT200", "ABSENT"):
        part = frame.loc[frame["previous_rank_bin"].eq(label)]
        evaluable = part.loc[part["next_evaluable"].astype(bool)]
        groups[label] = {
            "n": int(len(part)),
            "eligible_next_session": int(len(evaluable)),
            "next_top10_rate": _rate(evaluable, "next_top10"),
            "next_top20_rate": _rate(evaluable, "next_top20"),
            "next_absent_rate": (
                float((~evaluable["next_present"].astype(bool)).mean())
                if len(evaluable)
                else None
            ),
            "next_rank": _numeric_summary(evaluable["next_rank"]),
        }
    return {
        "n": int(len(frame)),
        "eligible_next_session": int(frame["next_evaluable"].astype(bool).sum()),
        "by_previous_rank_bin": groups,
    }


def build_block_summary(
    global_fresh: pd.DataFrame,
    severe_context: pd.DataFrame,
    underfill_supply: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for block in range(1, 7):
        fresh = global_fresh.loc[global_fresh["block"].eq(block)]
        for label in ("LE20", "21_30", "31_50", "51_100", "101_200", "GT200", "ABSENT"):
            part = fresh.loc[fresh["previous_rank_bin"].eq(label)]
            evaluable = part.loc[part["next_evaluable"].astype(bool)]
            rows.append(
                {
                    "analysis": "GLOBAL_FRESH_TOP10",
                    "block": block,
                    "stratum": label,
                    "n": int(len(part)),
                    "next_evaluable": int(len(evaluable)),
                    "next_top10_rate": _rate(evaluable, "next_top10"),
                    "next_top20_rate": _rate(evaluable, "next_top20"),
                    "high_churn_share": None,
                    "recovery_rate": None,
                    "adequate_supply_share": None,
                    "vacancy_days": None,
                }
            )

        severe = severe_context.loc[severe_context["block"].eq(block)]
        severe_eval = severe.loc[severe["next_evaluable"].astype(bool)]
        rows.append(
            {
                "analysis": "SEVERE_COLLAPSE_CONTEXT",
                "block": block,
                "stratum": "ALL_GT50",
                "n": int(len(severe)),
                "next_evaluable": int(len(severe_eval)),
                "next_top10_rate": None,
                "next_top20_rate": None,
                "high_churn_share": _rate(severe, "v2_high_churn_ge3"),
                "recovery_rate": _rate(severe_eval, "recovered_next_to_le20"),
                "adequate_supply_share": _rate(
                    severe, "core_plus_near_supply_ge1"
                ),
                "vacancy_days": None,
            }
        )

        underfill = underfill_supply.loc[underfill_supply["block"].eq(block)]
        rows.append(
            {
                "analysis": "UNDERFILL_SUPPLY",
                "block": block,
                "stratum": "ALL_UNDERFILLED",
                "n": int(len(underfill)),
                "next_evaluable": None,
                "next_top10_rate": None,
                "next_top20_rate": None,
                "high_churn_share": None,
                "recovery_rate": None,
                "adequate_supply_share": _rate(
                    underfill, "core_plus_21_50_ge_vacancies"
                ),
                "vacancy_days": int(underfill["vacancies"].sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_kill_diagnosis(
    global_fresh: pd.DataFrame,
    severe_context: pd.DataFrame,
    underfill_supply: pd.DataFrame,
    block_summary: pd.DataFrame,
) -> dict[str, Any]:
    severe_eval = severe_context.loc[
        severe_context["next_evaluable"].astype(bool)
    ]
    return {
        "schema_version": "decision_v3_kill_diagnosis_v1",
        "status": "COMPLETE_OUTCOME_BLIND_DECISION_V3_KILL_DIAGNOSIS",
        "source": {
            "historical_manifest_sha256": EXPECTED_HISTORICAL_MANIFEST_SHA256,
            "historical_score_sha256": EXPECTED_HISTORICAL_SCORE_SHA256,
            "structural_manifest_sha256": EXPECTED_STRUCTURAL_MANIFEST_SHA256,
            "structural_plan_digest": EXPECTED_STRUCTURAL_PLAN_DIGEST,
            "score_sessions": EXPECTED_SESSIONS,
            "score_rows": EXPECTED_SCORE_ROWS,
            "prereg_normalized_sha256": EXPECTED_PREREG_NORMALIZED_SHA256,
        },
        "guards": {
            "decision_v3_simulated": False,
            "alternative_decision_rule_simulated": False,
            "alternative_thresholds_tested": False,
            "decision_parameter_sweep": False,
            "realized_returns_loaded": False,
            "historical_pnl_computed": False,
            "h5_h10_decision_internals_used": False,
            "protected_or_fresh_forward_access": False,
            "provider_or_network_calls": False,
            "model_refit_or_retune": False,
        },
        "global_fresh_top10_persistence": _fresh_summary(global_fresh),
        "severe_collapse_replacement_context": {
            "n": int(len(severe_context)),
            "eligible_next_session": int(len(severe_eval)),
            "recovery_to_le20_rate": _rate(
                severe_eval, "recovered_next_to_le20"
            ),
            "v2_high_churn_ge3_share": _rate(
                severe_context, "v2_high_churn_ge3"
            ),
            "core_supply_ge1_share": _rate(
                severe_context, "core_supply_ge1"
            ),
            "core_plus_near_supply_ge1_share": _rate(
                severe_context, "core_plus_near_supply_ge1"
            ),
            "core_supply": _numeric_summary(severe_context["core_supply"]),
            "near_21_50_supply": _numeric_summary(
                severe_context["near_21_50_supply"]
            ),
        },
        "underfill_supply_decomposition": {
            "sessions": int(len(underfill_supply)),
            "vacancy_days": int(underfill_supply["vacancies"].sum()),
            "core_plus_21_50_ge_vacancies_share": _rate(
                underfill_supply, "core_plus_21_50_ge_vacancies"
            ),
            "sessions_core_plus_21_50_ge_vacancies": int(
                underfill_supply[
                    "core_plus_21_50_ge_vacancies"
                ].astype(bool).sum()
            ),
            "core_plus_21_50_supply": _numeric_summary(
                underfill_supply["core_plus_21_50_supply"]
            ),
            "vacancies": _numeric_summary(underfill_supply["vacancies"]),
        },
        "block_summary": block_summary.to_dict(orient="records"),
        "interpretation_boundary": (
            "Descriptive outcome-blind rank diagnosis only; reporting strata "
            "are not Decision thresholds and no V3 policy is executed."
        ),
        "next_session_boundary": {
            "last_frozen_index": 599,
            "terminal_rows_excluded_from_next_session_rates_only": True,
            "ticker_absence_on_real_next_session_counts_as_non_persistence": True,
        },
    }


def run_kill_diagnosis(
    *,
    structural_root: str | Path,
    historical_root: str | Path,
) -> DecisionV3KillDiagnosisResult:
    ledgers = load_frozen_structural_ledgers(structural_root)
    source = load_pinned_v4_x1_source_strict(historical_root)

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
    if int(underfill_supply["vacancies"].sum()) != EXPECTED_VACANCY_DAYS:
        raise DecisionV3KillDiagnosisError(
            "UNDERFILL_VACANCY_DAYS_CHANGED:"
            f"{int(underfill_supply['vacancies'].sum())}!={EXPECTED_VACANCY_DAYS}"
        )

    block_summary = build_block_summary(
        global_fresh, severe_context, underfill_supply
    )
    summary = summarize_kill_diagnosis(
        global_fresh, severe_context, underfill_supply, block_summary
    )
    return DecisionV3KillDiagnosisResult(
        summary=summary,
        global_fresh=global_fresh,
        severe_context=severe_context,
        underfill_supply=underfill_supply,
        block_summary=block_summary,
    )


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def write_kill_diagnosis_artifacts(
    result: DecisionV3KillDiagnosisResult,
    output_dir: str | Path,
) -> Path:
    destination = Path(output_dir).expanduser().resolve()
    if destination.exists():
        raise DecisionV3KillDiagnosisError(
            f"DECISION_V3_KILL_DIAGNOSIS_OUTPUT_EXISTS:{destination}"
        )
    staging = destination.with_name(destination.name + ".staging")
    if staging.exists():
        raise DecisionV3KillDiagnosisError(
            f"DECISION_V3_KILL_DIAGNOSIS_STAGING_EXISTS:{staging}"
        )
    staging.mkdir(parents=True, exist_ok=False)

    outputs: dict[str, bytes] = {
        "summary.json": (
            json.dumps(result.summary, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8"),
        "global_fresh_top10_persistence.csv": _csv_bytes(result.global_fresh),
        "severe_collapse_replacement_context.csv": _csv_bytes(
            result.severe_context
        ),
        "underfill_supply_decomposition.csv": _csv_bytes(
            result.underfill_supply
        ),
        "block_summary.csv": _csv_bytes(result.block_summary),
    }
    artifact_hashes: dict[str, str] = {}
    for name, content in outputs.items():
        (staging / name).write_bytes(content)
        artifact_hashes[name] = hashlib.sha256(content).hexdigest()

    manifest = {
        "schema_version": "decision_v3_kill_diagnosis_manifest_v1",
        "status": result.summary["status"],
        "source": result.summary["source"],
        "guards": result.summary["guards"],
        "artifacts": artifact_hashes,
    }
    manifest_path = staging / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    staging.rename(destination)
    return destination / "MANIFEST.json"
