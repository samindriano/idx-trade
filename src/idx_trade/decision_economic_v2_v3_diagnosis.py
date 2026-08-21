from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .decision_economic_comparison import (
    HistoricalSource,
    PolicyMembership,
    TARGET_SEATS,
    SEAT_WEIGHT,
    load_historical_source,
    load_structural_membership,
)


class DecisionEconomicV2V3DiagnosisError(RuntimeError):
    pass


def _dist(values: pd.Series | list[float]) -> dict[str, Any]:
    clean = pd.Series(values, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
            "positive_share": None,
        }
    return {
        "n": int(len(clean)),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "p25": float(clean.quantile(0.25)),
        "p75": float(clean.quantile(0.75)),
        "positive_share": float(clean.gt(0.0).mean()),
    }


def _rank_band(rank: int | None) -> str:
    if rank is None:
        return "ABSENT"
    if rank <= 20:
        return "LE20"
    if rank <= 50:
        return "R21_50"
    return "GT50"


def _return_lookup(source: HistoricalSource, horizon: int) -> dict[tuple[pd.Timestamp, str], float]:
    state_col = f"target_state_h{horizon}"
    ret_col = f"r{horizon}"
    available_state = f"TARGET_H{horizon}_AVAILABLE"
    frame = source.targets.loc[
        source.targets[state_col].eq(available_state), ["date", "ticker", ret_col]
    ].copy()
    frame[ret_col] = pd.to_numeric(frame[ret_col], errors="coerce")
    frame = frame.loc[np.isfinite(frame[ret_col])].copy()
    return {
        (pd.Timestamp(row.date), str(row.ticker)): float(getattr(row, ret_col))
        for row in frame.itertuples(index=False)
    }


def _rank_lookup(source: HistoricalSource) -> dict[tuple[pd.Timestamp, str], int]:
    frame = source.scores.copy()
    frame = frame.sort_values(
        ["date", "alpha_consensus", "ticker"],
        ascending=[True, False, True],
        kind="mergesort",
    )
    frame["rank_consensus"] = frame.groupby("date").cumcount() + 1
    return {
        (pd.Timestamp(row.date), str(row.ticker)): int(row.rank_consensus)
        for row in frame[["date", "ticker", "rank_consensus"]].itertuples(index=False)
    }


def _complete_support(
    tickers: tuple[str, ...],
    date: pd.Timestamp,
    lookup: dict[tuple[pd.Timestamp, str], float],
) -> bool:
    return all((date, ticker) in lookup for ticker in tickers)


def diagnose_loaded(
    source: HistoricalSource,
    v2: PolicyMembership,
    v3: PolicyMembership,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    rank_lookup = _rank_lookup(source)
    session_rows: list[dict[str, Any]] = []
    differential_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "schema_version": "decision_economic_v2_v3_focused_diagnosis_v1",
        "status": "COMPLETE_DEVELOPMENT_V2_V3_FOCUSED_ECONOMIC_DIAGNOSIS",
        "interpretation_boundary": {
            "development_evidence_only": True,
            "executable_policy_pnl": False,
            "threshold_search": False,
            "mechanisms": [
                "FULL_TARGET_PURE_MEMBERSHIP_SUBSTITUTION",
                "V2_UNDERFILL_MIXED_CASH_AND_SUBSTITUTION_NOT_UNIQUELY_DECOMPOSABLE",
            ],
            "headline_question": "DOES_V2_VALUE_MAINLY_SURVIVE_BY_RETAINING_NAMES_V3_REPLACES_OR_BY_UNDERFILL_CASH",
        },
        "horizons": {},
    }

    dates = tuple(pd.Timestamp(x) for x in source.dates)
    if tuple(sorted(v2.by_date)) != dates or tuple(sorted(v3.by_date)) != dates:
        raise DecisionEconomicV2V3DiagnosisError("POLICY_DATE_IDENTITY_MISMATCH")

    for horizon in (5, 10):
        returns = _return_lookup(source, horizon)
        horizon_sessions: list[dict[str, Any]] = []
        horizon_details: list[dict[str, Any]] = []

        for index, date in enumerate(dates):
            v2_names = tuple(v2.by_date[date])
            v3_names = tuple(v3.by_date[date])
            if not (
                _complete_support(v2_names, date, returns)
                and _complete_support(v3_names, date, returns)
            ):
                continue

            v2_set = set(v2_names)
            v3_set = set(v3_names)
            common = v2_set & v3_set
            v2_only = sorted(v2_set - v3_set)
            v3_only = sorted(v3_set - v2_set)
            gross_v2 = SEAT_WEIGHT * sum(returns[(date, ticker)] for ticker in v2_names)
            gross_v3 = SEAT_WEIGHT * sum(returns[(date, ticker)] for ticker in v3_names)
            delta = gross_v2 - gross_v3
            full_target = len(v2_names) == TARGET_SEATS and len(v3_names) == TARGET_SEATS
            mechanism = (
                "FULL_TARGET_PURE_MEMBERSHIP_SUBSTITUTION"
                if full_target
                else "V2_UNDERFILL_MIXED_CASH_AND_SUBSTITUTION_NOT_UNIQUELY_DECOMPOSABLE"
            )
            previous_v2 = set(v2.by_date[dates[index - 1]]) if index > 0 else set()
            previous_v3 = set(v3.by_date[dates[index - 1]]) if index > 0 else set()

            row = {
                "horizon": horizon,
                "session_index": index,
                "date": date.date().isoformat(),
                "mechanism": mechanism,
                "v2_target_size": len(v2_names),
                "v3_target_size": len(v3_names),
                "v2_cash_slots": TARGET_SEATS - len(v2_names),
                "common_count": len(common),
                "v2_only_count": len(v2_only),
                "v3_only_count": len(v3_only),
                "v2_gross": gross_v2,
                "v3_gross": gross_v3,
                "v2_minus_v3_gross": delta,
            }
            horizon_sessions.append(row)
            session_rows.append(row)

            for policy, tickers, previous in (
                ("V2_ONLY", v2_only, previous_v2),
                ("V3_ONLY", v3_only, previous_v3),
            ):
                for ticker in tickers:
                    rank = rank_lookup.get((date, ticker))
                    detail = {
                        "horizon": horizon,
                        "session_index": index,
                        "date": date.date().isoformat(),
                        "mechanism": mechanism,
                        "side": policy,
                        "ticker": ticker,
                        "return": returns[(date, ticker)],
                        "current_rank": rank,
                        "rank_band": _rank_band(rank),
                        "retained_from_previous_same_policy": ticker in previous,
                    }
                    horizon_details.append(detail)
                    differential_rows.append(detail)

        session_frame = pd.DataFrame(horizon_sessions)
        detail_frame = pd.DataFrame(horizon_details)
        if session_frame.empty:
            raise DecisionEconomicV2V3DiagnosisError(f"H{horizon}_NO_PAIRWISE_SUPPORT")

        full_sessions = session_frame.loc[
            session_frame["mechanism"].eq("FULL_TARGET_PURE_MEMBERSHIP_SUBSTITUTION")
        ]
        underfill_sessions = session_frame.loc[
            session_frame["mechanism"].eq(
                "V2_UNDERFILL_MIXED_CASH_AND_SUBSTITUTION_NOT_UNIQUELY_DECOMPOSABLE"
            )
        ]
        full_details = detail_frame.loc[
            detail_frame["mechanism"].eq("FULL_TARGET_PURE_MEMBERSHIP_SUBSTITUTION")
        ]

        def _side_summary(side: str) -> dict[str, Any]:
            part = full_details.loc[full_details["side"].eq(side)].copy()
            if part.empty:
                return {
                    "entries": 0,
                    "return": _dist([]),
                    "retained_share": None,
                    "rank_band": {},
                }
            by_band: dict[str, Any] = {}
            for band in ("LE20", "R21_50", "GT50", "ABSENT"):
                band_part = part.loc[part["rank_band"].eq(band)]
                by_band[band] = {
                    "entries": int(len(band_part)),
                    "return": _dist(band_part["return"]),
                    "retained_share": (
                        float(band_part["retained_from_previous_same_policy"].mean())
                        if len(band_part)
                        else None
                    ),
                }
            return {
                "entries": int(len(part)),
                "return": _dist(part["return"]),
                "retained_share": float(
                    part["retained_from_previous_same_policy"].mean()
                ),
                "rank_band": by_band,
            }

        retained_v2 = full_details.loc[
            full_details["side"].eq("V2_ONLY")
            & full_details["retained_from_previous_same_policy"].astype(bool)
        ]
        new_v3 = full_details.loc[
            full_details["side"].eq("V3_ONLY")
            & ~full_details["retained_from_previous_same_policy"].astype(bool)
        ]

        summary["horizons"][f"H{horizon}"] = {
            "pairwise_complete_support_dates": int(len(session_frame)),
            "overall_v2_minus_v3_gross": _dist(session_frame["v2_minus_v3_gross"]),
            "full_target_pure_substitution": {
                "dates": int(len(full_sessions)),
                "v2_minus_v3_gross": _dist(full_sessions["v2_minus_v3_gross"]),
                "v2_only": _side_summary("V2_ONLY"),
                "v3_only": _side_summary("V3_ONLY"),
                "v2_only_retained": {
                    "entries": int(len(retained_v2)),
                    "return": _dist(retained_v2["return"]),
                    "rank_band_counts": {
                        band: int(retained_v2["rank_band"].eq(band).sum())
                        for band in ("LE20", "R21_50", "GT50", "ABSENT")
                    },
                },
                "v3_only_new": {
                    "entries": int(len(new_v3)),
                    "return": _dist(new_v3["return"]),
                    "rank_band_counts": {
                        band: int(new_v3["rank_band"].eq(band).sum())
                        for band in ("LE20", "R21_50", "GT50", "ABSENT")
                    },
                },
            },
            "v2_underfill_mixed": {
                "dates": int(len(underfill_sessions)),
                "mean_v2_cash_slots": (
                    float(underfill_sessions["v2_cash_slots"].mean())
                    if len(underfill_sessions)
                    else None
                ),
                "v2_minus_v3_gross": _dist(underfill_sessions["v2_minus_v3_gross"]),
                "warning": "CASH_AND_MEMBERSHIP_SUBSTITUTION_ARE_NOT_UNIQUELY_IDENTIFIABLE_WITHOUT_ARBITRARY_SEAT_MATCHING",
            },
        }

    sessions = pd.DataFrame(session_rows).sort_values(
        ["horizon", "session_index"], kind="mergesort"
    ).reset_index(drop=True)
    details = pd.DataFrame(differential_rows).sort_values(
        ["horizon", "session_index", "side", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
    return summary, sessions, details


def run_v2_v3_diagnosis(
    historical_root: str | Path,
    v2_root: str | Path,
    v3_root: str | Path,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, HistoricalSource, PolicyMembership, PolicyMembership]:
    source = load_historical_source(historical_root)
    v2 = load_structural_membership(v2_root, "DECISION_V2", source.dates)
    v3 = load_structural_membership(v3_root, "DECISION_V3", source.dates)
    summary, sessions, details = diagnose_loaded(source, v2, v3)
    return summary, sessions, details, source, v2, v3
