from __future__ import annotations

from idx_trade.decision_v2_2_coherent_vacancy_admission import (
    V2_2_PROFILE,
    plan_decision_v2_2_coherent_vacancy_admission,
)
from idx_trade.decision_v2_minimal import (
    DecisionV2ShadowState,
    RankObservation,
    RankSession,
    plan_decision_v2_minimal,
)


def _session(day: str, overrides: dict[int, str], total: int = 40) -> RankSession:
    used = set(overrides.values())
    filler = [f"X{i:03d}" for i in range(1, total + 1) if f"X{i:03d}" not in used]
    ordered: list[str] = []
    for rank in range(1, total + 1):
        ordered.append(overrides.get(rank, filler.pop(0)))
    return RankSession(
        session_date=day,
        rows=tuple(
            RankObservation(ticker=ticker, rank=index + 1)
            for index, ticker in enumerate(ordered)
        ),
    )


def _head_map(session: RankSession, *, force_h10: tuple[str, int] | None = None) -> dict[str, tuple[int, int]]:
    by_rank = {row.rank: row.ticker for row in session.rows}
    h5 = {row.ticker: row.rank for row in session.rows}
    h10 = {row.ticker: row.rank for row in session.rows}
    if force_h10 is not None:
        ticker, wanted = force_h10
        original = h10[ticker]
        displaced = by_rank[wanted]
        h10[ticker] = wanted
        h10[displaced] = original
    return {ticker: (h5[ticker], h10[ticker]) for ticker in h5}


def test_noncoherent_qualified_challenger_does_not_fill_real_vacancy() -> None:
    held = tuple(f"H{i}" for i in range(1, 10))
    previous = _session(
        "2026-01-05",
        {
            1: "H1", 2: "H2", 3: "H3", 4: "H4", 5: "H5",
            6: "H6", 7: "H7", 8: "H8", 9: "H9", 15: "C",
        },
    )
    current = _session(
        "2026-01-06",
        {
            1: "C", 2: "H1", 3: "H2", 4: "H3", 5: "H4",
            6: "H5", 7: "H6", 8: "H7", 9: "H8", 10: "H9",
        },
    )
    state = DecisionV2ShadowState(
        as_of_session_date="2026-01-05",
        positions=held,
        rule_id=V2_2_PROFILE.rule_id,
    )

    original = plan_decision_v2_minimal(current, previous, state, V2_2_PROFILE)
    candidate = plan_decision_v2_2_coherent_vacancy_admission(
        current,
        previous,
        state,
        _head_map(current, force_h10=("C", 21)),
    )

    assert len(original.target_positions) == 10
    assert "C" in original.target_positions
    assert len(candidate.target_positions) == 9
    assert "C" not in candidate.target_positions
    assert candidate.unfilled_slots == 1
    assert not any(
        intent.reason == "QUALIFIED_COHERENT_VACANCY_FILL"
        for intent in candidate.buy_intents
    )


def test_coherent_qualified_challenger_fills_vacancy_like_v2() -> None:
    held = tuple(f"H{i}" for i in range(1, 10))
    previous = _session(
        "2026-01-05",
        {
            1: "H1", 2: "H2", 3: "H3", 4: "H4", 5: "H5",
            6: "H6", 7: "H7", 8: "H8", 9: "H9", 15: "C",
        },
    )
    current = _session(
        "2026-01-06",
        {
            1: "C", 2: "H1", 3: "H2", 4: "H3", 5: "H4",
            6: "H5", 7: "H6", 8: "H7", 9: "H8", 10: "H9",
        },
    )
    state = DecisionV2ShadowState(
        as_of_session_date="2026-01-05",
        positions=held,
        rule_id=V2_2_PROFILE.rule_id,
    )

    candidate = plan_decision_v2_2_coherent_vacancy_admission(
        current,
        previous,
        state,
        _head_map(current),
    )

    assert len(candidate.target_positions) == 10
    assert "C" in candidate.target_positions
    assert any(
        intent.ticker == "C" and intent.reason == "QUALIFIED_COHERENT_VACANCY_FILL"
        for intent in candidate.buy_intents
    )


def test_noncoherent_challenger_remains_eligible_for_original_soft_replacement() -> None:
    held = tuple(f"H{i}" for i in range(1, 11))
    previous = _session(
        "2026-01-05",
        {
            1: "H1", 2: "H2", 3: "H3", 4: "H4", 5: "H5",
            6: "H6", 7: "H7", 8: "H8", 9: "H9", 10: "H10", 15: "C",
        },
    )
    current = _session(
        "2026-01-06",
        {
            1: "C", 2: "H1", 3: "H2", 4: "H3", 5: "H4",
            6: "H5", 7: "H6", 8: "H7", 9: "H8", 10: "H9", 15: "H10",
        },
    )
    state = DecisionV2ShadowState(
        as_of_session_date="2026-01-05",
        positions=held,
        rule_id=V2_2_PROFILE.rule_id,
    )

    candidate = plan_decision_v2_2_coherent_vacancy_admission(
        current,
        previous,
        state,
        _head_map(current, force_h10=("C", 21)),
    )

    assert len(candidate.target_positions) == 10
    assert "C" in candidate.target_positions
    assert "H10" not in candidate.target_positions
    assert any(
        intent.ticker == "C" and intent.reason == "SOFT_RANK_GAP_REPLACEMENT"
        for intent in candidate.buy_intents
    )
