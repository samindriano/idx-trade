from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from .data import canonicalize_ohlcv
from .security_master import normalise_ticker
from .storage import merge_daily_history, write_parquet_atomic


SECONDARY_WITNESS_MARKER = "IDX_STOCK_SUMMARY_WITH_SECONDARY_OPEN_WITNESS"


class SecondaryProviderUnavailable(RuntimeError):
    """A public secondary source could not be accessed normally."""


def _required(frame: pd.DataFrame, columns: Iterable[str], label: str) -> None:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} columns missing: {sorted(missing)}")


def _normalise_evidence(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    data = frame.copy()
    _required(data, ("ticker", "date"), label)
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    return data.dropna(subset=["ticker", "date"])


def parse_public_ohlc_table(
    table: pd.DataFrame,
    *,
    ticker: str,
    source_ref: str,
) -> pd.DataFrame:
    """Parse a public historical OHLC table without assigning exchange semantics."""

    data = table.copy()
    data.columns = [str(column).strip().casefold() for column in data.columns]
    aliases = {
        "date": "date",
        "price": "secondary_close",
        "last": "secondary_close",
        "close": "secondary_close",
        "open": "secondary_open",
        "high": "secondary_high",
        "low": "secondary_low",
    }
    data = data.rename(columns={column: aliases.get(column, column) for column in data.columns})
    _required(
        data,
        ("date", "secondary_open", "secondary_high", "secondary_low", "secondary_close"),
        "Public OHLC table",
    )
    result = data[["date", "secondary_open", "secondary_high", "secondary_low", "secondary_close"]].copy()
    result["ticker"] = normalise_ticker(ticker)
    result["date"] = pd.to_datetime(result["date"], errors="coerce").dt.normalize()
    for column in ("secondary_open", "secondary_high", "secondary_low", "secondary_close"):
        result[column] = (
            result[column]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.replace("K", "", regex=False)
            .str.replace("M", "", regex=False)
        )
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["secondary_source_ref"] = source_ref
    return result.dropna(subset=["date"]).drop_duplicates(["ticker", "date"], keep="last")


def fetch_public_ohlc_table(
    url: str,
    *,
    ticker: str,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> pd.DataFrame:
    """Fetch a normal public HTML OHLC page; never bypass anti-bot controls."""

    client = session or requests.Session()
    response = client.get(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 idx-trade-research/2.0",
        },
        timeout=timeout,
    )
    if response.status_code in {401, 403, 429}:
        raise SecondaryProviderUnavailable(
            f"Secondary public OHLC source unavailable without bypass: HTTP {response.status_code}"
        )
    response.raise_for_status()
    try:
        tables = pd.read_html(StringIO(response.text))
    except (ValueError, ImportError) as error:
        raise SecondaryProviderUnavailable(
            f"Secondary public OHLC source returned no readable table: {error}"
        ) from error
    for table in tables:
        columns = {str(column).strip().casefold() for column in table.columns}
        if {"date", "open", "high", "low"}.issubset(columns) and (
            "price" in columns or "close" in columns or "last" in columns
        ):
            return parse_public_ohlc_table(table, ticker=ticker, source_ref=url)
    raise SecondaryProviderUnavailable("Secondary public OHLC source has no compatible OHLC table")


def cross_validate_secondary_open_witness(
    official_rows: pd.DataFrame,
    secondary_rows: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Accept only a secondary Open that exactly agrees with official IDX H/L/C."""

    official = _normalise_evidence(official_rows, "Official IDX evidence")
    secondary = _normalise_evidence(secondary_rows, "Secondary evidence")
    _required(
        official,
        ("official_high", "official_low", "official_close", "official_volume", "official_source_ref"),
        "Official IDX evidence",
    )
    _required(
        secondary,
        ("secondary_open", "secondary_high", "secondary_low", "secondary_close", "secondary_source_ref"),
        "Secondary evidence",
    )
    merged = official.merge(secondary, on=["ticker", "date"], how="left", suffixes=("", "_secondary"))
    accepted: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    for row in merged.itertuples(index=False):
        base = {"ticker": row.ticker, "date": row.date, "official_source_ref": row.official_source_ref}
        if pd.isna(row.secondary_source_ref):
            diagnostics.append({**base, "status": "UNRESOLVED", "diagnostic": "SECONDARY_ROW_UNAVAILABLE"})
            continue
        official_values = (row.official_high, row.official_low, row.official_close, row.official_volume)
        secondary_values = (
            row.secondary_open,
            row.secondary_high,
            row.secondary_low,
            row.secondary_close,
        )
        if any(pd.isna(value) or float(value) <= 0 for value in official_values):
            diagnostics.append({**base, "status": "UNRESOLVED", "diagnostic": "OFFICIAL_ROW_INVALID"})
            continue
        if any(pd.isna(value) or float(value) <= 0 for value in secondary_values):
            diagnostics.append({**base, "status": "UNRESOLVED", "diagnostic": "SECONDARY_OHLC_INVALID"})
            continue
        mismatch = next(
            (
                name
                for name, official_value, secondary_value in (
                    ("HIGH", row.official_high, row.secondary_high),
                    ("LOW", row.official_low, row.secondary_low),
                    ("CLOSE", row.official_close, row.secondary_close),
                )
                if float(official_value) != float(secondary_value)
            ),
            None,
        )
        if mismatch is not None:
            diagnostics.append(
                {**base, "status": "UNRESOLVED", "diagnostic": f"CROSS_SOURCE_PRICE_MISMATCH_{mismatch}"}
            )
            continue
        if not float(row.official_low) <= float(row.secondary_open) <= float(row.official_high):
            diagnostics.append(
                {**base, "status": "UNRESOLVED", "diagnostic": "SECONDARY_OPEN_OUTSIDE_OFFICIAL_RANGE"}
            )
            continue
        accepted.append(
            {
                "ticker": row.ticker,
                "date": row.date,
                "open": float(row.secondary_open),
                "high": float(row.official_high),
                "low": float(row.official_low),
                "close": float(row.official_close),
                "volume": float(row.official_volume),
                "price_source": SECONDARY_WITNESS_MARKER,
                "price_source_ref": row.official_source_ref,
                "secondary_open_source_ref": row.secondary_source_ref,
            }
        )
        diagnostics.append({**base, "status": "ACCEPTED", "diagnostic": "SECONDARY_OPEN_CROSS_VALIDATED"})

    canonical = canonicalize_ohlcv(pd.DataFrame(accepted)) if accepted else pd.DataFrame()
    if not canonical.empty:
        provenance = pd.DataFrame(accepted)[
            ["ticker", "date", "price_source", "price_source_ref", "secondary_open_source_ref"]
        ]
        canonical = canonical.merge(provenance, on=["ticker", "date"], how="left")
    return canonical, pd.DataFrame(diagnostics)


def merge_secondary_open_witness_history(
    existing: pd.DataFrame,
    candidate: pd.DataFrame,
    ticker: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill absent dates only; existing primary history is preserved unchanged."""

    symbol = normalise_ticker(ticker)
    old = existing.copy()
    incoming = candidate[candidate["ticker"].eq(symbol)].copy() if not candidate.empty else candidate.copy()
    if incoming.empty:
        return old.copy(), pd.DataFrame(
            columns=("ticker", "date", "status", "diagnostic")
        )
    existing_dates = set(pd.to_datetime(old["date"]).dt.normalize()) if not old.empty else set()
    fill = incoming[~pd.to_datetime(incoming["date"]).dt.normalize().isin(existing_dates)].copy()
    preserved = incoming[pd.to_datetime(incoming["date"]).dt.normalize().isin(existing_dates)].copy()
    merged, _ = merge_daily_history(old, fill, symbol, allow_revisions=False)
    diagnostics = pd.DataFrame(
        [
            {
                "ticker": symbol,
                "date": row.date,
                "status": "PRIMARY_PRICE_PRESERVED",
                "diagnostic": "EXISTING_PRIMARY_ROW_NOT_OVERWRITTEN",
            }
            for row in preserved.itertuples(index=False)
        ]
    )
    return merged, diagnostics


def write_secondary_open_witness_history(
    existing: pd.DataFrame,
    candidate: pd.DataFrame,
    ticker: str,
    output_path: str | Path,
) -> dict[str, int | str]:
    merged, diagnostics = merge_secondary_open_witness_history(existing, candidate, ticker)
    write_parquet_atomic(merged, Path(output_path))
    return {
        "ticker": normalise_ticker(ticker),
        "candidate_rows": int(len(candidate[candidate["ticker"].eq(normalise_ticker(ticker))]))
        if not candidate.empty
        else 0,
        "preserved_primary_rows": int(len(diagnostics)),
        "filled_rows": int(len(merged) - len(existing)),
        "stored_rows": int(len(merged)),
        "path": str(output_path),
    }
