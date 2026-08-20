from __future__ import annotations

import math

from .v4_x1_decision_v1_contract import TradeIntent
from .v4_x1_execution_v1_contract import (
    BUY_FEE_BPS,
    LOT_SIZE_SHARES,
    MAX_ENTRY_WEIGHT,
    MAX_ORDER_NOTIONAL_SHARE_REFERENCE_VALUE,
    SLIPPAGE_BPS,
    STAMP_DUTY_IDR,
    STAMP_DUTY_THRESHOLD_IDR,
)


def fee(gross: float, bps: float) -> float:
    return gross * bps / 10_000.0


def sell_effective_price(raw_price: float) -> float:
    return raw_price * (1.0 - SLIPPAGE_BPS / 10_000.0)


def buy_effective_price(raw_price: float) -> float:
    return raw_price * (1.0 + SLIPPAGE_BPS / 10_000.0)


def _stamp_for_turnover(turnover: float) -> float:
    return STAMP_DUTY_IDR if turnover > STAMP_DUTY_THRESHOLD_IDR else 0.0


def joint_open_allocation(*, entries, intents: dict[str, TradeIntent],
                          raw_open_prices: dict[str, float], regular_values: dict[str, float],
                          eod_nav: float, cash: float, sell_gross: float) -> dict[str, int]:
    """Allocate executable BUY lots jointly without independent per-name cash slices.

    V1 uses a fee-aware equal-target water fill. Each name first receives the
    whole-lot floor that fits inside its equal cash quota including buy fee.
    Residual cash is then spent one lot at a time on the most under-target name,
    but only when that additional lot moves the name closer to its equal-notional
    target. Entry-cap, Sizing-V1 upper-bound, reference-day capacity, fees and
    the account-level stamp duty are enforced on every candidate addition.

    Decision rank is never a weight signal; it is used only after equal-target
    distance ties, followed by ticker ASC for deterministic identity.
    """
    if not entries:
        return {}

    entries = tuple(entries)
    n = len(entries)
    desired = min(0.10 * eod_nav, cash / n)
    gross_per_lot: dict[str, float] = {}
    debit_per_lot: dict[str, float] = {}
    upper_lots: dict[str, int] = {}
    ranks: dict[str, int] = {}

    for entry in entries:
        ticker = entry.ticker
        effective = buy_effective_price(float(raw_open_prices[ticker]))
        gross_lot = effective * LOT_SIZE_SHARES
        debit_lot = gross_lot * (1.0 + BUY_FEE_BPS / 10_000.0)
        upper = entry.shares // LOT_SIZE_SHARES
        upper = min(
            upper,
            int(math.floor((MAX_ENTRY_WEIGHT * eod_nav) / gross_lot + 1e-12)),
        )
        capacity_notional = MAX_ORDER_NOTIONAL_SHARE_REFERENCE_VALUE * max(
            0.0, float(regular_values.get(ticker, 0.0))
        )
        upper = min(
            upper,
            int(math.floor(capacity_notional / gross_lot + 1e-12)),
        )
        gross_per_lot[ticker] = gross_lot
        debit_per_lot[ticker] = debit_lot
        upper_lots[ticker] = max(0, upper)
        ranks[ticker] = int(intents[ticker].rank_consensus or 10**9)

    lots = {
        entry.ticker: min(
            upper_lots[entry.ticker],
            int(math.floor(desired / debit_per_lot[entry.ticker] + 1e-12)),
        ) if upper_lots[entry.ticker] > 0 else 0
        for entry in entries
    }

    def gross_total(candidate: dict[str, int]) -> float:
        return sum(candidate[t] * gross_per_lot[t] for t in candidate)

    def debit_total(candidate: dict[str, int]) -> float:
        gross = gross_total(candidate)
        return gross + fee(gross, BUY_FEE_BPS) + _stamp_for_turnover(sell_gross + gross)

    # The account-level stamp can rarely make the fee-aware floors exceed cash.
    # Remove the least damaging lots rather than zeroing the entire buy batch.
    while debit_total(lots) > cash + 1e-6:
        removable = []
        for ticker, count in lots.items():
            if count <= 0:
                continue
            gross_lot = gross_per_lot[ticker]
            current = count * gross_lot
            after = (count - 1) * gross_lot
            penalty = abs(after - desired) - abs(current - desired)
            # If economic penalty ties, remove from the worse rank first.
            removable.append((round(penalty, 15), -ranks[ticker], ticker))
        if not removable:
            return {entry.ticker: 0 for entry in entries}
        _, _, chosen = min(removable)
        lots[chosen] -= 1

    # Joint residual water-fill. This avoids the prior implementation's
    # artificial cash drag while remaining equal-target rather than rank-weighted.
    while True:
        current_gross = gross_total(lots)
        candidates = []
        for entry in entries:
            ticker = entry.ticker
            count = lots[ticker]
            if count >= upper_lots[ticker]:
                continue
            lot_gross = gross_per_lot[ticker]
            current_notional = count * lot_gross
            next_notional = (count + 1) * lot_gross
            current_error = abs(current_notional - desired) / max(desired, 1.0)
            next_error = abs(next_notional - desired) / max(desired, 1.0)
            improvement = current_error - next_error
            if improvement < -1e-15:
                continue
            next_gross = current_gross + lot_gross
            next_debit = (
                next_gross
                + fee(next_gross, BUY_FEE_BPS)
                + _stamp_for_turnover(sell_gross + next_gross)
            )
            if next_debit > cash + 1e-6:
                continue
            candidates.append((-round(improvement, 15), ranks[ticker], ticker))
        if not candidates:
            break
        _, _, chosen = min(candidates)
        lots[chosen] += 1

    return {entry.ticker: int(lots[entry.ticker]) for entry in entries}
