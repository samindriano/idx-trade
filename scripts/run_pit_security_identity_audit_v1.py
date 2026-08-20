from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Outcome-blind V4 PIT identity audit")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--frozen-security-master", type=Path, required=True)
    parser.add_argument("--historical-security-master", type=Path, required=True)
    parser.add_argument("--pre-reconcile-security-master", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise SystemExit(f"fresh output directory already exists: {args.output_dir}")
    sys.path.insert(0, str(args.repo_root / "src"))
    from idx_trade.pit_security_identity_audit import (
        IDENTITY_POLICY,
        compare_representation_tables,
        derive_right_only_identity_overlay,
        json_safe,
        merge_identity_overlay,
        sha256_file,
    )
    from idx_trade.ranking_v4_3_features import build_v4_control_feature_table

    expected = {
        "calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
        "panel": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
        "frozen_security_master": "c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240",
    }
    for key, path in (
        ("calendar", args.calendar),
        ("panel", args.panel),
        ("frozen_security_master", args.frozen_security_master),
        ("historical_security_master", args.historical_security_master),
        ("pre_reconcile_security_master", args.pre_reconcile_security_master),
    ):
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
        actual = sha256_file(str(path))
        if key in expected and actual != expected[key]:
            raise SystemExit(f"hash mismatch for {key}: {actual} != {expected[key]}")

    calendar = pd.read_csv(args.calendar)
    panel = pd.read_parquet(args.panel)
    frozen = pd.read_csv(args.frozen_security_master)
    historical = pd.read_csv(args.historical_security_master)
    pre_reconcile = pd.read_csv(args.pre_reconcile_security_master)
    overlay, overlay_diag = derive_right_only_identity_overlay(frozen, historical)
    counterfactual_master = merge_identity_overlay(frozen, overlay)

    base_features, base_diag = build_v4_control_feature_table(panel, calendar["date"], frozen)
    counter_features, counter_diag = build_v4_control_feature_table(
        panel, calendar["date"], counterfactual_master
    )
    diff = compare_representation_tables(base_features, counter_features)
    base_primary = base_features[base_features["universe_primary_liquid"].astype(bool)]
    counter_primary = counter_features[counter_features["universe_primary_liquid"].astype(bool)]
    fren = counter_features[counter_features["ticker"].eq("FREN")].copy()
    fren_primary = fren[fren["universe_primary_liquid"].astype(bool)]
    direct_rows = counter_features.merge(
        base_features[["ticker", "date"]], on=["ticker", "date"], how="left", indicator=True
    )
    direct_rows = direct_rows[direct_rows["_merge"].eq("left_only")].drop(columns=["_merge"])
    direct_fren = direct_rows[direct_rows["ticker"].eq("FREN")]

    summary = {
        "schema_version": "pit_security_identity_audit_v1",
        "status": "PIT_SECURITY_IDENTITY_AUDIT_COMPLETE",
        "policy": IDENTITY_POLICY,
        "outcome_blind": True,
        "provider_calls": False,
        "model_fit": False,
        "model_scoring": False,
        "target_values_loaded": False,
        "protected_forward_accessed": False,
        "input_hashes": {key: sha256_file(str(path)) for key, path in {
            "calendar": args.calendar,
            "panel": args.panel,
            "frozen_security_master": args.frozen_security_master,
            "historical_security_master": args.historical_security_master,
            "pre_reconcile_security_master": args.pre_reconcile_security_master,
        }.items()},
        "input_rows": {
            "panel": len(panel),
            "calendar": len(calendar),
            "frozen_security_master": len(frozen),
            "historical_security_master": len(historical),
            "pre_reconcile_security_master": len(pre_reconcile),
        },
        "overlay": json_safe(overlay_diag.__dict__),
        "base_listing_diagnostics": json_safe(base_diag.__dict__),
        "counterfactual_listing_diagnostics": json_safe(counter_diag.__dict__),
        "direct_new_rows": len(direct_rows),
        "direct_new_tickers": sorted(direct_rows["ticker"].unique().tolist()),
        "direct_new_dates": sorted(pd.to_datetime(direct_rows["date"]).dt.date.astype(str).unique().tolist()),
        "fren": {
            "feature_rows": len(fren),
            "first_date": None if fren.empty else str(fren["date"].min().date()),
            "last_date": None if fren.empty else str(fren["date"].max().date()),
            "history_qualified_count": int(fren["universe_history_qualified"].astype(bool).sum()),
            "primary_liquid_count": len(fren_primary),
            "primary_liquid_dates": sorted(fren_primary["date"].dt.date.astype(str).tolist()),
            "median_peak_regular_market_value_60": {
                "median": None if fren.empty else float(fren["median_regular_value_60"].median()),
                "peak": None if fren.empty else float(fren["median_regular_value_60"].max()),
            },
        },
        "representation_diff": json_safe(diff.__dict__),
        "base_primary_rows": len(base_primary),
        "counterfactual_primary_rows": len(counter_primary),
        "decision": (
            "PIT_SECURITY_IDENTITY_OMISSION_CONFIRMED_REPRESENTATION_INERT"
            if len(fren_primary) == 0 and diff.changed_rows == 0
            else "PIT_SECURITY_IDENTITY_OMISSION_CHANGES_V4_REPRESENTATION_TRAINING_SUPPORT_INTERSECTION_REQUIRED"
        ),
        "stage_c": {
            "performed": False,
            "reason": "not material because no existing shared representation cells changed and FREN was not primary-liquid"
            if len(fren_primary) == 0 and diff.changed_rows == 0
            else "requires separately frozen support-identity input audit before any continuation",
        },
    }
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    overlay.to_csv(args.output_dir / "identity_overlay.csv", index=False)
    pd.DataFrame([diff.__dict__ | {"changed_by_column": json.dumps(diff.changed_by_column, sort_keys=True)}]).to_json(
        args.output_dir / "representation_diff.json", orient="records", indent=2
    )
    output_paths = (
        args.output_dir / "summary.json",
        args.output_dir / "identity_overlay.csv",
        args.output_dir / "representation_diff.json",
    )
    manifest = {
        "schema_version": "pit_security_identity_audit_manifest_v1",
        "status": summary["status"],
        "decision": summary["decision"],
        "stage": "B",
        "policy": IDENTITY_POLICY,
        "outcome_blind": True,
        "provider_calls": False,
        "model_fit": False,
        "model_scoring": False,
        "target_values_loaded": False,
        "protected_forward_accessed": False,
        "input_hashes": summary["input_hashes"],
        "output_hashes": {
            path.name: sha256_file(str(path)) for path in output_paths
        },
        "output_files": [path.name for path in output_paths],
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": summary["status"],
        "decision": summary["decision"],
        "overlay_rows": len(overlay),
        "changed_rows": diff.changed_rows,
        "fren_primary": len(fren_primary),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(str(manifest_path)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
