"""Freeze V2 inputs and request plan before any TradingView request."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from idx_trade.tradingview_price_path_v2 import (
    build_common_universe,
    build_expected_sessions,
    build_request_manifest,
    classify_official_activity,
    json_bytes,
    load_official_sessions,
    sha256_file,
)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def derive_actions(path: Path, start: str, end: str) -> pd.DataFrame:
    payload = load_json(path)
    rows = payload.get("data", [])
    output = []
    for row in rows if isinstance(rows, list) else []:
        action = str(row.get("JenisTindakan", "")).strip()
        token = action.lower().replace(" ", "")
        if "stocksplit" not in token and "reverse" not in token:
            continue
        ticker = str(row.get("StockCode") or row.get("KodeEmiten") or row.get("KodeSaham") or "").upper().strip()
        raw_date = row.get("TanggalPencatatan") or row.get("TanggalEfektif") or row.get("Tanggal")
        effective = pd.to_datetime(raw_date, errors="coerce")
        if not ticker or pd.isna(effective) or not pd.Timestamp(start) <= effective.normalize() <= pd.Timestamp(end):
            continue
        output.append({"ticker": ticker, "action": action, "effective_date": effective.date().isoformat(), "source": "IDX_LISTING_ACTIVITY_ISSUED_HISTORY", "source_ref": str(row.get("FullSavePath") or row.get("URL") or "")})
    return pd.DataFrame(output, columns=["ticker", "action", "effective_date", "source", "source_ref"]).drop_duplicates().sort_values(["ticker", "effective_date", "action"]).reset_index(drop=True)


def manifest_sha(root: Path) -> str:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            rows.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    target = root / "artifact_manifest.json"
    target.write_bytes(json_bytes({"schema": "idx-trade/tradingview-historical-price-path-v2-artifact-manifest", "artifacts": rows}))
    return sha256_file(target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--scope-exclusions", type=Path, required=True)
    parser.add_argument("--curated-identities", type=Path, required=True)
    parser.add_argument("--stock-summary-root", type=Path, required=True)
    parser.add_argument("--corporate-actions", type=Path, required=True)
    parser.add_argument("--canonical-panel", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    if args.artifact_root.exists() and any(args.artifact_root.iterdir()):
        raise SystemExit(f"artifact root is non-empty: {args.artifact_root}")
    config = load_json(args.config)
    root = args.artifact_root
    root.mkdir(parents=True, exist_ok=True)
    start, end = config["window"]["start"], config["window"]["end"]
    sessions = load_official_sessions(args.calendar, start, end)
    if len(sessions) != config["window"]["expected_session_count"]:
        raise SystemExit(f"official session count mismatch: {len(sessions)}")
    universe = build_common_universe(args.security_master, args.scope_exclusions, args.curated_identities, start, end)
    expected = build_expected_sessions(universe, sessions)
    activity = classify_official_activity(expected, args.stock_summary_root)
    requests = build_request_manifest(universe, sessions, config)
    actions = derive_actions(args.corporate_actions, start, end)
    input_hashes = {name: sha256_file(path) for name, path in {"config": args.config, "calendar": args.calendar, "security_master": args.security_master, "scope_exclusions": args.scope_exclusions, "curated_identities": args.curated_identities, "corporate_actions": args.corporate_actions, "canonical_panel": args.canonical_panel}.items()}
    write_csv(root / "official_sessions.csv", sessions)
    write_csv(root / "universe.csv", universe)
    write_csv(root / "expected_ticker_sessions.csv", expected)
    write_csv(root / "activity_reconciliation.csv", activity)
    write_csv(root / "request_manifest.csv", requests)
    write_csv(root / "corporate_action_events.csv", actions)
    prereg = {"schema": "idx-trade/tradingview-historical-price-path-v2-preregistration", "created_before_network": True, "network_started": False, "config": config, "input_paths": {"canonical_panel": str(args.canonical_panel)}, "input_hashes": input_hashes, "counts": {"official_sessions": len(sessions), "universe_tickers": int(universe["ticker"].nunique()), "expected_ticker_sessions": len(expected), "active_sessions": int((activity["activity_state"] == "ACTIVE").sum()), "no_trade_sessions": int((activity["activity_state"] == "NO_TRADE").sum()), "unknown_sessions": int((activity["activity_state"] == "UNKNOWN").sum()), "request_count": len(requests), "corporate_action_events": len(actions)}, "request_contract": config["provider"] | config["acquisition"], "gate_contract": config["gates"], "boundaries": config["boundaries"]}
    (root / "preregistration.json").write_bytes(json_bytes(prereg))
    digest = manifest_sha(root)
    print(json.dumps({"artifact_root": str(root), "artifact_manifest_sha256": digest, "counts": prereg["counts"], "input_hashes": input_hashes}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
