from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .data_gate import evaluate_data_gate
from .security_master import normalise_ticker
from .storage import write_csv_atomic


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
        raise ValueError("Full-universe gate requires at least one exchange session")
    return sessions


def required_tickers_for_window(
    security_master: pd.DataFrame,
    exchange_sessions: pd.DatetimeIndex,
    *,
    tradability_anchors: pd.DataFrame | None = None,
    tradability_intervals: pd.DataFrame | None = None,
) -> list[str]:
    """Discover every security that must be explained in the evaluated window.

    The primary candidate set is every security-master listing interval that
    overlaps the window. To prevent current-list omissions from creating a
    survivorship hole, official tradability point/interval evidence inside the
    same window also contributes ticker candidates. Evidence-only tickers are
    intentionally retained even when identity is missing; the DATA GATE then
    fails them as SECURITY_IDENTITY_UNRESOLVED until IDX/KSEI reconciliation.

    Yahoo/provider symbols never define this universe.
    """

    sessions = _canonical_sessions(exchange_sessions)
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
    required = set(overlaps["ticker"].dropna().map(normalise_ticker))

    if tradability_anchors is not None and not tradability_anchors.empty:
        anchor_required = {"ticker", "as_of_date"}
        anchor_missing = anchor_required - set(tradability_anchors.columns)
        if anchor_missing:
            raise ValueError(
                f"Tradability-anchor columns missing: {sorted(anchor_missing)}"
            )
        anchors = tradability_anchors.copy()
        anchors["as_of_date"] = pd.to_datetime(
            anchors["as_of_date"], errors="coerce"
        ).dt.normalize()
        anchors = anchors[
            anchors["as_of_date"].notna()
            & anchors["as_of_date"].ge(start)
            & anchors["as_of_date"].le(end)
        ]
        required.update(anchors["ticker"].dropna().map(normalise_ticker))

    if tradability_intervals is not None and not tradability_intervals.empty:
        interval_required = {"ticker", "effective_from", "effective_to"}
        interval_missing = interval_required - set(tradability_intervals.columns)
        if interval_missing:
            raise ValueError(
                f"Tradability-interval columns missing: {sorted(interval_missing)}"
            )
        intervals = tradability_intervals.copy()
        intervals["effective_from"] = pd.to_datetime(
            intervals["effective_from"], errors="coerce"
        ).dt.normalize()
        intervals["effective_to"] = pd.to_datetime(
            intervals["effective_to"], errors="coerce"
        ).dt.normalize()
        intervals = intervals[
            intervals["effective_from"].notna()
            & intervals["effective_from"].le(end)
            & (intervals["effective_to"].isna() | intervals["effective_to"].ge(start))
        ]
        required.update(intervals["ticker"].dropna().map(normalise_ticker))

    return sorted(ticker for ticker in required if ticker)


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
    applied to all securities discoverable from official listing identity and
    official tradability evidence. No model-universe liquidity filter is
    applied here: this is a market-data certification step, not alpha research.
    """

    sessions = _canonical_sessions(exchange_sessions)
    required = required_tickers_for_window(
        security_master,
        sessions,
        tradability_anchors=tradability_anchors,
        tradability_intervals=tradability_intervals,
    )
    if not required:
        raise ValueError("No securities are discoverable in the evaluated window")

    report = evaluate_data_gate(
        required,
        sessions,
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
    identity_unresolved = []
    if not ticker_gates.empty:
        for row in ticker_gates.itertuples(index=False):
            blockers = row.blockers if not isinstance(row.blockers, str) else (row.blockers,)
            if "SECURITY_IDENTITY_UNRESOLVED" in blockers:
                identity_unresolved.append(row.ticker)

    summary = {
        "passed": bool(report["passed"]),
        "window_start": sessions[0].date().isoformat(),
        "window_end": sessions[-1].date().isoformat(),
        "required_tickers": int(report["required_tickers"]),
        "passed_tickers": int(report["passed_tickers"]),
        "failed_tickers": int(report["failed_tickers"]),
        "identity_unresolved_tickers": sorted(identity_unresolved),
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
