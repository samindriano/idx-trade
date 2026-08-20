"""Outcome-blind audit of row-based feature windows versus IDX exchange sessions.

The audit measures effective exchange-session horizons on the frozen panel and
restricts the census to V2 prepared support plus exact V4-X final-fit H5/H10
rows. It does not change feature definitions, repair data, fit/score models, or
read target values/protected-forward outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.feature_window_session_semantics_audit import (  # noqa: E402
    WINDOW_SPECS,
    build_session_span_state,
    normalize_date,
    normalize_ticker,
    subset_state,
    summarize_support,
)

PROJECT = Path(r"D:\Documents\Project")
ARTIFACT_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "research_feasibility_1260_20260809"
DEFAULT_V11_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "tradingview_v2_1_training_basis_impact_v1_1_20260820"
DEFAULT_INTEGRITY_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "frozen_panel_official_idx_integrity_audit_v1_20260820"
DEFAULT_OUTPUT = PROJECT / "idx-trade-data-gate-20260808v" / "feature_window_session_semantics_audit_v1_20260820"
PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
V11_MANIFEST_SHA256 = "62562fa3f1d949c3e4f9e225aae13b116a5e2c00dffcceab6240ebb07ea422d6"
INTEGRITY_MANIFEST_SHA256 = "bf87e0c8ce49468113eec32cb7df931ff0df887444de727a57c65b495d87c016"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_EXPECTED:{path}")
    return value


def strict_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    seen = set(normalized.dropna().unique())
    if not seen.issubset({"true", "false"}):
        raise RuntimeError(f"INVALID_BOOLEAN:{label}:{sorted(seen)}")
    return normalized.eq("true")


def normalize_keys(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["ticker"] = normalize_ticker(out["ticker"])
    out["date"] = normalize_date(out["date"], "keys.date")
    return out


def verify_v11(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = root / "artifact_manifest.json"
    actual = sha256_file(manifest_path)
    if actual != V11_MANIFEST_SHA256:
        raise RuntimeError(f"V11_MANIFEST_SHA_MISMATCH:{actual}")
    manifest = read_json(manifest_path)
    summary = read_json(root / "training_basis_impact_summary.json")
    hashes = manifest.get("output_hashes") or {}
    for name, filename in (
        ("v2_impact_rows", "v2_training_feature_impact_rows.csv"),
        ("summary", "training_basis_impact_summary.json"),
    ):
        expected = str(hashes.get(name) or "")
        actual_hash = sha256_file(root / filename)
        if not expected or actual_hash != expected:
            raise RuntimeError(f"V11_OUTPUT_SHA_MISMATCH:{name}:{actual_hash}!={expected}")
    return manifest, summary


def verify_integrity(root: Path) -> dict[str, Any]:
    manifest_path = root / "MANIFEST.json"
    actual = sha256_file(manifest_path)
    if actual != INTEGRITY_MANIFEST_SHA256:
        raise RuntimeError(f"INTEGRITY_MANIFEST_SHA_MISMATCH:{actual}")
    summary = read_json(root / "summary.json")
    if summary.get("status") != "FROZEN_PANEL_OFFICIAL_IDX_NO_MATERIAL_ISSUE_ON_TESTED_DIMENSIONS":
        raise RuntimeError("PARENT_INTEGRITY_STATUS_CHANGED")
    missing = summary.get("official_active_hlc_missing_from_panel") or {}
    calendar = summary.get("calendar_integrity") or {}
    if int(missing.get("total_candidate_rows", -1)) != 0:
        raise RuntimeError("PARENT_INTEGRITY_ACTIVE_ROW_GAPS_NOT_ZERO")
    if calendar.get("active_witness_dates_missing_from_calendar"):
        raise RuntimeError("PARENT_INTEGRITY_CALENDAR_MISSING_ACTIVE_DATES")
    if calendar.get("calendar_sessions_without_any_stock_summary_witness"):
        raise RuntimeError("PARENT_INTEGRITY_CALENDAR_WITHOUT_WITNESS")
    return summary


def exact_v4_fit_keys(summary: dict[str, Any]) -> dict[str, pd.DataFrame]:
    v4 = summary.get("v4_x1") or {}
    combined_path = Path(str(v4.get("parent_combined") or ""))
    refit_root = Path(str(v4.get("final_refit_root") or ""))
    if not combined_path.is_file() or not refit_root.is_dir():
        raise RuntimeError("V4_EXACT_FIT_LINEAGE_PATHS_MISSING")

    combined = normalize_keys(pd.read_csv(combined_path))
    refit_manifest = read_json(refit_root / "MANIFEST.json")
    hashes = refit_manifest.get("output_hashes") or {}
    dates_path = refit_root / "v4_x1_final_training_dates.csv"
    fit_log_path = refit_root / "v4_x1_final_refit_log.json"
    if sha256_file(dates_path) != str(hashes.get("training_dates") or ""):
        raise RuntimeError("V4_TRAINING_DATES_SHA_MISMATCH")
    if sha256_file(fit_log_path) != str(hashes.get("fit_log") or ""):
        raise RuntimeError("V4_FIT_LOG_SHA_MISMATCH")

    dates = pd.read_csv(dates_path)
    dates["date"] = normalize_date(dates["date"], "v4.training_dates")
    fit_log = json.loads(fit_log_path.read_text(encoding="utf-8"))
    if not isinstance(fit_log, list):
        raise RuntimeError("V4_FIT_LOG_NOT_LIST")

    result: dict[str, pd.DataFrame] = {}
    for head, support_col in (("H5", "h5_full_target_support"), ("H10", "h10_full_target_support")):
        if support_col not in combined.columns:
            raise RuntimeError(f"V4_SUPPORT_COLUMN_MISSING:{support_col}")
        date_set = set(dates.loc[dates["head"].astype(str).str.upper().eq(head), "date"])
        support = strict_bool(combined[support_col], support_col)
        keys = combined.loc[
            combined["date"].isin(date_set) & support, ["ticker", "date"]
        ].drop_duplicates(["ticker", "date"])
        expected_rows = sorted(
            {int(row["training_rows"]) for row in fit_log if str(row.get("head", "")).upper() == head}
        )
        if len(expected_rows) != 1 or len(keys) != expected_rows[0]:
            raise RuntimeError(f"V4_EXACT_FIT_ROW_COUNT_MISMATCH:{head}:{len(keys)}:{expected_rows}")
        result[head] = keys
    result["UNION"] = pd.concat([result["H5"], result["H10"]], ignore_index=True).drop_duplicates(
        ["ticker", "date"]
    )
    return result


def extended_rows(state: pd.DataFrame, support_sets: dict[str, set[tuple[str, pd.Timestamp]]]) -> pd.DataFrame:
    out = state.copy()
    any_extended = pd.Series(False, index=out.index)
    for name, (_, nominal) in WINDOW_SPECS.items():
        flag = pd.to_numeric(out[f"{name}_effective_sessions"], errors="coerce").gt(float(nominal))
        out[f"extended__{name}"] = flag
        any_extended |= flag
    out = out.loc[any_extended].copy()
    identities = list(zip(out["ticker"], out["date"], strict=False))
    for label, support in support_sets.items():
        out[f"support__{label}"] = [identity in support for identity in identities]
    keep = [
        "ticker", "date", "session_index",
        *[f"{name}_effective_sessions" for name in WINDOW_SPECS],
        *[f"extended__{name}" for name in WINDOW_SPECS],
        *[f"support__{label}" for label in support_sets],
    ]
    return out[keep].sort_values(["date", "ticker"], kind="mergesort")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-root", type=Path, default=ARTIFACT_ROOT)
    p.add_argument("--v1-1-root", type=Path, default=DEFAULT_V11_ROOT)
    p.add_argument("--integrity-root", type=Path, default=DEFAULT_INTEGRITY_ROOT)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    artifact_root = args.artifact_root.resolve()
    v11_root = args.v1_1_root.resolve()
    integrity_root = args.integrity_root.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    panel_path = artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet"
    calendar_path = artifact_root / "official_exchange_sessions_1260.csv"
    if sha256_file(panel_path) != PANEL_SHA256:
        raise RuntimeError("FROZEN_PANEL_SHA_MISMATCH")
    if sha256_file(calendar_path) != CALENDAR_SHA256:
        raise RuntimeError("FROZEN_CALENDAR_SHA_MISMATCH")
    v11_manifest, v11_summary = verify_v11(v11_root)
    integrity_summary = verify_integrity(integrity_root)

    panel = pd.read_parquet(panel_path, columns=["ticker", "date"])
    calendar = pd.read_csv(calendar_path, usecols=["date"])
    calendar["date"] = normalize_date(calendar["date"], "calendar.date")
    if calendar["date"].duplicated().any():
        raise RuntimeError("FROZEN_CALENDAR_DUPLICATE_DATE")
    state = build_session_span_state(panel, calendar["date"])

    v2_keys = normalize_keys(pd.read_csv(v11_root / "v2_training_feature_impact_rows.csv", usecols=["ticker", "date"]))
    v2_keys = v2_keys.drop_duplicates(["ticker", "date"])
    v4_keys = exact_v4_fit_keys(v11_summary)

    support_frames = {
        "V2_PREPARED": subset_state(state, v2_keys, "V2_PREPARED"),
        "V4_H5_EXACT_FIT": subset_state(state, v4_keys["H5"], "V4_H5_EXACT_FIT"),
        "V4_H10_EXACT_FIT": subset_state(state, v4_keys["H10"], "V4_H10_EXACT_FIT"),
        "V4_UNION_EXACT_FIT": subset_state(state, v4_keys["UNION"], "V4_UNION_EXACT_FIT"),
    }
    summaries = {label: summarize_support(frame) for label, frame in support_frames.items()}

    v4_extended = any(
        int(window["extended_rows"]) > 0
        for window in summaries["V4_UNION_EXACT_FIT"]["windows"].values()
    )
    v2_extended = any(
        int(window["extended_rows"]) > 0
        for window in summaries["V2_PREPARED"]["windows"].values()
    )
    verdict = (
        "OBSERVED_BAR_VS_EXCHANGE_SESSION_HORIZON_DIVERGENCE_CONFIRMED"
        if v4_extended or v2_extended
        else "NO_OBSERVED_BAR_VS_EXCHANGE_SESSION_HORIZON_DIVERGENCE_ON_TESTED_SUPPORT"
    )

    support_sets = {
        label: set(zip(frame["ticker"], frame["date"], strict=False))
        for label, frame in support_frames.items()
    }
    evidence = extended_rows(state, support_sets)

    result = {
        "schema_version": "feature_window_session_semantics_audit_v1",
        "status": verdict,
        "interpretation": (
            "A confirmed divergence is a feature-semantics finding, not leakage and not proof of bad raw data. "
            "The frozen feature builder uses per-ticker observed-row shift/rolling for return/ATR/geometry/volume/value windows."
        ),
        "parent_integrity": {
            "status": integrity_summary["status"],
            "official_active_hlc_missing_from_panel_rows": int(
                integrity_summary["official_active_hlc_missing_from_panel"]["total_candidate_rows"]
            ),
            "calendar_sessions": int(integrity_summary["calendar_integrity"]["calendar_sessions"]),
            "implication": "extended horizons cannot be attributed to missing official ACTIVE valid-HLC rows on the tested frozen panel",
        },
        "support": summaries,
        "v4_primary_liquidity_note": (
            "The separate V4 primary-liquidity 60-session state is already exchange-session bounded in ranking_v4_3_features.py; "
            "this audit targets row-based return/ATR/high-low/relative-volume/relative-value windows."
        ),
        "guardrails": {
            "provider_calls": False,
            "repair_performed": False,
            "feature_definition_changed": False,
            "model_fit": False,
            "model_scoring": False,
            "target_values_accessed": False,
            "protected_forward_accessed": False,
            "parent_panel_overwritten": False,
        },
        "frozen_inputs": {
            "panel": str(panel_path),
            "panel_sha256": PANEL_SHA256,
            "calendar": str(calendar_path),
            "calendar_sha256": CALENDAR_SHA256,
            "v1_1_manifest_sha256": V11_MANIFEST_SHA256,
            "integrity_manifest_sha256": INTEGRITY_MANIFEST_SHA256,
        },
        "next": (
            "INDEPENDENT_REVIEW_AND_DECIDE_IF_OBSERVED_BAR_HORIZON_IS_INTENDED; DO_NOT CHANGE V4-X1 FEATURE DEFINITION INSIDE PRICE-BASIS REMEDIATION"
            if verdict.startswith("OBSERVED_BAR")
            else "CLOSE_WINDOW_SEMANTICS_CONCERN_ON_TESTED_SUPPORT"
        ),
    }

    output.mkdir(parents=True, exist_ok=True)
    evidence_path = output / "extended_window_rows.csv"
    summary_path = output / "summary.json"
    evidence.to_csv(evidence_path, index=False, lineterminator="\n")
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "feature_window_session_semantics_audit_manifest_v1",
        "status": verdict,
        "guardrails": result["guardrails"],
        "parent_hashes": result["frozen_inputs"],
        "output_hashes": {
            "extended_window_rows": sha256_file(evidence_path),
            "summary": sha256_file(summary_path),
        },
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**result, "manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
