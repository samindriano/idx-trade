from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .data_gate import evaluate_data_gate
from .security_master import normalise_ticker
from .storage import write_csv_atomic


def required_tickers_for_window(
    security_master: pd.DataFrame,
    exchange_sessions: pd.DatetimeIndex,
) -> list[str]:
    """Return securities whose listing interval overlaps the evaluated window.

    This is deliberately point-in-time. A current-active list must never define
    the historical research universe. Securities delisted before the window and
    IPOs listed after it are excluded from the required model universe, while
    any listing interval that touches at least one evaluated exchange session is
    included.
    """

    sessions = (
        pd.DatetimeIndex(pd.to_datetime(exchange_sessions))
        .dropna()
        .tz_localize(None)
        .normalize()
        .unique()
        .sort_values()
    )
    if len(sessions) == 0:
        raise ValueError("Full-universe gate requires at least one exchange session")

    required_columns = {"ticker", "listed_from", "listed_to"}
    missing = required_columns - set(security_master.columns)
    if missing:
        raise ValueError(f"Security-master columns missing: {sorted(missing)}")

    start = pd.Timestamp(sessions[0]).normalize()
    end = pd.Timestamp(sessions[-1]).normalize()
    master = security_master.copy()
    master["ticker"] = master["ticker"].map(normalise_ticker)
    master["listed_from"] = pd.to_datetime(master["listed_from"], errors="coerce").dt.normalize()
    master["listed_to"] = pd.to_datetime(master["listed_to"], errors="coerce").dt.normalize()
    master = master.dropna(subset=["ticker", "listed_from"])

    overlaps = master[
        master["listed_from"].le(end)
        & (master["listed_to"].isna() | master["listed_to"].ge(start))
    ]
    return sorted(overlaps["ticker"].dropna().unique().tolist())


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def _blocker_counts(ticker_gates: pd.DataFrame) -> dict[str, int]:
    counts: Counter[str] = Counter()
    if ticker_gates.empty or "blockers" not in ticker_gates.columns:
        return {}
    for value in ticker_gates["blockers"]:
        if isinstance(value, str):
            blockers = [value] if value else []
        else:
            blockers = list(value or ())
        counts.update(str(blocker) for blocker in blockers)
    return dict(sorted(counts.items()))


def run_full_universe_data_gate(
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
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    """Certify the complete point-in-time IDX universe for one bounded window.

    The exact same hard per-security DATA GATE used by the adversarial suite is
    applied to every security whose official listing interval overlaps the
    evaluated exchange-session window. No model-universe liquidity filter is
    applied here: this is a market-data certification step, not alpha research.
    """

    required = required_tickers_for_window(security_master, exchange_sessions)
    if not required:
        raise ValueError("No listed securities overlap the evaluated window")

    report = evaluate_data_gate(
        required,
        exchange_sessions,
        price_frames,
        security_master,
        tradability_intervals,
        tradability_coverage_windows,
        tradability_anchors=tradability_anchors,
        split_history_verified=split_history_verified,
        dividend_history_verified=dividend_history_verified,
        price_semantics_verified=price_semantics_verified,
    )

    ticker_gates = pd.DataFrame(report["ticker_gates"])
    session_reports = pd.DataFrame(report["session_coverage"]["reports"])
    summary = {
        "passed": bool(report["passed"]),
        "window_start": pd.Timestamp(pd.DatetimeIndex(exchange_sessions).min()).date().isoformat(),
        "window_end": pd.Timestamp(pd.DatetimeIndex(exchange_sessions).max()).date().isoformat(),
        "required_tickers": int(report["required_tickers"]),
        "passed_tickers": int(report["passed_tickers"]),
        "failed_tickers": int(report["failed_tickers"]),
        "price_required_tickers": (
            int(ticker_gates["price_requirements_applicable"].fillna(False).sum())
            if not ticker_gates.empty
            else 0
        ),
        "unknown_sessions": (
            int(session_reports["unknown_tradability_sessions"].sum())
            if not session_reports.empty
            else 0
        ),
        "missing_active_prices": (
            int(session_reports["missing_expected_sessions"].sum())
            if not session_reports.empty
            else 0
        ),
        "quarantined_nonactive_bars": int(
            report["session_coverage"].get("quarantined_nonactive_bars", 0)
        ),
        "blocker_counts": _blocker_counts(ticker_gates),
        "failed_ticker_symbols": list(report["failed_ticker_symbols"]),
    }

    result = {**report, "full_universe_summary": summary}
    if output_dir is not None:
        target = Path(output_dir)
        write_csv_atomic(ticker_gates, target / "full_universe_ticker_gates.csv")
        write_csv_atomic(session_reports, target / "full_universe_session_coverage.csv")
        _atomic_json(summary, target / "full_universe_gate_summary.json")

    return result
