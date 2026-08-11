"""Frozen, identity-first TradingView remediation audit.

The audit is deliberately narrower than the targeted census: it only examines
the 2,877 rows already classified as TradingView identity/provider errors and
authorizes one unchanged retry for SMBR.  It never writes a panel or derivative.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

from .provenance import sha256_file
from .security_master import normalise_ticker
from .tier2_open_audit import audit_provider_rows, redact_secrets
from .zapi_alt_open_audit import TRADINGVIEW_ENDPOINT, _empty_provider_frame, _provider_frame, _unwrap
from .zapi_tradingview_resume import _parse_payload, _safe_headers


BASE_ROOT = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v")
TARGET_ROOT = BASE_ROOT / "open_backfill_zapi_tradingview_targeted_census_v1_20260811"
TARGET_AUDIT_PATH = TARGET_ROOT / "tradingview_combined_row_audit.csv"
TARGET_STATUS_PATH = TARGET_ROOT / "tradingview_combined_ticker_status.csv"
TARGET_RAW_PATH = TARGET_ROOT / "tradingview_targeted_raw_responses.jsonl"
RESUME_RAW_PATH = BASE_ROOT / "open_backfill_zapi_tradingview_resume_v1_20260811" / "tradingview_resume_raw_responses.jsonl"
SECURITY_MASTER_PATH = BASE_ROOT / "listings" / "security_master.csv"
CURATED_IDENTITIES_PATH = Path(__file__).resolve().parents[2] / "config" / "curated_security_identities.csv"
OFFICIAL_SUMMARY_RAW_ROOT = BASE_ROOT / "zapi_idx_source_acceptance_v1_20260811_retry1" / "raw"
YAHOO_STATUS_PATH = BASE_ROOT / "open_backfill_yahoo_census_v1_20260810" / "provider_ticker_status.csv"
PANEL_PATH = BASE_ROOT / "research_feasibility_1260_20260809" / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet"
DERIVATIVE_ROOT = BASE_ROOT / "open_backfill_zapi_tradingview_derivative_v1_20260811"
DERIVATIVE_FILES = (
    "execution_open_candidate_panel_yahoo_tradingview.parquet",
    "execution_open_candidate_provenance_yahoo_tradingview.parquet",
)
OUTPUT_ROOT = BASE_ROOT / "open_backfill_zapi_tradingview_identity_remediation_v1_20260812"

EXPECTED_TARGET_AUDIT_SHA256 = "1c05a53155ed52783f112f58babc363e4ee081180542be71a9dfa1bd3ba4c5cd"
EXPECTED_TARGET_STATUS_SHA256 = "40a9acda3eae3cbb2068ce8240c11f9679c6620c68b6d357c9d1ca33fc0f1620"
EXPECTED_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
EXPECTED_TARGET_ROWS = 2877
TARGET_TICKERS = ("FREN", "MASA", "MFIN", "RMBA", "SMBR", "TURI")
RETRY_TICKER = "SMBR"
EXPECTED_CONTRACT = {"symbol": "IDX:<ticker>", "market": "indonesia", "resolution": "1D", "count": 1000}
CORPORATE_ACTION_CLASSES = {
    "CORPORATE_ACTION_ADJACENT_INCOMPLETE_OFFICIAL_EVIDENCE",
    "CORPORATE_ACTION_SCALE_MISMATCH_VERIFIED_FACTOR_FAILED",
}
FREN_FALLBACK_HTTP_STATUS = 404
FREN_STATUS_EVIDENCE = Path(__file__).resolve().parents[2] / "docs" / "checkpoints" / "2026-08-11_ZAPI_TRADINGVIEW_RESUME_RUNTIME.md"


def _write_json(value: object, path: Path) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[column]):
            data[column] = data[column].dt.strftime("%Y-%m-%d")
    data.to_csv(path, index=False, lineterminator="\n")


def _append_raw(path: Path, record: dict[str, Any], api_key: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(redact_secrets(record, (api_key,)), ensure_ascii=False, sort_keys=True, default=str) + "\n")


def _frame_sha256(frame: pd.DataFrame) -> str:
    return hashlib.sha256(frame.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()


def _load_frozen_target(path: str | Path = TARGET_AUDIT_PATH) -> tuple[pd.DataFrame, dict[str, Any]]:
    file = Path(path)
    digest = sha256_file(file)
    if digest != EXPECTED_TARGET_AUDIT_SHA256:
        raise RuntimeError(f"TradingView target source SHA mismatch: {digest}")
    audit = pd.read_csv(file)
    required = {"sample_id", "ticker", "date", "panel_high", "panel_low", "panel_close", "provider_class"}
    missing = required - set(audit.columns)
    if missing:
        raise ValueError(f"target audit columns missing: {sorted(missing)}")
    target = audit[audit["provider_class"].eq("TV_IDENTITY_OR_PROVIDER_ERROR")].copy()
    target["ticker"] = target["ticker"].map(normalise_ticker)
    target["date"] = pd.to_datetime(target["date"], errors="coerce").dt.normalize()
    if len(target) != EXPECTED_TARGET_ROWS:
        raise RuntimeError(f"Frozen target row count mismatch: {len(target)}")
    if target["date"].isna().any() or target.duplicated(["ticker", "date"]).any():
        raise ValueError("Frozen target contains invalid or duplicate ticker/date rows")
    if set(target["ticker"]) != set(TARGET_TICKERS):
        raise RuntimeError(f"Frozen target ticker set mismatch: {sorted(target['ticker'].unique())}")
    if target["residual_problem_class"].isin(CORPORATE_ACTION_CLASSES).any():
        raise RuntimeError("Corporate-action rows entered the remediation target")
    return target.reset_index(drop=True), {
        "source_path": str(file),
        "source_sha256": digest,
        "rows": int(len(target)),
        "filtered_target_sha256": _frame_sha256(target),
        "ticker_counts": {str(k): int(v) for k, v in target["ticker"].value_counts().sort_index().items()},
        "date_range_by_ticker": {
            ticker: {
                "rows": int(len(group)),
                "min_date": str(group["date"].min().date()),
                "max_date": str(group["date"].max().date()),
            }
            for ticker, group in target.groupby("ticker", sort=True)
        },
    }


def _load_status(path: str | Path = TARGET_STATUS_PATH) -> tuple[pd.DataFrame, dict[str, Any]]:
    file = Path(path)
    digest = sha256_file(file)
    if digest != EXPECTED_TARGET_STATUS_SHA256:
        raise RuntimeError(f"TradingView status SHA mismatch: {digest}")
    status = pd.read_csv(file)
    status["ticker"] = status["ticker"].map(normalise_ticker)
    selected = status[status["ticker"].isin(TARGET_TICKERS)].copy()
    return selected, {"path": str(file), "sha256": digest, "rows": int(len(selected)), "records": selected.to_dict("records")}


def _load_raw_error_status(path: Path, tickers: set[str]) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        ticker = normalise_ticker(record.get("requested_ticker") or record.get("ticker"))
        if ticker not in tickers:
            continue
        safe = record.get("safe_headers") or {}
        meta = record.get("meta") or {}
        result[ticker] = {
            "ticker": ticker,
            "http_status": safe.get("http_status"),
            "errors": meta.get("errors", []),
            "source_path": str(path),
            "raw_record_present": True,
        }
    return result


def _load_identity_evidence(
    *,
    tickers: tuple[str, ...] = TARGET_TICKERS,
    security_master_path: Path = SECURITY_MASTER_PATH,
    curated_path: Path = CURATED_IDENTITIES_PATH,
    official_root: Path = OFFICIAL_SUMMARY_RAW_ROOT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    master = pd.read_csv(security_master_path)
    master["ticker"] = master["ticker"].map(normalise_ticker)
    curated_rows: dict[str, dict[str, Any]] = {}
    with curated_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            curated_rows[normalise_ticker(row.get("ticker"))] = row

    snapshots: dict[str, list[dict[str, Any]]] = {ticker: [] for ticker in tickers}
    official_files: list[dict[str, Any]] = []
    for file in sorted(official_root.glob("official_*.json")):
        digest = sha256_file(file)
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except Exception:
            continue
        found: list[dict[str, Any]] = []

        def walk(value: object) -> None:
            if isinstance(value, dict):
                ticker = normalise_ticker(value.get("StockCode"))
                if ticker in snapshots:
                    row = {
                        "ticker": ticker,
                        "date": value.get("Date"),
                        "stock_name": value.get("StockName"),
                        "delisting_date": value.get("DelistingDate"),
                        "source_file": str(file),
                        "source_sha256": digest,
                    }
                    snapshots[ticker].append(row)
                    found.append(row)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(payload)
        if found:
            official_files.append({"path": str(file), "sha256": digest, "tickers": sorted({row["ticker"] for row in found})})

    identity_rows: list[dict[str, Any]] = []
    for ticker in tickers:
        master_rows = master[master["ticker"].eq(ticker)]
        curated = curated_rows.get(ticker)
        if not master_rows.empty:
            row = master_rows.iloc[0].to_dict()
            identity = {
                "ticker": ticker,
                "company_name": row.get("company_name"),
                "security_type": "common share (canonical project master contract)",
                "listed_from": row.get("listed_from"),
                "listed_to": row.get("listed_to"),
                "listing_source": row.get("source"),
                "identity_source": str(security_master_path),
            }
        elif curated:
            identity = {
                "ticker": ticker,
                "company_name": curated.get("company_name"),
                "security_type": curated.get("security_type"),
                "listed_from": curated.get("listed_from"),
                "listed_to": curated.get("listed_to"),
                "listing_source": curated.get("source"),
                "identity_source": str(curated_path),
                "source_ref": curated.get("source_ref"),
            }
        else:
            identity = {"ticker": ticker, "identity_source": None, "identity_status": "NOT_FOUND"}
        observed_names = sorted({str(row["stock_name"]) for row in snapshots[ticker] if row.get("stock_name")})
        identity.update(
            {
                "official_stock_summary_names": observed_names,
                "official_stock_summary_evidence_rows": snapshots[ticker],
                "explicit_ticker_aliases_found": [],
                "alias_evidence_status": "NO_EXPLICIT_HISTORICAL_CURRENT_TICKER_ALIAS_FOUND",
                "alternate_symbol_request_authorized": ticker == RETRY_TICKER,
                "alternate_symbol_request_reason": "none; unchanged canonical retry only" if ticker == RETRY_TICKER else "no project evidence supports an alternate symbol",
            }
        )
        identity_rows.append(identity)
    evidence = {
        "security_master_path": str(security_master_path),
        "security_master_sha256": sha256_file(security_master_path),
        "curated_identity_path": str(curated_path),
        "curated_identity_sha256": sha256_file(curated_path),
        "official_summary_raw_root": str(official_root),
        "official_summary_files": official_files,
        "ticker_history_conclusion": "No explicit alternate ticker relationship was found in preserved project evidence; official snapshots show name observations under the same ticker only.",
    }
    return identity_rows, evidence


def _build_audit_input(target: pd.DataFrame) -> pd.DataFrame:
    data = target.copy()
    data["sample_role"] = "AUTHORIZED_IDENTITY_PROVIDER_RESIDUAL"
    data["panel_open"] = np.nan
    for column in ("yahoo_raw_high", "yahoo_raw_low", "yahoo_raw_close"):
        if column not in data:
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
            "yahoo_raw_high",
            "yahoo_raw_low",
            "yahoo_raw_close",
        ]
    ].copy()


def _request_once(session: requests.Session, ticker: str, api_key: str) -> tuple[object | None, dict[str, Any]]:
    params = {"symbol": f"IDX:{ticker}", "market": "indonesia", "resolution": "1D", "count": 1000}
    try:
        response = session.get(TRADINGVIEW_ENDPOINT, params=params, headers={"x-api-key": api_key}, timeout=30)
    except Exception as error:
        return None, {
            "access_status": "REQUEST_ERROR",
            "attempts": 1,
            "retries": 0,
            "rate_limit_events": 0,
            "errors": [str(redact_secrets(f"{type(error).__name__}: {error}", (api_key,)))],
            "safe_headers": {},
        }
    safe = _safe_headers(response)
    try:
        payload = response.json() if response.status_code == 200 else None
    except Exception as error:
        return None, {
            "access_status": "REQUEST_ERROR",
            "attempts": 1,
            "retries": 0,
            "rate_limit_events": 0,
            "errors": [str(redact_secrets(f"JSON_ERROR:{error}", (api_key,)))],
            "safe_headers": safe,
        }
    if response.status_code == 200:
        return payload, {"access_status": "ACCESSIBLE", "attempts": 1, "retries": 0, "rate_limit_events": 0, "errors": [], "safe_headers": safe}
    return None, {
        "access_status": "RATE_LIMITED" if response.status_code == 429 else "REQUEST_ERROR",
        "attempts": 1,
        "retries": 0,
        "rate_limit_events": int(response.status_code == 429),
        "errors": [f"HTTP_{response.status_code}"],
        "safe_headers": safe,
    }


def _raw_response_shape(payload: object | None) -> dict[str, Any]:
    if payload is None:
        return {"payload_type": None, "top_level_keys": [], "content_keys": [], "candle_count": 0}
    body = _unwrap(payload)
    candles = body.get("candles") if isinstance(body, dict) else None
    return {
        "payload_type": type(payload).__name__,
        "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
        "content_keys": sorted(body.keys()) if isinstance(body, dict) else [],
        "candle_count": len(candles) if isinstance(candles, list) else 0,
        "symbol": body.get("symbol") if isinstance(body, dict) else None,
        "exchange": body.get("exchange") if isinstance(body, dict) else None,
        "market": body.get("market") if isinstance(body, dict) else None,
    }


def _classify_remediation(audit: pd.DataFrame, status: pd.DataFrame) -> pd.DataFrame:
    data = audit.copy()
    history = {
        normalise_ticker(row.ticker): (
            pd.Timestamp(row.min_date).normalize() if pd.notna(row.min_date) else None,
            pd.Timestamp(row.max_date).normalize() if pd.notna(row.max_date) else None,
            str(row.status),
        )
        for row in status.itertuples(index=False)
    }
    classes: list[str] = []
    reasons: list[str] = []
    for row in data.itertuples(index=False):
        if row.admission_status == "ADMISSIBLE_OPEN_EVIDENCE":
            classes.append("TV_RECOVERY_CANDIDATE")
            reasons.append("EXACT_HLC_POSITIVE_IN_RANGE_OPEN")
            continue
        if row.diagnostic == "NO_PROVIDER_ROW":
            min_date, max_date, current_status = history.get(normalise_ticker(row.ticker), (None, None, "NO_STATUS"))
            if current_status == "SUCCESS" and min_date is not None and max_date is not None and not (min_date <= row.date <= max_date):
                classes.append("TV_HISTORY_WINDOW_UNAVAILABLE")
                reasons.append("TARGET_DATE_OUTSIDE_RETURNED_1000_CANDLE_WINDOW")
            else:
                classes.append("TV_IDENTITY_OR_PROVIDER_ERROR")
                reasons.append("NO_REMEDIATION_PROVIDER_ROW")
        elif row.hlc_exact:
            classes.append("TV_PANEL_HLC_MATCH_OPEN_REJECTED")
            reasons.append(str(row.diagnostic))
        else:
            classes.append("TV_HLC_DISAGREEMENT")
            reasons.append(str(row.diagnostic))
    data["remediation_class"] = classes
    data["remediation_reason"] = reasons
    return data


def run_identity_remediation(
    *,
    output_dir: str | Path = OUTPUT_ROOT,
    target_audit_path: str | Path = TARGET_AUDIT_PATH,
    target_status_path: str | Path = TARGET_STATUS_PATH,
    api_key: str | None = None,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    panel_before = sha256_file(PANEL_PATH)
    if panel_before != EXPECTED_PANEL_SHA256:
        raise RuntimeError(f"Immutable panel SHA mismatch: {panel_before}")
    derivative_before = {name: sha256_file(DERIVATIVE_ROOT / name) for name in DERIVATIVE_FILES}
    target, target_meta = _load_frozen_target(target_audit_path)
    prior_status, prior_status_meta = _load_status(target_status_path)
    identity_rows, identity_meta = _load_identity_evidence()
    yahoo_status = pd.read_csv(YAHOO_STATUS_PATH)
    yahoo_status["ticker"] = yahoo_status["ticker"].map(normalise_ticker)
    yahoo_evidence = yahoo_status[yahoo_status["ticker"].isin(TARGET_TICKERS)].to_dict("records")
    prior_raw = _load_raw_error_status(TARGET_RAW_PATH, set(TARGET_TICKERS))
    prior_raw.update({key: value for key, value in _load_raw_error_status(RESUME_RAW_PATH, set(TARGET_TICKERS)).items() if key not in prior_raw})
    if "FREN" not in prior_raw:
        prior_raw["FREN"] = {
            "ticker": "FREN",
            "http_status": FREN_FALLBACK_HTTP_STATUS,
            "errors": ["HTTP_404"],
            "source_path": str(FREN_STATUS_EVIDENCE),
            "source_sha256": sha256_file(FREN_STATUS_EVIDENCE),
            "raw_record_present": False,
        }
    _write_csv(target, output / "frozen_identity_provider_target_rows.csv")
    _write_json(
        {
            "target_source": target_meta,
            "target_status_source": prior_status_meta,
            "target_rows_file_sha256": sha256_file(output / "frozen_identity_provider_target_rows.csv"),
            "target_status_records": prior_status_meta["records"],
        },
        output / "target_input_provenance.json",
    )
    _write_json({"identity_rows": identity_rows, "evidence_sources": identity_meta, "yahoo_provider_status": yahoo_evidence, "yahoo_status_path": str(YAHOO_STATUS_PATH), "yahoo_status_sha256": sha256_file(YAHOO_STATUS_PATH), "prior_tradingview_error_status": prior_raw}, output / "offline_identity_evidence.json")
    raw_path = output / "tradingview_remediation_raw_responses.jsonl"
    raw_path.write_text("", encoding="utf-8")
    api_key_value = api_key if api_key is not None else os.environ.get("ZAPI_API_KEY", "")
    new_provider = _empty_provider_frame()
    new_status = pd.DataFrame([{"ticker": RETRY_TICKER, "status": "NOT_ATTEMPTED", "min_date": None, "max_date": None, "rows": 0}])
    network = {"logical_requests": 0, "http_attempts": 0, "retries": 0, "rate_limit_events": 0, "request_errors": [], "retry_ticker": RETRY_TICKER, "retry_performed": False, "credential_present": bool(api_key_value), "response_shape": None}
    if api_key_value:
        session = requests.Session()
        network["logical_requests"] = 1
        payload, meta = _request_once(session, RETRY_TICKER, api_key_value)
        network["http_attempts"] = int(meta.get("attempts", 0))
        network["retries"] = int(meta.get("retries", 0))
        network["rate_limit_events"] = int(meta.get("rate_limit_events", 0))
        network["request_errors"] = list(meta.get("errors", []))
        network["retry_performed"] = True
        network["response_shape"] = _raw_response_shape(payload)
        _append_raw(
            raw_path,
            {
                "requested_ticker": RETRY_TICKER,
                "retry_reason": "prior HTTP 520",
                "request": {"endpoint": TRADINGVIEW_ENDPOINT, "params": {"symbol": "IDX:SMBR", "market": "indonesia", "resolution": "1D", "count": 1000}},
                "meta": meta,
                "safe_headers": meta.get("safe_headers", {}),
                "response": payload,
            },
            api_key_value,
        )
        if payload is not None:
            new_provider, status_row = _parse_payload(RETRY_TICKER, payload, "IDENTITY_REMEDIATION_SMBR_RETRY")
            new_status = pd.DataFrame([{"ticker": RETRY_TICKER, **status_row}])
        else:
            new_status = pd.DataFrame([{"ticker": RETRY_TICKER, "status": "RATE_LIMITED" if meta.get("rate_limit_events") else "REQUEST_ERROR", "min_date": None, "max_date": None, "rows": 0}])
    else:
        network["request_errors"] = ["ZAPI_BLOCKED_CREDENTIAL_ABSENT"]

    audit_input = _build_audit_input(target)
    audit_raw, audit_summary = audit_provider_rows(audit_input, new_provider, "ZAPI_TRADINGVIEW_IDENTITY_REMEDIATION")
    remediation_audit = _classify_remediation(audit_raw, new_status)
    _write_csv(new_provider, output / "tradingview_remediation_rows.csv")
    _write_csv(new_status, output / "tradingview_remediation_ticker_status.csv")
    _write_csv(remediation_audit, output / "tradingview_remediation_row_audit.csv")
    panel_after = sha256_file(PANEL_PATH)
    derivative_after = {name: sha256_file(DERIVATIVE_ROOT / name) for name in DERIVATIVE_FILES}
    if panel_after != panel_before or derivative_after != derivative_before:
        raise RuntimeError("Panel or accepted derivative changed during identity remediation")
    unresolved = remediation_audit[~remediation_audit["remediation_class"].eq("TV_RECOVERY_CANDIDATE")]
    summary = {
        "status": "TRADINGVIEW_IDENTITY_REMEDIATION_COMPLETE" if api_key_value else "ZAPI_BLOCKED_CREDENTIAL_ABSENT",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "frozen_target": target_meta,
        "preserved_prior_status": prior_status_meta,
        "identity_evidence": identity_meta,
        "identity_rows": identity_rows,
        "aliases_tested": [],
        "alias_request_justification": "No explicit historical/current ticker alias relationship was found in preserved project evidence; no alternate symbol request was made.",
        "canonical_retry": {"ticker": RETRY_TICKER, "symbol": "IDX:SMBR", "authorized_reason": "prior HTTP 520", "request_contract": EXPECTED_CONTRACT},
        "network": network,
        "remediation": {
            "target_rows": int(len(target)),
            "exact_ticker_date_coverage": int(remediation_audit["diagnostic"].ne("NO_PROVIDER_ROW").sum()),
            "exact_certified_hlc_count": int(remediation_audit["hlc_exact"].fillna(False).sum()),
            "admissible_open_candidates": int(remediation_audit["admission_status"].eq("ADMISSIBLE_OPEN_EVIDENCE").sum()),
            "resolved_candidate_rows": int(remediation_audit["remediation_class"].eq("TV_RECOVERY_CANDIDATE").sum()),
            "unresolved_rows": int(len(unresolved)),
            "unresolved_by_reason_ticker": [
                {str(key): (None if pd.isna(value) else value) for key, value in row.items()}
                for row in unresolved.groupby(["ticker", "remediation_class", "remediation_reason"], dropna=False, sort=True).size().reset_index(name="rows").to_dict("records")
            ],
            "rejection_breakdown": audit_summary["rejection_breakdown"],
        },
        "immutable_panel_sha256_before": panel_before,
        "immutable_panel_sha256_after": panel_after,
        "immutable_panel_unchanged": panel_before == panel_after == EXPECTED_PANEL_SHA256,
        "derivative_sha256_before": derivative_before,
        "derivative_sha256_after": derivative_after,
        "derivative_unchanged": derivative_before == derivative_after,
        "execution_grade_promoted": False,
        "panel_write_performed": False,
        "derivative_write_performed": False,
        "history_window_bucket_touched": False,
        "hlc_disagreement_bucket_touched": False,
        "corporate_action_bucket_touched": False,
        "alternate_provider_called": False,
        "artifact_manifest_excludes_summary_and_manifest": True,
    }
    _write_json(summary, output / "tradingview_identity_remediation_summary.json")
    data_files = sorted(path for path in output.iterdir() if path.is_file() and path.name not in {"artifact_manifest.json", "tradingview_identity_remediation_summary.json"})
    manifest = {"runtime": "tradingview_identity_provider_remediation_v1_20260812", "files": {path.name: sha256_file(path) for path in data_files}}
    _write_json(manifest, output / "artifact_manifest.json")
    summary["artifact_hashes"] = manifest["files"]
    summary["artifact_manifest_sha256"] = sha256_file(output / "artifact_manifest.json")
    _write_json(summary, output / "tradingview_identity_remediation_summary.json")
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Frozen TradingView identity/provider remediation audit")
    parser.add_argument("--output-dir", default=str(OUTPUT_ROOT))
    return parser


if __name__ == "__main__":
    print(json.dumps(run_identity_remediation(output_dir=_parser().parse_args().output_dir), ensure_ascii=False, indent=2, sort_keys=True, default=str))
