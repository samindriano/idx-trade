from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .provenance import sha256_file
from .ranking_v2_candidate import _assert_clean_output_dir
from .ranking_v3_structure_lite import (
    CALENDAR_SHA256,
    PANEL_SHA256,
    V3_B_FEATURE_COLUMNS,
    _read_calendar,
)
from .ranking_v4_participation import (
    MAX_V4_A_HISTORICAL_SIGNAL_INDEX,
    V4_A1_MODEL_FEATURE_COLUMNS,
    V4_A2_MODEL_FEATURE_COLUMNS,
    assert_historical_boundary,
    assert_spec_identity,
    feature_order_sha256,
)
from .research_v4_participation import (
    V4_A1_FEATURE_COLUMNS,
    V4_A2_FEATURE_COLUMNS,
    V4_A_FEATURE_COLUMNS,
    build_participation_quality_features,
)


V3_FINAL_LATE_CACHE_SHA256 = (
    "af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d"
)
V3_FINAL_LATE_MANIFEST_SHA256 = (
    "1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880"
)
V3_FINAL_LATE_CACHE_STATUS = "RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CACHE_FROZEN"
V4_A_CACHE_STATUS = "RANKING_V4_A_PARTICIPATION_CACHE_FROZEN_PRE_OUTCOME"


def _read_panel_bounded(path: Path, max_date: pd.Timestamp) -> pd.DataFrame:
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise RuntimeError("V4-A feature preparation requires Parquet signal panel")
    frame = pd.read_parquet(path, filters=[("date", "<=", max_date)])
    if frame.empty:
        raise RuntimeError("V4-A bounded signal panel is empty")
    frame = frame.copy()
    frame["date"] = (
        pd.to_datetime(frame["date"], errors="raise")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    if (frame["date"] > max_date).any():
        raise RuntimeError("V4-A panel physical read escaped session-1224 boundary")
    return frame


def _assert_v3_base_cache(cache_path: Path, manifest_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    actual_cache_sha = sha256_file(cache_path)
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_cache_sha != V3_FINAL_LATE_CACHE_SHA256:
        raise RuntimeError(
            "V4-A requires exact frozen V3-B late-development cache: "
            f"expected={V3_FINAL_LATE_CACHE_SHA256} actual={actual_cache_sha}"
        )
    if actual_manifest_sha != V3_FINAL_LATE_MANIFEST_SHA256:
        raise RuntimeError(
            "V4-A requires exact frozen V3-B late-development manifest: "
            f"expected={V3_FINAL_LATE_MANIFEST_SHA256} actual={actual_manifest_sha}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != V3_FINAL_LATE_CACHE_STATUS:
        raise RuntimeError("V4-A V3-B base manifest has unexpected status")
    if bool(manifest.get("post_1224_materialized", True)):
        raise RuntimeError("V4-A V3-B base manifest claims session 1225+ materialization")
    table = pd.read_parquet(cache_path)
    if table.empty:
        raise RuntimeError("V4-A V3-B base cache is empty")
    table = table.copy()
    table["ticker"] = (
        table["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    table["date"] = (
        pd.to_datetime(table["date"], errors="raise")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    table["signal_session_index"] = pd.to_numeric(
        table["signal_session_index"], errors="raise"
    ).astype(int)
    assert_historical_boundary(table)
    required = {"ticker", "date", "signal_session_index", *V3_B_FEATURE_COLUMNS}
    missing = required - set(table.columns)
    if missing:
        raise RuntimeError(f"V4-A V3-B base cache missing columns: {sorted(missing)}")
    if table.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V4-A V3-B base cache contains duplicate ticker/date rows")
    return table, manifest


def _coverage(frame: pd.DataFrame) -> dict[str, Any]:
    overall: dict[str, Any] = {}
    for column in V4_A_FEATURE_COLUMNS:
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        finite = np.isfinite(values)
        overall[column] = {
            "rows": int(len(values)),
            "finite_rows": int(finite.sum()),
            "finite_rate": float(finite.mean()) if len(values) else 0.0,
            "missing_rate": float(1.0 - finite.mean()) if len(values) else 1.0,
        }
    return overall


def prepare_v4a_cache(
    *,
    panel_path: Path,
    calendar_path: Path,
    v3_cache_path: Path,
    v3_manifest_path: Path,
    spec_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    """Append frozen A1+A2 features to exact V3-B rows without scoring outcomes."""

    _assert_clean_output_dir(output_dir)
    spec_blob = assert_spec_identity(spec_path)

    source_hashes = {
        "panel": sha256_file(panel_path),
        "calendar": sha256_file(calendar_path),
        "v3_cache": sha256_file(v3_cache_path),
        "v3_manifest": sha256_file(v3_manifest_path),
    }
    expected = {
        "panel": PANEL_SHA256,
        "calendar": CALENDAR_SHA256,
        "v3_cache": V3_FINAL_LATE_CACHE_SHA256,
        "v3_manifest": V3_FINAL_LATE_MANIFEST_SHA256,
    }
    if source_hashes != expected:
        raise RuntimeError(
            f"V4-A source identity mismatch: expected={expected} actual={source_hashes}"
        )

    base, base_manifest = _assert_v3_base_cache(v3_cache_path, v3_manifest_path)
    sessions = _read_calendar(calendar_path)
    if len(sessions) < MAX_V4_A_HISTORICAL_SIGNAL_INDEX:
        raise RuntimeError("official calendar does not cover V4-A session 1224")
    max_date = pd.Timestamp(sessions[MAX_V4_A_HISTORICAL_SIGNAL_INDEX - 1])
    panel = _read_panel_bounded(panel_path, max_date)
    participation = build_participation_quality_features(
        panel,
        sessions,
        max_signal_session_index=MAX_V4_A_HISTORICAL_SIGNAL_INDEX,
    )
    assert_historical_boundary(participation)

    participation_keyed = participation.set_index(["ticker", "date"])
    keys = pd.MultiIndex.from_frame(base[["ticker", "date"]])
    if not keys.is_unique:
        raise RuntimeError("V4-A base keys are not unique")
    missing_keys = keys.difference(participation_keyed.index)
    if len(missing_keys):
        raise RuntimeError(
            f"V4-A participation join has {len(missing_keys)} orphan V3-B rows"
        )

    joined = base.copy()
    aligned = participation_keyed.reindex(keys)
    for column in V4_A_FEATURE_COLUMNS:
        joined[column] = aligned[column].to_numpy()

    original_columns = list(base.columns)
    if not joined.loc[:, original_columns].equals(base.loc[:, original_columns]):
        raise RuntimeError("V4-A preparation changed existing V3-B cache columns")
    if tuple(V4_A1_MODEL_FEATURE_COLUMNS[: len(V3_B_FEATURE_COLUMNS)]) != tuple(
        V3_B_FEATURE_COLUMNS
    ):
        raise RuntimeError("V4-A1 does not preserve exact V3-B feature prefix")
    if tuple(V4_A2_MODEL_FEATURE_COLUMNS[: len(V3_B_FEATURE_COLUMNS)]) != tuple(
        V3_B_FEATURE_COLUMNS
    ):
        raise RuntimeError("V4-A2 does not preserve exact V3-B feature prefix")
    if joined.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V4-A prepared cache contains duplicate ticker/date rows")
    assert_historical_boundary(joined)

    for column in V4_A_FEATURE_COLUMNS:
        values = pd.to_numeric(joined[column], errors="coerce").to_numpy(dtype=float)
        if np.isinf(values).any():
            raise RuntimeError(f"V4-A prepared feature contains infinity: {column}")

    cache_path = output_dir / "ranking_v4_a_participation_prepared_cache.parquet"
    joined.to_parquet(cache_path, index=False)
    manifest = {
        "status": V4_A_CACHE_STATUS,
        "code_commit": code_commit,
        "spec_git_blob": spec_blob,
        "source_sha256": source_hashes,
        "base_v3_status": base_manifest.get("status"),
        "cache_path": str(cache_path),
        "cache_sha256": sha256_file(cache_path),
        "rows": int(len(joined)),
        "tickers": int(joined["ticker"].nunique()),
        "first_signal_session_index": int(joined["signal_session_index"].min()),
        "last_signal_session_index": int(joined["signal_session_index"].max()),
        "v3_b_feature_columns": list(V3_B_FEATURE_COLUMNS),
        "v4_a1_feature_columns": list(V4_A1_FEATURE_COLUMNS),
        "v4_a2_feature_columns": list(V4_A2_FEATURE_COLUMNS),
        "v4_a1_model_feature_order_sha256": feature_order_sha256(
            V4_A1_MODEL_FEATURE_COLUMNS
        ),
        "v4_a2_model_feature_order_sha256": feature_order_sha256(
            V4_A2_MODEL_FEATURE_COLUMNS
        ),
        "coverage": _coverage(joined),
        "post_1224_materialized": False,
        "outcome_metrics_computed": False,
        "fresh_forward_accessed": False,
        "integration_candidate_materialized": False,
        "independent_validation_claim": False,
    }
    manifest_path = output_dir / "ranking_v4_a_participation_prepared_cache_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest
