from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import requests

from .provenance import sha256_file
from .security_master import normalise_ticker
from .tier2_open_audit import audit_provider_rows, redact_secrets
from .zapi_alt_open_audit import (
    TRADINGVIEW_ENDPOINT,
    _empty_provider_frame,
    _provider_frame,
    classify_provider,
)
from .zapi_tradingview_resume import (
    EXPECTED_PANEL_SHA256,
    PRIOR_FOLLOWUP_ROOT,
    PRIOR_ROOT,
    _merge_rows,
    _parse_payload,
    _request_resume,
    _safe_headers,
    probe_pro_quota,
)


BASE_ROOT = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v")
RESIDUAL_ROOT = BASE_ROOT / "open_backfill_yahoo_census_v1_20260810"
RESIDUAL_DETAIL_PATH = RESIDUAL_ROOT / "residual_open_detail.csv"
OUTPUT_ROOT = BASE_ROOT / "open_backfill_zapi_tradingview_targeted_census_v1_20260811"
PANEL_PATH = BASE_ROOT / "research_feasibility_1260_20260809" / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet"

EXPECTED_RESIDUAL_DETAIL_SHA256 = "26cd2319991aa5dc2fcce78d7f256f31fb1762b4510c0623fcd16fb87b66fd02"
EXPECTED_PRIOR_RESUME_MANIFEST_SHA256 = "68adea6bd6cf2b251b43e010133d8a3899c7d3ff8af8566f4bd9b88f0f9f3134"
EXPECTED_PRIOR_FIRST_MANIFEST_SHA256 = "b5008e9942ca8681499f544c98a8bccda9c1e03b82ceb46ba1fbc45d3b1a6a80"
EXPECTED_PRIOR_FOLLOWUP_MANIFEST_SHA256 = "87e40d23e02f7557d8a90120577ff68fd3e3567ee339c856386c141fdb61802d"
EXPECTED_AUTHORIZED_COUNTS = {
    "PROVIDER_HLC_MISMATCH_NO_VERIFIED_SPLIT_FACTOR": 32103,
    "NO_PROVIDER_ROW": 3840,
    "PROVIDER_ERROR_OR_SYMBOL_RESOLUTION_FAILURE": 2876,
}
EXCLUDED_CORPORATE_ACTION_CLASSES = {
    "CORPORATE_ACTION_ADJACENT_INCOMPLETE_OFFICIAL_EVIDENCE",
    "CORPORATE_ACTION_SCALE_MISMATCH_VERIFIED_FACTOR_FAILED",
}
FORBIDDEN_ERROR_TICKERS = {"FREN", "MASA", "MFIN", "RMBA", "TURI"}


def _write_json(value: object, path: Path) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[column]):
            data[column] = data[column].dt.strftime("%Y-%m-%d")
    data.to_csv(path, index=False, lineterminator="\n")


def _write_jsonl_record(record: dict[str, Any], path: Path) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def _load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_authorized_residual_detail(path: str | Path = RESIDUAL_DETAIL_PATH) -> tuple[pd.DataFrame, dict[str, Any]]:
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(file)
    digest = sha256_file(file)
    if digest != EXPECTED_RESIDUAL_DETAIL_SHA256:
        raise RuntimeError(f"Residual detail SHA mismatch: {digest}")
    detail = pd.read_csv(file)
    required = {"ticker", "date", "problem_class", "panel_high", "panel_low", "panel_close"}
    missing = required - set(detail.columns)
    if missing:
        raise ValueError(f"Residual detail columns missing: {sorted(missing)}")
    detail["ticker"] = detail["ticker"].map(normalise_ticker)
    detail["date"] = pd.to_datetime(detail["date"], errors="coerce").dt.normalize()
    if detail["date"].isna().any() or detail.duplicated(["ticker", "date"]).any():
        raise ValueError("Residual detail must contain unique valid ticker/date rows")
    counts = {str(k): int(v) for k, v in detail["problem_class"].value_counts().items()}
    if any(counts.get(key, 0) != expected for key, expected in EXPECTED_AUTHORIZED_COUNTS.items()):
        raise RuntimeError(f"Unexpected residual class counts: {counts}")
    authorized = detail[~detail["problem_class"].isin(EXCLUDED_CORPORATE_ACTION_CLASSES)].copy()
    if len(authorized) != sum(EXPECTED_AUTHORIZED_COUNTS.values()):
        raise RuntimeError(f"Authorized residual count mismatch: {len(authorized)}")
    authorized = authorized.reset_index(drop=True)
    authorized.insert(0, "census_id", [f"RES-{index:05d}" for index in range(1, len(authorized) + 1)])
    metadata = {
        "path": str(file),
        "sha256": digest,
        "total_residual_rows": int(len(detail)),
        "authorized_rows": int(len(authorized)),
        "authorized_class_counts": {key: int(counts[key]) for key in EXPECTED_AUTHORIZED_COUNTS},
        "excluded_corporate_action_rows": int(detail["problem_class"].isin(EXCLUDED_CORPORATE_ACTION_CLASSES).sum()),
        "excluded_corporate_action_class_counts": {
            key: int(counts.get(key, 0)) for key in EXCLUDED_CORPORATE_ACTION_CLASSES
        },
    }
    return authorized, metadata


def _audit_input_from_residual(detail: pd.DataFrame) -> pd.DataFrame:
    data = detail.copy()
    data["sample_id"] = data["census_id"]
    data["sample_role"] = "AUTHORIZED_NON_CA_RESIDUAL"
    data["panel_open"] = np.nan
    for column in ("yahoo_raw_high", "yahoo_raw_low", "yahoo_raw_close"):
        if column not in data.columns:
            data[column] = np.nan
    return data[
        [
            "sample_id",
            "sample_role",
            "ticker",
            "date",
            "panel_open",
            "panel_high",
            "panel_low",
            "panel_close",
            "problem_class",
            "yahoo_raw_high",
            "yahoo_raw_low",
            "yahoo_raw_close",
        ]
        ].rename(columns={"problem_class": "residual_problem_class"})


def _prior_paths() -> dict[str, Path]:
    return {
        "prior_first_manifest": PRIOR_ROOT / "artifact_manifest.json",
        "prior_first_rows": PRIOR_ROOT / "tradingview_candidate_rows.csv",
        "prior_first_audit": PRIOR_ROOT / "tradingview_row_audit.csv",
        "prior_resume_manifest": BASE_ROOT / "open_backfill_zapi_tradingview_resume_v1_20260811" / "artifact_manifest.json",
        "prior_combined_rows": BASE_ROOT / "open_backfill_zapi_tradingview_resume_v1_20260811" / "tradingview_combined_rows_with_provenance.csv",
        "prior_combined_status": BASE_ROOT / "open_backfill_zapi_tradingview_resume_v1_20260811" / "tradingview_combined_ticker_status.csv",
        "prior_combined_audit": BASE_ROOT / "open_backfill_zapi_tradingview_resume_v1_20260811" / "tradingview_combined_row_audit.csv",
        "prior_followup_manifest": PRIOR_FOLLOWUP_ROOT / "artifact_manifest.json",
    }


def load_preserved_tradingview() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    paths = _prior_paths()
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing preserved artifact {name}: {path}")
    expected = {
        "prior_resume_manifest": EXPECTED_PRIOR_RESUME_MANIFEST_SHA256,
        "prior_first_manifest": EXPECTED_PRIOR_FIRST_MANIFEST_SHA256,
        "prior_followup_manifest": EXPECTED_PRIOR_FOLLOWUP_MANIFEST_SHA256,
    }
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    for name, digest in expected.items():
        if hashes[name] != digest:
            raise RuntimeError(f"Preserved {name} SHA mismatch: {hashes[name]}")
    rows = _load_csv(paths["prior_combined_rows"])
    rows["ticker"] = rows["ticker"].map(normalise_ticker)
    rows["date"] = pd.to_datetime(rows["date"], errors="coerce").dt.normalize()
    if "provenance" not in rows.columns:
        raise RuntimeError("Preserved combined TradingView provenance is missing")
    rows = rows.drop_duplicates(["ticker", "date"], keep="first").sort_values(["ticker", "date"]).reset_index(drop=True)
    status = _load_csv(paths["prior_combined_status"])
    status["ticker"] = status["ticker"].map(normalise_ticker)
    return rows, status, hashes


def _exact_coverage(detail: pd.DataFrame, provider: pd.DataFrame) -> pd.Series:
    keys = pd.MultiIndex.from_frame(detail[["ticker", "date"]])
    provider_keys = pd.MultiIndex.from_frame(provider[["ticker", "date"]].drop_duplicates()) if not provider.empty else pd.MultiIndex.from_tuples([])
    return pd.Series(keys.isin(provider_keys), index=detail.index)


def _ticker_coverage(detail: pd.DataFrame, provider: pd.DataFrame, prior_status: pd.DataFrame) -> dict[str, int]:
    exact = _exact_coverage(detail, provider)
    data = detail[["ticker"]].copy()
    data["exact"] = exact.to_numpy()
    per_ticker = data.groupby("ticker", sort=True)["exact"].agg(["sum", "count"])
    full = int((per_ticker["sum"] == per_ticker["count"]).sum())
    partial = int(((per_ticker["sum"] > 0) & (per_ticker["sum"] < per_ticker["count"])).sum())
    uncovered = int((per_ticker["sum"] == 0).sum())
    success = set(prior_status.loc[prior_status["status"].eq("SUCCESS"), "ticker"])
    return {
        "unique_authorized_residual_tickers": int(detail["ticker"].nunique()),
        "fully_covered_tickers_before_network": full,
        "partially_covered_tickers_before_network": partial,
        "uncovered_tickers_before_network": uncovered,
        "preserved_success_tickers_in_authorized_scope": int(len(success & set(detail["ticker"]))),
    }


def build_network_tickers(detail: pd.DataFrame, prior_status: pd.DataFrame) -> tuple[list[str], dict[str, Any]]:
    residual_tickers = set(detail["ticker"])
    successful = set(prior_status.loc[prior_status["status"].eq("SUCCESS"), "ticker"].map(normalise_ticker))
    prior_errors = set(prior_status.loc[prior_status["status"] != "SUCCESS", "ticker"].map(normalise_ticker))
    forbidden = residual_tickers & FORBIDDEN_ERROR_TICKERS
    requested = sorted(residual_tickers - successful - forbidden)
    return requested, {
        "prior_success_tickers_refetched": int(len(set(requested) & successful)),
        "forbidden_error_tickers_in_scope": sorted(forbidden),
        "prior_error_tickers_in_scope": sorted(residual_tickers & prior_errors),
        "network_ticker_set_sha256": sha256_file_from_lines(requested),
    }


def sha256_file_from_lines(values: Iterable[str]) -> str:
    import hashlib

    return hashlib.sha256(("\n".join(sorted(values)) + "\n").encode("utf-8")).hexdigest()


def _merge_status(prior: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([prior, new], ignore_index=True, sort=False)
    return combined.drop_duplicates(["ticker"], keep="last").sort_values("ticker").reset_index(drop=True)


def _arbitration(audit: pd.DataFrame) -> dict[str, int]:
    labels: Counter[str] = Counter()
    for row in audit.itertuples(index=False):
        if row.diagnostic == "NO_PROVIDER_ROW":
            labels["NO_PROVIDER_ROW"] += 1
            continue
        panel = bool(row.hlc_exact)
        yahoo = bool(getattr(row, "provider_hlc_matches_yahoo", False))
        if panel and yahoo:
            labels["SUPPORTS_CERTIFIED_PANEL_AND_YAHOO"] += 1
        elif panel:
            labels["SUPPORTS_CERTIFIED_PANEL"] += 1
        elif yahoo:
            labels["SUPPORTS_YAHOO"] += 1
        else:
            labels["DISAGREEMENT"] += 1
    return dict(sorted(labels.items()))


def _group_counts(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    grouped = frame.groupby(columns, dropna=False, sort=True).size().reset_index(name="rows")
    return [{str(key): (None if pd.isna(value) else value) for key, value in row.items()} for row in grouped.to_dict("records")]


def _candidate_concentration(audit: pd.DataFrame) -> dict[str, Any]:
    candidates = audit[audit["provider_class"].eq("TV_RECOVERY_CANDIDATE")].copy()
    if candidates.empty:
        return {"top_20": [], "cumulative_top_10": 0, "cumulative_top_50": 0, "cumulative_top_100": 0}
    counts = candidates["ticker"].value_counts().rename_axis("ticker").reset_index(name="rows")
    counts = counts.sort_values(["rows", "ticker"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    return {
        "top_20": counts.head(20).to_dict("records"),
        "cumulative_top_10": int(counts.head(10)["rows"].sum()),
        "cumulative_top_50": int(counts.head(50)["rows"].sum()),
        "cumulative_top_100": int(counts.head(100)["rows"].sum()),
    }


def _metrics(detail: pd.DataFrame, audit: pd.DataFrame, status: pd.DataFrame) -> dict[str, Any]:
    detail_fields = detail[["census_id", "problem_class", "residual_reason", "date"]]
    candidate = audit[audit["provider_class"].eq("TV_RECOVERY_CANDIDATE")].copy()
    candidate = candidate.merge(detail_fields, left_on="sample_id", right_on="census_id", how="left")
    candidate_date_column = "date_y" if "date_y" in candidate.columns else "date"
    candidate["year"] = pd.to_datetime(candidate[candidate_date_column], errors="coerce").dt.year
    non_candidate = audit[~audit["provider_class"].eq("TV_RECOVERY_CANDIDATE")].copy()
    non_candidate = non_candidate.merge(detail_fields, left_on="sample_id", right_on="census_id", how="left")
    non_candidate_date_column = "date_y" if "date_y" in non_candidate.columns else "date"
    non_candidate["year"] = pd.to_datetime(non_candidate[non_candidate_date_column], errors="coerce").dt.year
    provider_errors = status[status["status"] != "SUCCESS"]
    exact_coverage = audit["diagnostic"].ne("NO_PROVIDER_ROW")
    return {
        "authorized_rows": int(len(detail)),
        "unique_authorized_residual_tickers": int(detail["ticker"].nunique()),
        "exact_ticker_date_coverage": int(exact_coverage.sum()),
        "exact_ticker_date_coverage_rate": float(exact_coverage.mean()),
        "hlc_exact_count": int(audit["hlc_exact"].fillna(False).sum()),
        "hlc_exact_rate": float(audit["hlc_exact"].fillna(False).mean()),
        "admissible_open_recovery_candidates": int(len(candidate)),
        "admissible_open_recovery_rate": float(len(candidate) / len(detail)),
        "recovery_by_original_residual_class": {
            str(key): int(value) for key, value in candidate["problem_class"].value_counts().items()
        },
        "recovery_by_calendar_year": {
            str(key): int(value) for key, value in candidate["year"].value_counts().sort_index().items()
        },
        "recovery_ticker_concentration": _candidate_concentration(audit),
        "history_window_unavailable": int(audit["provider_class"].eq("TV_HISTORY_WINDOW_UNAVAILABLE").sum()),
        "hlc_disagreement": int(audit["provider_class"].eq("TV_HLC_DISAGREEMENT").sum()),
        "hlc_disagreement_rate": float(audit["provider_class"].eq("TV_HLC_DISAGREEMENT").mean()),
        "provider_class_counts": {str(key): int(value) for key, value in audit["provider_class"].value_counts().items()},
        "unresolved_by_reason_class_year": _group_counts(non_candidate, ["provider_class", "problem_class", "residual_reason", "year"]),
        "yahoo_arbitration": _arbitration(audit),
        "provider_symbol_error_ticker_count": int(len(provider_errors)),
        "provider_symbol_error_tickers": [str(value) for value in provider_errors["ticker"].tolist()],
    }


def _artifact_manifest(output: Path, summary_name: str) -> dict[str, Any]:
    files = sorted(path for path in output.iterdir() if path.is_file() and path.name not in {"artifact_manifest.json", summary_name})
    return {
        "runtime": "zapi_tradingview_targeted_census_v1_20260811",
        "files": {path.name: sha256_file(path) for path in files},
    }


def _validate_panel_before() -> str:
    digest = sha256_file(PANEL_PATH)
    if digest != EXPECTED_PANEL_SHA256:
        raise RuntimeError(f"Immutable panel SHA mismatch: {digest}")
    return digest


def run_targeted_census(
    *,
    residual_detail_path: str | Path = RESIDUAL_DETAIL_PATH,
    output_dir: str | Path = OUTPUT_ROOT,
) -> dict[str, Any]:
    panel_before = _validate_panel_before()
    detail, residual_meta = load_authorized_residual_detail(residual_detail_path)
    prior_rows, prior_status, prior_hashes = load_preserved_tradingview()
    coverage_before = _ticker_coverage(detail, prior_rows, prior_status)
    requested_tickers, request_meta = build_network_tickers(detail, prior_status)
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    _write_csv(detail, output / "authorized_non_ca_residual_detail.csv")
    _write_json(
        {
            "source_path": residual_meta["path"],
            "source_sha256": residual_meta["sha256"],
            "authorized_rows": residual_meta["authorized_rows"],
            "excluded_corporate_action_rows": residual_meta["excluded_corporate_action_rows"],
        },
        output / "residual_input_provenance.json",
    )

    api_key = os.environ.get("ZAPI_API_KEY")
    quota_before: dict[str, Any]
    quota_after: dict[str, Any]
    raw_path = output / "tradingview_targeted_raw_responses.jsonl"
    raw_path.write_text("", encoding="utf-8")
    new_frames: list[pd.DataFrame] = []
    new_status_rows: list[dict[str, Any]] = []
    logical_requests = attempts = retries = rate_limits = 0
    request_errors: list[str] = []
    terminal_stop: str | None = None
    if not api_key:
        quota_before = {"stage": "before", "plan_status": "UNKNOWN", "pro_limits_confirmed": False, "status": "ZAPI_BLOCKED_CREDENTIAL_ABSENT"}
        quota_after = {"stage": "after", "not_called": True}
        terminal_stop = "ZAPI_BLOCKED_CREDENTIAL_ABSENT"
    else:
        client = requests.Session()
        quota_before = probe_pro_quota(client, api_key, stage="before")
        _write_json(quota_before, output / "quota_before.json")
        if not quota_before.get("pro_limits_confirmed"):
            terminal_stop = "PRO_QUOTA_NOT_CONFIRMED"
            quota_after = {"stage": "after", "not_called": True}
        else:
            quota_after = {}
            for ticker in requested_tickers:
                logical_requests += 1
                payload, meta = _request_resume(client, ticker, api_key)
                attempts += int(meta.get("attempts", 0))
                retries += int(meta.get("retries", 0))
                rate_limits += int(meta.get("rate_limit_events", 0))
                request_errors.extend(f"{ticker}:{error}" for error in meta.get("errors", []))
                _write_jsonl_record(
                    {
                        "requested_ticker": ticker,
                        "request": {
                            "endpoint": TRADINGVIEW_ENDPOINT,
                            "params": {"symbol": f"IDX:{ticker}", "market": "indonesia", "resolution": "1D", "count": 1000},
                        },
                        "meta": {key: value for key, value in meta.items() if key != "safe_headers"},
                        "safe_headers": meta.get("safe_headers", {}),
                        "response": redact_secrets(payload, (api_key,)) if payload is not None else None,
                    },
                    raw_path,
                )
                if payload is None:
                    new_status_rows.append({"ticker": ticker, "status": "RATE_LIMITED" if meta.get("rate_limit_stop_reason") else meta.get("access_status", "REQUEST_ERROR"), "min_date": None, "max_date": None, "rows": 0})
                    if meta.get("rate_limit_stop_reason") in {"MONTH_QUOTA", "UNKNOWN_QUOTA_WINDOW"}:
                        terminal_stop = str(meta["rate_limit_stop_reason"])
                        break
                    continue
                frame, status = _parse_payload(ticker, payload, "TARGETED_CENSUS")
                if not frame.empty:
                    new_frames.append(frame)
                new_status_rows.append({"ticker": ticker, **status})
            quota_after = probe_pro_quota(client, api_key, stage="after")
            if terminal_stop:
                attempted = {row["ticker"] for row in new_status_rows}
                new_status_rows.extend({"ticker": ticker, "status": "NOT_ATTEMPTED_AFTER_QUOTA_STOP", "min_date": None, "max_date": None, "rows": 0} for ticker in requested_tickers if ticker not in attempted)
    _write_json(quota_before, output / "quota_before.json")
    _write_json(quota_after, output / "quota_after.json")
    new_provider = _provider_frame(pd.concat(new_frames, ignore_index=True) if new_frames else _empty_provider_frame())
    if not new_provider.empty:
        new_provider["provenance"] = "TARGETED_CENSUS"
    new_status = pd.DataFrame(new_status_rows, columns=["ticker", "status", "min_date", "max_date", "rows"])
    combined_provider = _merge_rows(prior_rows, new_provider)
    combined_status = _merge_status(prior_status, new_status)
    audit_input = _audit_input_from_residual(detail)
    audit_raw, audit_summary = audit_provider_rows(audit_input, combined_provider, "ZAPI_TRADINGVIEW_TARGETED_COMBINED")
    audit_sample = _audit_input_from_residual(detail)
    combined_audit = classify_provider(audit_sample, audit_raw, combined_status, "TV")
    audit_raw_new, _ = audit_provider_rows(audit_input, new_provider, "ZAPI_TRADINGVIEW_TARGETED_INCREMENTAL")
    new_audit = classify_provider(audit_sample, audit_raw_new, new_status, "TV")
    _write_csv(new_provider, output / "tradingview_targeted_rows.csv")
    _write_csv(new_status, output / "tradingview_targeted_ticker_status.csv")
    _write_csv(new_audit, output / "tradingview_targeted_row_audit.csv")
    _write_csv(combined_provider, output / "tradingview_combined_rows_with_provenance.csv")
    _write_csv(combined_status, output / "tradingview_combined_ticker_status.csv")
    _write_csv(combined_audit, output / "tradingview_combined_row_audit.csv")
    panel_after = _validate_panel_before()
    summary: dict[str, Any] = {
        "status": "ZAPI_TRADINGVIEW_TARGETED_CENSUS_COMPLETE" if terminal_stop is None else "ZAPI_TRADINGVIEW_TARGETED_CENSUS_STOPPED",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "endpoint": TRADINGVIEW_ENDPOINT,
        "request_contract": {"symbol": "IDX:<ticker>", "market": "indonesia", "resolution": "1D", "count": 1000},
        "residual_input": residual_meta,
        "prior_artifacts": prior_hashes,
        "preserved_tradingview_manifest_sha256": EXPECTED_PRIOR_RESUME_MANIFEST_SHA256,
        "reuse_offline": coverage_before,
        "network_selection": {**request_meta, "new_unique_tickers_requested": len(requested_tickers), "requested_tickers": requested_tickers},
        "network": {
            "logical_requests": logical_requests,
            "requests_made": attempts,
            "retries": retries,
            "rate_limit_events": rate_limits,
            "provider_errors": request_errors,
            "new_provider_rows": int(len(new_provider)),
            "targeted_status_counts": {str(k): int(v) for k, v in new_status["status"].value_counts().items()} if not new_status.empty else {},
            "quota_before": quota_before,
            "quota_after": quota_after,
            "terminal_stop": terminal_stop,
        },
        "final_census": _metrics(detail, combined_audit, combined_status),
        "incremental_census": _metrics(detail, new_audit, new_status) if not new_status.empty else {},
        "combined_provider_rows": int(len(combined_provider)),
        "combined_deduplicated_by_provider_ticker_date": not combined_provider.duplicated(["ticker", "date"]).any(),
        "hypothetical_remaining_non_ca_residual_if_all_candidates_approved": int(len(detail) - combined_audit["provider_class"].eq("TV_RECOVERY_CANDIDATE").sum()),
        "hypothetical_only_no_panel_write": True,
        "immutable_panel_sha256_before": panel_before,
        "immutable_panel_sha256_after": panel_after,
        "immutable_panel_unchanged": panel_before == panel_after == EXPECTED_PANEL_SHA256,
        "execution_grade_promoted": False,
        "bulk_backfill_authorized": False,
        "panel_backfill_performed": False,
        "corporate_action_repair_performed": False,
        "investing_called": False,
        "stock_history_called": False,
    }
    _write_json(summary, output / "zapi_tradingview_targeted_census_summary.json")
    _write_json(_artifact_manifest(output, "zapi_tradingview_targeted_census_summary.json"), output / "artifact_manifest.json")
    summary["artifact_manifest_sha256"] = sha256_file(output / "artifact_manifest.json")
    _write_json(summary, output / "zapi_tradingview_targeted_census_summary.json")
    return summary


def finalize_existing(*, output_dir: str | Path = OUTPUT_ROOT) -> dict[str, Any]:
    """Rebuild summaries/audits from a completed raw batch without network calls."""

    output = Path(output_dir)
    required = (
        "authorized_non_ca_residual_detail.csv",
        "quota_before.json",
        "quota_after.json",
        "tradingview_targeted_raw_responses.jsonl",
        "tradingview_targeted_rows.csv",
        "tradingview_targeted_ticker_status.csv",
    )
    for name in required:
        if not (output / name).is_file():
            raise FileNotFoundError(output / name)
    panel_before = _validate_panel_before()
    detail, residual_meta = load_authorized_residual_detail(RESIDUAL_DETAIL_PATH)
    prior_rows, prior_status, prior_hashes = load_preserved_tradingview()
    targeted_raw = _load_csv(output / "tradingview_targeted_rows.csv")
    new_provider = _provider_frame(targeted_raw)
    if "provenance" in targeted_raw.columns:
        new_provider["provenance"] = targeted_raw["provenance"].to_numpy()
    new_status = _load_csv(output / "tradingview_targeted_ticker_status.csv")
    new_status["ticker"] = new_status["ticker"].map(normalise_ticker)
    combined_provider = _merge_rows(prior_rows, new_provider)
    combined_status = _merge_status(prior_status, new_status)
    audit_sample = _audit_input_from_residual(detail)
    audit_raw, _ = audit_provider_rows(audit_sample, combined_provider, "ZAPI_TRADINGVIEW_TARGETED_COMBINED")
    combined_audit = classify_provider(audit_sample, audit_raw, combined_status, "TV")
    audit_raw_new, _ = audit_provider_rows(audit_sample, new_provider, "ZAPI_TRADINGVIEW_TARGETED_INCREMENTAL")
    new_audit = classify_provider(audit_sample, audit_raw_new, new_status, "TV")
    _write_csv(new_audit, output / "tradingview_targeted_row_audit.csv")
    _write_csv(combined_provider, output / "tradingview_combined_rows_with_provenance.csv")
    _write_csv(combined_status, output / "tradingview_combined_ticker_status.csv")
    _write_csv(combined_audit, output / "tradingview_combined_row_audit.csv")
    requested_tickers, request_meta = build_network_tickers(detail, prior_status)
    raw_records: list[dict[str, Any]] = []
    with (output / "tradingview_targeted_raw_responses.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw_records.append(json.loads(line))
    request_errors = [
        f"{record.get('requested_ticker')}:{error}"
        for record in raw_records
        for error in record.get("meta", {}).get("errors", [])
    ]
    quota_before = json.loads((output / "quota_before.json").read_text(encoding="utf-8"))
    quota_after = json.loads((output / "quota_after.json").read_text(encoding="utf-8"))
    panel_after = _validate_panel_before()
    summary: dict[str, Any] = {
        "status": "ZAPI_TRADINGVIEW_TARGETED_CENSUS_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "endpoint": TRADINGVIEW_ENDPOINT,
        "request_contract": {"symbol": "IDX:<ticker>", "market": "indonesia", "resolution": "1D", "count": 1000},
        "residual_input": residual_meta,
        "prior_artifacts": prior_hashes,
        "preserved_tradingview_manifest_sha256": EXPECTED_PRIOR_RESUME_MANIFEST_SHA256,
        "reuse_offline": _ticker_coverage(detail, prior_rows, prior_status),
        "network_selection": {**request_meta, "new_unique_tickers_requested": len(requested_tickers), "requested_tickers": requested_tickers},
        "network": {
            "logical_requests": len(raw_records),
            "requests_made": sum(int(record.get("meta", {}).get("attempts", 0)) for record in raw_records),
            "retries": sum(int(record.get("meta", {}).get("retries", 0)) for record in raw_records),
            "rate_limit_events": sum(int(record.get("meta", {}).get("rate_limit_events", 0)) for record in raw_records),
            "provider_errors": request_errors,
            "new_provider_rows": int(len(new_provider)),
            "targeted_status_counts": {str(k): int(v) for k, v in new_status["status"].value_counts().items()},
            "quota_before": quota_before,
            "quota_after": quota_after,
            "terminal_stop": None,
        },
        "final_census": _metrics(detail, combined_audit, combined_status),
        "incremental_census": _metrics(detail, new_audit, new_status),
        "combined_provider_rows": int(len(combined_provider)),
        "combined_deduplicated_by_provider_ticker_date": not combined_provider.duplicated(["ticker", "date"]).any(),
        "hypothetical_remaining_non_ca_residual_if_all_candidates_approved": int(len(detail) - combined_audit["provider_class"].eq("TV_RECOVERY_CANDIDATE").sum()),
        "hypothetical_only_no_panel_write": True,
        "immutable_panel_sha256_before": panel_before,
        "immutable_panel_sha256_after": panel_after,
        "immutable_panel_unchanged": panel_before == panel_after == EXPECTED_PANEL_SHA256,
        "execution_grade_promoted": False,
        "bulk_backfill_authorized": False,
        "panel_backfill_performed": False,
        "corporate_action_repair_performed": False,
        "investing_called": False,
        "stock_history_called": False,
        "reused_existing_network_artifacts": True,
    }
    _write_json(summary, output / "zapi_tradingview_targeted_census_summary.json")
    _write_json(_artifact_manifest(output, "zapi_tradingview_targeted_census_summary.json"), output / "artifact_manifest.json")
    summary["artifact_manifest_sha256"] = sha256_file(output / "artifact_manifest.json")
    _write_json(summary, output / "zapi_tradingview_targeted_census_summary.json")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen non-corporate-action Zapi TradingView residual census")
    parser.add_argument("--residual-detail", default=str(RESIDUAL_DETAIL_PATH))
    parser.add_argument("--output-dir", default=str(OUTPUT_ROOT))
    parser.add_argument("--finalize-existing", action="store_true")
    args = parser.parse_args()
    result = finalize_existing(output_dir=args.output_dir) if args.finalize_existing else run_targeted_census(residual_detail_path=args.residual_detail, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
