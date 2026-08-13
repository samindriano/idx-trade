from __future__ import annotations

import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pandas as pd

from .execution_evidence import stock_summary_execution_anchors
from .providers.idx_stock_summary import fetch_stock_summary_snapshot
from .security_master import canonicalize_tradability_anchors
from .storage import write_parquet_atomic


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    frame.to_csv(temp, index=False)
    temp.replace(path)


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temp.replace(path)


def _cache_paths(cache_dir: Path, session: pd.Timestamp) -> tuple[Path, Path]:
    stem = pd.Timestamp(session).strftime("%Y-%m-%d")
    return cache_dir / f"{stem}.parquet", cache_dir / f"{stem}.meta.json"


def _load_cached_snapshot(
    cache_dir: Path,
    session: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, object]] | None:
    frame_path, meta_path = _cache_paths(cache_dir, session)
    if not frame_path.is_file() or not meta_path.is_file():
        return None
    frame = pd.read_parquet(frame_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if not isinstance(meta, dict):
        raise ValueError(f"Invalid Stock Summary cache metadata: {meta_path}")
    return frame, meta


def _write_cached_snapshot(
    cache_dir: Path,
    session: pd.Timestamp,
    frame: pd.DataFrame,
    meta: dict[str, object],
) -> None:
    frame_path, meta_path = _cache_paths(cache_dir, session)
    write_parquet_atomic(frame, frame_path)
    _atomic_json(meta, meta_path)


def backfill_stock_summary_execution_evidence(
    exchange_sessions: pd.DatetimeIndex,
    output_dir: str | Path,
    *,
    fetcher: Callable[[pd.Timestamp], tuple[pd.DataFrame, object]] = (
        fetch_stock_summary_snapshot
    ),
    cache_dir: str | Path | None = None,
    reuse_cache: bool = True,
    force_refetch: bool = False,
) -> dict[str, object]:
    """Backfill direct official Regular-Market execution evidence by session.

    Parsed official Stock Summary snapshots are cached per exchange session so
    changes to downstream execution semantics can regenerate anchors without
    repeating network downloads. The cache stores the provider-parsed row set
    before ACTIVE/NO_TRADE classification plus fetch metadata.

    Every requested exchange session must have either a valid cached snapshot or
    a successful live fetch for the session-source audit to be complete. The
    runner never fills or guesses missing sessions or per-security rows.
    """

    sessions = (
        pd.DatetimeIndex(pd.to_datetime(exchange_sessions))
        .tz_localize(None)
        .normalize()
        .unique()
        .sort_values()
    )
    if len(sessions) == 0:
        raise ValueError("At least one official exchange session is required")

    output_dir = Path(output_dir)
    cache_root = Path(cache_dir) if cache_dir is not None else output_dir / "stock_summary_cache"
    anchor_frames: list[pd.DataFrame] = []
    diagnostic_frames: list[pd.DataFrame] = []
    session_rows: list[dict[str, object]] = []
    cached_sessions = 0
    fetched_sessions = 0

    for session in sessions:
        day = pd.Timestamp(session).normalize()
        try:
            cached = None
            if reuse_cache and not force_refetch:
                try:
                    cached = _load_cached_snapshot(cache_root, day)
                except Exception:
                    # A corrupt/incomplete cache entry is never trusted. Fetch a
                    # fresh official snapshot and atomically replace it instead.
                    cached = None

            if cached is not None:
                frame, meta_dict = cached
                cache_status = "CACHE"
                cached_sessions += 1
            else:
                frame, meta = fetcher(day)
                meta_dict = meta.to_dict() if hasattr(meta, "to_dict") else dict(meta)
                _write_cached_snapshot(cache_root, day, frame, meta_dict)
                cache_status = "FETCH"
                fetched_sessions += 1

            anchors, diagnostics = stock_summary_execution_anchors(frame)
            if not anchors.empty:
                anchor_frames.append(anchors)
            if not diagnostics.empty:
                diag = diagnostics.copy()
                diag["session"] = day
                diagnostic_frames.append(diag)
            session_rows.append(
                {
                    "session": day,
                    "status": "OK",
                    "retrieval": cache_status,
                    "parsed_rows": int(len(frame)),
                    "anchor_rows": int(len(anchors)),
                    "active_rows": int(anchors["state"].eq("ACTIVE").sum())
                    if not anchors.empty
                    else 0,
                    "no_trade_rows": int(anchors["state"].eq("NO_TRADE").sum())
                    if not anchors.empty
                    else 0,
                    "unresolved_rows": int(len(diagnostics)),
                    "source_ref": str(meta_dict.get("source_ref", "")),
                    "error": "",
                }
            )
        except Exception as error:
            session_rows.append(
                {
                    "session": day,
                    "status": "ERROR",
                    "retrieval": "ERROR",
                    "parsed_rows": 0,
                    "anchor_rows": 0,
                    "active_rows": 0,
                    "no_trade_rows": 0,
                    "unresolved_rows": 0,
                    "source_ref": "",
                    "error": str(error),
                }
            )

    anchors = (
        canonicalize_tradability_anchors(
            pd.concat(anchor_frames, ignore_index=True)
        )
        if anchor_frames
        else canonicalize_tradability_anchors(pd.DataFrame())
    )
    diagnostics = (
        pd.concat(diagnostic_frames, ignore_index=True)
        if diagnostic_frames
        else pd.DataFrame()
    )
    session_report = pd.DataFrame(session_rows)
    complete_sessions = int(session_report["status"].eq("OK").sum())
    failed_sessions = int(session_report["status"].eq("ERROR").sum())

    summary = {
        "requested_sessions": int(len(sessions)),
        "complete_sessions": complete_sessions,
        "failed_sessions": failed_sessions,
        "session_source_complete": failed_sessions == 0,
        "cached_sessions": cached_sessions,
        "fetched_sessions": fetched_sessions,
        "cache_dir": str(cache_root),
        "anchor_rows": int(len(anchors)),
        "active_anchor_rows": int(anchors["state"].eq("ACTIVE").sum())
        if not anchors.empty
        else 0,
        "no_trade_anchor_rows": int(anchors["state"].eq("NO_TRADE").sum())
        if not anchors.empty
        else 0,
        "unresolved_metric_rows": int(len(diagnostics)),
    }

    _atomic_csv(anchors, output_dir / "idx_execution_anchors.csv")
    _atomic_csv(diagnostics, output_dir / "idx_execution_diagnostics.csv")
    _atomic_csv(session_report, output_dir / "idx_execution_session_report.csv")
    _atomic_json(summary, output_dir / "idx_execution_backfill_summary.json")
    return summary
