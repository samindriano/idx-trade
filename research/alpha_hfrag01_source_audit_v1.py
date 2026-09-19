"""Target-free capability audit for official stock-summary composition fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import build_decision_universe, rolling, sha256_file


C1 = "C1_residual_reversal_5_v1"
C2 = "C2_participation_confirmation_5_v1"
C4 = "C4_path_efficiency_reversal_20_v1"
HLIQ = "HLIQ01_variability_log_turnover_20_v1"
TOP_K = 30
EXPECTED_SESSION_HASH = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_ANCHOR_HASH = "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e"
CACHE_COLUMNS = [
    "ticker",
    "as_of_date",
    "remarks",
    "volume",
    "frequency",
    "regular_value",
    "nonregular_volume",
    "nonregular_frequency",
    "security_status_raw",
    "security_status_field",
    "source",
    "source_ref",
]


def finite_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def cache_inventory_hash(cache_dir: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(cache_dir).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def daily_spearman(frame: pd.DataFrame, left: str, right: str) -> dict[str, object]:
    values: list[float] = []
    valid = (
        frame["eligible_decision_universe"]
        & np.isfinite(frame[left])
        & np.isfinite(frame[right])
    )
    for _, group in frame.loc[valid].groupby("date", sort=True):
        if len(group) < TOP_K:
            continue
        correlation = group[left].rank(method="average").corr(
            group[right].rank(method="average"), method="spearman"
        )
        if pd.notna(correlation):
            values.append(float(correlation))
    return {
        "date_count": len(values),
        "mean_daily_spearman": finite_float(np.mean(values)) if values else None,
        "median_daily_spearman": finite_float(np.median(values)) if values else None,
    }


def top30(frame: pd.DataFrame, column: str) -> dict[pd.Timestamp, set[str]]:
    valid = frame["eligible_decision_universe"] & np.isfinite(frame[column])
    result: dict[pd.Timestamp, set[str]] = {}
    for date, group in frame.loc[valid].groupby("date", sort=True):
        chosen = group.sort_values(
            [column, "ticker"], ascending=[False, True], kind="mergesort"
        ).head(TOP_K)
        if len(chosen) == TOP_K:
            result[pd.Timestamp(date)] = set(chosen["ticker"].astype(str))
    return result


def top30_overlap(frame: pd.DataFrame, left: str, right: str) -> dict[str, object]:
    left_sets = top30(frame, left)
    right_sets = top30(frame, right)
    dates = sorted(set(left_sets) & set(right_sets))
    overlaps = [len(left_sets[date] & right_sets[date]) / TOP_K for date in dates]
    return {
        "common_dates": len(dates),
        "mean_overlap": finite_float(np.mean(overlaps)) if overlaps else None,
        "min_overlap": finite_float(np.min(overlaps)) if overlaps else None,
    }


def bottom_value_q1_share(frame: pd.DataFrame, score: str) -> dict[str, object]:
    valid = (
        frame["eligible_decision_universe"]
        & np.isfinite(frame[score])
        & np.isfinite(frame["regular_market_value"])
        & frame["regular_market_value"].gt(0)
    )
    work = frame.loc[valid, ["date", "ticker", score, "regular_market_value"]].copy()
    work["value_percentile"] = work.groupby("date")["regular_market_value"].rank(
        pct=True, method="average"
    )
    selected: list[pd.DataFrame] = []
    for _, group in work.groupby("date", sort=True):
        chosen = group.sort_values(
            [score, "ticker"], ascending=[False, True], kind="mergesort"
        ).head(TOP_K)
        if len(chosen) == TOP_K:
            selected.append(chosen)
    if not selected:
        return {"selected_slots": 0, "bottom_value_q1_share": None}
    chosen = pd.concat(selected, ignore_index=True)
    return {
        "selected_slots": int(len(chosen)),
        "bottom_value_q1_share": finite_float(chosen["value_percentile"].le(0.25).mean()),
    }


def load_cache(cache_dir: Path) -> tuple[pd.DataFrame, dict[str, object], str]:
    parquet_files = sorted(cache_dir.glob("*.parquet"))
    meta_files = sorted(cache_dir.glob("*.meta.json"))
    meta_by_stem = {path.name.removesuffix(".meta.json"): path for path in meta_files}
    records: list[pd.DataFrame] = []
    sidecar_rows_match = True
    sidecar_date_match = True
    sidecar_source_refs: set[str] = set()
    sidecar_records_total = 0
    for path in parquet_files:
        date_token = path.stem
        sidecar = meta_by_stem.get(date_token)
        frame = pd.read_parquet(path, columns=CACHE_COLUMNS)
        frame["ticker"] = frame["ticker"].astype("string")
        frame["as_of_date"] = pd.to_datetime(frame["as_of_date"], errors="raise").dt.normalize()
        records.append(frame)
        if sidecar is None:
            sidecar_rows_match = False
            continue
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        sidecar_rows_match = sidecar_rows_match and int(metadata.get("rows", -1)) == len(frame)
        sidecar_date_match = sidecar_date_match and metadata.get("requested_date") == date_token
        sidecar_source_refs.add(str(metadata.get("source_ref")))
        sidecar_records_total += int(metadata.get("records_total", -1))
    cache = pd.concat(records, ignore_index=True)
    inventory_files = sorted([*parquet_files, *meta_files], key=lambda path: path.name)
    inventory_hash = cache_inventory_hash(cache_dir, inventory_files)
    stats = {
        "parquet_files": len(parquet_files),
        "meta_files": len(meta_files),
        "rows": int(len(cache)),
        "tickers": int(cache["ticker"].nunique()),
        "dates": int(cache["as_of_date"].nunique()),
        "date_min": str(cache["as_of_date"].min().date()),
        "date_max": str(cache["as_of_date"].max().date()),
        "duplicate_ticker_date_rows": int(cache.duplicated(["ticker", "as_of_date"]).sum()),
        "sidecar_rows_match": sidecar_rows_match,
        "sidecar_date_match": sidecar_date_match,
        "sidecar_source_ref_count": len(sidecar_source_refs),
        "sidecar_records_total": sidecar_records_total,
        "inventory_sha256": inventory_hash,
    }
    return cache, stats, inventory_hash


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    cache, cache_stats, inventory_hash = load_cache(args.cache_dir)
    panel = pd.read_parquet(
        args.panel, columns=["ticker", "date", "close", "volume", "regular_market_value"]
    )
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    features = pd.read_parquet(args.features, columns=["ticker", "date", C1, C2, C4])
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()

    universe, universe_stats = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors
    )
    full = universe.merge(panel, on=["ticker", "date"], how="left", validate="one_to_one")
    full = full.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    for column in ["close", "volume", "regular_market_value"]:
        full[column] = pd.to_numeric(full[column], errors="coerce")
    close_valid = full["close"].gt(0) & np.isfinite(full["close"])
    volume_valid = full["volume"].gt(0) & np.isfinite(full["volume"])
    full["log_turnover"] = np.log((full["close"] * full["volume"]).where(close_valid & volume_valid))
    full[HLIQ] = rolling(full, "log_turnover", 20, "std")
    full.loc[~full["eligible_decision_universe"], HLIQ] = np.nan

    cache = cache.rename(columns={"as_of_date": "date"})
    surface = full.merge(
        cache[["ticker", "date", "volume", "regular_value", "frequency", "nonregular_volume", "nonregular_frequency", "source", "source_ref"]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
        suffixes=("_panel", "_cache"),
    )
    surface = surface.merge(
        features, on=["ticker", "date"], how="left", validate="one_to_one"
    )
    for column in ["volume_cache", "regular_value", "frequency", "nonregular_volume", "nonregular_frequency"]:
        surface[column] = pd.to_numeric(surface[column], errors="coerce")
    surface["nonregular_volume_share"] = (
        surface["nonregular_volume"] / surface["volume_cache"].where(surface["volume_cache"].gt(0))
    )
    surface["nonregular_frequency_share"] = (
        surface["nonregular_frequency"] / surface["frequency"].where(surface["frequency"].gt(0))
    )

    overlap = cache.merge(
        panel[["ticker", "date", "volume", "regular_market_value"]],
        on=["ticker", "date"], how="inner", validate="one_to_one", suffixes=("_cache", "_panel")
    )
    volume_difference = (
        pd.to_numeric(overlap["volume_cache"], errors="coerce")
        - pd.to_numeric(overlap["volume_panel"], errors="coerce")
    ).abs()
    value_difference = (
        pd.to_numeric(overlap["regular_value"], errors="coerce")
        - pd.to_numeric(overlap["regular_market_value"], errors="coerce")
    ).abs()

    eligible = surface["eligible_decision_universe"]
    source_validity = {
        "cache_keys_unique": cache_stats["duplicate_ticker_date_rows"] == 0,
        "cache_dates_are_official": set(cache["date"].unique()).issubset(set(sessions["date"].unique())),
        "source_identity_exact": set(cache["source"].dropna().astype(str)) == {"IDX_PUBLIC_STOCK_SUMMARY"},
        "sidecar_rows_match": cache_stats["sidecar_rows_match"],
        "sidecar_dates_match": cache_stats["sidecar_date_match"],
        "required_fields_non_null": bool(
            cache[["ticker", "date", *CACHE_COLUMNS[2:]]].notna().all().all()
        ),
        "numeric_fields_nonnegative": bool(
            cache[["volume", "frequency", "regular_value", "nonregular_volume", "nonregular_frequency"]]
            .apply(pd.to_numeric, errors="coerce")
            .ge(0)
            .all()
            .all()
        ),
        "volume_exact_on_panel_overlap": bool(volume_difference.fillna(0).eq(0).all()),
        "regular_value_exact_on_panel_overlap": bool(value_difference.fillna(0).eq(0).all()),
    }
    ratios = {}
    for column in ["nonregular_volume_share", "nonregular_frequency_share"]:
        values = surface.loc[eligible, column].dropna()
        ratios[column] = {
            "eligible_finite_rows": int(values.size),
            "eligible_coverage": finite_float(values.size / int(eligible.sum())) if eligible.sum() else None,
            "eligible_positive_rows": int(values.gt(0).sum()),
            "q50": finite_float(values.quantile(0.50)) if len(values) else None,
            "q90": finite_float(values.quantile(0.90)) if len(values) else None,
            "q99": finite_float(values.quantile(0.99)) if len(values) else None,
            "outside_unit_interval_rows": int((values.lt(0) | values.gt(1)).sum()),
            "ticker_count": int(surface.loc[eligible & surface[column].notna(), "ticker"].nunique()),
            "date_count": int(surface.loc[eligible & surface[column].notna(), "date"].nunique()),
        }

    frozen_dates = set(sessions["date"].sort_values().iloc[-600:])
    structural = surface[surface["date"].isin(frozen_dates)].copy()
    references = {"C1": C1, "C2": C2, "C4": C4, "HLIQ": HLIQ}
    dependence = {
        ratio: {
            name: daily_spearman(structural, ratio, column)
            for name, column in references.items()
        }
        for ratio in ["nonregular_volume_share", "nonregular_frequency_share"]
    }
    top30 = {
        ratio: {
            name: top30_overlap(structural, ratio, column)
            for name, column in references.items()
        }
        for ratio in ["nonregular_volume_share", "nonregular_frequency_share"]
    }
    concentration = {
        ratio: bottom_value_q1_share(structural, ratio)
        for ratio in ["nonregular_volume_share", "nonregular_frequency_share"]
    }

    checks = {
        **source_validity,
        "official_sessions_hash": sha256_file(args.sessions) == EXPECTED_SESSION_HASH,
        "tradability_anchors_hash": sha256_file(args.anchors) == EXPECTED_ANCHOR_HASH,
        "features_keys_match_panel": set(zip(features["ticker"], features["date"])) == set(
            zip(panel["ticker"], panel["date"])
        ),
        "panel_only_rows_zero": len(panel) - len(overlap) == 0,
        "has_positive_nonregular_volume": int(pd.to_numeric(cache["nonregular_volume"], errors="coerce").gt(0).sum()) > 0,
        "has_positive_nonregular_frequency": int(pd.to_numeric(cache["nonregular_frequency"], errors="coerce").gt(0).sum()) > 0,
        "no_ratio_outside_unit_interval": all(
            value["outside_unit_interval_rows"] == 0 for value in ratios.values()
        ),
        "no_outcome_access": True,
        "no_provider_access": True,
        "no_candidate_id_created": True,
    }
    status = "SOURCE_PARTIAL_STRUCTURAL_SIGNAL" if all(checks.values()) else "SOURCE_BLOCKED"
    result = {
        "status": status,
        "stage": "HFRAG01_OFFICIAL_STOCK_SUMMARY_SOURCE_AUDIT",
        "hypothesis_id": "H-FRAG-01",
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "outcome_accessed": False,
        "provider_accessed": False,
        "candidate_id_created": False,
        "cache_source": {
            "path": str(args.cache_dir),
            "inventory_sha256": inventory_hash,
            **cache_stats,
        },
        "source_hashes": {
            "panel": sha256_file(args.panel),
            "features": sha256_file(args.features),
            "official_sessions": sha256_file(args.sessions),
            "tradability_anchors": sha256_file(args.anchors),
        },
        "universe": universe_stats,
        "panel_reconciliation": {
            "cache_rows": int(len(cache)),
            "panel_rows": int(len(panel)),
            "intersection_rows": int(len(overlap)),
            "cache_only_rows": int(len(cache) - len(overlap)),
            "panel_only_rows": int(len(panel) - len(overlap)),
            "cache_only_tickers": int(len(set(cache["ticker"]) - set(panel["ticker"]))),
            "volume_exact_rows": int(volume_difference.fillna(0).eq(0).sum()),
            "regular_value_exact_rows": int(value_difference.fillna(0).eq(0).sum()),
        },
        "ratios": ratios,
        "structural_window": {
            "date_count": len(frozen_dates),
            "min": str(min(frozen_dates).date()),
            "max": str(max(frozen_dates).date()),
            "dependence": dependence,
            "top30_overlap": top30,
            "bottom_value_q1_share": concentration,
        },
        "checks": checks,
        "interpretation": {
            "admissibility": "PARTIAL",
            "mechanism": "regular-versus-non-regular trading composition / possible trade-fragmentation state",
            "source_semantics_status": "UNKNOWN_PENDING_FIELD_DEFINITION_AND_AVAILABLE_AT_CONTRACT",
            "predictive_claim": False,
            "status_change_authorized": False,
            "packet_expansion_authorized": False,
        },
        "code_sha256": sha256_file(Path(__file__)),
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if status == "SOURCE_BLOCKED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
