"""Run exactly five frozen TradingView V2.1 depth-preflight requests."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
from typing import Any

import pandas as pd

from idx_trade.tradingview_price_path_v2 import normalize_response, sha256_file
from idx_trade.tradingview_price_path_v2_1 import (
    artifact_manifest,
    depth_completion_status,
    directory_manifest,
    load_identity_intervals,
    map_identity_frame,
    serialize_v2_1_request,
    validate_structural_rows,
    verify_input_hashes,
    write_network_start_marker,
    write_streaming_artifact,
)


CONTROLS = ("BBCA", "BBRI", "BMRI", "TLKM", "ASII")
PANEL_SHA = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")


def run_node(adapter: Path, request: dict[str, Any]) -> dict[str, Any]:
    try:
        process = subprocess.run(["node", str(adapter), json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))], capture_output=True, text=True, timeout=float(request["timeout_ms"]) / 1000 + 12)
    except subprocess.TimeoutExpired:
        return {"status": "TRANSPORT_TIMEOUT", "errors": ["node subprocess timeout"], "periods": [], "event_trace": ["runner_timeout"], "fetch_more": {"completion_reason": "request_timeout", "steps": []}}
    if process.returncode != 0:
        return {"status": "TRANSPORT_ERROR", "errors": [process.stderr[-2000:]], "periods": [], "event_trace": ["runner_error"], "fetch_more": {"completion_reason": "provider_error", "steps": []}}
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError:
        return {"status": "TRANSPORT_ERROR", "errors": ["invalid adapter JSON"], "periods": [], "event_trace": ["invalid_json"], "fetch_more": {"completion_reason": "provider_error", "steps": []}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prereg-root", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--scope-exclusions", type=Path, required=True)
    parser.add_argument("--curated-identities", type=Path, required=True)
    args = parser.parse_args()
    if args.runtime_root.exists() and any(args.runtime_root.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty preflight root: {args.runtime_root}")
    args.runtime_root.mkdir(parents=True, exist_ok=True)

    prereg_path = args.prereg_root / "preregistration.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("network_authorized") is not False or prereg.get("network_calls") != 0:
        raise SystemExit("preregistration is not frozen pre-network state")
    prereg_sha = sha256_file(prereg_path)
    panel = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet")
    if sha256_file(panel) != PANEL_SHA:
        raise SystemExit("canonical panel SHA changed")
    repo_root = args.adapter.resolve().parents[2]
    current_paths = {
        "adapter": args.adapter,
        "config": repo_root / "config" / "tradingview_historical_price_path_v2_1.json",
        "curated_identities": args.curated_identities,
        "package_lock": args.adapter.parent / "package-lock.json",
        "scope_exclusions": args.scope_exclusions,
        "security_master": args.security_master,
    }
    current_hash_check = verify_input_hashes(current_paths, prereg["input_hashes"])
    if not current_hash_check["valid"]:
        raise SystemExit(f"decision-bearing input hash mismatch: {current_hash_check}")
    original_prereg_path = Path(prereg["existing_offline_artifact_root"]) / "preregistration.json"
    original_prereg = json.loads(original_prereg_path.read_text(encoding="utf-8"))
    original_paths = {name: Path(path) for name, path in original_prereg["input_paths"].items()}
    original_check = verify_input_hashes(original_paths, original_prereg["input_hashes"])
    if not original_check["valid"]:
        raise SystemExit(f"preserved offline input hash mismatch: {original_check}")
    actual_dir = directory_manifest(Path(prereg["canonical_fidelity_directory_manifest"]["root"]))
    if actual_dir["aggregate_sha256"] != prereg["canonical_fidelity_directory_manifest"]["aggregate_sha256"]:
        raise SystemExit("canonical fidelity directory manifest changed")
    archive_manifest = Path(r"D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1\archive_manifest.json")
    if sha256_file(archive_manifest) != prereg["official_stock_summary_archive_manifest_sha256"]:
        raise SystemExit("official Stock Summary archive manifest changed")

    session_path = Path(original_prereg["input_paths"]["official_sessions"])
    sessions = pd.read_csv(session_path)
    official_sessions = set(sessions["date"].astype(str).str[:10])
    intervals = load_identity_intervals(args.security_master, args.curated_identities, args.scope_exclusions)
    # Keep the preregistered Asia/Jakarta end-of-day epoch stable across hosts.
    end_epoch = 1785517199
    requests = []
    for index, ticker in enumerate(CONTROLS, start=1):
        request = {
            "request_index": index,
            "ticker": ticker,
            "symbol": f"IDX:{ticker}",
            "server": "prodata",
            "timeframe": "60",
            "session": "regular",
            "adjustment": "none",
            "to": end_epoch,
            "initial_range": 500,
            "fetch_more_batch": 5000,
            "fetch_more_steps": 3,
            "timeout_ms": 25000,
            "fetch_more_wait_ms": 8000,
            "required_start": "2021-04-01",
            "prior_session_start": "2021-03-31",
            "required_end": "2026-07-31",
            "adapter_commit": "5baea86c8c7e576f13464919c86c3b4c4b0ecf4c",
            "preregistration_sha256": prereg_sha,
        }
        # The schema validator intentionally sees only the provider contract;
        # metadata fields remain in the serialized request unchanged.
        serialize_v2_1_request(request)
        requests.append(request)
    write_json(args.runtime_root / "request_manifest.json", {"schema": "idx-trade/tradingview-price-path-v2-1-depth-preflight", "preregistration_sha256": prereg_sha, "requests": requests})
    write_network_start_marker(args.runtime_root / "network_start_marker.json", prereg_path, len(requests))

    results = []
    for request in requests:
        started = datetime.now().astimezone().isoformat()
        response = run_node(args.adapter, request)
        payload = {"schema": "idx-trade/tradingview-price-path-v2-1-preflight-raw", "adapter_commit": request["adapter_commit"], "preregistration_sha256": prereg_sha, "request": request, "response": response, "started_at_local": started}
        raw_path = args.runtime_root / "raw" / f"{request['request_index']:02d}_{request['ticker']}.json"
        raw_sha = write_streaming_artifact(raw_path, [json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"])
        frame, diag = normalize_response(response, request, official_sessions)
        mapped = map_identity_frame(frame, intervals) if not frame.empty else frame.assign(identity_status=pd.Series(dtype=str), mapped_security_id=pd.Series(dtype=str))
        normalized_path = args.runtime_root / "normalized" / f"{request['request_index']:02d}_{request['ticker']}.csv"
        normalized_path.parent.mkdir(parents=True, exist_ok=True)
        mapped.to_csv(normalized_path, index=False)
        earliest = str(mapped["session_date"].min()) if not mapped.empty else None
        latest = str(mapped["session_date"].max()) if not mapped.empty else None
        prior_reached = earliest is not None and earliest <= request["prior_session_start"]
        required_reached = earliest is not None and earliest <= request["required_start"]
        reason = (response.get("fetch_more") or {}).get("completion_reason") or response.get("depth_completion_status")
        depth_status = response.get("depth_completion_status")
        if depth_status not in {"REQUIRED_START_REACHED", "MAX_DEPTH_EXHAUSTED", "NO_EXTENSION", "TIMEOUT", "PROVIDER_ERROR", "NOT_APPLICABLE"}:
            depth_status = depth_completion_status(provider_data_status=str(response.get("status")), earliest_session=earliest, required_start=request["required_start"], prior_buffer_reached=prior_reached, extension_reason=reason)
        identity_counts = mapped.get("identity_status", pd.Series(dtype=str)).value_counts().to_dict()
        structural = {**diag, **validate_structural_rows(mapped)}
        result = {
            "ticker": request["ticker"],
            "provider_data_status": response.get("status"),
            "depth_completion_status": depth_status,
            "completion_reason": reason,
            "initial_bar_count": ((response.get("fetch_more") or {}).get("steps", [])[0].get("before_count")
                                  if (response.get("fetch_more") or {}).get("steps")
                                  else len(response.get("periods") or [])),
            "final_bar_count": len(response.get("periods") or []),
            "earliest_session": earliest,
            "latest_session": latest,
            "required_start_reached": required_reached,
            "prior_session_buffer_reached": prior_reached,
            "elapsed_ms": response.get("elapsed_ms"),
            "raw_bytes": raw_path.stat().st_size,
            "raw_sha256": raw_sha["sha256"],
            "normalized_bytes": normalized_path.stat().st_size,
            "structural": structural,
            "identity_counts": identity_counts,
            "boundary_status": "REQUIRED_START_REACHED" if required_reached and prior_reached else "BOUNDARY_INCOMPLETE",
            "fetch_more_steps": response.get("fetch_more", {}).get("steps", []),
            "errors": response.get("errors", []),
        }
        write_json(args.runtime_root / "normalized" / f"{request['request_index']:02d}_{request['ticker']}.json", result)
        results.append(result)
    passed = all(row["provider_data_status"] == "AVAILABLE" and row["depth_completion_status"] == "REQUIRED_START_REACHED" and row["boundary_status"] == "REQUIRED_START_REACHED" and row["identity_counts"].get("MAPPED", 0) == row["final_bar_count"] and all(row["structural"].get(key, 0) == 0 for key in ("malformed_rows", "invalid_ohlcv_rows", "duplicate_rows", "session_date_leakage_rows", "extended_preopen_contamination_rows")) for row in results)
    summary = {"schema": "idx-trade/tradingview-price-path-v2-1-depth-preflight-runtime", "preregistration_sha256": prereg_sha, "logical_request_count": len(results), "provider_requests_made": len(results), "passed": passed, "controls": results, "all_controls_pass": passed, "panel_sha256_before": PANEL_SHA, "panel_sha256_after": sha256_file(panel), "modeling_authorized": False, "protected_outcomes_accessed": False}
    write_json(args.runtime_root / "preflight_summary.json", summary)
    manifest = artifact_manifest(args.runtime_root, exclude={"runtime_artifact_manifest.json"})
    write_json(args.runtime_root / "runtime_artifact_manifest.json", manifest)
    print(json.dumps({"passed": passed, "provider_requests_made": len(results), "runtime_root": str(args.runtime_root), "manifest_sha256": manifest["manifest_sha256"], "controls": results}, indent=2, default=str))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
