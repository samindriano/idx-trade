from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .decision_v2_minimal import DecisionV2Plan, DecisionV2ShadowState
from .v4_x1_decision_v1_contract import (
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    REQUIRED_SCORE_COLUMNS,
    VerifiedScoreSession,
    _VERIFIED_TOKEN,
)
from .v4_x1_decision_v2_minimal import (
    V4_X1_DECISION_V2_MINIMAL_PROFILE_V1,
    plan_v4_x1_decision_v2_minimal,
)


EXPECTED_SOURCE_MANIFEST_SHA256 = "6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205"
EXPECTED_SOURCE_SCORE_SHA256 = "48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b"
EXPECTED_SCORE_SESSIONS = 600
EXPECTED_SCORE_ROWS = 172_697
SCORE_FILENAME = "clean_challenger_validation_scores.parquet"
EXPECTED_V1_REPLACEMENTS = 2_686
EXPECTED_NAIVE_TOP10_REPLACEMENTS = 3_127

GATE_LIMITS = {
    "mean_replacements_per_transition_max": 2.25,
    "turnover_ratio_vs_naive_max": 0.50,
    "share_transitions_ge3_replacements_max": 0.35,
    "median_completed_holding_spell_min": 3.0,
    "one_session_completed_holding_share_max": 0.35,
    "mean_full_target_top10_overlap_min": 6.0,
    "mean_target_rank_max": 12.0,
    "mean_target_size_min": 9.0,
    "share_target_size_10_min": 0.70,
    "share_target_size_le8_max": 0.10,
}

SOURCE_GUARD_EXPECTATIONS = {
    "measurement_only": True,
    "provider_calls": False,
    "network_calls": False,
    "protected_forward_accessed": False,
    "fresh_forward_accessed": False,
}


class DecisionV2StructuralReplayError(RuntimeError):
    pass


@dataclass(frozen=True)
class PinnedReplaySource:
    frame: pd.DataFrame
    manifest_path: Path
    score_path: Path


@dataclass(frozen=True)
class ReplayPass:
    session_ledger: pd.DataFrame
    membership_ledger: pd.DataFrame
    intent_ledger: pd.DataFrame
    state_ledger: pd.DataFrame
    holding_spells: pd.DataFrame
    fold_boundaries: pd.DataFrame
    plan_digest: str


@dataclass(frozen=True)
class StructuralReplayResult:
    primary: ReplayPass
    summary: dict[str, Any]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_ticker(value: object) -> str:
    ticker = str(value).upper().replace(".JK", "").strip()
    if not ticker:
        raise DecisionV2StructuralReplayError("DECISION_V2_REPLAY_EMPTY_TICKER")
    return ticker


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_SOURCE_MANIFEST_INVALID"
        ) from exc
    if not isinstance(payload, dict):
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_SOURCE_MANIFEST_NOT_OBJECT"
        )
    for key, expected in SOURCE_GUARD_EXPECTATIONS.items():
        if payload.get(key) is not expected:
            raise DecisionV2StructuralReplayError(
                f"DECISION_V2_REPLAY_SOURCE_GUARD_CHANGED:{key}"
            )
    return payload


def _naive_top10_replacements(frame: pd.DataFrame) -> int:
    dates = [pd.Timestamp(value) for value in sorted(frame["date"].unique())]
    top10 = {
        date: set(
            frame.loc[
                frame["date"].eq(date) & frame["rank_consensus"].le(10),
                "ticker",
            ].astype(str)
        )
        for date in dates
    }
    total = 0
    for previous, current in zip(dates[:-1], dates[1:]):
        total += 10 - len(top10[previous] & top10[current])
    return int(total)


def load_pinned_v4_x1_source(root: str | Path) -> PinnedReplaySource:
    root_path = Path(root).expanduser().resolve()
    manifest_path = root_path / "MANIFEST.json"
    score_path = root_path / SCORE_FILENAME
    if not manifest_path.is_file() or not score_path.is_file():
        raise DecisionV2StructuralReplayError("DECISION_V2_REPLAY_SOURCE_MISSING")

    manifest_sha = sha256_file(manifest_path)
    score_sha = sha256_file(score_path)
    if manifest_sha != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_SOURCE_MANIFEST_SHA_MISMATCH:{manifest_sha}"
        )
    if score_sha != EXPECTED_SOURCE_SCORE_SHA256:
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_SOURCE_SCORE_SHA_MISMATCH:{score_sha}"
        )
    _load_manifest(manifest_path)

    frame = pd.read_parquet(score_path)
    required = {
        "ticker",
        "date",
        "fold",
        "mode",
        "alpha_h5",
        "alpha_h10",
        "alpha_consensus",
    }
    missing = required - set(frame.columns)
    if missing:
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_SCORE_COLUMNS_MISSING:{sorted(missing)}"
        )
    if len(frame) != EXPECTED_SCORE_ROWS:
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_SCORE_ROW_COUNT_CHANGED:{len(frame)}"
        )

    frame = frame.loc[:, sorted(required)].copy()
    frame["ticker"] = frame["ticker"].map(_normalize_ticker)
    frame["date"] = (
        pd.to_datetime(frame["date"], errors="raise")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    for column in ("alpha_h5", "alpha_h10", "alpha_consensus"):
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype(float)
        if not np.isfinite(frame[column]).all():
            raise DecisionV2StructuralReplayError(
                f"DECISION_V2_REPLAY_NONFINITE:{column}"
            )

    if frame.duplicated(["date", "ticker"]).any():
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_DUPLICATE_DATE_TICKER"
        )
    if frame["date"].nunique() != EXPECTED_SCORE_SESSIONS:
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_SCORE_SESSION_COUNT_CHANGED:{frame['date'].nunique()}"
        )
    if int(frame.groupby("date")["fold"].nunique().max()) != 1:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_MULTIPLE_FOLDS_PER_SESSION"
        )
    if int(frame.groupby("date")["mode"].nunique().max()) != 1:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_MULTIPLE_MODES_PER_SESSION"
        )

    ranked_parts: list[pd.DataFrame] = []
    for _, block in frame.groupby("date", sort=True):
        ranked = block.copy()
        order = ranked.sort_values(
            ["alpha_consensus", "ticker"],
            ascending=[False, True],
            kind="mergesort",
        ).index
        ranked.loc[order, "rank_consensus"] = np.arange(
            1,
            len(ranked) + 1,
            dtype=int,
        )
        ranked["rank_consensus"] = ranked["rank_consensus"].astype(int)
        expected_ranks = set(range(1, len(ranked) + 1))
        if set(ranked["rank_consensus"].tolist()) != expected_ranks:
            raise DecisionV2StructuralReplayError(
                "DECISION_V2_REPLAY_NONCONTIGUOUS_RANKS"
            )
        ranked_parts.append(ranked)

    ranked_frame = pd.concat(ranked_parts, ignore_index=True)
    naive_replacements = _naive_top10_replacements(ranked_frame)
    if naive_replacements != EXPECTED_NAIVE_TOP10_REPLACEMENTS:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_NAIVE_COMPARATOR_CHANGED:"
            f"{naive_replacements}!={EXPECTED_NAIVE_TOP10_REPLACEMENTS}"
        )

    return PinnedReplaySource(
        frame=ranked_frame,
        manifest_path=manifest_path,
        score_path=score_path,
    )


def _verified_session(
    block: pd.DataFrame,
    manifest_path: Path,
    score_path: Path,
) -> VerifiedScoreSession:
    score_block = (
        block.loc[:, list(REQUIRED_SCORE_COLUMNS)]
        .sort_values(["rank_consensus", "ticker"], kind="mergesort")
        .reset_index(drop=True)
    )
    return VerifiedScoreSession(
        session_date=pd.Timestamp(block["date"].iloc[0]).date().isoformat(),
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=score_path,
        artifact_sha256=EXPECTED_SOURCE_SCORE_SHA256,
        manifest_path=manifest_path,
        manifest_sha256=EXPECTED_SOURCE_MANIFEST_SHA256,
        scores=score_block,
        alpha_tie_rows=int(
            score_block["alpha_consensus"].duplicated(keep=False).sum()
        ),
        _verification_token=_VERIFIED_TOKEN,
    )


def _plan_payload(plan: DecisionV2Plan) -> dict[str, Any]:
    return {
        "date": plan.decision_session_date,
        "current": list(plan.current_shadow_positions),
        "target": list(plan.target_positions),
        "buys": [
            [item.ticker, item.rank_consensus, item.reason, item.replacement_peer]
            for item in plan.buy_intents
        ],
        "sells": [
            [item.ticker, item.rank_consensus, item.reason, item.replacement_peer]
            for item in plan.sell_intents
        ],
        "holds": list(plan.hold_tickers),
        "incumbents": [
            [item.ticker, item.current_rank, item.previous_rank, item.state]
            for item in plan.incumbent_observations
        ],
        "challengers": [
            [item.ticker, item.current_rank, item.previous_rank, item.state]
            for item in plan.challenger_observations
        ],
        "unfilled_slots": plan.unfilled_slots,
        "capacity_state": plan.capacity_state,
        "rule_id": plan.rule_id,
        "bootstrap": plan.bootstrap,
    }


def _replacement_count(plan: DecisionV2Plan) -> int:
    if plan.bootstrap:
        return 0
    # Conservative seat-change metric. A paired sell+buy is one replacement;
    # an exit-only or fill-only transition also counts as one changed seat.
    return max(len(plan.sell_intents), len(plan.buy_intents))


def _rank_map(block: pd.DataFrame) -> dict[str, int]:
    return {
        str(row.ticker): int(row.rank_consensus)
        for row in block.loc[:, ["ticker", "rank_consensus"]].itertuples(
            index=False
        )
    }


def _top_set(block: pd.DataFrame, maximum_rank: int) -> set[str]:
    return set(
        block.loc[
            block["rank_consensus"].le(maximum_rank),
            "ticker",
        ].astype(str)
    )


def replay_once(source: PinnedReplaySource) -> ReplayPass:
    frame = source.frame
    dates = [pd.Timestamp(value) for value in sorted(frame["date"].unique())]
    if len(dates) != EXPECTED_SCORE_SESSIONS:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_SESSION_LEDGER_CHANGED"
        )

    blocks = {date: block.copy() for date, block in frame.groupby("date", sort=True)}
    folds = {date: str(blocks[date]["fold"].iloc[0]) for date in dates}

    state = DecisionV2ShadowState.empty()
    previous_verified: VerifiedScoreSession | None = None
    open_spells: dict[str, dict[str, Any]] = {}

    plan_payloads: list[dict[str, Any]] = []
    session_rows: list[dict[str, Any]] = []
    membership_rows: list[dict[str, Any]] = []
    intent_rows: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    spell_rows: list[dict[str, Any]] = []
    fold_boundary_rows: list[dict[str, Any]] = []

    for index, session_date in enumerate(dates):
        block = blocks[session_date]
        verified = _verified_session(
            block,
            source.manifest_path,
            source.score_path,
        )

        if index == 0:
            if previous_verified is not None:
                raise DecisionV2StructuralReplayError(
                    "DECISION_V2_REPLAY_PREROLL_DETECTED"
                )
            if state.as_of_session_date is not None or state.positions:
                raise DecisionV2StructuralReplayError(
                    "DECISION_V2_REPLAY_BOOTSTRAP_STATE_NOT_EMPTY"
                )
        else:
            expected_previous_date = dates[index - 1].date().isoformat()
            if previous_verified is None:
                raise DecisionV2StructuralReplayError(
                    "DECISION_V2_REPLAY_PREVIOUS_SESSION_MISSING"
                )
            if previous_verified.session_date != expected_previous_date:
                raise DecisionV2StructuralReplayError(
                    "DECISION_V2_REPLAY_NONADJACENT_PREVIOUS_SESSION"
                )
            if state.as_of_session_date != expected_previous_date:
                raise DecisionV2StructuralReplayError(
                    "DECISION_V2_REPLAY_STATE_NOT_ADJACENT"
                )
            if state.rule_id != V4_X1_DECISION_V2_MINIMAL_PROFILE_V1.rule_id:
                raise DecisionV2StructuralReplayError(
                    "DECISION_V2_REPLAY_STATE_RULE_ID_UNBOUND"
                )

        plan = plan_v4_x1_decision_v2_minimal(
            current_verified=verified,
            previous_verified=previous_verified,
            shadow_state=state,
        )
        if plan.bootstrap != (index == 0):
            raise DecisionV2StructuralReplayError(
                "DECISION_V2_REPLAY_BOOTSTRAP_POSITION_CHANGED"
            )

        target = tuple(plan.target_positions)
        if len(target) > 10:
            raise DecisionV2StructuralReplayError(
                "DECISION_V2_REPLAY_TARGET_OVER_CAPACITY"
            )
        if len(set(target)) != len(target):
            raise DecisionV2StructuralReplayError(
                "DECISION_V2_REPLAY_DUPLICATE_TARGET"
            )

        rank_map = _rank_map(block)
        top10 = _top_set(block, 10)
        top20 = _top_set(block, 20)
        if any(ticker not in rank_map for ticker in target):
            raise DecisionV2StructuralReplayError(
                "DECISION_V2_REPLAY_UNRANKED_TARGET_RETAINED"
            )

        target_ranks = [rank_map[ticker] for ticker in target]
        top10_overlap = len(set(target) & top10)
        top20_overlap = len(set(target) & top20)
        sell_count = len(plan.sell_intents)
        buy_count = len(plan.buy_intents)
        replacements = _replacement_count(plan)

        session_rows.append(
            {
                "index": index,
                "date": session_date.date().isoformat(),
                "fold": folds[session_date],
                "bootstrap": bool(plan.bootstrap),
                "target_size": len(target),
                "unfilled_slots": int(plan.unfilled_slots),
                "capacity_state": plan.capacity_state,
                "sell_count": sell_count,
                "buy_count": buy_count,
                "replacement_count": replacements,
                "top10_overlap": top10_overlap,
                "top10_overlap_normalized": (
                    float(top10_overlap / len(target)) if target else None
                ),
                "top20_overlap": top20_overlap,
                "top20_overlap_normalized": (
                    float(top20_overlap / len(target)) if target else None
                ),
                "worst_target_rank": max(target_ranks) if target_ranks else None,
                "target_rank_gt20_count": sum(
                    rank_value > 20 for rank_value in target_ranks
                ),
            }
        )

        prior_target = set(state.positions)
        for ticker in target:
            rank_value = rank_map[ticker]
            membership_rows.append(
                {
                    "index": index,
                    "date": session_date.date().isoformat(),
                    "fold": folds[session_date],
                    "ticker": ticker,
                    "rank_consensus": rank_value,
                    "in_top10": rank_value <= 10,
                    "in_top20": rank_value <= 20,
                    "held_at_start": ticker in prior_target,
                }
            )

        for intent in (*plan.sell_intents, *plan.buy_intents):
            intent_rows.append(
                {
                    "index": index,
                    "date": session_date.date().isoformat(),
                    "side": intent.side,
                    "ticker": intent.ticker,
                    "rank_consensus": intent.rank_consensus,
                    "reason": intent.reason,
                    "replacement_peer": intent.replacement_peer,
                }
            )

        for observation in plan.incumbent_observations:
            state_rows.append(
                {
                    "index": index,
                    "date": session_date.date().isoformat(),
                    "kind": "INCUMBENT",
                    "ticker": observation.ticker,
                    "current_rank": observation.current_rank,
                    "previous_rank": observation.previous_rank,
                    "state": observation.state,
                }
            )
        for observation in plan.challenger_observations:
            state_rows.append(
                {
                    "index": index,
                    "date": session_date.date().isoformat(),
                    "kind": "CHALLENGER",
                    "ticker": observation.ticker,
                    "current_rank": observation.current_rank,
                    "previous_rank": observation.previous_rank,
                    "state": observation.state,
                }
            )

        current_target = set(target)
        exited = sorted(prior_target - current_target)
        entered = sorted(current_target - prior_target)

        for ticker in exited:
            spell = open_spells.pop(ticker, None)
            if spell is None:
                raise DecisionV2StructuralReplayError(
                    f"DECISION_V2_REPLAY_EXIT_WITHOUT_OPEN_SPELL:{ticker}"
                )
            spell_rows.append(
                {
                    **spell,
                    "exit_index": index,
                    "exit_date": session_date.date().isoformat(),
                    "duration_sessions": index - int(spell["entry_index"]),
                    "right_censored": False,
                    "censor_date": None,
                }
            )

        for ticker in entered:
            if ticker in open_spells:
                raise DecisionV2StructuralReplayError(
                    f"DECISION_V2_REPLAY_DUPLICATE_OPEN_SPELL:{ticker}"
                )
            entry_reason = next(
                (
                    intent.reason
                    for intent in plan.buy_intents
                    if intent.ticker == ticker
                ),
                "BOOTSTRAP_TOP10" if index == 0 else None,
            )
            if entry_reason is None:
                raise DecisionV2StructuralReplayError(
                    f"DECISION_V2_REPLAY_ENTRY_WITHOUT_BUY_INTENT:{ticker}"
                )
            open_spells[ticker] = {
                "ticker": ticker,
                "entry_index": index,
                "entry_date": session_date.date().isoformat(),
                "entry_reason": entry_reason,
            }

        if index > 0 and folds[session_date] != folds[dates[index - 1]]:
            fold_boundary_rows.append(
                {
                    "from_index": index - 1,
                    "to_index": index,
                    "from_date": dates[index - 1].date().isoformat(),
                    "to_date": session_date.date().isoformat(),
                    "from_fold": folds[dates[index - 1]],
                    "to_fold": folds[session_date],
                    "replacement_count": replacements,
                    "sell_count": sell_count,
                    "buy_count": buy_count,
                    "target_size": len(target),
                    "top10_overlap": top10_overlap,
                    "mean_target_rank": (
                        float(np.mean(target_ranks))
                        if target_ranks
                        else None
                    ),
                }
            )

        plan_payloads.append(_plan_payload(plan))
        state = DecisionV2ShadowState.from_plan(plan)
        previous_verified = verified

    last_index = len(dates) - 1
    last_date = dates[-1].date().isoformat()
    for spell in open_spells.values():
        spell_rows.append(
            {
                **spell,
                "exit_index": None,
                "exit_date": None,
                "duration_sessions": (
                    last_index - int(spell["entry_index"]) + 1
                ),
                "right_censored": True,
                "censor_date": last_date,
            }
        )

    return ReplayPass(
        session_ledger=pd.DataFrame(session_rows),
        membership_ledger=pd.DataFrame(membership_rows),
        intent_ledger=pd.DataFrame(intent_rows),
        state_ledger=pd.DataFrame(state_rows),
        holding_spells=pd.DataFrame(spell_rows),
        fold_boundaries=pd.DataFrame(fold_boundary_rows),
        plan_digest=canonical_json_sha256(plan_payloads),
    )


def _safe_rate(mask: pd.Series) -> float | None:
    return None if len(mask) == 0 else float(mask.astype(bool).mean())


def _quantiles(values: pd.Series) -> dict[str, float | None]:
    numeric = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if numeric.empty:
        return {
            "mean": None,
            "median": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "max": None,
        }
    return {
        "mean": float(numeric.mean()),
        "median": float(numeric.median()),
        "p75": float(numeric.quantile(0.75)),
        "p90": float(numeric.quantile(0.90)),
        "p95": float(numeric.quantile(0.95)),
        "max": float(numeric.max()),
    }


def _completed_spells(pass_result: ReplayPass) -> pd.DataFrame:
    spells = pass_result.holding_spells
    if spells.empty:
        return spells.copy()
    return spells.loc[
        ~spells["right_censored"].astype(bool)
    ].copy()


def _segment_summary(
    sessions: pd.DataFrame,
    memberships: pd.DataFrame,
    completed_spells: pd.DataFrame,
    *,
    label: str,
) -> dict[str, Any]:
    transitions = sessions.loc[
        ~sessions["bootstrap"].astype(bool)
    ].copy()
    return {
        "label": label,
        "sessions": int(len(sessions)),
        "transitions": int(len(transitions)),
        "mean_replacements_per_transition": (
            float(transitions["replacement_count"].mean())
            if len(transitions)
            else None
        ),
        "share_transitions_ge3_replacements": (
            _safe_rate(transitions["replacement_count"].ge(3))
            if len(transitions)
            else None
        ),
        "mean_target_size": (
            float(sessions["target_size"].mean())
            if len(sessions)
            else None
        ),
        "share_target_size_10": (
            _safe_rate(sessions["target_size"].eq(10))
            if len(sessions)
            else None
        ),
        "mean_target_rank": (
            float(memberships["rank_consensus"].mean())
            if len(memberships)
            else None
        ),
        "mean_full_target_top10_overlap": (
            float(
                sessions.loc[
                    sessions["target_size"].eq(10),
                    "top10_overlap",
                ].mean()
            )
            if sessions["target_size"].eq(10).any()
            else None
        ),
        "unfilled_sessions": int(
            sessions["capacity_state"]
            .eq("UNFILLED_NO_QUALIFIED_CHALLENGER")
            .sum()
        ),
        "target_rank_gt20_name_days": int(
            memberships["rank_consensus"].gt(20).sum()
        ) if len(memberships) else 0,
        "completed_spell_count": int(len(completed_spells)),
        "completed_spell_duration": (
            _quantiles(completed_spells["duration_sessions"])
            if len(completed_spells)
            else _quantiles(pd.Series(dtype=float))
        ),
    }


def _build_time_segments(
    pass_result: ReplayPass,
    source: PinnedReplaySource,
) -> dict[str, Any]:
    sessions = pass_result.session_ledger
    memberships = pass_result.membership_ledger
    spells = _completed_spells(pass_result)

    block_summaries: dict[str, Any] = {}
    for block_index in range(6):
        lower = block_index * 100
        upper = lower + 99
        segment_sessions = sessions.loc[
            sessions["index"].between(lower, upper)
        ].copy()
        segment_memberships = memberships.loc[
            memberships["index"].between(lower, upper)
        ].copy()
        exit_index = pd.to_numeric(
            spells["exit_index"],
            errors="coerce",
        ) if len(spells) else pd.Series(dtype=float)
        segment_spells = (
            spells.loc[exit_index.between(lower, upper)].copy()
            if len(spells)
            else spells.copy()
        )
        key = f"BLOCK_{block_index + 1:02d}_{lower:03d}_{upper:03d}"
        block_summaries[key] = _segment_summary(
            segment_sessions,
            segment_memberships,
            segment_spells,
            label=key,
        )

    fold_by_date = (
        source.frame.loc[:, ["date", "fold"]]
        .drop_duplicates()
        .sort_values("date", kind="mergesort")
    )
    fold_by_date["date_key"] = fold_by_date["date"].dt.date.astype(str)

    fold_summaries: dict[str, Any] = {}
    for fold_value, fold_dates in fold_by_date.groupby("fold", sort=True):
        date_keys = set(fold_dates["date_key"].tolist())
        segment_sessions = sessions.loc[
            sessions["date"].isin(date_keys)
        ].copy()
        segment_memberships = memberships.loc[
            memberships["date"].isin(date_keys)
        ].copy()
        indices = set(segment_sessions["index"].astype(int).tolist())
        if len(spells):
            numeric_exit = pd.to_numeric(
                spells["exit_index"],
                errors="coerce",
            )
            segment_spells = spells.loc[
                numeric_exit.isin(indices)
            ].copy()
        else:
            segment_spells = spells.copy()
        key = str(fold_value)
        fold_summaries[key] = _segment_summary(
            segment_sessions,
            segment_memberships,
            segment_spells,
            label=key,
        )

    return {
        "hundred_date_blocks": block_summaries,
        "fold_segments": fold_summaries,
        "fold_boundary_transitions": (
            pass_result.fold_boundaries.to_dict(orient="records")
        ),
    }


def _pending_recovery_metrics(
    pass_result: ReplayPass,
    source: PinnedReplaySource,
) -> dict[str, Any]:
    states = pass_result.state_ledger
    pending = states.loc[
        states["kind"].eq("INCUMBENT")
        & states["state"].eq("EXIT_PENDING_1")
    ].copy()
    if pending.empty:
        return {
            "exit_pending_observations": 0,
            "eligible_next_session": 0,
            "recovered_next_session_count": 0,
            "recovery_rate": None,
        }

    rank_lookup = {
        (
            pd.Timestamp(row.date).date().isoformat(),
            str(row.ticker),
        ): int(row.rank_consensus)
        for row in source.frame.loc[
            :,
            ["date", "ticker", "rank_consensus"],
        ].itertuples(index=False)
    }
    sessions = pass_result.session_ledger.sort_values(
        "index",
        kind="mergesort",
    )
    next_date_by_index = {
        int(current.index): str(following.date)
        for current, following in zip(
            sessions.iloc[:-1].itertuples(index=False),
            sessions.iloc[1:].itertuples(index=False),
        )
    }

    eligible = 0
    recovered = 0
    for row in pending.itertuples(index=False):
        next_date = next_date_by_index.get(int(row.index))
        if next_date is None:
            continue
        eligible += 1
        next_rank = rank_lookup.get((next_date, str(row.ticker)))
        if next_rank is not None and next_rank <= 20:
            recovered += 1

    return {
        "exit_pending_observations": int(len(pending)),
        "eligible_next_session": int(eligible),
        "recovered_next_session_count": int(recovered),
        "recovery_rate": (
            float(recovered / eligible)
            if eligible
            else None
        ),
    }


def _correctness_checks(
    pass_result: ReplayPass,
    source: PinnedReplaySource,
) -> dict[str, Any]:
    sessions = pass_result.session_ledger
    memberships = pass_result.membership_ledger
    intents = pass_result.intent_ledger
    states = pass_result.state_ledger

    no_target_size_gt10 = bool(sessions["target_size"].le(10).all())
    no_duplicate_target_ticker = not bool(
        memberships.duplicated(["date", "ticker"]).any()
    )

    date_by_index = {
        int(row.index): str(row.date)
        for row in sessions.itertuples(index=False)
    }
    previous_date_by_index = {
        index: date_by_index[index - 1]
        for index in range(1, len(sessions))
    }
    rank_lookup = {
        (
            pd.Timestamp(row.date).date().isoformat(),
            str(row.ticker),
        ): int(row.rank_consensus)
        for row in source.frame.loc[
            :,
            ["date", "ticker", "rank_consensus"],
        ].itertuples(index=False)
    }

    unqualified_nonbootstrap_entrant_violations = 0
    one_observation_gt20_exit_violations = 0
    soft_replacement_gap_violations = 0

    if not intents.empty:
        for row in intents.itertuples(index=False):
            index = int(row.index)
            if row.side == "BUY_INTENT" and row.reason != "BOOTSTRAP_TOP10":
                previous_date = previous_date_by_index.get(index)
                current_rank = rank_lookup.get((str(row.date), str(row.ticker)))
                previous_rank = (
                    rank_lookup.get((previous_date, str(row.ticker)))
                    if previous_date is not None
                    else None
                )
                if (
                    current_rank is None
                    or current_rank > 10
                    or previous_rank is None
                    or previous_rank > 20
                ):
                    unqualified_nonbootstrap_entrant_violations += 1

            if (
                row.side == "SELL_INTENT"
                and row.reason == "CONFIRMED_EXIT_GT20_2"
            ):
                previous_date = previous_date_by_index.get(index)
                current_rank = rank_lookup.get((str(row.date), str(row.ticker)))
                previous_rank = (
                    rank_lookup.get((previous_date, str(row.ticker)))
                    if previous_date is not None
                    else None
                )
                if not (
                    current_rank is not None
                    and current_rank > 20
                    and previous_rank is not None
                    and previous_rank > 20
                ):
                    one_observation_gt20_exit_violations += 1

        soft_buys = intents.loc[
            intents["side"].eq("BUY_INTENT")
            & intents["reason"].eq("SOFT_RANK_GAP_REPLACEMENT")
        ]
        soft_buy_rank = {
            (
                str(row.date),
                str(row.ticker),
            ): int(row.rank_consensus)
            for row in soft_buys.itertuples(index=False)
        }
        soft_sells = intents.loc[
            intents["side"].eq("SELL_INTENT")
            & intents["reason"].eq("SOFT_RANK_GAP_REPLACEMENT")
        ]
        for row in soft_sells.itertuples(index=False):
            challenger_rank = soft_buy_rank.get(
                (str(row.date), str(row.replacement_peer))
            )
            if (
                challenger_rank is None
                or row.rank_consensus is None
                or int(row.rank_consensus) - challenger_rank < 5
            ):
                soft_replacement_gap_violations += 1

    membership_keys = set(
        zip(
            memberships["date"].astype(str),
            memberships["ticker"].astype(str),
        )
    )
    confirmed_gt20_incumbent_retained_violations = 0
    if not states.empty:
        confirmed = states.loc[
            states["kind"].eq("INCUMBENT")
            & states["state"].eq("CONFIRMED_EXIT")
        ]
        confirmed_gt20_incumbent_retained_violations = sum(
            (str(row.date), str(row.ticker)) in membership_keys
            for row in confirmed.itertuples(index=False)
        )

    stale_state_violations = 0
    if len(memberships):
        for row in memberships.loc[
            memberships["rank_consensus"].gt(20)
        ].itertuples(index=False):
            index = int(row.index)
            if index == 0:
                continue
            previous_date = previous_date_by_index[index]
            previous_membership = (
                previous_date,
                str(row.ticker),
            ) in membership_keys
            previous_rank = rank_lookup.get(
                (previous_date, str(row.ticker))
            )
            if (
                previous_membership
                and previous_rank is not None
                and previous_rank > 20
            ):
                stale_state_violations += 1

    return {
        "no_target_size_gt10": no_target_size_gt10,
        "no_duplicate_target_ticker": no_duplicate_target_ticker,
        "unqualified_nonbootstrap_entrant_violations": int(
            unqualified_nonbootstrap_entrant_violations
        ),
        "one_observation_gt20_exit_violations": int(
            one_observation_gt20_exit_violations
        ),
        "confirmed_gt20_incumbent_retained_violations": int(
            confirmed_gt20_incumbent_retained_violations
        ),
        "soft_replacement_gap_violations": int(
            soft_replacement_gap_violations
        ),
        "stale_state_violations": int(stale_state_violations),
    }


def summarize_replay(
    primary: ReplayPass,
    secondary: ReplayPass,
    source: PinnedReplaySource,
) -> dict[str, Any]:
    if primary.plan_digest != secondary.plan_digest:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_NONDETERMINISTIC_PLAN_DIGEST"
        )

    sessions = primary.session_ledger
    memberships = primary.membership_ledger
    transitions = sessions.loc[
        ~sessions["bootstrap"].astype(bool)
    ].copy()
    completed_spells = _completed_spells(primary)
    states = primary.state_ledger
    intents = primary.intent_ledger

    if len(sessions) != EXPECTED_SCORE_SESSIONS:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_OUTPUT_SESSION_COUNT_CHANGED"
        )
    if len(transitions) != EXPECTED_SCORE_SESSIONS - 1:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_OUTPUT_TRANSITION_COUNT_CHANGED"
        )

    total_replacements = int(transitions["replacement_count"].sum())
    replacement_distribution = _quantiles(
        transitions["replacement_count"]
    )
    transition_distribution = {
        "share_0": _safe_rate(
            transitions["replacement_count"].eq(0)
        ),
        "share_1": _safe_rate(
            transitions["replacement_count"].eq(1)
        ),
        "share_2": _safe_rate(
            transitions["replacement_count"].eq(2)
        ),
        "share_ge3": _safe_rate(
            transitions["replacement_count"].ge(3)
        ),
    }

    completed_duration = (
        _quantiles(completed_spells["duration_sessions"])
        if len(completed_spells)
        else _quantiles(pd.Series(dtype=float))
    )
    one_session_share = (
        _safe_rate(completed_spells["duration_sessions"].eq(1))
        if len(completed_spells)
        else None
    )
    le3_share = (
        _safe_rate(completed_spells["duration_sessions"].le(3))
        if len(completed_spells)
        else None
    )

    full_sessions = sessions.loc[
        sessions["target_size"].eq(10)
    ]
    pending_metrics = _pending_recovery_metrics(primary, source)
    correctness = _correctness_checks(primary, source)

    confirmed_exit_count = (
        int(
            (
                states["kind"].eq("INCUMBENT")
                & states["state"].eq("CONFIRMED_EXIT")
            ).sum()
        )
        if not states.empty
        else 0
    )
    universe_exit_count = (
        int(
            (
                states["kind"].eq("INCUMBENT")
                & states["state"].eq("UNIVERSE_EXIT")
            ).sum()
        )
        if not states.empty
        else 0
    )
    fresh_rejected_count = (
        int(
            (
                states["kind"].eq("CHALLENGER")
                & states["state"].isin(
                    {
                        "UNCONFIRMED_PREVIOUS_GT_THRESHOLD",
                        "UNCONFIRMED_PREVIOUS_ABSENT",
                    }
                )
            ).sum()
        )
        if not states.empty
        else 0
    )
    soft_replacement_count = (
        int(
            (
                intents["side"].eq("SELL_INTENT")
                & intents["reason"].eq("SOFT_RANK_GAP_REPLACEMENT")
            ).sum()
        )
        if not intents.empty
        else 0
    )
    vacancy_fill_count = (
        int(
            (
                intents["side"].eq("BUY_INTENT")
                & intents["reason"].eq("QUALIFIED_VACANCY_FILL")
            ).sum()
        )
        if not intents.empty
        else 0
    )

    metrics = {
        "turnover_churn": {
            "replacement_metric_definition": (
                "max(sell_intent_count,buy_intent_count) "
                "per non-bootstrap transition"
            ),
            "total_replacements_excluding_bootstrap": total_replacements,
            "replacement_distribution": replacement_distribution,
            "transition_distribution": transition_distribution,
            "turnover_ratio_vs_naive_exact_daily_top10": float(
                total_replacements / EXPECTED_NAIVE_TOP10_REPLACEMENTS
            ),
            "turnover_ratio_vs_frozen_decision_v1": float(
                total_replacements / EXPECTED_V1_REPLACEMENTS
            ),
            "naive_exact_daily_top10_replacements_reference": (
                EXPECTED_NAIVE_TOP10_REPLACEMENTS
            ),
            "decision_v1_replacements_reference": EXPECTED_V1_REPLACEMENTS,
        },
        "holding_persistence": {
            "completed_holding_spell_count": int(
                len(completed_spells)
            ),
            "completed_duration_sessions": completed_duration,
            "one_session_holding_share": one_session_share,
            "le3_session_holding_share": le3_share,
            "right_censored_spell_count": (
                int(
                    primary.holding_spells[
                        "right_censored"
                    ].astype(bool).sum()
                )
                if len(primary.holding_spells)
                else 0
            ),
        },
        "rank_quality": {
            "mean_current_top10_overlap_full_target": (
                float(full_sessions["top10_overlap"].mean())
                if len(full_sessions)
                else None
            ),
            "mean_top10_overlap_normalized_all_sessions": (
                float(
                    sessions[
                        "top10_overlap_normalized"
                    ].dropna().mean()
                )
                if sessions[
                    "top10_overlap_normalized"
                ].notna().any()
                else None
            ),
            "mean_current_top20_overlap": float(
                sessions["top20_overlap"].mean()
            ),
            "mean_top20_overlap_normalized": (
                float(
                    sessions[
                        "top20_overlap_normalized"
                    ].dropna().mean()
                )
                if sessions[
                    "top20_overlap_normalized"
                ].notna().any()
                else None
            ),
            "mean_target_rank": (
                float(memberships["rank_consensus"].mean())
                if len(memberships)
                else None
            ),
            "median_target_rank": (
                float(memberships["rank_consensus"].median())
                if len(memberships)
                else None
            ),
            "mean_worst_held_rank": (
                float(
                    sessions[
                        "worst_target_rank"
                    ].dropna().mean()
                )
                if sessions["worst_target_rank"].notna().any()
                else None
            ),
            "target_rank_gt20_name_days": (
                int(memberships["rank_consensus"].gt(20).sum())
                if len(memberships)
                else 0
            ),
            "sessions_with_target_rank_gt20": int(
                sessions["target_rank_gt20_count"].gt(0).sum()
            ),
        },
        "decision_state_behavior": {
            **pending_metrics,
            "confirmed_exit_count": confirmed_exit_count,
            "universe_exit_count": universe_exit_count,
            "soft_replacement_count": soft_replacement_count,
            "vacancy_fill_count": vacancy_fill_count,
            "fresh_top10_rejected_unconfirmed_count": (
                fresh_rejected_count
            ),
            "unfilled_no_qualified_challenger_sessions": int(
                sessions["capacity_state"]
                .eq("UNFILLED_NO_QUALIFIED_CHALLENGER")
                .sum()
            ),
            "unfilled_vacancy_days": int(
                sessions["unfilled_slots"].sum()
            ),
        },
        "capacity": {
            "mean_target_size": float(
                sessions["target_size"].mean()
            ),
            "median_target_size": float(
                sessions["target_size"].median()
            ),
            "minimum_target_size": int(
                sessions["target_size"].min()
            ),
            "share_target_size_10": _safe_rate(
                sessions["target_size"].eq(10)
            ),
            "share_target_size_9": _safe_rate(
                sessions["target_size"].eq(9)
            ),
            "share_target_size_le8": _safe_rate(
                sessions["target_size"].le(8)
            ),
        },
        "stability_across_time": _build_time_segments(
            primary,
            source,
        ),
        "correctness": {
            **correctness,
            "deterministic_second_pass_match": True,
            "primary_plan_digest": primary.plan_digest,
            "secondary_plan_digest": secondary.plan_digest,
        },
    }

    gates = evaluate_gates(metrics)
    status = (
        "DECISION_V2_MINIMAL_STRUCTURAL_ACCEPT"
        if all(bool(gate["pass"]) for gate in gates.values())
        else "DECISION_V2_MINIMAL_STRUCTURAL_REJECT"
    )

    return {
        "schema_version": (
            "decision_v2_minimal_structural_replay_v1"
        ),
        "status": status,
        "source": {
            "manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
            "score_sha256": EXPECTED_SOURCE_SCORE_SHA256,
            "score_sessions": EXPECTED_SCORE_SESSIONS,
            "score_rows": EXPECTED_SCORE_ROWS,
            "alpha_model_id": EXPECTED_ALPHA_MODEL_ID,
            "alpha_model_fingerprint": (
                EXPECTED_ALPHA_MODEL_FINGERPRINT
            ),
            "decision_rule_id": (
                V4_X1_DECISION_V2_MINIMAL_PROFILE_V1.rule_id
            ),
        },
        "guards": {
            "realized_returns_loaded": False,
            "historical_pnl_computed": False,
            "target_outcome_ledger_loaded": False,
            "protected_or_fresh_forward_access": False,
            "provider_or_network_calls": False,
            "model_refit_or_retune": False,
            "decision_parameter_sweep": False,
            "alternative_thresholds_tested": False,
            "fold_resets": False,
            "preroll_used": False,
        },
        "metrics": metrics,
        "gates": gates,
    }


def evaluate_gates(
    metrics: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    churn = metrics["turnover_churn"]
    holding = metrics["holding_persistence"]
    rank_quality = metrics["rank_quality"]
    capacity = metrics["capacity"]
    correctness = metrics["correctness"]

    gate_a_conditions = {
        "no_target_size_gt10": bool(
            correctness["no_target_size_gt10"]
        ),
        "no_duplicate_target_ticker": bool(
            correctness["no_duplicate_target_ticker"]
        ),
        "no_unqualified_nonbootstrap_entrant": (
            int(
                correctness[
                    "unqualified_nonbootstrap_entrant_violations"
                ]
            )
            == 0
        ),
        "no_one_observation_gt20_exit": (
            int(
                correctness[
                    "one_observation_gt20_exit_violations"
                ]
            )
            == 0
        ),
        "no_confirmed_gt20_incumbent_retained": (
            int(
                correctness[
                    "confirmed_gt20_incumbent_retained_violations"
                ]
            )
            == 0
        ),
        "no_soft_replacement_gap_violation": (
            int(
                correctness[
                    "soft_replacement_gap_violations"
                ]
            )
            == 0
        ),
        "deterministic_second_pass_match": bool(
            correctness["deterministic_second_pass_match"]
        ),
    }
    gate_b_conditions = {
        "mean_replacements_per_transition": (
            float(
                churn["replacement_distribution"]["mean"]
            )
            <= GATE_LIMITS[
                "mean_replacements_per_transition_max"
            ]
        ),
        "turnover_ratio_vs_naive": (
            float(
                churn[
                    "turnover_ratio_vs_naive_exact_daily_top10"
                ]
            )
            <= GATE_LIMITS["turnover_ratio_vs_naive_max"]
        ),
        "share_transitions_ge3_replacements": (
            float(
                churn["transition_distribution"]["share_ge3"]
            )
            <= GATE_LIMITS[
                "share_transitions_ge3_replacements_max"
            ]
        ),
    }
    gate_c_conditions = {
        "median_completed_holding_spell": (
            float(
                holding[
                    "completed_duration_sessions"
                ]["median"]
            )
            >= GATE_LIMITS[
                "median_completed_holding_spell_min"
            ]
        ),
        "one_session_completed_holding_share": (
            float(holding["one_session_holding_share"])
            <= GATE_LIMITS[
                "one_session_completed_holding_share_max"
            ]
        ),
    }
    gate_d_conditions = {
        "mean_full_target_top10_overlap": (
            float(
                rank_quality[
                    "mean_current_top10_overlap_full_target"
                ]
            )
            >= GATE_LIMITS[
                "mean_full_target_top10_overlap_min"
            ]
        ),
        "mean_target_rank": (
            float(rank_quality["mean_target_rank"])
            <= GATE_LIMITS["mean_target_rank_max"]
        ),
    }
    gate_e_conditions = {
        "mean_target_size": (
            float(capacity["mean_target_size"])
            >= GATE_LIMITS["mean_target_size_min"]
        ),
        "share_target_size_10": (
            float(capacity["share_target_size_10"])
            >= GATE_LIMITS["share_target_size_10_min"]
        ),
        "share_target_size_le8": (
            float(capacity["share_target_size_le8"])
            <= GATE_LIMITS["share_target_size_le8_max"]
        ),
    }
    gate_f_conditions = {
        "no_hidden_stale_state": (
            int(correctness["stale_state_violations"]) == 0
        ),
    }

    groups = {
        "A_correctness_determinism": gate_a_conditions,
        "B_churn_reduction": gate_b_conditions,
        "C_holding_persistence": gate_c_conditions,
        "D_rank_quality_preservation": gate_d_conditions,
        "E_capacity": gate_e_conditions,
        "F_no_hidden_stale_state": gate_f_conditions,
    }
    return {
        name: {
            "pass": all(conditions.values()),
            "conditions": conditions,
        }
        for name, conditions in groups.items()
    }


def run_structural_replay(
    source: PinnedReplaySource,
) -> StructuralReplayResult:
    # Two in-memory passes are part of one authorized evaluation and exist
    # solely to satisfy the preregistered determinism gate. They use the
    # exact same already-loaded pinned score frame and no alternate policy.
    primary = replay_once(source)
    secondary = replay_once(source)
    summary = summarize_replay(
        primary,
        secondary,
        source,
    )
    return StructuralReplayResult(
        primary=primary,
        summary=summary,
    )


def _frame_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(
        index=False,
        lineterminator="\n",
    ).encode("utf-8")


def write_structural_replay_artifacts(
    result: StructuralReplayResult,
    output_dir: str | Path,
) -> Path:
    destination = Path(output_dir).expanduser().resolve()
    if destination.exists():
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_OUTPUT_ALREADY_EXISTS:{destination}"
        )

    staging = destination.with_name(
        destination.name + ".staging"
    )
    if staging.exists():
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_STAGING_ALREADY_EXISTS:{staging}"
        )
    staging.mkdir(parents=True, exist_ok=False)

    outputs: dict[str, bytes] = {
        "summary.json": (
            json.dumps(
                result.summary,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8"),
        "decision_session_ledger.csv": _frame_to_csv_bytes(
            result.primary.session_ledger
        ),
        "decision_membership_ledger.csv": _frame_to_csv_bytes(
            result.primary.membership_ledger
        ),
        "decision_intent_ledger.csv": _frame_to_csv_bytes(
            result.primary.intent_ledger
        ),
        "decision_state_ledger.csv": _frame_to_csv_bytes(
            result.primary.state_ledger
        ),
        "holding_spells.csv": _frame_to_csv_bytes(
            result.primary.holding_spells
        ),
        "fold_boundary_transitions.csv": _frame_to_csv_bytes(
            result.primary.fold_boundaries
        ),
    }

    artifact_hashes: dict[str, str] = {}
    for name, content in outputs.items():
        path = staging / name
        path.write_bytes(content)
        artifact_hashes[name] = hashlib.sha256(
            content
        ).hexdigest()

    manifest = {
        "schema_version": (
            "decision_v2_minimal_structural_replay_manifest_v1"
        ),
        "status": result.summary["status"],
        "source": result.summary["source"],
        "guards": result.summary["guards"],
        "plan_digest": result.primary.plan_digest,
        "artifacts": artifact_hashes,
    }
    manifest_path = staging / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    staging.rename(destination)
    return destination / "MANIFEST.json"
