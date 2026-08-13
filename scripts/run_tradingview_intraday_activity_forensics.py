"""Offline activity-aware forensic runner for the frozen TradingView pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from idx_trade.tradingview_activity_forensics import activity_aware_summary, build_activity_forensics, expected_listed_sessions
from idx_trade.tradingview_remediation import sha256_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--admission-artifact-root", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    lineage = config["lineage"]
    root = args.admission_artifact_root
    inputs = {
        "artifact_manifest": root / "artifact_manifest.json",
        "sample_manifest": root / "sample_manifest.json",
        "bars": root / "normalized" / "mathieu_intraday_bars.csv",
        "requests": root / "normalized" / "mathieu_request_manifest.csv",
    }
    expected_hashes = {
        "artifact_manifest": lineage["admission_artifact_manifest_sha256"],
        "sample_manifest": lineage["sample_manifest_sha256"],
        "bars": lineage["mathieu_intraday_bars_sha256"],
        "requests": lineage["mathieu_request_manifest_sha256"],
    }
    for key, path in inputs.items():
        actual = sha256_file(path)
        if actual != expected_hashes[key]:
            raise ValueError(f"{key} hash mismatch: {actual} != {expected_hashes[key]}")
    if sha256_file(args.panel) != lineage["canonical_panel_sha256"]:
        raise ValueError("canonical panel hash mismatch")
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise ValueError("output root must be new and empty")
    args.output_root.mkdir(parents=True, exist_ok=True)

    sample_manifest = json.loads(inputs["sample_manifest"].read_text(encoding="utf-8"))
    expected = expected_listed_sessions(sample_manifest)
    bars = pd.read_csv(inputs["bars"])
    panel = pd.read_parquet(args.panel, columns=["ticker", "date", "open", "high", "low", "close", "volume"])
    result = build_activity_forensics(expected, bars, panel)
    summary = activity_aware_summary(result, threshold=float(config["diagnostic_reference"]["coverage_threshold"]))
    result.to_csv(args.output_root / "activity_support.csv", index=False)
    result[~result["tv_present"]].to_csv(args.output_root / "missing_session_forensics.csv", index=False)
    (args.output_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
