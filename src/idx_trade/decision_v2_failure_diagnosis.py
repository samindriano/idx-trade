from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .decision_v2_structural_replay import sha256_file
from .decision_v2_structural_source import load_pinned_v4_x1_source_strict


EXPECTED_STRUCTURAL_MANIFEST_SHA256 = (
    "a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba"
)
EXPECTED_STRUCTURAL_STATUS = "DECISION_V2_MINIMAL_STRUCTURAL_REJECT"
EXPECTED_PLAN_DIGEST = (
    "51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4"
)
EXPECTED_SCORE_MANIFEST_SHA256 = (
    "6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205"
)
EXPECTED_SCORE_SHA256 = (
    "48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b"
)
EXPECTED_SESSIONS = 600
EXPECTED_SCORE_ROWS = 172_697

REQUIRED_ARTIFACTS = (
    "summary.json",
    "decision_session_ledger.csv",
    "decision_membership_ledger.csv",
    "decision_intent_ledger.csv",
    "decision_state_ledger.csv",
    "holding_spells.csv",
    "fold_boundary_transitions.csv",
)


class DecisionV2FailureDiagnosisError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrozenStructuralLedgers:
    root: Path
    manifest: dict[str, Any]
    sessions: pd.DataFrame
    memberships: pd.DataFrame
    intents: pd.DataFrame
    states: pd.DataFrame


@dataclass(frozen=True)
class FailureDiagnosisResult:
    summary: dict[str, Any]
    exit_pending: pd.DataFrame
    rejected_fresh: pd.DataFrame
    churn_attribution: pd.DataFrame
    block_summary: pd.DataFrame


def descriptive_rank_bin(rank: object | None) -> str:
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


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV2FailureDiagnosisError(f"INVALID_JSON:{path}") from exc
    if not isinstance(payload, dict):
        raise DecisionV2FailureDiagnosisError(f"JSON_NOT_OBJECT:{path}")
    return payload


def load_frozen_structural_ledgers(root: str | Path) -> FrozenStructuralLedgers:
    root_path = Path(root).expanduser().resolve()
    manifest_path = root_path / "MANIFEST.json"
    if not manifest_path.is_file():
        raise DecisionV2FailureDiagnosisError("STRUCTURAL_MANIFEST_MISSING")
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != EXPECTED_STRUCTURAL_MANIFEST_SHA256:
        raise DecisionV2FailureDiagnosisError(
            "STRUCTURAL_MANIFEST_SHA_MISMATCH:"
            f"{actual_manifest_sha}!={EXPECTED_STRUCTURAL_MANIFEST_SHA256}"
        )
    manifest = _read_json(manifest_path)
    if manifest.get("status") != EXPECTED_STRUCTURAL_STATUS:
        raise DecisionV2FailureDiagnosisError("STRUCTURAL_STATUS_CHANGED")
    if manifest.get("plan_digest") != EXPECTED_PLAN_DIGEST:
        raise DecisionV2FailureDiagnosisError("STRUCTURAL_PLAN_DIGEST_CHANGED")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise DecisionV2FailureDiagnosisError("STRUCTURAL_ARTIFACT_MAP_MISSING")

    for name in REQUIRED_ARTIFACTS:
        path = root_path / name
        if not path.is_file():
            raise DecisionV2FailureDiagnosisError(f"STRUCTURAL_ARTIFACT_MISSING:{name}")
        expected_sha = artifacts.get(name)
        if not isinstance(expected_sha, str):
            raise DecisionV2FailureDiagnosisError(f"STRUCTURAL_ARTIFACT_SHA_MISSING:{name}")
        actual_sha = sha256_file(path)
        if actual_sha != expected_sha:
            raise DecisionV2FailureDiagnosisError(
                f"STRUCTURAL_ARTIFACT_SHA_MISMATCH:{name}:{actual_sha}!={expected_sha}"
            )

    summary = _read_json(root_path / "summary.json")
    if summary.get("status") != EXPECTED_STRUCTURAL_STATUS:
        raise DecisionV2FailureDiagnosisError("STRUCTURAL_SUMMARY_STATUS_CHANGED")

    sessions = pd.read_csv(root_path / "decision_session_ledger.csv")
    memberships = pd.read_csv(root_path / "decision_membership_ledger.csv")
    intents = pd.read_csv(root_path / "decision_intent_ledger.csv")
    states = pd.read_csv(root_path / "decision_state_ledger.csv")

    if len(sessions) != EXPECTED_SESSIONS:
        raise DecisionV2FailureDiagnosisError(
            f"STRUCTURAL_SESSION_COUNT_CHANGED:{len(sessions)}"
        )
    expected_indices = list(range(EXPECTED_SESSIONS))
    if sessions["index"].astype(int).tolist() != expected_indices:
        raise DecisionV2FailureDiagnosisError("STRUCTURAL_SESSION_INDEX_NOT_EXACT")
    if sessions["date"].duplicated().any():
        raise DecisionV2FailureDiagnosisError("STRUCTURAL_DUPLICATE_SESSION_DATE")

    return FrozenStructuralLedgers(
        root=root_path,
        manifest=manifest,
        sessions=sessions,
        memberships=memberships,
        intents=intents,
        states=states,
    )


def _rank_lookup(score_frame: pd.DataFrame) -> dict[tuple[int, str], int]:
    dates = sorted(pd.Timestamp(x) for x in score_frame["date"].unique())
    index_by_date = {d.date().isoformat(): i for i, d in enumerate(dates)}
    return {
        (index_by_date[pd.Timestamp(row.date).date().isoformat()], str(row.ticker)): int(row.rank_consensus)
        for row in score_frame.loc[:, ["date", "ticker", "rank_consensus"]].itertuples(index=False)
    }


def _state_lookup(states: pd.DataFrame) -> dict[tuple[int, str, str], str]:
    return {
        (int(row.index), str(row.ticker), str(row.kind)): str(row.state)
        for row in states.itertuples(index=False)
    }


def _safe_rate(series: pd.Series) -> float | None:
    return None if len(series) == 0 else float(series.astype(bool).mean())


def _numeric_summary(series: pd.Series) -> dict[str, float | None]:
    x = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if x.empty:
        return {"mean": None, "median": None, "p75": None, "p90": None, "p95": None, "max": None}
    return {
        "mean": float(x.mean()),
        "median": float(x.median()),
        "p75": float(x.quantile(0.75)),
        "p90": float(x.quantile(0.90)),
        "p95": float(x.quantile(0.95)),
        "max": float(x.max()),
    }


def build_exit_pending_diagnosis(
    ledgers: FrozenStructuralLedgers,
    rank_lookup: dict[tuple[int, str], int],
) -> pd.DataFrame:
    state_lookup = _state_lookup(ledgers.states)
    pending = ledgers.states.loc[
        ledgers.states["kind"].eq("INCUMBENT")
        & ledgers.states["state"].eq("EXIT_PENDING_1")
    ].copy()
    rows: list[dict[str, Any]] = []
    for row in pending.itertuples(index=False):
        idx = int(row.index)
        ticker = str(row.ticker)
        current_rank = int(row.current_rank)
        previous_rank = int(row.previous_rank) if not pd.isna(row.previous_rank) else None
        next_rank = rank_lookup.get((idx + 1, ticker)) if idx + 1 < EXPECTED_SESSIONS else None
        next_state = state_lookup.get((idx + 1, ticker, "INCUMBENT")) if idx + 1 < EXPECTED_SESSIONS else None
        rows.append(
            {
                "index": idx,
                "date": str(row.date),
                "block": idx // 100 + 1,
                "ticker": ticker,
                "previous_rank": previous_rank,
                "current_rank": current_rank,
                "current_rank_bin": descriptive_rank_bin(current_rank),
                "rank_jump": current_rank - previous_rank if previous_rank is not None else None,
                "rank_excess_over20": current_rank - 20,
                "next_rank": next_rank,
                "next_rank_bin": descriptive_rank_bin(next_rank),
                "next_present": next_rank is not None,
                "next_top10": next_rank is not None and next_rank <= 10,
                "next_top20": next_rank is not None and next_rank <= 20,
                "recovered_to_le20": next_rank is not None and next_rank <= 20,
                "next_incumbent_state": next_state,
                "confirmed_exit_next": next_state == "CONFIRMED_EXIT",
            }
        )
    return pd.DataFrame(rows)


def build_rejected_fresh_diagnosis(
    ledgers: FrozenStructuralLedgers,
    rank_lookup: dict[tuple[int, str], int],
) -> pd.DataFrame:
    underfilled = ledgers.sessions.loc[
        ledgers.sessions["capacity_state"].eq("UNFILLED_NO_QUALIFIED_CHALLENGER")
    ].copy()
    underfilled_indices = set(underfilled["index"].astype(int))
    states = ledgers.states.loc[
        ledgers.states["index"].astype(int).isin(underfilled_indices)
        & ledgers.states["kind"].eq("CHALLENGER")
        & ledgers.states["state"].isin(
            ["UNCONFIRMED_PREVIOUS_GT_THRESHOLD", "UNCONFIRMED_PREVIOUS_ABSENT"]
        )
    ].copy()
    slots = {
        int(row.index): int(row.unfilled_slots)
        for row in underfilled.itertuples(index=False)
    }
    rejected_counts = states.groupby(states["index"].astype(int)).size().to_dict()
    rows: list[dict[str, Any]] = []
    for row in states.itertuples(index=False):
        idx = int(row.index)
        ticker = str(row.ticker)
        previous_rank = int(row.previous_rank) if not pd.isna(row.previous_rank) else None
        current_rank = int(row.current_rank)
        next_rank = rank_lookup.get((idx + 1, ticker)) if idx + 1 < EXPECTED_SESSIONS else None
        rows.append(
            {
                "index": idx,
                "date": str(row.date),
                "block": idx // 100 + 1,
                "ticker": ticker,
                "previous_rank": previous_rank,
                "previous_rank_bin": descriptive_rank_bin(previous_rank),
                "current_rank": current_rank,
                "state": str(row.state),
                "session_unfilled_slots": slots[idx],
                "session_rejected_fresh_count": int(rejected_counts.get(idx, 0)),
                "rejected_supply_ge_vacancy": int(rejected_counts.get(idx, 0)) >= slots[idx],
                "next_rank": next_rank,
                "next_rank_bin": descriptive_rank_bin(next_rank),
                "next_present": next_rank is not None,
                "next_top10": next_rank is not None and next_rank <= 10,
                "next_top20": next_rank is not None and next_rank <= 20,
            }
        )
    return pd.DataFrame(rows)


def build_churn_attribution(ledgers: FrozenStructuralLedgers) -> pd.DataFrame:
    intents = ledgers.intents.copy()
    rows: list[dict[str, Any]] = []
    for session in ledgers.sessions.loc[~ledgers.sessions["bootstrap"].astype(bool)].itertuples(index=False):
        idx = int(session.index)
        day = intents.loc[intents["index"].astype(int).eq(idx)]
        def count(side: str, reason: str) -> int:
            return int((day["side"].eq(side) & day["reason"].eq(reason)).sum())
        confirmed = count("SELL_INTENT", "CONFIRMED_EXIT_GT20_2")
        universe = count("SELL_INTENT", "UNIVERSE_EXIT")
        soft_sell = count("SELL_INTENT", "SOFT_RANK_GAP_REPLACEMENT")
        vacancy_fill = count("BUY_INTENT", "QUALIFIED_VACANCY_FILL")
        soft_buy = count("BUY_INTENT", "SOFT_RANK_GAP_REPLACEMENT")
        drivers = {
            "CONFIRMED_EXIT": confirmed,
            "SOFT_REPLACEMENT": soft_sell,
            "UNIVERSE_EXIT": universe,
        }
        maximum = max(drivers.values()) if drivers else 0
        leaders = sorted(k for k, v in drivers.items() if v == maximum and v > 0)
        dominant = "NONE" if not leaders else leaders[0] if len(leaders) == 1 else "MIXED_TIE:" + "+".join(leaders)
        rows.append(
            {
                "index": idx,
                "date": str(session.date),
                "block": idx // 100 + 1,
                "replacement_count": int(session.replacement_count),
                "high_churn_ge3": int(session.replacement_count) >= 3,
                "sell_count": int(session.sell_count),
                "buy_count": int(session.buy_count),
                "confirmed_exit_sells": confirmed,
                "universe_exit_sells": universe,
                "soft_replacement_sells": soft_sell,
                "qualified_vacancy_fill_buys": vacancy_fill,
                "soft_replacement_buys": soft_buy,
                "dominant_sell_driver": dominant,
                "unfilled_slots": int(session.unfilled_slots),
            }
        )
    return pd.DataFrame(rows)


def _group_exit_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"n": 0}
    excess_total = float(frame["rank_excess_over20"].sum())
    groups: dict[str, Any] = {}
    for label, part in frame.groupby("current_rank_bin", sort=False):
        groups[str(label)] = {
            "n": int(len(part)),
            "recovery_rate": _safe_rate(part["recovered_to_le20"]),
            "next_top10_rate": _safe_rate(part["next_top10"]),
            "next_top20_rate": _safe_rate(part["next_top20"]),
            "confirmed_exit_next_rate": _safe_rate(part["confirmed_exit_next"]),
            "current_rank": _numeric_summary(part["current_rank"]),
            "rank_jump": _numeric_summary(part["rank_jump"]),
            "next_rank": _numeric_summary(part["next_rank"]),
            "share_total_rank_excess_over20": (
                float(part["rank_excess_over20"].sum() / excess_total) if excess_total > 0 else None
            ),
        }
    return {
        "n": int(len(frame)),
        "overall_recovery_rate": _safe_rate(frame["recovered_to_le20"]),
        "overall_current_rank": _numeric_summary(frame["current_rank"]),
        "overall_rank_jump": _numeric_summary(frame["rank_jump"]),
        "by_current_rank_bin": groups,
    }


def _group_fresh_summary(frame: pd.DataFrame, sessions: pd.DataFrame) -> dict[str, Any]:
    underfilled = sessions.loc[sessions["capacity_state"].eq("UNFILLED_NO_QUALIFIED_CHALLENGER")].copy()
    if underfilled.empty:
        return {"underfilled_sessions": 0}
    session_supply = frame.groupby("index").size().to_dict() if not frame.empty else {}
    supply_ge = [int(session_supply.get(int(row.index), 0)) >= int(row.unfilled_slots) for row in underfilled.itertuples(index=False)]
    groups: dict[str, Any] = {}
    if not frame.empty:
        for label, part in frame.groupby("previous_rank_bin", sort=False):
            groups[str(label)] = {
                "n": int(len(part)),
                "next_top10_rate": _safe_rate(part["next_top10"]),
                "next_top20_rate": _safe_rate(part["next_top20"]),
                "next_absent_rate": _safe_rate(~part["next_present"]),
                "current_rank": _numeric_summary(part["current_rank"]),
                "next_rank": _numeric_summary(part["next_rank"]),
            }
    return {
        "underfilled_sessions": int(len(underfilled)),
        "unfilled_vacancy_days": int(underfilled["unfilled_slots"].sum()),
        "rejected_fresh_rows_on_underfilled_sessions": int(len(frame)),
        "share_underfilled_sessions_rejected_supply_ge_vacancy": float(np.mean(supply_ge)) if supply_ge else None,
        "by_previous_rank_bin": groups,
    }


def _group_churn_summary(frame: pd.DataFrame) -> dict[str, Any]:
    high = frame.loc[frame["high_churn_ge3"].astype(bool)].copy()
    incidence: dict[str, Any] = {}
    for column in ("confirmed_exit_sells", "soft_replacement_sells", "universe_exit_sells", "qualified_vacancy_fill_buys"):
        incidence[column] = {
            "all_transition_total": int(frame[column].sum()),
            "high_churn_transition_total": int(high[column].sum()),
            "share_high_churn_sessions_with_any": _safe_rate(high[column].gt(0)) if len(high) else None,
            "mean_count_on_high_churn_sessions": float(high[column].mean()) if len(high) else None,
        }
    return {
        "transitions": int(len(frame)),
        "high_churn_ge3_transitions": int(len(high)),
        "high_churn_share": _safe_rate(frame["high_churn_ge3"]),
        "dominant_sell_driver_counts_high_churn": high["dominant_sell_driver"].value_counts().sort_index().to_dict(),
        "mechanism_incidence": incidence,
    }


def _build_block_summary(
    sessions: pd.DataFrame,
    exit_pending: pd.DataFrame,
    fresh: pd.DataFrame,
    churn: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for block in range(1, 7):
        s = sessions.loc[((sessions["index"].astype(int) // 100) + 1).eq(block)]
        e = exit_pending.loc[exit_pending["block"].eq(block)]
        f = fresh.loc[fresh["block"].eq(block)]
        c = churn.loc[churn["block"].eq(block)]
        under = s.loc[s["capacity_state"].eq("UNFILLED_NO_QUALIFIED_CHALLENGER")]
        supply = f.groupby("index").size().to_dict() if not f.empty else {}
        supply_ge = [int(supply.get(int(r.index), 0)) >= int(r.unfilled_slots) for r in under.itertuples(index=False)]
        rows.append(
            {
                "block": block,
                "sessions": int(len(s)),
                "exit_pending_count": int(len(e)),
                "exit_pending_recovery_rate": _safe_rate(e["recovered_to_le20"]) if len(e) else None,
                "exit_pending_gt100_share": _safe_rate(e["current_rank"].gt(100)) if len(e) else None,
                "exit_pending_rank_excess_over20_sum": int(e["rank_excess_over20"].sum()) if len(e) else 0,
                "underfilled_sessions": int(len(under)),
                "unfilled_vacancy_days": int(under["unfilled_slots"].sum()),
                "rejected_fresh_rows": int(len(f)),
                "rejected_fresh_next_top20_rate": _safe_rate(f["next_top20"]) if len(f) else None,
                "share_underfilled_supply_ge_vacancy": float(np.mean(supply_ge)) if supply_ge else None,
                "mean_replacements": float(c["replacement_count"].mean()) if len(c) else None,
                "high_churn_ge3_share": _safe_rate(c["high_churn_ge3"]) if len(c) else None,
                "confirmed_exit_sells": int(c["confirmed_exit_sells"].sum()) if len(c) else 0,
                "soft_replacement_sells": int(c["soft_replacement_sells"].sum()) if len(c) else 0,
                "universe_exit_sells": int(c["universe_exit_sells"].sum()) if len(c) else 0,
            }
        )
    return pd.DataFrame(rows)


def run_failure_mechanism_diagnosis(
    structural_root: str | Path,
    historical_root: str | Path,
) -> FailureDiagnosisResult:
    ledgers = load_frozen_structural_ledgers(structural_root)
    source = load_pinned_v4_x1_source_strict(historical_root)
    if sha256_file(source.manifest_path) != EXPECTED_SCORE_MANIFEST_SHA256:
        raise DecisionV2FailureDiagnosisError("HISTORICAL_MANIFEST_IDENTITY_CHANGED")
    if sha256_file(source.score_path) != EXPECTED_SCORE_SHA256:
        raise DecisionV2FailureDiagnosisError("HISTORICAL_SCORE_IDENTITY_CHANGED")
    if len(source.frame) != EXPECTED_SCORE_ROWS or source.frame["date"].nunique() != EXPECTED_SESSIONS:
        raise DecisionV2FailureDiagnosisError("HISTORICAL_SHAPE_CHANGED")

    rank_lookup = _rank_lookup(source.frame)
    exit_pending = build_exit_pending_diagnosis(ledgers, rank_lookup)
    rejected_fresh = build_rejected_fresh_diagnosis(ledgers, rank_lookup)
    churn = build_churn_attribution(ledgers)
    blocks = _build_block_summary(ledgers.sessions, exit_pending, rejected_fresh, churn)

    summary = {
        "schema_version": "decision_v2_failure_mechanism_diagnosis_v1",
        "status": "COMPLETE_OUTCOME_BLIND_DECISION_V2_FAILURE_MECHANISM_DIAGNOSIS",
        "source": {
            "structural_manifest_sha256": EXPECTED_STRUCTURAL_MANIFEST_SHA256,
            "structural_plan_digest": EXPECTED_PLAN_DIGEST,
            "historical_manifest_sha256": EXPECTED_SCORE_MANIFEST_SHA256,
            "historical_score_sha256": EXPECTED_SCORE_SHA256,
            "score_sessions": EXPECTED_SESSIONS,
            "score_rows": EXPECTED_SCORE_ROWS,
        },
        "guards": {
            "decision_v2_structural_replay_rerun": False,
            "alternative_decision_rule_simulated": False,
            "alternative_thresholds_tested": False,
            "decision_parameter_sweep": False,
            "realized_returns_loaded": False,
            "historical_pnl_computed": False,
            "protected_or_fresh_forward_access": False,
            "model_refit_or_retune": False,
            "provider_or_network_calls": False,
        },
        "exit_grace_severity": _group_exit_summary(exit_pending),
        "candidate_scarcity": _group_fresh_summary(rejected_fresh, ledgers.sessions),
        "residual_churn": _group_churn_summary(churn),
        "block_mechanism_summary": blocks.to_dict(orient="records"),
        "interpretation_boundary": (
            "Descriptive mechanism diagnosis only. Rank bins are reporting strata, not Decision thresholds."
        ),
    }
    return FailureDiagnosisResult(
        summary=summary,
        exit_pending=exit_pending,
        rejected_fresh=rejected_fresh,
        churn_attribution=churn,
        block_summary=blocks,
    )


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def write_failure_diagnosis_artifacts(result: FailureDiagnosisResult, output_dir: str | Path) -> Path:
    destination = Path(output_dir).expanduser().resolve()
    if destination.exists():
        raise DecisionV2FailureDiagnosisError(f"OUTPUT_ALREADY_EXISTS:{destination}")
    staging = destination.with_name(destination.name + ".staging")
    if staging.exists():
        raise DecisionV2FailureDiagnosisError(f"STAGING_ALREADY_EXISTS:{staging}")
    staging.mkdir(parents=True, exist_ok=False)

    outputs: dict[str, bytes] = {
        "summary.json": (json.dumps(result.summary, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        "exit_pending_diagnosis.csv": _csv_bytes(result.exit_pending),
        "rejected_fresh_top10_diagnosis.csv": _csv_bytes(result.rejected_fresh),
        "churn_transition_attribution.csv": _csv_bytes(result.churn_attribution),
        "block_mechanism_summary.csv": _csv_bytes(result.block_summary),
    }
    hashes: dict[str, str] = {}
    for name, content in outputs.items():
        (staging / name).write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()
    manifest = {
        "schema_version": "decision_v2_failure_mechanism_diagnosis_manifest_v1",
        "status": result.summary["status"],
        "source": result.summary["source"],
        "guards": result.summary["guards"],
        "artifacts": hashes,
    }
    manifest_path = staging / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(destination)
    return destination / "MANIFEST.json"
