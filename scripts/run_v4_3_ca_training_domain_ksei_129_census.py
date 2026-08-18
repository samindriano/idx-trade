"""Acquire exact official-KSEI CA history for the frozen V4-3 historical 129.

This is a bounded, outcome-blind expansion of the already accepted KSEI CA
coverage domain.  The exact 129 ticker identities are read from the previously
emitted blocked V4-3 CA training-domain gate and hash-checked before any network
call.  The runner reuses the unchanged strict KSEI registered-security parser
and the same curl_cffi transport policy used by the accepted KSEI gap recovery.

No return, target/rank, model, prediction, performance, or protected-forward
artifact is read or produced.  The output is a delta only; the accepted parent
611-ticker census remains immutable until a separate offline merge/replay step.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = Path(__file__).resolve().parent
for value in (SRC_ROOT, SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from idx_trade.v4_ksei_ca_history import MECHANICAL_FAMILIES, is_active_status
from idx_trade.v4_ksei_coverage_gap import (
    sha256_bytes,
    sha256_file,
    ticker_identity_sha256,
    write_jsonl,
)
from run_v4_ksei_coverage_gap_remediation import (
    date_bounds,
    failure_class,
    recover_ticker,
    utc_now,
)


DEFAULT_CONFIG = Path("config/v4_3_ca_training_domain_ksei_129_v1.json")


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def load_config(path: Path) -> dict[str, Any]:
    value = read_json(path, "CONFIG")
    if value.get("schema_version") != "v4_3_ca_training_domain_ksei_129_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if value.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    return value


def verify_blocked_gate(root: Path, config: dict[str, Any]) -> tuple[dict[str, Any], list[str], dict[str, str]]:
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    blocked = config["blocked_training_gate"]
    expected_manifest = str(blocked["manifest_sha256"])
    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected_manifest:
        raise RuntimeError(
            f"BLOCKED_GATE_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected_manifest}"
        )
    manifest = read_json(manifest_path, "BLOCKED_GATE_MANIFEST")
    summary = read_json(summary_path, "BLOCKED_GATE_SUMMARY")
    if manifest.get("status") != "V4_3_CA_TRAINING_DOMAIN_BLOCKED_REVIEW_REQUIRED":
        raise RuntimeError("BLOCKED_GATE_STATUS_CHANGED")
    if summary.get("status") != "V4_3_CA_TRAINING_DOMAIN_BLOCKED_REVIEW_REQUIRED":
        raise RuntimeError("BLOCKED_GATE_SUMMARY_STATUS_CHANGED")
    for key in (
        "historical_target_loaded",
        "historical_target_rank_materialized",
        "historical_model_fit",
        "historical_prediction_generated",
        "historical_performance_computed",
        "protected_forward_accessed",
        "provider_calls",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"BLOCKED_GATE_GUARDRAIL_CHANGED:{key}")

    outputs = manifest.get("output_hashes") or {}
    expected_summary = outputs.get("summary")
    if not expected_summary or sha256_file(summary_path) != expected_summary:
        raise RuntimeError("BLOCKED_GATE_SUMMARY_HASH_MISMATCH")

    diagnostics = summary.get("ca_diagnostics") or {}
    tickers = sorted(
        {
            str(value).upper().replace(".JK", "").strip()
            for value in diagnostics.get("coverage_missing_historical_ticker_list") or []
        }
    )
    expected_count = int(blocked["expected_missing_tickers"])
    if len(tickers) != expected_count:
        raise RuntimeError(f"HISTORICAL_129_COUNT_CHANGED:{len(tickers)}")
    if any(len(ticker) != 4 for ticker in tickers):
        raise RuntimeError("HISTORICAL_129_TICKER_FORMAT_INVALID")
    expected_identity = str(blocked["missing_ticker_identity_sha256"])
    actual_identity = ticker_identity_sha256(tickers)
    if actual_identity != expected_identity:
        raise RuntimeError(
            f"HISTORICAL_129_IDENTITY_CHANGED:{actual_identity}!={expected_identity}"
        )
    return summary, tickers, {
        "blocked_gate_manifest": actual_manifest,
        "blocked_gate_summary": sha256_file(summary_path),
        "historical_129_identity": actual_identity,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocked-gate-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    config = load_config(args.config)
    provider = config["provider"]
    hard = config["hard_boundaries"]
    if provider.get("source_substitution") is not False:
        raise RuntimeError("SOURCE_SUBSTITUTION_NOT_ALLOWED")
    if provider.get("parser_relaxation") is not False:
        raise RuntimeError("PARSER_RELAXATION_NOT_ALLOWED")
    if provider.get("fresh_session_per_ticker") is not True:
        raise RuntimeError("FRESH_SESSION_POLICY_CHANGED")
    if provider.get("home_warmup_per_ticker") is not True:
        raise RuntimeError("HOME_WARMUP_POLICY_CHANGED")
    if hard.get("acquire_exact_129_only") is not True:
        raise RuntimeError("EXACT_129_SCOPE_NOT_FROZEN")
    for key in (
        "full_parent_recrawl",
        "alternate_provider",
        "alternate_ksei_security_identity",
        "parser_or_semantic_relaxation",
        "target_or_rank_materialization",
        "model_fit",
        "prediction",
        "performance",
        "protected_forward_access",
    ):
        if hard.get(key) is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")

    blocked_summary, tickers, input_hashes = verify_blocked_gate(
        args.blocked_gate_root, config
    )

    args.output_dir.mkdir(parents=True)
    raw_root = args.output_dir / "raw"
    raw_root.mkdir()

    coverage_rows: list[dict[str, Any]] = []
    history_rows: list[dict[str, Any]] = []
    request_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []

    for index, ticker in enumerate(tickers, start=1):
        success, records, parsed_rows = recover_ticker(
            ticker=ticker,
            provider=provider,
            raw_root=raw_root,
        )
        request_rows.extend(records)
        earliest, latest = date_bounds(parsed_rows)
        active_rows = [row for row in parsed_rows if is_active_status(row["status"])]
        active_mechanical = [
            row
            for row in active_rows
            if row["event_family"] in MECHANICAL_FAMILIES
        ]
        active_unknown = [
            row for row in active_rows if row["event_family"] == "UNKNOWN"
        ]
        certified = success is not None
        security_records = [
            row for row in records if row.get("request_kind") == "SECURITY_HISTORY"
        ]
        coverage_rows.append(
            {
                "ticker": ticker,
                "coverage_status": (
                    "COVERAGE_CERTIFIED" if certified else "COVERAGE_UNRESOLVED"
                ),
                "coverage_certified": certified,
                "attempt_count": len(security_records),
                "final_http_status": int(success["status_code"]) if success else 0,
                "source_url": (
                    success["final_url"]
                    if success
                    else str(provider["security_url_template"]).format(ticker=ticker)
                ),
                "source_sha256": success["sha256"] if success else None,
                "ca_rows": len(parsed_rows),
                "active_ca_rows": len(active_rows),
                "active_mechanical_rows": len(active_mechanical),
                "active_unknown_rows": len(active_unknown),
                "earliest_ca_date": earliest,
                "latest_ca_date": latest,
                "failure_reason": "" if certified else failure_class(records),
            }
        )
        result_rows.append(
            {
                "ticker": ticker,
                "coverage_certified": certified,
                "security_attempts": len(security_records),
                "ca_rows": len(parsed_rows),
                "active_mechanical_rows": len(active_mechanical),
                "active_unknown_rows": len(active_unknown),
                "failure_class": "" if certified else failure_class(records),
            }
        )
        history_rows.extend(parsed_rows)
        if index < len(tickers):
            sleep_seconds = float(provider.get("inter_ticker_sleep_seconds", 0.0))
            if sleep_seconds:
                time.sleep(sleep_seconds)

    coverage = pd.DataFrame(coverage_rows).sort_values("ticker", kind="mergesort")
    results = pd.DataFrame(result_rows).sort_values("ticker", kind="mergesort")
    if len(coverage) != 129 or coverage["ticker"].nunique() != 129:
        raise RuntimeError("HISTORICAL_129_COVERAGE_IDENTITY_CORRUPTED")
    if set(coverage["ticker"]) != set(tickers):
        raise RuntimeError("HISTORICAL_129_COVERAGE_TICKER_SET_CHANGED")

    coverage_path = args.output_dir / "ticker_coverage_delta_129.csv"
    history_path = args.output_dir / "ksei_ca_history_delta_129.jsonl"
    request_path = args.output_dir / "request_records_delta_129.jsonl"
    results_path = args.output_dir / "recovery_results_129.csv"
    coverage.to_csv(coverage_path, index=False, lineterminator="\n")
    write_jsonl(history_path, history_rows)
    write_jsonl(request_path, request_rows)
    results.to_csv(results_path, index=False, lineterminator="\n")

    certified = int(coverage["coverage_certified"].sum())
    unresolved = int((~coverage["coverage_certified"]).sum())
    unresolved_tickers = coverage.loc[
        ~coverage["coverage_certified"], "ticker"
    ].tolist()
    failure_counts = Counter(
        coverage.loc[~coverage["coverage_certified"], "failure_reason"].astype(str)
    )
    status = (
        "V4_3_CA_TRAINING_DOMAIN_KSEI_129_CENSUS_COMPLETE"
        if unresolved == 0
        else "V4_3_CA_TRAINING_DOMAIN_KSEI_129_CENSUS_COMPLETE_WITH_GAPS"
    )
    summary = {
        "schema_version": "v4_3_ca_training_domain_ksei_129_census_v1",
        "status": status,
        "outcome_blind": True,
        "provider": provider["name"],
        "provider_calls": True,
        "network_calls": True,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "scientific_config_changed": False,
        "ticker_count": len(tickers),
        "ticker_identity_sha256": ticker_identity_sha256(tickers),
        "coverage_certified_tickers": certified,
        "coverage_unresolved_tickers": unresolved,
        "coverage_unresolved_ticker_list": unresolved_tickers,
        "history_rows": len(history_rows),
        "failure_class_counts": dict(sorted(failure_counts.items())),
        "parent_blocked_gate": {
            "decision_tickers": (blocked_summary.get("ca_diagnostics") or {}).get("decision_tickers"),
            "coverage_census_tickers": (blocked_summary.get("ca_diagnostics") or {}).get("coverage_census_tickers"),
            "coverage_missing_historical_tickers": (blocked_summary.get("ca_diagnostics") or {}).get("coverage_missing_historical_tickers"),
        },
        "transport": {
            "library": provider["transport_library"],
            "impersonate": provider["impersonate"],
            "fresh_session_per_ticker": provider["fresh_session_per_ticker"],
            "home_warmup_per_ticker": provider["home_warmup_per_ticker"],
            "max_security_attempts_per_ticker": provider["max_security_attempts_per_ticker"],
            "backoff_seconds": provider["backoff_seconds"],
            "timeout_seconds": provider["timeout_seconds"],
            "inter_ticker_sleep_seconds": provider["inter_ticker_sleep_seconds"],
            "source_substitution": False,
            "parser_relaxation": False,
        },
        "input_hashes": input_hashes,
        "next": "OFFLINE_MERGE_129_WITH_FINAL_CA_CENSUS_AND_REPLAY_TRAINING_DOMAIN_GATE",
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output_hashes = {
        "ticker_coverage_delta_129": sha256_file(coverage_path),
        "ksei_ca_history_delta_129": sha256_file(history_path),
        "request_records_delta_129": sha256_file(request_path),
        "recovery_results_129": sha256_file(results_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_ksei_129_manifest_v1",
        "created_at_utc": utc_now(),
        "status": status,
        "outcome_blind": True,
        "ticker_count": len(tickers),
        "ticker_identity_sha256": ticker_identity_sha256(tickers),
        "input_hashes": input_hashes,
        "output_hashes": output_hashes,
        "raw_capture_count": sum(
            1 for path in raw_root.rglob("*.html") if path.is_file()
        ),
        "raw_capture_bytes": sum(
            path.stat().st_size for path in raw_root.rglob("*.html") if path.is_file()
        ),
        "guardrails": {
            "target_or_rank_materialized": False,
            "model_fit": False,
            "prediction_generated": False,
            "performance_computed": False,
            "protected_forward_accessed": False,
            "scientific_config_changed": False,
            "source_substitution": False,
            "parser_relaxation": False
        }
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "status": status,
                "ticker_count": len(tickers),
                "coverage_certified_tickers": certified,
                "coverage_unresolved_tickers": unresolved,
                "coverage_unresolved_ticker_list": unresolved_tickers,
                "history_rows": len(history_rows),
                "failure_class_counts": dict(sorted(failure_counts.items())),
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "target_or_rank_materialized": False,
                "model_fit": False,
                "performance_computed": False,
                "protected_forward_accessed": False,
                "next": summary["next"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
