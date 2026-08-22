from __future__ import annotations

from idx_trade.decision_v2_1_conservative_severe_replacement import (
    V2_1_PROFILE,
    plan_decision_v2_1_conservative_severe_replacement,
)
from idx_trade.decision_v2_minimal import (
    DecisionV2ShadowState,
    RankObservation,
    RankSession,
    plan_decision_v2_minimal,
)


def _session(day: str, ordered: list[str]) -> RankSession:
    return RankSession(
        session_date=day,
        rows=tuple(
            RankObservation(ticker=ticker, rank=index + 1)
            for index, ticker in enumerate(ordered)
        ),
    )


def _universe_order(overrides: dict[int, str], total: int = 70) -> list[str]:
    names = [f"X{index:03d}" for index in range(1, total + 1)]
    used = set(overrides.values())
    filler = [name for name in names if name not in used]
    result: list[str] = []
    for rank in range(1, total + 1):
        if rank in overrides:
            result.append(overrides[rank])
        else:
            result.append(filler.pop(0))
    return result


def _top10(prefix: str) -> dict[int, str]:
    return {rank: f"{prefix}{rank}" for rank in range(1, 11)}


def test_established_top10_challenger_replaces_severe_pending_before_ordinary_soft_replace() -> None:
    held = tuple(f"H{i}" for i in range(1, 11))
    previous = _session(
        "2026-01-05",
        _universe_order(
            {
                **_top10("P"),
                1: "C",
                11: "H1",
                12: "H2",
                13: "H3",
                14: "H4",
                15: "H5",
                16: "H6",
                17: "H7",
                18: "H8",
                19: "H9",
                20: "H10",
            }
        ),
    )
    current = _session(
        "2026-01-06",
        _universe_order(
            {
                **_top10("Q"),
                1: "C",
                11: "H2",
                12: "H3",
                13: "H4",
                14: "H5",
                15: "H6",
                16: "H7",
                17: "H8",
                18: "H9",
                19: "H10",
                60: "H1",
            }
        ),
    )
    state = DecisionV2ShadowState(
        as_of_session_date="2026-01-05",
        positions=held,
        rule_id=V2_1_PROFILE.rule_id,
    )

    original = plan_decision_v2_minimal(current, previous, state, V2_1_PROFILE)
    candidate = plan_decision_v2_1_conservative_severe_replacement(
        current, previous, state
    )

    # Exact V2 would use C for its ordinary 11..20 soft replacement and still
    # carry the rank-60 first-day pending incumbent.
    assert "H1" in original.target_positions
    assert "H10" not in original.target_positions

    # V2.1 gives the one deliberately established challenger priority against
    # the severe pending incumbent, while keeping the acceptable incumbent.
    assert "H1" not in candidate.target_positions
    assert "H10" in candidate.target_positions
    assert "C" in candidate.target_positions
    severe_sells = [
        item
        for item in candidate.sell_intents
        if item.reason == "ESTABLISHED_SEVERE_PENDING_REPLACEMENT"
    ]
    assert len(severe_sells) == 1
    assert severe_sells[0].ticker == "H1"
    assert severe_sells[0].replacement_peer == "C"


def test_non_established_qualified_challenger_gets_no_new_severe_permission() -> None:
    held = tuple(f"H{i}" for i in range(1, 11))
    previous = _session(
        "2026-01-05",
        _universe_order(
            {
                **_top10("P"),
                11: "H1",
                12: "H2",
                13: "H3",
                14: "H4",
                15: "C",
                16: "H5",
                17: "H6",
                18: "H7",
                19: "H8",
                20: "H9",
                21: "H10",
            }
        ),
    )
    current = _session(
        "2026-01-06",
        _universe_order(
            {
                **_top10("Q"),
                1: "C",
                11: "H2",
                12: "H3",
                13: "H4",
                14: "H5",
                15: "H6",
                16: "H7",
                17: "H8",
                18: "H9",
                19: "H10",
                60: "H1",
            }
        ),
    )
    state = DecisionV2ShadowState(
        as_of_session_date="2026-01-05",
        positions=held,
        rule_id=V2_1_PROFILE.rule_id,
    )

    original = plan_decision_v2_minimal(current, previous, state, V2_1_PROFILE)
    candidate = plan_decision_v2_1_conservative_severe_replacement(
        current, previous, state
    )

    assert candidate.target_positions == original.target_positions
    assert not any(
        item.reason == "ESTABLISHED_SEVERE_PENDING_REPLACEMENT"
        for item in candidate.sell_intents
    )


def test_real_vacancy_consumes_established_challenger_before_optional_severe_replacement() -> None:
    held = tuple(f"H{i}" for i in range(1, 10))
    previous = _session(
        "2026-01-05",
        _universe_order(
            {
                **_top10("P"),
                1: "C",
                11: "H1",
                12: "H2",
                13: "H3",
                14: "H4",
                15: "H5",
                16: "H6",
                17: "H7",
                18: "H8",
                19: "H9",
            }
        ),
    )
    current = _session(
        "2026-01-06",
        _universe_order(
            {
                **_top10("Q"),
                1: "C",
                11: "H2",
                12: "H3",
                13: "H4",
                14: "H5",
                15: "H6",
                16: "H7",
                17: "H8",
                18: "H9",
                60: "H1",
            }
        ),
    )
    state = DecisionV2ShadowState(
        as_of_session_date="2026-01-05",
        positions=held,
        rule_id=V2_1_PROFILE.rule_id,
    )

    candidate = plan_decision_v2_1_conservative_severe_replacement(
        current, previous, state
    )

    assert len(candidate.target_positions) == 10
    assert "C" in candidate.target_positions
    assert "H1" in candidate.target_positions
    assert any(
        item.ticker == "C" and item.reason == "QUALIFIED_VACANCY_FILL"
        for item in candidate.buy_intents
    )
    assert not any(
        item.reason == "ESTABLISHED_SEVERE_PENDING_REPLACEMENT"
        for item in candidate.sell_intents
    )
