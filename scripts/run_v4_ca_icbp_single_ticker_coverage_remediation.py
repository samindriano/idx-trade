"""Single-ticker official-KSEI retry for the residual ICBP V4 coverage gap.

The accepted 598/610 remediation root is immutable input.  This runner contacts
only the exact official ICBP registered-security URL through the already frozen
KSEI transport and parser.  No alias, alternate source, parser relaxation, or
other ticker is allowed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = Path(__file__).resolve().parent
for path in (SRC_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pandas as pd

import run_v4_ca_coverage_gap_continuity_replay as coverage_replay
import run_v4_ksei_coverage_gap_remediation as gap_runner
from idx_trade.v4_ca_icbp_single_ticker_remediation import (
    EXPECTED_OUTPUT_UNRESOLVED,
    TARGET_TICKER,
    build_certified_target_row,
    normalize_parent_coverage,
    parsed_history_stats,
    validate_output_coverage,
    validate_parent_history,
)
from idx_trade.v4_ksei_coverage_gap import (
    merge_coverage,
    merge_history,
    read_jsonl,
    sha256_file,
    write_jsonl,
)


EXPECTED_PARENT_MANIFEST_SHA256 = "7e86f5e52d7c2ff609ee9dd4be28ff1aefea1e4d5c7d7d9dbffb6abd07185f50"
EXPECTED_CONFIG_SHA256 = "a749749d799030a74baee0fb0e555f4df45fa86d"
DEFAULT_CONFIG = Path("config/v4_ksei_coverage_gap_remediation_v1.json")
EXPECTED_URL_TEMPLATE = "https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}?setLocale=en-US"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-remediation-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def validate_provider_config(path: Path) -> dict[str, Any]:
    if sha256_file(path) != EXPECTED_CONFIG_SHA256:
        raise RuntimeError("ICBP_PROVIDER_CONFIG_HASH_CHANGED")
    config = gap_runner.load_config(path)
    gaps = {str(value).upper().strip() for value in config.get("gap_tickers", [])}
    if TARGET_TICKER not in gaps:
        raise RuntimeError("ICBP_NOT_IN_FROZEN_ORIGINAL_GAP_SET")
    provider = config["provider"]
    if provider.get("security_url_template") != EXPECTED_URL_TEMPLATE:
        raise RuntimeError("ICBP_SECURITY_URL_TEMPLATE_CHANGED")
    if provider.get("source_substitution") is not False:
        raise RuntimeError("ICBP_SOURCE_SUBSTITUTION_FORBIDDEN")
    if provider.get("parser_relaxation") is not False:
        raise RuntimeError("ICBP_PARSER_RELAXATION_FORBIDDEN")
    if provider.get("fresh_session_per_ticker") is not True:
        raise RuntimeError("ICBP_FRESH_SESSION_POLICY_CHANGED")
    if provider.get("home_warmup_per_ticker") is not True:
        raise RuntimeError("ICBP_HOME_WARMUP_POLICY_CHANGED")
    if int(provider.get("max_security_attempts_per_ticker") or 0) != 2:
        raise RuntimeError("ICBP_MAX_SECURITY_ATTEMPTS_CHANGED")
    return config


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    parent_summary, parent_manifest_sha = coverage_replay.verify_remediation_root(
        args.parent_remediation_root
    )
    if parent_manifest_sha != EXPECTED_PARENT_MANIFEST_SHA256:
        raise RuntimeError(f"ICBP_PARENT_MANIFEST_SHA_MISMATCH:{parent_manifest_sha}")
    config = validate_provider_config(args.config)
    provider = config["provider"]

    parent_coverage_path = args.parent_remediation_root / "ticker_coverage.csv"
    parent_history_path = args.parent_remediation_root / "ksei_ca_history.jsonl"
    parent_requests_path = args.parent_remediation_root / "request_records.jsonl"
    parent_coverage = normalize_parent_coverage(pd.read_csv(parent_coverage_path))
    parent_history = read_jsonl(parent_history_path)
    validate_parent_history(parent_history)

    target_parent = parent_coverage[parent_coverage["ticker"].eq(TARGET_TICKER)].iloc[0].to_dict()

    # Only after every parent/config assertion passes do we consume the fresh root.
    args.output_dir.mkdir(parents=True)
    raw_root = args.output_dir / "raw"
    raw_root.mkdir()

    success, request_delta, parsed_rows = gap_runner.recover_ticker(
        ticker=TARGET_TICKER,
        provider=provider,
        raw_root=raw_root,
    )
    request_delta_path = args.output_dir / "request_delta.jsonl"
    write_jsonl(request_delta_path, request_delta)

    if success is None:
        failure = {
            "schema_version": "v4_ca_icbp_single_ticker_coverage_remediation_v1",
            "status": "V4_CA_ICBP_SINGLE_TICKER_COVERAGE_REMEDIATION_FAILED_CLOSED",
            "outcome_blind": True,
            "provider_calls": True,
            "target_ticker": TARGET_TICKER,
            "source_substitution": False,
            "parser_relaxation": False,
            "full_610_recrawl": False,
            "parent_manifest_sha256": parent_manifest_sha,
            "request_count": len(request_delta),
            "failure_class": gap_runner.failure_class(request_delta),
            "output_hashes": {"request_delta": sha256_file(request_delta_path)},
        }
        summary_path = args.output_dir / "summary.json"
        summary_path.write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest = {
            "schema_version": "v4_ca_icbp_single_ticker_coverage_remediation_manifest_v1",
            "status": failure["status"],
            "outcome_blind": True,
            "summary_sha256": sha256_file(summary_path),
            "output_hashes": failure["output_hashes"],
        }
        (args.output_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(failure, indent=2, sort_keys=True))
        return 2

    stats = parsed_history_stats(parsed_rows)
    security_records = [
        row for row in request_delta if row.get("request_kind") == "SECURITY_HISTORY"
    ]
    replacement = build_certified_target_row(
        target_parent,
        success_record=success,
        security_attempt_count=len(security_records),
        stats=stats,
    )
    remediation = pd.DataFrame([replacement], columns=parent_coverage.columns)
    remediation["coverage_certified"] = remediation["coverage_certified"].astype(bool)
    merged_coverage = merge_coverage(
        parent_coverage,
        remediation,
        gap_tickers=[TARGET_TICKER],
    )
    merged_coverage = validate_output_coverage(merged_coverage)
    merged_history = merge_history(
        parent_history,
        parsed_rows,
        gap_tickers=[TARGET_TICKER],
    )

    coverage_path = args.output_dir / "ticker_coverage.csv"
    history_path = args.output_dir / "ksei_ca_history.jsonl"
    requests_path = args.output_dir / "request_records.jsonl"
    merged_coverage.to_csv(coverage_path, index=False, lineterminator="\n")
    write_jsonl(history_path, merged_history)
    parent_requests = read_jsonl(parent_requests_path) if parent_requests_path.is_file() else []
    write_jsonl(requests_path, [*parent_requests, *request_delta])

    summary = {
        "schema_version": "v4_ca_icbp_single_ticker_coverage_remediation_v1",
        "status": "V4_CA_ICBP_SINGLE_TICKER_COVERAGE_REMEDIATION_COMPLETE",
        "outcome_blind": True,
        "provider_calls": True,
        "provider_calls_in_continuity_replay": False,
        "target_ticker": TARGET_TICKER,
        "source_substitution": False,
        "parser_relaxation": False,
        "full_610_recrawl": False,
        "alternate_provider": False,
        "parent_manifest_sha256": parent_manifest_sha,
        "parent_summary_sha256": sha256_file(args.parent_remediation_root / "summary.json"),
        "parent_coverage_sha256": sha256_file(parent_coverage_path),
        "parent_history_sha256": sha256_file(parent_history_path),
        "provider_config_sha256": sha256_file(args.config),
        "provider_security_url": EXPECTED_URL_TEMPLATE.format(ticker=TARGET_TICKER),
        "security_attempts": len(security_records),
        "request_count": len(request_delta),
        "source_sha256": str(success["sha256"]),
        "parsed_history": stats,
        "merged_coverage_certified_tickers": 599,
        "remaining_unresolved_ticker_count": len(EXPECTED_OUTPUT_UNRESOLVED),
        "remaining_unresolved_tickers": sorted(EXPECTED_OUTPUT_UNRESOLVED),
        "merged_history_rows": len(merged_history),
        "output_hashes": {},
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["output_hashes"] = {
        "ticker_coverage": sha256_file(coverage_path),
        "ksei_ca_history": sha256_file(history_path),
        "request_records": sha256_file(requests_path),
        "request_delta": sha256_file(request_delta_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ca_icbp_single_ticker_coverage_remediation_manifest_v1",
        "status": summary["status"],
        "outcome_blind": True,
        "summary_sha256": sha256_file(summary_path),
        "parent_manifest_sha256": parent_manifest_sha,
        "output_hashes": summary["output_hashes"],
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
