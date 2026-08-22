from __future__ import annotations

from .decision_v3_graded_evidence import (
    CapacityState,
    ChallengerObservation,
    ChallengerState,
    DecisionV3Error,
    DecisionV3Intent,
    DecisionV3Plan,
    DecisionV3Profile,
    DecisionV3ShadowState,
    IncumbentObservation,
    IncumbentState,
    RankSession,
    _append_vacancy_fill,
    _challengers,
    _parse_date,
    _sort_tickers_by_rank,
    _validate_rank_session,
    _validate_shadow_state,
)


def _is_severe_exit_session(
    incumbent_observations: list[IncumbentObservation],
) -> bool:
    """Freeze the V4 severe-session flag from start-of-session incumbents only."""
    return any(
        obs.state == "SEVERE_DETERIORATION_EXIT"
        for obs in incumbent_observations
    )


def plan_decision_v4_refill_decoupling(
    current_session: RankSession,
    previous_session: RankSession | None,
    shadow_state: DecisionV3ShadowState,
    profile: DecisionV3Profile,
) -> DecisionV3Plan:
    """Decision V3 semantics with the preregistered V4 refill decoupling only."""
    profile.validate()
    current = _validate_rank_session(current_session, profile)
    current_positions = _validate_shadow_state(shadow_state, profile)

    is_bootstrap = shadow_state.as_of_session_date is None
    if is_bootstrap:
        if previous_session is not None:
            raise DecisionV3Error("DECISION_V4_BOOTSTRAP_PREROLL_FORBIDDEN")
        ordered = sorted(current.ranks.items(), key=lambda item: (item[1], item[0]))
        selected = tuple(ticker for ticker, _ in ordered[: profile.target_count_max])
        buys = tuple(
            DecisionV3Intent(
                side="BUY_INTENT",
                ticker=ticker,
                rank_consensus=current.ranks[ticker],
                reason="BOOTSTRAP_TOP10",
            )
            for ticker in selected
        )
        unfilled_slots = profile.target_count_max - len(selected)
        return DecisionV3Plan(
            decision_session_date=current.session_date,
            current_shadow_positions=(),
            target_positions=selected,
            buy_intents=buys,
            sell_intents=(),
            hold_tickers=(),
            incumbent_observations=(),
            challenger_observations=(),
            unfilled_slots=unfilled_slots,
            capacity_state=(
                "FULL"
                if unfilled_slots == 0
                else "UNFILLED_NO_QUALIFIED_CHALLENGER"
            ),
            rule_id=profile.rule_id,
            bootstrap=True,
        )

    if previous_session is None:
        raise DecisionV3Error("DECISION_V4_PREVIOUS_SESSION_REQUIRED")
    previous = _validate_rank_session(previous_session, profile)
    if shadow_state.as_of_session_date != previous.session_date:
        raise DecisionV3Error("DECISION_V4_STATE_PREVIOUS_SESSION_MISMATCH")
    if _parse_date(previous.session_date, "DECISION_V4_PREVIOUS_DATE_INVALID") >= _parse_date(
        current.session_date, "DECISION_V4_CURRENT_DATE_INVALID"
    ):
        raise DecisionV3Error("DECISION_V4_SESSION_ORDER_INVALID")

    held_at_start = set(current_positions)
    missing_from_previous = sorted(held_at_start - set(previous.ranks))
    if missing_from_previous:
        raise DecisionV3Error(
            "DECISION_V4_STATE_POSITION_MISSING_FROM_PREVIOUS_SESSION:"
            + ",".join(missing_from_previous)
        )

    incumbent_observations: list[IncumbentObservation] = []
    sell_intents: list[DecisionV3Intent] = []
    retained: set[str] = set()
    acceptable_for_soft_replace: set[str] = set()

    # This whole classification block intentionally mirrors Decision V3.
    # The severe-session flag is derived only after every start-of-session
    # incumbent has been classified, before challengers/refill/replacement.
    for ticker in current_positions:
        previous_rank = previous.ranks[ticker]
        current_rank = current.ranks.get(ticker)
        if current_rank is None:
            state: IncumbentState = "UNIVERSE_EXIT"
            sell_intents.append(
                DecisionV3Intent(
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
        elif current_rank <= profile.mild_deterioration_max_rank:
            if previous_rank <= profile.retention_zone_max_rank:
                state = "MILD_DETERIORATION_PENDING_1"
                retained.add(ticker)
            else:
                state = "CONFIRMED_MILD_DETERIORATION_EXIT"
                sell_intents.append(
                    DecisionV3Intent(
                        side="SELL_INTENT",
                        ticker=ticker,
                        rank_consensus=current_rank,
                        reason="CONFIRMED_MILD_DETERIORATION_EXIT",
                    )
                )
        else:
            state = "SEVERE_DETERIORATION_EXIT"
            sell_intents.append(
                DecisionV3Intent(
                    side="SELL_INTENT",
                    ticker=ticker,
                    rank_consensus=current_rank,
                    reason="SEVERE_DETERIORATION_EXIT",
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

    # PREREGISTERED V4 MECHANISM: freeze once from start-of-session
    # incumbent classification only.
    severe_exit_session = _is_severe_exit_session(incumbent_observations)

    challenger_observations = _challengers(current, previous, held_at_start, profile)
    by_tier: dict[ChallengerState, list[ChallengerObservation]] = {
        "A_CORE": [],
        "B_NEAR": [],
        "C_DISTANT": [],
        "D_NO_HISTORY": [],
    }
    for obs in challenger_observations:
        by_tier[obs.state].append(obs)
    for candidates in by_tier.values():
        candidates.sort(key=lambda obs: (obs.current_rank, obs.ticker))

    buy_intents: list[DecisionV3Intent] = []

    # This is the only behavioral divergence from Decision V3.
    # A severe-exit session restricts every vacancy, regardless of origin,
    # to A_CORE supply. Non-severe sessions preserve V3 A -> B -> C priority.
    vacancy_tiers: tuple[ChallengerState, ...] = (
        ("A_CORE",)
        if severe_exit_session
        else ("A_CORE", "B_NEAR", "C_DISTANT")
    )
    for tier in vacancy_tiers:
        while len(retained) < profile.target_count_max and by_tier[tier]:
            challenger = by_tier[tier].pop(0)
            if challenger.ticker in retained:
                continue
            _append_vacancy_fill(challenger, retained, buy_intents)

    # EXACT V3 Tier-A soft replacement semantics remain active after refill.
    available_core = by_tier["A_CORE"]
    while available_core and acceptable_for_soft_replace:
        challenger = available_core[0]
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
        if (
            incumbent_rank - challenger.current_rank
            < profile.soft_replacement_min_rank_advantage
        ):
            break

        available_core.pop(0)
        retained.remove(incumbent_ticker)
        acceptable_for_soft_replace.remove(incumbent_ticker)
        retained.add(challenger.ticker)
        sell_intents.append(
            DecisionV3Intent(
                side="SELL_INTENT",
                ticker=incumbent_ticker,
                rank_consensus=incumbent_rank,
                reason="SOFT_RANK_GAP_REPLACEMENT",
                replacement_peer=challenger.ticker,
            )
        )
        buy_intents.append(
            DecisionV3Intent(
                side="BUY_INTENT",
                ticker=challenger.ticker,
                rank_consensus=challenger.current_rank,
                reason="SOFT_RANK_GAP_REPLACEMENT",
                replacement_peer=incumbent_ticker,
            )
        )

    if len(retained) > profile.target_count_max:
        raise DecisionV3Error("DECISION_V4_TARGET_OVER_CAPACITY")
    if not profile.allow_temporary_underfill and len(retained) < profile.target_count_max:
        raise DecisionV3Error("DECISION_V4_UNDERFILL_FORBIDDEN")

    challenger_by_ticker = {obs.ticker: obs for obs in challenger_observations}
    expected_buy_tier = {
        "TIER_A_VACANCY_FILL": "A_CORE",
        "TIER_B_VACANCY_FILL": "B_NEAR",
        "TIER_C_RESIDUAL_VACANCY_FILL": "C_DISTANT",
        "SOFT_RANK_GAP_REPLACEMENT": "A_CORE",
    }
    for buy in buy_intents:
        challenger = challenger_by_ticker.get(buy.ticker)
        if challenger is None:
            raise DecisionV3Error("DECISION_V4_NONBOOTSTRAP_BUY_NOT_CHALLENGER")
        expected_tier = expected_buy_tier.get(buy.reason)
        if expected_tier is None or challenger.state != expected_tier:
            raise DecisionV3Error("DECISION_V4_BUY_PERMISSION_TIER_MISMATCH")
        if challenger.state == "D_NO_HISTORY":
            raise DecisionV3Error("DECISION_V4_NO_HISTORY_ENTRY_FORBIDDEN")
        if (
            severe_exit_session
            and buy.reason in {"TIER_B_VACANCY_FILL", "TIER_C_RESIDUAL_VACANCY_FILL"}
        ):
            raise DecisionV3Error("DECISION_V4_SEVERE_SESSION_NONCORE_REFILL_FORBIDDEN")

    sell_names = {intent.ticker for intent in sell_intents}
    buy_names = {intent.ticker for intent in buy_intents}
    if sell_names & buy_names:
        raise DecisionV3Error("DECISION_V4_BUY_SELL_COLLISION")

    observation_by_ticker = {obs.ticker: obs for obs in incumbent_observations}
    for ticker in retained:
        obs = observation_by_ticker.get(ticker)
        if obs is None:
            continue
        if obs.state in {
            "CONFIRMED_MILD_DETERIORATION_EXIT",
            "SEVERE_DETERIORATION_EXIT",
            "UNIVERSE_EXIT",
        }:
            raise DecisionV3Error("DECISION_V4_MANDATORY_EXIT_RETAINED")
        if obs.current_rank is None:
            raise DecisionV3Error("DECISION_V4_ABSENT_TARGET_RETAINED")
        if obs.current_rank > profile.mild_deterioration_max_rank:
            raise DecisionV3Error("DECISION_V4_SEVERE_RANK_RETAINED")
        if (
            profile.retention_zone_max_rank
            < obs.current_rank
            <= profile.mild_deterioration_max_rank
            and obs.previous_rank > profile.retention_zone_max_rank
        ):
            raise DecisionV3Error("DECISION_V4_SECOND_CONSECUTIVE_MILD_RETAINED")

    for intent in sell_intents:
        if intent.reason == "SEVERE_DETERIORATION_EXIT":
            obs = observation_by_ticker[intent.ticker]
            if not (
                obs.current_rank is not None
                and obs.current_rank > profile.mild_deterioration_max_rank
            ):
                raise DecisionV3Error("DECISION_V4_SEVERE_EXIT_WITHOUT_SEVERE_RANK")
        elif intent.reason == "CONFIRMED_MILD_DETERIORATION_EXIT":
            obs = observation_by_ticker[intent.ticker]
            if not (
                obs.current_rank is not None
                and profile.retention_zone_max_rank
                < obs.current_rank
                <= profile.mild_deterioration_max_rank
                and obs.previous_rank > profile.retention_zone_max_rank
            ):
                raise DecisionV3Error("DECISION_V4_CONFIRMED_MILD_EXIT_INVALID")
        elif intent.reason == "SOFT_RANK_GAP_REPLACEMENT":
            if intent.replacement_peer is None:
                raise DecisionV3Error("DECISION_V4_SOFT_REPLACEMENT_PEER_MISSING")
            challenger = challenger_by_ticker[intent.replacement_peer]
            if challenger.state != "A_CORE":
                raise DecisionV3Error("DECISION_V4_NONCORE_SOFT_REPLACEMENT")
            if (
                (intent.rank_consensus or 0) - challenger.current_rank
                < profile.soft_replacement_min_rank_advantage
            ):
                raise DecisionV3Error("DECISION_V4_SOFT_REPLACEMENT_GAP_BROKEN")

    target = _sort_tickers_by_rank(retained, current.ranks)
    hold = tuple(
        ticker
        for ticker in target
        if ticker in held_at_start and ticker not in sell_names
    )
    incumbent_observations.sort(key=lambda obs: obs.ticker)
    challenger_observations = tuple(
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

    return DecisionV3Plan(
        decision_session_date=current.session_date,
        current_shadow_positions=current_positions,
        target_positions=target,
        buy_intents=tuple(buy_intents),
        sell_intents=tuple(sell_intents),
        hold_tickers=hold,
        incumbent_observations=tuple(incumbent_observations),
        challenger_observations=challenger_observations,
        unfilled_slots=unfilled_slots,
        capacity_state=capacity_state,
        rule_id=profile.rule_id,
        bootstrap=False,
    )
