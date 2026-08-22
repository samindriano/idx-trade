from __future__ import annotations

from dataclasses import replace

from .decision_v2_minimal import (
    CapacityState,
    ChallengerObservation,
    DecisionV2Error,
    DecisionV2Intent,
    DecisionV2Plan,
    DecisionV2Profile,
    DecisionV2ShadowState,
    IncumbentObservation,
    IncumbentState,
    RankSession,
    _challengers,
    _parse_date,
    _sort_tickers_by_rank,
    _validate_rank_session,
    _validate_shadow_state,
)


RULE_ID = "V4_X1_DECISION_V2_1_CONSERVATIVE_SEVERE_REPLACEMENT_V1"
SEVERE_PENDING_MIN_RANK = 51
ESTABLISHED_CHALLENGER_PREVIOUS_RANK_MAX = 10

V2_1_PROFILE = DecisionV2Profile(
    rule_id=RULE_ID,
    target_count_max=10,
    strong_zone_max_rank=10,
    retention_zone_max_rank=20,
    soft_replacement_min_rank_advantage=5,
    entry_confirmation_previous_rank_max=20,
    exit_confirmation_consecutive_outside_retention=2,
    universe_absence_exit_immediate=True,
    allow_temporary_underfill=True,
    bootstrap_first_session_exact_top10=True,
)


def plan_decision_v2_1_conservative_severe_replacement(
    current_session: RankSession,
    previous_session: RankSession | None,
    shadow_state: DecisionV2ShadowState,
    profile: DecisionV2Profile = V2_1_PROFILE,
) -> DecisionV2Plan:
    """Exact V2 Minimal plus one conservative discretionary replacement permission.

    V2 behavior is preserved except after ordinary vacancy filling and before the
    existing 11..20 soft-replacement stage. A first-day pending incumbent whose
    current rank is >50 may be replaced one-for-one only by a still-unused
    qualified challenger that is Top10 on both the current and previous session.

    The severe observation alone never creates a vacancy. If no established
    challenger is available, the incumbent receives the original V2 one-session
    grace. Temporary underfill and V2 vacancy qualification are unchanged.
    """

    profile.validate()
    if profile.strong_zone_max_rank != ESTABLISHED_CHALLENGER_PREVIOUS_RANK_MAX:
        raise DecisionV2Error("DECISION_V2_1_STRONG_ZONE_CHANGED")
    if profile.retention_zone_max_rank != 20:
        raise DecisionV2Error("DECISION_V2_1_RETENTION_ZONE_CHANGED")

    current = _validate_rank_session(current_session, profile)
    current_positions = _validate_shadow_state(shadow_state, profile)

    is_bootstrap = shadow_state.as_of_session_date is None
    if is_bootstrap:
        if previous_session is not None:
            raise DecisionV2Error("DECISION_V2_1_BOOTSTRAP_PREROLL_FORBIDDEN")
        ordered = sorted(current.ranks.items(), key=lambda item: (item[1], item[0]))
        selected = tuple(ticker for ticker, _ in ordered[: profile.target_count_max])
        buys = tuple(
            DecisionV2Intent(
                side="BUY_INTENT",
                ticker=ticker,
                rank_consensus=current.ranks[ticker],
                reason="BOOTSTRAP_TOP10",
            )
            for ticker in selected
        )
        return DecisionV2Plan(
            decision_session_date=current.session_date,
            current_shadow_positions=(),
            target_positions=selected,
            buy_intents=buys,
            sell_intents=(),
            hold_tickers=(),
            incumbent_observations=(),
            challenger_observations=(),
            unfilled_slots=profile.target_count_max - len(selected),
            capacity_state="FULL",
            rule_id=profile.rule_id,
            bootstrap=True,
        )

    if previous_session is None:
        raise DecisionV2Error("DECISION_V2_1_PREVIOUS_SESSION_REQUIRED")
    previous = _validate_rank_session(previous_session, profile)
    if shadow_state.as_of_session_date != previous.session_date:
        raise DecisionV2Error("DECISION_V2_1_STATE_PREVIOUS_SESSION_MISMATCH")
    if _parse_date(previous.session_date, "DECISION_V2_1_PREVIOUS_DATE_INVALID") >= _parse_date(
        current.session_date, "DECISION_V2_1_CURRENT_DATE_INVALID"
    ):
        raise DecisionV2Error("DECISION_V2_1_SESSION_ORDER_INVALID")

    held_at_start = set(current_positions)
    missing_from_previous = sorted(held_at_start - set(previous.ranks))
    if missing_from_previous:
        raise DecisionV2Error(
            "DECISION_V2_1_STATE_POSITION_MISSING_FROM_PREVIOUS_SESSION:"
            + ",".join(missing_from_previous)
        )

    incumbent_observations: list[IncumbentObservation] = []
    sell_intents: list[DecisionV2Intent] = []
    retained: set[str] = set()
    acceptable_for_soft_replace: set[str] = set()
    severe_pending_for_established_replace: set[str] = set()

    for ticker in current_positions:
        previous_rank = previous.ranks[ticker]
        current_rank = current.ranks.get(ticker)
        if current_rank is None:
            state: IncumbentState = "UNIVERSE_EXIT"
            sell_intents.append(
                DecisionV2Intent(
                    side="SELL_INTENT",
                    ticker=ticker,
                    rank_consensus=None,
                    reason="UNIVERSE_EXIT",
                )
            )
        elif current_rank <= profile.strong_zone_max_rank:
            state = "STRONG_HOLD"
            retained.add(ticker)
        elif current_rank <= profile.retention_zone_max_rank:
            state = "ACCEPTABLE_HOLD"
            retained.add(ticker)
            acceptable_for_soft_replace.add(ticker)
        elif previous_rank <= profile.retention_zone_max_rank:
            state = "EXIT_PENDING_1"
            retained.add(ticker)
            if current_rank >= SEVERE_PENDING_MIN_RANK:
                severe_pending_for_established_replace.add(ticker)
        else:
            state = "CONFIRMED_EXIT"
            sell_intents.append(
                DecisionV2Intent(
                    side="SELL_INTENT",
                    ticker=ticker,
                    rank_consensus=current_rank,
                    reason="CONFIRMED_EXIT_GT20_2",
                )
            )
        incumbent_observations.append(
            IncumbentObservation(
                ticker=ticker,
                current_rank=current_rank,
                previous_rank=previous_rank,
                state=state,
            )
        )

    challenger_observations = _challengers(current, previous, held_at_start, profile)
    available_qualified = [obs for obs in challenger_observations if obs.qualified]
    available_qualified.sort(key=lambda obs: (obs.current_rank, obs.ticker))

    buy_intents: list[DecisionV2Intent] = []

    # Preserve V2 vacancy-fill priority exactly. This protects the existing right
    # to abstain: only V2-qualified challengers can fill real vacancies.
    while len(retained) < profile.target_count_max and available_qualified:
        challenger = available_qualified.pop(0)
        if challenger.ticker in retained:
            continue
        retained.add(challenger.ticker)
        buy_intents.append(
            DecisionV2Intent(
                side="BUY_INTENT",
                ticker=challenger.ticker,
                rank_consensus=challenger.current_rank,
                reason="QUALIFIED_VACANCY_FILL",
            )
        )

    # V2.1's only new permission: severe first-day pending incumbents may be
    # displaced only by an established (Top10 -> Top10) challenger. No incumbent
    # is sold unless the replacement is admitted in the same operation.
    while severe_pending_for_established_replace:
        established = [
            obs
            for obs in available_qualified
            if obs.previous_rank is not None
            and obs.previous_rank <= ESTABLISHED_CHALLENGER_PREVIOUS_RANK_MAX
        ]
        if not established:
            break
        established.sort(key=lambda obs: (obs.current_rank, obs.ticker))
        challenger = established[0]
        replaceable = sorted(
            (
                (ticker, current.ranks[ticker])
                for ticker in severe_pending_for_established_replace
                if ticker in retained
            ),
            key=lambda item: (-item[1], item[0]),
        )
        if not replaceable:
            break
        incumbent_ticker, incumbent_rank = replaceable[0]
        if incumbent_rank - challenger.current_rank < profile.soft_replacement_min_rank_advantage:
            raise DecisionV2Error("DECISION_V2_1_SEVERE_REPLACEMENT_GAP_UNEXPECTED")

        available_qualified = [
            obs for obs in available_qualified if obs.ticker != challenger.ticker
        ]
        retained.remove(incumbent_ticker)
        severe_pending_for_established_replace.remove(incumbent_ticker)
        retained.add(challenger.ticker)
        sell_intents.append(
            DecisionV2Intent(
                side="SELL_INTENT",
                ticker=incumbent_ticker,
                rank_consensus=incumbent_rank,
                reason="ESTABLISHED_SEVERE_PENDING_REPLACEMENT",
                replacement_peer=challenger.ticker,
            )
        )
        buy_intents.append(
            DecisionV2Intent(
                side="BUY_INTENT",
                ticker=challenger.ticker,
                rank_consensus=challenger.current_rank,
                reason="ESTABLISHED_SEVERE_PENDING_REPLACEMENT",
                replacement_peer=incumbent_ticker,
            )
        )

    # Preserve ordinary V2 11..20 soft replacement exactly, now using only the
    # remaining qualified challenger supply.
    while available_qualified and acceptable_for_soft_replace:
        challenger = available_qualified[0]
        replaceable = sorted(
            (
                (ticker, current.ranks[ticker])
                for ticker in acceptable_for_soft_replace
                if ticker in retained
            ),
            key=lambda item: (-item[1], item[0]),
        )
        if not replaceable:
            break
        incumbent_ticker, incumbent_rank = replaceable[0]
        if incumbent_rank - challenger.current_rank < profile.soft_replacement_min_rank_advantage:
            break
        available_qualified.pop(0)
        retained.remove(incumbent_ticker)
        acceptable_for_soft_replace.remove(incumbent_ticker)
        retained.add(challenger.ticker)
        sell_intents.append(
            DecisionV2Intent(
                side="SELL_INTENT",
                ticker=incumbent_ticker,
                rank_consensus=incumbent_rank,
                reason="SOFT_RANK_GAP_REPLACEMENT",
                replacement_peer=challenger.ticker,
            )
        )
        buy_intents.append(
            DecisionV2Intent(
                side="BUY_INTENT",
                ticker=challenger.ticker,
                rank_consensus=challenger.current_rank,
                reason="SOFT_RANK_GAP_REPLACEMENT",
                replacement_peer=incumbent_ticker,
            )
        )

    if len(retained) > profile.target_count_max:
        raise DecisionV2Error("DECISION_V2_1_TARGET_OVER_CAPACITY")
    if not profile.allow_temporary_underfill and len(retained) < profile.target_count_max:
        raise DecisionV2Error("DECISION_V2_1_UNDERFILL_FORBIDDEN")

    qualified_by_ticker = {
        obs.ticker: obs for obs in challenger_observations if obs.qualified
    }
    for buy in buy_intents:
        challenger = qualified_by_ticker.get(buy.ticker)
        if challenger is None:
            raise DecisionV2Error("DECISION_V2_1_UNQUALIFIED_NONBOOTSTRAP_BUY")
        if buy.reason == "ESTABLISHED_SEVERE_PENDING_REPLACEMENT":
            if challenger.previous_rank is None or challenger.previous_rank > ESTABLISHED_CHALLENGER_PREVIOUS_RANK_MAX:
                raise DecisionV2Error("DECISION_V2_1_SEVERE_REPLACEMENT_CHALLENGER_NOT_ESTABLISHED")

    sell_names = {intent.ticker for intent in sell_intents}
    buy_names = {intent.ticker for intent in buy_intents}
    if sell_names & buy_names:
        raise DecisionV2Error("DECISION_V2_1_BUY_SELL_COLLISION")

    observation_by_ticker = {obs.ticker: obs for obs in incumbent_observations}
    for intent in sell_intents:
        if intent.reason == "ESTABLISHED_SEVERE_PENDING_REPLACEMENT":
            obs = observation_by_ticker[intent.ticker]
            if not (
                obs.state == "EXIT_PENDING_1"
                and obs.current_rank is not None
                and obs.current_rank >= SEVERE_PENDING_MIN_RANK
                and obs.previous_rank <= profile.retention_zone_max_rank
                and intent.replacement_peer in qualified_by_ticker
            ):
                raise DecisionV2Error("DECISION_V2_1_INVALID_SEVERE_PENDING_REPLACEMENT")

    target = _sort_tickers_by_rank(retained, current.ranks)
    hold = tuple(
        ticker for ticker in target if ticker in held_at_start and ticker not in sell_names
    )
    incumbent_observations.sort(key=lambda obs: obs.ticker)
    challenger_tuple = tuple(
        sorted(challenger_observations, key=lambda obs: (obs.current_rank, obs.ticker))
    )
    sell_intents.sort(
        key=lambda intent: (
            0 if intent.rank_consensus is None else 1,
            -(intent.rank_consensus or 0),
            intent.ticker,
        )
    )
    buy_intents.sort(
        key=lambda intent: ((intent.rank_consensus or 10**9), intent.ticker)
    )

    unfilled_slots = profile.target_count_max - len(target)
    capacity_state: CapacityState = (
        "FULL" if unfilled_slots == 0 else "UNFILLED_NO_QUALIFIED_CHALLENGER"
    )
    return DecisionV2Plan(
        decision_session_date=current.session_date,
        current_shadow_positions=current_positions,
        target_positions=target,
        buy_intents=tuple(buy_intents),
        sell_intents=tuple(sell_intents),
        hold_tickers=hold,
        incumbent_observations=tuple(incumbent_observations),
        challenger_observations=challenger_tuple,
        unfilled_slots=unfilled_slots,
        capacity_state=capacity_state,
        rule_id=profile.rule_id,
        bootstrap=False,
    )
