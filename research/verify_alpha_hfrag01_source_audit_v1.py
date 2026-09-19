"""Independent target-free verifier for the H-FRAG-01 source audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import build_decision_universe, sha256_file


EXPECTED_SESSION_HASH = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_ANCHOR_HASH = "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e"
EXPECTED_STAGE = "HFRAG01_OFFICIAL_STOCK_SUMMARY_SOURCE_AUDIT"
REQUIRED_COLUMNS = [
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
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    parquet_files = sorted(args.cache_dir.glob("*.parquet"))
    meta_files = sorted(args.cache_dir.glob("*.meta.json"))
    frames: list[pd.DataFrame] = []
    sidecar_rows = 0
    sidecar_records = 0
    sidecar_dates_match = True
    sidecar_rows_match = True
    sidecar_source_refs: set[str] = set()
    for path in parquet_files:
        frame = pd.read_parquet(path)
        frames.append(frame)
        meta_path = path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        sidecar_rows += int(meta["rows"])
        sidecar_records += int(meta["records_total"])
        sidecar_dates_match = sidecar_dates_match and str(meta["requested_date"]) == path.stem
        sidecar_rows_match = sidecar_rows_match and int(meta["rows"]) == len(frame)
        sidecar_source_refs.add(str(meta["source_ref"]))

    cache = pd.concat(frames, ignore_index=True)
    cache["date"] = pd.to_datetime(cache["as_of_date"], errors="raise").dt.normalize()
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    panel = pd.read_parquet(
        args.panel, columns=["ticker", "date", "regular_market_value", "volume"]
    )
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    cache["ticker"] = cache["ticker"].astype("string")
    panel["ticker"] = panel["ticker"].astype("string")

    universe, _ = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors
    )
    eligible = universe.merge(
        cache[["ticker", "date", "volume", "frequency", "nonregular_volume", "nonregular_frequency"]],
        on=["ticker", "date"], how="left", validate="one_to_one",
    )
    eligible_mask = eligible["eligible_decision_universe"]
    volume = pd.to_numeric(eligible["volume"], errors="coerce")
    frequency = pd.to_numeric(eligible["frequency"], errors="coerce")
    nonregular_volume = pd.to_numeric(eligible["nonregular_volume"], errors="coerce")
    nonregular_frequency = pd.to_numeric(eligible["nonregular_frequency"], errors="coerce")
    volume_ratio = nonregular_volume / volume.where(volume.gt(0))
    frequency_ratio = nonregular_frequency / frequency.where(frequency.gt(0))

    overlap = cache.merge(
        panel, on=["ticker", "date"], how="inner", validate="one_to_one", suffixes=("_cache", "_panel")
    )
    volume_equal = pd.to_numeric(overlap["volume_cache"], errors="coerce").eq(
        pd.to_numeric(overlap["volume_panel"], errors="coerce")
    )
    value_equal = pd.to_numeric(overlap["regular_value"], errors="coerce").eq(
        pd.to_numeric(overlap["regular_market_value"], errors="coerce")
    )
    numeric = cache[["volume", "frequency", "regular_value", "nonregular_volume", "nonregular_frequency"]].apply(
        pd.to_numeric, errors="coerce"
    )

    checks = {
        "artifact_stage": artifact.get("stage") == EXPECTED_STAGE,
        "artifact_status": artifact.get("status") == "SOURCE_BLOCKED",
        "artifact_partial_admissibility": artifact.get("interpretation", {}).get("admissibility") == "PARTIAL",
        "no_outcome_access": artifact.get("outcome_accessed") is False,
        "no_provider_access": artifact.get("provider_accessed") is False,
        "no_candidate_id_created": artifact.get("candidate_id_created") is False,
        "code_hash": artifact.get("code_sha256") == sha256_file(args.code),
        "sessions_hash": sha256_file(args.sessions) == EXPECTED_SESSION_HASH,
        "anchors_hash": sha256_file(args.anchors) == EXPECTED_ANCHOR_HASH,
        "parquet_file_count": len(parquet_files) == 1260,
        "meta_file_count": len(meta_files) == 1260,
        "required_columns": set(REQUIRED_COLUMNS).issubset(set(cache.columns)),
        "cache_keys_unique": int(cache.duplicated(["ticker", "date"]).sum()) == 0,
        "official_dates": set(cache["date"].unique()).issubset(set(sessions["date"].unique())),
        "source_identity": set(cache["source"].astype(str)) == {"IDX_PUBLIC_STOCK_SUMMARY"},
        "sidecar_rows_match": sidecar_rows_match and sidecar_rows == len(cache),
        "sidecar_dates_match": sidecar_dates_match,
        "numeric_nonnegative": bool(numeric.ge(0).all().all()),
        "volume_exact_overlap": bool(volume_equal.all()),
        "value_exact_overlap": bool(value_equal.all()),
        "boundedness_violation_count": int(
            (volume_ratio.loc[eligible_mask].lt(0) | volume_ratio.loc[eligible_mask].gt(1)).sum()
        )
        == artifact["ratios"]["nonregular_volume_share"]["outside_unit_interval_rows"],
        "frequency_boundedness_violation_count": int(
            (frequency_ratio.loc[eligible_mask].lt(0) | frequency_ratio.loc[eligible_mask].gt(1)).sum()
        )
        == artifact["ratios"]["nonregular_frequency_share"]["outside_unit_interval_rows"],
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verification_type": "independent_source_inventory_and_reconciliation_target_free",
        "artifact_sha256": sha256_file(args.artifact),
        "verifier_code_sha256": sha256_file(Path(__file__)),
        "cache_inventory_sha256": inventory_hash(args.cache_dir, sorted(parquet_files + meta_files)),
        "checks": checks,
        "recomputed": {
            "cache_rows": int(len(cache)),
            "cache_tickers": int(cache["ticker"].nunique()),
            "cache_dates": int(cache["date"].nunique()),
            "sidecar_rows": sidecar_rows,
            "sidecar_records_total": sidecar_records,
            "sidecar_source_ref_count": len(sidecar_source_refs),
            "panel_overlap_rows": int(len(overlap)),
            "panel_only_rows": int(len(panel.merge(cache[["ticker", "date"]], on=["ticker", "date"], how="left", indicator=True).query("_merge == 'left_only'"))),
            "cache_only_rows": int(len(cache.merge(panel[["ticker", "date"]], on=["ticker", "date"], how="left", indicator=True).query("_merge == 'left_only'"))),
            "volume_exact_rows": int(volume_equal.sum()),
            "value_exact_rows": int(value_equal.sum()),
            "nonregular_volume_boundedness_violations": int((volume_ratio.loc[eligible_mask].lt(0) | volume_ratio.loc[eligible_mask].gt(1)).sum()),
            "nonregular_frequency_boundedness_violations": int((frequency_ratio.loc[eligible_mask].lt(0) | frequency_ratio.loc[eligible_mask].gt(1)).sum()),
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
