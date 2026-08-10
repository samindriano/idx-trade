from __future__ import annotations

import argparse
import io
import json
import math
import time
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from .data import raw_price_semantics_verified
from .provenance import sha256_file
from .providers.yahoo import download_daily
from .security_master import normalise_ticker
from .tier2_open_audit import _prepare_panel, redact_secrets
from .yahoo_semantics_audit import _normalise_actions


DEFAULT_EXPECTED_PANEL_SHA256 = (
    "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
)
DEFAULT_START = "2021-04-29"
DEFAULT_END_INCLUSIVE = "2026-07-31"
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 2.0
CACHE_SEMANTICS = "YAHOO_YFINANCE_RAW_OHLC_AUTO_ADJUST_FALSE_ACTIONS_TRUE_V1"

DownloadFn = Callable[[list[str], object, object | None, bool], dict[str, pd.DataFrame]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def _csv_write(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def _parquet_write(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)


def _safe_version(package: str) -> str | None:
    try:
        return importlib_metadata.version(package)
    except importlib_metadata.PackageNotFoundError:
        return None


def _cache_identity(ticker: str, start: object, end_inclusive: object) -> dict[str, Any]:
    return {
        "ticker": normalise_ticker(ticker),
        "start": pd.Timestamp(start).date().isoformat(),
        "end_inclusive": pd.Timestamp(end_inclusive).date().isoformat(),
        "semantics": CACHE_SEMANTICS,
        "yfinance_version": _safe_version("yfinance"),
    }


def _cache_paths(cache_root: Path, ticker: str) -> tuple[Path, Path]:
    clean = normalise_ticker(ticker)
    return cache_root / f"{clean}.parquet", cache_root / f"{clean}.json"


def _normalise_provider_frame(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    data = frame.copy()
    data["ticker"] = normalise_ticker(ticker)
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    data = data.dropna(subset=["date"]).sort_values("date", kind="mergesort")
    data = data.drop_duplicates(["ticker", "date"], keep="last").reset_index(drop=True)
    return data


def _load_valid_cache(
    cache_root: Path,
    ticker: str,
    start: object,
    end_inclusive: object,
) -> dict[str, Any] | None:
    parquet_path, meta_path = _cache_paths(cache_root, ticker)
    if not meta_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if meta.get("identity") != _cache_identity(ticker, start, end_inclusive):
        return None
    status = meta.get("status")
    if status == "SUCCESS":
        if not parquet_path.is_file() or meta.get("parquet_sha256") != sha256_file(parquet_path):
            return None
        try:
            frame = pd.read_parquet(parquet_path)
        except Exception:
            return None
        frame = _normalise_provider_frame(frame, ticker)
        if frame.empty or not raw_price_semantics_verified(frame):
            return None
        return {
            "ticker": normalise_ticker(ticker),
            "status": "SUCCESS",
            "frame": frame,
            "cache_hit": True,
            "network_attempts": 0,
            "retries": 0,
            "metadata": meta,
        }
    if status == "NO_DATA_COMPLETE":
        return {
            "ticker": normalise_ticker(ticker),
            "status": status,
            "frame": pd.DataFrame(),
            "cache_hit": True,
            "network_attempts": 0,
            "retries": 0,
            "metadata": meta,
        }
    return None


def fetch_ticker_cached(
    ticker: str,
    *,
    start: object,
    end_inclusive: object,
    cache_root: str | Path,
    download_fn: DownloadFn = download_daily,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Fetch one ticker with a resumable fail-closed raw cache.

    Only SUCCESS and a clean, log-free NO_DATA result are terminal cache states.
    Provider exceptions or error output remain retryable on the next run.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    cache_dir = Path(cache_root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = _load_valid_cache(cache_dir, ticker, start, end_inclusive)
    if cached is not None:
        return cached

    clean = normalise_ticker(ticker)
    parquet_path, meta_path = _cache_paths(cache_dir, clean)
    end_exclusive = (pd.Timestamp(end_inclusive).normalize() + pd.Timedelta(days=1)).date()
    errors: list[str] = []
    logs: list[str] = []
    attempts = 0
    last_frame = pd.DataFrame()

    for attempt in range(1, max_attempts + 1):
        attempts += 1
        try:
            stream = io.StringIO()
            with redirect_stdout(stream), redirect_stderr(stream):
                result = download_fn(
                    [clean],
                    pd.Timestamp(start).date(),
                    end_exclusive,
                    False,
                )
            captured = str(redact_secrets(stream.getvalue().strip()))
            if captured:
                logs.append(captured)
            frame = _normalise_provider_frame(result.get(clean, pd.DataFrame()), clean)
            if not frame.empty:
                if not raw_price_semantics_verified(frame):
                    errors.append("RAW_PRICE_SEMANTICS_INVALID")
                else:
                    last_frame = frame
                    break
            elif not captured:
                last_frame = frame
                break
            else:
                errors.append("EMPTY_WITH_PROVIDER_DIAGNOSTIC")
        except Exception as error:
            errors.append(str(redact_secrets(f"{type(error).__name__}: {error}")))
        if attempt < max_attempts and backoff_seconds > 0:
            sleep_fn(backoff_seconds * (2 ** (attempt - 1)))

    identity = _cache_identity(clean, start, end_inclusive)
    retrieved_at = _utc_now()
    retries = max(0, attempts - 1)
    if not last_frame.empty and raw_price_semantics_verified(last_frame):
        _parquet_write(parquet_path, last_frame)
        meta = {
            "identity": identity,
            "status": "SUCCESS",
            "retrieved_at_utc": retrieved_at,
            "rows": int(len(last_frame)),
            "min_date": pd.Timestamp(last_frame["date"].min()).date().isoformat(),
            "max_date": pd.Timestamp(last_frame["date"].max()).date().isoformat(),
            "parquet_sha256": sha256_file(parquet_path),
            "network_attempts": attempts,
            "retries": retries,
            "provider_logs": logs,
            "provider_errors": errors,
        }
        _json_write(meta_path, meta)
        return {
            "ticker": clean,
            "status": "SUCCESS",
            "frame": last_frame,
            "cache_hit": False,
            "network_attempts": attempts,
            "retries": retries,
            "metadata": meta,
        }

    clean_no_data = not errors and not logs
    status = "NO_DATA_COMPLETE" if clean_no_data else "ERROR"
    meta = {
        "identity": identity,
        "status": status,
        "retrieved_at_utc": retrieved_at,
        "rows": 0,
        "parquet_sha256": None,
        "network_attempts": attempts,
        "retries": retries,
        "provider_logs": logs,
        "provider_errors": errors,
    }
    _json_write(meta_path, meta)
    return {
        "ticker": clean,
        "status": status,
        "frame": pd.DataFrame(),
        "cache_hit": False,
        "network_attempts": attempts,
        "retries": retries,
        "metadata": meta,
    }


def fetch_universe_cached(
    tickers: list[str],
    *,
    start: object,
    end_inclusive: object,
    cache_root: str | Path,
    download_fn: DownloadFn = download_daily,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Fetch the exact ticker universe serially for rate-limit safety."""

    rows: list[pd.DataFrame] = []
    statuses: list[dict[str, Any]] = []
    for ticker in sorted({normalise_ticker(value) for value in tickers}):
        result = fetch_ticker_cached(
            ticker,
            start=start,
            end_inclusive=end_inclusive,
            cache_root=cache_root,
            download_fn=download_fn,
            max_attempts=max_attempts,
            backoff_seconds=backoff_seconds,
            sleep_fn=sleep_fn,
        )
        meta = result["metadata"]
        statuses.append(
            {
                "ticker": ticker,
                "status": result["status"],
                "cache_hit": bool(result["cache_hit"]),
                "network_attempts": int(result["network_attempts"]),
                "retries": int(result["retries"]),
                "rows": int(meta.get("rows", 0)),
                "retrieved_at_utc": meta.get("retrieved_at_utc"),
                "parquet_sha256": meta.get("parquet_sha256"),
                "provider_errors": " | ".join(meta.get("provider_errors", [])),
                "provider_logs": " | ".join(meta.get("provider_logs", [])),
            }
        )
        frame = result["frame"]
        if not frame.empty:
            annotated = frame.copy()
            annotated["cache_ref"] = str(_cache_paths(Path(cache_root), ticker)[0])
            annotated["cache_sha256"] = meta.get("parquet_sha256")
            annotated["retrieved_at_utc"] = meta.get("retrieved_at_utc")
            rows.append(annotated)
    provider = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    status_frame = pd.DataFrame(statuses).sort_values("ticker", kind="mergesort").reset_index(drop=True)
    summary = {
        "tickers_attempted": int(len(status_frame)),
        "tickers_success": int(status_frame["status"].eq("SUCCESS").sum()),
        "tickers_no_data": int(status_frame["status"].eq("NO_DATA_COMPLETE").sum()),
        "tickers_error": int(status_frame["status"].eq("ERROR").sum()),
        "cache_hits": int(status_frame["cache_hit"].sum()),
        "network_attempts": int(status_frame["network_attempts"].sum()),
        "retries": int(status_frame["retries"].sum()),
        "provider_rows": int(len(provider)),
    }
    return provider, status_frame, summary


def _provider_for_merge(provider: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if provider.empty:
        return pd.DataFrame(columns=["ticker", "date"]), 0
    data = provider.copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    data = data.dropna(subset=["ticker", "date"])
    duplicate_mask = data.duplicated(["ticker", "date"], keep=False)
    duplicate_rows = int(duplicate_mask.sum())
    return data.loc[~duplicate_mask].copy(), duplicate_rows


def build_full_direct_audit(panel: pd.DataFrame, provider: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Vectorized frozen direct admission over every panel row."""

    base = _prepare_panel(panel).rename(
        columns={
            "open": "panel_open",
            "high": "panel_high",
            "low": "panel_low",
            "close": "panel_close",
        }
    )
    provider_valid, duplicate_rows = _provider_for_merge(provider)
    keep = [
        "ticker",
        "date",
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "raw_volume",
        "vendor_adj_close",
        "stock_splits",
        "dividends",
        "cache_ref",
        "cache_sha256",
        "retrieved_at_utc",
    ]
    for column in keep:
        if column not in provider_valid.columns:
            provider_valid[column] = pd.NA
    merged = base.merge(
        provider_valid[keep],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    has_provider = merged["_merge"].eq("both")
    known = merged["panel_open"].notna() & merged["panel_open"].gt(0)
    for column in ("raw_open", "raw_high", "raw_low", "raw_close"):
        merged[column] = pd.to_numeric(merged[column], errors="coerce")
    raw_hlc_valid = (
        merged[["raw_high", "raw_low", "raw_close"]].notna().all(axis=1)
        & merged[["raw_high", "raw_low", "raw_close"]].gt(0).all(axis=1)
    )
    merged["hlc_exact"] = (
        has_provider
        & raw_hlc_valid
        & merged["raw_high"].eq(merged["panel_high"])
        & merged["raw_low"].eq(merged["panel_low"])
        & merged["raw_close"].eq(merged["panel_close"])
    )
    merged["known_open_exact"] = pd.Series(pd.NA, index=merged.index, dtype="boolean")
    known_compare = known & has_provider & merged["raw_open"].notna()
    merged.loc[known_compare, "known_open_exact"] = merged.loc[known_compare, "raw_open"].eq(
        merged.loc[known_compare, "panel_open"]
    )
    open_valid = merged["raw_open"].notna() & merged["raw_open"].gt(0)
    open_in_range = open_valid & merged["raw_open"].ge(merged["panel_low"]) & merged["raw_open"].le(
        merged["panel_high"]
    )
    direct_admissible = (~known) & merged["hlc_exact"] & open_in_range
    merged["direct_admissible"] = direct_admissible
    merged["direct_candidate_open"] = np.where(direct_admissible, merged["raw_open"], np.nan)
    merged["direct_evidence_class"] = np.where(direct_admissible, "DIRECT_RAW_HLC_EXACT", pd.NA)
    diagnostic = pd.Series("NO_PROVIDER_ROW", index=merged.index, dtype="object")
    diagnostic.loc[has_provider] = "UNCLASSIFIED_PROVIDER_ROW"
    diagnostic.loc[has_provider & ~raw_hlc_valid] = "RAW_HLC_INVALID"
    mismatch_high = has_provider & raw_hlc_valid & ~merged["raw_high"].eq(merged["panel_high"])
    mismatch_low = has_provider & raw_hlc_valid & ~merged["raw_low"].eq(merged["panel_low"])
    mismatch_close = has_provider & raw_hlc_valid & ~merged["raw_close"].eq(merged["panel_close"])
    diagnostic.loc[mismatch_high] = "HLC_MISMATCH_HIGH"
    diagnostic.loc[~mismatch_high & mismatch_low] = "HLC_MISMATCH_LOW"
    diagnostic.loc[~mismatch_high & ~mismatch_low & mismatch_close] = "HLC_MISMATCH_CLOSE"
    diagnostic.loc[merged["hlc_exact"] & ~open_valid] = "CANDIDATE_OPEN_INVALID"
    diagnostic.loc[merged["hlc_exact"] & open_valid & ~open_in_range] = "CANDIDATE_OPEN_OUTSIDE_CERTIFIED_RANGE"
    diagnostic.loc[direct_admissible] = "DIRECT_FROZEN_CONTRACT_PASS"
    diagnostic.loc[known & merged["hlc_exact"] & merged["known_open_exact"].eq(True)] = "EXISTING_OPEN_PRESERVED_EXACT"
    diagnostic.loc[known & merged["hlc_exact"] & merged["known_open_exact"].eq(False)] = "EXISTING_OPEN_PRESERVED_OPEN_MISMATCH"
    merged["direct_diagnostic"] = diagnostic
    merged["provider_row_present"] = has_provider
    merged = merged.drop(columns=["_merge"])

    known_provider = known & has_provider
    known_hlc = known_provider & merged["hlc_exact"]
    summary = {
        "panel_rows": int(len(merged)),
        "provider_exact_ticker_date_rows": int(has_provider.sum()),
        "provider_exact_ticker_date_rate": float(has_provider.mean()) if len(merged) else None,
        "provider_duplicate_rows_excluded": duplicate_rows,
        "known_open_rows_total": int(known.sum()),
        "known_open_provider_rows": int(known_provider.sum()),
        "known_open_hlc_exact_count": int(known_hlc.sum()),
        "known_open_hlc_exact_rate_vs_provider": float(known_hlc.sum() / known_provider.sum()) if known_provider.any() else None,
        "known_open_comparison_rows": int(merged.loc[known_hlc, "known_open_exact"].notna().sum()),
        "known_open_exact_count": int(merged.loc[known_hlc, "known_open_exact"].fillna(False).sum()),
        "known_open_exact_rate_after_hlc_gate": float(
            merged.loc[known_hlc, "known_open_exact"].fillna(False).mean()
        )
        if known_hlc.any()
        else None,
        "missing_open_rows_total": int((~known).sum()),
        "direct_missing_open_accepted": int(direct_admissible.sum()),
    }
    return merged, summary


def _event_map(actions: pd.DataFrame) -> dict[str, list[tuple[pd.Timestamp, float | None]]]:
    data = _normalise_actions(actions)
    result: dict[str, list[tuple[pd.Timestamp, float | None]]] = {}
    for (ticker, date), group in data.groupby(["ticker", "effective_date"], sort=True):
        ratios = sorted({float(value) for value in group["ratio"].dropna() if float(value) > 0})
        ratio = ratios[0] if len(ratios) == 1 else None
        result.setdefault(ticker, []).append((pd.Timestamp(date).normalize(), ratio))
    return result


def _cumulative_factor_from_map(
    ticker: str,
    date: object,
    events: dict[str, list[tuple[pd.Timestamp, float | None]]],
) -> tuple[float | None, str]:
    future = [(event_date, ratio) for event_date, ratio in events.get(normalise_ticker(ticker), []) if event_date > pd.Timestamp(date).normalize()]
    if not future:
        return 1.0, "NO_FUTURE_SPLIT"
    if any(ratio is None for _, ratio in future):
        return None, "FACTOR_UNAVAILABLE_INCOMPLETE_OFFICIAL_ACTION"
    return float(math.prod(float(ratio) for _, ratio in future)), "OFFICIAL_CUMULATIVE_FACTOR"


def apply_verified_split_reconstruction(
    direct_audit: pd.DataFrame,
    actions: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Evaluate only direct H/L/C mismatches with independent official factors."""

    audit = direct_audit.copy()
    audit["split_factor"] = np.nan
    audit["split_factor_status"] = pd.NA
    audit["split_reconstructed_hlc_exact"] = False
    audit["split_reconstructed_open"] = np.nan
    audit["split_known_open_exact"] = pd.Series(pd.NA, index=audit.index, dtype="boolean")
    audit["split_admissible"] = False
    audit["split_diagnostic"] = "NOT_EVALUATED"
    events = _event_map(actions)
    candidates = audit["provider_row_present"] & ~audit["hlc_exact"]
    cache: dict[tuple[str, pd.Timestamp], tuple[float | None, str]] = {}
    for index in audit.index[candidates]:
        ticker = normalise_ticker(audit.at[index, "ticker"])
        date = pd.Timestamp(audit.at[index, "date"]).normalize()
        key = (ticker, date)
        factor, factor_status = cache.setdefault(key, _cumulative_factor_from_map(ticker, date, events))
        audit.at[index, "split_factor"] = factor
        audit.at[index, "split_factor_status"] = factor_status
        if factor is None or factor == 1.0:
            audit.at[index, "split_diagnostic"] = factor_status
            continue
        transformed = {
            field: float(audit.at[index, f"raw_{field}"]) * factor
            if pd.notna(audit.at[index, f"raw_{field}"])
            else np.nan
            for field in ("open", "high", "low", "close")
        }
        hlc_exact = all(
            np.isfinite(transformed[field])
            and transformed[field] == float(audit.at[index, f"panel_{field}"])
            for field in ("high", "low", "close")
        )
        audit.at[index, "split_reconstructed_hlc_exact"] = hlc_exact
        audit.at[index, "split_reconstructed_open"] = transformed["open"]
        if not hlc_exact:
            audit.at[index, "split_diagnostic"] = "SPLIT_SCALE_HLC_MISMATCH"
            continue
        open_valid = (
            np.isfinite(transformed["open"])
            and transformed["open"] > 0
            and float(audit.at[index, "panel_low"]) <= transformed["open"] <= float(audit.at[index, "panel_high"])
        )
        if not open_valid:
            audit.at[index, "split_diagnostic"] = "SPLIT_SCALE_OPEN_INVALID_OR_OUT_OF_RANGE"
            continue
        known = pd.notna(audit.at[index, "panel_open"]) and float(audit.at[index, "panel_open"]) > 0
        if known:
            exact = transformed["open"] == float(audit.at[index, "panel_open"])
            audit.at[index, "split_known_open_exact"] = exact
            audit.at[index, "split_diagnostic"] = (
                "SPLIT_SCALE_EXISTING_OPEN_PRESERVED_EXACT"
                if exact
                else "SPLIT_SCALE_EXISTING_OPEN_PRESERVED_OPEN_MISMATCH"
            )
        else:
            audit.at[index, "split_admissible"] = True
            audit.at[index, "split_diagnostic"] = "SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE"

    summary = {
        "direct_hlc_mismatch_rows_evaluated": int(candidates.sum()),
        "verified_factor_nonunit_rows": int((audit["split_factor"].notna() & audit["split_factor"].ne(1.0)).sum()),
        "reconstructed_hlc_exact_count": int(audit["split_reconstructed_hlc_exact"].sum()),
        "reconstructed_known_open_comparison_rows": int(audit["split_known_open_exact"].notna().sum()),
        "reconstructed_known_open_exact_count": int(audit["split_known_open_exact"].fillna(False).sum()),
        "reconstructed_missing_open_accepted": int(audit["split_admissible"].sum()),
    }
    return audit, summary


def build_derivative_candidate(audit: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Create a derivative candidate while preserving every existing Open."""

    data = audit.copy()
    known = data["panel_open"].notna() & data["panel_open"].gt(0)
    direct = (~known) & data["direct_admissible"]
    split = (~known) & ~direct & data["split_admissible"]
    candidate = data["panel_open"].copy()
    candidate.loc[direct] = data.loc[direct, "direct_candidate_open"]
    candidate.loc[split] = data.loc[split, "split_reconstructed_open"]
    derivative = pd.DataFrame(
        {
            "ticker": data["ticker"],
            "date": data["date"],
            "open": candidate,
            "high": data["panel_high"],
            "low": data["panel_low"],
            "close": data["panel_close"],
        }
    )
    if "volume" in data.columns:
        derivative["volume"] = data["volume"]
    provenance = pd.DataFrame(
        {
            "ticker": data["ticker"],
            "date": data["date"],
            "open_source": np.select(
                [known, direct, split],
                ["IMMUTABLE_PANEL", "YAHOO_YFINANCE", "YAHOO_YFINANCE"],
                default=None,
            ),
            "open_evidence_class": np.select(
                [known, direct, split],
                ["EXISTING_IMMUTABLE", "DIRECT_RAW_HLC_EXACT", "SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE"],
                default=None,
            ),
            "validation_status": np.select(
                [known, direct, split],
                ["PRESERVED", "ACCEPTED", "ACCEPTED"],
                default="UNRESOLVED",
            ),
            "source_cache_ref": data.get("cache_ref"),
            "source_raw_sha256": data.get("cache_sha256"),
            "retrieved_at_utc": data.get("retrieved_at_utc"),
            "split_factor": np.where(split, data["split_factor"], np.nan),
            "direct_diagnostic": data["direct_diagnostic"],
            "split_diagnostic": data["split_diagnostic"],
        }
    )
    if not derivative.loc[known, "open"].equals(data.loc[known, "panel_open"]):
        raise RuntimeError("Existing Open changed while building derivative")
    summary = {
        "direct_fills": int(direct.sum()),
        "split_fills": int(split.sum()),
        "total_fills": int((direct | split).sum()),
        "initial_null_open": int((~known).sum()),
        "final_null_open": int(derivative["open"].isna().sum()),
    }
    return derivative, provenance, summary


def _date_stratum(series: pd.Series) -> pd.Series:
    dates = pd.to_datetime(series).dt.normalize()
    first, last = dates.min(), dates.max()
    if pd.isna(first) or pd.isna(last) or first == last:
        return pd.Series("ALL", index=series.index)
    span = (last - first).days
    return pd.Series(
        np.select(
            [dates.le(first + pd.Timedelta(days=span / 3)), dates.le(first + pd.Timedelta(days=2 * span / 3))],
            ["EARLY", "MID"],
            default="LATE",
        ),
        index=series.index,
    )


def summarize_census_rows(audit: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = audit.copy()
    data["year"] = pd.to_datetime(data["date"]).dt.year
    data["date_stratum"] = _date_stratum(data["date"])
    known = data["panel_open"].notna() & data["panel_open"].gt(0)
    accepted = data["direct_admissible"] | data["split_admissible"]
    final_diag = np.where(data["direct_admissible"], "DIRECT_ACCEPTED", np.where(data["split_admissible"], "SPLIT_ACCEPTED", data["direct_diagnostic"]))
    data["final_diagnostic"] = final_diag
    by_year = (
        data.loc[~known]
        .assign(accepted=accepted.loc[~known])
        .groupby("year", sort=True)
        .agg(rows=("ticker", "size"), accepted=("accepted", "sum"), provider_rows=("provider_row_present", "sum"))
        .reset_index()
    )
    by_year["unresolved"] = by_year["rows"] - by_year["accepted"]
    rejection = (
        data.loc[(~known) & ~accepted, "final_diagnostic"]
        .value_counts(dropna=False)
        .rename_axis("diagnostic")
        .reset_index(name="rows")
    )
    temporal = (
        data.assign(accepted=accepted)
        .groupby("date_stratum", sort=True)
        .agg(
            rows=("ticker", "size"),
            provider_rows=("provider_row_present", "sum"),
            hlc_exact=("hlc_exact", "sum"),
            accepted=("accepted", "sum"),
        )
        .reset_index()
    )
    return by_year, rejection, temporal


def build_cache_manifest(cache_root: str | Path, statuses: pd.DataFrame) -> dict[str, Any]:
    cache_dir = Path(cache_root)
    entries = []
    for row in statuses.sort_values("ticker", kind="mergesort").itertuples(index=False):
        _, meta_path = _cache_paths(cache_dir, row.ticker)
        entries.append(
            {
                "ticker": row.ticker,
                "status": row.status,
                "metadata_file": meta_path.name,
                "metadata_sha256": sha256_file(meta_path) if meta_path.is_file() else None,
                "parquet_sha256": row.parquet_sha256 if pd.notna(row.parquet_sha256) else None,
            }
        )
    return {"semantics": CACHE_SEMANTICS, "entries": entries}


def run_yahoo_open_census(
    *,
    panel_path: str | Path,
    official_actions_path: str | Path,
    output_dir: str | Path,
    expected_panel_sha256: str = DEFAULT_EXPECTED_PANEL_SHA256,
    start: str = DEFAULT_START,
    end_inclusive: str = DEFAULT_END_INCLUSIVE,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
) -> dict[str, Any]:
    panel_file = Path(panel_path)
    actions_file = Path(official_actions_path)
    output = Path(output_dir)
    if not panel_file.is_file() or not actions_file.is_file():
        raise FileNotFoundError("panel and official-actions inputs are required")
    output.mkdir(parents=True, exist_ok=True)
    cache_root = output / "raw_cache"

    panel_sha_before = sha256_file(panel_file)
    if panel_sha_before != expected_panel_sha256:
        raise RuntimeError(f"Immutable panel SHA mismatch before runtime: {panel_sha_before}")
    panel = _prepare_panel(pd.read_parquet(panel_file))
    actions = pd.read_csv(actions_file)
    tickers = sorted(panel["ticker"].dropna().map(normalise_ticker).unique())

    provider, statuses, fetch_summary = fetch_universe_cached(
        tickers,
        start=start,
        end_inclusive=end_inclusive,
        cache_root=cache_root,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
    )
    _parquet_write(output / "yahoo_provider_rows.parquet", provider)
    _csv_write(output / "provider_ticker_status.csv", statuses)
    cache_manifest = build_cache_manifest(cache_root, statuses)
    _json_write(output / "raw_cache_manifest.json", cache_manifest)

    direct_audit, direct_summary = build_full_direct_audit(panel, provider)
    full_audit, split_summary = apply_verified_split_reconstruction(direct_audit, actions)
    derivative, provenance, derivative_summary = build_derivative_candidate(full_audit)
    by_year, rejection, temporal = summarize_census_rows(full_audit)

    _parquet_write(output / "yahoo_open_census_row_audit.parquet", full_audit)
    _parquet_write(output / "execution_open_candidate_panel.parquet", derivative)
    _parquet_write(output / "execution_open_candidate_provenance.parquet", provenance)
    _csv_write(output / "missing_open_by_year.csv", by_year)
    _csv_write(output / "missing_open_rejection_histogram.csv", rejection)
    _csv_write(output / "temporal_quality_summary.csv", temporal)

    initial_null = int(panel["open"].isna().sum())
    final_null = int(derivative["open"].isna().sum())
    gap_closed = initial_null - final_null
    status_counts = statuses["status"].value_counts().to_dict()
    unsupported = statuses.loc[~statuses["status"].eq("SUCCESS"), ["ticker", "status", "provider_errors", "provider_logs"]]
    _csv_write(output / "unsupported_or_error_tickers.csv", unsupported)

    summary = {
        "status": "YAHOO_FULL_UNIVERSE_OPEN_CENSUS_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "panel_sha256_before": panel_sha_before,
        "panel_rows": int(len(panel)),
        "panel_tickers": int(len(tickers)),
        "window": {"start": start, "end_inclusive": end_inclusive},
        "fetch": {**fetch_summary, "status_counts": {str(k): int(v) for k, v in status_counts.items()}},
        "direct": direct_summary,
        "split": split_summary,
        "derivative": {
            **derivative_summary,
            "gap_closed": gap_closed,
            "gap_closed_pct": float(gap_closed / initial_null) if initial_null else None,
        },
        "named_provider_status": {
            ticker: statuses.loc[statuses["ticker"].eq(ticker)].to_dict(orient="records")
            for ticker in ("FREN", "MASA", "MFIN", "PURE")
        },
        "execution_grade_promoted": False,
    }
    _json_write(output / "census_summary.json", summary)

    panel_sha_after = sha256_file(panel_file)
    if panel_sha_after != panel_sha_before:
        raise RuntimeError(f"Immutable panel changed during runtime: {panel_sha_after}")
    summary["panel_sha256_after"] = panel_sha_after

    artifact_files = sorted(path for path in output.iterdir() if path.is_file())
    artifact_manifest = {
        "runtime": "open_backfill_yahoo_census_v1_20260810",
        "files": {path.name: sha256_file(path) for path in artifact_files},
        "raw_cache_manifest_sha256": sha256_file(output / "raw_cache_manifest.json"),
        "execution_grade_promoted": False,
    }
    _json_write(output / "artifact_manifest.json", artifact_manifest)
    summary["artifact_manifest_sha256"] = sha256_file(output / "artifact_manifest.json")
    summary["derivative_panel_sha256"] = sha256_file(output / "execution_open_candidate_panel.parquet")
    summary["provenance_sha256"] = sha256_file(output / "execution_open_candidate_provenance.parquet")
    _json_write(output / "census_summary.json", summary)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Full-universe Yahoo historical Open recovery census")
    parser.add_argument("--panel", required=True)
    parser.add_argument("--official-actions", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-panel-sha256", default=DEFAULT_EXPECTED_PANEL_SHA256)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end-inclusive", default=DEFAULT_END_INCLUSIVE)
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument("--backoff-seconds", type=float, default=DEFAULT_BACKOFF_SECONDS)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run_yahoo_open_census(
        panel_path=args.panel,
        official_actions_path=args.official_actions,
        output_dir=args.output_dir,
        expected_panel_sha256=args.expected_panel_sha256,
        start=args.start,
        end_inclusive=args.end_inclusive,
        max_attempts=args.max_attempts,
        backoff_seconds=args.backoff_seconds,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
