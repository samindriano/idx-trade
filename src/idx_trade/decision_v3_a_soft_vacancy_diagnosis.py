from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any

import pandas as pd

from .decision_v3_failure_diagnosis import (
    DecisionV3FailureDiagnosisError,
    EXPECTED_PLAN_DIGEST,
    EXPECTED_SESSIONS,
    load_frozen_v3_structural_ledgers,
)
from .decision_v3_structural_source import (
    EXPECTED_SCORE_ROWS,
    EXPECTED_SOURCE_MANIFEST_SHA256,
    EXPECTED_SOURCE_SCORE_SHA256,
    canonical_json_sha256,
    load_pinned_v4_x1_source_strict,
    sha256_file,
)

CONTRACT_RELATIVE_PATH = Path("docs/specs/decision_v3_a_soft_vacancy_diagnosis_v1.json")
EXPECTED_CONTRACT_CANONICAL_SHA256 = (
    "f3d549cafb04fb66735f7a668f6094b800c5354b148361c5d9ba4d9773a57663"
)
EXPECTED_FAILURE_DIAGNOSIS_MANIFEST_SHA256 = (
    "73350606e408f987602575797f67474f83839256debee7e7b74496255beb0cab"
)
EXPECTED_QUALITY_SUPPLY_MANIFEST_SHA256 = (
    "4818ec82add5344115dfa82f1104947859d17a992ac817a7d3e0d5bdbfdd9e76"
)

A_VACANCY_REASON = "TIER_A_VACANCY_FILL"
A_SOFT_REASON = "SOFT_RANK_GAP_REPLACEMENT"
ENTRY_CLASS_BY_REASON = {
    A_VACANCY_REASON: "A_VACANCY",
    A_SOFT_REASON: "A_SOFT",
}


@dataclass(frozen=True)
class ASoftVacancyDiagnosisResult:
    summary: dict[str, Any]
    entry_diagnosis: pd.DataFrame
    stratified_next_severe: pd.DataFrame
    session_context_summary: pd.DataFrame


def verify_a_soft_vacancy_contract(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser().resolve() / CONTRACT_RELATIVE_PATH
    if not path.is_file():
        raise DecisionV3FailureDiagnosisError("A_SOFT_VACANCY_CONTRACT_MISSING")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3FailureDiagnosisError(
            "A_SOFT_VACANCY_CONTRACT_INVALID_JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise DecisionV3FailureDiagnosisError("A_SOFT_VACANCY_CONTRACT_NOT_OBJECT")
    actual = canonical_json_sha256(payload)
    if actual != EXPECTED_CONTRACT_CANONICAL_SHA256:
        raise DecisionV3FailureDiagnosisError(
            f"A_SOFT_VACANCY_CONTRACT_SHA_CHANGED:{actual}!={EXPECTED_CONTRACT_CANONICAL_SHA256}"
        )
    if payload.get("status") != "FROZEN_BEFORE_EXECUTION":
        raise DecisionV3FailureDiagnosisError("A_SOFT_VACANCY_CONTRACT_STATUS_CHANGED")
    if payload.get("execution_authorized") is not False:
        raise DecisionV3FailureDiagnosisError(
            "A_SOFT_VACANCY_CONTRACT_EXECUTION_FLAG_CHANGED"
        )
    forbidden = payload.get("forbidden", {})
    if not forbidden or not all(value is True for value in forbidden.values()):
        raise DecisionV3FailureDiagnosisError(
            "A_SOFT_VACANCY_CONTRACT_FORBIDDEN_GUARD_CHANGED"
        )
    return path


def verify_quality_supply_manifest(root: str | Path) -> Path:
    path = Path(root).expanduser().resolve() / "MANIFEST.json"
    if not path.is_file():
        raise DecisionV3FailureDiagnosisError("QUALITY_SUPPLY_PARENT_MANIFEST_MISSING")
    actual = sha256_file(path)
    if actual != EXPECTED_QUALITY_SUPPLY_MANIFEST_SHA256:
        raise DecisionV3FailureDiagnosisError(
            f"QUALITY_SUPPLY_PARENT_MANIFEST_SHA_CHANGED:{actual}!={EXPECTED_QUALITY_SUPPLY_MANIFEST_SHA256}"
        )
    return path


def _rank_maps(frame: pd.DataFrame) -> tuple[list[pd.Timestamp], dict[int, dict[str, int]]]:
    dates = sorted(pd.Timestamp(x).normalize() for x in frame["date"].drop_duplicates())
    maps: dict[int, dict[str, int]] = {}
    for index, day in enumerate(dates):
        block = frame.loc[frame["date"].eq(day), ["ticker", "rank_consensus"]]
        maps[index] = {
            str(row.ticker): int(row.rank_consensus)
            for row in block.itertuples(index=False)
        }
    return dates, maps


def consecutive_rank_run(
    *, ticker: str, entry_index: int, max_rank: int, rank_maps: dict[int, dict[str, int]]
) -> int:
    run = 0
    index = entry_index
    while index >= 0:
        rank = rank_maps.get(index, {}).get(ticker)
        if rank is None or rank > max_rank:
            break
        run += 1
        index -= 1
    return run


def _bucket_current_rank(rank: int) -> str:
    if rank <= 3:
        return "1-3"
    if rank <= 6:
        return "4-6"
    if rank <= 10:
        return "7-10"
    raise DecisionV3FailureDiagnosisError(f"A_ENTRY_CURRENT_RANK_NOT_TOP10:{rank}")


def _bucket_previous_rank(rank: int) -> str:
    if rank <= 10:
        return "1-10"
    if rank <= 20:
        return "11-20"
    raise DecisionV3FailureDiagnosisError(f"A_ENTRY_PREVIOUS_RANK_NOT_CORE:{rank}")


def _bucket_run(value: int) -> str:
    if value <= 1:
        return "1"
    if value == 2:
        return "2"
    return ">=3"


def _bucket_severe(value: int) -> str:
    if value <= 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return ">=3"


def _bucket_top10_overlap(value: int) -> str:
    if value <= 3:
        return "0-3"
    if value <= 6:
        return "4-6"
    return "7-10"


def _bucket_top20_overlap(value: int) -> str:
    if value <= 9:
        return "0-9"
    if value <= 14:
        return "10-14"
    return "15-20"


def _rate(series: pd.Series) -> float | None:
    clean = series.dropna()
    if clean.empty:
        return None
    return float(clean.astype(bool).mean())


def _numeric_summary(series: pd.Series) -> dict[str, float | int | None]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if values.empty:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
            "p90": None,
        }
    return {
        "count": int(values.size),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "p25": float(values.quantile(0.25)),
        "p75": float(values.quantile(0.75)),
        "p90": float(values.quantile(0.90)),
    }


def _cross_section_context(
    current: dict[str, int], previous: dict[str, int]
) -> dict[str, int]:
    current_top10 = {ticker for ticker, rank in current.items() if rank <= 10}
    previous_top10 = {ticker for ticker, rank in previous.items() if rank <= 10}
    current_top20 = {ticker for ticker, rank in current.items() if rank <= 20}
    previous_top20 = {ticker for ticker, rank in previous.items() if rank <= 20}
    prev_top10_to_gt50_or_absent = sum(
        current.get(ticker, 10**9) > 50 for ticker in previous_top10
    )
    return {
        "top10_overlap": len(current_top10 & previous_top10),
        "top20_overlap": len(current_top20 & previous_top20),
        "previous_top10_to_gt50_or_absent_count": int(prev_top10_to_gt50_or_absent),
    }


def _sell_reason_lookup(intents: pd.DataFrame) -> dict[tuple[int, str], str]:
    lookup: dict[tuple[int, str], str] = {}
    sells = intents.loc[intents["side"].eq("SELL_INTENT")]
    for row in sells.itertuples(index=False):
        key = (int(row.session_index), str(row.ticker))
        if key in lookup:
            raise DecisionV3FailureDiagnosisError(
                f"A_DIAGNOSIS_DUPLICATE_SELL_INTENT:{key}"
            )
        lookup[key] = str(row.reason)
    return lookup


def _state_lookup(states: pd.DataFrame) -> dict[tuple[int, str, str], str]:
    lookup: dict[tuple[int, str, str], str] = {}
    for row in states.itertuples(index=False):
        key = (int(row.session_index), str(row.ticker), str(row.kind))
        if key in lookup:
            raise DecisionV3FailureDiagnosisError(
                f"A_DIAGNOSIS_DUPLICATE_STATE:{key}"
            )
        lookup[key] = str(row.state)
    return lookup


def _build_entry_rows(
    *,
    ledgers: Any,
    rank_maps: dict[int, dict[str, int]],
    dates: list[pd.Timestamp],
) -> pd.DataFrame:
    sessions = ledgers.sessions.set_index(ledgers.sessions["session_index"].astype(int))
    sell_lookup = _sell_reason_lookup(ledgers.intents)
    states = _state_lookup(ledgers.states)

    entry_intents = ledgers.intents.loc[
        ledgers.intents["side"].eq("BUY_INTENT")
        & ledgers.intents["reason"].isin(list(ENTRY_CLASS_BY_REASON))
    ].copy()
    if entry_intents.empty:
        raise DecisionV3FailureDiagnosisError("A_DIAGNOSIS_NO_A_ENTRIES")

    spell_lookup: dict[tuple[int, str, str], Any] = {}
    for spell in ledgers.holding_spells.itertuples(index=False):
        reason = str(spell.entry_reason)
        if reason not in ENTRY_CLASS_BY_REASON:
            continue
        key = (int(spell.entry_index), str(spell.ticker), reason)
        if key in spell_lookup:
            raise DecisionV3FailureDiagnosisError(
                f"A_DIAGNOSIS_DUPLICATE_HOLDING_SPELL:{key}"
            )
        spell_lookup[key] = spell

    rows: list[dict[str, Any]] = []
    for intent in entry_intents.itertuples(index=False):
        entry_index = int(intent.session_index)
        ticker = str(intent.ticker)
        reason = str(intent.reason)
        entry_class = ENTRY_CLASS_BY_REASON[reason]
        if entry_index <= 0:
            raise DecisionV3FailureDiagnosisError(
                f"A_DIAGNOSIS_NONBOOTSTRAP_ENTRY_INDEX_INVALID:{entry_index}"
            )
        current_rank = rank_maps[entry_index].get(ticker)
        previous_rank = rank_maps[entry_index - 1].get(ticker)
        if current_rank is None or previous_rank is None:
            raise DecisionV3FailureDiagnosisError(
                f"A_DIAGNOSIS_A_ENTRY_RANK_MISSING:{entry_index}:{ticker}"
            )
        if current_rank > 10 or previous_rank > 20:
            raise DecisionV3FailureDiagnosisError(
                f"A_DIAGNOSIS_A_PERMISSION_MISMATCH:{entry_index}:{ticker}:{current_rank}:{previous_rank}"
            )
        if int(intent.rank_consensus) != int(current_rank):
            raise DecisionV3FailureDiagnosisError(
                f"A_DIAGNOSIS_INTENT_RANK_MISMATCH:{entry_index}:{ticker}"
            )

        spell = spell_lookup.get((entry_index, ticker, reason))
        if spell is None:
            raise DecisionV3FailureDiagnosisError(
                f"A_DIAGNOSIS_HOLDING_SPELL_MISSING:{entry_index}:{ticker}:{reason}"
            )
        completed = bool(spell.completed)
        right_censored = bool(spell.right_censored)
        exit_index = None if pd.isna(spell.exit_index) else int(spell.exit_index)
        if completed and exit_index is None:
            raise DecisionV3FailureDiagnosisError(
                f"A_DIAGNOSIS_COMPLETED_SPELL_WITHOUT_EXIT_INDEX:{entry_index}:{ticker}"
            )
        exit_reason = (
            "RIGHT_CENSORED"
            if right_censored
            else sell_lookup.get((int(exit_index), ticker), "MISSING_SELL_INTENT")
        )
        if completed and exit_reason == "MISSING_SELL_INTENT":
            raise DecisionV3FailureDiagnosisError(
                f"A_DIAGNOSIS_COMPLETED_SPELL_WITHOUT_SELL:{entry_index}:{ticker}"
            )

        session = sessions.loc[entry_index]
        context = _cross_section_context(rank_maps[entry_index], rank_maps[entry_index - 1])
        top10_run = consecutive_rank_run(
            ticker=ticker,
            entry_index=entry_index,
            max_rank=10,
            rank_maps=rank_maps,
        )
        top20_run = consecutive_rank_run(
            ticker=ticker,
            entry_index=entry_index,
            max_rank=20,
            rank_maps=rank_maps,
        )
        last3_indices = [i for i in range(max(0, entry_index - 2), entry_index + 1)]
        last3_top10_count = sum(
            rank_maps[i].get(ticker, 10**9) <= 10 for i in last3_indices
        )
        last3_top20_count = sum(
            rank_maps[i].get(ticker, 10**9) <= 20 for i in last3_indices
        )
        rank_t_minus_2 = (
            None if entry_index < 2 else rank_maps[entry_index - 2].get(ticker)
        )
        rank_t_minus_3 = (
            None if entry_index < 3 else rank_maps[entry_index - 3].get(ticker)
        )

        severe_count = int(session["severe_exit_count"])
        confirmed_count = int(session["confirmed_mild_exit_count"])
        universe_count = int(session["universe_exit_count"])
        mandatory_count = severe_count + confirmed_count + universe_count

        next_observable = entry_index < EXPECTED_SESSIONS - 1
        next_state = (
            None
            if not next_observable
            else states.get((entry_index + 1, ticker, "INCUMBENT"))
        )
        next_severe = (
            None
            if not next_observable
            else bool(next_state == "SEVERE_DETERIORATION_EXIT")
        )

        replacement_peer = (
            None if pd.isna(intent.replacement_peer) else str(intent.replacement_peer)
        )
        replacement_peer_rank = None
        replacement_gap = None
        if entry_class == "A_SOFT":
            if not replacement_peer:
                raise DecisionV3FailureDiagnosisError(
                    f"A_DIAGNOSIS_SOFT_REPLACEMENT_PEER_MISSING:{entry_index}:{ticker}"
                )
            replacement_peer_rank = rank_maps[entry_index].get(replacement_peer)
            if replacement_peer_rank is None:
                raise DecisionV3FailureDiagnosisError(
                    f"A_DIAGNOSIS_SOFT_REPLACEMENT_PEER_RANK_MISSING:{entry_index}:{replacement_peer}"
                )
            replacement_gap = int(replacement_peer_rank) - int(current_rank)
            if replacement_gap < 5:
                raise DecisionV3FailureDiagnosisError(
                    f"A_DIAGNOSIS_SOFT_GAP_INVALID:{entry_index}:{ticker}:{replacement_gap}"
                )

        rows.append(
            {
                "ticker": ticker,
                "entry_index": entry_index,
                "entry_date": pd.Timestamp(dates[entry_index]).strftime("%Y-%m-%d"),
                "entry_block": entry_index // 100 + 1,
                "entry_class": entry_class,
                "entry_reason": reason,
                "current_rank": int(current_rank),
                "previous_rank": int(previous_rank),
                "rank_delta_current_minus_previous": int(current_rank) - int(previous_rank),
                "rank_t_minus_2": rank_t_minus_2,
                "rank_t_minus_3": rank_t_minus_3,
                "top10_run_including_entry": int(top10_run),
                "top20_run_including_entry": int(top20_run),
                "last3_top10_count": int(last3_top10_count),
                "last3_top20_count": int(last3_top20_count),
                "severe_exit_count": severe_count,
                "confirmed_mild_exit_count": confirmed_count,
                "universe_exit_count": universe_count,
                "mandatory_exit_count": mandatory_count,
                "entry_on_severe_session": severe_count > 0,
                "top10_overlap": int(context["top10_overlap"]),
                "top20_overlap": int(context["top20_overlap"]),
                "previous_top10_to_gt50_or_absent_count": int(
                    context["previous_top10_to_gt50_or_absent_count"]
                ),
                "replacement_peer": replacement_peer,
                "replacement_peer_rank": replacement_peer_rank,
                "soft_rank_gap": replacement_gap,
                "duration_sessions": int(spell.duration_sessions),
                "one_session_holding": int(spell.duration_sessions) == 1,
                "completed": completed,
                "right_censored": right_censored,
                "exit_index": exit_index,
                "exit_reason": exit_reason,
                "eventual_severe_exit": (
                    None if not completed else bool(exit_reason == "SEVERE_DETERIORATION_EXIT")
                ),
                "next_session_observable": next_observable,
                "next_session_state": next_state,
                "next_session_severe_exit": next_severe,
                "current_rank_bucket": _bucket_current_rank(int(current_rank)),
                "previous_rank_bucket": _bucket_previous_rank(int(previous_rank)),
                "top10_run_bucket": _bucket_run(int(top10_run)),
                "top20_run_bucket": _bucket_run(int(top20_run)),
                "severe_exit_count_bucket": _bucket_severe(severe_count),
                "top10_overlap_bucket": _bucket_top10_overlap(int(context["top10_overlap"])),
                "top20_overlap_bucket": _bucket_top20_overlap(int(context["top20_overlap"])),
            }
        )

    result = pd.DataFrame(rows).sort_values(
        ["entry_index", "entry_class", "current_rank", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
    expected_counts = {"A_VACANCY": 721, "A_SOFT": 422}
    actual_counts = result["entry_class"].value_counts().to_dict()
    if actual_counts != expected_counts:
        raise DecisionV3FailureDiagnosisError(
            f"A_DIAGNOSIS_ENTRY_COUNTS_CHANGED:{actual_counts}!={expected_counts}"
        )
    return result


def _context_row(block: pd.DataFrame, *, population: str, entry_class: str) -> dict[str, Any]:
    completed = block.loc[block["completed"].astype(bool)]
    next_obs = block.loc[block["next_session_observable"].astype(bool)]
    return {
        "population": population,
        "entry_class": entry_class,
        "entries": int(len(block)),
        "completed_entries": int(len(completed)),
        "next_session_observable_entries": int(len(next_obs)),
        "next_session_severe_rate": _rate(next_obs["next_session_severe_exit"]),
        "eventual_severe_rate_completed_only": _rate(completed["eventual_severe_exit"]),
        "one_session_holding_rate": _rate(block["one_session_holding"]),
        "current_rank_mean": None if block.empty else float(block["current_rank"].mean()),
        "current_rank_median": None if block.empty else float(block["current_rank"].median()),
        "previous_rank_mean": None if block.empty else float(block["previous_rank"].mean()),
        "previous_rank_median": None if block.empty else float(block["previous_rank"].median()),
        "rank_delta_mean": None if block.empty else float(block["rank_delta_current_minus_previous"].mean()),
        "top10_run_mean": None if block.empty else float(block["top10_run_including_entry"].mean()),
        "top10_run_median": None if block.empty else float(block["top10_run_including_entry"].median()),
        "top10_run_ge2_share": None if block.empty else float((block["top10_run_including_entry"] >= 2).mean()),
        "top10_run_ge3_share": None if block.empty else float((block["top10_run_including_entry"] >= 3).mean()),
        "top20_run_mean": None if block.empty else float(block["top20_run_including_entry"].mean()),
        "top20_run_median": None if block.empty else float(block["top20_run_including_entry"].median()),
        "last3_top10_count_mean": None if block.empty else float(block["last3_top10_count"].mean()),
        "last3_top20_count_mean": None if block.empty else float(block["last3_top20_count"].mean()),
        "severe_session_share": None if block.empty else float(block["entry_on_severe_session"].mean()),
        "severe_exit_count_mean": None if block.empty else float(block["severe_exit_count"].mean()),
        "mandatory_exit_count_mean": None if block.empty else float(block["mandatory_exit_count"].mean()),
        "top10_overlap_mean": None if block.empty else float(block["top10_overlap"].mean()),
        "top20_overlap_mean": None if block.empty else float(block["top20_overlap"].mean()),
        "previous_top10_to_gt50_or_absent_mean": None if block.empty else float(block["previous_top10_to_gt50_or_absent_count"].mean()),
        "duration_mean": None if block.empty else float(block["duration_sessions"].mean()),
        "duration_median": None if block.empty else float(block["duration_sessions"].median()),
    }


def _build_session_context_summary(entries: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for population, mask in (
        ("ALL", pd.Series(True, index=entries.index)),
        ("SEVERE_ONLY", entries["entry_on_severe_session"].astype(bool)),
    ):
        population_block = entries.loc[mask]
        for entry_class in ("A_SOFT", "A_VACANCY"):
            block = population_block.loc[population_block["entry_class"].eq(entry_class)]
            rows.append(_context_row(block, population=population, entry_class=entry_class))
    return pd.DataFrame(rows)


def _stratified_pair_rows(entries: pd.DataFrame) -> pd.DataFrame:
    dimensions = {
        "current_rank": "current_rank_bucket",
        "previous_rank": "previous_rank_bucket",
        "top10_run_including_entry": "top10_run_bucket",
        "top20_run_including_entry": "top20_run_bucket",
        "severe_exit_count": "severe_exit_count_bucket",
        "top10_overlap": "top10_overlap_bucket",
        "top20_overlap": "top20_overlap_bucket",
    }
    rows: list[dict[str, Any]] = []
    for population, population_block in (
        ("ALL", entries),
        ("SEVERE_ONLY", entries.loc[entries["entry_on_severe_session"].astype(bool)]),
    ):
        for dimension, column in dimensions.items():
            for stratum in sorted(population_block[column].dropna().astype(str).unique()):
                cell = population_block.loc[population_block[column].astype(str).eq(stratum)]
                soft = cell.loc[cell["entry_class"].eq("A_SOFT")]
                vacancy = cell.loc[cell["entry_class"].eq("A_VACANCY")]
                soft_next = soft.loc[soft["next_session_observable"].astype(bool)]
                vacancy_next = vacancy.loc[vacancy["next_session_observable"].astype(bool)]
                soft_completed = soft.loc[soft["completed"].astype(bool)]
                vacancy_completed = vacancy.loc[vacancy["completed"].astype(bool)]
                soft_rate = _rate(soft_next["next_session_severe_exit"])
                vacancy_rate = _rate(vacancy_next["next_session_severe_exit"])
                rows.append(
                    {
                        "population": population,
                        "dimension": dimension,
                        "stratum": stratum,
                        "a_soft_entries": int(len(soft)),
                        "a_vacancy_entries": int(len(vacancy)),
                        "a_soft_next_observable": int(len(soft_next)),
                        "a_vacancy_next_observable": int(len(vacancy_next)),
                        "a_soft_next_severe_rate": soft_rate,
                        "a_vacancy_next_severe_rate": vacancy_rate,
                        "soft_minus_vacancy_next_severe_rate_gap": (
                            None
                            if soft_rate is None or vacancy_rate is None
                            else float(soft_rate - vacancy_rate)
                        ),
                        "a_soft_completed": int(len(soft_completed)),
                        "a_vacancy_completed": int(len(vacancy_completed)),
                        "a_soft_eventual_severe_rate": _rate(
                            soft_completed["eventual_severe_exit"]
                        ),
                        "a_vacancy_eventual_severe_rate": _rate(
                            vacancy_completed["eventual_severe_exit"]
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _class_summary(entries: pd.DataFrame, entry_class: str) -> dict[str, Any]:
    block = entries.loc[entries["entry_class"].eq(entry_class)]
    next_obs = block.loc[block["next_session_observable"].astype(bool)]
    completed = block.loc[block["completed"].astype(bool)]
    return {
        "entries": int(len(block)),
        "next_session_observable_entries": int(len(next_obs)),
        "next_session_severe_rate": _rate(next_obs["next_session_severe_exit"]),
        "completed_entries": int(len(completed)),
        "eventual_severe_rate_completed_only": _rate(completed["eventual_severe_exit"]),
        "one_session_holding_rate": _rate(block["one_session_holding"]),
        "duration_sessions": _numeric_summary(block["duration_sessions"]),
        "candidate_evidence": {
            "current_rank": _numeric_summary(block["current_rank"]),
            "previous_rank": _numeric_summary(block["previous_rank"]),
            "rank_delta_current_minus_previous": _numeric_summary(
                block["rank_delta_current_minus_previous"]
            ),
            "top10_run_including_entry": _numeric_summary(
                block["top10_run_including_entry"]
            ),
            "top20_run_including_entry": _numeric_summary(
                block["top20_run_including_entry"]
            ),
            "last3_top10_count": _numeric_summary(block["last3_top10_count"]),
            "last3_top20_count": _numeric_summary(block["last3_top20_count"]),
        },
        "session_context": {
            "severe_session_share": float(block["entry_on_severe_session"].mean()),
            "severe_exit_count": _numeric_summary(block["severe_exit_count"]),
            "mandatory_exit_count": _numeric_summary(block["mandatory_exit_count"]),
            "top10_overlap": _numeric_summary(block["top10_overlap"]),
            "top20_overlap": _numeric_summary(block["top20_overlap"]),
            "previous_top10_to_gt50_or_absent_count": _numeric_summary(
                block["previous_top10_to_gt50_or_absent_count"]
            ),
        },
    }


def _direction_summary(stratified: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for population in ("ALL", "SEVERE_ONLY"):
        pop = stratified.loc[stratified["population"].eq(population)]
        by_dimension: dict[str, Any] = {}
        for dimension, block in pop.groupby("dimension", sort=True):
            comparable = block.dropna(subset=["soft_minus_vacancy_next_severe_rate_gap"])
            gaps = pd.to_numeric(
                comparable["soft_minus_vacancy_next_severe_rate_gap"], errors="coerce"
            ).dropna()
            by_dimension[str(dimension)] = {
                "comparable_strata": int(len(gaps)),
                "soft_lower_next_severe_strata": int((gaps < 0).sum()),
                "soft_equal_next_severe_strata": int((gaps == 0).sum()),
                "soft_higher_next_severe_strata": int((gaps > 0).sum()),
                "median_soft_minus_vacancy_gap": (
                    None if gaps.empty else float(gaps.median())
                ),
            }
        result[population] = by_dimension
    return result


def run_a_soft_vacancy_diagnosis(
    *,
    structural_root: str | Path,
    historical_root: str | Path,
    quality_supply_root: str | Path,
) -> ASoftVacancyDiagnosisResult:
    ledgers = load_frozen_v3_structural_ledgers(structural_root)
    source = load_pinned_v4_x1_source_strict(historical_root)
    verify_quality_supply_manifest(quality_supply_root)

    if ledgers.manifest.get("status") != "DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_REJECT":
        raise DecisionV3FailureDiagnosisError("A_DIAGNOSIS_PARENT_STATUS_CHANGED")
    if ledgers.manifest.get("plan_digest") != EXPECTED_PLAN_DIGEST:
        raise DecisionV3FailureDiagnosisError("A_DIAGNOSIS_PARENT_PLAN_CHANGED")
    if len(source.frame) != EXPECTED_SCORE_ROWS:
        raise DecisionV3FailureDiagnosisError("A_DIAGNOSIS_SOURCE_ROW_COUNT_CHANGED")

    dates, rank_maps = _rank_maps(source.frame)
    if len(dates) != EXPECTED_SESSIONS:
        raise DecisionV3FailureDiagnosisError("A_DIAGNOSIS_SOURCE_SESSION_COUNT_CHANGED")

    entries = _build_entry_rows(
        ledgers=ledgers,
        rank_maps=rank_maps,
        dates=dates,
    )
    stratified = _stratified_pair_rows(entries)
    context = _build_session_context_summary(entries)

    all_soft = entries.loc[entries["entry_class"].eq("A_SOFT")]
    all_vacancy = entries.loc[entries["entry_class"].eq("A_VACANCY")]
    severe_soft = all_soft.loc[all_soft["entry_on_severe_session"].astype(bool)]
    severe_vacancy = all_vacancy.loc[all_vacancy["entry_on_severe_session"].astype(bool)]

    def next_rate(block: pd.DataFrame) -> float | None:
        obs = block.loc[block["next_session_observable"].astype(bool)]
        return _rate(obs["next_session_severe_exit"])

    summary = {
        "status": "COMPLETE_OUTCOME_BLIND_DECISION_V3_A_SOFT_VACANCY_DIAGNOSIS",
        "scientific_boundary": {
            "decision_v4_implemented_or_replayed": False,
            "alternative_rule_or_wait_policy_simulated": False,
            "hypothetical_portfolio_or_pnl_computed": False,
            "returns_or_outcomes_accessed": False,
            "protected_or_fresh_forward_accessed": False,
            "model_refit_or_retune": False,
            "provider_or_network_called": False,
        },
        "pins": {
            "parent_status": ledgers.manifest.get("status"),
            "parent_plan_digest": EXPECTED_PLAN_DIGEST,
            "failure_diagnosis_manifest_sha256": EXPECTED_FAILURE_DIAGNOSIS_MANIFEST_SHA256,
            "quality_supply_diagnosis_manifest_sha256": EXPECTED_QUALITY_SUPPLY_MANIFEST_SHA256,
            "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
            "source_score_sha256": EXPECTED_SOURCE_SCORE_SHA256,
            "sessions": EXPECTED_SESSIONS,
            "rows": EXPECTED_SCORE_ROWS,
        },
        "overall": {
            "A_SOFT": _class_summary(entries, "A_SOFT"),
            "A_VACANCY": _class_summary(entries, "A_VACANCY"),
            "next_session_severe_rate_gap_soft_minus_vacancy": (
                None
                if next_rate(all_soft) is None or next_rate(all_vacancy) is None
                else float(next_rate(all_soft) - next_rate(all_vacancy))
            ),
        },
        "severe_session_only": {
            "A_SOFT_entries": int(len(severe_soft)),
            "A_VACANCY_entries": int(len(severe_vacancy)),
            "A_SOFT_next_session_severe_rate": next_rate(severe_soft),
            "A_VACANCY_next_session_severe_rate": next_rate(severe_vacancy),
            "next_session_severe_rate_gap_soft_minus_vacancy": (
                None
                if next_rate(severe_soft) is None or next_rate(severe_vacancy) is None
                else float(next_rate(severe_soft) - next_rate(severe_vacancy))
            ),
        },
        "stratified_direction": _direction_summary(stratified),
        "interpretation_guard": (
            "A-soft versus A-vacancy comparisons are descriptive structural statistics on the "
            "already-observed frozen V3 trajectory. Fixed rank/persistence/stress strata are "
            "reporting bins, not candidate Decision V4 thresholds, and no causal effect is claimed."
        ),
    }
    return ASoftVacancyDiagnosisResult(
        summary=summary,
        entry_diagnosis=entries,
        stratified_next_severe=stratified,
        session_context_summary=context,
    )


def write_a_soft_vacancy_artifacts(
    result: ASoftVacancyDiagnosisResult,
    output_dir: str | Path,
) -> Path:
    out = Path(output_dir).expanduser().resolve()
    stage = out.parent / f".{out.name}.staging"
    if out.exists():
        raise DecisionV3FailureDiagnosisError(f"A_DIAGNOSIS_OUTPUT_EXISTS:{out}")
    if stage.exists():
        raise DecisionV3FailureDiagnosisError(f"A_DIAGNOSIS_STAGING_EXISTS:{stage}")
    stage.mkdir(parents=True, exist_ok=False)
    try:
        summary_path = stage / "summary.json"
        summary_path.write_text(
            json.dumps(result.summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result.entry_diagnosis.to_csv(stage / "a_entry_diagnosis.csv", index=False)
        result.stratified_next_severe.to_csv(
            stage / "stratified_next_severe.csv", index=False
        )
        result.session_context_summary.to_csv(
            stage / "session_context_summary.csv", index=False
        )
        artifact_names = [
            "summary.json",
            "a_entry_diagnosis.csv",
            "stratified_next_severe.csv",
            "session_context_summary.csv",
        ]
        artifacts = {name: sha256_file(stage / name) for name in artifact_names}
        manifest = {
            "status": result.summary["status"],
            "contract_canonical_sha256": EXPECTED_CONTRACT_CANONICAL_SHA256,
            "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
            "source_score_sha256": EXPECTED_SOURCE_SCORE_SHA256,
            "parent_plan_digest": EXPECTED_PLAN_DIGEST,
            "quality_supply_diagnosis_manifest_sha256": EXPECTED_QUALITY_SUPPLY_MANIFEST_SHA256,
            "scientific_boundary": result.summary["scientific_boundary"],
            "artifacts": artifacts,
        }
        manifest_path = stage / "MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        stage.rename(out)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    return out / "MANIFEST.json"
