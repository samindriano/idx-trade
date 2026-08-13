"""Run the offline-first TradingView Open/session-semantics forensic audit."""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
import json
from pathlib import Path
import subprocess
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from idx_trade.tradingview_open_session_semantics import (
    REQUIRED_PANEL_SHA256,
    REQUIRED_UPSTREAM_COMMIT,
    build_session_forensics,
    classify_live_probe,
    inspect_market_info,
    json_bytes,
    offline_summary,
    sha256_file,
    summarize_live_response,
)


UTC = timezone.utc
WIB = ZoneInfo("Asia/Jakarta")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def end_epoch(day: date) -> int:
    return int(datetime.combine(day, time(23, 59, 59), tzinfo=WIB).timestamp())


def run_node(adapter: Path, request: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    try:
        completed = subprocess.run(
            ["node", str(adapter), json.dumps(request, separators=(",", ":"))],
            capture_output=True,
            text=True,
            timeout=float(request["timeout_ms"]) / 1000 + 15,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "request": request,
            "server": request["server"],
            "status": "TRANSPORT_TIMEOUT",
            "errors": ["runner subprocess timeout"],
            "periods": [],
            "event_trace": ["runner_timeout"],
        }, str(exc)
    if completed.returncode != 0:
        return {
            "request": request,
            "server": request["server"],
            "status": "TRANSPORT_ERROR",
            "errors": [completed.stderr[-2000:]],
            "periods": [],
            "event_trace": ["runner_error"],
        }, completed.stderr[-2000:]
    try:
        return json.loads(completed.stdout), completed.stderr[-2000:] if completed.stderr else None
    except json.JSONDecodeError:
        return {
            "request": request,
            "server": request["server"],
            "status": "TRANSPORT_ERROR",
            "errors": ["invalid adapter JSON"],
            "periods": [],
            "event_trace": ["invalid_json"],
        }, completed.stdout[-2000:]


def verify_inputs(config: Path, admission_root: Path, panel: Path) -> dict[str, Any]:
    cfg = json.loads(config.read_text(encoding="utf-8"))
    if cfg["upstream"]["mathieu_commit"] != REQUIRED_UPSTREAM_COMMIT:
        raise SystemExit("unexpected Mathieu upstream commit")
    actual_panel = sha256_file(panel)
    if actual_panel != REQUIRED_PANEL_SHA256:
        raise SystemExit(f"canonical panel SHA mismatch: {actual_panel}")
    artifact_manifest = admission_root / "artifact_manifest.json"
    if not artifact_manifest.exists():
        raise SystemExit("admission artifact manifest missing")
    return {
        "config_sha256": sha256_file(config),
        "admission_artifact_manifest_sha256": sha256_file(artifact_manifest),
        "admission_daily_comparison_sha256": sha256_file(admission_root / "normalized" / "daily_comparison.csv"),
        "admission_tv1d_comparison_sha256": sha256_file(admission_root / "normalized" / "tv1d_comparison.csv"),
        "admission_mathieu_bars_sha256": sha256_file(admission_root / "normalized" / "mathieu_intraday_bars.csv"),
        "admission_request_manifest_sha256": sha256_file(admission_root / "normalized" / "mathieu_request_manifest.csv"),
        "canonical_panel_sha256": actual_panel,
    }


def live_plan(config: dict[str, Any]) -> list[dict[str, Any]]:
    probe = config["live_probe"]
    rows: list[dict[str, Any]] = []
    index = 1
    for ticker in probe["tickers"]:
        for raw_date in probe["dates"]:
            day = date.fromisoformat(raw_date)
            for timeframe in probe["timeframes"]:
                for session in probe["sessions"]:
                    rows.append({
                        "request_index": index,
                        "ticker": ticker,
                        "date": raw_date,
                        "timeframe": str(timeframe),
                        "session": session,
                        "symbol": f"IDX:{ticker}",
                        "server": probe["server"] if "server" in probe else config["upstream"]["server"],
                        "adjustment": probe["adjustment"],
                        "range": probe["initial_range"],
                        "initial_range": probe["initial_range"],
                        "to": end_epoch(day),
                        "requested_from_epoch": int(datetime.combine(day, time.min, tzinfo=WIB).timestamp()),
                        "requested_to_epoch": end_epoch(day),
                        "fetch_more_steps": probe["fetch_more_steps"],
                        "fetch_more_batch": probe["fetch_more_batch"],
                        "fetch_more_wait_ms": probe["fetch_more_wait_ms"],
                        "timeout_ms": probe["timeout_ms"],
                        "phase": "open_session_probe",
                    })
                    index += 1
    return rows


def write_artifact_manifest(root: Path) -> str:
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            entries.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    manifest = root / "artifact_manifest.json"
    write_json(manifest, {"schema": "idx-trade/tradingview-open-session-semantics-artifact-manifest-v1", "artifacts": entries})
    return sha256_file(manifest)


def run_offline(config_path: Path, admission_root: Path, panel: Path, artifact_root: Path) -> dict[str, Any]:
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "offline").mkdir(parents=True, exist_ok=True)
    inputs = verify_inputs(config_path, admission_root, panel)
    metadata = inspect_market_info(admission_root)
    sessions = build_session_forensics(admission_root, panel)
    metadata.to_csv(artifact_root / "offline" / "market_info_summary.csv", index=False)
    sessions.to_csv(artifact_root / "offline" / "session_forensics.csv", index=False)
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    summary = offline_summary(metadata, sessions)
    summary.update({
        "schema": "idx-trade/tradingview-open-session-semantics-offline-v1",
        "network_calls": 0,
        "frozen_admission_verdict_unchanged": True,
        "input_hashes": inputs,
        "upstream_commit": cfg["upstream"]["mathieu_commit"],
    })
    write_json(artifact_root / "offline" / "summary.json", summary)
    plan = live_plan(cfg)
    prereg = {
        "schema": "idx-trade/tradingview-open-session-semantics-prenetwork-v1",
        "network_started": False,
        "created_at_utc": datetime.now(tz=UTC).isoformat(),
        "input_hashes": inputs,
        "config_sha256": inputs["config_sha256"],
        "live_request_count": len(plan),
        "live_plan": plan,
        "frozen_probe": cfg["live_probe"],
        "decision_rules": cfg["decision_rules"],
        "boundaries": cfg["boundaries"],
    }
    write_json(artifact_root / "pre_network_preparation.json", prereg)
    write_artifact_manifest(artifact_root)
    return summary


def run_live(config_path: Path, admission_root: Path, panel: Path, adapter: Path, artifact_root: Path) -> dict[str, Any]:
    (artifact_root / "live").mkdir(parents=True, exist_ok=True)
    inputs = verify_inputs(config_path, admission_root, panel)
    prereg_path = artifact_root / "pre_network_preparation.json"
    if not prereg_path.exists():
        raise SystemExit("offline preregistration artifact missing")
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("network_started"):
        raise SystemExit("network already marked started; refuse rerun")
    if prereg.get("input_hashes") != inputs:
        raise SystemExit("input hash changed after preregistration")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    plan = live_plan(cfg)
    if len(plan) != prereg["live_request_count"]:
        raise SystemExit("live plan changed after preregistration")
    prereg["network_started"] = True
    prereg["network_started_at_utc"] = datetime.now(tz=UTC).isoformat()
    write_json(prereg_path, prereg)
    rows: list[dict[str, Any]] = []
    for position, request in enumerate(plan, start=1):
        raw_path = artifact_root / "raw" / "live" / f"{request['request_index']:04d}_{request['ticker']}_{request['date']}_{request['timeframe']}m_{request['session']}.json"
        response, stderr = run_node(adapter, request)
        payload = {"adapter_commit": cfg["upstream"]["mathieu_commit"], "request": request, "response": response, "adapter_stderr": stderr}
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(json_bytes(payload))
        rows.append(summarize_live_response(request, response))
        print(json.dumps({"progress": f"{position}/{len(plan)}", **rows[-1]}, ensure_ascii=False), flush=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(artifact_root / "live" / "probe_summary.csv", index=False)
    verdict = classify_live_probe(frame, cfg)
    summary = {
        "schema": "idx-trade/tradingview-open-session-semantics-live-v1",
        "input_hashes": inputs,
        "upstream_commit": cfg["upstream"]["mathieu_commit"],
        "requests": len(plan),
        "status_counts": {str(k): int(v) for k, v in frame["status"].value_counts(dropna=False).items()},
        "preopen_rows": int((frame["preopen_bar_count"].fillna(0) > 0).sum()),
        "regular_preopen_rows": int(((frame["session"] == "regular") & (frame["preopen_bar_count"].fillna(0) > 0)).sum()),
        "extended_preopen_rows": int(((frame["session"] == "extended") & (frame["preopen_bar_count"].fillna(0) > 0)).sum()),
        "verdict": verdict,
        "frozen_admission_verdict_unchanged": True,
        "panel_sha256_after": sha256_file(panel),
        "probe_contract": cfg["live_probe"],
    }
    (artifact_root / "live").mkdir(parents=True, exist_ok=True)
    write_json(artifact_root / "live" / "summary.json", summary)
    write_artifact_manifest(artifact_root)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["offline", "live"], required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--admission-root", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--adapter", type=Path)
    args = parser.parse_args()
    if args.mode == "offline":
        summary = run_offline(args.config, args.admission_root, args.panel, args.artifact_root)
    else:
        if args.adapter is None:
            raise SystemExit("--adapter is required for live mode")
        summary = run_live(args.config, args.admission_root, args.panel, args.adapter, args.artifact_root)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
