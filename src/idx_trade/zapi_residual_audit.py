from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import requests

from .provenance import sha256_file
from .security_master import normalise_ticker
from .tier2_open_audit import (
    DEFAULT_ZAPI_ENDPOINT,
    _empty_provider_frame,
    _parse_zapi_response,
    _prepare_panel,
    audit_provider_rows,
    classify_zapi_access_failure,
    redact_secrets,
)

DEFAULT_SEED = 20260811
DEFAULT_EXPECTED_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
DEFAULT_HLC_MISMATCH_ROWS = 120
DEFAULT_PROVIDER_GAP_ROWS = 80
DEFAULT_CONTROL_ROWS = 40
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 0.70
ERROR_OR_SYMBOL_CLASS = "PROVIDER_ERROR_OR_SYMBOL_RESOLUTION_FAILURE"
NO_PROVIDER_CLASS = "NO_PROVIDER_ROW"
NO_FACTOR_HLC_CLASS = "PROVIDER_HLC_MISMATCH_NO_VERIFIED_SPLIT_FACTOR"
INCOMPLETE_ACTION_CLASS = "CORPORATE_ACTION_ADJACENT_INCOMPLETE_OFFICIAL_EVIDENCE"
VERIFIED_FACTOR_FAILED_CLASS = "CORPORATE_ACTION_SCALE_MISMATCH_VERIFIED_FACTOR_FAILED"

SleepFn = Callable[[float], None]


def _normalise_audit(audit: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker",
        "date",
        "panel_open",
        "panel_high",
        "panel_low",
        "panel_close",
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "provider_row_present",
        "hlc_exact",
        "direct_admissible",
        "split_admissible",
        "split_factor",
        "split_factor_status",
        "split_reconstructed_hlc_exact",
    }
    missing = required - set(audit.columns)
    if missing:
        raise ValueError(f"Yahoo census audit columns missing: {sorted(missing)}")
    data = audit.copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if data["date"].isna().any() or data.duplicated(["ticker", "date"]).any():
        raise ValueError("Yahoo census audit must contain unique valid ticker/date rows")
    for column in (
        "panel_open",
        "panel_high",
        "panel_low",
        "panel_close",
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "split_factor",
    ):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    for column in (
        "provider_row_present",
        "hlc_exact",
        "direct_admissible",
        "split_admissible",
        "split_reconstructed_hlc_exact",
    ):
        data[column] = data[column].fillna(False).astype(bool)
    return data


def classify_residual_rows(audit: pd.DataFrame, provider_status: pd.DataFrame) -> pd.DataFrame:
    """Reproduce the accepted residual classes without changing census evidence."""

    data = _normalise_audit(audit)
    statuses = provider_status.copy()
    if not statuses.empty:
        if not {"ticker", "status"}.issubset(statuses.columns):
            raise ValueError("Provider status must contain ticker/status")
        statuses["ticker"] = statuses["ticker"].map(normalise_ticker)
    error_tickers = set(statuses.loc[statuses["status"].eq("ERROR"), "ticker"]) if not statuses.empty else set()

    known = data["panel_open"].notna() & data["panel_open"].gt(0)
    residual = (~known) & ~data["direct_admissible"] & ~data["split_admissible"]
    data["residual_problem_class"] = pd.NA

    provider_error = residual & data["ticker"].isin(error_tickers)
    data.loc[provider_error, "residual_problem_class"] = ERROR_OR_SYMBOL_CLASS

    no_provider = residual & ~provider_error & ~data["provider_row_present"]
    data.loc[no_provider, "residual_problem_class"] = NO_PROVIDER_CLASS

    incomplete_action = (
        residual
        & data["provider_row_present"]
        & data["split_factor_status"].eq("FACTOR_UNAVAILABLE_INCOMPLETE_OFFICIAL_ACTION")
    )
    data.loc[incomplete_action, "residual_problem_class"] = INCOMPLETE_ACTION_CLASS

    verified_factor_failed = (
        residual
        & data["provider_row_present"]
        & data["split_factor"].notna()
        & data["split_factor"].ne(1.0)
        & ~data["split_reconstructed_hlc_exact"]
        & data["residual_problem_class"].isna()
    )
    data.loc[verified_factor_failed, "residual_problem_class"] = VERIFIED_FACTOR_FAILED_CLASS

    no_factor_hlc = (
        residual
        & data["provider_row_present"]
        & ~data["hlc_exact"]
        & data["residual_problem_class"].isna()
    )
    data.loc[no_factor_hlc, "residual_problem_class"] = NO_FACTOR_HLC_CLASS

    unresolved_other = residual & data["residual_problem_class"].isna()
    data.loc[unresolved_other, "residual_problem_class"] = "UNRESOLVED_OTHER_FAIL_CLOSED"
    data["is_residual"] = residual
    return data


def _stable_rank(seed: int, role: str, ticker: object, date: object) -> str:
    payload = f"{int(seed)}|{role}|{normalise_ticker(ticker)}|{pd.Timestamp(date).date().isoformat()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _select_diverse(pool: pd.DataFrame, count: int, *, seed: int, role: str) -> pd.DataFrame:
    if count <= 0 or pool.empty:
        return pool.head(0).copy()
    ranked = pool.copy()
    ranked["_rank"] = [
        _stable_rank(seed, role, ticker, date)
        for ticker, date in zip(ranked["ticker"], ranked["date"])
    ]
    ranked["_year"] = pd.to_datetime(ranked["date"]).dt.year
    ranked = ranked.sort_values(["_rank", "ticker", "date"], kind="mergesort")
    chosen: list[int] = []
    used: set[int] = set()

    # Guarantee temporal representation before maximizing ticker diversity.
    for _, group in ranked.groupby("_year", sort=True):
        index = int(group.index[0])
        if index not in used and len(chosen) < count:
            chosen.append(index)
            used.add(index)

    seen_tickers = set(ranked.loc[chosen, "ticker"]) if chosen else set()
    for index, row in ranked.iterrows():
        if len(chosen) >= count:
            break
        if index in used or row["ticker"] in seen_tickers:
            continue
        chosen.append(int(index))
        used.add(int(index))
        seen_tickers.add(row["ticker"])

    for index in ranked.index:
        if len(chosen) >= count:
            break
        if int(index) in used:
            continue
        chosen.append(int(index))
        used.add(int(index))

    return ranked.loc[chosen].drop(columns=["_rank", "_year"]).copy()


def build_targeted_sample(
    audit: pd.DataFrame,
    provider_status: pd.DataFrame,
    *,
    seed: int = DEFAULT_SEED,
    hlc_mismatch_rows: int = DEFAULT_HLC_MISMATCH_ROWS,
    provider_gap_rows: int = DEFAULT_PROVIDER_GAP_ROWS,
    control_rows: int = DEFAULT_CONTROL_ROWS,
) -> pd.DataFrame:
    """Build a provider-outcome-independent targeted Source-2 audit sample."""

    data = classify_residual_rows(audit, provider_status)
    known = data["panel_open"].notna() & data["panel_open"].gt(0)
    control_pool = data[
        known
        & data["provider_row_present"]
        & data["hlc_exact"]
        & data.get("known_open_exact", pd.Series(False, index=data.index)).fillna(False).astype(bool)
    ].copy()
    mismatch_pool = data[data["residual_problem_class"].eq(NO_FACTOR_HLC_CLASS)].copy()
    gap_pool = data[
        data["residual_problem_class"].isin([NO_PROVIDER_CLASS, ERROR_OR_SYMBOL_CLASS])
    ].copy()

    selected_mismatch = _select_diverse(
        mismatch_pool, min(hlc_mismatch_rows, len(mismatch_pool)), seed=seed, role="RESIDUAL_HLC_MISMATCH"
    )

    # Provider-gap sample must include every ticker-level Yahoo error when available.
    selected_gap_parts: list[pd.DataFrame] = []
    error_pool = gap_pool[gap_pool["residual_problem_class"].eq(ERROR_OR_SYMBOL_CLASS)]
    for ticker in sorted(error_pool["ticker"].unique()):
        one = _select_diverse(error_pool[error_pool["ticker"].eq(ticker)], 1, seed=seed, role="RESIDUAL_PROVIDER_GAP")
        if not one.empty:
            selected_gap_parts.append(one)
    already = pd.concat(selected_gap_parts, ignore_index=False) if selected_gap_parts else gap_pool.head(0)
    remaining_gap = gap_pool.drop(index=already.index, errors="ignore")
    remaining_count = max(0, min(provider_gap_rows, len(gap_pool)) - len(already))
    if remaining_count:
        selected_gap_parts.append(
            _select_diverse(remaining_gap, remaining_count, seed=seed, role="RESIDUAL_PROVIDER_GAP")
        )
    selected_gap = pd.concat(selected_gap_parts, ignore_index=False) if selected_gap_parts else gap_pool.head(0)

    selected_control = _select_diverse(
        control_pool, min(control_rows, len(control_pool)), seed=seed, role="KNOWN_CONTROL"
    )

    parts: list[pd.DataFrame] = []
    for role, frame in (
        ("RESIDUAL_HLC_MISMATCH", selected_mismatch),
        ("RESIDUAL_PROVIDER_GAP", selected_gap),
        ("KNOWN_CONTROL", selected_control),
    ):
        if frame.empty:
            continue
        item = frame.copy()
        item["sample_role"] = role
        parts.append(item)
    sample = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if sample.empty:
        raise RuntimeError("Targeted Source-2 sample is empty")
    sample = sample.sort_values(["sample_role", "ticker", "date"], kind="mergesort").reset_index(drop=True)
    sample["sample_id"] = [f"Z2-{index:03d}" for index in range(1, len(sample) + 1)]
    sample["yahoo_raw_open"] = sample["raw_open"]
    sample["yahoo_raw_high"] = sample["raw_high"]
    sample["yahoo_raw_low"] = sample["raw_low"]
    sample["yahoo_raw_close"] = sample["raw_close"]
    keep = [
        "sample_id",
        "sample_role",
        "residual_problem_class",
        "ticker",
        "date",
        "panel_open",
        "panel_high",
        "panel_low",
        "panel_close",
        "yahoo_raw_open",
        "yahoo_raw_high",
        "yahoo_raw_low",
        "yahoo_raw_close",
    ]
    return sample[keep].copy()


def sample_manifest_sha256(sample: pd.DataFrame) -> str:
    data = sample.copy()
    data["date"] = pd.to_datetime(data["date"]).dt.strftime("%Y-%m-%d")
    return hashlib.sha256(data.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()


def fetch_zapi_date_grouped(
    sample: pd.DataFrame,
    *,
    api_key: str | None,
    endpoint: str = DEFAULT_ZAPI_ENDPOINT,
    session: requests.Session | None = None,
    timeout: int = 30,
    min_request_interval_seconds: float = DEFAULT_MIN_REQUEST_INTERVAL_SECONDS,
    sleep_fn: SleepFn = time.sleep,
) -> dict[str, Any]:
    """Fetch Zapi by unique sample date, bounded and rate-limit aware."""

    if not api_key:
        return {
            "rows": _empty_provider_frame(),
            "access_status": "ZAPI_BLOCKED_CREDENTIAL_ABSENT",
            "credential_status": "ABSENT",
            "plan_status": "NOT_TESTED_CREDENTIAL_ABSENT",
            "requests_made": 0,
            "retries": 0,
            "rate_limit_events": 0,
            "request_errors": [],
            "dates_requested": 0,
        }

    client = session or requests.Session()
    frames: list[pd.DataFrame] = []
    errors: list[str] = []
    requests_made = 0
    retries = 0
    rate_limit_events = 0
    access_status = "ACCESSIBLE"
    plan_status = "EMPIRICALLY_REACHED"
    dates = sorted(pd.to_datetime(sample["date"]).dt.normalize().unique())

    for date_value in dates:
        date = pd.Timestamp(date_value).normalize()
        date_text = date.strftime("%Y%m%d")
        requested_tickers = set(sample.loc[pd.to_datetime(sample["date"]).dt.normalize().eq(date), "ticker"])
        source_ref = f"zapi://finance:idx/stock-summary?date={date_text}&length=1000"
        response = None
        for attempt in range(1, 4):
            try:
                response = client.get(
                    endpoint,
                    params={"length": 1000, "start": 0, "date": date_text},
                    headers={"x-api-key": api_key},
                    timeout=timeout,
                )
                requests_made += 1
            except Exception as error:
                errors.append(str(redact_secrets(f"{date_text}:{type(error).__name__}: {error}", (api_key,))))
                access_status = "REQUEST_ERROR"
                response = None
                if attempt < 3:
                    retries += 1
                    sleep_fn(max(1.0, min_request_interval_seconds))
                    continue
                break

            if response.status_code == 429:
                rate_limit_events += 1
                if attempt < 3:
                    retries += 1
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = max(float(retry_after), 1.0) if retry_after is not None else 2.0 * attempt
                    except ValueError:
                        delay = 2.0 * attempt
                    sleep_fn(delay)
                    continue
                errors.append(f"{date_text}:HTTP_429:RATE_LIMITED")
                access_status = "RATE_LIMITED"
                response = None
                break

            if response.status_code != 200:
                failure = classify_zapi_access_failure(response.status_code, getattr(response, "text", ""))
                errors.append(f"{date_text}:HTTP_{response.status_code}:{failure}")
                access_status = failure
                if failure == "PLAN_GATED":
                    plan_status = "PLAN_GATED"
                elif failure == "ACCESS_DENIED":
                    plan_status = "ACCESS_DENIED"
                response = None
                break
            break

        if response is None:
            if access_status in {"PLAN_GATED", "ACCESS_DENIED"}:
                break
            continue
        try:
            payload = response.json()
        except Exception as error:
            errors.append(str(redact_secrets(f"{date_text}:JSON_ERROR:{error}", (api_key,))))
            access_status = "REQUEST_ERROR"
            continue
        parsed, _ = _parse_zapi_response(payload, source_ref)
        if not parsed.empty:
            parsed = parsed[parsed["ticker"].isin(requested_tickers)].copy()
            if not parsed.empty:
                frames.append(parsed)
        if min_request_interval_seconds > 0:
            sleep_fn(min_request_interval_seconds)

    provider = pd.concat(frames, ignore_index=True) if frames else _empty_provider_frame()
    return {
        "rows": provider,
        "access_status": access_status,
        "credential_status": "PRESENT_NOT_RETAINED",
        "plan_status": plan_status,
        "requests_made": requests_made,
        "retries": retries,
        "rate_limit_events": rate_limit_events,
        "request_errors": errors,
        "dates_requested": len(dates),
    }


def build_arbitration(sample: pd.DataFrame, zapi_audit: pd.DataFrame) -> pd.DataFrame:
    data = zapi_audit.merge(
        sample[
            [
                "sample_id",
                "residual_problem_class",
                "yahoo_raw_open",
                "yahoo_raw_high",
                "yahoo_raw_low",
                "yahoo_raw_close",
            ]
        ],
        on="sample_id",
        how="left",
        validate="one_to_one",
    )
    for column in (
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "yahoo_raw_open",
        "yahoo_raw_high",
        "yahoo_raw_low",
        "yahoo_raw_close",
    ):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["zapi_hlc_matches_yahoo"] = (
        data[["raw_high", "raw_low", "raw_close"]].notna().all(axis=1)
        & data[["yahoo_raw_high", "yahoo_raw_low", "yahoo_raw_close"]].notna().all(axis=1)
        & data["raw_high"].eq(data["yahoo_raw_high"])
        & data["raw_low"].eq(data["yahoo_raw_low"])
        & data["raw_close"].eq(data["yahoo_raw_close"])
    )
    classification: list[str] = []
    for row in data.itertuples(index=False):
        if row.sample_role == "KNOWN_CONTROL":
            if row.diagnostic == "NO_PROVIDER_ROW":
                classification.append("CONTROL_ZAPI_NO_ROW")
            elif (
                bool(row.hlc_exact)
                and pd.notna(row.known_open_exact)
                and bool(row.known_open_exact)
            ):
                classification.append("CONTROL_PANEL_HLC_OPEN_EXACT")
            elif bool(row.hlc_exact):
                classification.append("CONTROL_PANEL_HLC_ONLY")
            else:
                classification.append("CONTROL_DISAGREEMENT")
            continue
        if row.sample_role == "RESIDUAL_PROVIDER_GAP":
            if row.admission_status == "ADMISSIBLE_OPEN_EVIDENCE":
                classification.append("SOURCE2_RECOVERY_CANDIDATE")
            elif row.diagnostic == "NO_PROVIDER_ROW":
                classification.append("SOURCE2_NO_ROW")
            elif bool(row.hlc_exact):
                classification.append("SOURCE2_PANEL_HLC_MATCH_OPEN_REJECTED")
            else:
                classification.append("SOURCE2_HLC_DISAGREEMENT")
            continue
        if row.sample_role == "RESIDUAL_HLC_MISMATCH":
            if bool(row.hlc_exact):
                classification.append("SOURCE2_SUPPORTS_CERTIFIED_PANEL")
            elif bool(row.zapi_hlc_matches_yahoo):
                classification.append("SOURCE2_SUPPORTS_YAHOO")
            elif row.diagnostic == "NO_PROVIDER_ROW":
                classification.append("SOURCE2_NO_ROW")
            else:
                classification.append("THREE_WAY_DISAGREEMENT")
            continue
        classification.append("UNCLASSIFIED")
    data["arbitration_class"] = classification
    return data


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[column]):
            data[column] = data[column].dt.strftime("%Y-%m-%d")
    data.to_csv(path, index=False, lineterminator="\n")


def _write_json(value: object, path: Path) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _write_artifact_manifest(output: Path) -> str:
    summary_name = "zapi_targeted_summary.json"
    manifest_name = "artifact_manifest.json"
    artifact_files = sorted(
        path
        for path in output.iterdir()
        if path.is_file() and path.name not in {summary_name, manifest_name}
    )
    manifest = {
        "runtime": "zapi_targeted_residual_audit_v1_20260811",
        "files": {path.name: sha256_file(path) for path in artifact_files},
        "execution_grade_promoted": False,
    }
    manifest_path = output / manifest_name
    _write_json(manifest, manifest_path)
    return sha256_file(manifest_path)


def run_zapi_residual_audit(
    *,
    panel_path: str | Path,
    yahoo_census_audit_path: str | Path,
    provider_status_path: str | Path,
    output_dir: str | Path,
    expected_panel_sha256: str = DEFAULT_EXPECTED_PANEL_SHA256,
    zapi_endpoint: str = DEFAULT_ZAPI_ENDPOINT,
) -> dict[str, Any]:
    panel_file = Path(panel_path)
    audit_file = Path(yahoo_census_audit_path)
    status_file = Path(provider_status_path)
    output = Path(output_dir)
    if not panel_file.is_file() or not audit_file.is_file() or not status_file.is_file():
        raise FileNotFoundError("panel, Yahoo census audit, and provider status inputs are required")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty audit directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    panel_sha_before = sha256_file(panel_file)
    if panel_sha_before != expected_panel_sha256:
        raise RuntimeError(f"Immutable panel SHA mismatch before runtime: {panel_sha_before}")
    panel = _prepare_panel(pd.read_parquet(panel_file))
    census_audit = pd.read_parquet(audit_file)
    provider_status = pd.read_csv(status_file)
    if len(census_audit) != len(panel):
        raise RuntimeError("Yahoo census audit row count does not match immutable panel")

    classified = classify_residual_rows(census_audit, provider_status)
    sample = build_targeted_sample(classified, provider_status)
    sample_hash = sample_manifest_sha256(sample)
    _write_csv(sample, output / "zapi_targeted_sample_manifest.csv")
    _write_json(
        {
            "seed": DEFAULT_SEED,
            "sample_sha256": sample_hash,
            "sample_rows": int(len(sample)),
            "role_counts": {str(k): int(v) for k, v in sample["sample_role"].value_counts().items()},
            "unique_tickers": int(sample["ticker"].nunique()),
            "unique_dates": int(pd.to_datetime(sample["date"]).nunique()),
        },
        output / "zapi_targeted_sample_manifest.json",
    )

    api_key = os.environ.get("ZAPI_API_KEY") if "ZAPI_API_KEY" in os.environ else None
    fetched = fetch_zapi_date_grouped(sample, api_key=api_key, endpoint=zapi_endpoint)
    zapi_rows = fetched["rows"]
    audit_input = sample[
        [
            "sample_id",
            "sample_role",
            "ticker",
            "date",
            "panel_open",
            "panel_high",
            "panel_low",
            "panel_close",
        ]
    ].copy()
    zapi_row_audit, zapi_summary = audit_provider_rows(audit_input, zapi_rows, "ZAPI_IDX_TARGETED")
    arbitration = build_arbitration(sample, zapi_row_audit)

    _write_csv(zapi_rows, output / "zapi_candidate_rows.csv")
    _write_csv(zapi_row_audit, output / "zapi_row_audit.csv")
    _write_csv(arbitration, output / "zapi_arbitration.csv")

    panel_sha_after = sha256_file(panel_file)
    if panel_sha_after != panel_sha_before:
        raise RuntimeError(f"Immutable panel changed during runtime: {panel_sha_after}")

    summary = {
        "status": "ZAPI_TARGETED_RESIDUAL_AUDIT_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "panel_sha256_before": panel_sha_before,
        "panel_sha256_after": panel_sha_after,
        "sample_sha256": sample_hash,
        "sample_rows": int(len(sample)),
        "sample_role_counts": {str(k): int(v) for k, v in sample["sample_role"].value_counts().items()},
        "zapi_access": {k: v for k, v in fetched.items() if k != "rows"},
        "zapi_quality": {k: v for k, v in zapi_summary.items() if k != "candidate_rows"},
        "arbitration_counts": {str(k): int(v) for k, v in arbitration["arbitration_class"].value_counts().items()},
        "execution_grade_promoted": False,
        "bulk_backfill_authorized": False,
        "corporate_action_repair_performed": False,
    }
    summary_path = output / "zapi_targeted_summary.json"
    _write_json(summary, summary_path)
    summary["artifact_manifest_sha256"] = _write_artifact_manifest(output)
    _write_json(summary, summary_path)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Targeted Zapi audit for unresolved Yahoo historical Open rows")
    parser.add_argument("--panel", required=True)
    parser.add_argument("--yahoo-census-audit", required=True)
    parser.add_argument("--provider-status", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-panel-sha256", default=DEFAULT_EXPECTED_PANEL_SHA256)
    parser.add_argument("--zapi-endpoint", default=DEFAULT_ZAPI_ENDPOINT)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run_zapi_residual_audit(
        panel_path=args.panel,
        yahoo_census_audit_path=args.yahoo_census_audit,
        provider_status_path=args.provider_status,
        output_dir=args.output_dir,
        expected_panel_sha256=args.expected_panel_sha256,
        zapi_endpoint=args.zapi_endpoint,
    )
    print(json.dumps(redact_secrets(result), ensure_ascii=False, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
