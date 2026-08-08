from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .storage import write_csv_atomic


def _canonical_sessions(values: pd.DatetimeIndex | list[object] | tuple[object, ...]) -> pd.DatetimeIndex:
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(values))
        .dropna()
        .tz_localize(None)
        .normalize()
        .unique()
        .sort_values()
    )
    if len(sessions) == 0:
        raise ValueError("At least one official exchange session is required")
    return sessions


def trailing_session_window(
    exchange_sessions: pd.DatetimeIndex | list[object] | tuple[object, ...],
    horizon: int,
) -> pd.DatetimeIndex:
    """Return the exact trailing official-session window for a research horizon."""

    sessions = _canonical_sessions(exchange_sessions)
    requested = int(horizon)
    if requested <= 0:
        raise ValueError("horizon must be positive")
    if requested > len(sessions):
        raise ValueError(
            f"Insufficient official calendar history: requested {requested}, "
            f"available {len(sessions)}"
        )
    return sessions[-requested:]


def _require_suffix_baseline(
    target_sessions: pd.DatetimeIndex,
    baseline_sessions: pd.DatetimeIndex,
) -> None:
    if len(baseline_sessions) > len(target_sessions):
        raise ValueError("Certified baseline cannot be longer than target window")
    expected = target_sessions[-len(baseline_sessions) :]
    if not expected.equals(baseline_sessions):
        raise ValueError(
            "Certified baseline must be the exact trailing suffix of the target "
            "official-session window"
        )


def stock_summary_cache_coverage(
    cache_dir: str | Path,
    sessions: pd.DatetimeIndex | list[object] | tuple[object, ...],
) -> dict[str, object]:
    """Audit resumable Stock Summary cache presence without trusting partial entries.

    A cache session counts as reusable only when both the parsed parquet snapshot
    and its metadata JSON exist. A lone file is treated as missing so the normal
    backfill path can refetch and atomically repair it.
    """

    requested = _canonical_sessions(sessions)
    root = Path(cache_dir)
    cached: list[pd.Timestamp] = []
    missing: list[pd.Timestamp] = []
    partial: list[pd.Timestamp] = []

    for session in requested:
        stem = pd.Timestamp(session).strftime("%Y-%m-%d")
        frame_exists = (root / f"{stem}.parquet").is_file()
        meta_exists = (root / f"{stem}.meta.json").is_file()
        if frame_exists and meta_exists:
            cached.append(pd.Timestamp(session))
        elif frame_exists or meta_exists:
            partial.append(pd.Timestamp(session))
            missing.append(pd.Timestamp(session))
        else:
            missing.append(pd.Timestamp(session))

    return {
        "requested_sessions": int(len(requested)),
        "cached_sessions": int(len(cached)),
        "missing_sessions": int(len(missing)),
        "partial_cache_sessions": int(len(partial)),
        "cached_session_dates": [value.date().isoformat() for value in cached],
        "missing_session_dates": [value.date().isoformat() for value in missing],
        "partial_cache_session_dates": [value.date().isoformat() for value in partial],
    }


def plan_history_expansion(
    exchange_sessions: pd.DatetimeIndex | list[object] | tuple[object, ...],
    *,
    target_horizon: int,
    certified_baseline_sessions: pd.DatetimeIndex | list[object] | tuple[object, ...],
    stock_summary_cache_dir: str | Path | None = None,
) -> dict[str, object]:
    """Build a fail-closed, network-minimizing plan for a larger history window.

    The certified baseline is required to be the exact trailing suffix of the
    target official-session window. This prevents a historical expansion from
    accidentally mixing different calendars or end dates and guarantees that
    `additional_sessions` is a pure backward extension of already-certified data.
    """

    all_sessions = _canonical_sessions(exchange_sessions)
    target = trailing_session_window(all_sessions, target_horizon)
    baseline = _canonical_sessions(certified_baseline_sessions)
    _require_suffix_baseline(target, baseline)

    additional = target[: len(target) - len(baseline)]
    cache = (
        stock_summary_cache_coverage(stock_summary_cache_dir, target)
        if stock_summary_cache_dir is not None
        else {
            "requested_sessions": int(len(target)),
            "cached_sessions": 0,
            "missing_sessions": int(len(target)),
            "partial_cache_sessions": 0,
            "cached_session_dates": [],
            "missing_session_dates": [value.date().isoformat() for value in target],
            "partial_cache_session_dates": [],
        }
    )

    return {
        "target_horizon": int(target_horizon),
        "target_window_start": target[0].date().isoformat(),
        "target_window_end": target[-1].date().isoformat(),
        "target_sessions": int(len(target)),
        "baseline_sessions": int(len(baseline)),
        "baseline_window_start": baseline[0].date().isoformat(),
        "baseline_window_end": baseline[-1].date().isoformat(),
        "additional_sessions": int(len(additional)),
        "additional_window_start": (
            additional[0].date().isoformat() if len(additional) else None
        ),
        "additional_window_end": (
            additional[-1].date().isoformat() if len(additional) else None
        ),
        "additional_session_dates": [value.date().isoformat() for value in additional],
        "stock_summary_cache": cache,
        "network_fetch_sessions_if_cache_reused": int(cache["missing_sessions"]),
    }


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def write_history_expansion_preflight(
    plan: dict[str, object],
    output_dir: str | Path,
) -> None:
    """Persist the preflight plan and exact additional-session set for handoff/audit."""

    target = Path(output_dir)
    _atomic_json(plan, target / "history_expansion_preflight.json")
    write_csv_atomic(
        pd.DataFrame({"date": plan.get("additional_session_dates", [])}),
        target / "history_expansion_additional_sessions.csv",
    )
