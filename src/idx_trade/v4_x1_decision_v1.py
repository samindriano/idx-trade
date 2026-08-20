from __future__ import annotations

import pandas as pd

from .v4_x1_decision_v1_contract import (
    EXPECTED_CONFIG_SHA256, EXPECTED_ALPHA_MODEL_ID, EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_GENERATION, TARGET_POSITIONS, ENTRY_RANK_MAX, HARD_EXIT_RANK_GT,
    REPLACEMENT_RANK_GAP_MIN, SHADOW_STATE_SOURCE, EXECUTION_REFERENCE,
    EXPECTED_FREEZE_BOUNDARY, EXPECTED_SCIENTIFIC_BLOBS, _VERIFIED_TOKEN,
    REQUIRED_SCORE_COLUMNS, DecisionV1Error, VerifiedScoreSession, ShadowPortfolioState,
    TradeIntent, DecisionPlan, verify_frozen_config, _normalize_ticker,
)
from .v4_x1_decision_v1_verify import verify_v4_x1_score_artifact

def _validate_shadow_state(state: ShadowPortfolioState, decision_date: str) -> tuple[str, ...]:
    if not isinstance(state, ShadowPortfolioState):
        raise DecisionV1Error("DECISION_V1_SHADOW_STATE_TYPE_REQUIRED")
    if state.source != SHADOW_STATE_SOURCE:
        raise DecisionV1Error("DECISION_V1_NON_SHADOW_STATE_FORBIDDEN")
    positions = tuple(_normalize_ticker(t) for t in state.positions)
    if len(set(positions)) != len(positions):
        raise DecisionV1Error("DECISION_V1_SHADOW_DUPLICATE_POSITION")
    if len(positions) > TARGET_POSITIONS:
        raise DecisionV1Error("DECISION_V1_SHADOW_OVER_TARGET")
    if state.as_of_session_date is not None:
        parsed = pd.to_datetime(state.as_of_session_date, errors="coerce")
        if pd.isna(parsed):
            raise DecisionV1Error("DECISION_V1_SHADOW_DATE_INVALID")
        shadow_date = pd.Timestamp(parsed).tz_localize(None).normalize()
        if shadow_date > pd.Timestamp(decision_date):
            raise DecisionV1Error("DECISION_V1_SHADOW_STATE_FROM_FUTURE")
    return tuple(sorted(positions))


def plan_decision_v1(
    verified: VerifiedScoreSession,
    shadow_state: ShadowPortfolioState,
) -> DecisionPlan:
    if not isinstance(verified, VerifiedScoreSession) or verified._verification_token is not _VERIFIED_TOKEN:
        raise DecisionV1Error("DECISION_V1_VERIFIED_SCORE_SESSION_REQUIRED")
    if verified.model_id != EXPECTED_ALPHA_MODEL_ID or verified.model_fingerprint != EXPECTED_ALPHA_MODEL_FINGERPRINT:
        raise DecisionV1Error("DECISION_V1_VERIFIED_LINEAGE_CHANGED")

    current = _validate_shadow_state(shadow_state, verified.session_date)
    score_view = verified.scores.sort_values("rank_consensus", kind="mergesort").reset_index(drop=True)
    ranks = dict(zip(score_view["ticker"], score_view["rank_consensus"], strict=True))

    mandatory_sells: list[TradeIntent] = []
    replacement_sells: list[TradeIntent] = []
    buy_intents: list[TradeIntent] = []
    retained: set[str] = set()

    for ticker in current:
        rank = ranks.get(ticker)
        if rank is None:
            mandatory_sells.append(TradeIntent(
                side="SELL_INTENT",
                ticker=ticker,
                rank_consensus=None,
                reason="NO_LONGER_IN_V4_X1_DECISION_UNIVERSE",
            ))
        elif rank > HARD_EXIT_RANK_GT:
            mandatory_sells.append(TradeIntent(
                side="SELL_INTENT",
                ticker=ticker,
                rank_consensus=int(rank),
                reason="HARD_EXIT_RANK_GT20",
            ))
        else:
            retained.add(ticker)

    mandatory_sells = sorted(
        mandatory_sells,
        key=lambda intent: (
            0 if intent.rank_consensus is None else 1,
            -(intent.rank_consensus or 0),
            intent.ticker,
        ),
    )

    top10 = score_view.loc[
        score_view["rank_consensus"].le(ENTRY_RANK_MAX), ["ticker", "rank_consensus"]
    ].sort_values(["rank_consensus", "ticker"], kind="mergesort")
    candidates = [
        (str(row.ticker), int(row.rank_consensus))
        for row in top10.itertuples(index=False)
        if str(row.ticker) not in retained
    ]

    unconditional_vacancies = TARGET_POSITIONS - len(current)
    vacancy_buys: list[tuple[str, int]] = []
    while len(retained) < TARGET_POSITIONS and candidates:
        ticker, rank = candidates.pop(0)
        retained.add(ticker)
        vacancy_buys.append((ticker, rank))

    if len(retained) != TARGET_POSITIONS:
        raise DecisionV1Error("DECISION_V1_CANNOT_REACH_TARGET_POSITIONS")

    paired_mandatory: list[TradeIntent] = []
    for index, (ticker, rank) in enumerate(vacancy_buys):
        if index < unconditional_vacancies:
            buy_intents.append(TradeIntent(
                side="BUY_INTENT",
                ticker=ticker,
                rank_consensus=rank,
                reason="FILL_VACANCY_TOP10",
            ))
            continue
        mandatory_index = index - unconditional_vacancies
        if mandatory_index >= len(mandatory_sells):
            raise DecisionV1Error("DECISION_V1_MANDATORY_PAIRING_INVARIANT_BROKEN")
        exit_intent = mandatory_sells[mandatory_index]
        paired_mandatory.append(TradeIntent(
            side="SELL_INTENT",
            ticker=exit_intent.ticker,
            rank_consensus=exit_intent.rank_consensus,
            reason=exit_intent.reason,
            replacement_peer=ticker,
        ))
        buy_intents.append(TradeIntent(
            side="BUY_INTENT",
            ticker=ticker,
            rank_consensus=rank,
            reason="MANDATORY_EXIT_REPLACEMENT",
            replacement_peer=exit_intent.ticker,
        ))

    if len(paired_mandatory) != len(mandatory_sells):
        raise DecisionV1Error("DECISION_V1_MANDATORY_EXIT_WITHOUT_TARGET_REPLACEMENT")
    mandatory_sells = paired_mandatory

    while candidates:
        replaceable = sorted(
            (
                (ticker, int(ranks[ticker]))
                for ticker in retained
                if int(ranks[ticker]) > ENTRY_RANK_MAX
            ),
            key=lambda pair: (-pair[1], pair[0]),
        )
        if not replaceable:
            break
        candidate_ticker, candidate_rank = candidates[0]
        incumbent_ticker, incumbent_rank = replaceable[0]
        if incumbent_rank - candidate_rank < REPLACEMENT_RANK_GAP_MIN:
            break
        candidates.pop(0)
        retained.remove(incumbent_ticker)
        retained.add(candidate_ticker)
        replacement_sells.append(TradeIntent(
            side="SELL_INTENT",
            ticker=incumbent_ticker,
            rank_consensus=incumbent_rank,
            reason="RANK_GAP_REPLACEMENT",
            replacement_peer=candidate_ticker,
        ))
        buy_intents.append(TradeIntent(
            side="BUY_INTENT",
            ticker=candidate_ticker,
            rank_consensus=candidate_rank,
            reason="RANK_GAP_REPLACEMENT",
            replacement_peer=incumbent_ticker,
        ))

    sell_intents = mandatory_sells + replacement_sells

    if len(retained) != TARGET_POSITIONS:
        raise DecisionV1Error("DECISION_V1_TARGET_POSITION_INVARIANT_BROKEN")
    if any(ranks.get(t, 10**9) > HARD_EXIT_RANK_GT for t in retained):
        raise DecisionV1Error("DECISION_V1_HARD_EXIT_INVARIANT_BROKEN")

    buy_names = {x.ticker for x in buy_intents}
    sell_names = {x.ticker for x in sell_intents}
    if buy_names & sell_names:
        raise DecisionV1Error("DECISION_V1_BUY_SELL_COLLISION")
    if any((x.rank_consensus or 10**9) > ENTRY_RANK_MAX for x in buy_intents):
        raise DecisionV1Error("DECISION_V1_BUY_OUTSIDE_TOP10")

    by_sell_peer = {
        x.replacement_peer: x.ticker
        for x in sell_intents
        if x.replacement_peer is not None
    }
    for buy in buy_intents:
        if buy.reason in {"MANDATORY_EXIT_REPLACEMENT", "RANK_GAP_REPLACEMENT"}:
            if buy.replacement_peer is None or by_sell_peer.get(buy.ticker) != buy.replacement_peer:
                raise DecisionV1Error("DECISION_V1_REPLACEMENT_PAIRING_BROKEN")

    unheld_top10 = [
        (ticker, rank) for ticker, rank in candidates if ticker not in retained
    ]
    buffer_incumbents = [
        (ticker, int(ranks[ticker])) for ticker in retained if int(ranks[ticker]) > ENTRY_RANK_MAX
    ]
    if unheld_top10 and buffer_incumbents:
        best_candidate_rank = min(rank for _, rank in unheld_top10)
        worst_incumbent_rank = max(rank for _, rank in buffer_incumbents)
        if worst_incumbent_rank - best_candidate_rank >= REPLACEMENT_RANK_GAP_MIN:
            raise DecisionV1Error("DECISION_V1_REPLACEMENT_FIXED_POINT_BROKEN")

    target = tuple(sorted(retained, key=lambda t: (int(ranks[t]), t)))
    hold = tuple(t for t in target if t in set(current) and t not in sell_names)
    return DecisionPlan(
        decision_session_date=verified.session_date,
        execution_reference=EXECUTION_REFERENCE,
        current_shadow_positions=current,
        target_positions=target,
        buy_intents=tuple(buy_intents),
        sell_intents=tuple(sell_intents),
        hold_tickers=hold,
        alpha_tie_rows=verified.alpha_tie_rows,
    )
