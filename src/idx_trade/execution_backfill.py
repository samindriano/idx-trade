from __future__ import annotations

import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pandas as pd

from .execution_evidence import stock_summary_execution_anchors
from .providers.idx_stock_summary import fetch_stock_summary_snapshot
from .security_master import canonicalize_tradability_anchors


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


def backfill_stock_summary_execution_evidence(
    exchange_sessions: pd.DatetimeIndex,
    output_dir: str | Path,
    *,
    fetcher: Callable[[pd.Timestamp], tuple[pd.DataFrame, object]] = (
        fetch_stock_summary_snapshot
    ),
) -> dict[str, object]:
    """Backfill direct official Regular-Market execution evidence by session.

    Every requested exchange session must be fetched successfully for the
    session-source audit to be complete. Per-security gaps remain visible later
    through the normal coverage gate; this runner never fills or guesses them.
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
    anchor_frames: list[pd.DataFrame] = []
    diagnostic_frames: list[pd.DataFrame] = []
    session_rows: list[dict[str, object]] = []

    for session in sessions:
        day = pd.Timestamp(session).normalize()
        try:
            frame, meta = fetcher(day)
            anchors, diagnostics = stock_summary_execution_anchors(frame)
            if not anchors.empty:
                anchor_frames.append(anchors)
            if not diagnostics.empty:
                diag = diagnostics.copy()
                diag["session"] = day
                diagnostic_frames.append(diag)
            meta_dict = meta.to_dict() if hasattr(meta, "to_dict") else dict(meta)
            session_rows.append(
                {
                    "session": day,
                    "status": "OK",
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
