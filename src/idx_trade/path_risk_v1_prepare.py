"""Outcome-blind Path Risk V1 discovery feature cache preparation."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .path_risk_v1 import (
    PATH_RISK_CACHE_STATUS,
    PATH_RISK_FEATURE_COLUMNS,
    PATH_RISK_FEATURE_ORDER_SHA256,
)
from .provenance import environment_manifest, sha256_file, write_manifest_atomic
from .ranking_v3_structure_lite import (
    CALENDAR_SHA256,
    MAX_DISCOVERY_SIGNAL_INDEX,
    PANEL_SHA256,
    SECURITY_MASTER_SHA256,
    _feature_order_hash,
    _normalized_git_blob_sha1,
)
from .research_features import build_baseline_features
from .research_v2_features import V2_FULL_FEATURE_COLUMNS, build_v2_feature_table
from .research_v3_structure_lite import STRUCTURE_LITE_FEATURE_COLUMNS, build_structure_lite_features


FROZEN_PANEL_SHA256 = PANEL_SHA256
FROZEN_CALENDAR_SHA256 = CALENDAR_SHA256
FROZEN_SECURITY_MASTER_SHA256 = SECURITY_MASTER_SHA256
DISCOVERY_MAX_SESSION = MAX_DISCOVERY_SIGNAL_INDEX
RAW_COLUMNS = ("ticker", "date", "high", "low", "close", "volume", "regular_market_value")
FORBIDDEN_CACHE_TOKENS = (
    "binary_target",
    "label_status",
    "target",
    "outcome",
    "future_outcome",
    "first_barrier_date",
    "mfe_h",
    "mae_h",
    "realized",
)


def _canonical_hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _assert_new_or_empty(directory: Path) -> None:
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError(f"Path Risk output directory must be new or empty: {directory}")
    directory.mkdir(parents=True, exist_ok=True)


def _read_calendar(path: Path) -> pd.DatetimeIndex:
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    candidates = [column for column in ("date", "session_date", "trading_date") if column in frame.columns]
    if len(candidates) != 1:
        raise ValueError(f"Path Risk calendar requires one recognized date column, got {candidates}")
    values = pd.to_datetime(frame[candidates[0]], errors="coerce")
    sessions = pd.DatetimeIndex(values).tz_localize(None).normalize().dropna().unique().sort_values()
    if len(sessions) < DISCOVERY_MAX_SESSION:
        raise ValueError("official calendar does not cover Path Risk discovery boundary")
    return sessions


def _read_listing_map(path: Path) -> dict[str, pd.Timestamp]:
    frame = pd.read_csv(path, usecols=["ticker", "listed_from"])
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    frame["listed_from"] = pd.to_datetime(frame["listed_from"], errors="coerce").dt.normalize()
    frame = frame.dropna(subset=["ticker", "listed_from"])
    return {str(ticker): pd.Timestamp(value) for ticker, value in frame.groupby("ticker")["listed_from"].min().items()}


def _read_panel_bounded(path: Path, max_date: pd.Timestamp) -> tuple[pd.DataFrame, list[str]]:
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("Path Risk discovery panel must be Parquet")
    schema_columns = list(pq.ParquetFile(path).schema.names)
    missing = set(RAW_COLUMNS) - set(schema_columns)
    if missing:
        raise ValueError(f"Path Risk panel missing {sorted(missing)}")
    columns = list(RAW_COLUMNS) + (["tradability_state"] if "tradability_state" in schema_columns else [])
    try:
        frame = pd.read_parquet(path, columns=columns, filters=[("date", "<=", max_date)])
    except Exception:
        frame = pd.read_parquet(path, columns=columns)
    frame = frame.copy()
    dates = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if dates.isna().any():
        raise ValueError("Path Risk panel contains invalid dates")
    frame["date"] = dates
    frame = frame[frame["date"] <= max_date].copy()
    if frame.empty or (frame["date"] > max_date).any():
        raise ValueError("Path Risk panel is empty or escaped the discovery boundary")
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("Path Risk panel contains duplicate ticker/date rows")
    if "tradability_state" in frame.columns and not frame["tradability_state"].astype(str).str.upper().eq("ACTIVE").all():
        raise ValueError("Path Risk discovery panel must contain ACTIVE rows only")
    return frame, schema_columns


def _environment(*, source_paths: list[Path], config: dict[str, Any]) -> dict[str, Any]:
    environment = environment_manifest(source_paths=source_paths, config=config)
    environment["runtime"] = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
    }
    environment["manifest_sha256"] = _canonical_hash(environment)
    return environment


def _build_cache(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    spec_path: Path,
    output_dir: Path,
    code_commit: str,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    _assert_new_or_empty(output_dir)
    source_hashes = {
        "panel": sha256_file(panel_path),
        "calendar": sha256_file(calendar_path),
        "security_master": sha256_file(security_master_path),
    }
    expected = {
        "panel": FROZEN_PANEL_SHA256,
        "calendar": FROZEN_CALENDAR_SHA256,
        "security_master": FROZEN_SECURITY_MASTER_SHA256,
    }
    if source_hashes != expected:
        raise RuntimeError(f"Path Risk source hash mismatch: expected={expected} actual={source_hashes}")
    spec_identity = {
        "spec_sha256_normalized": hashlib.sha256(spec_path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")).hexdigest(),
        "spec_git_blob": _normalized_git_blob_sha1(spec_path),
    }
    sessions = _read_calendar(calendar_path)
    max_date = pd.Timestamp(sessions[DISCOVERY_MAX_SESSION - 1])
    panel, panel_schema = _read_panel_bounded(panel_path, max_date)
    listing_map = _read_listing_map(security_master_path)

    started = time.perf_counter()
    baseline = build_baseline_features(panel, sessions, listed_from=listing_map)
    v2 = build_v2_feature_table(baseline)
    date_to_index = {pd.Timestamp(day): index + 1 for index, day in enumerate(sessions)}
    v2["signal_session_index"] = v2["date"].map(date_to_index).astype(int)
    v2 = v2[v2["signal_session_index"] <= DISCOVERY_MAX_SESSION].copy()
    structure = build_structure_lite_features(panel, sessions, max_signal_session_index=DISCOVERY_MAX_SESSION)
    primary = v2[v2["universe_primary_liquid"].astype(bool)].copy()
    if primary.empty:
        raise RuntimeError("Path Risk discovery produced no primary-liquid rows")
    keys = primary[["ticker", "date"]]
    if keys.duplicated().any() or structure.duplicated(["ticker", "date"]).any():
        raise RuntimeError("Path Risk discovery contains duplicate identity rows")
    structure_index = structure.set_index(["ticker", "date"])
    key_index = pd.MultiIndex.from_frame(keys)
    missing_keys = key_index.difference(structure_index.index)
    if len(missing_keys):
        raise RuntimeError(f"Path Risk Structure-Lite join has {len(missing_keys)} orphan rows")
    aligned = structure_index.reindex(key_index)
    cache = primary[["ticker", "date", "signal_session_index", "universe_primary_liquid", *V2_FULL_FEATURE_COLUMNS]].copy()
    for column in STRUCTURE_LITE_FEATURE_COLUMNS:
        cache[column] = pd.to_numeric(aligned[column], errors="coerce").to_numpy(dtype=float)
    cache = cache[["ticker", "date", "signal_session_index", "universe_primary_liquid", *PATH_RISK_FEATURE_COLUMNS]]
    cache = cache.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)
    if cache.duplicated(["ticker", "date"]).any():
        raise RuntimeError("Path Risk cache contains duplicate ticker/date rows")
    if int(cache["signal_session_index"].max()) > DISCOVERY_MAX_SESSION:
        raise RuntimeError("Path Risk cache contains session 985+")
    forbidden_columns = [
        column for column in cache.columns if any(token in column.lower() for token in FORBIDDEN_CACHE_TOKENS)
    ]
    if forbidden_columns:
        raise RuntimeError(f"Path Risk cache contains forbidden outcome columns: {forbidden_columns}")

    finite_report: dict[str, dict[str, Any]] = {}
    infinity_cells = 0
    constant_features: list[str] = []
    all_null_features: list[str] = []
    for column in PATH_RISK_FEATURE_COLUMNS:
        values = pd.to_numeric(cache[column], errors="coerce").to_numpy(dtype=float)
        finite = np.isfinite(values)
        infinity_cells += int(np.isinf(values).sum())
        unique = int(pd.Series(values[finite]).nunique())
        finite_report[column] = {
            "rows": int(len(values)),
            "finite_rows": int(finite.sum()),
            "finite_rate": float(finite.mean()),
            "unique_finite_values": unique,
        }
        if unique <= 1:
            constant_features.append(column)
        if not finite.any():
            all_null_features.append(column)
    if infinity_cells or all_null_features:
        raise RuntimeError(f"Path Risk cache finite audit failed: infinity={infinity_cells} all_null={all_null_features}")
    cache_path = output_dir / "path_risk_v1_discovery_feature_cache.parquet"
    cache.to_parquet(cache_path, index=False)
    cache_sha = sha256_file(cache_path)
    primary_counts = cache.groupby("date", sort=True).size()
    manifest = {
        "status": PATH_RISK_CACHE_STATUS,
        "code_commit": code_commit,
        "source_sha256": source_hashes,
        "spec_identity": spec_identity,
        "panel_schema_columns": panel_schema,
        "cache_path": str(cache_path),
        "cache_sha256": cache_sha,
        "rows": int(len(cache)),
        "tickers": int(cache["ticker"].nunique()),
        "first_signal_session_index": int(cache["signal_session_index"].min()),
        "last_signal_session_index": int(cache["signal_session_index"].max()),
        "feature_columns": list(PATH_RISK_FEATURE_COLUMNS),
        "feature_order_sha256": PATH_RISK_FEATURE_ORDER_SHA256,
        "v2_feature_order_sha256": _feature_order_hash(tuple(V2_FULL_FEATURE_COLUMNS)),
        "primary_liquid_count_by_date": {
            "min": int(primary_counts.min()),
            "median": float(primary_counts.median()),
            "max": int(primary_counts.max()),
        },
        "real_h10_labels_loaded": False,
        "real_path_risk_target_computed": False,
        "pr001_model_fitted": False,
        "path_risk_performance_metrics_computed": False,
        "f5_f6_path_risk_accessed": False,
        "fresh_forward_accessed": False,
        "forward_marker_written": False,
    }
    manifest_path = output_dir / "path_risk_v1_discovery_feature_cache_manifest.json"
    write_manifest_atomic(manifest_path, manifest)
    manifest_sha = sha256_file(manifest_path)
    audit = {
        "status": PATH_RISK_CACHE_STATUS,
        "cache_sha256": cache_sha,
        "manifest_sha256": manifest_sha,
        "source_sha256": source_hashes,
        "spec_identity": spec_identity,
        "rows": int(len(cache)),
        "tickers": int(cache["ticker"].nunique()),
        "first_signal_session_index": int(cache["signal_session_index"].min()),
        "last_signal_session_index": int(cache["signal_session_index"].max()),
        "primary_liquid_count_by_date": manifest["primary_liquid_count_by_date"],
        "feature_order_sha256": PATH_RISK_FEATURE_ORDER_SHA256,
        "feature_order_exact": list(cache.columns[4:]) == list(PATH_RISK_FEATURE_COLUMNS),
        "per_feature": finite_report,
        "infinity_cells": infinity_cells,
        "constant_features": constant_features,
        "all_null_features": all_null_features,
        "forbidden_outcome_columns": forbidden_columns,
        "real_h10_labels_loaded": False,
        "real_path_risk_target_computed": False,
        "pr001_model_fitted": False,
        "path_risk_performance_metrics_computed": False,
        "f5_f6_path_risk_accessed": False,
        "fresh_forward_accessed": False,
        "forward_marker_written": False,
        "runtime_seconds": float(time.perf_counter() - started),
        "environment": _environment(
            source_paths=[Path(__file__), Path(__file__).with_name("path_risk_v1.py"), spec_path],
            config={"phase": "PATH_RISK_V1_DISCOVERY_FEATURE_CACHE", "outcome_access": False},
        ),
    }
    audit_path = output_dir / "path_risk_v1_discovery_feature_audit.json"
    write_manifest_atomic(audit_path, audit)
    audit["audit_sha256"] = sha256_file(audit_path)
    return cache, manifest, audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Outcome-blind Path Risk V1 discovery cache")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--panel", type=Path, required=True)
    prepare.add_argument("--calendar", type=Path, required=True)
    prepare.add_argument("--security-master", type=Path, required=True)
    prepare.add_argument("--spec", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--code-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        _, manifest, audit = _build_cache(
            panel_path=args.panel,
            calendar_path=args.calendar,
            security_master_path=args.security_master,
            spec_path=args.spec,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
        print(json.dumps({"manifest": manifest, "audit": audit}, indent=2, ensure_ascii=False, default=str))
        return 0
    raise AssertionError(f"unsupported Path Risk command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
