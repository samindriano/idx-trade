from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Mapping, Sequence

import pandas as pd

from .official_open_evidence_v1 import (
    ALLOWED_TRANSPORTS as OFFICIAL_OPEN_ALLOWED_TRANSPORTS,
    AUTHORITY as OFFICIAL_OPEN_AUTHORITY,
    FALLBACK_POLICY as OFFICIAL_OPEN_FALLBACK_POLICY,
    FIELD_SEMANTICS as OFFICIAL_OPEN_FIELD_SEMANTICS,
    SCHEMA_VERSION as OFFICIAL_OPEN_SCHEMA_VERSION,
    TRANSPORT_POLICY as OFFICIAL_OPEN_TRANSPORT_POLICY,
    UPSTREAM_PATH as OFFICIAL_OPEN_UPSTREAM_PATH,
    OfficialOpenEvidenceError,
    normalize_idx_stock_summary_payload,
    validate_transport_provenance,
)
from .v4_x1_decision_v1_contract import DecisionV1Error, _normalize_ticker

_EOD_INPUT_TOKEN = object()
_OPEN_INPUT_TOKEN = object()
_CA_ATTESTATION_TOKEN = object()
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _date(value: object, code: str) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise DecisionV1Error(code)
    return pd.Timestamp(parsed).tz_localize(None).normalize().date().isoformat()


def _finite_positive(value: object) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) and x > 0 else None


def _finite_nonnegative(value: object) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) and x >= 0 else None


@dataclass(frozen=True)
class VerifiedEODExecutionInputs:
    session_date: str
    next_official_session_date: str
    raw_close_prices: Mapping[str, float]
    regular_market_values: Mapping[str, float]
    ohlcv_artifact_path: Path
    ohlcv_artifact_sha256: str
    model_input_path: Path
    model_input_sha256: str
    official_calendar_path: Path
    official_calendar_sha256: str
    _verification_token: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class VerifiedOpenExecutionInputs:
    session_date: str
    raw_open_prices: Mapping[str, float]
    available_tickers: frozenset[str]
    ohlcv_artifact_path: Path
    ohlcv_artifact_sha256: str
    _verification_token: object = field(repr=False, compare=False)
    manifest_path: Path | None = None
    manifest_sha256: str = ""
    raw_source_path: Path | None = None
    raw_source_sha256: str = ""
    authority: str = ""
    upstream_path: str = ""
    field_semantics: str = ""
    fallback_policy: str = ""
    transport: str = ""
    transport_policy: str = ""


@dataclass(frozen=True)
class VerifiedCorporateActionAttestation:
    from_session_date: str
    through_session_date: str
    covered_tickers: frozenset[str]
    status: str
    attestation_path: Path
    attestation_sha256: str
    source_path: Path
    source_sha256: str
    _verification_token: object = field(repr=False, compare=False)


def verify_eod_execution_inputs(
    *,
    session_ohlcv_path: str | Path,
    model_input_path: str | Path,
    official_calendar_path: str | Path,
    decision_session_date: str,
    required_tickers: Sequence[str],
) -> VerifiedEODExecutionInputs:
    session_date = _date(decision_session_date, "EXECUTION_V1_EOD_SESSION_DATE_INVALID")
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

    ohlcv = pd.read_parquet(ohlcv_path)
    model = pd.read_parquet(model_path)
    calendar = pd.read_csv(calendar_path)
    if "date" not in calendar.columns:
        raise DecisionV1Error("EXECUTION_V1_OFFICIAL_CALENDAR_DATE_MISSING")
    sessions = pd.to_datetime(calendar["date"], errors="coerce")
    if sessions.isna().any():
        raise DecisionV1Error("EXECUTION_V1_OFFICIAL_CALENDAR_DATE_INVALID")
    normalized_sessions = [
        pd.Timestamp(x).tz_localize(None).normalize().date().isoformat()
        for x in sessions
    ]
    if len(normalized_sessions) != len(set(normalized_sessions)):
        raise DecisionV1Error("EXECUTION_V1_OFFICIAL_CALENDAR_DUPLICATE_DATE")
    session_keys = sorted(set(normalized_sessions))
    if any(pd.Timestamp(x).weekday() >= 5 for x in session_keys):
        raise DecisionV1Error("EXECUTION_V1_OFFICIAL_CALENDAR_WEEKEND_SESSION")
    if session_date not in session_keys:
        raise DecisionV1Error("EXECUTION_V1_DECISION_DATE_NOT_OFFICIAL_SESSION")
    idx = session_keys.index(session_date)
    if idx + 1 >= len(session_keys):
        raise DecisionV1Error("EXECUTION_V1_NEXT_OFFICIAL_SESSION_UNAVAILABLE")
    next_session = session_keys[idx + 1]

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
        _date(x, "EXECUTION_V1_EOD_ARTIFACT_DATE_INVALID") == session_date
        for x in left_dates
    ):
        raise DecisionV1Error("EXECUTION_V1_EOD_OHLCV_DATE_MISMATCH")
    if not all(
        _date(x, "EXECUTION_V1_EOD_ARTIFACT_DATE_INVALID") == session_date
        for x in right_dates
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

    closes = {}
    regular_values = {}
    invalid_regular_values = []
    for row in merged.itertuples(index=False):
        close = _finite_positive(row.close)
        value = _finite_nonnegative(row.regular_market_value)
        if close is not None:
            closes[row.ticker] = close
        if value is None:
            invalid_regular_values.append(row.ticker)
        else:
            regular_values[row.ticker] = value

    if invalid_regular_values:
        raise DecisionV1Error(
            "EXECUTION_V1_EOD_REGULAR_MARKET_VALUE_INVALID:"
            + str(sorted(invalid_regular_values))
        )

    required = {_normalize_ticker(x) for x in required_tickers}
    missing_close = required - set(closes)
    if missing_close:
        raise DecisionV1Error(
            f"EXECUTION_V1_EOD_REQUIRED_CLOSE_MISSING:{sorted(missing_close)}"
        )

    return VerifiedEODExecutionInputs(
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
    )


def _resolve_manifest_artifact(manifest_path: Path, raw_value: object, code: str) -> Path:
    text = str(raw_value or "").strip()
    if not text:
        raise DecisionV1Error(code)
    path = Path(text)
    if not path.is_absolute():
        path = (manifest_path.parent / path).resolve()
    else:
        path = path.expanduser().resolve()
    if not path.is_file():
        raise DecisionV1Error(code)
    return path


def _numeric_series_equal(left: pd.Series, right: pd.Series) -> bool:
    a = pd.to_numeric(left, errors="coerce")
    b = pd.to_numeric(right, errors="coerce")
    return bool(((a.isna() & b.isna()) | a.eq(b)).all())


def verify_open_execution_inputs(
    *,
    execution_session_date: str,
    manifest_path: str | Path | None = None,
    session_ohlcv_path: str | Path | None = None,
) -> VerifiedOpenExecutionInputs:
    """Admit only hash-bound official IDX Stock Summary OpenPrice evidence."""

    session_date = _date(
        execution_session_date, "EXECUTION_V1_OPEN_SESSION_DATE_INVALID"
    )
    if manifest_path is None:
        suffix = (
            f":{Path(session_ohlcv_path).expanduser()}"
            if session_ohlcv_path is not None
            else ""
        )
        raise DecisionV1Error(
            f"EXECUTION_V1_OPEN_CERTIFIED_MANIFEST_REQUIRED{suffix}"
        )

    manifest = Path(manifest_path).expanduser().resolve()
    if not manifest.is_file():
        raise DecisionV1Error(f"EXECUTION_V1_OPEN_MANIFEST_MISSING:{manifest}")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV1Error("EXECUTION_V1_OPEN_MANIFEST_INVALID") from exc
    if not isinstance(payload, dict):
        raise DecisionV1Error("EXECUTION_V1_OPEN_MANIFEST_NOT_OBJECT")

    expected_contract = {
        "schema_version": OFFICIAL_OPEN_SCHEMA_VERSION,
        "authority": OFFICIAL_OPEN_AUTHORITY,
        "upstream_path": OFFICIAL_OPEN_UPSTREAM_PATH,
        "transport_policy": OFFICIAL_OPEN_TRANSPORT_POLICY,
        "field_semantics": OFFICIAL_OPEN_FIELD_SEMANTICS,
        "fallback_policy": OFFICIAL_OPEN_FALLBACK_POLICY,
        "execution_grade": True,
        "duplicate_key_count": 0,
    }
    for key, value in expected_contract.items():
        if payload.get(key) != value:
            raise DecisionV1Error(
                f"EXECUTION_V1_OPEN_MANIFEST_CONTRACT_CHANGED:{key}"
            )
    transport = str(payload.get("transport") or "")
    if transport not in OFFICIAL_OPEN_ALLOWED_TRANSPORTS:
        raise DecisionV1Error("EXECUTION_V1_OPEN_MANIFEST_CONTRACT_CHANGED:transport")

    manifest_session = _date(
        payload.get("session_date"), "EXECUTION_V1_OPEN_MANIFEST_DATE_INVALID"
    )
    if manifest_session != session_date:
        raise DecisionV1Error("EXECUTION_V1_OPEN_MANIFEST_DATE_MISMATCH")

    raw_path = _resolve_manifest_artifact(
        manifest,
        payload.get("raw_artifact_path"),
        "EXECUTION_V1_OPEN_RAW_ARTIFACT_MISSING",
    )
    normalized_path = _resolve_manifest_artifact(
        manifest,
        payload.get("normalized_artifact_path"),
        "EXECUTION_V1_OPEN_NORMALIZED_ARTIFACT_MISSING",
    )
    declared_raw_sha = str(payload.get("raw_artifact_sha256") or "")
    declared_normalized_sha = str(payload.get("normalized_artifact_sha256") or "")
    if not _SHA256_RE.fullmatch(declared_raw_sha):
        raise DecisionV1Error("EXECUTION_V1_OPEN_RAW_SHA_INVALID")
    if not _SHA256_RE.fullmatch(declared_normalized_sha):
        raise DecisionV1Error("EXECUTION_V1_OPEN_NORMALIZED_SHA_INVALID")
    actual_raw_sha = _sha256(raw_path)
    actual_normalized_sha = _sha256(normalized_path)
    if actual_raw_sha != declared_raw_sha:
        raise DecisionV1Error("EXECUTION_V1_OPEN_RAW_SHA_MISMATCH")
    if actual_normalized_sha != declared_normalized_sha:
        raise DecisionV1Error("EXECUTION_V1_OPEN_NORMALIZED_SHA_MISMATCH")

    raw_bytes = raw_path.read_bytes()
    try:
        validate_transport_provenance(raw_bytes, transport=transport)
        raw_frame, counts = normalize_idx_stock_summary_payload(
            raw_bytes, expected_session_date=session_date
        )
    except OfficialOpenEvidenceError as exc:
        raise DecisionV1Error(
            f"EXECUTION_V1_OPEN_RAW_EVIDENCE_INVALID:{exc}"
        ) from exc

    for key, expected_value in (
        ("row_count", counts["row_count"]),
        ("unique_ticker_count", counts["unique_ticker_count"]),
        ("records_total", counts["records_total"]),
        ("records_filtered", counts["records_filtered"]),
    ):
        try:
            declared = int(payload.get(key))
        except (TypeError, ValueError) as exc:
            raise DecisionV1Error(
                f"EXECUTION_V1_OPEN_MANIFEST_COUNT_INVALID:{key}"
            ) from exc
        if declared != int(expected_value):
            raise DecisionV1Error(
                f"EXECUTION_V1_OPEN_MANIFEST_COUNT_MISMATCH:{key}"
            )

    frame = pd.read_parquet(normalized_path)
    required = {"ticker", "session_date", "open_price", "first_trade"}
    if not required.issubset(frame.columns):
        raise DecisionV1Error("EXECUTION_V1_OPEN_NORMALIZED_SCHEMA_INVALID")
    view = frame.loc[:, ["ticker", "session_date", "open_price", "first_trade"]].copy()
    view["ticker"] = view["ticker"].map(_normalize_ticker)
    dates = pd.to_datetime(view["session_date"], errors="coerce")
    if dates.isna().any():
        raise DecisionV1Error("EXECUTION_V1_OPEN_NORMALIZED_DATE_INVALID")
    view["session_date"] = [
        _date(x, "EXECUTION_V1_OPEN_NORMALIZED_DATE_INVALID") for x in dates
    ]
    if not view["session_date"].eq(session_date).all():
        raise DecisionV1Error("EXECUTION_V1_OPEN_NORMALIZED_DATE_MISMATCH")
    if view.duplicated(["ticker", "session_date"]).any():
        raise DecisionV1Error("EXECUTION_V1_OPEN_NORMALIZED_DUPLICATE_TICKER")
    view = view.sort_values(["ticker", "session_date"]).reset_index(drop=True)

    if len(view) != len(raw_frame) or not view[["ticker", "session_date"]].equals(
        raw_frame[["ticker", "session_date"]]
    ):
        raise DecisionV1Error("EXECUTION_V1_OPEN_NORMALIZED_KEYSET_MISMATCH")
    if not _numeric_series_equal(view["open_price"], raw_frame["open_price"]):
        raise DecisionV1Error("EXECUTION_V1_OPEN_NORMALIZED_OPENPRICE_MISMATCH")
    if not _numeric_series_equal(view["first_trade"], raw_frame["first_trade"]):
        raise DecisionV1Error(
            "EXECUTION_V1_OPEN_NORMALIZED_FIRSTTRADE_WITNESS_MISMATCH"
        )

    prices: dict[str, float] = {}
    for row in raw_frame.itertuples(index=False):
        price = _finite_positive(row.open_price)
        if price is not None:
            prices[row.ticker] = price

    positive_count = len(prices)
    unavailable_count = len(raw_frame) - positive_count
    try:
        declared_positive = int(payload.get("positive_openprice_count"))
        declared_unavailable = int(payload.get("unavailable_openprice_count"))
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(
            "EXECUTION_V1_OPEN_MANIFEST_AVAILABILITY_COUNT_INVALID"
        ) from exc
    if (
        declared_positive != positive_count
        or declared_unavailable != unavailable_count
    ):
        raise DecisionV1Error(
            "EXECUTION_V1_OPEN_MANIFEST_AVAILABILITY_COUNT_MISMATCH"
        )

    return VerifiedOpenExecutionInputs(
        session_date=session_date,
        raw_open_prices=prices,
        available_tickers=frozenset(prices),
        ohlcv_artifact_path=normalized_path,
        ohlcv_artifact_sha256=actual_normalized_sha,
        _verification_token=_OPEN_INPUT_TOKEN,
        manifest_path=manifest,
        manifest_sha256=_sha256(manifest),
        raw_source_path=raw_path,
        raw_source_sha256=actual_raw_sha,
        authority=OFFICIAL_OPEN_AUTHORITY,
        upstream_path=OFFICIAL_OPEN_UPSTREAM_PATH,
        field_semantics=OFFICIAL_OPEN_FIELD_SEMANTICS,
        fallback_policy=OFFICIAL_OPEN_FALLBACK_POLICY,
        transport=transport,
        transport_policy=OFFICIAL_OPEN_TRANSPORT_POLICY,
    )


def verify_corporate_action_attestation(
    *,
    attestation_path: str | Path,
    expected_from_session_date: str,
    expected_through_session_date: str,
    required_tickers: Sequence[str],
) -> VerifiedCorporateActionAttestation:
    path = Path(attestation_path).expanduser().resolve()
    if not path.is_file():
        raise DecisionV1Error(f"EXECUTION_V1_CA_ATTESTATION_MISSING:{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV1Error("EXECUTION_V1_CA_ATTESTATION_INVALID") from exc
    if not isinstance(payload, dict):
        raise DecisionV1Error("EXECUTION_V1_CA_ATTESTATION_NOT_OBJECT")
    if payload.get("schema_version") != "v4_x1_paper_ca_attestation_v1":
        raise DecisionV1Error("EXECUTION_V1_CA_ATTESTATION_SCHEMA_CHANGED")
    from_date = _date(
        payload.get("from_session_date"), "EXECUTION_V1_CA_FROM_DATE_INVALID"
    )
    through_date = _date(
        payload.get("through_session_date"), "EXECUTION_V1_CA_THROUGH_DATE_INVALID"
    )
    if from_date != _date(
        expected_from_session_date, "EXECUTION_V1_CA_EXPECTED_FROM_INVALID"
    ):
        raise DecisionV1Error("EXECUTION_V1_CA_FROM_DATE_MISMATCH")
    if through_date != _date(
        expected_through_session_date, "EXECUTION_V1_CA_EXPECTED_THROUGH_INVALID"
    ):
        raise DecisionV1Error("EXECUTION_V1_CA_THROUGH_DATE_MISMATCH")
    status = str(payload.get("status") or "")
    if status != "NO_RELEVANT_EVENTS":
        raise DecisionV1Error(
            f"EXECUTION_V1_CA_RECONCILIATION_REQUIRED:{status or 'UNKNOWN'}"
        )
    rows = payload.get("evidence_rows")
    if not isinstance(rows, list):
        raise DecisionV1Error("EXECUTION_V1_CA_EVIDENCE_ROWS_MISSING")
    covered: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise DecisionV1Error("EXECUTION_V1_CA_EVIDENCE_ROW_INVALID")
        ticker = _normalize_ticker(row.get("ticker"))
        if row.get("status") != "NO_RELEVANT_EVENT":
            raise DecisionV1Error(f"EXECUTION_V1_CA_RELEVANT_EVENT:{ticker}")
        covered.add(ticker)
    required = {_normalize_ticker(x) for x in required_tickers}
    if not required.issubset(covered):
        raise DecisionV1Error(
            f"EXECUTION_V1_CA_COVERAGE_INCOMPLETE:{sorted(required-covered)}"
        )

    raw_source_path = Path(str(payload.get("source_path") or ""))
    if not raw_source_path.is_absolute():
        raw_source_path = (path.parent / raw_source_path).resolve()
    if not raw_source_path.is_file():
        raise DecisionV1Error("EXECUTION_V1_CA_SOURCE_ARTIFACT_MISSING")
    declared_source_sha = str(payload.get("source_sha256") or "")
    if not _SHA256_RE.fullmatch(declared_source_sha):
        raise DecisionV1Error("EXECUTION_V1_CA_SOURCE_SHA_INVALID")
    actual_source_sha = _sha256(raw_source_path)
    if actual_source_sha != declared_source_sha:
        raise DecisionV1Error("EXECUTION_V1_CA_SOURCE_SHA_MISMATCH")

    return VerifiedCorporateActionAttestation(
        from_session_date=from_date,
        through_session_date=through_date,
        covered_tickers=frozenset(covered),
        status=status,
        attestation_path=path,
        attestation_sha256=_sha256(path),
        source_path=raw_source_path,
        source_sha256=actual_source_sha,
        _verification_token=_CA_ATTESTATION_TOKEN,
    )
