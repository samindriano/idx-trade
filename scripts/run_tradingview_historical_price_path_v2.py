"""Execute the frozen V2 acquisition and write only external artifacts."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
from typing import Any

import pandas as pd

from idx_trade.tradingview_price_path_v2 import (
    aggregate_daily,
    evaluate_gates,
    fidelity_report,
    json_bytes,
    load_canonical,
    normalize_response,
    sha256_file,
)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def run_node(adapter: Path, request: dict[str, Any]) -> dict[str, Any]:
    try:
        proc = subprocess.run(["node", str(adapter), json.dumps(request, separators=(",", ":"))], capture_output=True, text=True, timeout=float(request["timeout_ms"]) / 1000 + 12)
    except subprocess.TimeoutExpired:
        return {"request": request, "status": "TRANSPORT_TIMEOUT", "errors": ["node subprocess timeout"], "periods": [], "event_trace": ["runner_timeout"]}
    if proc.returncode != 0:
        return {"request": request, "status": "TRANSPORT_ERROR", "errors": [proc.stderr[-2000:]], "periods": [], "event_trace": ["runner_error"]}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"request": request, "status": "TRANSPORT_ERROR", "errors": ["invalid adapter JSON"], "periods": [], "event_trace": ["invalid_json"]}


def artifact_manifest(root: Path) -> str:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            rows.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    target = root / "artifact_manifest.json"
    target.write_bytes(json_bytes({"schema": "idx-trade/tradingview-historical-price-path-v2-runtime-manifest", "artifacts": rows}))
    return sha256_file(target)


def load_and_verify_prereg(root: Path, config: Path, canonical_root: Path, allow_contract_repair: bool) -> dict[str, Any]:
    prereg_path = root / "preregistration.json"
    if not prereg_path.exists():
        raise SystemExit("missing preregistration.json")
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if not prereg.get("created_before_network"):
        raise SystemExit("preregistration is not an untouched pre-network manifest")
    if prereg.get("network_started") and not allow_contract_repair:
        raise SystemExit("runtime already started; use the explicit bounded contract-repair resume only for the documented invalid-parameter attempt")
    if prereg["input_hashes"]["config"] != sha256_file(config):
        raise SystemExit("config hash changed after preregistration")
    canonical_panel = Path(prereg.get("input_paths", {}).get("canonical_panel", ""))
    expected_panel_sha = prereg["input_hashes"].get("canonical_panel")
    if expected_panel_sha and canonical_panel.exists() and sha256_file(canonical_panel) != expected_panel_sha:
        raise SystemExit("canonical panel hash changed after preregistration")
    return prereg


def mark_network_started(root: Path, prereg: dict[str, Any]) -> None:
    prereg["network_started"] = True
    prereg["network_started_before_first_request"] = True
    (root / "preregistration.json").write_bytes(json_bytes(prereg))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument("--repair-contract-failure", action="store_true")
    args = parser.parse_args()
    prereg = load_and_verify_prereg(args.artifact_root, args.config, args.canonical_root, args.repair_contract_failure)
    config = prereg["config"]
    root = args.artifact_root
    requests = pd.read_csv(root / "request_manifest.csv").fillna("").to_dict(orient="records")
    for request in requests:
        request["timeframe"] = str(request["timeframe"])
        request["session"] = str(request["session"])
        request["adjustment"] = str(request["adjustment"])
        request["to"] = int(request["to"])
    raw_root = root / "raw" / "mathieu"
    raw_root.mkdir(parents=True, exist_ok=True)
    mark_network_started(root, prereg)
    results: dict[int, dict[str, Any]] = {}
    def one(request: dict[str, Any]) -> tuple[int, dict[str, Any], bool]:
        index = int(request["request_index"])
        path = raw_root / f"{index:04d}_{request['ticker']}.json"
        repair_path = raw_root / "repair_timeframe_contract" / f"{index:04d}_{request['ticker']}.json"
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing_response = existing.get("response", existing)
            invalid_parameters = any("invalid parameters" in str(error).lower() for error in existing_response.get("errors", []))
            if not args.repair_contract_failure or not invalid_parameters:
                return index, existing, True
            if repair_path.exists():
                return index, json.loads(repair_path.read_text(encoding="utf-8")), True
        response = run_node(args.adapter, request)
        payload = {"adapter_commit": config["provider"]["adapter_commit"], "request": request, "response": response}
        target = repair_path if args.repair_contract_failure and path.exists() else path
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".tmp")
        temp.write_bytes(json_bytes(payload))
        temp.replace(target)
        return index, payload, False
    with ThreadPoolExecutor(max_workers=int(config["acquisition"]["max_workers"])) as executor:
        futures = [executor.submit(one, request) for request in requests]
        for position, future in enumerate(as_completed(futures), start=1):
            index, payload, reused = future.result()
            results[index] = payload
            response = payload.get("response", payload)
            print(json.dumps({"progress": f"{position}/{len(requests)}", "request_index": index, "ticker": payload.get("request", {}).get("ticker"), "status": response.get("status"), "periods": len(response.get("periods") or []), "reused": reused}), flush=True)
    official_sessions = set(pd.read_csv(root / "official_sessions.csv")["date"].astype(str).str[:10])
    bar_frames, diagnostic_rows = [], []
    for index in sorted(results):
        payload = results[index]
        request = payload["request"]
        response = payload.get("response", payload)
        frame, diag = normalize_response(response, request, official_sessions)
        if not frame.empty:
            bar_frames.append(frame)
        diagnostic_rows.append({"request_index": index, "ticker": request["ticker"], "status": response.get("status"), "period_count": len(response.get("periods") or []), "elapsed_ms": response.get("elapsed_ms"), "event_trace": json.dumps(response.get("event_trace", [])), "websocket_connected": (response.get("event_observation") or {}).get("websocket_connected"), "completion_reason": response.get("completion_reason") or (response.get("fetch_more") or {}).get("completion_reason"), **diag})
    bars = pd.concat(bar_frames, ignore_index=True) if bar_frames else pd.DataFrame()
    diagnostics = pd.DataFrame(diagnostic_rows)
    daily = aggregate_daily(bars)
    activity = pd.read_csv(root / "activity_reconciliation.csv")
    canonical = load_canonical(args.canonical_root, activity["ticker"].unique())
    ca = pd.read_csv(root / "corporate_action_events.csv")
    matched, fidelity = fidelity_report(daily, activity, canonical, ca)
    gate = evaluate_gates(pd.read_csv(root / "expected_ticker_sessions.csv"), activity, bars, diagnostics, fidelity, config)
    status_counts = diagnostics["status"].value_counts(dropna=False).to_dict() if not diagnostics.empty else {}
    write_csv(root / "normalized" / "intraday_bars.csv", bars)
    write_csv(root / "normalized" / "daily_aggregates.csv", daily)
    write_csv(root / "normalized" / "request_diagnostics.csv", diagnostics)
    write_csv(root / "normalized" / "fidelity_rows.csv", matched)
    years = {}
    covered_keys = set(zip(bars.loc[bars.get("session_admissible", pd.Series(dtype=bool)) == True, "ticker"], bars.loc[bars.get("session_admissible", pd.Series(dtype=bool)) == True, "session_date"])) if not bars.empty else set()
    for year, group in activity.assign(year=activity["session_date"].str[:4]).groupby("year", sort=True):
        active = int((group["activity_state"] == "ACTIVE").sum())
        covered = int(sum(row.activity_state == "ACTIVE" and (row.ticker, row.session_date) in covered_keys for row in group.itertuples(index=False)))
        years[str(year)] = {"active_sessions": active, "covered_active_sessions": covered, "true_provider_misses": active - covered}
    required_structural = gate["gates"]["structural_integrity"] and gate["gates"]["activity_unknown"]
    if gate["all_gates_pass"]:
        verdict = "TRADINGVIEW_PRICE_PATH_V2_ADMITTED"
        bars[bars["session_admissible"]].to_parquet(root / "model_safe_price_path.parquet", index=False)
    elif not required_structural or gate["true_provider_misses"]:
        verdict = "TRADINGVIEW_PRICE_PATH_V2_REJECTED"
    else:
        verdict = "TRADINGVIEW_PRICE_PATH_V2_INCONCLUSIVE"
    summary = {"schema": "idx-trade/tradingview-historical-price-path-v2-runtime", "verdict": verdict, "provider_status_counts": status_counts, "gate": gate, "fidelity": fidelity, "by_year": years, "canonical_ticker_count": int(canonical["ticker"].nunique()) if not canonical.empty else 0, "canonical_panel_sha256_before": prereg["input_hashes"].get("canonical_panel"), "modeling_authorized": False, "protected_outcomes_accessed": False}
    (root / "runtime_summary.json").write_bytes(json_bytes(summary))
    digest = artifact_manifest(root)
    print(json.dumps({"verdict": verdict, "artifact_manifest_sha256": digest, "summary": summary}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
