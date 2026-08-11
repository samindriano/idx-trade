from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
import requests

from .provenance import sha256_file
from .providers.yahoo import download_daily
from .security_master import normalise_ticker


DEFAULT_SAMPLE_SEED = 20260810
DEFAULT_SAMPLE_SIZE = 50
DEFAULT_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
DEFAULT_ZAPI_ENDPOINT = "https://api.zpi.web.id/v1/finance:idx/stock-summary"
PREFERRED_SAMPLE_TICKERS = ("FREN", "MASA", "MFIN", "BBCA", "BBRI", "AADI", "ALDO", "BREN")
SAMPLE_ROLE_ORDER = (
    "KNOWN_EXISTING_OPEN",
    "MISSING_OPEN_WILDAN_ROW",
    "MISSING_OPEN_WILDAN_NO_ROW",
)
AUDIT_COLUMNS = (
    "sample_id",
    "sample_role",
    "ticker",
    "date",
    "panel_open",
    "panel_high",
    "panel_low",
    "panel_close",
    "wildan_diagnostic",
    "edge_case_tags",
)
PROVIDER_COLUMNS = (
    "ticker",
    "date",
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
    "first_trade",
    "vendor_adj_close",
    "dividends",
    "stock_splits",
    "explicit_split_event",
    "explicit_dividend_event",
    "source_ref",
)


def _empty_provider_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=list(PROVIDER_COLUMNS))


def _stable_rank(seed: int, ticker: object, date: object, role: object = "") -> str:
    value = f"{int(seed)}|{normalise_ticker(ticker)}|{pd.Timestamp(date).date().isoformat()}|{role}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalise_date(value: object) -> pd.Timestamp:
    return pd.Timestamp(value).tz_localize(None).normalize()


def redact_secrets(value: object, secrets: Iterable[str] = ()) -> object:
    """Redact explicit secrets and common API-key/bearer forms recursively."""

    explicit = tuple(str(secret) for secret in secrets if secret)
    patterns = (
        re.compile(r"\bzpi_[A-Za-z0-9_-]+\b"),
        re.compile(r"(?i)(bearer\s+)[^\s,;]+"),
        re.compile(r"(?i)(x-api-key\s*[:=]\s*)[^\s,;]+"),
        re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+"),
    )

    def clean_string(text: str) -> str:
        cleaned = text
        for secret in explicit:
            cleaned = cleaned.replace(secret, "[REDACTED]")
        for pattern in patterns:
            if pattern.pattern.startswith("\\b"):
                cleaned = pattern.sub("[REDACTED]", cleaned)
            else:
                cleaned = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", cleaned)
        return cleaned

    if isinstance(value, str):
        return clean_string(value)
    if isinstance(value, Mapping):
        return {str(key): redact_secrets(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item, secrets) for item in value)
    return value


def _prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", "open", "high", "low", "close"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Panel columns missing: {sorted(missing)}")
    data = panel.copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if data["date"].isna().any() or data.duplicated(["ticker", "date"]).any():
        raise ValueError("Panel must contain unique valid ticker/date rows")
    for column in ("open", "high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    return data


def _read_optional_csv(path: str | Path | None, parse_dates: Iterable[str] = ()) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    file = Path(path)
    if not file.is_file():
        return pd.DataFrame()
    return pd.read_csv(file, parse_dates=list(parse_dates))


def _edge_tags(
    candidates: pd.DataFrame,
    *,
    security_master: pd.DataFrame | None = None,
    corporate_actions: pd.DataFrame | None = None,
    tradability_intervals: pd.DataFrame | None = None,
) -> pd.Series:
    result = pd.Series("", index=candidates.index, dtype="object")

    def append_tag(mask: pd.Series, tag: str) -> None:
        nonlocal result
        mask = mask.reindex(result.index, fill_value=False).fillna(False)
        result.loc[mask] = result.loc[mask].map(
            lambda value: "|".join(sorted(set(filter(None, [*str(value).split("|"), tag]))))
        )

    def key_membership(events: pd.DataFrame) -> pd.Series:
        if events.empty:
            return pd.Series(False, index=candidates.index)
        keys = pd.MultiIndex.from_frame(candidates[["ticker", "date"]])
        event_keys = pd.MultiIndex.from_frame(events[["ticker", "date"]].drop_duplicates())
        return pd.Series(keys.isin(event_keys), index=candidates.index)

    if security_master is not None and not security_master.empty and {"ticker", "listed_from"}.issubset(
        security_master.columns
    ):
        master = security_master[["ticker", "listed_from"]].copy()
        master["ticker"] = master["ticker"].map(normalise_ticker)
        master["listed_from"] = pd.to_datetime(master["listed_from"], errors="coerce").dt.normalize()
        append_tag(key_membership(master.rename(columns={"listed_from": "date"}).dropna()), "NEW_LISTING")
    if corporate_actions is not None and not corporate_actions.empty and {"ticker", "effective_date"}.issubset(
        corporate_actions.columns
    ):
        actions = corporate_actions[["ticker", "effective_date"]].copy()
        actions["ticker"] = actions["ticker"].map(normalise_ticker)
        actions["effective_date"] = pd.to_datetime(actions["effective_date"], errors="coerce").dt.normalize()
        action_events = pd.concat(
            [
                actions.rename(columns={"effective_date": "date"}),
                actions.assign(effective_date=actions["effective_date"] - pd.Timedelta(days=1)).rename(
                    columns={"effective_date": "date"}
                ),
                actions.assign(effective_date=actions["effective_date"] + pd.Timedelta(days=1)).rename(
                    columns={"effective_date": "date"}
                ),
            ],
            ignore_index=True,
        )
        append_tag(key_membership(action_events.dropna()), "CORPORATE_ACTION_ADJACENT")
    if tradability_intervals is not None and not tradability_intervals.empty and {
        "ticker",
        "effective_from",
        "effective_to",
    }.issubset(tradability_intervals.columns):
        intervals = tradability_intervals[["ticker", "effective_from", "effective_to"]].copy()
        intervals["ticker"] = intervals["ticker"].map(normalise_ticker)
        for column in ("effective_from", "effective_to"):
            intervals[column] = pd.to_datetime(intervals[column], errors="coerce").dt.normalize()
        boundary_events: list[pd.DataFrame] = []
        for column in ("effective_from", "effective_to"):
            base = intervals[["ticker", column]].rename(columns={column: "date"}).dropna()
            boundary_events.extend(
                [
                    base,
                    base.assign(date=base["date"] - pd.Timedelta(days=1)),
                    base.assign(date=base["date"] + pd.Timedelta(days=1)),
                ]
            )
        append_tag(key_membership(pd.concat(boundary_events, ignore_index=True)), "SUSPENSION_RESUMPTION")
    return result


def build_audit_candidates(
    panel: pd.DataFrame,
    wildan_diagnostics: pd.DataFrame,
    *,
    security_master: pd.DataFrame | None = None,
    corporate_actions: pd.DataFrame | None = None,
    tradability_intervals: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the provider-outcome-independent candidate universe."""

    data = _prepare_panel(panel)
    diagnostics = wildan_diagnostics.copy()
    required = {"ticker", "date", "diagnostic"}
    missing = required - set(diagnostics.columns)
    if missing:
        raise ValueError(f"Wildan diagnostics columns missing: {sorted(missing)}")
    diagnostics["ticker"] = diagnostics["ticker"].map(normalise_ticker)
    diagnostics["date"] = pd.to_datetime(diagnostics["date"], errors="coerce").dt.normalize()
    diagnostics = diagnostics.dropna(subset=["ticker", "date"])
    diagnostics = diagnostics.drop_duplicates(["ticker", "date"], keep="last")
    data = data.merge(
        diagnostics[["ticker", "date", "diagnostic"]].rename(columns={"diagnostic": "wildan_diagnostic"}),
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    data["panel_open"] = data["open"]
    data["panel_high"] = data["high"]
    data["panel_low"] = data["low"]
    data["panel_close"] = data["close"]
    data["sample_role"] = "MISSING_OPEN_UNCLASSIFIED"
    data.loc[data["open"].gt(0), "sample_role"] = "KNOWN_EXISTING_OPEN"
    missing_open = data["open"].isna() | data["open"].le(0)
    had_wildan = missing_open & data["wildan_diagnostic"].ne("SECONDARY_ROW_UNAVAILABLE") & data["wildan_diagnostic"].notna()
    no_wildan = missing_open & data["wildan_diagnostic"].eq("SECONDARY_ROW_UNAVAILABLE")
    data.loc[had_wildan, "sample_role"] = "MISSING_OPEN_WILDAN_ROW"
    data.loc[no_wildan, "sample_role"] = "MISSING_OPEN_WILDAN_NO_ROW"
    data["edge_case_tags"] = _edge_tags(
        data,
        security_master=security_master,
        corporate_actions=corporate_actions,
        tradability_intervals=tradability_intervals,
    )
    if security_master is not None and not security_master.empty and "ticker" in security_master.columns:
        known_tickers = set(security_master["ticker"].map(normalise_ticker))
        missing_identity = ~data["ticker"].isin(known_tickers)
        data.loc[missing_identity, "edge_case_tags"] = data.loc[missing_identity, "edge_case_tags"].map(
            lambda value: "|".join(sorted(set(filter(None, [*str(value).split("|"), "IDENTITY_EDGE"]))))
        )
    return data


def _ranked_rows(data: pd.DataFrame, seed: int) -> pd.DataFrame:
    ranked = data.copy()
    ranked["_rank"] = [
        _stable_rank(seed, ticker, date, role)
        for ticker, date, role in zip(ranked["ticker"], ranked["date"], ranked["sample_role"])
    ]
    preferred = {ticker: index for index, ticker in enumerate(PREFERRED_SAMPLE_TICKERS)}
    ranked["_preferred"] = ranked["ticker"].map(preferred).fillna(len(preferred)).astype(int)
    return ranked.sort_values(["_preferred", "_rank", "ticker", "date"], kind="mergesort")


def select_audit_sample(
    candidates: pd.DataFrame,
    *,
    seed: int = DEFAULT_SAMPLE_SEED,
    target_size: int = DEFAULT_SAMPLE_SIZE,
    minimum_existing: int = 20,
    minimum_wildan_row: int = 20,
    minimum_wildan_no_row: int = 5,
) -> pd.DataFrame:
    """Select a fixed, hashed sample using only panel/Wildan/edge evidence."""

    required_columns = set(AUDIT_COLUMNS) - {"sample_id", "edge_case_tags"}
    missing = required_columns - set(candidates.columns)
    if missing:
        raise ValueError(f"Audit candidates missing: {sorted(missing)}")
    data = candidates.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    data = data.dropna(subset=["ticker", "date"]).drop_duplicates(["ticker", "date"], keep="last")
    ranked = _ranked_rows(data, seed)
    selected_keys: set[tuple[str, pd.Timestamp]] = set()

    def add_rows(pool: pd.DataFrame, count: int) -> None:
        for row in pool.itertuples(index=False):
            if len(selected_keys) >= target_size or count <= 0:
                break
            key = (normalise_ticker(row.ticker), pd.Timestamp(row.date).normalize())
            if key not in selected_keys:
                selected_keys.add(key)
                count -= 1

    # Preserve factual edge cases where the supplied evidence has one.
    for tag in ("NEW_LISTING", "CORPORATE_ACTION_ADJACENT", "SUSPENSION_RESUMPTION"):
        add_rows(ranked[ranked["edge_case_tags"].fillna("").str.contains(tag, regex=False)], 1)

    # Guarantee requested named securities where the immutable panel has them.
    for ticker in PREFERRED_SAMPLE_TICKERS:
        add_rows(ranked[ranked["ticker"].eq(ticker)], 1)

    quotas = (
        ("KNOWN_EXISTING_OPEN", minimum_existing),
        ("MISSING_OPEN_WILDAN_ROW", minimum_wildan_row),
        ("MISSING_OPEN_WILDAN_NO_ROW", minimum_wildan_no_row),
    )
    for role, minimum in quotas:
        current = sum(
            1
            for ticker, date in selected_keys
            if ((ranked["ticker"].eq(ticker)) & ranked["date"].eq(date) & ranked["sample_role"].eq(role)).any()
        )
        add_rows(ranked[ranked["sample_role"].eq(role)], max(0, minimum - current))

    add_rows(ranked, max(0, target_size - len(selected_keys)))
    selected = ranked[
        ranked.apply(lambda row: (row["ticker"], pd.Timestamp(row["date"]).normalize()) in selected_keys, axis=1)
    ].copy()
    role_order = {role: index for index, role in enumerate(SAMPLE_ROLE_ORDER)}
    selected["_role_order"] = selected["sample_role"].map(role_order).fillna(99)
    selected = selected.sort_values(["_role_order", "ticker", "date"], kind="mergesort").reset_index(drop=True)
    selected["sample_id"] = [f"T2-{index:03d}" for index in range(1, len(selected) + 1)]
    return selected[list(AUDIT_COLUMNS)]


def sample_manifest_sha256(sample: pd.DataFrame) -> str:
    data = sample[list(AUDIT_COLUMNS)].copy()
    data["date"] = pd.to_datetime(data["date"]).dt.strftime("%Y-%m-%d")
    payload = data.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _provider_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return _empty_provider_frame()
    data = frame.copy()
    if "ticker" not in data.columns:
        data["ticker"] = pd.NA
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    for column in PROVIDER_COLUMNS:
        if column not in data.columns:
            data[column] = pd.NA
    for column in ("raw_open", "raw_high", "raw_low", "raw_close", "raw_volume", "first_trade", "vendor_adj_close", "dividends", "stock_splits"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    return data[list(PROVIDER_COLUMNS)].copy()


def audit_provider_rows(sample: pd.DataFrame, provider_rows: pd.DataFrame, source: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the frozen admission contract without ever mutating the panel."""

    sample_data = sample.copy()
    sample_data["ticker"] = sample_data["ticker"].map(normalise_ticker)
    sample_data["date"] = pd.to_datetime(sample_data["date"]).dt.normalize()
    provider = _provider_frame(provider_rows)
    valid_provider = provider.dropna(subset=["ticker", "date"])
    duplicate_keys = int(valid_provider.duplicated(["ticker", "date"], keep=False).sum())
    grouped = {key: group for key, group in valid_provider.groupby(["ticker", "date"], sort=False)}
    rows: list[dict[str, Any]] = []
    for sample_row in sample_data.itertuples(index=False):
        key = (sample_row.ticker, sample_row.date)
        matches = grouped.get(key, pd.DataFrame())
        base = {
            "sample_id": sample_row.sample_id,
            "source": source,
            "ticker": sample_row.ticker,
            "date": sample_row.date,
            "sample_role": sample_row.sample_role,
            "panel_open": sample_row.panel_open,
            "panel_high": sample_row.panel_high,
            "panel_low": sample_row.panel_low,
            "panel_close": sample_row.panel_close,
            "provider_rows_for_key": int(len(matches)),
            "raw_open": np.nan,
            "raw_high": np.nan,
            "raw_low": np.nan,
            "raw_close": np.nan,
            "raw_volume": np.nan,
            "vendor_adj_close": np.nan,
            "dividends": np.nan,
            "stock_splits": np.nan,
            "source_ref": None,
            "hlc_exact": False,
            "known_open_exact": None,
            "admission_status": "REJECTED",
            "diagnostic": "NO_PROVIDER_ROW",
        }
        if matches.empty:
            rows.append(base)
            continue
        candidate = matches.iloc[-1]
        for column in ("raw_open", "raw_high", "raw_low", "raw_close", "raw_volume", "vendor_adj_close", "dividends", "stock_splits", "source_ref"):
            base[column] = candidate.get(column)
        if len(matches) > 1:
            base["diagnostic"] = "PROVIDER_DUPLICATE_KEY"
            rows.append(base)
            continue
        values = [_as_float(candidate[column]) for column in ("raw_high", "raw_low", "raw_close")]
        panel_values = [_as_float(sample_row.panel_high), _as_float(sample_row.panel_low), _as_float(sample_row.panel_close)]
        if not all(np.isfinite(value) and value > 0 for value in values):
            base["diagnostic"] = "RAW_HLC_INVALID"
            rows.append(base)
            continue
        base["hlc_exact"] = all(provider_value == panel_value for provider_value, panel_value in zip(values, panel_values))
        if sample_row.sample_role in {"KNOWN_EXISTING_OPEN", "KNOWN_CONTROL"}:
            provider_open = _as_float(candidate["raw_open"])
            base["known_open_exact"] = bool(np.isfinite(provider_open) and provider_open == _as_float(sample_row.panel_open))
            base["admission_status"] = "PRESERVED_EXISTING_OPEN"
            base["diagnostic"] = "EXISTING_OPEN_PRESERVED" if base["hlc_exact"] else "HLC_MISMATCH"
            rows.append(base)
            continue
        if not base["hlc_exact"]:
            for name, provider_value, panel_value in zip(("HIGH", "LOW", "CLOSE"), values, panel_values):
                if provider_value != panel_value:
                    base["diagnostic"] = f"HLC_MISMATCH_{name}"
                    break
            rows.append(base)
            continue
        provider_open = _as_float(candidate["raw_open"])
        if not np.isfinite(provider_open) or provider_open <= 0:
            base["diagnostic"] = "CANDIDATE_OPEN_INVALID"
            rows.append(base)
            continue
        if not _as_float(sample_row.panel_low) <= provider_open <= _as_float(sample_row.panel_high):
            base["diagnostic"] = "CANDIDATE_OPEN_OUTSIDE_CERTIFIED_RANGE"
            rows.append(base)
            continue
        base["admission_status"] = "ADMISSIBLE_OPEN_EVIDENCE"
        base["diagnostic"] = "FROZEN_CONTRACT_PASS"
        rows.append(base)

    audit = pd.DataFrame(rows)
    known = audit[audit["sample_role"].isin(["KNOWN_EXISTING_OPEN", "KNOWN_CONTROL"])]
    known_comparisons = int(known["known_open_exact"].notna().sum())
    known_exact = int(known["known_open_exact"].fillna(False).sum())
    returned = audit[audit["diagnostic"].ne("NO_PROVIDER_ROW")]
    hlc_comparisons = int(returned["hlc_exact"].notna().sum())
    hlc_exact = int(returned["hlc_exact"].fillna(False).sum())
    missing = audit[~audit["sample_role"].isin(["KNOWN_EXISTING_OPEN", "KNOWN_CONTROL"])]
    summary: dict[str, Any] = {
        "source": source,
        "sample_rows_requested": int(len(sample_data)),
        "provider_rows_returned": int(len(provider)),
        "exact_ticker_date_rows": int((audit["diagnostic"] != "NO_PROVIDER_ROW").sum()),
        "hlc_exact_count": hlc_exact,
        "hlc_comparison_rows": hlc_comparisons,
        "hlc_exact_rate": float(hlc_exact / hlc_comparisons) if hlc_comparisons else None,
        "known_open_sample_rows": int(len(known)),
        "known_open_comparison_rows": known_comparisons,
        "known_open_exact_count": known_exact,
        "known_open_exact_rate": float(known_exact / known_comparisons) if known_comparisons else None,
        "missing_open_candidates": int(len(missing)),
        "admissible_missing_open_rows": int(missing["admission_status"].eq("ADMISSIBLE_OPEN_EVIDENCE").sum()),
        "rejection_breakdown": {str(key): int(value) for key, value in audit["diagnostic"].value_counts().items()},
        "provider_duplicate_key_rows": duplicate_keys,
        "identity_date_anomalies": 0,
        "corporate_action_fields_present": bool(
            provider[["vendor_adj_close", "dividends", "stock_splits"]].notna().any().any()
        )
        if not provider.empty
        else False,
        "candidate_rows": audit,
    }
    return audit, summary


def classify_zapi_access_failure(status_code: int, body_text: str) -> str:
    lowered = str(body_text).casefold()
    if status_code in {402, 403} and any(token in lowered for token in ("plan", "upgrade", "minplan", "subscription", "credit")):
        return "PLAN_GATED"
    if status_code in {401, 403}:
        return "ACCESS_DENIED"
    if status_code == 404:
        return "REQUEST_ERROR"
    if status_code >= 500:
        return "REQUEST_ERROR"
    if status_code >= 400:
        return "ACCESS_DENIED"
    return "REQUEST_ERROR"


def _parse_zapi_response(payload: object, source_ref: str) -> tuple[pd.DataFrame, int]:
    records: object = payload.get("data", []) if isinstance(payload, dict) else []
    if isinstance(records, dict):
        records = records.get("data", [])
    if not isinstance(records, list):
        return _empty_provider_frame(), 0
    parsed: list[dict[str, Any]] = []
    invalid_identity_date = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        ticker = record.get("StockCode", record.get("Code", record.get("code")))
        raw_date = record.get("Date", record.get("date"))
        date = pd.to_datetime(raw_date, errors="coerce")
        if ticker is None or pd.isna(date):
            invalid_identity_date += 1
            continue
        parsed.append(
            {
                "ticker": normalise_ticker(ticker),
                "date": pd.Timestamp(date).tz_localize(None).normalize(),
                "raw_open": record.get("OpenPrice", record.get("open")),
                "raw_high": record.get("High", record.get("high")),
                "raw_low": record.get("Low", record.get("low")),
                "raw_close": record.get("Close", record.get("close")),
                "raw_volume": record.get("Volume", record.get("volume")),
                "first_trade": record.get("FirstTrade", record.get("first_trade")),
                "source_ref": source_ref,
            }
        )
    return _provider_frame(pd.DataFrame(parsed)), invalid_identity_date


def run_zapi_audit(
    sample: pd.DataFrame,
    *,
    api_key: str | None = None,
    endpoint: str = DEFAULT_ZAPI_ENDPOINT,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Run only per-sample Zapi requests, or fail closed when no key exists."""

    if not api_key:
        audit, summary = audit_provider_rows(sample, _empty_provider_frame(), "ZAPI_IDX")
        summary.update(
            {
                "access_status": "ZAPI_BLOCKED_CREDENTIAL_ABSENT",
                "credential_status": "ABSENT",
                "plan_status": "NOT_TESTED_CREDENTIAL_ABSENT",
                "requests_made": 0,
                "request_errors": [],
                "identity_date_anomalies": 0,
            }
        )
        return {"rows": _empty_provider_frame(), "audit": audit, "summary": summary}

    client = session or requests.Session()
    rows: list[pd.DataFrame] = []
    errors: list[str] = []
    requests_made = 0
    invalid_identity_date = 0
    access_status = "ACCESSIBLE"
    plan_status = "EMPIRICALLY_REACHED"
    for row in sample.sort_values(["ticker", "date"], kind="mergesort").itertuples(index=False):
        date_text = pd.Timestamp(row.date).strftime("%Y%m%d")
        source_ref = f"zapi://finance:idx/stock-summary?date={date_text}&code={row.ticker}"
        try:
            response = client.get(
                endpoint,
                params={"length": 1000, "start": 0, "date": date_text, "code": row.ticker},
                headers={"x-api-key": api_key},
                timeout=timeout,
            )
            requests_made += 1
            if response.status_code != 200:
                failure = classify_zapi_access_failure(response.status_code, getattr(response, "text", ""))
                access_status = failure
                if failure == "PLAN_GATED":
                    plan_status = "PLAN_GATED"
                elif failure == "ACCESS_DENIED":
                    plan_status = "ACCESS_DENIED"
                errors.append(f"HTTP_{response.status_code}:{failure}")
                if failure in {"PLAN_GATED", "ACCESS_DENIED"}:
                    break
                continue
            payload = response.json()
            parsed, invalid = _parse_zapi_response(payload, source_ref)
            invalid_identity_date += invalid
            if not parsed.empty:
                rows.append(parsed)
        except Exception as error:  # provider errors are recorded, not converted to evidence
            requests_made += 1
            errors.append(str(redact_secrets(str(error), (api_key,))))
            access_status = "REQUEST_ERROR"
    provider = _provider_frame(pd.concat(rows, ignore_index=True) if rows else _empty_provider_frame())
    audit, summary = audit_provider_rows(sample, provider, "ZAPI_IDX")
    summary.update(
        {
            "access_status": access_status,
            "credential_status": "PRESENT_NOT_RETAINED",
            "plan_status": plan_status,
            "requests_made": requests_made,
            "request_errors": errors,
            "identity_date_anomalies": invalid_identity_date,
            "endpoint": endpoint,
        }
    )
    return {"rows": provider, "audit": audit, "summary": summary}


def run_yahoo_audit(sample: pd.DataFrame) -> dict[str, Any]:
    """Fetch bounded per-ticker Yahoo raw OHLC evidence for the sample only."""

    frames: list[pd.DataFrame] = []
    errors: list[str] = []
    tickers = sorted(set(sample["ticker"].map(normalise_ticker)))
    for ticker in tickers:
        rows = sample[sample["ticker"].eq(ticker)]
        start = pd.Timestamp(rows["date"].min()).date()
        end = (pd.Timestamp(rows["date"].max()) + pd.Timedelta(days=1)).date()
        try:
            provider_log = io.StringIO()
            with redirect_stdout(provider_log), redirect_stderr(provider_log):
                result = download_daily([ticker], start=start, end=end, threads=False)
            logged = provider_log.getvalue().strip()
            if logged:
                errors.append(f"{ticker}:{redact_secrets(logged)}")
            frame = result.get(ticker, _empty_provider_frame())
            if not frame.empty:
                frame = frame.copy()
                frame["source_ref"] = f"yahoo://{ticker}.JK/raw?start={start.isoformat()}&end={end.isoformat()}"
                frames.append(_provider_frame(frame))
        except Exception as error:  # each ticker is independent in this bounded audit
            errors.append(f"{ticker}:{redact_secrets(str(error))}")
    provider = _provider_frame(pd.concat(frames, ignore_index=True) if frames else _empty_provider_frame())
    audit, summary = audit_provider_rows(sample, provider, "YAHOO_YFINANCE")
    summary.update(
        {
            "access_status": "YAHOO_YFINANCE_ATTEMPTED",
            "credential_status": "NOT_APPLICABLE",
            "plan_status": "PERSONAL_RESEARCH_ONLY_UNOFFICIAL",
            "requests_made": len(tickers),
            "request_tickers": tickers,
            "request_errors": errors,
            "raw_adjusted_separation": True,
        }
    )
    return {"rows": provider, "audit": audit, "summary": summary}


def _write_json(value: object, path: Path) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[column]):
            data[column] = data[column].dt.strftime("%Y-%m-%d")
    data.to_csv(path, index=False, lineterminator="\n")


def _serialise_source_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if key != "candidate_rows"}


def run_tier2_source_audit(
    *,
    panel_path: str | Path,
    wildan_diagnostics_path: str | Path,
    output_dir: str | Path,
    expected_panel_sha256: str = DEFAULT_PANEL_SHA256,
    security_master_path: str | Path | None = None,
    corporate_actions_path: str | Path | None = None,
    tradability_intervals_path: str | Path | None = None,
    zapi_endpoint: str = DEFAULT_ZAPI_ENDPOINT,
) -> dict[str, Any]:
    panel_file = Path(panel_path)
    diagnostics_file = Path(wildan_diagnostics_path)
    output = Path(output_dir)
    if not panel_file.is_file() or not diagnostics_file.is_file():
        raise FileNotFoundError("Tier-2 input artifact is missing")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty audit directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    panel_sha_before = sha256_file(panel_file)
    if panel_sha_before != expected_panel_sha256:
        raise RuntimeError(f"Immutable panel SHA mismatch before runtime: {panel_sha_before}")
    panel = pd.read_parquet(panel_file)
    diagnostics = pd.read_csv(diagnostics_file)
    security_master = _read_optional_csv(security_master_path, parse_dates=("listed_from", "listed_to"))
    actions = _read_optional_csv(corporate_actions_path, parse_dates=("effective_date", "listing_date"))
    intervals = _read_optional_csv(tradability_intervals_path, parse_dates=("effective_from", "effective_to"))
    candidates = build_audit_candidates(
        panel,
        diagnostics,
        security_master=security_master,
        corporate_actions=actions,
        tradability_intervals=intervals,
    )
    sample = select_audit_sample(candidates)
    sample_hash = sample_manifest_sha256(sample)
    _write_csv(sample, output / "audit_sample_manifest.csv")
    _write_json(
        {
            "seed": DEFAULT_SAMPLE_SEED,
            "target_size": DEFAULT_SAMPLE_SIZE,
            "sample_rows": int(len(sample)),
            "sample_sha256": sample_hash,
            "role_counts": {str(key): int(value) for key, value in sample["sample_role"].value_counts().items()},
            "edge_case_counts": {
                tag: int(sample["edge_case_tags"].fillna("").str.contains(tag, regex=False).sum())
                for tag in ("NEW_LISTING", "CORPORATE_ACTION_ADJACENT", "SUSPENSION_RESUMPTION", "IDENTITY_EDGE")
            },
        },
        output / "audit_sample_manifest.json",
    )

    api_key = os.environ.get("ZAPI_API_KEY") if "ZAPI_API_KEY" in os.environ else None
    zapi = run_zapi_audit(sample, api_key=api_key, endpoint=zapi_endpoint)
    yahoo = run_yahoo_audit(sample)
    for name, result in (("zapi", zapi), ("yahoo", yahoo)):
        _write_csv(result["rows"], output / f"{name}_candidate_rows.csv")
        _write_csv(result["audit"], output / f"{name}_row_audit.csv")
        result["summary"]["candidate_rows_artifact"] = f"{name}_candidate_rows.csv"
        result["summary"]["row_audit_artifact"] = f"{name}_row_audit.csv"
        result["summary"]["candidate_rows_sha256"] = sha256_file(output / f"{name}_candidate_rows.csv")
        result["summary"]["row_audit_sha256"] = sha256_file(output / f"{name}_row_audit.csv")
        _write_json(_serialise_source_summary(result["summary"]), output / f"{name}_summary.json")

    panel_sha_after = sha256_file(panel_file)
    if panel_sha_after != panel_sha_before:
        raise RuntimeError(f"Immutable panel changed during runtime: {panel_sha_after}")
    overall = {
        "status": "OPEN_BACKFILL_TIER2_SOURCE_AUDIT_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "panel_path": str(panel_file),
        "panel_sha256_before": panel_sha_before,
        "panel_sha256_after": panel_sha_after,
        "baseline_null_open_rows": int(panel["open"].isna().sum()),
        "execution_grade_promoted": False,
        "sample_rows": int(len(sample)),
        "sample_sha256": sample_hash,
        "sample_role_counts": {str(key): int(value) for key, value in sample["sample_role"].value_counts().items()},
        "sources": {
            "ZAPI_IDX": _serialise_source_summary(zapi["summary"]),
            "YAHOO_YFINANCE": _serialise_source_summary(yahoo["summary"]),
        },
        "prohibited_actions_not_performed": [
            "bulk_446843_row_backfill",
            "idx_website_scraping",
            "tradingview_or_investing_ingestion",
            "stage5_rerun",
            "ranking_v2_change",
            "execution_pnl_claim",
            "main_merge",
        ],
    }
    _write_json(overall, output / "audit_summary.json")
    files = sorted(path for path in output.iterdir() if path.is_file())
    manifest = {
        "runtime": "open_backfill_tier2_source_audit_v1_20260810",
        "files": {path.name: sha256_file(path) for path in files},
    }
    manifest_path = output / "artifact_manifest.json"
    _write_json(manifest, manifest_path)
    return {
        **overall,
        "output_dir": str(output),
        "artifact_hashes": manifest["files"],
        "artifact_manifest_sha256": sha256_file(manifest_path),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded Tier-2 historical Open source audit")
    parser.add_argument("--panel", required=True)
    parser.add_argument("--wildan-diagnostics", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-panel-sha256", default=DEFAULT_PANEL_SHA256)
    parser.add_argument("--security-master")
    parser.add_argument("--corporate-actions")
    parser.add_argument("--tradability-intervals")
    parser.add_argument("--zapi-endpoint", default=DEFAULT_ZAPI_ENDPOINT)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run_tier2_source_audit(
        panel_path=args.panel,
        wildan_diagnostics_path=args.wildan_diagnostics,
        output_dir=args.output_dir,
        expected_panel_sha256=args.expected_panel_sha256,
        security_master_path=args.security_master,
        corporate_actions_path=args.corporate_actions,
        tradability_intervals_path=args.tradability_intervals,
        zapi_endpoint=args.zapi_endpoint,
    )
    print(json.dumps(redact_secrets(result), ensure_ascii=False, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
