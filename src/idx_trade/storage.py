from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

import pandas as pd


COMPARE_COLUMNS = (
    "raw_open", "raw_high", "raw_low", "raw_close", "raw_volume",
    "vendor_adj_close", "explicit_split_event", "explicit_dividend_event",
)


class DataRevisionConflict(RuntimeError):
    pass


@dataclass(frozen=True)
class RevisionConflict:
    ticker: str
    date: str
    column: str
    existing: object
    incoming: object

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _equal(left: object, right: object) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    return left == right


def revision_conflicts(existing: pd.DataFrame, incoming: pd.DataFrame, ticker: str) -> list[RevisionConflict]:
    if existing.empty or incoming.empty:
        return []
    old = existing.set_index("date")
    new = incoming.set_index("date")
    overlap = old.index.intersection(new.index)
    conflicts: list[RevisionConflict] = []
    for session in overlap:
        for column in COMPARE_COLUMNS:
            if column not in old.columns or column not in new.columns:
                continue
            left, right = old.at[session, column], new.at[session, column]
            if not _equal(left, right):
                conflicts.append(
                    RevisionConflict(
                        ticker=ticker,
                        date=pd.Timestamp(session).date().isoformat(),
                        column=column,
                        existing=left,
                        incoming=right,
                    )
                )
    return conflicts


def merge_daily_history(
    existing: pd.DataFrame,
    incoming: pd.DataFrame,
    ticker: str,
    *,
    allow_revisions: bool = False,
) -> tuple[pd.DataFrame, list[RevisionConflict]]:
    """Merge new provider rows without silently rewriting mature history."""

    conflicts = revision_conflicts(existing, incoming, ticker)
    if conflicts and not allow_revisions:
        preview = ", ".join(f"{row.date}:{row.column}" for row in conflicts[:5])
        raise DataRevisionConflict(f"Provider revised existing {ticker} history ({preview})")

    merged = pd.concat([existing, incoming], ignore_index=True)
    merged["date"] = pd.to_datetime(merged["date"], errors="coerce").dt.normalize()
    merged = merged.dropna(subset=["date"]).sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    return merged, conflicts


def write_parquet_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)
