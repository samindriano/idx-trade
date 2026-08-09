from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd

from .providers.idx_sessions import fetch_exchange_sessions_month_with_source
from .storage import write_parquet_atomic


JAKARTA = ZoneInfo("Asia/Jakarta")
STATUS_BLOCKED_SOURCE = "BLOCKED_SOURCE_NOT_FROZEN"
STATUS_ALREADY_ARCHIVED = "ALREADY_ARCHIVED"
STATUS_ARCHIVED = "ARCHIVED"
STATUS_NO_SESSION = "NO_EXPECTED_SESSION"

SnapshotFetcher = Callable[[pd.Timestamp], tuple[pd.DataFrame, dict[str, object]]]


@dataclass(frozen=True)
class ArchiveResult:
    session: str
    status: str
    rows: int = 0
    snapshot_path: str = ""
    manifest_path: str = ""
    snapshot_sha256: str = ""
    provider: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "session": self.session,
            "status": self.status,
            "rows": self.rows,
            "snapshot_path": self.snapshot_path,
            "manifest_path": self.manifest_path,
            "snapshot_sha256": self.snapshot_sha256,
            "provider": self.provider,
            "message": self.message,
        }


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temp.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _session_dir(data_root: str | Path, session: pd.Timestamp) -> Path:
    day = pd.Timestamp(session).tz_localize(None).normalize()
    return Path(data_root) / "forward_open_archive" / "sessions" / day.date().isoformat()


def validate_snapshot(frame: pd.DataFrame, session: pd.Timestamp) -> pd.DataFrame:
    """Validate a complete per-session OHLCV snapshot without fabricating data."""

    required = {"ticker", "date", "open", "high", "low", "close", "volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Forward snapshot columns missing: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Forward snapshot is empty")

    expected = pd.Timestamp(session).tz_localize(None).normalize()
    data = frame.copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if data["date"].isna().any() or not data["date"].eq(expected).all():
        raise ValueError("Forward snapshot contains a date outside the requested session")
    if data["ticker"].eq("").any() or data.duplicated(["ticker", "date"]).any():
        raise ValueError("Forward snapshot has blank/duplicate ticker-date rows")

    numeric = data[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
    if numeric[["open", "high", "low", "close"]].isna().any().any():
        raise ValueError("Forward snapshot has missing OHLC")
    if not (numeric[["open", "high", "low", "close"]] > 0).all().all():
        raise ValueError("Forward snapshot has non-positive OHLC")
    if numeric["volume"].isna().any() or numeric["volume"].lt(0).any():
        raise ValueError("Forward snapshot has invalid volume")
    if not (
        numeric["high"].ge(numeric[["open", "low", "close"]].max(axis=1))
        & numeric["low"].le(numeric[["open", "high", "close"]].min(axis=1))
    ).all():
        raise ValueError("Forward snapshot violates OHLC envelope")

    for column in numeric.columns:
        data[column] = numeric[column]
    return data.sort_values(["ticker", "date"]).reset_index(drop=True)


def load_provider(module_name: str) -> tuple[SnapshotFetcher, str]:
    """Load a separately audited provider adapter.

    The provider module must expose ``fetch_session(session)`` and may expose
    ``SOURCE_ID``. No provider is hardcoded here because the forward acquisition
    source is still a separate audit/gate.
    """

    name = str(module_name).strip()
    if not name:
        raise ValueError("provider module is required")
    module = importlib.import_module(name)
    fetcher = getattr(module, "fetch_session", None)
    if not callable(fetcher):
        raise ValueError(f"Provider module {name!r} has no callable fetch_session")
    source_id = str(getattr(module, "SOURCE_ID", name)).strip() or name
    return fetcher, source_id


def archive_one_session(
    session: pd.Timestamp,
    *,
    data_root: str | Path,
    fetcher: SnapshotFetcher,
    provider_id: str,
) -> ArchiveResult:
    day = pd.Timestamp(session).tz_localize(None).normalize()
    folder = _session_dir(data_root, day)
    snapshot_path = folder / "ohlcv.parquet"
    manifest_path = folder / "manifest.json"

    if snapshot_path.is_file() and manifest_path.is_file():
        return ArchiveResult(
            session=day.date().isoformat(),
            status=STATUS_ALREADY_ARCHIVED,
            rows=int(pd.read_parquet(snapshot_path, columns=["ticker"]).shape[0]),
            snapshot_path=str(snapshot_path),
            manifest_path=str(manifest_path),
            snapshot_sha256=_sha256(snapshot_path),
            provider=provider_id,
        )

    frame, provider_meta = fetcher(day)
    validated = validate_snapshot(frame, day)
    folder.mkdir(parents=True, exist_ok=True)
    write_parquet_atomic(validated, snapshot_path)
    snapshot_sha = _sha256(snapshot_path)
    manifest = {
        "status": STATUS_ARCHIVED,
        "session": day.date().isoformat(),
        "provider": provider_id,
        "provider_metadata": provider_meta,
        "rows": int(len(validated)),
        "tickers": int(validated["ticker"].nunique()),
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": snapshot_sha,
        "archived_at_jakarta": datetime.now(JAKARTA).isoformat(),
        "contract": "RAW_FORWARD_OHLCV_ARCHIVE_V1",
        "execution_grade_promoted": False,
    }
    _atomic_json(manifest, manifest_path)
    return ArchiveResult(
        session=day.date().isoformat(),
        status=STATUS_ARCHIVED,
        rows=int(len(validated)),
        snapshot_path=str(snapshot_path),
        manifest_path=str(manifest_path),
        snapshot_sha256=snapshot_sha,
        provider=provider_id,
    )


def expected_sessions(*, now: datetime, lookback_days: int) -> tuple[pd.DatetimeIndex, dict[str, object]]:
    """Resolve recent expected sessions from the existing official IDX calendar source."""

    end = pd.Timestamp(now.astimezone(JAKARTA).date())
    start = end - pd.Timedelta(days=max(1, int(lookback_days)))
    months = pd.period_range(start=start, end=end, freq="M")
    sessions: set[pd.Timestamp] = set()
    evidence: list[dict[str, object]] = []
    for period in months:
        result = fetch_exchange_sessions_month_with_source(period.year, period.month)
        evidence.append(
            {
                "year": period.year,
                "month": period.month,
                "source_identity": result.source_identity,
                "source_ref": result.source_ref,
                "fallback_reason": result.fallback_reason,
            }
        )
        for session in result.sessions:
            day = pd.Timestamp(session).tz_localize(None).normalize()
            if start <= day <= end:
                sessions.add(day)
    return pd.DatetimeIndex(sorted(sessions)), {"calendar_evidence": evidence}


def run_forward_archive(
    *,
    data_root: str | Path,
    provider_module: str | None,
    lookback_days: int = 45,
    now: datetime | None = None,
) -> dict[str, object]:
    """Archive every recent official session not already stored.

    If no provider has been frozen/configured yet, the command records a durable
    blocked status instead of silently choosing a source. This makes it safe to
    install the scheduler before the provider audit is complete.
    """

    current = now or datetime.now(JAKARTA)
    root = Path(data_root)
    status_path = root / "forward_open_archive" / "latest_run.json"

    if not str(provider_module or "").strip():
        summary = {
            "status": STATUS_BLOCKED_SOURCE,
            "run_at_jakarta": current.astimezone(JAKARTA).isoformat(),
            "provider_module": "",
            "message": "Forward Open acquisition source has not been frozen. No network price source was selected.",
        }
        _atomic_json(summary, status_path)
        return summary

    fetcher, provider_id = load_provider(str(provider_module))
    sessions, calendar_meta = expected_sessions(now=current, lookback_days=lookback_days)
    if len(sessions) == 0:
        summary = {
            "status": STATUS_NO_SESSION,
            "run_at_jakarta": current.astimezone(JAKARTA).isoformat(),
            "provider": provider_id,
            **calendar_meta,
        }
        _atomic_json(summary, status_path)
        return summary

    results = [
        archive_one_session(session, data_root=root, fetcher=fetcher, provider_id=provider_id)
        for session in sessions
    ]
    summary = {
        "status": "FORWARD_ARCHIVE_RUN_COMPLETE",
        "run_at_jakarta": current.astimezone(JAKARTA).isoformat(),
        "provider": provider_id,
        "lookback_days": int(lookback_days),
        "expected_sessions": int(len(sessions)),
        "archived_now": sum(result.status == STATUS_ARCHIVED for result in results),
        "already_archived": sum(result.status == STATUS_ALREADY_ARCHIVED for result in results),
        "results": [result.to_dict() for result in results],
        **calendar_meta,
    }
    _atomic_json(summary, status_path)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive recent IDX OHLCV/Open snapshots fail-closed")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--provider-module", default="")
    parser.add_argument("--lookback-days", type=int, default=45)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = run_forward_archive(
        data_root=args.data_root,
        provider_module=args.provider_module,
        lookback_days=args.lookback_days,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["status"] != STATUS_BLOCKED_SOURCE else 2


if __name__ == "__main__":
    raise SystemExit(main())
