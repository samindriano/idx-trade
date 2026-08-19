"""Full-panel, outcome-blind official-IDX integrity audit.

This forensic runner uses only frozen local artifacts and already-captured IDX
Stock Summary bytes. It does not call providers, mutate canonical artifacts,
fit/score models, or access targets/protected outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
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

from idx_trade.frozen_panel_official_idx_integrity_audit import (  # noqa: E402
    apply_official_volume_counterfactual,
    build_volume_comparison,
    build_volume_feature_state,
    calendar_witness_diagnostics,
    candidate_official_active_gaps,
    compare_volume_feature_states,
    detect_volume_ratio_seams,
    normalize_ticker,
    official_active_valid_hlc_mask,
)
from idx_trade.ranking_v4_3_preregistration import build_primary_liquid_state  # noqa: E402

PROJECT = Path(r"D:\Documents\Project")
ARTIFACT_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "research_feasibility_1260_20260809"
PANEL_PATH = ARTIFACT_ROOT / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet"
CALENDAR_PATH = ARTIFACT_ROOT / "official_exchange_sessions_1260.csv"
STOCK_SUMMARY_ROOT = PROJECT / "idx-trade-foreign-flow-historical-20260814-v1"
DEFAULT_OUTPUT = PROJECT / "idx-trade-data-gate-20260808v" / "frozen_panel_official_idx_integrity_audit_v1_20260820"

PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label}_SHA_MISMATCH:{actual}!={expected}:{path}")


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


def load_official_idx_witness(root: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    paths = sorted(root.rglob("stock_summary.raw.json"))
    if not paths:
        raise RuntimeError(f"OFFICIAL_IDX_STOCK_SUMMARY_NOT_FOUND:{root}")
    parts: list[pd.DataFrame] = []
    accepted_files = 0
    rejected_files = 0
    dates: list[pd.Timestamp] = []
    for path in paths:
        try:
            day = pd.Timestamp(path.parent.name).normalize()
            raw = json.loads(path.read_text(encoding="utf-8"))
            rows = _stock_rows(raw)
        except Exception:
            rejected_files += 1
            continue
        if not rows:
            rejected_files += 1
            continue
        frame = pd.DataFrame(rows)
        required = {"StockCode", "High", "Low", "Close", "Volume", "Frequency", "Value"}
        if not required.issubset(frame.columns):
            rejected_files += 1
            continue
        out = pd.DataFrame(
            {
                "ticker": normalize_ticker(frame["StockCode"]),
                "date": day,
                "idx_high": pd.to_numeric(frame["High"], errors="coerce"),
                "idx_low": pd.to_numeric(frame["Low"], errors="coerce"),
                "idx_close": pd.to_numeric(frame["Close"], errors="coerce"),
                "idx_volume": pd.to_numeric(frame["Volume"], errors="coerce"),
                "idx_frequency": pd.to_numeric(frame["Frequency"], errors="coerce"),
                "idx_value": pd.to_numeric(frame["Value"], errors="coerce"),
            }
        )
        valid_identity = out["ticker"].ne("") & out["ticker"].str.fullmatch(r"[A-Z0-9]{4,5}", na=False)
        out = out.loc[valid_identity].copy()
        if out.empty:
            rejected_files += 1
            continue
        parts.append(out)
        accepted_files += 1
        dates.append(day)
    if not parts:
        raise RuntimeError("OFFICIAL_IDX_STOCK_SUMMARY_HAS_NO_INTEGRITY_WITNESS_ROWS")
    result = pd.concat(parts, ignore_index=True)
    if result.duplicated(["ticker", "date"]).any():
        dupes = result[result.duplicated(["ticker", "date"], keep=False)][["ticker", "date"]]
        raise RuntimeError(f"OFFICIAL_IDX_DUPLICATE_IDENTITY:{dupes.head(20).to_dict('records')}")
    result = result.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    return result, {
        "raw_files_found": int(len(paths)),
        "raw_files_accepted": int(accepted_files),
        "raw_files_rejected": int(rejected_files),
        "witness_rows": int(len(result)),
        "witness_tickers": int(result["ticker"].nunique()),
        "first_witness_date": min(dates).date().isoformat() if dates else None,
        "last_witness_date": max(dates).date().isoformat() if dates else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=PANEL_PATH)
    parser.add_argument("--calendar", type=Path, default=CALENDAR_PATH)
    parser.add_argument("--stock-summary-root", type=Path, default=STOCK_SUMMARY_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _ratio_stats(series: pd.Series) -> dict[str, float | int | None]:
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return {"n": 0, "median": None, "p01": None, "p05": None, "p95": None, "p99": None}
    return {
        "n": int(len(values)),
        "median": float(values.median()),
        "p01": float(values.quantile(0.01)),
        "p05": float(values.quantile(0.05)),
        "p95": float(values.quantile(0.95)),
        "p99": float(values.quantile(0.99)),
    }


def _parity_summary(block: pd.DataFrame) -> pd.Series:
    if block.empty:
        return pd.Series({"rows": 0, "exact_rate": np.nan, "within_1pct_rate": np.nan, "median_ratio": np.nan})
    comparable = block[block["volume_comparable"].astype(bool)]
    ratio = pd.to_numeric(comparable["panel_idx_volume_ratio"], errors="coerce").dropna()
    return pd.Series(
        {
            "rows": int(len(comparable)),
            "exact_rate": float(comparable["panel_idx_volume_exact"].mean()) if len(comparable) else np.nan,
            "within_1pct_rate": float(comparable["panel_idx_volume_within_1pct"].mean()) if len(comparable) else np.nan,
            "median_ratio": float(ratio.median()) if len(ratio) else np.nan,
        }
    )


def main() -> int:
    args = parse_args()
    panel_path = args.panel.resolve()
    calendar_path = args.calendar.resolve()
    stock_root = args.stock_summary_root.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    require_sha(panel_path, PANEL_SHA256, "FROZEN_PANEL")
    require_sha(calendar_path, CALENDAR_SHA256, "FROZEN_CALENDAR")

    panel = pd.read_parquet(panel_path)
    forbidden_tokens = ("target_rank", "realized_return", "binary_target", "label_status", "actual_up", "outcome")
    forbidden = [column for column in panel.columns if any(token in str(column).lower() for token in forbidden_tokens)]
    if forbidden:
        raise RuntimeError(f"OUTCOME_OR_LABEL_COLUMN_PRESENT:{sorted(forbidden)}")
    required_panel = {"ticker", "date", "high", "low", "close", "volume", "regular_market_value", "price_provenance"}
    missing = required_panel - set(panel.columns)
    if missing:
        raise RuntimeError(f"FROZEN_PANEL_MISSING_COLUMNS:{sorted(missing)}")

    calendar = pd.read_csv(calendar_path)
    if "date" not in calendar.columns:
        raise RuntimeError("CALENDAR_DATE_COLUMN_MISSING")
    sessions = pd.DatetimeIndex(pd.to_datetime(calendar["date"], errors="coerce")).tz_localize(None).normalize()
    if sessions.isna().any() or sessions.duplicated().any():
        raise RuntimeError("FROZEN_CALENDAR_INVALID")
    sessions = sessions.sort_values()

    witness, witness_meta = load_official_idx_witness(stock_root)
    comparison = build_volume_comparison(panel, witness)
    panel_dates = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    witness_dates = pd.DatetimeIndex(witness["date"].dropna().unique())
    panel_on_witness = panel.loc[panel_dates.isin(witness_dates), ["ticker", "date"]].drop_duplicates()
    overlap = comparison[["ticker", "date"]].drop_duplicates()
    overlap_rate = len(overlap) / len(panel_on_witness) if len(panel_on_witness) else 0.0

    comparable = comparison[comparison["volume_comparable"].astype(bool)].copy() if not comparison.empty else comparison.copy()
    exact = comparable["panel_idx_volume_exact"].astype(bool) if not comparable.empty else pd.Series(dtype=bool)
    mismatch = comparable.loc[~exact].copy() if len(exact) else comparable.copy()
    seams = detect_volume_ratio_seams(comparison, jump_factor=1.20)
    comparison["year"] = pd.to_datetime(comparison["date"]).dt.year
    by_provenance = comparison.groupby("price_provenance", dropna=False, sort=True).apply(_parity_summary, include_groups=False).reset_index()
    by_year = comparison.groupby("year", dropna=False, sort=True).apply(_parity_summary, include_groups=False).reset_index()

    calendar_diag = calendar_witness_diagnostics(witness, sessions)
    gaps = candidate_official_active_gaps(panel, witness, sessions)
    interior = gaps[gaps["gap_class"].eq("INTERIOR_OFFICIAL_ACTIVE_HLC_MISSING")].copy() if not gaps.empty else gaps.copy()
    leading = gaps[gaps["gap_class"].eq("LEADING_OFFICIAL_ACTIVE_HLC_MISSING")].copy() if not gaps.empty else gaps.copy()
    trailing = gaps[gaps["gap_class"].eq("TRAILING_OFFICIAL_ACTIVE_HLC_MISSING")].copy() if not gaps.empty else gaps.copy()

    official_active_overlap = comparison["official_active_valid_hlc"].astype(bool) if not comparison.empty else pd.Series(dtype=bool)
    panel_rows_without_official_active = comparison.loc[~official_active_overlap].copy() if len(official_active_overlap) else comparison.copy()

    primary = build_primary_liquid_state(panel, sessions)
    counterfactual, direct_volume_changes = apply_official_volume_counterfactual(panel, witness)
    before_features = build_volume_feature_state(panel, primary)
    after_features = build_volume_feature_state(counterfactual, primary)
    volume_feature_diff, feature_summary = compare_volume_feature_states(before_features, after_features)

    schema_diag = {
        "price_provenance_present": "price_provenance" in panel.columns,
        "volume_provenance_present": "volume_provenance" in panel.columns,
        "regular_market_value_provenance_present": "regular_market_value_provenance" in panel.columns,
        "open_provenance_present": "open_provenance" in panel.columns,
    }
    schema_diag["field_level_provenance_under_specified"] = not all(
        schema_diag[key]
        for key in (
            "volume_provenance_present",
            "regular_market_value_provenance_present",
            "open_provenance_present",
        )
    )

    active_omitted_calendar = len(calendar_diag["active_witness_dates_missing_from_calendar"])
    no_active_calendar = len(calendar_diag["calendar_sessions_without_any_official_active_valid_hlc"])
    no_witness_calendar = len(calendar_diag["calendar_sessions_without_any_stock_summary_witness"])
    mismatch_rows = int((~exact).sum()) if len(exact) else 0
    panel_nonactive_rows = int(len(panel_rows_without_official_active))
    interior_rows = int(len(interior))

    if active_omitted_calendar or no_witness_calendar:
        verdict = "FROZEN_PANEL_OFFICIAL_IDX_CALENDAR_INTEGRITY_ISSUE_FOUND"
    elif panel_nonactive_rows:
        verdict = "FROZEN_PANEL_OFFICIAL_IDX_ACTIVITY_SEMANTICS_ISSUE_FOUND"
    elif mismatch_rows and feature_summary["any_volume_representation_changed_rows"] > 0:
        verdict = "FROZEN_PANEL_OFFICIAL_IDX_VOLUME_REPRESENTATION_ISSUE_FOUND"
    elif mismatch_rows:
        verdict = "FROZEN_PANEL_OFFICIAL_IDX_VOLUME_MISMATCH_FOUND_NO_MEASURED_REPRESENTATION_CHANGE"
    elif interior_rows:
        verdict = "FROZEN_PANEL_OFFICIAL_IDX_INTERIOR_ACTIVE_COVERAGE_GAPS_FOUND"
    elif no_active_calendar:
        verdict = "FROZEN_PANEL_OFFICIAL_IDX_CALENDAR_ACTIVITY_WITNESS_ANOMALY_FOUND"
    else:
        verdict = "FROZEN_PANEL_OFFICIAL_IDX_NO_MATERIAL_ISSUE_ON_TESTED_DIMENSIONS"

    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "volume_mismatches": output / "full_panel_volume_mismatches.csv",
        "volume_seams": output / "full_panel_volume_ratio_seams_20pct.csv",
        "volume_by_provenance": output / "full_panel_volume_summary_by_provenance.csv",
        "volume_by_year": output / "full_panel_volume_summary_by_year.csv",
        "panel_rows_without_official_active": output / "panel_rows_without_official_active_valid_hlc.csv",
        "official_active_gaps": output / "official_active_hlc_missing_from_panel.csv",
        "interior_gaps": output / "official_active_hlc_interior_gaps.csv",
        "direct_volume_changes": output / "official_volume_counterfactual_direct_rows.csv",
        "volume_feature_changes": output / "official_volume_counterfactual_representation_changes.csv",
    }
    mismatch.to_csv(paths["volume_mismatches"], index=False, lineterminator="\n")
    seams.to_csv(paths["volume_seams"], index=False, lineterminator="\n")
    by_provenance.to_csv(paths["volume_by_provenance"], index=False, lineterminator="\n")
    by_year.to_csv(paths["volume_by_year"], index=False, lineterminator="\n")
    panel_rows_without_official_active.to_csv(paths["panel_rows_without_official_active"], index=False, lineterminator="\n")
    gaps.to_csv(paths["official_active_gaps"], index=False, lineterminator="\n")
    interior.to_csv(paths["interior_gaps"], index=False, lineterminator="\n")
    direct_volume_changes.to_csv(paths["direct_volume_changes"], index=False, lineterminator="\n")
    volume_feature_diff.loc[volume_feature_diff["any_volume_representation_changed"].astype(bool)].to_csv(
        paths["volume_feature_changes"], index=False, lineterminator="\n"
    )

    summary = {
        "schema_version": "frozen_panel_official_idx_integrity_audit_v1",
        "status": verdict,
        "frozen_inputs": {
            "panel": str(panel_path),
            "panel_sha256": PANEL_SHA256,
            "calendar": str(calendar_path),
            "calendar_sha256": CALENDAR_SHA256,
            "stock_summary_root": str(stock_root),
        },
        "witness": witness_meta,
        "coverage": {
            "frozen_panel_rows": int(len(panel)),
            "frozen_panel_tickers": int(panel["ticker"].astype(str).nunique()),
            "panel_rows_on_witness_dates": int(len(panel_on_witness)),
            "exact_ticker_date_overlap_rows": int(len(overlap)),
            "identity_overlap_rate_on_witness_dates": float(overlap_rate),
            "comparable_volume_rows": int(len(comparable)),
        },
        "volume_parity": {
            "exact_rows": int(exact.sum()) if len(exact) else 0,
            "mismatch_rows": mismatch_rows,
            "exact_rate": float(exact.mean()) if len(exact) else None,
            "within_1pct_rate": float(comparable["panel_idx_volume_within_1pct"].mean()) if len(comparable) else None,
            "panel_idx_volume_ratio": _ratio_stats(comparable.get("panel_idx_volume_ratio", pd.Series(dtype=float))),
            "ratio_seams_ge_20pct": int(len(seams)),
            "ratio_seams_with_price_provenance_change": int(seams["provenance_changed"].sum()) if len(seams) else 0,
            "panel_overlap_rows_without_official_active_valid_hlc": panel_nonactive_rows,
        },
        "calendar_integrity": calendar_diag,
        "official_active_hlc_missing_from_panel": {
            "total_candidate_rows": int(len(gaps)),
            "interior_rows": interior_rows,
            "interior_tickers": int(interior["ticker"].nunique()) if len(interior) else 0,
            "leading_rows": int(len(leading)),
            "leading_tickers": int(leading["ticker"].nunique()) if len(leading) else 0,
            "trailing_rows": int(len(trailing)),
            "trailing_tickers": int(trailing["ticker"].nunique()) if len(trailing) else 0,
            "interpretation": "forensic candidates only; especially leading/trailing rows can reflect listing, warm-up, CA, or admission-domain semantics rather than a data bug",
        },
        "bounded_official_volume_counterfactual": {
            "direct_volume_rows_changed": int(len(direct_volume_changes)),
            "direct_volume_tickers_changed": int(direct_volume_changes["ticker"].nunique()) if len(direct_volume_changes) else 0,
            **feature_summary,
            "interpretation": "full-panel official-overlap lower-bound counterfactual only; not remediation authorization",
        },
        "provenance_schema": schema_diag,
        "guardrails": {
            "provider_calls": False,
            "model_fit": False,
            "model_scoring": False,
            "target_values_accessed": False,
            "protected_forward_accessed": False,
            "parent_panel_overwritten": False,
            "repair_performed": False,
        },
        "next": "INDEPENDENT_REVIEW_ONLY; no repair/refit is authorized by this audit result",
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_hashes = {name: sha256_file(path) for name, path in paths.items()}
    output_hashes["summary"] = sha256_file(summary_path)
    manifest = {
        "schema_version": "frozen_panel_official_idx_integrity_audit_manifest_v1",
        "status": verdict,
        "guardrails": summary["guardrails"],
        "input_hashes": {"panel": PANEL_SHA256, "calendar": CALENDAR_SHA256},
        "output_hashes": output_hashes,
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
