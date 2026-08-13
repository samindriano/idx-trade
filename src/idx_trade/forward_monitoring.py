from __future__ import annotations

import argparse
import json
from math import isfinite
import os
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd

from .price_backfill import _download_in_batches
from .forward_ohlcv import (
    MODEL_INPUT_COLUMNS,
    SESSION_OHLCV_COLUMNS,
    build_session_ohlcv,
    provider_row_evidence_sha256,
    validate_ohlcv_against_model_input,
    write_immutable_ohlcv,
)
from .provenance import sha256_file, write_manifest_atomic
from .providers.idx_index_summary import fetch_index_summary_snapshot
from .providers.idx_stock_summary import fetch_stock_summary_snapshot
from .providers.yahoo import download_daily
from .ranking_v2_forward_runtime import FRESH_FORWARD_CUTOFF
from .security_master import (
    COVERAGE_WINDOW_COLUMNS,
    SECURITY_COLUMNS,
    TRADABILITY_ANCHOR_COLUMNS,
    TRADABILITY_COLUMNS,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
    existence_state,
    normalise_ticker,
    tradability_state,
)
from .session_backfill import run_exchange_session_backfill
from .states import ExistenceState, TradabilityState
from .storage import write_csv_atomic, write_parquet_atomic


JAKARTA = ZoneInfo("Asia/Jakarta")
MONITOR_SCHEMA_VERSION = 1
CAPTURE_STALE_MINUTES = 30
MODEL_RUN_STALE_MINUTES = 30


@dataclass(frozen=True)
class RuntimePaths:
    runtime_root: Path
    monitor_root: Path
    registry_path: Path
    session_root: Path
    calendar_root: Path
    raw_price_root: Path
    listings_root: Path
    tradability_root: Path


def runtime_paths(runtime_root: str | Path) -> RuntimePaths:
    root = Path(runtime_root).expanduser().resolve()
    monitor = root / "forward_monitoring"
    return RuntimePaths(
        runtime_root=root,
        monitor_root=monitor,
        registry_path=monitor / "monitor.sqlite3",
        session_root=monitor / "sessions",
        calendar_root=monitor / "calendar",
        raw_price_root=root / "prices" / "raw",
        listings_root=root / "listings",
        tradability_root=root / "tradability",
    )


def _utcnow() -> str:
    return datetime.now(tz=ZoneInfo("UTC")).isoformat()


def _immutable_bytes(path: Path, payload: bytes) -> bool:
    """Create an artifact once, accepting only an identical existing copy."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable artifact revision conflict: {path}")
        return False

    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_bytes(payload)
    try:
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise RuntimeError(f"immutable artifact revision conflict: {path}")
        except OSError:
            # A same-volume hard link is available on normal local Windows
            # filesystems.  The exclusive create fallback retains the
            # no-overwrite invariant on filesystems where it is not.
            with path.open("xb") as destination:
                destination.write(payload)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def _promote_immutable(source: Path, target: Path) -> bool:
    return _immutable_bytes(target, source.read_bytes())


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed.astimezone(ZoneInfo("UTC"))


def _stale(value: str | None, *, minutes: int) -> bool:
    parsed = _parse_utc(value)
    if parsed is None:
        return True
    return datetime.now(tz=ZoneInfo("UTC")) - parsed > timedelta(minutes=minutes)


def _connect(paths: RuntimePaths) -> sqlite3.Connection:
    paths.monitor_root.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(paths.registry_path, timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS monitor_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS session_snapshots (
            session_date TEXT PRIMARY KEY,
            state TEXT NOT NULL CHECK(state IN ('AVAILABLE','FETCHING','DATA_READY','DATA_FAILED')),
            snapshot_path TEXT,
            snapshot_sha256 TEXT,
            evidence_path TEXT,
            evidence_sha256 TEXT,
            manifest_path TEXT,
            manifest_sha256 TEXT,
            started_at TEXT,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            lease_owner TEXT,
            heartbeat_at TEXT,
            error_code TEXT,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS model_runs (
            session_date TEXT NOT NULL,
            model_id TEXT NOT NULL,
            model_fingerprint TEXT NOT NULL,
            generation TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN (
                'NOT_STARTED','QUEUED','PREPARING','SCORING','WRITING','DONE','FAILED','INTERRUPTED'
            )),
            progress_fraction REAL NOT NULL DEFAULT 0,
            artifact_path TEXT,
            artifact_sha256 TEXT,
            manifest_path TEXT,
            manifest_sha256 TEXT,
            started_at TEXT,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            lease_owner TEXT,
            heartbeat_at TEXT,
            error_code TEXT,
            error_message TEXT,
            PRIMARY KEY(session_date, model_id, model_fingerprint),
            FOREIGN KEY(session_date) REFERENCES session_snapshots(session_date)
        );

        CREATE INDEX IF NOT EXISTS model_runs_state_idx
            ON model_runs(state, session_date);
        """
    )
    connection.execute(
        "INSERT INTO monitor_meta(key, value) VALUES('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(MONITOR_SCHEMA_VERSION),),
    )
    return connection


def _normal_date(value: object) -> pd.Timestamp:
    date = pd.Timestamp(value)
    if date.tzinfo is not None:
        date = date.tz_convert(JAKARTA).tz_localize(None)
    return date.normalize()


def _closed_through_date(now: datetime | None = None) -> pd.Timestamp:
    local = (now or datetime.now(tz=JAKARTA)).astimezone(JAKARTA)
    day = pd.Timestamp(local.date())
    # Do not treat today's official session as EOD input before a conservative
    # 17:00 Jakarta cutoff. The exact exchange-day list is still authoritative.
    if (local.hour, local.minute) < (17, 0):
        day -= pd.Timedelta(days=1)
    return day.normalize()


def _read_sessions(path: Path) -> pd.DatetimeIndex:
    if not path.exists():
        return pd.DatetimeIndex([])
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError(f"official session artifact has no date column: {path}")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.isna().any():
        raise RuntimeError(f"official session artifact contains an invalid date: {path}")
    normalized = pd.DatetimeIndex(dates).tz_localize(None).normalize()
    if normalized.duplicated().any():
        duplicates = normalized[normalized.duplicated(keep=False)]
        sample = sorted({value.date().isoformat() for value in duplicates})[:10]
        raise RuntimeError(f"official session artifact contains duplicate dates: {sample}")
    return normalized.sort_values()


def sync_forward_calendar(paths: RuntimePaths, *, through: pd.Timestamp | None = None) -> pd.DatetimeIndex:
    end = _normal_date(through if through is not None else _closed_through_date())
    start = _normal_date(FRESH_FORWARD_CUTOFF) + pd.Timedelta(days=1)
    if end < start:
        return pd.DatetimeIndex([])
    result = run_exchange_session_backfill(start, end, paths.calendar_root)
    if not bool(result.get("complete")):
        raise RuntimeError(f"official forward calendar sync incomplete: {result}")
    return _read_sessions(paths.calendar_root / "exchange_sessions.csv")


def _load_forward_calendar(paths: RuntimePaths) -> pd.DatetimeIndex:
    return _read_sessions(paths.calendar_root / "exchange_sessions.csv")


def _candidate_tables(root: Path) -> list[Path]:
    if not root.exists():
        return []
    preferred = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".csv", ".parquet", ".pq"}
    ]
    return sorted(preferred, key=lambda path: (len(path.parts), path.name.lower(), str(path).lower()))


def _table_columns(path: Path) -> set[str]:
    try:
        if path.suffix.lower() == ".csv":
            return set(pd.read_csv(path, nrows=0).columns.astype(str))
        return set(pd.read_parquet(path).columns.astype(str))
    except Exception:
        return set()


def _discover_table(root: Path, required: Iterable[str], *, label: str, optional: bool = False) -> pd.DataFrame:
    required_set = set(required)
    matches: list[Path] = []
    for path in _candidate_tables(root):
        if required_set.issubset(_table_columns(path)):
            matches.append(path)
    if not matches:
        if optional:
            return pd.DataFrame(columns=sorted(required_set))
        raise RuntimeError(f"{label} artifact not found below {root}")
    # Prefer canonical-looking names, then shallow paths.
    keywords = {
        "security master": ("security_master", "master"),
        "tradability intervals": ("tradability_intervals", "interval"),
        "tradability coverage": ("coverage_window", "coverage"),
        "tradability anchors": ("tradability_anchor", "anchor"),
    }.get(label, ())
    def ranking(path: Path) -> tuple[int, int, str, str]:
        return (
            0 if any(token in path.name.lower() for token in keywords) else 1,
            len(path.parts),
            path.name.lower(),
            str(path).lower(),
        )

    matches.sort(key=ranking)
    if len(matches) > 1 and ranking(matches[0])[:2] == ranking(matches[1])[:2]:
        raise RuntimeError(
            f"ambiguous {label} artifacts below {root}: "
            f"{matches[0]} and {matches[1]}"
        )
    selected = matches[0]
    return pd.read_csv(selected) if selected.suffix.lower() == ".csv" else pd.read_parquet(selected)


def _load_security_master(paths: RuntimePaths) -> pd.DataFrame:
    frame = _discover_table(paths.listings_root, SECURITY_COLUMNS, label="security master")
    data = frame.copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["listed_from"] = pd.to_datetime(data["listed_from"], errors="coerce").dt.normalize()
    data["listed_to"] = pd.to_datetime(data["listed_to"], errors="coerce").dt.normalize()
    data = data.dropna(subset=["ticker", "listed_from"])
    data = data[data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)]
    return data[list(SECURITY_COLUMNS)].sort_values(["ticker", "listed_from"]).reset_index(drop=True)


def _load_tradability(paths: RuntimePaths) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    intervals = _discover_table(
        paths.tradability_root,
        TRADABILITY_COLUMNS,
        label="tradability intervals",
        optional=True,
    )
    windows = _discover_table(
        paths.tradability_root,
        COVERAGE_WINDOW_COLUMNS,
        label="tradability coverage",
        optional=True,
    )
    anchors = _discover_table(
        paths.tradability_root,
        TRADABILITY_ANCHOR_COLUMNS,
        label="tradability anchors",
        optional=True,
    )
    return (
        canonicalize_tradability_intervals(intervals),
        canonicalize_coverage_windows(windows),
        canonicalize_tradability_anchors(anchors),
    )


def _listed_tickers(master: pd.DataFrame, session: pd.Timestamp) -> list[str]:
    tickers = sorted(master["ticker"].dropna().astype(str).unique().tolist())
    return [ticker for ticker in tickers if existence_state(master, ticker, session) is ExistenceState.LISTED]


def _point_state(row: pd.Series) -> TradabilityState:
    volume = pd.to_numeric(pd.Series([row.get("volume")]), errors="coerce").iloc[0]
    frequency = pd.to_numeric(pd.Series([row.get("frequency")]), errors="coerce").iloc[0]
    if pd.isna(volume) or pd.isna(frequency) or float(volume) < 0 or float(frequency) < 0:
        return TradabilityState.UNKNOWN
    if float(volume) > 0 and float(frequency) > 0:
        return TradabilityState.ACTIVE
    if float(volume) == 0 and float(frequency) == 0:
        return TradabilityState.NO_TRADE
    return TradabilityState.UNKNOWN


def _raw_row(path: Path, session: pd.Timestamp) -> pd.Series | None:
    if not path.exists():
        return None
    try:
        frame = pd.read_parquet(path)
    except Exception:
        return None
    if "date" not in frame.columns:
        return None
    if "ticker" in frame.columns:
        identities = frame["ticker"].map(normalise_ticker)
        nonempty = identities.ne("")
        if nonempty.any() and identities.loc[nonempty].ne(path.stem.upper()).any():
            raise RuntimeError(f"raw provider ticker disagrees with file identity: {path}")
    dates = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    selected = frame.loc[dates.eq(session)]
    if selected.empty:
        return None
    if len(selected) != 1:
        raise RuntimeError(
            f"raw provider has duplicate rows for {path.stem.upper()} on "
            f"{session.date().isoformat()}"
        )
    return selected.iloc[0]


def _downloaded_provider_row(
    frame: pd.DataFrame,
    ticker: str,
    session: pd.Timestamp,
) -> pd.Series | None:
    if frame.empty or "date" not in frame.columns:
        return None
    if "ticker" in frame.columns:
        identities = frame["ticker"].map(normalise_ticker)
        nonempty = identities.ne("")
        if nonempty.any():
            if identities.loc[nonempty].ne(ticker).any():
                raise RuntimeError(f"downloaded provider ticker disagrees with requested identity: {ticker}")
            frame = frame.loc[identities.eq(ticker)].copy()
    dates = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    selected = frame.loc[dates.eq(session)]
    if selected.empty:
        return None
    if len(selected) != 1:
        raise RuntimeError(
            f"downloaded provider has duplicate rows for {ticker} on "
            f"{session.date().isoformat()}"
        )
    return selected.iloc[0]


def _price_payload(
    ticker: str,
    row: pd.Series,
    session: pd.Timestamp,
    regular_value: float,
    *,
    source: str,
    source_ref: str,
    source_sha256: str | None = None,
    observed_retrieved_at_utc: str | None = None,
) -> dict[str, object]:
    required = ("raw_open", "raw_high", "raw_low", "raw_close", "raw_volume")
    missing = [column for column in required if column not in row.index or pd.isna(row[column])]
    if missing:
        raise RuntimeError(f"price row for {ticker} missing canonical columns {missing}")
    prices = {column: float(row[column]) for column in required[:-1]}
    volume = float(row["raw_volume"])
    if not all(pd.notna(value) and isfinite(value) and value > 0 for value in prices.values()):
        raise RuntimeError(f"price row for {ticker} has invalid positive OHLC")
    if not pd.notna(volume) or not isfinite(volume) or volume < 0:
        raise RuntimeError(f"price row for {ticker} has invalid non-negative volume")
    if prices["raw_low"] > min(prices["raw_open"], prices["raw_close"]):
        raise RuntimeError(f"price row for {ticker} low is above open/close")
    if prices["raw_high"] < max(prices["raw_open"], prices["raw_close"]):
        raise RuntimeError(f"price row for {ticker} high is below open/close")
    return {
        "ticker": ticker,
        "date": session,
        "open": prices["raw_open"],
        "high": float(row["raw_high"]),
        "low": float(row["raw_low"]),
        "close": float(row["raw_close"]),
        "volume": volume,
        "regular_market_value": float(regular_value),
        "source": source,
        "source_ref": source_ref,
        "source_sha256": source_sha256 or provider_row_evidence_sha256(ticker, session, row),
        "observed_retrieved_at_utc": observed_retrieved_at_utc,
    }


def _existing_session(paths: RuntimePaths, session: pd.Timestamp) -> sqlite3.Row | None:
    connection = _connect(paths)
    try:
        return connection.execute(
            "SELECT * FROM session_snapshots WHERE session_date = ?",
            (session.date().isoformat(),),
        ).fetchone()
    finally:
        connection.close()


def _verify_ready_artifacts(
    snapshot_path: Path,
    evidence_path: Path,
    manifest_path: Path,
    *,
    expected_session: str | None = None,
    snapshot_sha256: str | None = None,
    evidence_sha256: str | None = None,
    manifest_sha256: str | None = None,
) -> bool:
    checks = (
        (snapshot_path, snapshot_sha256),
        (evidence_path, evidence_sha256),
        (manifest_path, manifest_sha256),
    )
    for path, expected in checks:
        if not path.exists() or (expected and sha256_file(path) != expected):
            return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    if not isinstance(manifest, dict):
        return False
    if manifest.get("status") != "DATA_READY":
        return False
    if manifest.get("outcome_blind") is not True:
        return False
    if manifest.get("forward_outcomes_accessed") is not False:
        return False
    try:
        manifest_session = _normal_date(manifest.get("session_date")).date().isoformat()
    except (TypeError, ValueError):
        return False
    if expected_session is not None and manifest_session != expected_session:
        return False

    core_pairs = (
        ("snapshot_path", "snapshot_sha256", snapshot_path),
        ("evidence_path", "evidence_sha256", evidence_path),
    )
    declared_paths: set[Path] = {manifest_path.resolve()}
    for path_key, hash_key, actual_path in core_pairs:
        declared_path = manifest.get(path_key)
        declared_hash = manifest.get(hash_key)
        if not declared_path or not declared_hash:
            return False
        resolved = Path(str(declared_path)).resolve()
        if resolved != actual_path.resolve() or str(declared_hash) != sha256_file(actual_path):
            return False
        if resolved in declared_paths:
            return False
        declared_paths.add(resolved)

    artifact_pairs = (
        ("stock_summary_raw_path", "stock_summary_raw_sha256"),
        ("stock_summary_path", "stock_summary_sha256"),
        ("index_summary_raw_path", "index_summary_raw_sha256"),
        ("index_summary_path", "index_summary_sha256"),
        ("session_ohlcv_path", "session_ohlcv_sha256"),
        ("calendar_path", "calendar_sha256"),
    )
    for path_key, hash_key in artifact_pairs:
        artifact_path = manifest.get(path_key)
        expected_hash = manifest.get(hash_key)
        if not artifact_path or not expected_hash:
            return False
        path = Path(str(artifact_path))
        resolved = path.resolve()
        if resolved in declared_paths:
            return False
        declared_paths.add(resolved)
        if not path.exists() or sha256_file(path) != str(expected_hash):
            return False
    try:
        for key in ("stock_summary_raw_path", "index_summary_raw_path"):
            raw = json.loads(Path(str(manifest[key])).read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return False
        source_specs = (("stock_summary", "as_of_date", "ticker"), ("index_summary", "session_date", "index_code"))
        for prefix, date_column, identity_column in source_specs:
            frame = pd.read_csv(Path(str(manifest[f"{prefix}_path"])))
            if frame.empty or date_column not in frame.columns or identity_column not in frame.columns:
                return False
            dates = pd.to_datetime(frame[date_column], errors="coerce").dt.normalize()
            if dates.isna().any() or not dates.eq(pd.Timestamp(manifest_session)).all():
                return False
            if frame[identity_column].astype(str).str.strip().eq("").any():
                return False
            if frame.duplicated([identity_column, date_column]).any():
                return False
            source = manifest.get(f"{prefix}_source")
            if not isinstance(source, dict) or source.get("session_date") != manifest_session:
                return False

        snapshot = pd.read_parquet(snapshot_path)
        evidence = pd.read_parquet(evidence_path)
        session_ohlcv = pd.read_parquet(Path(str(manifest["session_ohlcv_path"])))
        if snapshot.empty or evidence.empty:
            return False
        if set(MODEL_INPUT_COLUMNS) - set(snapshot.columns):
            return False
        if set(SESSION_OHLCV_COLUMNS) - set(session_ohlcv.columns):
            return False
        if {"ticker", "session_date"} - set(evidence.columns):
            return False
        snapshot_dates = pd.to_datetime(snapshot["date"], errors="coerce").dt.normalize()
        evidence_dates = pd.to_datetime(evidence["session_date"], errors="coerce").dt.normalize()
        expected = pd.Timestamp(manifest_session)
        if snapshot_dates.isna().any() or not snapshot_dates.eq(expected).all():
            return False
        if evidence_dates.isna().any() or not evidence_dates.eq(expected).all():
            return False
        if snapshot.assign(date=snapshot_dates).duplicated(["ticker", "date"]).any():
            return False
        if evidence.assign(session_date=evidence_dates).duplicated(["ticker", "session_date"]).any():
            return False
        validate_ohlcv_against_model_input(session_ohlcv, snapshot, expected)
        if "model_input_rows" in manifest and int(manifest["model_input_rows"]) != len(snapshot):
            return False
        if "point_evidence_rows" in manifest and int(manifest["point_evidence_rows"]) != len(evidence):
            return False
    except Exception:
        return False
    return True


def _verify_ready_row(row: sqlite3.Row) -> bool:
    paths = tuple(Path(str(row[key])) if row[key] else None for key in (
        "snapshot_path", "evidence_path", "manifest_path"
    ))
    if any(path is None for path in paths):
        return False
    return _verify_ready_artifacts(
        paths[0], paths[1], paths[2],
        expected_session=str(row["session_date"]),
        snapshot_sha256=row["snapshot_sha256"],
        evidence_sha256=row["evidence_sha256"],
        manifest_sha256=row["manifest_sha256"],
    )


def _verify_model_run_artifacts(row: Any) -> bool:
    """Verify a model result semantically before it can be treated as DONE."""

    try:
        artifact = Path(str(row["artifact_path"]))
        manifest_path = Path(str(row["manifest_path"]))
        if not artifact.exists() or not manifest_path.exists():
            return False
        artifact_sha = sha256_file(artifact)
        manifest_sha = sha256_file(manifest_path)
        if row["artifact_sha256"] and artifact_sha != str(row["artifact_sha256"]):
            return False
        if row["manifest_sha256"] and manifest_sha != str(row["manifest_sha256"]):
            return False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("status") != "DONE":
            return False
        session_key = str(row["session_date"])
        model_id = str(row["model_id"])
        fingerprint = str(row["model_fingerprint"])
        if manifest.get("session_date") != session_key:
            return False
        if (
            manifest.get("model_id") != model_id
            or manifest.get("generation") != str(row["generation"])
            or manifest.get("model_sha256") != fingerprint
        ):
            return False
        if manifest.get("outcome_blind") is not True:
            return False
        if manifest.get("fresh_forward_outcomes_accessed") is not False:
            return False
        if manifest.get("forward_outcome_access_marker_written") is not False:
            return False
        if "o2_counter_registered" in manifest and manifest.get("o2_counter_registered") is not True:
            return False
        if Path(str(manifest.get("score_artifact_path", ""))).resolve() != artifact.resolve():
            return False
        if manifest.get("score_artifact_sha256") != artifact_sha:
            return False

        frame = pd.read_parquet(artifact)
        required = {"ticker", "session_date", "score", "model_id", "model_sha256"}
        if frame.empty or required - set(frame.columns):
            return False
        if not frame["session_date"].astype(str).eq(session_key).all():
            return False
        if not frame["model_id"].astype(str).eq(model_id).all():
            return False
        if not frame["model_sha256"].astype(str).eq(fingerprint).all():
            return False
        if frame.duplicated(["ticker", "session_date"]).any():
            return False
        if int(manifest.get("score_rows", -1)) != len(frame):
            return False
        if int(manifest.get("scored_rows", -1)) != int(frame["score"].notna().sum()):
            return False
    except Exception:
        return False
    return True


def _claim_session(paths: RuntimePaths, session: pd.Timestamp) -> tuple[str, str | None]:
    key = session.date().isoformat()
    owner = uuid4().hex
    now = _utcnow()
    connection = _connect(paths)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM session_snapshots WHERE session_date = ?", (key,)
        ).fetchone()
        if row is not None and row["state"] == "DATA_READY":
            if not _verify_ready_row(row):
                connection.rollback()
                raise RuntimeError(f"canonical DATA_READY artifact failed hash verification for {key}")
            connection.commit()
            return "ALREADY_READY", None
        if row is not None and row["state"] == "FETCHING" and not _stale(
            row["heartbeat_at"], minutes=CAPTURE_STALE_MINUTES
        ):
            connection.commit()
            return "ALREADY_FETCHING", None
        connection.execute(
            """
            INSERT INTO session_snapshots(
                session_date, state, started_at, updated_at, lease_owner, heartbeat_at,
                error_code, error_message
            ) VALUES (?, 'FETCHING', ?, ?, ?, ?, NULL, NULL)
            ON CONFLICT(session_date) DO UPDATE SET
                state='FETCHING',
                started_at=excluded.started_at,
                updated_at=excluded.updated_at,
                lease_owner=excluded.lease_owner,
                heartbeat_at=excluded.heartbeat_at,
                error_code=NULL,
                error_message=NULL
            """,
            (key, now, now, owner, now),
        )
        connection.commit()
        return "CLAIMED", owner
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def _heartbeat(paths: RuntimePaths, session: pd.Timestamp, owner: str) -> None:
    now = _utcnow()
    connection = _connect(paths)
    try:
        updated = connection.execute(
            """
            UPDATE session_snapshots SET heartbeat_at=?, updated_at=?
            WHERE session_date=? AND state='FETCHING' AND lease_owner=?
            """,
            (now, now, session.date().isoformat(), owner),
        ).rowcount
        if updated != 1:
            raise RuntimeError("session capture lease was lost")
    finally:
        connection.close()


def _fail_session(paths: RuntimePaths, session: pd.Timestamp, owner: str, error: Exception) -> None:
    now = _utcnow()
    code = type(error).__name__.upper()
    connection = _connect(paths)
    try:
        connection.execute(
            """
            UPDATE session_snapshots SET
                state='DATA_FAILED', updated_at=?, completed_at=?, heartbeat_at=?,
                error_code=?, error_message=?
            WHERE session_date=? AND lease_owner=?
            """,
            (now, now, now, code, str(error)[:4000], session.date().isoformat(), owner),
        )
    finally:
        connection.close()


def _complete_session(
    paths: RuntimePaths,
    session: pd.Timestamp,
    owner: str,
    *,
    snapshot_path: Path,
    evidence_path: Path,
    manifest_path: Path,
) -> None:
    snapshot_sha = sha256_file(snapshot_path)
    evidence_sha = sha256_file(evidence_path)
    manifest_sha = sha256_file(manifest_path)
    if not _verify_ready_artifacts(
        snapshot_path,
        evidence_path,
        manifest_path,
        expected_session=session.date().isoformat(),
        snapshot_sha256=snapshot_sha,
        evidence_sha256=evidence_sha,
        manifest_sha256=manifest_sha,
    ):
        raise RuntimeError("canonical session artifacts failed semantic verification before commit")
    now = _utcnow()
    connection = _connect(paths)
    try:
        connection.execute("BEGIN IMMEDIATE")
        updated = connection.execute(
            """
            UPDATE session_snapshots SET
                state='DATA_READY', snapshot_path=?, snapshot_sha256=?,
                evidence_path=?, evidence_sha256=?, manifest_path=?, manifest_sha256=?,
                updated_at=?, completed_at=?, heartbeat_at=?, error_code=NULL, error_message=NULL
            WHERE session_date=? AND state='FETCHING' AND lease_owner=?
            """,
            (
                str(snapshot_path), snapshot_sha, str(evidence_path), evidence_sha,
                str(manifest_path), manifest_sha, now, now, now,
                session.date().isoformat(), owner,
            ),
        ).rowcount
        if updated != 1:
            connection.rollback()
            raise RuntimeError("session capture lease was lost before canonical commit")
        connection.commit()
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def _session_states(paths: RuntimePaths) -> dict[str, sqlite3.Row]:
    connection = _connect(paths)
    try:
        rows = connection.execute("SELECT * FROM session_snapshots ORDER BY session_date").fetchall()
        return {str(row["session_date"]): row for row in rows}
    finally:
        connection.close()


def _earliest_missing(paths: RuntimePaths, sessions: pd.DatetimeIndex) -> pd.Timestamp | None:
    states = _session_states(paths)
    for date in sessions:
        key = pd.Timestamp(date).date().isoformat()
        row = states.get(key)
        if row is None or row["state"] != "DATA_READY" or not _verify_ready_row(row):
            return pd.Timestamp(date).normalize()
    return None


def capture_session(
    runtime_root: str | Path,
    *,
    target_date: str | pd.Timestamp | None = None,
    batch_size: int = 100,
) -> dict[str, Any]:
    """Fetch and freeze one exact outcome-blind IDX session snapshot.

    The official IDX session calendar and Stock Summary are the point-state / regular-market
    evidence. Yahoo supplies raw OHLCV only for tickers with official ACTIVE regular-market
    evidence. The canonical snapshot contains no future labels or H10 outcomes.
    """

    paths = runtime_paths(runtime_root)
    if not paths.runtime_root.exists():
        raise FileNotFoundError(f"runtime root does not exist: {paths.runtime_root}")
    closed_through = _closed_through_date()
    calendar = sync_forward_calendar(paths, through=closed_through)
    if len(calendar) == 0:
        raise RuntimeError("no closed forward IDX sessions are available yet")

    earliest = _earliest_missing(paths, calendar)
    if target_date is None:
        if earliest is None:
            return {"status": "NO_MISSING_SESSION", "message": "all known closed forward sessions are DATA_READY"}
        session = earliest
    else:
        session = _normal_date(target_date)
        if session not in calendar:
            raise ValueError(f"target is not a closed official IDX session: {session.date().isoformat()}")
        existing = _existing_session(paths, session)
        if existing is None or existing["state"] != "DATA_READY":
            if earliest is not None and session != earliest:
                raise ValueError(
                    "cannot skip an earlier missing session: "
                    f"earliest={earliest.date().isoformat()} requested={session.date().isoformat()}"
                )

    claim, owner = _claim_session(paths, session)
    if claim == "ALREADY_READY":
        return {"status": "DATA_READY", "session_date": session.date().isoformat(), "idempotent": True}
    if claim == "ALREADY_FETCHING":
        return {"status": "FETCHING", "session_date": session.date().isoformat(), "idempotent": True}
    assert owner is not None

    session_key = session.date().isoformat()
    attempt_id = uuid4().hex
    attempt_dir = paths.monitor_root / "attempts" / session_key / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=False)

    try:
        master = _load_security_master(paths)
        intervals, windows, anchors = _load_tradability(paths)
        listed = _listed_tickers(master, session)
        if not listed:
            raise RuntimeError(f"security master has no listed common shares on {session_key}")
        _heartbeat(paths, session, owner)

        stock_result = fetch_stock_summary_snapshot(session, include_capture=True)
        if len(stock_result) != 3:
            raise RuntimeError("official Stock Summary raw capture metadata is missing")
        stock_summary, stock_meta, stock_capture = stock_result
        if stock_summary.empty:
            raise RuntimeError(f"official IDX Stock Summary is empty for {session_key}")
        if stock_meta.requested_date != session_key:
            raise RuntimeError(
                f"official IDX Stock Summary metadata date mismatch: "
                f"requested={session_key} returned={stock_meta.requested_date}"
            )
        stock_dates = pd.to_datetime(stock_summary["as_of_date"], errors="coerce").dt.normalize()
        if stock_dates.isna().any() or not stock_dates.eq(session).all():
            raise RuntimeError(f"official IDX Stock Summary rows are stale or date-mismatched for {session_key}")
        if stock_summary.duplicated(["ticker", "as_of_date"]).any():
            raise RuntimeError(f"official IDX Stock Summary contains duplicate ticker rows for {session_key}")
        write_csv_atomic(stock_summary, attempt_dir / "idx_stock_summary.csv")
        (attempt_dir / "idx_stock_summary.raw.json").write_bytes(stock_capture.raw_bytes)

        index_result = fetch_index_summary_snapshot(session, include_capture=True)
        if len(index_result) != 3:
            raise RuntimeError("official Index Summary raw capture metadata is missing")
        index_summary, index_meta, index_capture = index_result
        if index_summary.empty:
            raise RuntimeError(f"official IDX Index Summary is empty for {session_key}")
        if index_meta.requested_date != session_key:
            raise RuntimeError(
                f"official IDX Index Summary metadata date mismatch: "
                f"requested={session_key} returned={index_meta.requested_date}"
            )
        index_dates = pd.to_datetime(index_summary["session_date"], errors="coerce").dt.normalize()
        if index_dates.isna().any() or not index_dates.eq(session).all():
            raise RuntimeError(f"official IDX Index Summary rows are stale or date-mismatched for {session_key}")
        if index_summary.duplicated(["index_code", "session_date"]).any():
            raise RuntimeError(f"official IDX Index Summary contains duplicate index rows for {session_key}")
        write_csv_atomic(index_summary, attempt_dir / "idx_index_summary.csv")
        (attempt_dir / "idx_index_summary.raw.json").write_bytes(index_capture.raw_bytes)
        summary_by_ticker = {
            str(row.ticker): row
            for row in stock_summary.drop_duplicates("ticker", keep="last").itertuples(index=False)
        }

        evidence_rows: list[dict[str, object]] = []
        active: list[str] = []
        unresolved: list[str] = []
        regular_values: dict[str, float] = {}

        for ticker in listed:
            raw = summary_by_ticker.get(ticker)
            if raw is not None:
                row = pd.Series(raw._asdict())
                point = _point_state(row)
                regular_value = pd.to_numeric(pd.Series([row.get("regular_value")]), errors="coerce").iloc[0]
                if point is TradabilityState.ACTIVE:
                    if pd.isna(regular_value) or float(regular_value) < 0:
                        unresolved.append(ticker)
                        state = TradabilityState.UNKNOWN
                        reason = "REGULAR_MARKET_VALUE_MISSING"
                    else:
                        active.append(ticker)
                        regular_values[ticker] = float(regular_value)
                        state = point
                        reason = "IDX_STOCK_SUMMARY_ACTIVE"
                elif point is TradabilityState.NO_TRADE:
                    state = point
                    reason = "IDX_STOCK_SUMMARY_NO_TRADE"
                else:
                    unresolved.append(ticker)
                    state = TradabilityState.UNKNOWN
                    reason = "IDX_STOCK_SUMMARY_POINT_UNRESOLVED"
            else:
                fallback = tradability_state(
                    intervals,
                    windows,
                    ticker,
                    session,
                    market="REGULAR",
                    anchors=anchors,
                )
                state = fallback
                if fallback in {TradabilityState.ACTIVE, TradabilityState.UNKNOWN}:
                    unresolved.append(ticker)
                    reason = "STOCK_SUMMARY_ROW_ABSENT_UNRESOLVED"
                else:
                    reason = f"EXPLICIT_TRADABILITY_{fallback.value}"

            evidence_rows.append(
                {
                    "ticker": ticker,
                    "session_date": session,
                    "point_state": state.value,
                    "evidence_reason": reason,
                    "stock_summary_row_present": raw is not None,
                    "regular_market_value": regular_values.get(ticker),
                }
            )

        if unresolved:
            raise RuntimeError(
                f"session point evidence unresolved for {len(unresolved)} listed tickers; "
                f"sample={unresolved[:20]}"
            )
        _heartbeat(paths, session, owner)

        price_rows: dict[str, dict[str, object]] = {}
        local_hits = 0
        missing_prices: list[str] = []
        for ticker in active:
            raw_path = paths.raw_price_root / f"{ticker}.parquet"
            row = _raw_row(raw_path, session)
            if row is None:
                missing_prices.append(ticker)
                continue
            price_rows[ticker] = _price_payload(
                ticker,
                row,
                session,
                regular_values[ticker],
                source="YAHOO_YFINANCE_RAW_OHLCV",
                source_ref=f"https://finance.yahoo.com/quote/{ticker}.JK/history",
                source_sha256=sha256_file(raw_path),
            )
            local_hits += 1

        downloaded_hits = 0
        download_errors: dict[str, str] = {}
        download_observed_at = _utcnow()
        if missing_prices:
            payload, download_errors = _download_in_batches(
                missing_prices,
                session.date().isoformat(),
                (session + pd.Timedelta(days=1)).date().isoformat(),
                downloader=download_daily,
                batch_size=batch_size,
            )
            for ticker in missing_prices:
                frame = payload.get(ticker, pd.DataFrame())
                selected = _downloaded_provider_row(frame, ticker, session)
                if selected is None:
                    continue
                price_rows[ticker] = _price_payload(
                    ticker,
                    selected,
                    session,
                    regular_values[ticker],
                    source="YAHOO_YFINANCE_AUTO_ADJUST_FALSE",
                    source_ref=f"https://finance.yahoo.com/quote/{ticker}.JK/history",
                    observed_retrieved_at_utc=download_observed_at,
                )
                downloaded_hits += 1

        missing_active_prices = sorted(set(active) - set(price_rows))
        if missing_active_prices:
            detail = {ticker: download_errors.get(ticker) for ticker in missing_active_prices if ticker in download_errors}
            raise RuntimeError(
                f"official ACTIVE tickers missing raw provider price: {missing_active_prices[:20]}; "
                f"download_errors={detail}"
            )

        evidence = pd.DataFrame(evidence_rows).sort_values("ticker").reset_index(drop=True)
        snapshot = pd.DataFrame(price_rows.values()).loc[:, MODEL_INPUT_COLUMNS]
        snapshot = snapshot.sort_values("ticker").reset_index(drop=True)
        if snapshot.empty:
            raise RuntimeError("session has no model-safe ACTIVE price rows")
        session_ohlcv = build_session_ohlcv(price_rows)
        validate_ohlcv_against_model_input(session_ohlcv, snapshot, session)
        _heartbeat(paths, session, owner)

        final_dir = paths.session_root / session_key
        final_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = final_dir / "model_input.parquet"
        evidence_path = final_dir / "session_evidence.parquet"
        stock_summary_path = final_dir / "idx_stock_summary.csv"
        stock_summary_raw_path = final_dir / "idx_stock_summary.raw.json"
        index_summary_path = final_dir / "idx_index_summary.csv"
        index_summary_raw_path = final_dir / "idx_index_summary.raw.json"
        session_ohlcv_path = final_dir / "session_ohlcv.parquet"
        manifest_path = final_dir / "manifest.json"

        # The destination is deterministic and the registry guarantees that an existing
        # verified DATA_READY session is never overwritten. DATA_FAILED/FETCHING attempts
        # may safely promote a newly complete canonical artifact.
        write_parquet_atomic(snapshot, snapshot_path)
        write_parquet_atomic(evidence, evidence_path)
        _promote_immutable(attempt_dir / "idx_stock_summary.csv", stock_summary_path)
        _promote_immutable(attempt_dir / "idx_stock_summary.raw.json", stock_summary_raw_path)
        _promote_immutable(attempt_dir / "idx_index_summary.csv", index_summary_path)
        _promote_immutable(attempt_dir / "idx_index_summary.raw.json", index_summary_raw_path)
        session_ohlcv_sha256 = write_immutable_ohlcv(session_ohlcv, session_ohlcv_path)

        manifest: dict[str, Any] = {
            "schema_version": MONITOR_SCHEMA_VERSION,
            "status": "DATA_READY",
            "session_date": session_key,
            "fresh_forward_cutoff": str(pd.Timestamp(FRESH_FORWARD_CUTOFF).date()),
            "outcome_blind": True,
            "forward_outcomes_accessed": False,
            "listed_tickers": len(listed),
            "active_regular_market_tickers": len(active),
            "model_input_rows": len(snapshot),
            "point_evidence_rows": len(evidence),
            "local_price_hits": local_hits,
            "downloaded_price_hits": downloaded_hits,
            "session_ohlcv_path": str(session_ohlcv_path),
            "session_ohlcv_sha256": session_ohlcv_sha256,
            "open_coverage_status": "COMPLETE_ACTIVE_MODEL_ROWS",
            "open_source_counts": session_ohlcv["source"].value_counts().to_dict(),
            "snapshot_path": str(snapshot_path),
            "snapshot_sha256": sha256_file(snapshot_path),
            "evidence_path": str(evidence_path),
            "evidence_sha256": sha256_file(evidence_path),
            "stock_summary_path": str(stock_summary_path),
            "stock_summary_sha256": sha256_file(stock_summary_path),
            "stock_summary_meta": stock_meta.to_dict(),
            "stock_summary_raw_path": str(stock_summary_raw_path),
            "stock_summary_raw_sha256": sha256_file(stock_summary_raw_path),
            "stock_summary_source": {
                "source": "IDX_OFFICIAL",
                "endpoint": stock_capture.endpoint,
                "params": stock_capture.params,
                "source_ref": stock_capture.source_ref,
                "session_date": session_key,
                "retrieval_started_at_utc": stock_capture.retrieval_started_at_utc,
                "observed_available_at_utc": stock_capture.observed_available_at_utc,
                "row_count": stock_capture.row_count,
                "records_total": stock_capture.records_total,
                "records_filtered": stock_capture.records_filtered,
                "completeness_status": stock_capture.completeness_status,
            },
            "index_summary_path": str(index_summary_path),
            "index_summary_sha256": sha256_file(index_summary_path),
            "index_summary_meta": index_meta.to_dict(),
            "index_summary_raw_path": str(index_summary_raw_path),
            "index_summary_raw_sha256": sha256_file(index_summary_raw_path),
            "index_summary_source": {
                "source": "IDX_OFFICIAL",
                "endpoint": index_capture.endpoint,
                "params": index_capture.params,
                "source_ref": index_capture.source_ref,
                "session_date": session_key,
                "retrieval_started_at_utc": index_capture.retrieval_started_at_utc,
                "observed_available_at_utc": index_capture.observed_available_at_utc,
                "row_count": index_capture.row_count,
                "records_total": index_capture.records_total,
                "records_filtered": index_capture.records_filtered,
                "completeness_status": index_capture.completeness_status,
            },
            "market_context_status": "INDEX_SUMMARY_OFFICIAL_BREADTH_DERIVED_ONLY",
            "calendar_path": str(paths.calendar_root / "exchange_sessions.csv"),
            "calendar_sha256": sha256_file(paths.calendar_root / "exchange_sessions.csv"),
            "captured_at_utc": _utcnow(),
        }
        write_manifest_atomic(manifest_path, manifest)
        _complete_session(
            paths,
            session,
            owner,
            snapshot_path=snapshot_path,
            evidence_path=evidence_path,
            manifest_path=manifest_path,
        )
        return {
            "status": "DATA_READY",
            "session_date": session_key,
            "model_input_rows": len(snapshot),
            "listed_tickers": len(listed),
            "active_tickers": len(active),
            "local_price_hits": local_hits,
            "downloaded_price_hits": downloaded_hits,
            "snapshot_sha256": sha256_file(snapshot_path),
            "session_ohlcv_path": str(session_ohlcv_path),
            "session_ohlcv_sha256": session_ohlcv_sha256,
        }
    except Exception as error:
        _fail_session(paths, session, owner, error)
        failure = {
            "status": "DATA_FAILED",
            "session_date": session_key,
            "error_code": type(error).__name__.upper(),
            "error_message": str(error),
            "failed_at_utc": _utcnow(),
        }
        write_manifest_atomic(attempt_dir / "failure.json", failure)
        raise


def _reconcile_stale(paths: RuntimePaths) -> None:
    connection = _connect(paths)
    try:
        ready_rows = connection.execute(
            "SELECT * FROM session_snapshots WHERE state='DATA_READY'"
        ).fetchall()
        for row in ready_rows:
            if _verify_ready_row(row):
                continue
            now = _utcnow()
            connection.execute(
                """UPDATE session_snapshots
                   SET state='DATA_FAILED', updated_at=?, completed_at=?,
                       error_code='INCOMPLETE_ARTIFACTS',
                       error_message='DATA_READY session failed semantic artifact verification'
                 WHERE session_date=? AND state='DATA_READY'""",
                (now, now, row["session_date"]),
            )

        rows = connection.execute(
            "SELECT * FROM session_snapshots WHERE state='FETCHING'"
        ).fetchall()
        for row in rows:
            if not _stale(row["heartbeat_at"], minutes=CAPTURE_STALE_MINUTES):
                continue
            key = str(row["session_date"])
            lease_owner = row["lease_owner"]
            heartbeat_at = row["heartbeat_at"]
            final_dir = paths.session_root / key
            snapshot = final_dir / "model_input.parquet"
            evidence = final_dir / "session_evidence.parquet"
            manifest = final_dir / "manifest.json"
            if snapshot.exists() and evidence.exists() and manifest.exists():
                now = _utcnow()
                candidate = connection.execute(
                    """SELECT * FROM session_snapshots
                       WHERE session_date=? AND state='FETCHING'
                         AND lease_owner=? AND heartbeat_at=?""",
                    (key, lease_owner, heartbeat_at),
                ).fetchone()
                if candidate is not None and _verify_ready_artifacts(
                    snapshot, evidence, manifest, expected_session=key
                ):
                    connection.execute(
                        """
                        UPDATE session_snapshots SET
                            state='DATA_READY', snapshot_path=?, snapshot_sha256=?,
                            evidence_path=?, evidence_sha256=?, manifest_path=?, manifest_sha256=?,
                            updated_at=?, completed_at=?, heartbeat_at=?, error_code=NULL, error_message=NULL
                        WHERE session_date=? AND state='FETCHING'
                          AND lease_owner=? AND heartbeat_at=?
                        """,
                        (
                            str(snapshot), sha256_file(snapshot), str(evidence), sha256_file(evidence),
                            str(manifest), sha256_file(manifest), now, now, now,
                            key, lease_owner, heartbeat_at,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE session_snapshots SET state='DATA_FAILED', updated_at=?, completed_at=?,
                            error_code='INCOMPLETE_ARTIFACTS', error_message='stale capture artifacts failed manifest verification'
                        WHERE session_date=? AND state='FETCHING'
                          AND lease_owner=? AND heartbeat_at=?
                        """,
                        (now, now, key, lease_owner, heartbeat_at),
                    )
            else:
                now = _utcnow()
                connection.execute(
                    """
                    UPDATE session_snapshots SET state='DATA_FAILED', updated_at=?, completed_at=?,
                        error_code='INTERRUPTED', error_message='capture process disappeared before canonical completion'
                        WHERE session_date=? AND state='FETCHING'
                          AND lease_owner=? AND heartbeat_at=?
                        """,
                        (now, now, key, lease_owner, heartbeat_at),
                )

        model_rows = connection.execute(
            "SELECT * FROM model_runs WHERE state IN ('PREPARING','SCORING','WRITING')"
        ).fetchall()
        for row in model_rows:
            if not _stale(row["heartbeat_at"], minutes=MODEL_RUN_STALE_MINUTES):
                continue
            artifact = Path(row["artifact_path"]) if row["artifact_path"] else None
            manifest = Path(row["manifest_path"]) if row["manifest_path"] else None
            if artifact and manifest and _verify_model_run_artifacts(row):
                now = _utcnow()
                connection.execute(
                    """
                    UPDATE model_runs SET state='DONE', progress_fraction=1,
                        artifact_sha256=?, manifest_sha256=?, updated_at=?, completed_at=?, heartbeat_at=?
                    WHERE session_date=? AND model_id=? AND model_fingerprint=?
                    """,
                    (
                        sha256_file(artifact), sha256_file(manifest), now, now, now,
                        row["session_date"], row["model_id"], row["model_fingerprint"],
                    ),
                )
            else:
                connection.execute(
                    """
                    UPDATE model_runs SET state='INTERRUPTED', updated_at=?,
                        error_code='INCOMPLETE_ARTIFACTS',
                        error_message='stale model artifacts failed semantic manifest verification'
                    WHERE session_date=? AND model_id=? AND model_fingerprint=?
                    """,
                    (_utcnow(), row["session_date"], row["model_id"], row["model_fingerprint"]),
                )
    finally:
        connection.close()


def monitoring_status(runtime_root: str | Path) -> dict[str, Any]:
    paths = runtime_paths(runtime_root)
    if not paths.runtime_root.exists():
        raise FileNotFoundError(f"runtime root does not exist: {paths.runtime_root}")
    _reconcile_stale(paths)
    calendar = _load_forward_calendar(paths)
    states = _session_states(paths)
    earliest = _earliest_missing(paths, calendar) if len(calendar) else None
    session_rows: list[dict[str, Any]] = []
    for date in calendar:
        key = pd.Timestamp(date).date().isoformat()
        row = states.get(key)
        session_rows.append(
            {
                "session_date": key,
                "state": str(row["state"]) if row is not None else "AVAILABLE",
                "error_code": row["error_code"] if row is not None else None,
                "error_message": row["error_message"] if row is not None else None,
                "completed_at": row["completed_at"] if row is not None else None,
            }
        )

    connection = _connect(paths)
    try:
        models = [dict(row) for row in connection.execute(
            "SELECT * FROM model_runs ORDER BY session_date, generation, model_id"
        ).fetchall()]
        ready_count = int(connection.execute(
            "SELECT COUNT(*) FROM session_snapshots WHERE state='DATA_READY'"
        ).fetchone()[0])
    finally:
        connection.close()

    return {
        "schema_version": MONITOR_SCHEMA_VERSION,
        "runtime_ready": True,
        "runtime_root": str(paths.runtime_root),
        "calendar_ready": bool(len(calendar)),
        "calendar_first_session": calendar.min().date().isoformat() if len(calendar) else None,
        "calendar_last_session": calendar.max().date().isoformat() if len(calendar) else None,
        "next_missing_session": earliest.date().isoformat() if earliest is not None else None,
        "data_ready_sessions": ready_count,
        "sessions": session_rows[-30:],
        "model_runs": models[-200:],
        "outcome_access": "LOCKED",
        "forward_outcomes_accessed": False,
        "generated_at_utc": _utcnow(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IDX Trade outcome-blind forward monitoring runtime")
    parser.add_argument("command", choices=("status", "capture", "sync-calendar"))
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--date", default=None)
    parser.add_argument("--batch-size", type=int, default=100)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "status":
        result = monitoring_status(args.runtime_root)
    elif args.command == "sync-calendar":
        sessions = sync_forward_calendar(runtime_paths(args.runtime_root))
        result = {
            "status": "CALENDAR_READY",
            "sessions": len(sessions),
            "first": sessions.min().date().isoformat() if len(sessions) else None,
            "last": sessions.max().date().isoformat() if len(sessions) else None,
        }
    else:
        result = capture_session(args.runtime_root, target_date=args.date, batch_size=args.batch_size)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "error_code": type(error).__name__.upper(),
                    "error_message": str(error),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise
