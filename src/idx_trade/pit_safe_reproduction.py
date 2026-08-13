"""PIT-safe historical input reconstruction without model fitting or providers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .ohlcv_o2_geometry_research import O2_GEOMETRY_FEATURES
from .ranking_v3_forward_runtime import V3_B_FEATURE_COLUMNS, _join_structure_onto_exact_rows
from .research_baselines import prepare_primary_model_table
from .research_features import (
    build_baseline_features,
    filter_panel_to_listing_domain,
    strict_boolean_series,
)
from .research_v2_features import V2_FULL_FEATURE_COLUMNS, build_v2_feature_table
from .research_v3_structure_lite import STRUCTURE_LITE_FEATURE_COLUMNS, build_structure_lite_features


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_key_hash(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date", "signal_session_index"]].copy()
    keys["ticker"] = keys["ticker"].astype(str)
    keys["date"] = pd.to_datetime(keys["date"], errors="raise").dt.strftime("%Y-%m-%d")
    keys["signal_session_index"] = pd.to_numeric(keys["signal_session_index"], errors="raise").astype(int)
    lines = keys.sort_values(["ticker", "date", "signal_session_index"], kind="mergesort").astype(str).agg("|".join, axis=1)
    return hashlib.sha256(("\n".join(lines.tolist()) + "\n").encode("utf-8")).hexdigest()


def _listing_map(master: pd.DataFrame) -> dict[str, object]:
    return {
        str(row.ticker): row.listed_from
        for row in master[["ticker", "listed_from"]].itertuples(index=False)
    }


def _read_calendar(path: Path) -> pd.DatetimeIndex:
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise ValueError("official calendar must contain date")
    dates = pd.to_datetime(frame["date"], errors="raise", utc=True).dt.tz_localize(None).dt.normalize()
    if dates.duplicated().any():
        raise ValueError("official calendar contains duplicate dates")
    return pd.DatetimeIndex(dates)


def _normalize_table_dates(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["ticker"] = result["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    result["date"] = pd.to_datetime(result["date"], errors="raise", utc=True).dt.tz_localize(None).dt.normalize()
    return result


def _identity_delta(old: pd.DataFrame, new: pd.DataFrame) -> dict[str, object]:
    old_keys = set(map(tuple, old[["ticker", "date"]].itertuples(index=False, name=None)))
    new_keys = set(map(tuple, new[["ticker", "date"]].itertuples(index=False, name=None)))
    removed = sorted(old_keys - new_keys)
    added = sorted(new_keys - old_keys)
    return {
        "old_rows": int(len(old)),
        "new_rows": int(len(new)),
        "removed_rows": int(len(removed)),
        "added_rows": int(len(added)),
        "unchanged_identity_rows": int(len(old_keys & new_keys)),
        "removed_tickers": sorted({key[0] for key in removed}),
        "added_tickers": sorted({key[0] for key in added}),
        "removed_sessions": sorted({pd.Timestamp(key[1]).date().isoformat() for key in removed}),
        "added_sessions": sorted({pd.Timestamp(key[1]).date().isoformat() for key in added}),
    }


def _feature_deltas(old: pd.DataFrame, new: pd.DataFrame, columns: Iterable[str]) -> tuple[pd.DataFrame, dict[str, int]]:
    features = list(columns)
    old_keyed = old.set_index(["ticker", "date"])
    new_keyed = new.set_index(["ticker", "date"])
    shared = old_keyed.index.intersection(new_keyed.index)
    rows: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    for feature in features:
        left = old_keyed.loc[shared, feature]
        right = new_keyed.loc[shared, feature]
        equal = left.eq(right) | (left.isna() & right.isna())
        changed = ~equal
        counts[feature] = int(changed.sum())
        for (ticker, date), old_value, new_value in zip(
            shared[changed], left.loc[changed], right.loc[changed], strict=False
        ):
            rows.append(
                {
                    "ticker": ticker,
                    "date": pd.Timestamp(date).date().isoformat(),
                    "feature": feature,
                    "old_value": old_value,
                    "corrected_value": new_value,
                }
            )
    return pd.DataFrame(rows), counts


def reconstruct_inputs(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    h10_labels_path: Path,
    old_v2_table_path: Path,
    coverage_path: Path,
    protocol_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, object]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"PIT-safe output directory must be new or empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    panel = pd.read_parquet(panel_path)
    calendar = _read_calendar(calendar_path)
    master = pd.read_csv(security_master_path)
    labels = pd.read_parquet(h10_labels_path)
    old_v2 = _normalize_table_dates(pd.read_parquet(old_v2_table_path))
    corrected_panel, panel_diagnostics = filter_panel_to_listing_domain(panel, master, calendar)

    panel_output = output_dir / "pit_safe_signal_panel.parquet"
    corrected_panel.to_parquet(panel_output, index=False)

    baseline = build_baseline_features(
        corrected_panel,
        calendar,
        listed_from=_listing_map(master),
        security_master=master,
    )
    v2_features = build_v2_feature_table(baseline)
    v2_table = prepare_primary_model_table(v2_features, labels)
    date_to_index = {pd.Timestamp(value): index + 1 for index, value in enumerate(calendar)}
    v2_table["signal_session_index"] = v2_table["date"].map(date_to_index)
    if v2_table["signal_session_index"].isna().any():
        raise RuntimeError("corrected V2 table contains dates outside official calendar")
    v2_table["signal_session_index"] = v2_table["signal_session_index"].astype(int)
    v2_table = v2_table[v2_table["signal_session_index"].le(1250)].copy()
    v2_keep = [
        "ticker", "date", "signal_session_index", "binary_target", "label_status",
        "universe_primary_liquid", "close_return_5", "close_return_20", "atr14_over_close",
        "close_position_20", "distance_high_20_atr", "distance_low_20_atr",
        "distance_high_60_atr", "distance_low_60_atr", "relative_volume_20",
        "log_regular_value_relative_20", "observed_session_count", "security_age_sessions_exact",
        *V2_FULL_FEATURE_COLUMNS,
    ]
    missing = set(v2_keep) - set(v2_table.columns)
    if missing:
        raise RuntimeError(f"corrected V2 table missing columns: {sorted(missing)}")
    v2_table = v2_table.loc[:, v2_keep].sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)
    v2_output = output_dir / "pit_safe_ranking_v2_prepared_model_table.parquet"
    v2_table.to_parquet(v2_output, index=False)

    structure_panel = corrected_panel[["ticker", "date", "high", "low", "close", "volume"]].copy()
    structure = build_structure_lite_features(structure_panel, calendar, max_signal_session_index=1250)
    v3_table = _join_structure_onto_exact_rows(v2_table, structure, require_frozen_training_facts=False)
    v3_output = output_dir / "pit_safe_ranking_v3_b_training_table.parquet"
    v3_table.to_parquet(v3_output, index=False)

    coverage = _normalize_table_dates(pd.read_csv(coverage_path))
    coverage["open_feature_ready"] = strict_boolean_series(coverage["open_feature_ready"], field_name="open_feature_ready")
    ready = coverage[coverage["open_feature_ready"]].copy()
    geometry_columns = {"ticker", "date", "signal_session_index", "open_position", "open_to_high", "open_to_low"}
    if not geometry_columns.issubset(ready.columns):
        raise RuntimeError(f"coverage artifact missing O2 geometry columns: {sorted(geometry_columns - set(ready.columns))}")
    o2_table = v3_table.merge(
        ready[list(geometry_columns)],
        on=["ticker", "date"],
        how="inner",
        validate="one_to_one",
        suffixes=("", "_coverage"),
    )
    if not (o2_table["signal_session_index"].astype(int) == o2_table["signal_session_index_coverage"].astype(int)).all():
        raise RuntimeError("corrected O2 coverage signal-session identities disagree")
    o2_table = o2_table.drop(columns=["signal_session_index_coverage"])
    o2_output = output_dir / "pit_safe_o2_input_table.parquet"
    o2_table.to_parquet(o2_output, index=False)

    identity_delta = _identity_delta(old_v2, v2_table)
    delta_rows, feature_counts = _feature_deltas(old_v2, v2_table, [*V2_FULL_FEATURE_COLUMNS, "observed_session_count", "security_age_sessions_exact"])
    delta_output = output_dir / "v2_feature_deltas_long.csv"
    delta_rows.to_csv(delta_output, index=False)
    changed_rows = int(delta_rows[["ticker", "date"]].drop_duplicates().shape[0]) if not delta_rows.empty else 0
    affected_sessions = sorted(delta_rows["date"].drop_duplicates().tolist()) if not delta_rows.empty else []
    affected_tickers = sorted(delta_rows["ticker"].drop_duplicates().tolist()) if not delta_rows.empty else []
    koci_delta = delta_rows[delta_rows["ticker"].eq("KOCI")] if not delta_rows.empty else delta_rows
    context_delta = delta_rows[delta_rows["feature"].eq("market_primary_liquid_count")] if not delta_rows.empty else delta_rows

    artifacts = {
        path.name: sha256_file(path)
        for path in (panel_output, v2_output, v3_output, o2_output, delta_output)
    }
    report = {
        "status": "REPRODUCTION_BLOCKED",
        "reproduction_boundary": "HISTORICAL_LADDER_REPLAY_REQUIRED",
        "execution_status": "REPRODUCTION_BLOCKED",
        "code_commit": code_commit,
        "protocol_path": str(protocol_path),
        "protocol_sha256": sha256_file(protocol_path),
        "parent_artifacts": {
            "panel": {"path": str(panel_path), "sha256": sha256_file(panel_path)},
            "calendar": {"path": str(calendar_path), "sha256": sha256_file(calendar_path)},
            "security_master": {"path": str(security_master_path), "sha256": sha256_file(security_master_path)},
            "h10_labels": {"path": str(h10_labels_path), "sha256": sha256_file(h10_labels_path)},
            "old_v2_table": {"path": str(old_v2_table_path), "sha256": sha256_file(old_v2_table_path)},
            "coverage": {"path": str(coverage_path), "sha256": sha256_file(coverage_path)},
        },
        "panel_listing_domain": panel_diagnostics,
        "koci_2023_10_06_removed": bool(
            not corrected_panel[(corrected_panel["ticker"].eq("KOCI")) & (corrected_panel["date"].eq(pd.Timestamp("2023-10-06")))].any(axis=None)
        ),
        "v2_identity_delta": identity_delta,
        "v2_feature_delta": {
            "changed_identity_rows_with_feature_change": changed_rows,
            "affected_sessions": len(affected_sessions),
            "affected_tickers": len(affected_tickers),
            "affected_session_dates": affected_sessions,
            "affected_ticker_names": affected_tickers,
            "per_feature_changed_row_counts": feature_counts,
            "koci_changed_feature_rows": int(len(koci_delta)),
            "market_primary_liquid_count_changed_rows": int(len(context_delta)),
        },
        "corrected_inputs": {
            "v2_rows": int(len(v2_table)),
            "v2_tickers": int(v2_table["ticker"].nunique()),
            "v3_b_rows": int(len(v3_table)),
            "v3_b_tickers": int(v3_table["ticker"].nunique()),
            "o2_rows": int(len(o2_table)),
            "o2_tickers": int(o2_table["ticker"].nunique()),
            "v2_key_sha256": _stable_key_hash(v2_table),
            "o2_key_sha256": _stable_key_hash(o2_table),
        },
        "artifacts": artifacts,
        "prohibited_actions": {
            "model_fit": False,
            "provider_calls": False,
            "protected_outcomes_accessed": False,
            "forward_scoring": False,
            "old_artifacts_overwritten": False,
        },
    }
    report_path = output_dir / "pit_safe_reconstruction_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    manifest = {
        "schema": "idx-trade/pit-safe-v2-v3b-o2-reconstruction-v1",
        "status": report["status"],
        "reproduction_boundary": report["reproduction_boundary"],
        "code_commit": code_commit,
        "protocol_sha256": report["protocol_sha256"],
        "parent_artifacts": report["parent_artifacts"],
        "artifacts": {**artifacts, report_path.name: sha256_file(report_path)},
    }
    manifest_path = output_dir / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    report["report_path"] = str(report_path)
    report["report_sha256"] = sha256_file(report_path)
    report["manifest_path"] = str(manifest_path)
    report["manifest_sha256"] = sha256_file(manifest_path)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("panel_path", "calendar_path", "security_master_path", "h10_labels_path", "old_v2_table_path", "coverage_path", "protocol_path", "output_dir"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = reconstruct_inputs(**vars(args))
    print(json.dumps({key: report[key] for key in ("status", "reproduction_boundary", "panel_listing_domain", "v2_identity_delta", "v2_feature_delta", "corrected_inputs", "report_path", "manifest_path", "manifest_sha256")}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
