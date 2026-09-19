"""Independent target-free verifier for the EXECSTATE-01 source audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from alpha_stage_a_v2 import sha256_file


def inventory_hash(cache_dir: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(cache_dir).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--regular-anchors", type=Path, required=True)
    parser.add_argument("--no-trade-anchors", type=Path, required=True)
    parser.add_argument("--session-report", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    usecols = ["ticker", "as_of_date", "state", "source", "market"]
    anchors = pd.read_csv(args.anchors, usecols=usecols)
    regular = pd.read_csv(args.regular_anchors, usecols=["ticker", "as_of_date"])
    no_trade = pd.read_csv(args.no_trade_anchors, usecols=["ticker", "as_of_date"])
    report = pd.read_csv(args.session_report)
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    for frame, date_column in [(anchors, "as_of_date"), (regular, "as_of_date"), (no_trade, "as_of_date")]:
        frame["ticker"] = frame["ticker"].astype("string")
        frame[date_column] = pd.to_datetime(frame[date_column], errors="raise").dt.normalize()
    report["session"] = pd.to_datetime(report["session"], errors="raise").dt.normalize()
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()

    parquet_files = sorted(args.cache_dir.glob("*.parquet"))
    raw_frames = []
    for path in parquet_files:
        frame = pd.read_parquet(
            path,
            columns=["ticker", "as_of_date", "volume", "frequency", "regular_value", "nonregular_volume", "nonregular_frequency"],
        )
        frame["ticker"] = frame["ticker"].astype("string")
        frame["as_of_date"] = pd.to_datetime(frame["as_of_date"], errors="raise").dt.normalize()
        raw_frames.append(frame)
    raw = pd.concat(raw_frames, ignore_index=True)
    for column in ["volume", "frequency", "regular_value", "nonregular_volume", "nonregular_frequency"]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw["nonregular_activity"] = raw["nonregular_volume"].gt(0) | raw["nonregular_frequency"].gt(0)
    merged = anchors.merge(raw, on=["ticker", "as_of_date"], how="inner", validate="one_to_one")
    active = merged["state"].eq("ACTIVE")
    no_trade_mask = merged["state"].eq("NO_TRADE")
    nonregular_no_trade = int((no_trade_mask & merged["nonregular_activity"]).sum())
    nonregular_active = int((active & merged["nonregular_activity"]).sum())

    checks = {
        "artifact_status": artifact.get("status") == "SOURCE_PARTIAL_STRUCTURAL_SIGNAL",
        "artifact_stage": artifact.get("stage") == "EXECSTATE01_OFFICIAL_EXECUTION_STATE_SOURCE_AUDIT",
        "no_outcome_access": artifact.get("outcome_accessed") is False,
        "no_provider_access": artifact.get("provider_accessed") is False,
        "no_candidate_id_created": artifact.get("candidate_id_created") is False,
        "code_hash": artifact.get("code_sha256") == sha256_file(args.code),
        "anchors_hash": artifact.get("source_hashes", {}).get("anchors") == sha256_file(args.anchors),
        "regular_hash": artifact.get("source_hashes", {}).get("regular_anchors") == sha256_file(args.regular_anchors),
        "no_trade_hash": artifact.get("source_hashes", {}).get("no_trade_anchors") == sha256_file(args.no_trade_anchors),
        "report_hash": artifact.get("source_hashes", {}).get("session_report") == sha256_file(args.session_report),
        "sessions_hash": artifact.get("source_hashes", {}).get("official_sessions") == sha256_file(args.sessions),
        "cache_inventory_hash": artifact.get("source_hashes", {}).get("cache_inventory") == inventory_hash(
            args.cache_dir,
            sorted(list(args.cache_dir.glob("*.parquet")) + list(args.cache_dir.glob("*.meta.json"))),
        ),
        "anchor_keys_unique": int(anchors.duplicated(["ticker", "as_of_date"]).sum()) == 0,
        "state_values": set(anchors["state"].astype(str)).issubset({"ACTIVE", "NO_TRADE"}),
        "source_values": set(anchors["source"].astype(str)) == {"IDX_PUBLIC_STOCK_SUMMARY"},
        "market_values": set(anchors["market"].astype(str)) == {"REGULAR"},
        "regular_count": int(active.sum()) == len(regular),
        "no_trade_count": int(no_trade_mask.sum()) == len(no_trade),
        "report_ok": bool(report["status"].eq("OK").all()),
        "report_unresolved_zero": int(report["unresolved_rows"].sum()) == 0,
        "raw_join_rows": len(merged) == len(anchors),
        "nonregular_no_trade_count": nonregular_no_trade == artifact["source"]["no_trade_nonregular_rows"],
        "nonregular_active_count": nonregular_active == artifact["source"]["active_nonregular_rows"],
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verification_type": "independent_execution_state_reconciliation_target_free",
        "artifact_sha256": sha256_file(args.artifact),
        "verifier_code_sha256": sha256_file(Path(__file__)),
        "checks": checks,
        "recomputed": {
            "anchor_rows": int(len(anchors)),
            "active_rows": int(active.sum()),
            "no_trade_rows": int(no_trade_mask.sum()),
            "raw_join_rows": int(len(merged)),
            "no_trade_nonregular_rows": nonregular_no_trade,
            "active_nonregular_rows": nonregular_active,
        },
        "scope": {
            "outcome_accessed": False,
            "provider_accessed": False,
            "cloud_accessed": False,
            "incumbent_predictive_accessed": False,
        },
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
