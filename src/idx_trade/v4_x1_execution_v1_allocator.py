from __future__ import annotations

import itertools
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


def buy_candidate_sets(*, entries, raw_open_prices: dict[str, float], regular_values: dict[str, float],
                       eod_nav: float, actual_cash: float):
    tickers = [entry.ticker for entry in entries]
    desired = min(0.10 * eod_nav, actual_cash / len(tickers)) if tickers else 0.0
    effective_prices: dict[str, float] = {}
    sets: list[tuple[int, ...]] = []
    for entry in entries:
        ticker = entry.ticker
        effective = buy_effective_price(raw_open_prices[ticker])
        effective_prices[ticker] = effective
        upper = entry.shares // LOT_SIZE_SHARES
        upper = min(
            upper,
            int(math.floor((MAX_ENTRY_WEIGHT * eod_nav) / (effective * LOT_SIZE_SHARES) + 1e-12)),
        )
        capacity_notional = MAX_ORDER_NOTIONAL_SHARE_REFERENCE_VALUE * max(
            0.0, float(regular_values.get(ticker, 0.0))
        )
        upper = min(
            upper,
            int(math.floor(capacity_notional / (effective * LOT_SIZE_SHARES) + 1e-12)),
        )
        if upper <= 0:
            sets.append((0,))
            continue
        raw = desired / (effective * LOT_SIZE_SHARES)
        floor_lots = min(int(math.floor(raw + 1e-12)), upper)
        ceil_lots = min(int(math.ceil(raw - 1e-12)), upper)
        sets.append(tuple(sorted({
            max(0, floor_lots - 1),
            max(0, floor_lots),
            max(0, ceil_lots),
        })))
    return tickers, sets, effective_prices, desired


def joint_open_allocation(*, entries, intents: dict[str, TradeIntent],
                          raw_open_prices: dict[str, float], regular_values: dict[str, float],
                          eod_nav: float, cash: float, sell_gross: float) -> dict[str, int]:
    if not entries:
        return {}
    tickers, candidate_sets, effective_prices, desired = buy_candidate_sets(
        entries=entries,
        raw_open_prices=raw_open_prices,
        regular_values=regular_values,
        eod_nav=eod_nav,
        actual_cash=cash,
    )
    ranks = {t: int(intents[t].rank_consensus or 10**9) for t in tickers}
    rank_order = sorted(range(len(tickers)), key=lambda i: (ranks[tickers[i]], tickers[i]))
    ticker_order = sorted(range(len(tickers)), key=lambda i: tickers[i])
    best_key = None
    best_lots = None
    for lots_raw in itertools.product(*candidate_sets):
        lots = tuple(int(x) for x in lots_raw)
        gross = sum(
            lots[i] * LOT_SIZE_SHARES * effective_prices[tickers[i]]
            for i in range(len(tickers))
        )
        fees = fee(gross, BUY_FEE_BPS)
        turnover = sell_gross + gross
        stamp = STAMP_DUTY_IDR if turnover > STAMP_DUTY_THRESHOLD_IDR else 0.0
        if gross + fees + stamp > cash + 1e-6:
            continue
        objective = sum(
            (
                (lots[i] * LOT_SIZE_SHARES * effective_prices[tickers[i]] - desired)
                / max(desired, 1.0)
            ) ** 2
            for i in range(len(tickers))
        )
        key = (
            round(objective, 15),
            -round(gross, 6),
            tuple(-lots[i] for i in rank_order),
            tuple(-lots[i] for i in ticker_order),
        )
        if best_key is None or key < best_key:
            best_key = key
            best_lots = lots
    if best_lots is None:
        return {ticker: 0 for ticker in tickers}
    return {ticker: best_lots[i] for i, ticker in enumerate(tickers)}
