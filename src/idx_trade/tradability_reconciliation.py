from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .security_master import normalise_market, normalise_ticker, tradability_state
from .states import TradabilityState


SNAPSHOT_COLUMNS = ("ticker", "market", "state", "as_of_date", "source", "source_ref")


@dataclass(frozen=True)
class SnapshotReconciliation:
    ticker: str
    market: str
    as_of_date: str
    expected_state: str
    reconstructed_state: str
    matched: bool
    source: str
    source_ref: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def canonicalize_tradability_snapshot(frame: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize an official point-in-time trading-status snapshot.

    A snapshot is evidence/checkpoint data, not a substitute for the event log.
    It can expose missing or wrongly compiled suspension/resumption events.
    """

    missing = set(SNAPSHOT_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Tradability snapshot columns missing: {sorted(missing)}")
    data = frame[list(SNAPSHOT_COLUMNS)].copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["market"] = data["market"].map(normalise_market)
    data["state"] = data["state"].map(lambda value: TradabilityState(str(value)).value)
    data["as_of_date"] = pd.to_datetime(data["as_of_date"], errors="coerce").dt.normalize()
    data = data.dropna(subset=["ticker", "market", "state", "as_of_date", "source"])
    duplicate = data.duplicated(["ticker", "market", "as_of_date"], keep=False)
    if duplicate.any():
        groups = data.loc[duplicate].groupby(["ticker", "market", "as_of_date"])["state"].nunique()
        if (groups > 1).any():
            raise ValueError("Official snapshot has conflicting states for the same ticker/market/date")
        data = data.drop_duplicates(["ticker", "market", "as_of_date"], keep="last")
    return data.sort_values(["as_of_date", "ticker", "market"]).reset_index(drop=True)


def reconcile_tradability_snapshot(
    snapshot: pd.DataFrame,
    tradability_intervals: pd.DataFrame,
    tradability_coverage_windows: pd.DataFrame,
) -> dict[str, object]:
    """Compare event-derived state with independent official snapshot evidence."""

    evidence = canonicalize_tradability_snapshot(snapshot)
    rows: list[SnapshotReconciliation] = []
    for row in evidence.itertuples(index=False):
        reconstructed = tradability_state(
            tradability_intervals,
            tradability_coverage_windows,
            row.ticker,
            pd.Timestamp(row.as_of_date),
            market=row.market,
        )
        expected = TradabilityState(str(row.state))
        rows.append(
            SnapshotReconciliation(
                ticker=row.ticker,
                market=row.market,
                as_of_date=pd.Timestamp(row.as_of_date).date().isoformat(),
                expected_state=expected.value,
                reconstructed_state=reconstructed.value,
                matched=reconstructed is expected,
                source=str(row.source),
                source_ref=str(row.source_ref),
            )
        )

    mismatches = [row for row in rows if not row.matched]
    return {
        "passed": bool(rows) and not mismatches,
        "evidence_rows": len(rows),
        "matched_rows": len(rows) - len(mismatches),
        "mismatch_rows": len(mismatches),
        "mismatch_tickers": sorted({row.ticker for row in mismatches}),
        "rows": [row.to_dict() for row in rows],
    }


def assert_snapshot_reconciliation(report: dict[str, object]) -> None:
    if not bool(report.get("passed", False)):
        raise RuntimeError(
            "Tradability snapshot reconciliation failed; do not declare a complete coverage window. "
            f"Mismatch tickers: {report.get('mismatch_tickers', [])}"
        )
