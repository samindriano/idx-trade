from __future__ import annotations

from .decision_v2_minimal import (
    CapacityState,
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


RULE_ID = "V4_X1_DECISION_V2_2_COHERENT_VACANCY_ADMISSION_V1"
HEAD_ACCEPTABLE_MAX_RANK = 20

V2_2_PROFILE = DecisionV2Profile(
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


def _validate_head_ranks(
    current_ranks: dict[str, int],
    current_head_ranks: dict[str, tuple[int, int]],
) -> None:
    if set(current_head_ranks) != set(current_ranks):
        raise DecisionV2Error("DECISION_V2_2_HEAD_RANK_IDENTITY_MISMATCH")
    expected = set(range(1, len(current_ranks) + 1))
    h5 = set()
    h10 = set()
    for ticker, pair in current_head_ranks.items():
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise DecisionV2Error(f"DECISION_V2_2_HEAD_RANK_PAIR_INVALID:{ticker}")
        rank_h5, rank_h10 = pair
        for value in (rank_h5, rank_h10):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise DecisionV2Error(f"DECISION_V2_2_HEAD_RANK_INVALID:{ticker}")
        h5.add(rank_h5)
        h10.add(rank_h10)
    if h5 != expected or h10 != expected:
        raise DecisionV2Error("DECISION_V2_2_HEAD_RANKS_NOT_CONTIGUOUS")


def _coherent_for_vacancy(ticker: str, head_ranks: dict[str, tuple[int, int]]) -> bool:
    rank_h5, rank_h10 = head_ranks[ticker]
    return rank_h5 <= HEAD_ACCEPTABLE_MAX_RANK and rank_h10 <= HEAD_ACCEPTABLE_MAX_RANK


def plan_decision_v2_2_coherent_vacancy_admission(
    current_session: RankSession,
    previous_session: RankSession | None,
    shadow_state: DecisionV2ShadowState,
    current_head_ranks: dict[str, tuple[int, int]],
    profile: DecisionV2Profile = V2_2_PROFILE,
) -> DecisionV2Plan:
    """Exact V2 Minimal except vacancy fills require current H5/H10 coherence.

    A challenger must first satisfy the original V2 qualification: current
    consensus Top10 and previous consensus rank <=20. For a real vacancy only,
    that challenger may fill cash when its current H5 and H10 head ranks are both
    <=20. This threshold reuses V2's frozen acceptable/retention-zone boundary.

    Qualified challengers blocked from vacancy fill remain available to the
    original V2 soft-replacement stage. Exit confirmation, incumbent patience,
    gap-5 soft replacement, bootstrap behavior, and temporary underfill are
    otherwise unchanged.
    """

    profile.validate()
    if profile.retention_zone_max_rank != HEAD_ACCEPTABLE_MAX_RANK:
        raise DecisionV2Error("DECISION_V2_2_HEAD_BOUNDARY_MUST_MATCH_RETENTION_ZONE")

    current = _validate_rank_session(current_session, profile)
    _validate_head_ranks(current.ranks, current_head_ranks)
    current_positions = _validate_shadow_state(shadow_state, profile)

    is_bootstrap = shadow_state.as_of_session_date is None
    if is_bootstrap:
        if previous_session is not None:
            raise DecisionV2Error("DECISION_V2_2_BOOTSTRAP_PREROLL_FORBIDDEN")
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
        unfilled_slots = profile.target_count_max - len(selected)
        return DecisionV2Plan(
            decision_session_date=current.session_date,
            current_shadow_positions=(),
            target_positions=selected,
            buy_intents=buys,
            sell_intents=(),
            hold_tickers=(),
            incumbent_observations=(),
            challenger_observations=(),
            unfilled_slots=unfilled_slots,
            capacity_state="FULL" if unfilled_slots == 0 else "UNFILLED_NO_QUALIFIED_CHALLENGER",
            rule_id=profile.rule_id,
            bootstrap=True,
        )

    if previous_session is None:
        raise DecisionV2Error("DECISION_V2_2_PREVIOUS_SESSION_REQUIRED")
    previous = _validate_rank_session(previous_session, profile)
    if shadow_state.as_of_session_date != previous.session_date:
        raise DecisionV2Error("DECISION_V2_2_STATE_PREVIOUS_SESSION_MISMATCH")
    if _parse_date(previous.session_date, "DECISION_V2_2_PREVIOUS_DATE_INVALID") >= _parse_date(
        current.session_date, "DECISION_V2_2_CURRENT_DATE_INVALID"
    ):
        raise DecisionV2Error("DECISION_V2_2_SESSION_ORDER_INVALID")

    held_at_start = set(current_positions)
    missing_from_previous = sorted(held_at_start - set(previous.ranks))
    if missing_from_previous:
        raise DecisionV2Error(
            "DECISION_V2_2_STATE_POSITION_MISSING_FROM_PREVIOUS_SESSION:"
            + ",".join(missing_from_previous)
        )

    incumbent_observations: list[IncumbentObservation] = []
    sell_intents: list[DecisionV2Intent] = []
    retained: set[str] = set()
    acceptable_for_soft_replace: set[str] = set()

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

    # Only this stage differs from exact V2. Search the remaining qualified pool
    # for the best consensus-ranked challenger that is acceptable on BOTH alpha
    # heads. Noncoherent qualified candidates are deliberately left in the pool
    # for the unchanged soft-replacement stage below.
    while len(retained) < profile.target_count_max:
        coherent_index = next(
            (
                index
                for index, obs in enumerate(available_qualified)
                if _coherent_for_vacancy(obs.ticker, current_head_ranks)
                and obs.ticker not in retained
            ),
            None,
        )
        if coherent_index is None:
            break
        challenger = available_qualified.pop(coherent_index)
        retained.add(challenger.ticker)
        buy_intents.append(
            DecisionV2Intent(
                side="BUY_INTENT",
                ticker=challenger.ticker,
                rank_consensus=challenger.current_rank,
                reason="QUALIFIED_COHERENT_VACANCY_FILL",
            )
        )

    # Exact V2 soft replacement, over every still-unused qualified challenger,
    # including candidates that were not coherent enough to fill cash.
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
        raise DecisionV2Error("DECISION_V2_2_TARGET_OVER_CAPACITY")
    if not profile.allow_temporary_underfill and len(retained) < profile.target_count_max:
        raise DecisionV2Error("DECISION_V2_2_UNDERFILL_FORBIDDEN")

    qualified_by_ticker = {
        obs.ticker: obs for obs in challenger_observations if obs.qualified
    }
    for buy in buy_intents:
        if buy.ticker not in qualified_by_ticker:
            raise DecisionV2Error("DECISION_V2_2_UNQUALIFIED_NONBOOTSTRAP_BUY")
        if buy.reason == "QUALIFIED_COHERENT_VACANCY_FILL" and not _coherent_for_vacancy(
            buy.ticker, current_head_ranks
        ):
            raise DecisionV2Error("DECISION_V2_2_NONCOHERENT_VACANCY_BUY")

    sell_names = {intent.ticker for intent in sell_intents}
    buy_names = {intent.ticker for intent in buy_intents}
    if sell_names & buy_names:
        raise DecisionV2Error("DECISION_V2_2_BUY_SELL_COLLISION")

    observation_by_ticker = {obs.ticker: obs for obs in incumbent_observations}
    for ticker in retained:
        obs = observation_by_ticker.get(ticker)
        if obs is None:
            continue
        if obs.state in {"CONFIRMED_EXIT", "UNIVERSE_EXIT"}:
            raise DecisionV2Error("DECISION_V2_2_CONFIRMED_EXIT_RETAINED")
        if obs.current_rank is None:
            raise DecisionV2Error("DECISION_V2_2_ABSENT_TARGET_RETAINED")
        if (
            obs.current_rank > profile.retention_zone_max_rank
            and obs.previous_rank > profile.retention_zone_max_rank
        ):
            raise DecisionV2Error("DECISION_V2_2_TWO_SESSION_OUTSIDE_RETENTION_RETAINED")

    for intent in sell_intents:
        if intent.reason == "CONFIRMED_EXIT_GT20_2":
            obs = observation_by_ticker[intent.ticker]
            if not (
                obs.current_rank is not None
                and obs.current_rank > profile.retention_zone_max_rank
                and obs.previous_rank > profile.retention_zone_max_rank
            ):
                raise DecisionV2Error("DECISION_V2_2_CONFIRMED_EXIT_WITHOUT_TWO_BAD_OBSERVATIONS")
        if intent.reason == "SOFT_RANK_GAP_REPLACEMENT":
            if intent.replacement_peer is None:
                raise DecisionV2Error("DECISION_V2_2_SOFT_REPLACEMENT_PEER_MISSING")
            challenger = qualified_by_ticker[intent.replacement_peer]
            if (intent.rank_consensus or 0) - challenger.current_rank < profile.soft_replacement_min_rank_advantage:
                raise DecisionV2Error("DECISION_V2_2_SOFT_REPLACEMENT_GAP_BROKEN")

    target = _sort_tickers_by_rank(retained, current.ranks)
    hold = tuple(ticker for ticker in target if ticker in held_at_start and ticker not in sell_names)
    incumbent_observations = sorted(incumbent_observations, key=lambda obs: obs.ticker)
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
    buy_intents.sort(key=lambda intent: ((intent.rank_consensus or 10**9), intent.ticker))

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
        challenger_observations=challenger_observations,
        unfilled_slots=unfilled_slots,
        capacity_state=capacity_state,
        rule_id=profile.rule_id,
        bootstrap=False,
    )
