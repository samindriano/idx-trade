from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pandas as pd

from .data_gate import evaluate_data_gate
from .security_master import normalise_ticker


ADVERSARIAL_COLUMNS = ("case_id", "ticker", "case_family", "gate_focus", "reference_note")


def load_adversarial_cases(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = set(ADVERSARIAL_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Adversarial case columns missing: {sorted(missing)}")
    data = frame[list(ADVERSARIAL_COLUMNS)].copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    if data["case_id"].duplicated().any():
        duplicated = data.loc[data["case_id"].duplicated(), "case_id"].tolist()
        raise ValueError(f"Duplicate adversarial case IDs: {duplicated[:10]}")
    if not data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False).all():
        raise ValueError("Adversarial catalog contains invalid IDX ticker symbols")
    return data.reset_index(drop=True)


def unique_required_tickers(cases: pd.DataFrame) -> list[str]:
    return sorted(cases["ticker"].dropna().map(normalise_ticker).unique().tolist())


def run_adversarial_data_gate(
    cases: pd.DataFrame,
    exchange_sessions: pd.DatetimeIndex,
    price_frames: Mapping[str, pd.DataFrame],
    security_master: pd.DataFrame,
    tradability_intervals: pd.DataFrame,
    tradability_coverage_windows: pd.DataFrame,
    *,
    corporate_action_verified: Mapping[str, bool],
    price_semantics_verified: Mapping[str, bool] | None = None,
) -> dict[str, object]:
    """Run the hard data gate on deliberately difficult IDX names.

    The catalog is a QA suite, not a model universe. A pass means the data layer
    can explain these cases without silently dropping or inventing trading data.
    """

    required = unique_required_tickers(cases)
    report = evaluate_data_gate(
        required,
        exchange_sessions,
        price_frames,
        security_master,
        tradability_intervals,
        tradability_coverage_windows,
        corporate_action_verified=corporate_action_verified,
        price_semantics_verified=price_semantics_verified,
    )

    ticker_gate = pd.DataFrame(report["ticker_gates"])
    case_rows = cases.merge(ticker_gate, on="ticker", how="left", validate="many_to_one")
    family_rows: list[dict[str, object]] = []
    for family, group in case_rows.groupby("case_family", sort=True):
        family_rows.append(
            {
                "case_family": family,
                "cases": int(len(group)),
                "unique_tickers": int(group["ticker"].nunique()),
                "passed_cases": int(group["passed"].fillna(False).sum()),
                "failed_cases": int((~group["passed"].fillna(False)).sum()),
                "passed": bool(group["passed"].fillna(False).all()),
            }
        )

    return {
        **report,
        "case_count": int(len(cases)),
        "case_family_summary": family_rows,
        "case_results": case_rows.to_dict(orient="records"),
    }
