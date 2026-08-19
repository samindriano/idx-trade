"""Bounded, outcome-blind Regular-Market Value basis audit.

Purpose
-------
Compare the frozen research-panel ``regular_market_value`` field with official
IDX Stock Summary ``Value`` on exact ticker/date overlap, then measure bounded
representation and primary-liquidity effects of an official-value
counterfactual.  This is an audit only: no provider calls, no model fitting or
scoring, no target/outcome materialization, and no parent-artifact mutation.
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

from idx_trade.ranking_v4_3_preregistration import build_primary_liquid_state  # noqa: E402
from idx_trade.regular_market_value_basis_audit import (  # noqa: E402
    apply_official_value_counterfactual,
    build_value_comparison,
    build_value_feature_state,
    compare_value_feature_states,
    detect_ratio_seams,
    normalize_ticker,
    ratio_summary,
)

PROJECT = Path(r"D:\Documents\Project")
ARTIFACT_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "research_feasibility_1260_20260809"
PANEL_PATH = ARTIFACT_ROOT / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet"
CALENDAR_PATH = ARTIFACT_ROOT / "official_exchange_sessions_1260.csv"
STOCK_SUMMARY_ROOT = PROJECT / "idx-trade-foreign-flow-historical-20260814-v1"
DEFAULT_OUTPUT = PROJECT / "idx-trade-data-gate-20260808v" / "regular_market_value_basis_audit_v1_20260820"

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


def load_official_idx_value(root: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
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
        required = {"StockCode", "Close", "Volume", "Value"}
        if not required.issubset(frame.columns):
            rejected_files += 1
            continue
        out = pd.DataFrame({
            "ticker": normalize_ticker(frame["StockCode"]),
            "date": day,
            "idx_close": pd.to_numeric(frame["Close"], errors="coerce"),
            "idx_volume": pd.to_numeric(frame["Volume"], errors="coerce"),
            "idx_regular_market_value": pd.to_numeric(frame["Value"], errors="coerce"),
        })
        valid_identity = out["ticker"].ne("") & out["ticker"].str.fullmatch(r"[A-Z0-9]{4,5}", na=False)
        out = out.loc[valid_identity].copy()
        if out.empty:
            rejected_files += 1
            continue
        parts.append(out)
        accepted_files += 1
        dates.append(day)
    if not parts:
        raise RuntimeError("OFFICIAL_IDX_STOCK_SUMMARY_HAS_NO_VALUE_ROWS")
    result = pd.concat(parts, ignore_index=True)
    if result.duplicated(["ticker", "date"]).any():
        dupes = result[result.duplicated(["ticker", "date"], keep=False)][["ticker", "date"]]
        raise RuntimeError(f"OFFICIAL_IDX_DUPLICATE_IDENTITY:{dupes.head(20).to_dict('records')}")
    result = result.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    meta = {
        "raw_files_found": int(len(paths)),
        "raw_files_accepted": int(accepted_files),
        "raw_files_rejected": int(rejected_files),
        "witness_rows": int(len(result)),
        "witness_tickers": int(result["ticker"].nunique()),
        "first_witness_date": min(dates).date().isoformat() if dates else None,
        "last_witness_date": max(dates).date().isoformat() if dates else None,
    }
    return result, meta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=PANEL_PATH)
    parser.add_argument("--calendar", type=Path, default=CALENDAR_PATH)
    parser.add_argument("--stock-summary-root", type=Path, default=STOCK_SUMMARY_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _finite_summary(series: pd.Series) -> dict[str, float | int | None]:
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
    required_panel = {
        "ticker", "date", "close", "volume", "regular_market_value", "price_provenance"
    }
    missing = required_panel - set(panel.columns)
    if missing:
        raise RuntimeError(f"FROZEN_PANEL_MISSING_COLUMNS:{sorted(missing)}")
    forbidden_tokens = ("target_rank", "realized_return", "binary_target", "label_status", "outcome")
    forbidden = [column for column in panel.columns if any(token in str(column).lower() for token in forbidden_tokens)]
    if forbidden:
        raise RuntimeError(f"OUTCOME_OR_LABEL_COLUMN_PRESENT:{sorted(forbidden)}")

    calendar = pd.read_csv(calendar_path)
    if "date" not in calendar.columns:
        raise RuntimeError("CALENDAR_DATE_COLUMN_MISSING")
    sessions = pd.DatetimeIndex(pd.to_datetime(calendar["date"], errors="coerce")).tz_localize(None).normalize()
    if sessions.isna().any() or sessions.duplicated().any():
        raise RuntimeError("FROZEN_CALENDAR_INVALID")

    idx, witness_meta = load_official_idx_value(stock_root)
    comparison = build_value_comparison(panel, idx)

    panel_dates = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    witness_dates = pd.DatetimeIndex(idx["date"].dropna().unique())
    panel_on_witness_dates = panel.loc[panel_dates.isin(witness_dates)].copy()
    overlap_keys = comparison[["ticker", "date"]].drop_duplicates()
    denominator = panel_on_witness_dates[["ticker", "date"]].drop_duplicates()
    identity_coverage_rate = (len(overlap_keys) / len(denominator)) if len(denominator) else 0.0

    comparable = comparison[comparison["value_comparable"].astype(bool)].copy() if not comparison.empty else comparison.copy()
    exact = comparable["panel_idx_value_exact"].astype(bool) if not comparable.empty else pd.Series(dtype=bool)
    mismatch = comparable.loc[~exact].copy() if not comparable.empty else comparable.copy()

    comparison["year"] = pd.to_datetime(comparison["date"]).dt.year if not comparison.empty else pd.Series(dtype=int)
    overall_summary = ratio_summary(comparison)
    by_provenance = ratio_summary(comparison, by="price_provenance")
    by_year = ratio_summary(comparison, by="year")
    seams = detect_ratio_seams(comparison, jump_factor=1.20)

    counterfactual, direct_evidence = apply_official_value_counterfactual(panel, idx)
    before_primary = build_primary_liquid_state(panel, sessions)
    after_primary = build_primary_liquid_state(counterfactual, sessions)
    before_features = build_value_feature_state(panel, before_primary)
    after_features = build_value_feature_state(counterfactual, after_primary)
    feature_diff, feature_summary = compare_value_feature_states(before_features, after_features)

    primary_compare = before_primary[[
        "ticker", "date", "median_regular_value_60", "universe_primary_liquid"
    ]].merge(
        after_primary[["ticker", "date", "median_regular_value_60", "universe_primary_liquid"]],
        on=["ticker", "date"], how="inner", suffixes=("_before", "_after"), validate="one_to_one"
    )
    primary_changed = primary_compare[
        primary_compare["universe_primary_liquid_before"].astype(bool)
        .ne(primary_compare["universe_primary_liquid_after"].astype(bool))
    ].copy()

    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "comparison": output / "panel_vs_idx_regular_market_value_rows.csv",
        "mismatch": output / "panel_vs_idx_regular_market_value_mismatches.csv",
        "summary_by_provenance": output / "regular_market_value_summary_by_provenance.csv",
        "summary_by_year": output / "regular_market_value_summary_by_year.csv",
        "ratio_seams": output / "regular_market_value_ratio_seams_20pct.csv",
        "counterfactual_direct": output / "official_value_counterfactual_direct_rows.csv",
        "feature_diff": output / "regular_market_value_representation_diff.csv",
        "primary_changed": output / "primary_liquid_eligibility_changes.csv",
    }
    comparison.to_csv(paths["comparison"], index=False, lineterminator="\n")
    mismatch.to_csv(paths["mismatch"], index=False, lineterminator="\n")
    by_provenance.to_csv(paths["summary_by_provenance"], index=False, lineterminator="\n")
    by_year.to_csv(paths["summary_by_year"], index=False, lineterminator="\n")
    seams.to_csv(paths["ratio_seams"], index=False, lineterminator="\n")
    direct_evidence.to_csv(paths["counterfactual_direct"], index=False, lineterminator="\n")
    feature_diff.loc[feature_diff["any_value_representation_changed"].astype(bool)].to_csv(
        paths["feature_diff"], index=False, lineterminator="\n"
    )
    primary_changed.to_csv(paths["primary_changed"], index=False, lineterminator="\n")

    overall_record = overall_summary.iloc[0].to_dict() if not overall_summary.empty else {}
    exact_rate = float(overall_record.get("exact_rate", 0.0) or 0.0)
    within_1pct_rate = float(overall_record.get("within_1pct_rate", 0.0) or 0.0)
    close_volume_like_rate = float(overall_record.get("close_volume_like_1pct_rate", 0.0) or 0.0)

    if len(comparable) == 0:
        verdict = "REGULAR_MARKET_VALUE_AUDIT_NO_COMPARABLE_OFFICIAL_WITNESS"
    elif exact_rate >= 0.999 and feature_summary["primary_liquid_changed_rows"] == 0:
        verdict = "REGULAR_MARKET_VALUE_BASIS_NO_MATERIAL_MISMATCH_ON_OFFICIAL_OVERLAP"
    elif feature_summary["primary_liquid_changed_rows"] > 0:
        verdict = "REGULAR_MARKET_VALUE_BASIS_MISMATCH_WITH_PRIMARY_LIQUIDITY_IMPACT_FOUND"
    elif feature_summary["any_value_representation_changed_rows"] > 0:
        verdict = "REGULAR_MARKET_VALUE_BASIS_MISMATCH_WITH_REPRESENTATION_IMPACT_FOUND"
    else:
        verdict = "REGULAR_MARKET_VALUE_BASIS_MISMATCH_FOUND_NO_MEASURED_DOWNSTREAM_CHANGE"

    summary = {
        "schema_version": "regular_market_value_basis_audit_v1",
        "status": verdict,
        "official_semantics": {
            "source": "IDX_PUBLIC_STOCK_SUMMARY",
            "field": "Value",
            "interpretation": "official Regular-Market traded value; NonRegular metrics are separate",
        },
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
            "panel_rows_on_witness_dates": int(len(denominator)),
            "exact_ticker_date_overlap_rows": int(len(overlap_keys)),
            "identity_overlap_rate_on_witness_dates": float(identity_coverage_rate),
            "comparable_positive_value_rows": int(len(comparable)),
        },
        "value_parity": {
            "exact_rows": int(exact.sum()) if len(exact) else 0,
            "mismatch_rows": int((~exact).sum()) if len(exact) else 0,
            "exact_rate": exact_rate,
            "within_1pct_rate": within_1pct_rate,
            "panel_value_close_x_volume_like_1pct_rate": close_volume_like_rate,
            "panel_idx_value_ratio": _finite_summary(comparable.get("panel_idx_value_ratio", pd.Series(dtype=float))),
            "panel_value_over_close_volume": _finite_summary(comparable.get("panel_value_over_close_volume", pd.Series(dtype=float))),
            "idx_value_over_close_volume": _finite_summary(comparable.get("idx_value_over_close_volume", pd.Series(dtype=float))),
            "ratio_seams_ge_20pct": int(len(seams)),
            "ratio_seams_with_price_provenance_change": int(seams["provenance_changed"].sum()) if not seams.empty else 0,
        },
        "bounded_official_counterfactual": {
            "direct_value_rows_changed": int(len(direct_evidence)),
            "direct_value_tickers_changed": int(direct_evidence["ticker"].nunique()) if not direct_evidence.empty else 0,
            **feature_summary,
            "primary_liquid_false_to_true": int((
                ~primary_changed["universe_primary_liquid_before"].astype(bool)
                & primary_changed["universe_primary_liquid_after"].astype(bool)
            ).sum()) if not primary_changed.empty else 0,
            "primary_liquid_true_to_false": int((
                primary_changed["universe_primary_liquid_before"].astype(bool)
                & ~primary_changed["universe_primary_liquid_after"].astype(bool)
            ).sum()) if not primary_changed.empty else 0,
            "interpretation": "lower-bound/bounded overlap counterfactual only; not a remediation authorization",
        },
        "guardrails": {
            "provider_calls": False,
            "model_fit": False,
            "model_scoring": False,
            "target_values_accessed": False,
            "protected_forward_accessed": False,
            "parent_panel_overwritten": False,
            "regular_market_value_repaired": False,
        },
        "next": (
            "INDEPENDENT_REVIEW; if mismatch is material, preregister a separate value remediation. "
            "Do not fold value changes into HLC remediation implicitly."
        ),
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"] = summary_path

    manifest = {
        "schema_version": "regular_market_value_basis_audit_manifest_v1",
        "status": verdict,
        "inputs": {
            "panel": {"path": str(panel_path), "sha256": PANEL_SHA256},
            "calendar": {"path": str(calendar_path), "sha256": CALENDAR_SHA256},
            "stock_summary_root": str(stock_root),
        },
        "guardrails": summary["guardrails"],
        "output_hashes": {name: sha256_file(path) for name, path in paths.items()},
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        **summary,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
