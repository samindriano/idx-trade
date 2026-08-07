from __future__ import annotations

from datetime import date

import pandas as pd
import yfinance as yf

from ..data import canonicalize_ohlcv
from ..security_master import normalise_ticker


def _extract_symbol(download: pd.DataFrame, provider_symbol: str) -> pd.DataFrame:
    if not isinstance(download.columns, pd.MultiIndex):
        return download
    for level in range(download.columns.nlevels):
        values = download.columns.get_level_values(level).astype(str)
        if provider_symbol in values:
            return download.xs(provider_symbol, axis=1, level=level, drop_level=True)
    return pd.DataFrame()


def _normalise_yahoo_frame(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    rename = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
        "Dividends": "dividends",
        "Stock Splits": "stock_splits",
    }
    data = data.rename(columns=rename).reset_index().rename(columns={"Date": "date", "Datetime": "date"})
    return data


def download_daily(
    tickers: list[str],
    start: date | str,
    end: date | str | None = None,
    threads: bool = True,
) -> dict[str, pd.DataFrame]:
    """Download daily Yahoo data with raw OHLC preserved.

    `auto_adjust=False` is intentional. Vendor adjusted close is retained only as
    a separate analytical field by `canonicalize_ohlcv`; it never replaces raw
    execution prices.
    """

    clean_tickers = sorted({normalise_ticker(ticker) for ticker in tickers})
    symbols = [f"{ticker}.JK" for ticker in clean_tickers]
    if not symbols:
        return {}

    downloaded = yf.download(
        symbols,
        start=pd.Timestamp(start).date().isoformat(),
        end=pd.Timestamp(end).date().isoformat() if end is not None else None,
        auto_adjust=False,
        actions=True,
        group_by="ticker",
        progress=False,
        threads=threads,
    )

    result: dict[str, pd.DataFrame] = {}
    for ticker, symbol in zip(clean_tickers, symbols):
        raw = _extract_symbol(downloaded, symbol)
        if raw.empty:
            result[ticker] = pd.DataFrame()
            continue
        result[ticker] = canonicalize_ohlcv(_normalise_yahoo_frame(raw), ticker)
    return result
