"""Run the bounded TradingView Open/price-path remediation lane."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from idx_trade.tradingview_open_price_path_remediation import extract_first_60m_pair_reconciliation, extract_preopen_reconciliation
from idx_trade.tradingview_open_session_semantics import sha256_file, summarize_live_response
from scripts.run_tradingview_open_session_semantics import live_plan, run_node, run_offline, write_artifact_manifest, write_json


EXPECTED_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
EXPECTED_ADMISSION_MANIFEST_SHA256 = "de7246e447a83b15c083d19a00808f13670d97f720bd1e28ce8756e02186e8ee"
EXPECTED_SESSION_MANIFEST_SHA256 = "91e0d1de66a4be0f513f0b69c860b06f3b3d072b4d66ff6ac5eddf6c661bff01"
EXPECTED_ACTIVITY_MANIFEST_SHA256 = "f8076b83e170eb6180fbe3c3896000f33894c13e679c31e426816d471b6c0864"


def _load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_inputs(config: dict[str, Any], config_path: Path, admission_root: Path, session_root: Path, panel: Path, activity_root: Path) -> dict[str, str]:
    actual_panel = sha256_file(panel)
    if actual_panel != EXPECTED_PANEL_SHA256:
        raise SystemExit(f"canonical panel SHA mismatch: {actual_panel}")
    stage1_manifest = admission_root / "artifact_manifest.json"
    activity_manifest = activity_root / "MANIFEST.json"
    for required in (stage1_manifest, activity_manifest, session_root / "live" / "summary.json"):
        if not required.exists():
            raise SystemExit(f"missing immutable input: {required}")
    stage1_hash = sha256_file(stage1_manifest)
    if stage1_hash != EXPECTED_ADMISSION_MANIFEST_SHA256:
        raise SystemExit(f"admission manifest SHA mismatch: {stage1_hash}")
    session_manifest = session_root / "artifact_manifest.json"
    session_hash = sha256_file(session_manifest)
    if session_hash != EXPECTED_SESSION_MANIFEST_SHA256:
        raise SystemExit(f"session-semantics manifest SHA mismatch: {session_hash}")
    activity_hash = sha256_file(activity_manifest)
    if activity_hash != EXPECTED_ACTIVITY_MANIFEST_SHA256:
        raise SystemExit(f"independent activity manifest SHA mismatch: {activity_hash}")
    return {
        "config_sha256": sha256_file(config_path),
        "stage1_manifest_sha256": stage1_hash,
        "session_manifest_sha256": session_hash,
        "stage1_live_summary_sha256": sha256_file(session_root / "live" / "summary.json"),
        "activity_manifest_sha256": activity_hash,
        "activity_resolution_sha256": sha256_file(activity_root / "normalized" / "resolution_195.csv"),
        "canonical_panel_sha256": actual_panel,
    }


def _prepare_preregistration(root: Path, config: dict[str, Any], inputs: dict[str, str]) -> None:
    path = root / "pre_network_preparation.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update({
        "schema": "idx-trade/tradingview-open-price-path-remediation-prenetwork-v1",
        "network_started": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "remediation_input_hashes": inputs,
        "independent_activity": config["independent_activity"],
        "offline_reconciliation": config["offline_reconciliation"],
        "live_probe": config["live_probe"],
        "boundaries": config["boundaries"],
    })
    write_json(path, payload)


def run_offline_mode(config_path: Path, admission_root: Path, session_root: Path, panel: Path, activity_root: Path, artifact_root: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    inputs = verify_inputs(config, config_path, admission_root, session_root, panel, activity_root)
    summary = run_offline(config_path, admission_root, panel, artifact_root)
    bars, reconciliation, reconciliation_summary = extract_preopen_reconciliation(
        session_root,
        admission_root,
        panel,
        config["offline_reconciliation"]["tickers"],
        config["offline_reconciliation"]["date"],
    )
    offline = artifact_root / "offline"
    bars.to_csv(offline / "preopen_bars_2026-07-01.csv", index=False)
    reconciliation.to_csv(offline / "open_reconciliation_2026-07-01.csv", index=False)
    summary.update({
        "schema": "idx-trade/tradingview-open-price-path-remediation-offline-v1",
        "network_calls": 0,
        "frozen_stage1_verdict": config["decision_rules"]["preserve_stage1_verdict"],
        "frozen_admission_verdict_unchanged": True,
        "input_hashes": inputs,
        "independent_activity_resolution": config["independent_activity"],
        "preopen_reconciliation": reconciliation_summary,
    })
    write_json(offline / "summary.json", summary)
    _prepare_preregistration(artifact_root, config, inputs)
    write_artifact_manifest(artifact_root)
    return summary


def run_live_mode(config_path: Path, admission_root: Path, session_root: Path, panel: Path, activity_root: Path, adapter: Path, artifact_root: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    inputs = verify_inputs(config, config_path, admission_root, session_root, panel, activity_root)
    prereg_path = artifact_root / "pre_network_preparation.json"
    if not prereg_path.exists():
        raise SystemExit("offline remediation preregistration is missing")
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("network_started"):
        raise SystemExit("network already marked started; refuse rerun")
    if prereg.get("remediation_input_hashes") != inputs:
        raise SystemExit("immutable remediation input hash changed after freeze")
    plan = live_plan(config)
    if len(plan) != int(config["live_probe"]["expected_requests"]):
        raise SystemExit("live plan count changed after freeze")
    prereg["network_started"] = True
    prereg["network_started_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(prereg_path, prereg)
    rows: list[dict[str, Any]] = []
    for position, request in enumerate(plan, start=1):
        raw_path = artifact_root / "raw" / "live" / f"{request['request_index']:04d}_{request['ticker']}_{request['date']}_{request['timeframe']}m_{request['session']}.json"
        response, stderr = run_node(adapter, request)
        payload = {"adapter_commit": config["upstream"]["mathieu_commit"], "request": request, "response": response, "adapter_stderr": stderr}
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        rows.append(summarize_live_response(request, response))
        print(json.dumps({"progress": f"{position}/{len(plan)}", **rows[-1]}, ensure_ascii=False), flush=True)
    frame = pd.DataFrame(rows)
    live_dir = artifact_root / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    live_summary_path = live_dir / "probe_summary.csv"
    frame.to_csv(live_summary_path, index=False)
    live_summary = {
        "schema": "idx-trade/tradingview-open-price-path-remediation-live-v1",
        "input_hashes": inputs,
        "upstream_commit": config["upstream"]["mathieu_commit"],
        "requests": len(plan),
        "status_counts": {str(k): int(v) for k, v in frame["status"].value_counts(dropna=False).items()},
        "preopen_rows": int((frame["preopen_bar_count"].fillna(0) > 0).sum()),
        "regular_preopen_rows": int(((frame["session"] == "regular") & (frame["preopen_bar_count"].fillna(0) > 0)).sum()),
        "extended_preopen_rows": int(((frame["session"] == "extended") & (frame["preopen_bar_count"].fillna(0) > 0)).sum()),
        "frozen_stage1_verdict": config["decision_rules"]["preserve_stage1_verdict"],
        "frozen_admission_verdict_unchanged": True,
        "panel_sha256_after": sha256_file(panel),
        "probe_contract": config["live_probe"],
    }
    # probe_summary.csv was written above; the JSON summary is separate.
    live_summary_json_path = live_dir / "summary.json"
    write_json(live_summary_json_path, live_summary)
    live_summary.update({
        "remediation_input_hashes": inputs,
        "independent_activity_resolution": config["independent_activity"],
        "offline_reconciliation_summary": json.loads((artifact_root / "offline" / "summary.json").read_text(encoding="utf-8")).get("preopen_reconciliation"),
    })
    write_json(live_summary_json_path, live_summary)
    # The manifest hashes the summary; do not put the manifest hash back into
    # the summary itself, which would create a self-referential hash.
    write_artifact_manifest(artifact_root)
    return live_summary


def finalize_live_from_raw(config_path: Path, admission_root: Path, session_root: Path, panel: Path, activity_root: Path, artifact_root: Path) -> dict[str, Any]:
    """Finalize an already-started one-shot run without making network calls."""

    config = _load_config(config_path)
    inputs = verify_inputs(config, config_path, admission_root, session_root, panel, activity_root)
    prereg_path = artifact_root / "pre_network_preparation.json"
    if not prereg_path.exists():
        raise SystemExit("network preregistration is missing")
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("network_started") is not True:
        raise SystemExit("network has not been marked started")
    plan = live_plan(config)
    rows: list[dict[str, Any]] = []
    raw_dir = artifact_root / "raw" / "live"
    for request in plan:
        raw_path = raw_dir / f"{request['request_index']:04d}_{request['ticker']}_{request['date']}_{request['timeframe']}m_{request['session']}.json"
        if not raw_path.exists():
            raise SystemExit(f"missing raw response; refusing finalization: {raw_path.name}")
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        if payload.get("request") != request:
            raise SystemExit(f"raw request mismatch; refusing finalization: {raw_path.name}")
        rows.append(summarize_live_response(request, payload.get("response") or {}))
    frame = pd.DataFrame(rows)
    live_dir = artifact_root / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(live_dir / "probe_summary.csv", index=False)
    pair = extract_first_60m_pair_reconciliation(
        artifact_root,
        admission_root,
        panel,
        config["live_probe"]["tickers"],
        config["live_probe"]["dates"],
    )
    pair.to_csv(live_dir / "first_60m_pair_reconciliation.csv", index=False)
    summary = {
        "schema": "idx-trade/tradingview-open-price-path-remediation-live-v1",
        "input_hashes": inputs,
        "upstream_commit": config["upstream"]["mathieu_commit"],
        "requests": len(plan),
        "status_counts": {str(k): int(v) for k, v in frame["status"].value_counts(dropna=False).items()},
        "preopen_rows": int((frame["preopen_bar_count"].fillna(0) > 0).sum()),
        "regular_preopen_rows": int(((frame["session"] == "regular") & (frame["preopen_bar_count"].fillna(0) > 0)).sum()),
        "extended_preopen_rows": int(((frame["session"] == "extended") & (frame["preopen_bar_count"].fillna(0) > 0)).sum()),
        "frozen_stage1_verdict": config["decision_rules"]["preserve_stage1_verdict"],
        "frozen_admission_verdict_unchanged": True,
        "panel_sha256_after": sha256_file(panel),
        "probe_contract": config["live_probe"],
        "remediation_input_hashes": inputs,
        "independent_activity_resolution": config["independent_activity"],
        "offline_reconciliation_summary": json.loads((artifact_root / "offline" / "summary.json").read_text(encoding="utf-8")).get("preopen_reconciliation"),
        "network_finalization": "raw_responses_reused_after_post-request_local_write_failure; zero additional calls",
        "first_60m_pair_reconciliation": {
            "rows": int(len(pair)),
            "available_pairs": int(len(pair)),
            "extended60_open_equals_official_open": int(pair["extended60_open_equals_official_open"].sum()) if not pair.empty else 0,
            "regular60_open_equals_official_open": int(pair["regular60_open_equals_official_open"].sum()) if not pair.empty else 0,
            "extended60_open_equals_tv1d_open": int(pair["extended60_open_equals_tv1d_open"].sum()) if not pair.empty else 0,
            "regular60_open_equals_tv1d_open": int(pair["regular60_open_equals_tv1d_open"].sum()) if not pair.empty else 0,
            "official_open_inside_extended60_hl": int(pair["official_open_inside_extended60_hl"].sum()) if not pair.empty else 0,
            "mean_extended60_open_diff_bps_official": float(pair["extended60_open_diff_bps_official"].mean()) if not pair.empty else None,
            "mean_regular60_open_diff_bps_official": float(pair["regular60_open_diff_bps_official"].mean()) if not pair.empty else None,
            "mean_extended60_open_diff_bps_tv1d": float(pair["extended60_open_diff_bps_tv1d"].mean()) if not pair.empty else None,
            "mean_regular60_open_diff_bps_tv1d": float(pair["regular60_open_diff_bps_tv1d"].mean()) if not pair.empty else None,
        },
    }
    write_json(live_dir / "summary.json", summary)
    write_artifact_manifest(artifact_root)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["offline", "live", "finalize"], required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--admission-root", type=Path, required=True)
    parser.add_argument("--session-root", type=Path, required=True)
    parser.add_argument("--activity-root", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--adapter", type=Path)
    args = parser.parse_args()
    if args.mode == "offline":
        result = run_offline_mode(args.config, args.admission_root, args.session_root, args.panel, args.activity_root, args.artifact_root)
    elif args.mode == "live":
        if args.adapter is None:
            raise SystemExit("--adapter is required for live mode")
        result = run_live_mode(args.config, args.admission_root, args.session_root, args.panel, args.activity_root, args.adapter, args.artifact_root)
    else:
        result = finalize_live_from_raw(args.config, args.admission_root, args.session_root, args.panel, args.activity_root, args.artifact_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
