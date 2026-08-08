from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .full_universe import run_full_universe_data_gate
from .storage import write_csv_atomic


DEFAULT_SESSION_HORIZONS = (43, 126, 252, 504, 756, 1260)


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def _canonical_sessions(exchange_sessions: pd.DatetimeIndex) -> pd.DatetimeIndex:
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(exchange_sessions))
        .dropna()
        .tz_localize(None)
        .normalize()
        .unique()
        .sort_values()
    )
    if len(sessions) == 0:
        raise ValueError("History ladder requires at least one exchange session")
    return sessions


def run_history_certification_ladder(
    exchange_sessions: pd.DatetimeIndex,
    price_frames: dict[str, pd.DataFrame],
    security_master: pd.DataFrame,
    tradability_intervals: pd.DataFrame,
    tradability_coverage_windows: pd.DataFrame,
    *,
    tradability_anchors: pd.DataFrame | None = None,
    split_history_verified: dict[str, bool],
    dividend_history_verified: dict[str, bool] | None = None,
    price_semantics_verified: dict[str, bool] | None = None,
    session_horizons: tuple[int, ...] | list[int] = DEFAULT_SESSION_HORIZONS,
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    """Find the longest trailing market window that passes the full DATA GATE.

    Horizons are measured in official IDX exchange sessions and all end on the
    latest supplied session. Each horizon reruns the point-in-time full-universe
    certification; no shorter-window pass is extrapolated backward into history.
    """

    sessions = _canonical_sessions(exchange_sessions)
    horizons = sorted({int(value) for value in session_horizons if int(value) > 0})
    if not horizons:
        raise ValueError("At least one positive history horizon is required")

    rows: list[dict[str, object]] = []
    detailed: dict[str, dict[str, object]] = {}
    for requested in horizons:
        if requested > len(sessions):
            rows.append(
                {
                    "requested_sessions": requested,
                    "evaluated_sessions": 0,
                    "window_start": None,
                    "window_end": sessions[-1].date().isoformat(),
                    "status": "INSUFFICIENT_CALENDAR_HISTORY",
                    "passed": False,
                    "required_tickers": 0,
                    "passed_tickers": 0,
                    "failed_tickers": 0,
                    "unknown_sessions": None,
                    "missing_active_prices": None,
                    "quarantined_nonactive_bars": None,
                    "blocker_counts": {},
                }
            )
            continue

        window = sessions[-requested:]
        report = run_full_universe_data_gate(
            window,
            price_frames,
            security_master,
            tradability_intervals,
            tradability_coverage_windows,
            tradability_anchors=tradability_anchors,
            split_history_verified=split_history_verified,
            dividend_history_verified=dividend_history_verified,
            price_semantics_verified=price_semantics_verified,
        )
        summary = report["full_universe_summary"]
        key = f"{requested}_sessions"
        detailed[key] = report
        rows.append(
            {
                "requested_sessions": requested,
                "evaluated_sessions": requested,
                "window_start": summary["window_start"],
                "window_end": summary["window_end"],
                "status": "PASS" if summary["passed"] else "FAIL",
                "passed": bool(summary["passed"]),
                "required_tickers": int(summary["required_tickers"]),
                "passed_tickers": int(summary["passed_tickers"]),
                "failed_tickers": int(summary["failed_tickers"]),
                "unknown_sessions": int(summary["unknown_sessions"]),
                "missing_active_prices": int(summary["missing_active_prices"]),
                "quarantined_nonactive_bars": int(summary["quarantined_nonactive_bars"]),
                "blocker_counts": dict(summary["blocker_counts"]),
            }
        )

    ladder = pd.DataFrame(rows)
    passing = ladder[ladder["passed"].eq(True) & ladder["evaluated_sessions"].gt(0)]
    if passing.empty:
        longest = None
    else:
        longest_row = passing.sort_values("evaluated_sessions").iloc[-1]
        longest = {
            "sessions": int(longest_row["evaluated_sessions"]),
            "window_start": longest_row["window_start"],
            "window_end": longest_row["window_end"],
        }

    summary = {
        "latest_session": sessions[-1].date().isoformat(),
        "available_calendar_sessions": int(len(sessions)),
        "horizons_tested": horizons,
        "passing_horizons": [
            int(value) for value in ladder.loc[ladder["passed"].eq(True), "evaluated_sessions"] if int(value) > 0
        ],
        "longest_passing_window": longest,
        "all_tested_horizons_pass": bool(len(ladder)) and bool(ladder["passed"].all()),
    }

    if output_dir is not None:
        target = Path(output_dir)
        write_csv_atomic(ladder, target / "history_certification_ladder.csv")
        _atomic_json(summary, target / "history_certification_summary.json")

    return {
        "summary": summary,
        "ladder": ladder.to_dict(orient="records"),
        "reports": detailed,
    }
