"""Step-2 v1.2: price-basis seam proof and exact V4-X fit-row impact.

Consumes the immutable v1.1 audit artifacts.  No providers, model fitting,
model scoring, target values, or protected-forward outcomes are accessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_V11_ROOT = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_v2_1_training_basis_impact_v1_1_20260820"
)
DEFAULT_OUTPUT = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_v2_1_training_basis_impact_v1_2_20260820"
)
EXPECTED_V11_MANIFEST_SHA256 = "62562fa3f1d949c3e4f9e225aae13b116a5e2c00dffcceab6240ebb07ea422d6"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_EXPECTED:{path}")
    return value


def strict_bool(series: pd.Series, *, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    allowed = {"true", "false"}
    seen = set(normalized.dropna().unique())
    if not seen.issubset(allowed):
        raise RuntimeError(f"INVALID_BOOLEAN:{label}:{sorted(seen)}")
    return normalized.eq("true")


def normalize_keys(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["ticker"] = (
        out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    out["date"] = pd.to_datetime(out["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    return out


def verify_v11(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = root / "artifact_manifest.json"
    actual = sha256_file(manifest_path)
    if actual != EXPECTED_V11_MANIFEST_SHA256:
        raise RuntimeError(
            f"V11_MANIFEST_SHA_MISMATCH:{actual}!={EXPECTED_V11_MANIFEST_SHA256}"
        )
    manifest = read_json(manifest_path)
    summary = read_json(root / "training_basis_impact_summary.json")
    hashes = manifest.get("output_hashes") or {}
    files = {
        "panel_basis_rows": root / "panel_vs_idx_basis_rows.csv",
        "stable_scale_runs": root / "stable_scale_runs.csv",
        "counterfactual_hlc_rows": root / "counterfactual_hlc_rows.csv",
        "v2_impact_rows": root / "v2_training_feature_impact_rows.csv",
        "v4_impact_rows": root / "v4_x1_candidate_training_feature_impact_rows.csv",
        "summary": root / "training_basis_impact_summary.json",
    }
    for name, path in files.items():
        expected = str(hashes.get(name) or "")
        actual_hash = sha256_file(path)
        if not expected or actual_hash != expected:
            raise RuntimeError(f"V11_OUTPUT_SHA_MISMATCH:{name}:{actual_hash}!={expected}")
    return manifest, summary


def changed_scope_summary(diff: pd.DataFrame, affected_tickers: set[str]) -> dict[str, Any]:
    frame = normalize_keys(diff)
    changed = pd.to_numeric(frame["changed_feature_count"], errors="raise").astype(int).gt(0)
    direct = changed & frame["ticker"].isin(affected_tickers)
    spill = changed & ~frame["ticker"].isin(affected_tickers)
    change_columns = [c for c in frame.columns if c.startswith("changed__")]

    def feature_counts(mask: pd.Series) -> dict[str, int]:
        result: dict[str, int] = {}
        for column in change_columns:
            count = int(strict_bool(frame[column], label=column)[mask].sum())
            if count:
                result[column.removeprefix("changed__")] = count
        return result

    return {
        "rows": int(len(frame)),
        "changed_rows": int(changed.sum()),
        "changed_row_rate": float(changed.mean()) if len(frame) else 0.0,
        "changed_tickers": int(frame.loc[changed, "ticker"].nunique()),
        "changed_dates": int(frame.loc[changed, "date"].nunique()),
        "direct_changed_rows": int(direct.sum()),
        "direct_changed_tickers": int(frame.loc[direct, "ticker"].nunique()),
        "spillover_changed_rows": int(spill.sum()),
        "spillover_changed_tickers": int(frame.loc[spill, "ticker"].nunique()),
        "direct_feature_counts": feature_counts(direct),
        "spillover_feature_counts": feature_counts(spill),
    }


def seam_boundaries(basis: pd.DataFrame, runs: pd.DataFrame) -> pd.DataFrame:
    data = normalize_keys(basis).sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    run_frame = runs.copy()
    run_frame["ticker"] = run_frame["ticker"].astype(str).str.upper().str.strip()
    run_frame["start_date"] = pd.to_datetime(run_frame["start_date"], errors="raise").dt.normalize()
    run_frame["end_date"] = pd.to_datetime(run_frame["end_date"], errors="raise").dt.normalize()
    records: list[dict[str, Any]] = []

    for row in run_frame.itertuples(index=False):
        block = data[data["ticker"].eq(row.ticker)].reset_index(drop=True)
        date_to_pos = {pd.Timestamp(v): i for i, v in enumerate(block["date"])}
        start = date_to_pos.get(pd.Timestamp(row.start_date))
        end = date_to_pos.get(pd.Timestamp(row.end_date))
        if start is None or end is None:
            raise RuntimeError(f"RUN_BOUNDARY_NOT_IN_BASIS:{row.ticker}:{row.run_id}")
        factor = float(row.factor)
        for boundary, left_pos, right_pos, expected_ratio in (
            ("ENTRY", start - 1, start, 1.0 / factor),
            ("EXIT", end, end + 1, factor),
        ):
            if left_pos < 0 or right_pos >= len(block):
                continue
            left = block.iloc[left_pos]
            right = block.iloc[right_pos]
            panel_gross = float(right["panel_close"]) / float(left["panel_close"])
            idx_gross = float(right["idx_close"]) / float(left["idx_close"])
            gross_ratio = panel_gross / idx_gross
            records.append(
                {
                    "ticker": row.ticker,
                    "run_id": int(row.run_id),
                    "factor": factor,
                    "boundary": boundary,
                    "left_date": pd.Timestamp(left["date"]).strftime("%Y-%m-%d"),
                    "right_date": pd.Timestamp(right["date"]).strftime("%Y-%m-%d"),
                    "left_provenance": str(left.get("price_provenance", "")),
                    "right_provenance": str(right.get("price_provenance", "")),
                    "panel_return": panel_gross - 1.0,
                    "idx_return": idx_gross - 1.0,
                    "return_delta": (panel_gross - 1.0) - (idx_gross - 1.0),
                    "gross_ratio": gross_ratio,
                    "expected_scale_gross_ratio": expected_ratio,
                    "scale_explained": bool(np.isclose(gross_ratio, expected_ratio, rtol=1e-6, atol=1e-6)),
                }
            )
    return pd.DataFrame(records)


def seam_summary(boundaries: pd.DataFrame) -> dict[str, Any]:
    if boundaries.empty:
        return {"boundaries": 0}
    abs_delta = boundaries["return_delta"].abs()
    provenance_change = boundaries["left_provenance"].ne(boundaries["right_provenance"])
    return {
        "boundaries": int(len(boundaries)),
        "scale_explained_boundaries": int(boundaries["scale_explained"].sum()),
        "scale_explained_rate": float(boundaries["scale_explained"].mean()),
        "provenance_change_boundaries": int(provenance_change.sum()),
        "median_abs_return_delta": float(abs_delta.median()),
        "p90_abs_return_delta": float(abs_delta.quantile(0.90)),
        "max_abs_return_delta": float(abs_delta.max()),
    }


def subset_diff(diff: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    left = normalize_keys(diff)
    right = normalize_keys(keys[["ticker", "date"]]).drop_duplicates(["ticker", "date"])
    out = left.merge(right, on=["ticker", "date"], how="inner", validate="one_to_one")
    if len(out) != len(right):
        raise RuntimeError(f"DIFF_KEY_COVERAGE_MISMATCH:{len(out)}!={len(right)}")
    return out


def exact_v4_fit_audit(summary: dict[str, Any], v4_diff: pd.DataFrame, affected: set[str]) -> dict[str, Any]:
    v4 = summary["v4_x1"]
    combined_path = Path(v4["parent_combined"])
    refit_root = Path(v4["final_refit_root"])
    combined = normalize_keys(pd.read_csv(combined_path))
    dates_path = refit_root / "v4_x1_final_training_dates.csv"
    fit_log_path = refit_root / "v4_x1_final_refit_log.json"
    refit_manifest = read_json(refit_root / "MANIFEST.json")
    expected_dates_sha = str((refit_manifest.get("output_hashes") or {}).get("training_dates") or "")
    expected_fit_sha = str((refit_manifest.get("output_hashes") or {}).get("fit_log") or "")
    if sha256_file(dates_path) != expected_dates_sha or sha256_file(fit_log_path) != expected_fit_sha:
        raise RuntimeError("V4_REFIT_OUTPUT_SHA_MISMATCH")
    dates = pd.read_csv(dates_path)
    dates["date"] = pd.to_datetime(dates["date"], errors="raise").dt.normalize()
    fit_log = json.loads(fit_log_path.read_text(encoding="utf-8"))
    if not isinstance(fit_log, list):
        raise RuntimeError("V4_FIT_LOG_NOT_LIST")

    results: dict[str, Any] = {}
    union_parts: list[pd.DataFrame] = []
    for head, support_col in (("H5", "h5_full_target_support"), ("H10", "h10_full_target_support")):
        if support_col not in combined.columns:
            raise RuntimeError(f"V4_SUPPORT_COLUMN_MISSING:{support_col}")
        date_set = set(dates.loc[dates["head"].astype(str).str.upper().eq(head), "date"])
        support = strict_bool(combined[support_col], label=support_col)
        keys = combined.loc[combined["date"].isin(date_set) & support, ["ticker", "date"]].drop_duplicates()
        expected_rows = sorted({int(r["training_rows"]) for r in fit_log if str(r.get("head", "")).upper() == head})
        if len(expected_rows) != 1 or len(keys) != expected_rows[0]:
            raise RuntimeError(f"V4_EXACT_FIT_ROW_COUNT_MISMATCH:{head}:{len(keys)}:{expected_rows}")
        exact = subset_diff(v4_diff, keys)
        results[head] = {
            "training_rows": int(len(keys)),
            **changed_scope_summary(exact, affected),
        }
        union_parts.append(keys)
    union_keys = pd.concat(union_parts, ignore_index=True).drop_duplicates(["ticker", "date"])
    union_diff = subset_diff(v4_diff, union_keys)
    results["UNION"] = {
        "training_rows": int(len(union_keys)),
        **changed_scope_summary(union_diff, affected),
    }
    results["verdict"] = (
        "V4_X1_EXACT_FIT_REPRESENTATION_BASIS_IMPACT_FOUND"
        if results["H5"]["changed_rows"] or results["H10"]["changed_rows"]
        else "V4_X1_EXACT_FIT_REPRESENTATION_BASIS_IMPACT_NOT_FOUND"
    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-1-root", type=Path, default=DEFAULT_V11_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    root = args.v1_1_root.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")
    _manifest, summary = verify_v11(root)

    basis = pd.read_csv(root / "panel_vs_idx_basis_rows.csv")
    runs = pd.read_csv(root / "stable_scale_runs.csv")
    v2_diff = pd.read_csv(root / "v2_training_feature_impact_rows.csv")
    v4_diff = pd.read_csv(root / "v4_x1_candidate_training_feature_impact_rows.csv")
    affected = set(runs["ticker"].astype(str).str.upper())

    stable_rows = basis["panel_idx_stable_run_member"]
    stable_mask = strict_bool(stable_rows, label="panel_idx_stable_run_member")
    stable_basis = basis.loc[stable_mask].copy()
    provenance_counts = stable_basis.get("price_provenance", pd.Series(dtype=str)).astype(str).value_counts().to_dict()
    boundaries = seam_boundaries(basis, runs)

    v2_scope = changed_scope_summary(v2_diff, affected)
    v4_candidate_scope = changed_scope_summary(v4_diff, affected)
    v4_exact = exact_v4_fit_audit(summary, v4_diff, affected)
    v4_exact_found = v4_exact["verdict"] == "V4_X1_EXACT_FIT_REPRESENTATION_BASIS_IMPACT_FOUND"

    result = {
        "schema_version": "training_price_basis_impact_audit_v1_2",
        "parent_v1_1_manifest_sha256": EXPECTED_V11_MANIFEST_SHA256,
        "guardrails": {
            "provider_calls": False,
            "model_fit": False,
            "model_scoring": False,
            "target_values_accessed": False,
            "protected_forward_accessed": False,
            "panel_mutated_in_place": False,
        },
        "basis_evidence": {
            "stable_scale_tickers": sorted(affected),
            "stable_scale_rows": int(stable_mask.sum()),
            "stable_rows_by_price_provenance": {str(k): int(v) for k, v in provenance_counts.items()},
            "seam_boundary_summary": seam_summary(boundaries),
        },
        "v2_clean_prepared_representation": {
            "verdict": (
                "V2_PREPARED_REPRESENTATION_BASIS_IMPACT_FOUND"
                if v2_scope["changed_rows"] else "V2_PREPARED_REPRESENTATION_BASIS_IMPACT_NOT_FOUND"
            ),
            **v2_scope,
        },
        "v4_x1_candidate_scope": v4_candidate_scope,
        "v4_x1_exact_fit_scope": v4_exact,
        "adjudication": {
            "training_lineage_status": (
                "PRICE_BASIS_CONTAMINATION_CONFIRMED_IN_FROZEN_MODEL_REPRESENTATIONS"
                if v2_scope["changed_rows"] and v4_exact_found
                else "PRICE_BASIS_TRAINING_IMPACT_PARTIAL_OR_UNRESOLVED"
            ),
            "retrain_authorized": False,
            "tradingview_full_acquisition_authorized": False,
            "next": "REVIEW_MAGNITUDE_AND_REMEDIATION_PROTOCOL_BEFORE_ANY_MODEL_REFIT_OR_FULL_TRADINGVIEW_ACQUISITION",
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    boundary_path = output / "price_basis_seam_boundaries.csv"
    boundaries.to_csv(boundary_path, index=False, lineterminator="\n")
    summary_path = output / "training_basis_impact_v1_2_summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_manifest = {
        "schema_version": "training_price_basis_impact_artifact_manifest_v1_2",
        "parent_v1_1_manifest_sha256": EXPECTED_V11_MANIFEST_SHA256,
        "guardrails": result["guardrails"],
        "output_hashes": {
            "seam_boundaries": sha256_file(boundary_path),
            "summary": sha256_file(summary_path),
        },
    }
    manifest_path = output / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(out_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**result, "artifact_manifest": str(manifest_path), "artifact_manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
