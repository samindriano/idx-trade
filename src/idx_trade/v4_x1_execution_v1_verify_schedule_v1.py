"""Dual-calendar verification for forward PAPER EOD execution inputs.

Observed IDX statistical sessions prove that the decision session actually
occurred.  A separate hash-pinned planned Bursa schedule proves which future
session is the next permissible execution date.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from .official_trading_schedule_v1 import (
    OfficialTradingScheduleError,
    VerifiedOfficialTradingSchedule,
    load_verified_official_trading_schedule,
    next_planned_session,
)
from .v4_x1_decision_v1_contract import DecisionV1Error, _normalize_ticker
from .v4_x1_execution_v1_verify import (
    VerifiedEODExecutionInputs,
    _EOD_INPUT_TOKEN,
    _date,
    _finite_nonnegative,
    _finite_positive,
    _sha256,
)


@dataclass(frozen=True)
class VerifiedScheduledEODExecutionInputs(VerifiedEODExecutionInputs):
    execution_schedule_attestation_path: Path
    execution_schedule_attestation_sha256: str
    execution_schedule_source_path: Path
    execution_schedule_source_sha256: str
    execution_schedule_source_reference: str


def verify_eod_execution_inputs_with_schedule(
    *,
    session_ohlcv_path: str | Path,
    model_input_path: str | Path,
    official_calendar_path: str | Path,
    execution_schedule_attestation_path: str | Path,
    execution_schedule_attestation_sha256: str,
    decision_session_date: str,
    required_tickers: Sequence[str],
) -> VerifiedScheduledEODExecutionInputs:
    """Verify EOD provenance and derive next execution from planned schedule."""

    session_date = _date(
        decision_session_date, "EXECUTION_V1_EOD_SESSION_DATE_INVALID"
    )
    ohlcv_path = Path(session_ohlcv_path).expanduser().resolve()
    model_path = Path(model_input_path).expanduser().resolve()
    calendar_path = Path(official_calendar_path).expanduser().resolve()
    for path, code in (
        (ohlcv_path, "EXECUTION_V1_EOD_OHLCV_ARTIFACT_MISSING"),
        (model_path, "EXECUTION_V1_EOD_MODEL_INPUT_MISSING"),
        (calendar_path, "EXECUTION_V1_OFFICIAL_CALENDAR_MISSING"),
    ):
        if not path.is_file():
            raise DecisionV1Error(f"{code}:{path}")

    # OBSERVED authority: prove the decision session actually occurred.
    calendar = pd.read_csv(calendar_path)
    if "date" not in calendar.columns:
        raise DecisionV1Error("EXECUTION_V1_OFFICIAL_CALENDAR_DATE_MISSING")
    sessions = pd.to_datetime(calendar["date"], errors="coerce")
    if sessions.isna().any():
        raise DecisionV1Error("EXECUTION_V1_OFFICIAL_CALENDAR_DATE_INVALID")
    normalized_sessions = [
        pd.Timestamp(value).tz_localize(None).normalize().date().isoformat()
        for value in sessions
    ]
    if len(normalized_sessions) != len(set(normalized_sessions)):
        raise DecisionV1Error("EXECUTION_V1_OFFICIAL_CALENDAR_DUPLICATE_DATE")
    observed_sessions = sorted(set(normalized_sessions))
    if any(pd.Timestamp(value).weekday() >= 5 for value in observed_sessions):
        raise DecisionV1Error("EXECUTION_V1_OFFICIAL_CALENDAR_WEEKEND_SESSION")
    if session_date not in observed_sessions:
        raise DecisionV1Error("EXECUTION_V1_DECISION_DATE_NOT_OFFICIAL_SESSION")

    # PLANNED authority: prove holiday semantics and the future successor.
    try:
        schedule = load_verified_official_trading_schedule(
            execution_schedule_attestation_path,
            expected_sha256=execution_schedule_attestation_sha256,
        )
        next_session = next_planned_session(schedule, session_date)
    except OfficialTradingScheduleError as exc:
        message = str(exc)
        if message == "OFFICIAL_SCHEDULE_NEXT_SESSION_UNAVAILABLE":
            raise DecisionV1Error("EXECUTION_V1_NEXT_OFFICIAL_SESSION_UNAVAILABLE") from exc
        if message == "OFFICIAL_SCHEDULE_DECISION_NOT_SCHEDULED_SESSION":
            raise DecisionV1Error("EXECUTION_V1_OBSERVED_PLANNED_SESSION_CONFLICT") from exc
        raise DecisionV1Error(f"EXECUTION_V1_EXECUTION_SCHEDULE_INVALID:{message}") from exc

    ohlcv = pd.read_parquet(ohlcv_path)
    model = pd.read_parquet(model_path)
    required_ohlcv = {"ticker", "session_date", "close"}
    required_model = {"ticker", "date", "close", "regular_market_value"}
    if not required_ohlcv.issubset(ohlcv.columns):
        raise DecisionV1Error("EXECUTION_V1_EOD_OHLCV_SCHEMA_INVALID")
    if not required_model.issubset(model.columns):
        raise DecisionV1Error("EXECUTION_V1_EOD_MODEL_INPUT_SCHEMA_INVALID")

    left = ohlcv.loc[:, ["ticker", "session_date", "close"]].copy()
    right = model.loc[:, ["ticker", "date", "close", "regular_market_value"]].copy()
    left["ticker"] = left["ticker"].map(_normalize_ticker)
    right["ticker"] = right["ticker"].map(_normalize_ticker)
    if left["ticker"].duplicated().any() or right["ticker"].duplicated().any():
        raise DecisionV1Error("EXECUTION_V1_EOD_DUPLICATE_TICKER")

    left_dates = pd.to_datetime(left["session_date"], errors="coerce")
    right_dates = pd.to_datetime(right["date"], errors="coerce")
    if left_dates.isna().any() or right_dates.isna().any():
        raise DecisionV1Error("EXECUTION_V1_EOD_ARTIFACT_DATE_INVALID")
    if not all(
        _date(value, "EXECUTION_V1_EOD_ARTIFACT_DATE_INVALID") == session_date
        for value in left_dates
    ):
        raise DecisionV1Error("EXECUTION_V1_EOD_OHLCV_DATE_MISMATCH")
    if not all(
        _date(value, "EXECUTION_V1_EOD_ARTIFACT_DATE_INVALID") == session_date
        for value in right_dates
    ):
        raise DecisionV1Error("EXECUTION_V1_EOD_MODEL_DATE_MISMATCH")

    merged = right.merge(
        left.rename(columns={"close": "ohlcv_close"})[["ticker", "ohlcv_close"]],
        on="ticker",
        how="left",
        validate="one_to_one",
    )
    if merged["ohlcv_close"].isna().any():
        raise DecisionV1Error("EXECUTION_V1_EOD_TICKER_SET_MISMATCH")
    close_model = pd.to_numeric(merged["close"], errors="coerce")
    close_ohlcv = pd.to_numeric(merged["ohlcv_close"], errors="coerce")
    if close_model.isna().any() or close_ohlcv.isna().any():
        raise DecisionV1Error("EXECUTION_V1_EOD_CLOSE_INVALID")
    if not ((close_model - close_ohlcv).abs() <= 1e-10).all():
        raise DecisionV1Error("EXECUTION_V1_EOD_CLOSE_PROVENANCE_MISMATCH")

    closes: dict[str, float] = {}
    regular_values: dict[str, float] = {}
    for row in merged.itertuples(index=False):
        close = _finite_positive(row.close)
        value = _finite_nonnegative(row.regular_market_value)
        if close is not None:
            closes[row.ticker] = close
        regular_values[row.ticker] = 0.0 if value is None else value

    required = {_normalize_ticker(value) for value in required_tickers}
    missing_close = required - set(closes)
    if missing_close:
        raise DecisionV1Error(
            f"EXECUTION_V1_EOD_REQUIRED_CLOSE_MISSING:{sorted(missing_close)}"
        )

    return VerifiedScheduledEODExecutionInputs(
        session_date=session_date,
        next_official_session_date=next_session,
        raw_close_prices=closes,
        regular_market_values=regular_values,
        ohlcv_artifact_path=ohlcv_path,
        ohlcv_artifact_sha256=_sha256(ohlcv_path),
        model_input_path=model_path,
        model_input_sha256=_sha256(model_path),
        official_calendar_path=calendar_path,
        official_calendar_sha256=_sha256(calendar_path),
        _verification_token=_EOD_INPUT_TOKEN,
        execution_schedule_attestation_path=schedule.attestation_path,
        execution_schedule_attestation_sha256=schedule.attestation_sha256,
        execution_schedule_source_path=schedule.source_document_path,
        execution_schedule_source_sha256=schedule.source_document_sha256,
        execution_schedule_source_reference=schedule.source_reference,
    )


def schedule_from_eod_inputs(
    value: VerifiedScheduledEODExecutionInputs,
) -> VerifiedOfficialTradingSchedule:
    return load_verified_official_trading_schedule(
        value.execution_schedule_attestation_path,
        expected_sha256=value.execution_schedule_attestation_sha256,
    )


__all__ = [
    "VerifiedScheduledEODExecutionInputs",
    "schedule_from_eod_inputs",
    "verify_eod_execution_inputs_with_schedule",
]
