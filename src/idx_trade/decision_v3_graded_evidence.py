from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


class DecisionV3Error(RuntimeError):
    pass


@dataclass(frozen=True)
class DecisionV3Profile:
    rule_id: str
    target_count_max: int
    strong_zone_max_rank: int
    retention_zone_max_rank: int
    mild_deterioration_max_rank: int
    soft_replacement_min_rank_advantage: int
    universe_absence_exit_immediate: bool = True
    allow_temporary_underfill: bool = True
    bootstrap_first_session_exact_top10: bool = True

    def validate(self) -> None:
        if not self.rule_id.strip():
            raise DecisionV3Error("DECISION_V3_PROFILE_RULE_ID_EMPTY")
        if self.target_count_max <= 0:
            raise DecisionV3Error("DECISION_V3_PROFILE_TARGET_COUNT_INVALID")
        if self.strong_zone_max_rank <= 0:
            raise DecisionV3Error("DECISION_V3_PROFILE_STRONG_ZONE_INVALID")
        if self.retention_zone_max_rank <= self.strong_zone_max_rank:
            raise DecisionV3Error("DECISION_V3_PROFILE_RETENTION_NOT_ABOVE_STRONG")
        if self.mild_deterioration_max_rank <= self.retention_zone_max_rank:
            raise DecisionV3Error("DECISION_V3_PROFILE_MILD_NOT_ABOVE_RETENTION")
        if self.soft_replacement_min_rank_advantage <= 0:
            raise DecisionV3Error("DECISION_V3_PROFILE_REPLACEMENT_GAP_INVALID")
        if not self.universe_absence_exit_immediate:
            raise DecisionV3Error("DECISION_V3_UNIVERSE_EXIT_MUST_BE_IMMEDIATE")
        if not self.allow_temporary_underfill:
            raise DecisionV3Error("DECISION_V3_UNDERFILL_MUST_BE_ALLOWED")
        if not self.bootstrap_first_session_exact_top10:
            raise DecisionV3Error("DECISION_V3_BOOTSTRAP_CONTRACT_CHANGED")


@dataclass(frozen=True)
class RankObservation:
    ticker: str
    rank: int


@dataclass(frozen=True)
class RankSession:
    session_date: str
    rows: tuple[RankObservation, ...]


SHADOW_STATE_SOURCE = "DECISION_V3_GRADED_EVIDENCE_SHADOW_ONLY"


@dataclass(frozen=True)
class DecisionV3ShadowState:
    as_of_session_date: str | None
    positions: tuple[str, ...]
    source: str = SHADOW_STATE_SOURCE
    rule_id: str | None = None

    @classmethod
    def empty(cls) -> "DecisionV3ShadowState":
        return cls(as_of_session_date=None, positions=())

    @classmethod
    def from_plan(cls, plan: "DecisionV3Plan") -> "DecisionV3ShadowState":
        if not isinstance(plan, DecisionV3Plan):
            raise DecisionV3Error("DECISION_V3_PLAN_TYPE_REQUIRED_FOR_SHADOW_STATE")
        return cls(
            as_of_session_date=plan.decision_session_date,
            positions=plan.target_positions,
            rule_id=plan.rule_id,
        )


@dataclass(frozen=True)
class DecisionV3Intent:
    side: Literal["BUY_INTENT", "SELL_INTENT"]
    ticker: str
    rank_consensus: int | None
    reason: str
    replacement_peer: str | None = None


IncumbentState = Literal[
    "STRONG_HOLD",
    "ACCEPTABLE_HOLD",
    "MILD_DETERIORATION_PENDING_1",
    "CONFIRMED_MILD_DETERIORATION_EXIT",
    "SEVERE_DETERIORATION_EXIT",
    "UNIVERSE_EXIT",
]


@dataclass(frozen=True)
class IncumbentObservation:
    ticker: str
    current_rank: int | None
    previous_rank: int
    state: IncumbentState


ChallengerState = Literal[
    "A_CORE",
    "B_NEAR",
    "C_DISTANT",
    "D_NO_HISTORY",
]


@dataclass(frozen=True)
class ChallengerObservation:
    ticker: str
    current_rank: int
    previous_rank: int | None
    state: ChallengerState

    @property
    def may_fill_vacancy(self) -> bool:
        return self.state in {"A_CORE", "B_NEAR", "C_DISTANT"}

    @property
    def may_soft_replace(self) -> bool:
        return self.state == "A_CORE"


CapacityState = Literal[
    "FULL",
    "UNFILLED_NO_QUALIFIED_CHALLENGER",
]


@dataclass(frozen=True)
class DecisionV3Plan:
    decision_session_date: str
    current_shadow_positions: tuple[str, ...]
    target_positions: tuple[str, ...]
    buy_intents: tuple[DecisionV3Intent, ...]
    sell_intents: tuple[DecisionV3Intent, ...]
    hold_tickers: tuple[str, ...]
    incumbent_observations: tuple[IncumbentObservation, ...]
    challenger_observations: tuple[ChallengerObservation, ...]
    unfilled_slots: int
    capacity_state: CapacityState
    rule_id: str
    bootstrap: bool = False


@dataclass(frozen=True)
class _ValidatedSession:
    session_date: str
    ranks: dict[str, int]


def _parse_date(value: str, error_code: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise DecisionV3Error(error_code) from exc


def _validate_rank_session(
    session: RankSession,
    profile: DecisionV3Profile,
) -> _ValidatedSession:
    if not isinstance(session, RankSession):
        raise DecisionV3Error("DECISION_V3_RANK_SESSION_TYPE_REQUIRED")
    _parse_date(session.session_date, "DECISION_V3_RANK_SESSION_DATE_INVALID")
    if len(session.rows) < profile.target_count_max:
        raise DecisionV3Error("DECISION_V3_RANK_SESSION_TOO_SMALL")

    ranks: dict[str, int] = {}
    seen_ranks: set[int] = set()
    for row in session.rows:
        if not isinstance(row, RankObservation):
            raise DecisionV3Error("DECISION_V3_RANK_OBSERVATION_TYPE_REQUIRED")
        ticker = str(row.ticker).strip()
        if not ticker:
            raise DecisionV3Error("DECISION_V3_EMPTY_TICKER")
        if ticker != row.ticker:
            raise DecisionV3Error("DECISION_V3_TICKER_NOT_CANONICAL")
        if ticker in ranks:
            raise DecisionV3Error("DECISION_V3_DUPLICATE_TICKER")
        if isinstance(row.rank, bool) or not isinstance(row.rank, int) or row.rank <= 0:
            raise DecisionV3Error("DECISION_V3_RANK_INVALID")
        if row.rank in seen_ranks:
            raise DecisionV3Error("DECISION_V3_DUPLICATE_RANK")
        ranks[ticker] = row.rank
        seen_ranks.add(row.rank)

    expected = set(range(1, len(session.rows) + 1))
    if seen_ranks != expected:
        raise DecisionV3Error("DECISION_V3_RANKS_NOT_CONTIGUOUS")
    return _ValidatedSession(session.session_date, ranks)


def _validate_shadow_state(
    state: DecisionV3ShadowState,
    profile: DecisionV3Profile,
) -> tuple[str, ...]:
    if not isinstance(state, DecisionV3ShadowState):
        raise DecisionV3Error("DECISION_V3_SHADOW_STATE_TYPE_REQUIRED")
    if state.source != SHADOW_STATE_SOURCE:
        raise DecisionV3Error("DECISION_V3_NON_SHADOW_STATE_FORBIDDEN")
    if len(state.positions) > profile.target_count_max:
        raise DecisionV3Error("DECISION_V3_SHADOW_OVER_TARGET")
    if len(set(state.positions)) != len(state.positions):
        raise DecisionV3Error("DECISION_V3_SHADOW_DUPLICATE_POSITION")
    for ticker in state.positions:
        if not ticker or ticker != ticker.strip():
            raise DecisionV3Error("DECISION_V3_SHADOW_TICKER_NOT_CANONICAL")
    if state.as_of_session_date is None:
        if state.positions:
            raise DecisionV3Error("DECISION_V3_INITIAL_STATE_MUST_BE_EMPTY")
        if state.rule_id not in {None, profile.rule_id}:
            raise DecisionV3Error("DECISION_V3_BOOTSTRAP_RULE_ID_MISMATCH")
    else:
        _parse_date(state.as_of_session_date, "DECISION_V3_SHADOW_DATE_INVALID")
        if state.rule_id is not None and state.rule_id != profile.rule_id:
            raise DecisionV3Error("DECISION_V3_SHADOW_RULE_ID_MISMATCH")
    return tuple(sorted(state.positions))


def _sort_tickers_by_rank(
    tickers: set[str] | tuple[str, ...],
    ranks: dict[str, int],
) -> tuple[str, ...]:
    return tuple(sorted(tickers, key=lambda ticker: (ranks[ticker], ticker)))


def _challengers(
    current: _ValidatedSession,
    previous: _ValidatedSession,
    held_at_start: set[str],
    profile: DecisionV3Profile,
) -> tuple[ChallengerObservation, ...]:
    observations: list[ChallengerObservation] = []
    for ticker, current_rank in sorted(
        current.ranks.items(), key=lambda item: (item[1], item[0])
    ):
        if current_rank > profile.strong_zone_max_rank or ticker in held_at_start:
            continue
        previous_rank = previous.ranks.get(ticker)
        if previous_rank is None:
            state: ChallengerState = "D_NO_HISTORY"
        elif previous_rank <= profile.retention_zone_max_rank:
            state = "A_CORE"
        elif previous_rank <= profile.mild_deterioration_max_rank:
            state = "B_NEAR"
        else:
            state = "C_DISTANT"
        observations.append(
            ChallengerObservation(
                ticker=ticker,
                current_rank=current_rank,
                previous_rank=previous_rank,
                state=state,
            )
        )
    return tuple(observations)


def _append_vacancy_fill(
    challenger: ChallengerObservation,
    retained: set[str],
    buy_intents: list[DecisionV3Intent],
) -> None:
    if challenger.state == "A_CORE":
        reason = "TIER_A_VACANCY_FILL"
    elif challenger.state == "B_NEAR":
        reason = "TIER_B_VACANCY_FILL"
    elif challenger.state == "C_DISTANT":
        reason = "TIER_C_RESIDUAL_VACANCY_FILL"
    else:
        raise DecisionV3Error("DECISION_V3_TIER_D_VACANCY_FILL_FORBIDDEN")
    retained.add(challenger.ticker)
    buy_intents.append(
        DecisionV3Intent(
            side="BUY_INTENT",
            ticker=challenger.ticker,
            rank_consensus=challenger.current_rank,
            reason=reason,
        )
    )


def plan_decision_v3_graded_evidence(
    current_session: RankSession,
    previous_session: RankSession | None,
    shadow_state: DecisionV3ShadowState,
    profile: DecisionV3Profile,
) -> DecisionV3Plan:
    profile.validate()
    current = _validate_rank_session(current_session, profile)
    current_positions = _validate_shadow_state(shadow_state, profile)

    is_bootstrap = shadow_state.as_of_session_date is None
    if is_bootstrap:
        if previous_session is not None:
            raise DecisionV3Error("DECISION_V3_BOOTSTRAP_PREROLL_FORBIDDEN")
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
        raise DecisionV3Error("DECISION_V3_PREVIOUS_SESSION_REQUIRED")
    previous = _validate_rank_session(previous_session, profile)
    if shadow_state.as_of_session_date != previous.session_date:
        raise DecisionV3Error("DECISION_V3_STATE_PREVIOUS_SESSION_MISMATCH")
    if _parse_date(previous.session_date, "DECISION_V3_PREVIOUS_DATE_INVALID") >= _parse_date(
        current.session_date, "DECISION_V3_CURRENT_DATE_INVALID"
    ):
        raise DecisionV3Error("DECISION_V3_SESSION_ORDER_INVALID")

    held_at_start = set(current_positions)
    missing_from_previous = sorted(held_at_start - set(previous.ranks))
    if missing_from_previous:
        raise DecisionV3Error(
            "DECISION_V3_STATE_POSITION_MISSING_FROM_PREVIOUS_SESSION:"
            + ",".join(missing_from_previous)
        )

    incumbent_observations: list[IncumbentObservation] = []
    sell_intents: list[DecisionV3Intent] = []
    retained: set[str] = set()
    acceptable_for_soft_replace: set[str] = set()

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
    for tier in ("A_CORE", "B_NEAR", "C_DISTANT"):
        while len(retained) < profile.target_count_max and by_tier[tier]:
            challenger = by_tier[tier].pop(0)
            if challenger.ticker in retained:
                continue
            _append_vacancy_fill(challenger, retained, buy_intents)

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
        raise DecisionV3Error("DECISION_V3_TARGET_OVER_CAPACITY")
    if not profile.allow_temporary_underfill and len(retained) < profile.target_count_max:
        raise DecisionV3Error("DECISION_V3_UNDERFILL_FORBIDDEN")

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
            raise DecisionV3Error("DECISION_V3_NONBOOTSTRAP_BUY_NOT_CHALLENGER")
        expected_tier = expected_buy_tier.get(buy.reason)
        if expected_tier is None or challenger.state != expected_tier:
            raise DecisionV3Error("DECISION_V3_BUY_PERMISSION_TIER_MISMATCH")
        if challenger.state == "D_NO_HISTORY":
            raise DecisionV3Error("DECISION_V3_NO_HISTORY_ENTRY_FORBIDDEN")

    sell_names = {intent.ticker for intent in sell_intents}
    buy_names = {intent.ticker for intent in buy_intents}
    if sell_names & buy_names:
        raise DecisionV3Error("DECISION_V3_BUY_SELL_COLLISION")

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
            raise DecisionV3Error("DECISION_V3_MANDATORY_EXIT_RETAINED")
        if obs.current_rank is None:
            raise DecisionV3Error("DECISION_V3_ABSENT_TARGET_RETAINED")
        if obs.current_rank > profile.mild_deterioration_max_rank:
            raise DecisionV3Error("DECISION_V3_SEVERE_RANK_RETAINED")
        if (
            profile.retention_zone_max_rank < obs.current_rank <= profile.mild_deterioration_max_rank
            and obs.previous_rank > profile.retention_zone_max_rank
        ):
            raise DecisionV3Error("DECISION_V3_SECOND_CONSECUTIVE_MILD_RETAINED")

    for intent in sell_intents:
        if intent.reason == "SEVERE_DETERIORATION_EXIT":
            obs = observation_by_ticker[intent.ticker]
            if not (
                obs.current_rank is not None
                and obs.current_rank > profile.mild_deterioration_max_rank
            ):
                raise DecisionV3Error("DECISION_V3_SEVERE_EXIT_WITHOUT_SEVERE_RANK")
        elif intent.reason == "CONFIRMED_MILD_DETERIORATION_EXIT":
            obs = observation_by_ticker[intent.ticker]
            if not (
                obs.current_rank is not None
                and profile.retention_zone_max_rank
                < obs.current_rank
                <= profile.mild_deterioration_max_rank
                and obs.previous_rank > profile.retention_zone_max_rank
            ):
                raise DecisionV3Error("DECISION_V3_CONFIRMED_MILD_EXIT_INVALID")
        elif intent.reason == "SOFT_RANK_GAP_REPLACEMENT":
            if intent.replacement_peer is None:
                raise DecisionV3Error("DECISION_V3_SOFT_REPLACEMENT_PEER_MISSING")
            challenger = challenger_by_ticker[intent.replacement_peer]
            if challenger.state != "A_CORE":
                raise DecisionV3Error("DECISION_V3_NONCORE_SOFT_REPLACEMENT")
            if (
                (intent.rank_consensus or 0) - challenger.current_rank
                < profile.soft_replacement_min_rank_advantage
            ):
                raise DecisionV3Error("DECISION_V3_SOFT_REPLACEMENT_GAP_BROKEN")

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
