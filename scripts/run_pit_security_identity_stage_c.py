"""Run the exact, outcome-blind V4-X training-support intersection audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd


STAGE_B_HEAD = "0e778d2311eba01e66966f3440262d9ea50cc8e2"
EXPECTED = {
    "calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "panel": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
    "frozen_security_master": "c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240",
    "historical_security_master": "9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9",
    "target_state": "f7b0b0f29616f6f12615d87925f116218f4a2e01c97ef64bb8e1fc4984f30d1c",
    "per_date_support": "ac11a75c891b965db14c6b6ea8f64da10ad08c492c7a6410fbd77d790a6e28e4",
    "prefit_manifest": "0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc",
    "stage_b_manifest": "f81e0a0b8e30cddba7b9bb58d378fd06800d4cc61a50d71cf279c9c7f0885489",
    "stage_b_representation_diff": "a13940e40e7e50ff7f6ee6edf2b9574a1a08928f7754df0e9458a43748adaea8",
}
EXPECTED_BLOB = {
    "v4_config": "7bfca6b0805e680092c7f8baa6efcd39998482d6",
    "final_refit_runner": "2d538c1c99fb348b87d6c268e2df821b9099d203",
    "feature_builder": "59ad05f815870ae00480dc7945fe18371d8eff9c",
}
EXPECTED_STAGE_B_COUNTS = {
    "direct_new_rows": 952,
    "changed_rows": 707462,
    "spillover_changed_rows": 707462,
    "changed_dates": 933,
    "changed_tickers": 922,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "repo_root",
        "target_state_parquet",
        "per_date_support",
        "prefit_manifest",
        "stage_b_manifest",
        "stage_b_representation_diff",
        "calendar",
        "panel",
        "frozen_security_master",
        "historical_security_master",
        "output_dir",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label}_SHA_MISMATCH:{actual}!={expected}")
    return actual


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_INVALID:{path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def json_safe(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp,)):
        return value.date().isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        return json_safe(value.item())
    return value


def git_blob(repo_root: Path, path: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", f"HEAD:{path}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def load_stage_b_diff(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        value = value[0]
    if not isinstance(value, dict):
        raise RuntimeError("STAGE_B_REPRESENTATION_DIFF_INVALID")
    return value


def key_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.loc[:, ["ticker", "date"]].copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["date"] = pd.to_datetime(out["date"], errors="raise").dt.normalize()
    if out.duplicated(["ticker", "date"]).any():
        raise RuntimeError("MODEL_FRAME_DUPLICATE_TICKER_DATE")
    return out


def absent_keys(support: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    return support.merge(
        key_frame(frame), on=["ticker", "date"], how="left", indicator=True
    ).loc[lambda value: value["_merge"].eq("left_only"), ["ticker", "date"]]


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise SystemExit(f"fresh output directory already exists: {args.output_dir}")

    sys.path.insert(0, str(args.repo_root / "src"))
    from idx_trade.pit_security_identity_audit import (
        IDENTITY_POLICY,
        derive_right_only_identity_overlay,
        merge_identity_overlay,
        representation_change_sets,
    )
    from idx_trade.ranking_v4_3_features import build_v4_control_feature_table
    from idx_trade.pit_security_identity_training_support import (
        ALLOWED_TARGET_STATE_COLUMNS,
        FORBIDDEN_TARGET_COLUMNS,
        normalize_per_date_support,
        normalize_target_states,
        select_exact_head_support,
        summarize_intersection,
        union_intersections,
        verify_target_projection,
        verify_target_schema,
    )

    paths = {
        "calendar": args.calendar,
        "panel": args.panel,
        "frozen_security_master": args.frozen_security_master,
        "historical_security_master": args.historical_security_master,
        "target_state": args.target_state_parquet,
        "per_date_support": args.per_date_support,
        "prefit_manifest": args.prefit_manifest,
        "stage_b_manifest": args.stage_b_manifest,
        "stage_b_representation_diff": args.stage_b_representation_diff,
    }
    for key, path in paths.items():
        expected = EXPECTED[key]
        require_sha(path, expected, key.upper())

    if git_blob(args.repo_root, "config/ranking_v4_x1_final_refit_v1.json") != EXPECTED_BLOB["v4_config"]:
        raise RuntimeError("V4_CONFIG_BLOB_MISMATCH")
    if git_blob(args.repo_root, "scripts/run_v4_x1_final_refit_freeze.py") != EXPECTED_BLOB["final_refit_runner"]:
        raise RuntimeError("FINAL_REFIT_RUNNER_BLOB_MISMATCH")
    if git_blob(args.repo_root, "src/idx_trade/ranking_v4_3_features.py") != EXPECTED_BLOB["feature_builder"]:
        raise RuntimeError("FEATURE_BUILDER_BLOB_MISMATCH")

    stage_b_manifest = read_json(args.stage_b_manifest, "STAGE_B_MANIFEST")
    if stage_b_manifest.get("status") != "PIT_SECURITY_IDENTITY_AUDIT_COMPLETE":
        raise RuntimeError("STAGE_B_STATUS_CHANGED")
    if stage_b_manifest.get("stage") != "B" or not stage_b_manifest.get("outcome_blind"):
        raise RuntimeError("STAGE_B_MANIFEST_CONTRACT_INVALID")
    if stage_b_manifest.get("decision") != "PIT_SECURITY_IDENTITY_OMISSION_CHANGES_V4_REPRESENTATION_TRAINING_SUPPORT_INTERSECTION_REQUIRED":
        raise RuntimeError("STAGE_B_DECISION_CHANGED")
    output_hashes = stage_b_manifest.get("output_hashes", {})
    if output_hashes.get("representation_diff.json") != EXPECTED["stage_b_representation_diff"]:
        raise RuntimeError("STAGE_B_DIFF_HASH_NOT_PINNED_IN_MANIFEST")

    prefit_manifest = read_json(args.prefit_manifest, "PREFIT_MANIFEST")
    if prefit_manifest.get("status") != "V4_3R_CA80_PREFIT_SUPPORT_PASS_READY_TO_FREEZE_EXECUTION":
        raise RuntimeError("PREFIT_STATUS_CHANGED")
    prefit_outputs = prefit_manifest.get("output_hashes", {})
    if prefit_outputs.get("per_date") != EXPECTED["per_date_support"]:
        raise RuntimeError("PREFIT_SUPPORT_HASH_NOT_PINNED")

    # Inspect only the parquet schema first; never ask the parquet reader for
    # forbidden numeric targets/ranks.
    import pyarrow.parquet as pq

    schema_names = tuple(pq.ParquetFile(args.target_state_parquet).schema.names)
    forbidden_present = sorted(verify_target_schema(schema_names))
    verify_target_projection(ALLOWED_TARGET_STATE_COLUMNS)
    target_states = pd.read_parquet(
        args.target_state_parquet, columns=list(ALLOWED_TARGET_STATE_COLUMNS)
    )
    if tuple(target_states.columns) != ALLOWED_TARGET_STATE_COLUMNS:
        raise RuntimeError("TARGET_PROJECTION_COLUMN_ORDER_CHANGED")
    target_states = normalize_target_states(target_states)
    per_date = normalize_per_date_support(
        pd.read_csv(
            args.per_date_support,
            usecols=["session_index", "date", "h5_eligible", "h10_eligible"],
        )
    )
    h5_support = select_exact_head_support(
        target_states, per_date, head="h5", expected_eligible_dates=986
    )
    h10_support = select_exact_head_support(
        target_states, per_date, head="h10", expected_eligible_dates=982
    )

    calendar = pd.read_csv(args.calendar)
    panel = pd.read_parquet(args.panel)
    frozen_master = pd.read_csv(args.frozen_security_master)
    historical_master = pd.read_csv(args.historical_security_master)
    overlay, overlay_diag = derive_right_only_identity_overlay(
        frozen_master, historical_master
    )
    counterfactual_master = merge_identity_overlay(frozen_master, overlay)
    base_features, base_diag = build_v4_control_feature_table(
        panel, calendar["date"], frozen_master
    )
    counter_features, counter_diag = build_v4_control_feature_table(
        panel, calendar["date"], counterfactual_master
    )
    direct_keys, changed_keys, changed_by_column = representation_change_sets(
        base_features, counter_features
    )
    direct_tickers = sorted({str(key[0]) for key in direct_keys})
    if direct_tickers != ["FREN"]:
        raise RuntimeError(f"STAGE_B_DIRECT_TICKER_CHANGED:{direct_tickers}")
    affected_rows = pd.DataFrame(
        [
            {"ticker": str(ticker), "date": pd.Timestamp(date), "impact_type": "DIRECT_FREN"}
            for ticker, date in sorted(direct_keys, key=lambda value: (str(value[1]), str(value[0])))
        ]
        + [
            {"ticker": str(ticker), "date": pd.Timestamp(date), "impact_type": "SPILLOVER"}
            for ticker, date in sorted(changed_keys, key=lambda value: (str(value[1]), str(value[0])))
        ]
    )
    if affected_rows.duplicated(["ticker", "date", "impact_type"]).any():
        raise RuntimeError("AFFECTED_REPRESENTATION_DUPLICATE")

    stage_b_diff = load_stage_b_diff(args.stage_b_representation_diff)
    observed_counts = {
        "direct_new_rows": len(direct_keys),
        "changed_rows": len(changed_keys),
        "spillover_changed_rows": len([key for key in changed_keys if str(key[0]) != "FREN"]),
        "changed_dates": len({str(pd.Timestamp(key[1]).date()) for key in changed_keys}),
        "changed_tickers": len({str(key[0]) for key in changed_keys}),
    }
    for key, expected in EXPECTED_STAGE_B_COUNTS.items():
        if observed_counts[key] != expected or int(stage_b_diff.get(key, -1)) != expected:
            raise RuntimeError(
                f"STAGE_B_REDERIVE_MISMATCH:{key}:{observed_counts[key]}:{stage_b_diff.get(key)}:{expected}"
            )

    base_primary = base_features.loc[base_features["universe_primary_liquid"].astype(bool)]
    counter_primary = counter_features.loc[counter_features["universe_primary_liquid"].astype(bool)]
    direct_frame = pd.DataFrame(list(direct_keys), columns=["ticker", "date"])
    direct_frame["ticker"] = direct_frame["ticker"].astype(str)
    direct_frame["date"] = pd.to_datetime(direct_frame["date"]).dt.normalize()

    presence_rows: list[dict[str, Any]] = []
    presence_gaps: list[pd.DataFrame] = []
    for head, support in (("H5", h5_support), ("H10", h10_support)):
        missing_counter = absent_keys(support, counter_primary)
        non_direct_support = support.merge(
            direct_frame, on=["ticker", "date"], how="left", indicator=True
        ).loc[lambda value: value["_merge"].eq("left_only"), ["ticker", "date"]]
        missing_base = absent_keys(non_direct_support, base_primary)
        presence_rows.append(
            {
                "head": head,
                "support_rows": len(support),
                "counter_primary_rows": len(support) - len(missing_counter),
                "counter_primary_missing": len(missing_counter),
                "base_expected_rows": len(non_direct_support),
                "base_present_non_direct": len(non_direct_support) - len(missing_base),
                "base_missing_non_direct": len(missing_base),
                "base_missing_direct_expected": len(support) - len(non_direct_support),
            }
        )
        if not missing_counter.empty:
            missing_counter = missing_counter.assign(head=head, reason="MISSING_COUNTER_PRIMARY_FRAME")
            presence_gaps.append(missing_counter)
        if not missing_base.empty:
            missing_base = missing_base.assign(head=head, reason="MISSING_BASE_NON_DIRECT_PRIMARY_FRAME")
            presence_gaps.append(missing_base)

    h5_direct = affected_rows.loc[affected_rows["impact_type"].eq("DIRECT_FREN")].merge(
        h5_support, on=["ticker", "date"], how="inner"
    )
    h5_spill = affected_rows.loc[affected_rows["impact_type"].eq("SPILLOVER")].merge(
        h5_support, on=["ticker", "date"], how="inner"
    )
    h10_direct = affected_rows.loc[affected_rows["impact_type"].eq("DIRECT_FREN")].merge(
        h10_support, on=["ticker", "date"], how="inner"
    )
    h10_spill = affected_rows.loc[affected_rows["impact_type"].eq("SPILLOVER")].merge(
        h10_support, on=["ticker", "date"], how="inner"
    )
    h5_intersection = pd.concat([h5_direct, h5_spill], ignore_index=True)
    h10_intersection = pd.concat([h10_direct, h10_spill], ignore_index=True)
    union = union_intersections(h5_intersection, h10_intersection)
    if presence_gaps:
        gap_frame = pd.concat(presence_gaps, ignore_index=True)
    else:
        gap_frame = pd.DataFrame(columns=["ticker", "date", "head", "reason"])

    affected_dates = len({str(pd.Timestamp(key[1]).date()) for key in direct_keys | changed_keys})
    h5_eligible_dates = int(per_date["h5_eligible"].sum())
    h10_eligible_dates = int(per_date["h10_eligible"].sum())
    decision = (
        "STAGE_C_BLOCKED_EXACT_SUPPORT_NOT_PRESENT_IN_PRIMARY_MODEL_FRAME"
        if not gap_frame.empty
        else (
            "PIT_SECURITY_IDENTITY_REPRESENTATION_CHANGE_OUTSIDE_V4_X_EXACT_TRAINING_SUPPORT"
            if union.empty
            else "V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION"
        )
    )
    eventual_refit = decision == "V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION"
    args.output_dir.mkdir(parents=True)
    h5_support.to_csv(args.output_dir / "h5_support_identities.csv", index=False, date_format="%Y-%m-%d")
    h10_support.to_csv(args.output_dir / "h10_support_identities.csv", index=False, date_format="%Y-%m-%d")
    affected_rows.to_csv(args.output_dir / "affected_representation_identities.csv", index=False, date_format="%Y-%m-%d")
    h5_intersection.to_csv(args.output_dir / "h5_intersection.csv", index=False, date_format="%Y-%m-%d")
    h10_intersection.to_csv(args.output_dir / "h10_intersection.csv", index=False, date_format="%Y-%m-%d")
    union.to_csv(args.output_dir / "union_intersection.csv", index=False, date_format="%Y-%m-%d")
    gap_frame.to_csv(args.output_dir / "support_presence_gaps.csv", index=False, date_format="%Y-%m-%d")

    def impact_summary(frame: pd.DataFrame) -> dict[str, Any]:
        result = summarize_intersection(frame)
        result["fraction_support_rows"] = float(len(frame) / len(h5_support if frame is h5_intersection else h10_support)) if len(h5_support if frame is h5_intersection else h10_support) else 0.0
        return result

    summary = {
        "schema_version": "pit_security_identity_stage_c_manifest_v1",
        "status": "PIT_SECURITY_IDENTITY_STAGE_C_COMPLETE",
        "stage": "C",
        "stage_b_head": STAGE_B_HEAD,
        "stage_b_manifest_sha256": EXPECTED["stage_b_manifest"],
        "stage_b_representation_diff_sha256": EXPECTED["stage_b_representation_diff"],
        "identity_policy": IDENTITY_POLICY,
        "input_hashes": EXPECTED,
        "frozen_code_blobs": EXPECTED_BLOB,
        "target_schema_names": list(schema_names),
        "forbidden_target_columns_present_in_schema": forbidden_present,
        "forbidden_target_columns_loaded": [],
        "target_numeric_values_accessed": False,
        "target_state_projection": list(ALLOWED_TARGET_STATE_COLUMNS),
        "per_date_projection": ["session_index", "date", "h5_eligible", "h10_eligible"],
        "eligible_dates": {"H5": h5_eligible_dates, "H10": h10_eligible_dates},
        "support": {
            "H5": {"rows": len(h5_support), "tickers": h5_support["ticker"].nunique(), "dates": h5_support["date"].nunique()},
            "H10": {"rows": len(h10_support), "tickers": h10_support["ticker"].nunique(), "dates": h10_support["date"].nunique()},
        },
        "stage_b_rederive": {
            "overlay": json_safe(overlay_diag.__dict__),
            "base_primary_rows": len(base_primary),
            "counterfactual_primary_rows": len(counter_primary),
            "observed_counts": observed_counts,
            "changed_by_column": changed_by_column,
        },
        "support_presence": presence_rows,
        "intersections": {
            "H5": impact_summary(h5_intersection),
            "H10": impact_summary(h10_intersection),
            "union": summarize_intersection(union),
            "affected_representation_dates": affected_dates,
            "affected_representation_date_fraction_of_all_changed_dates": float(affected_dates / observed_counts["changed_dates"]) if observed_counts["changed_dates"] else 0.0,
        },
        "decision": decision,
        "eventual_clean_refit_required": eventual_refit,
        "provider_calls": False,
        "model_fit": False,
        "model_scoring": False,
        "predictions_accessed": False,
        "performance_metrics_accessed": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
        "counter_mutated": False,
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(json_safe(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_paths = [path for path in args.output_dir.iterdir() if path.is_file() and path.name != "MANIFEST.json"]
    manifest = {
        "schema_version": "pit_security_identity_stage_c_manifest_v1",
        "status": summary["status"],
        "decision": decision,
        "stage": "C",
        "outcome_blind": True,
        "input_hashes": EXPECTED,
        "frozen_code_blobs": EXPECTED_BLOB,
        "output_hashes": {path.name: sha256_file(path) for path in sorted(output_paths)},
        "output_files": sorted(path.name for path in output_paths),
        "forbidden_target_columns_loaded": [],
        "target_numeric_values_accessed": False,
        "provider_calls": False,
        "model_fit": False,
        "model_scoring": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "h5_support_rows": len(h5_support), "h10_support_rows": len(h10_support), "h5_intersection": summarize_intersection(h5_intersection), "h10_intersection": summarize_intersection(h10_intersection), "union": summarize_intersection(union), "manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
