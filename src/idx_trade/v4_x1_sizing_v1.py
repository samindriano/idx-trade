from __future__ import annotations

from dataclasses import dataclass, field
import itertools
import math
from pathlib import Path
from typing import Mapping, Sequence

from .v4_x1_decision_v1_contract import (
    DecisionPlan,
    DecisionV1Error,
    ShadowPortfolioState,
    TradeIntent,
    VerifiedScoreSession,
)

EXPECTED_SIZING_CONFIG_SHA256 = "7bf8e43aba9153b8d01d4ba932970e2aa437f1427a6d6f4f862063ff75a3c704"
SIZING_RULE_ID = "V4_X1_SIZING_V1"
LOT_SIZE_SHARES = 100
TARGET_WEIGHT_PER_NAME = 0.10
MAX_ENTRY_WEIGHT_PER_NAME = 0.15
PRIMARY_PAPER_NAV_IDR = 50_000_000
SENSITIVITY_PAPER_NAV_IDR = (25_000_000, 100_000_000)
FEASIBILITY_ONLY_NAV_IDR = (10_000_000,)
SUPPORTED_DECISION_RULES = (
    "V4_X1_DECISION_V1",
    "V4_X1_DECISION_V2_MINIMAL_V1",
)
_SIZING_PLAN_TOKEN = object()
_VERIFIED_DECISION_PLAN_TOKEN = object()


@dataclass(frozen=True)
class VerifiedDecisionPlan:
    """Legacy Decision V1 provenance wrapper retained for compatibility."""

    plan: DecisionPlan
    score_session_date: str
    score_artifact_sha256: str
    _verification_token: object = field(repr=False, compare=False)


def verify_decision_plan_for_downstream(
    decision_plan: DecisionPlan,
    verified_score: VerifiedScoreSession,
    shadow_state: ShadowPortfolioState,
) -> VerifiedDecisionPlan:
    if not isinstance(decision_plan, DecisionPlan):
        raise DecisionV1Error("SIZING_V1_DECISION_PLAN_REQUIRED")
    from .v4_x1_decision_v1 import plan_decision_v1

    expected = plan_decision_v1(verified_score, shadow_state)
    if decision_plan != expected:
        raise DecisionV1Error("SIZING_V1_DECISION_PLAN_PROVENANCE_MISMATCH")
    return VerifiedDecisionPlan(
        plan=decision_plan,
        score_session_date=verified_score.session_date,
        score_artifact_sha256=verified_score.artifact_sha256,
        _verification_token=_VERIFIED_DECISION_PLAN_TOKEN,
    )


@dataclass(frozen=True)
class EntrySizing:
    ticker: str
    rank_consensus: int
    reference_price: float
    lot_value: float
    desired_notional: float
    lots: int
    shares: int
    sized_notional: float
    sized_weight: float
    status: str


@dataclass(frozen=True)
class SizingPlan:
    decision_session_date: str
    nav_idr: float
    available_cash_idr: float
    target_weight_per_name: float
    max_entry_weight_per_name: float
    entries: tuple[EntrySizing, ...]
    total_sized_notional: float
    residual_cash_after_sizing_reference: float
    rule_id: str = SIZING_RULE_ID
    _verification_token: object | None = field(default=None, repr=False, compare=False)


def _finite_positive(value: object, name: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(f"SIZING_V1_{name}_INVALID") from exc
    if not math.isfinite(x) or x <= 0:
        raise DecisionV1Error(f"SIZING_V1_{name}_INVALID")
    return x


def _finite_nonnegative(value: object, name: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(f"SIZING_V1_{name}_INVALID") from exc
    if not math.isfinite(x) or x < 0:
        raise DecisionV1Error(f"SIZING_V1_{name}_INVALID")
    return x


def verify_sizing_v1_config(config_path: str | Path) -> None:
    import hashlib
    import json

    path = Path(config_path).expanduser().resolve()
    if not path.is_file():
        raise DecisionV1Error(f"SIZING_V1_CONFIG_MISSING:{path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != EXPECTED_SIZING_CONFIG_SHA256:
        raise DecisionV1Error(
            f"SIZING_V1_CONFIG_SHA_MISMATCH:{actual}!={EXPECTED_SIZING_CONFIG_SHA256}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "decision_rules": list(SUPPORTED_DECISION_RULES),
        "decision_adapter_policy": (
            "EXACT_RECOMPUTATION_AND_PROVENANCE_VERIFICATION_NO_RULE_ID_PROJECTION"
        ),
        "lot_size_shares": LOT_SIZE_SHARES,
        "target_weight_per_name": TARGET_WEIGHT_PER_NAME,
        "max_entry_weight_per_name": MAX_ENTRY_WEIGHT_PER_NAME,
        "primary_paper_nav_idr": PRIMARY_PAPER_NAV_IDR,
        "rank_weighting": False,
        "conviction_weighting": False,
        "strategic_cash_overlay": False,
        "historical_pnl_authorized": False,
        "allocation_tie_breaker": (
            "BETTER_DECISION_RANK_THEN_TICKER_ASC_ONLY_ON_EXACT_OBJECTIVE_TIE"
        ),
        "decision_plan_provenance_required": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise DecisionV1Error(f"SIZING_V1_CONFIG_CONTRACT_CHANGED:{key}")


def _require_verified_decision_plan(verified_plan: VerifiedDecisionPlan) -> DecisionPlan:
    if not isinstance(verified_plan, VerifiedDecisionPlan):
        raise DecisionV1Error("SIZING_V1_VERIFIED_DECISION_PLAN_REQUIRED")
    if verified_plan._verification_token is not _VERIFIED_DECISION_PLAN_TOKEN:
        raise DecisionV1Error("SIZING_V1_VERIFIED_DECISION_PLAN_REQUIRED")
    plan = verified_plan.plan
    if not isinstance(plan, DecisionPlan) or plan.rule_id != "V4_X1_DECISION_V1":
        raise DecisionV1Error("SIZING_V1_DECISION_RULE_CHANGED")
    if verified_plan.score_session_date != plan.decision_session_date:
        raise DecisionV1Error("SIZING_V1_DECISION_SCORE_SESSION_MISMATCH")
    return plan


def _candidate_lots(
    *,
    desired_notional: float,
    lot_value: float,
    nav_idr: float,
) -> tuple[int, ...]:
    max_lots = int(
        math.floor((MAX_ENTRY_WEIGHT_PER_NAME * nav_idr) / lot_value + 1e-12)
    )
    if max_lots <= 0:
        return (0,)
    raw = desired_notional / lot_value
    floor_lots = min(int(math.floor(raw + 1e-12)), max_lots)
    ceil_lots = min(int(math.ceil(raw - 1e-12)), max_lots)
    return tuple(sorted({max(0, floor_lots), max(0, ceil_lots)}))


def _objective(
    lots: tuple[int, ...],
    lot_values: tuple[float, ...],
    desired_notional: float,
) -> float:
    return sum(
        ((n * lv - desired_notional) / max(desired_notional, 1.0)) ** 2
        for n, lv in zip(lots, lot_values, strict=True)
    )


def _size_entries_core(
    *,
    decision_session_date: str,
    target_positions: Sequence[str],
    intents: Sequence[TradeIntent],
    nav_idr: float,
    available_cash_idr: float,
    reference_prices: Mapping[str, float],
) -> SizingPlan:
    """Decision-rule-neutral Sizing V1 math.

    The caller must establish decision provenance before entering this function.
    This separation allows the frozen Sizing V1 allocator to consume either the
    legacy Decision V1 plan or the frozen Decision V2 Minimal incumbent without
    projecting one decision rule into the identity of the other.
    """

    nav = _finite_positive(nav_idr, "NAV")
    cash = _finite_nonnegative(available_cash_idr, "AVAILABLE_CASH")
    if cash > nav * (1 + 1e-9):
        raise DecisionV1Error("SIZING_V1_CASH_EXCEEDS_NAV")

    buys = tuple(
        sorted(intents, key=lambda x: (x.ticker, int(x.rank_consensus or 10**9)))
    )
    if not buys:
        return SizingPlan(
            decision_session_date=decision_session_date,
            nav_idr=nav,
            available_cash_idr=cash,
            target_weight_per_name=TARGET_WEIGHT_PER_NAME,
            max_entry_weight_per_name=MAX_ENTRY_WEIGHT_PER_NAME,
            entries=(),
            total_sized_notional=0.0,
            residual_cash_after_sizing_reference=cash,
            _verification_token=_SIZING_PLAN_TOKEN,
        )

    if any(x.side != "BUY_INTENT" for x in buys):
        raise DecisionV1Error("SIZING_V1_NON_BUY_INTENT_IN_BUY_SET")
    if len({x.ticker for x in buys}) != len(buys):
        raise DecisionV1Error("SIZING_V1_DUPLICATE_BUY_INTENT")
    target_set = set(target_positions)
    if any(x.ticker not in target_set for x in buys):
        raise DecisionV1Error("SIZING_V1_BUY_OUTSIDE_DECISION_TARGET")
    if any(x.rank_consensus is None or int(x.rank_consensus) > 10 for x in buys):
        raise DecisionV1Error("SIZING_V1_BUY_OUTSIDE_DECISION_TOP10")

    desired = min(TARGET_WEIGHT_PER_NAME * nav, cash / len(buys))
    tickers = tuple(x.ticker for x in buys)
    prices: list[float] = []
    lot_values: list[float] = []
    candidate_sets: list[tuple[int, ...]] = []
    ranks = {x.ticker: int(x.rank_consensus) for x in buys}

    for ticker in tickers:
        if ticker not in reference_prices:
            raise DecisionV1Error(f"SIZING_V1_REFERENCE_PRICE_MISSING:{ticker}")
        price = _finite_positive(
            reference_prices[ticker], f"REFERENCE_PRICE_{ticker}"
        )
        lot_value = price * LOT_SIZE_SHARES
        prices.append(price)
        lot_values.append(lot_value)
        candidate_sets.append(
            _candidate_lots(
                desired_notional=desired,
                lot_value=lot_value,
                nav_idr=nav,
            )
        )

    lot_values_t = tuple(lot_values)
    rank_order = tuple(
        sorted(range(len(tickers)), key=lambda i: (ranks[tickers[i]], tickers[i]))
    )
    ticker_order = tuple(sorted(range(len(tickers)), key=lambda i: tickers[i]))
    best_key: tuple[object, ...] | None = None
    selected: tuple[int, ...] | None = None

    for lots_raw in itertools.product(*candidate_sets):
        lots = tuple(int(x) for x in lots_raw)
        total = sum(
            n * lv for n, lv in zip(lots, lot_values_t, strict=True)
        )
        if total > cash + 1e-6:
            continue
        objective = _objective(lots, lot_values_t, desired)
        key: tuple[object, ...] = (
            round(objective, 15),
            -round(total, 6),
            tuple(-lots[i] for i in rank_order),
            tuple(-lots[i] for i in ticker_order),
        )
        if best_key is None or key < best_key:
            best_key = key
            selected = lots

    if selected is None:
        raise DecisionV1Error("SIZING_V1_NO_FEASIBLE_ALLOCATION")

    entries: list[EntrySizing] = []
    for intent, price, lot_value, lots in zip(
        buys, prices, lot_values, selected, strict=True
    ):
        notional = lots * lot_value
        max_lots = int(
            math.floor(
                (MAX_ENTRY_WEIGHT_PER_NAME * nav) / lot_value + 1e-12
            )
        )
        if lots > max_lots:
            raise DecisionV1Error("SIZING_V1_ENTRY_CAP_BREACH")
        if lots == 0:
            if max_lots == 0:
                status = "LOT_SIZE_INFEASIBLE_15PCT_CAP"
            elif cash == 0:
                status = "NO_AVAILABLE_CASH"
            else:
                status = "ZERO_LOT_CLOSEST_FEASIBLE_ALLOCATION"
        else:
            status = "SIZED"
        entries.append(
            EntrySizing(
                ticker=intent.ticker,
                rank_consensus=int(intent.rank_consensus),
                reference_price=price,
                lot_value=lot_value,
                desired_notional=desired,
                lots=int(lots),
                shares=int(lots * LOT_SIZE_SHARES),
                sized_notional=float(notional),
                sized_weight=float(notional / nav),
                status=status,
            )
        )

    entries = sorted(entries, key=lambda x: (x.rank_consensus, x.ticker))
    total = sum(x.sized_notional for x in entries)
    if total > cash + 1e-6:
        raise DecisionV1Error("SIZING_V1_CASH_INVARIANT_BROKEN")
    if any(x.shares % LOT_SIZE_SHARES for x in entries):
        raise DecisionV1Error("SIZING_V1_LOT_INVARIANT_BROKEN")
    if any(
        x.sized_weight > MAX_ENTRY_WEIGHT_PER_NAME + 1e-12 for x in entries
    ):
        raise DecisionV1Error("SIZING_V1_CAP_INVARIANT_BROKEN")

    return SizingPlan(
        decision_session_date=decision_session_date,
        nav_idr=nav,
        available_cash_idr=cash,
        target_weight_per_name=TARGET_WEIGHT_PER_NAME,
        max_entry_weight_per_name=MAX_ENTRY_WEIGHT_PER_NAME,
        entries=tuple(entries),
        total_sized_notional=float(total),
        residual_cash_after_sizing_reference=float(cash - total),
        _verification_token=_SIZING_PLAN_TOKEN,
    )


def _size_entries_for_intents(
    verified_plan: VerifiedDecisionPlan,
    intents: Sequence[TradeIntent],
    *,
    nav_idr: float,
    available_cash_idr: float,
    reference_prices: Mapping[str, float],
) -> SizingPlan:
    """Legacy V1 entry point retained because Execution V1 still imports it."""

    decision_plan = _require_verified_decision_plan(verified_plan)
    return _size_entries_core(
        decision_session_date=decision_plan.decision_session_date,
        target_positions=decision_plan.target_positions,
        intents=intents,
        nav_idr=nav_idr,
        available_cash_idr=available_cash_idr,
        reference_prices=reference_prices,
    )


def size_decision_v1_entries(
    verified_plan: VerifiedDecisionPlan,
    *,
    nav_idr: float,
    available_cash_idr: float,
    reference_prices: Mapping[str, float],
) -> SizingPlan:
    decision_plan = _require_verified_decision_plan(verified_plan)
    return _size_entries_for_intents(
        verified_plan,
        decision_plan.buy_intents,
        nav_idr=nav_idr,
        available_cash_idr=available_cash_idr,
        reference_prices=reference_prices,
    )
