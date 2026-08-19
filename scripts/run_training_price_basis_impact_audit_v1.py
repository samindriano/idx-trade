"""Offline Step-2 audit: official IDX price basis -> frozen V2/V4-X training lineage.

No provider calls, model fitting, model scoring, historical target
materialization, or protected-forward access are performed here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.training_price_basis_impact_audit import (  # noqa: E402
    V2_FULL_FEATURE_COLUMNS,
    add_hlc_basis_comparison,
    apply_hlc_counterfactual,
    build_v2_hgb_xs_market_features,
    feature_difference_table,
    feature_parity_summary,
    mark_stable_scale_runs,
    normalize_date,
    normalize_panel,
    normalize_ticker,
)


DEFAULT_PROJECT_ROOT = Path(r"D:\Documents\Project")
DEFAULT_ARTIFACT_ROOT = DEFAULT_PROJECT_ROOT / "idx-trade-data-gate-20260808v" / "research_feasibility_1260_20260809"
DEFAULT_STOCK_SUMMARY_ROOT = DEFAULT_PROJECT_ROOT / "idx-trade-foreign-flow-historical-20260814-v1"
DEFAULT_V2_REPLAY_ROOT = DEFAULT_PROJECT_ROOT / "idx-trade-data-gate-20260808v" / "pit_safe_historical_replay_v1_20260813_001"
DEFAULT_OUTPUT = DEFAULT_PROJECT_ROOT / "idx-trade-data-gate-20260808v" / "tradingview_v2_1_training_basis_impact_v1_20260820"

PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
V2_SECURITY_MASTER_SHA256 = "9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9"
V2_CLEAN_REPLAY_TABLE_SHA256 = "79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826"
V4_PARENT_MANIFEST_SHA256 = "12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43"
V4_READY_STATUS = "V4_X1_FINAL_REFIT_FROZEN_READY_FOR_FRESH_PROSPECTIVE_SCORING"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--stock-summary-root", type=Path, default=DEFAULT_STOCK_SUMMARY_ROOT)
    parser.add_argument("--v2-replay-root", type=Path, default=DEFAULT_V2_REPLAY_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha(path: Path, expected: str, label: str) -> Path:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label}_SHA_MISMATCH:{actual}!={expected}:{path}")
    return path


def find_named_hashed(root: Path, name: str, expected: str, label: str) -> Path:
    candidates = sorted(root.rglob(name))
    for path in candidates:
        if path.is_file() and sha256_file(path) == expected:
            return path
    raise RuntimeError(f"{label}_NOT_FOUND_BY_NAME_AND_SHA:{name}:{expected}:{root}")


def find_pattern_hashed(root: Path, pattern: str, expected: str, label: str) -> Path:
    candidates = sorted(path for path in root.rglob(pattern) if path.is_file())
    for path in candidates:
        if sha256_file(path) == expected:
            return path
    raise RuntimeError(f"{label}_NOT_FOUND_BY_PATTERN_AND_SHA:{pattern}:{expected}:{root}")


def _stock_rows(value: object) -> list[dict[str, Any]] | None:
    if isinstance(value, list):
        dicts = [row for row in value if isinstance(row, dict)]
        if dicts and any("StockCode" in row for row in dicts):
            return dicts
        for item in value:
            found = _stock_rows(item)
            if found is not None:
                return found
    elif isinstance(value, dict):
        if "StockCode" in value:
            return [value]
        for child in value.values():
            found = _stock_rows(child)
            if found is not None:
                return found
    return None


def load_official_idx_hlc(stock_summary_root: Path) -> pd.DataFrame:
    paths = sorted(stock_summary_root.rglob("stock_summary.raw.json"))
    if not paths:
        raise RuntimeError(f"OFFICIAL_IDX_STOCK_SUMMARY_NOT_FOUND:{stock_summary_root}")
    parts: list[pd.DataFrame] = []
    for path in paths:
        try:
            day = pd.Timestamp(path.parent.name).normalize()
        except Exception:
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = _stock_rows(raw)
        if not rows:
            continue
        frame = pd.DataFrame(rows)
        required = {"StockCode", "High", "Low", "Close"}
        if not required.issubset(frame.columns):
            continue
        out = pd.DataFrame(
            {
                "ticker": normalize_ticker(frame["StockCode"]),
                "date": day,
                "idx_high": pd.to_numeric(frame["High"], errors="coerce"),
                "idx_low": pd.to_numeric(frame["Low"], errors="coerce"),
                "idx_close": pd.to_numeric(frame["Close"], errors="coerce"),
            }
        )
        valid = (
            out["ticker"].ne("")
            & np.isfinite(out[["idx_high", "idx_low", "idx_close"]]).all(axis=1)
            & out[["idx_high", "idx_low", "idx_close"]].gt(0.0).all(axis=1)
        )
        parts.append(out.loc[valid])
    if not parts:
        raise RuntimeError("OFFICIAL_IDX_STOCK_SUMMARY_HAS_NO_VALID_HLC")
    result = pd.concat(parts, ignore_index=True)
    if result.duplicated(["ticker", "date"]).any():
        dupes = result[result.duplicated(["ticker", "date"], keep=False)][["ticker", "date"]]
        raise RuntimeError(f"OFFICIAL_IDX_DUPLICATE_IDENTITY:{dupes.head(10).to_dict('records')}")
    return result.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def load_calendar(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError("CALENDAR_DATE_COLUMN_MISSING")
    frame["date"] = normalize_date(frame["date"], label="calendar")
    if frame["date"].duplicated().any():
        raise RuntimeError("CALENDAR_DUPLICATE_DATE")
    return frame.sort_values("date", kind="mergesort").reset_index(drop=True)


def filter_listing_domain(panel: pd.DataFrame, security_master: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    data = normalize_panel(panel).drop(columns=["listed_from", "listed_to"], errors="ignore")
    required = {"ticker", "listed_from", "listed_to"}
    missing = required - set(security_master.columns)
    if missing:
        raise RuntimeError(f"V2_SECURITY_MASTER_MISSING_COLUMNS:{sorted(missing)}")
    master = security_master[["ticker", "listed_from", "listed_to"]].copy()
    master["ticker"] = normalize_ticker(master["ticker"])
    master["listed_from"] = pd.to_datetime(master["listed_from"], errors="coerce").dt.normalize()
    raw_to = master["listed_to"]
    master["listed_to"] = pd.to_datetime(raw_to, errors="coerce").dt.normalize()
    nonempty_to = raw_to.notna() & raw_to.astype(str).str.strip().ne("")
    if master["ticker"].eq("").any() or master["ticker"].duplicated().any():
        raise RuntimeError("V2_SECURITY_MASTER_IDENTITY_INVALID")
    if master["listed_from"].isna().any() or (nonempty_to & master["listed_to"].isna()).any():
        raise RuntimeError("V2_SECURITY_MASTER_DATE_INVALID")
    if (master["listed_to"].notna() & master["listed_to"].lt(master["listed_from"])).any():
        raise RuntimeError("V2_SECURITY_MASTER_INTERVAL_INVALID")
    merged = data.merge(master, on="ticker", how="left", validate="many_to_one", indicator="_master")
    missing_master = merged["_master"].ne("both")
    pre = (~missing_master) & merged["date"].lt(merged["listed_from"])
    post = (~missing_master) & merged["listed_to"].notna() & merged["date"].gt(merged["listed_to"])
    keep = ~(missing_master | pre | post)
    stats = {
        "input_rows": int(len(merged)),
        "admitted_rows": int(keep.sum()),
        "excluded_missing_master": int(missing_master.sum()),
        "excluded_pre_listing": int(pre.sum()),
        "excluded_post_listing": int(post.sum()),
    }
    out = merged.loc[keep].drop(columns=["_master", "listed_from", "listed_to"])
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True), stats


def load_v2_replay_table(root: Path) -> tuple[pd.DataFrame, Path]:
    for path in sorted(root.rglob("*.parquet")):
        if sha256_file(path) != V2_CLEAN_REPLAY_TABLE_SHA256:
            continue
        frame = pd.read_parquet(path)
        required = {"ticker", "date", *V2_FULL_FEATURE_COLUMNS}
        if required.issubset(frame.columns):
            frame["ticker"] = normalize_ticker(frame["ticker"])
            frame["date"] = normalize_date(frame["date"], label="V2 replay")
            if frame.duplicated(["ticker", "date"]).any():
                raise RuntimeError("V2_REPLAY_DUPLICATE_IDENTITY")
            return frame, path
    raise RuntimeError(f"V2_CLEAN_REPLAY_TABLE_NOT_FOUND:{root}:{V2_CLEAN_REPLAY_TABLE_SHA256}")


def import_hist_runner(repo_root: Path):
    path = repo_root / "scripts" / "run_v4_3r_historical_one_shot.py"
    spec = importlib.util.spec_from_file_location("v4_3r_hist_basis_audit", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("V4_HIST_RUNNER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_EXPECTED:{path}")
    return value


def discover_v4_final_refit(project_root: Path) -> tuple[Path, pd.DataFrame, dict[str, Any]]:
    for dates_path in sorted(project_root.rglob("v4_x1_final_training_dates.csv")):
        root = dates_path.parent
        manifest_path = root / "MANIFEST.json"
        summary_path = root / "summary.json"
        if not manifest_path.is_file() or not summary_path.is_file():
            continue
        try:
            manifest = read_json(manifest_path)
            summary = read_json(summary_path)
        except Exception:
            continue
        if manifest.get("schema_version") != "ranking_v4_x1_final_refit_manifest_v1":
            continue
        if manifest.get("status") != V4_READY_STATUS or summary.get("status") != V4_READY_STATUS:
            continue
        if manifest.get("provider_calls") is not False or manifest.get("protected_forward_accessed") is not False:
            continue
        expected = str((manifest.get("output_hashes") or {}).get("training_dates") or "")
        if not expected or sha256_file(dates_path) != expected:
            continue
        dates = pd.read_csv(dates_path)
        required = {"head", "session_index", "date"}
        if not required.issubset(dates.columns):
            continue
        dates["date"] = normalize_date(dates["date"], label="V4-X training dates")
        return root, dates, manifest
    raise RuntimeError(f"V4_X1_FINAL_REFIT_NOT_FOUND:{project_root}")


def discover_v4_inputs(project_root: Path, cfg: dict[str, Any]) -> dict[str, Path]:
    hashes = cfg["market_input_sha256"]
    paths = {
        "calendar": find_named_hashed(project_root, "official_exchange_sessions_1260.csv", hashes["calendar"], "V4_CALENDAR"),
        "panel": find_named_hashed(project_root, "model_safe_signal_research_panel_1260.parquet", hashes["panel"], "V4_PANEL"),
        "anchors": find_named_hashed(project_root, "tradability_anchors_1260.csv", hashes["anchors"], "V4_ANCHORS"),
        "intervals": find_named_hashed(project_root, "tradability_intervals_1260.csv", hashes["intervals"], "V4_INTERVALS"),
        "open_derivative_panel": find_named_hashed(project_root, "execution_open_candidate_panel_yahoo_tradingview.parquet", hashes["open_derivative_panel"], "V4_OPEN_DERIVATIVE"),
        "open_derivative_manifest": find_named_hashed(project_root, "artifact_manifest.json", hashes["open_derivative_manifest"], "V4_OPEN_DERIVATIVE_MANIFEST"),
        "overlay_parquet": find_named_hashed(project_root, "open_recovery_overlay.parquet", hashes["overlay_parquet"], "V4_OVERLAY"),
        "overlay_manifest": find_named_hashed(project_root, "manifest.json", hashes["overlay_manifest"], "V4_OVERLAY_MANIFEST"),
        "security_master": find_pattern_hashed(project_root, "*security*master*.csv", hashes["security_master"], "V4_SECURITY_MASTER"),
    }
    return paths


def discover_parent_combined(project_root: Path) -> tuple[pd.DataFrame, Path]:
    for path in sorted(project_root.rglob("v4_3_full_target_support_rows_idx_combined.csv")):
        manifest = path.parent / "MANIFEST.json"
        if manifest.is_file() and sha256_file(manifest) == V4_PARENT_MANIFEST_SHA256:
            frame = pd.read_csv(path)
            required = {"ticker", "date", "session_index"}
            if not required.issubset(frame.columns):
                raise RuntimeError("V4_PARENT_COMBINED_COLUMNS_MISSING")
            frame["ticker"] = normalize_ticker(frame["ticker"])
            frame["date"] = normalize_date(frame["date"], label="V4 combined")
            if frame.duplicated(["ticker", "date"]).any():
                raise RuntimeError("V4_PARENT_COMBINED_DUPLICATE_IDENTITY")
            return frame, path
    raise RuntimeError(f"V4_PARENT_COMBINED_NOT_FOUND:{project_root}")


def summarize_stable_runs(rows: pd.DataFrame) -> pd.DataFrame:
    stable = rows[rows["panel_idx_stable_run_member"].fillna(False).astype(bool)].copy()
    if stable.empty:
        return pd.DataFrame(columns=["ticker", "run_id", "factor", "start_date", "end_date", "rows", "price_provenance"])
    group_cols = ["ticker", "panel_idx_run_id", "panel_idx_factor_key"]
    records: list[dict[str, Any]] = []
    for keys, block in stable.groupby(group_cols, sort=True, dropna=False):
        provenance = ""
        if "price_provenance" in block.columns:
            provenance = "|".join(sorted(set(block["price_provenance"].dropna().astype(str))))
        records.append(
            {
                "ticker": keys[0],
                "run_id": int(keys[1]),
                "factor": float(keys[2]),
                "start_date": block["date"].min().strftime("%Y-%m-%d"),
                "end_date": block["date"].max().strftime("%Y-%m-%d"),
                "rows": int(len(block)),
                "price_provenance": provenance,
            }
        )
    return pd.DataFrame(records)


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    project_root = args.project_root.resolve()
    artifact_root = args.artifact_root.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    panel_path = require_sha(
        artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet",
        PANEL_SHA256,
        "FROZEN_PANEL",
    )
    calendar_path = require_sha(artifact_root / "official_exchange_sessions_1260.csv", CALENDAR_SHA256, "OFFICIAL_CALENDAR")
    panel = normalize_panel(pd.read_parquet(panel_path))
    calendar = load_calendar(calendar_path)
    official = load_official_idx_hlc(args.stock_summary_root.resolve())

    panel_view_cols = ["ticker", "date", "high", "low", "close"]
    if "price_provenance" in panel.columns:
        panel_view_cols.append("price_provenance")
    panel_view = panel[panel_view_cols].rename(columns={"high": "panel_high", "low": "panel_low", "close": "panel_close"})
    basis = panel_view.merge(official, on=["ticker", "date"], how="inner", validate="one_to_one")
    basis = add_hlc_basis_comparison(
        basis,
        left_prefix="panel_",
        right_prefix="idx_",
        result_prefix="panel_idx",
    )
    basis = mark_stable_scale_runs(
        basis,
        calendar["date"],
        factor_column="panel_idx_scale_factor",
        prefix="panel_idx",
    )
    stable_runs = summarize_stable_runs(basis)
    counterfactual_panel, counterfactual_rows = apply_hlc_counterfactual(
        panel,
        basis,
        member_column="panel_idx_stable_run_member",
    )

    # V2 current clean historical replay lineage. We first prove local feature
    # reconstruction parity against the immutable 292,631-row replay artifact.
    v2_master_path = find_pattern_hashed(project_root, "*security*master*.csv", V2_SECURITY_MASTER_SHA256, "V2_SECURITY_MASTER")
    v2_master = pd.read_csv(v2_master_path)
    v2_original_panel, v2_listing_stats = filter_listing_domain(panel, v2_master)
    v2_counter_panel, v2_counter_listing_stats = filter_listing_domain(counterfactual_panel, v2_master)
    if v2_listing_stats != v2_counter_listing_stats:
        raise RuntimeError(f"V2_LISTING_GATE_CHANGED_UNEXPECTEDLY:{v2_listing_stats}!={v2_counter_listing_stats}")
    v2_original_features = build_v2_hgb_xs_market_features(v2_original_panel, calendar["date"])
    v2_counter_features = build_v2_hgb_xs_market_features(v2_counter_panel, calendar["date"])
    v2_replay, v2_replay_path = load_v2_replay_table(args.v2_replay_root.resolve())
    v2_keys = v2_replay[["ticker", "date"]].copy()
    v2_parity = feature_difference_table(
        v2_original_features,
        v2_replay,
        feature_columns=V2_FULL_FEATURE_COLUMNS,
        keys=v2_keys,
    )
    v2_parity_summary = feature_parity_summary(v2_parity)
    if len(v2_parity) != len(v2_replay):
        v2_verdict = "V2_TRAINING_IMPACT_UNRESOLVED_CACHE_OR_PARITY"
    elif v2_parity_summary["changed_rows"] != 0:
        v2_verdict = "V2_TRAINING_IMPACT_UNRESOLVED_CACHE_OR_PARITY"
    else:
        v2_impact = feature_difference_table(
            v2_original_features,
            v2_counter_features,
            feature_columns=V2_FULL_FEATURE_COLUMNS,
            keys=v2_keys,
        )
        v2_impact_summary = feature_parity_summary(v2_impact)
        v2_verdict = (
            "V2_NO_TRAINING_SCALE_BASIS_IMPACT"
            if v2_impact_summary["changed_rows"] == 0
            else "V2_TRAINING_SCALE_BASIS_IMPACT_FOUND"
        )
    if "v2_impact" not in locals():
        v2_impact = pd.DataFrame()
        v2_impact_summary = {"rows": 0, "changed_rows": 0, "changed_cells": 0, "changed_row_rate": 0.0, "changed_feature_counts": {}}

    # V4-X: exact frozen feature/model-frame code. We intentionally stop before
    # materialize_v4_target_ledger; all final-training-date model-frame rows are
    # audited as an outcome-free superset of actual H5/H10 fit rows.
    cfg = read_json(repo_root / "config" / "ranking_v4_x1_final_refit_v1.json")
    v4_paths = discover_v4_inputs(project_root, cfg)
    if v4_paths["panel"].resolve() != panel_path.resolve():
        raise RuntimeError("V4_PANEL_PATH_DIFFERS_FROM_FROZEN_SHARED_PANEL")
    hist = import_hist_runner(repo_root)
    v4_calendar = load_calendar(v4_paths["calendar"])
    v4_calendar["session_index"] = np.arange(len(v4_calendar), dtype=np.int64)
    combined, combined_path = discover_parent_combined(project_root)
    derivative = pd.read_parquet(v4_paths["open_derivative_panel"])
    overlay = pd.read_parquet(v4_paths["overlay_parquet"])
    anchors = pd.read_csv(v4_paths["anchors"])
    intervals = pd.read_csv(v4_paths["intervals"])
    v4_master = pd.read_csv(v4_paths["security_master"])

    original_features, original_pit = hist.build_v4_control_feature_table(panel, v4_calendar["date"], v4_master)
    counter_features, counter_pit = hist.build_v4_control_feature_table(counterfactual_panel, v4_calendar["date"], v4_master)
    original_price, original_price_stats = hist.build_price_evidence(panel, v4_calendar, derivative, overlay, anchors, intervals)
    counter_price, counter_price_stats = hist.build_price_evidence(counterfactual_panel, v4_calendar, derivative, overlay, anchors, intervals)
    original_model_frame = hist.prepare_model_frame(original_features, combined, original_price)
    counter_model_frame = hist.prepare_model_frame(counter_features, combined, counter_price)

    v4_refit_root, v4_training_dates, v4_refit_manifest = discover_v4_final_refit(project_root)
    v4_keys = original_model_frame[
        original_model_frame["date"].isin(set(v4_training_dates["date"]))
    ][["ticker", "date"]].drop_duplicates()
    v4_feature_columns = tuple(hist.V4_CONTROL_FEATURE_COLUMNS) + tuple(hist.SESSION_GEOMETRY_FEATURE_COLUMNS)
    v4_impact = feature_difference_table(
        original_model_frame,
        counter_model_frame,
        feature_columns=v4_feature_columns,
        keys=v4_keys,
    )
    v4_impact_summary = feature_parity_summary(v4_impact)
    v4_verdict = (
        "V4_X1_NO_TRAINING_SCALE_BASIS_IMPACT"
        if v4_impact_summary["changed_rows"] == 0
        else "V4_X1_POTENTIAL_TRAINING_SCALE_BASIS_IMPACT_FOUND"
    )

    if v2_verdict == "V2_NO_TRAINING_SCALE_BASIS_IMPACT" and v4_verdict == "V4_X1_NO_TRAINING_SCALE_BASIS_IMPACT":
        combined_verdict = "FROZEN_TRAINING_PANEL_BASIS_IMPACT_NOT_FOUND"
    elif v2_verdict == "V2_TRAINING_SCALE_BASIS_IMPACT_FOUND" or v4_verdict == "V4_X1_POTENTIAL_TRAINING_SCALE_BASIS_IMPACT_FOUND":
        combined_verdict = "FROZEN_TRAINING_PANEL_BASIS_IMPACT_FOUND"
    else:
        combined_verdict = "FROZEN_TRAINING_PANEL_BASIS_IMPACT_UNRESOLVED"

    output.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {
        "panel_basis_rows": output / "panel_vs_idx_basis_rows.csv",
        "stable_scale_runs": output / "stable_scale_runs.csv",
        "counterfactual_hlc_rows": output / "counterfactual_hlc_rows.csv",
        "v2_parity_rows": output / "v2_reconstruction_parity_rows.csv",
        "v2_impact_rows": output / "v2_training_feature_impact_rows.csv",
        "v4_impact_rows": output / "v4_x1_candidate_training_feature_impact_rows.csv",
    }
    basis.to_csv(outputs["panel_basis_rows"], index=False, lineterminator="\n")
    stable_runs.to_csv(outputs["stable_scale_runs"], index=False, lineterminator="\n")
    counterfactual_rows.to_csv(outputs["counterfactual_hlc_rows"], index=False, lineterminator="\n")
    v2_parity.to_csv(outputs["v2_parity_rows"], index=False, lineterminator="\n")
    v2_impact.to_csv(outputs["v2_impact_rows"], index=False, lineterminator="\n")
    v4_impact.to_csv(outputs["v4_impact_rows"], index=False, lineterminator="\n")

    panel_basis_summary = {
        "panel_rows": int(len(panel)),
        "official_idx_rows": int(len(official)),
        "overlap_rows": int(len(basis)),
        "hlc_exact_rows": int(basis["panel_idx_hlc_exact"].sum()),
        "hlc_exact_rate": float(basis["panel_idx_hlc_exact"].mean()) if len(basis) else None,
        "row_scale_consistent_mismatch_rows": int(basis["panel_idx_row_scale_consistent"].sum()),
        "stable_scale_rows": int(basis["panel_idx_stable_run_member"].sum()),
        "stable_scale_runs": int(len(stable_runs)),
        "stable_scale_tickers": int(stable_runs["ticker"].nunique()) if len(stable_runs) else 0,
    }
    summary = {
        "schema_version": "training_price_basis_impact_audit_v1",
        "status": combined_verdict,
        "guardrails": {
            "provider_calls": False,
            "model_fit": False,
            "model_scoring": False,
            "historical_target_materialized": False,
            "protected_forward_accessed": False,
            "panel_mutated_in_place": False,
        },
        "shared_frozen_panel_sha256": PANEL_SHA256,
        "panel_idx_basis": panel_basis_summary,
        "v2_clean_replay": {
            "verdict": v2_verdict,
            "listing_gate": v2_listing_stats,
            "replay_table": str(v2_replay_path),
            "replay_table_sha256": V2_CLEAN_REPLAY_TABLE_SHA256,
            "replay_rows": int(len(v2_replay)),
            "reconstruction_parity": v2_parity_summary,
            "counterfactual_feature_impact": v2_impact_summary,
        },
        "v4_x1": {
            "verdict": v4_verdict,
            "audit_scope": "OUTCOME_FREE_SUPERSET_OF_FINAL_H5_H10_TRAINING_ROWS_ON_FINAL_TRAINING_DATES",
            "final_refit_root": str(v4_refit_root),
            "final_refit_status": v4_refit_manifest.get("status"),
            "candidate_rows": int(len(v4_impact)),
            "counterfactual_feature_impact": v4_impact_summary,
            "original_pit_diagnostics": original_pit.__dict__,
            "counterfactual_pit_diagnostics": counter_pit.__dict__,
            "original_price_evidence": original_price_stats,
            "counterfactual_price_evidence": counter_price_stats,
            "parent_combined": str(combined_path),
            "parent_manifest_sha256": V4_PARENT_MANIFEST_SHA256,
        },
        "adjudication": {
            "verdict": combined_verdict,
            "interpretation": (
                "No stable official-IDX-vs-panel scale basis regime changes frozen V2 or V4-X training representations."
                if combined_verdict == "FROZEN_TRAINING_PANEL_BASIS_IMPACT_NOT_FOUND"
                else "At least one frozen training representation changes under a stable official-IDX scale-basis counterfactual; no retraining is authorized by this audit."
                if combined_verdict == "FROZEN_TRAINING_PANEL_BASIS_IMPACT_FOUND"
                else "Training impact could not be resolved under the frozen parity/input guards."
            ),
        },
    }
    summary_path = output / "training_basis_impact_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs["summary"] = summary_path
    manifest = {
        "schema_version": "training_price_basis_impact_artifact_manifest_v1",
        "status": combined_verdict,
        "inputs": {
            "panel": {"path": str(panel_path), "sha256": PANEL_SHA256},
            "calendar": {"path": str(calendar_path), "sha256": CALENDAR_SHA256},
            "v2_security_master": {"path": str(v2_master_path), "sha256": V2_SECURITY_MASTER_SHA256},
            "v2_clean_replay": {"path": str(v2_replay_path), "sha256": V2_CLEAN_REPLAY_TABLE_SHA256},
            "v4_parent_combined": {"path": str(combined_path), "manifest_sha256": V4_PARENT_MANIFEST_SHA256},
            "v4_final_refit_root": str(v4_refit_root),
        },
        "guardrails": summary["guardrails"],
        "output_hashes": {name: sha256_file(path) for name, path in outputs.items()},
    }
    manifest_path = output / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    console = {
        "panel_idx_basis": panel_basis_summary,
        "stable_scale_runs": stable_runs.to_dict("records"),
        "v2_clean_replay": summary["v2_clean_replay"],
        "v4_x1": summary["v4_x1"],
        "adjudication": summary["adjudication"],
        "artifact_manifest": str(manifest_path),
        "artifact_manifest_sha256": sha256_file(manifest_path),
    }
    print(json.dumps(console, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
