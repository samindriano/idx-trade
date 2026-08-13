"""Frozen Ranking V2 final-refit and outcome-blind forward runtime.

This module deliberately separates the authorized implementation phase from
the later one-shot outcome-access phase.  The final refit reads only the
immutable historical prepared cache.  Forward feature construction and H10
maturity diagnostics never read labels or outcomes.  The access-marker writer
exists for the separately authorized phase and is covered only with temporary
fixtures in tests.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence, TypeVar

import joblib
import numpy as np
import pandas as pd

from .provenance import environment_manifest, sha256_file, write_manifest_atomic
from .research_features import build_baseline_features
from .research_v2_features import V2_FULL_FEATURE_COLUMNS, build_v2_feature_table
from .research_v2_models import HGB_XS_MARKET, pointwise_model, pointwise_raw_score
from .research_v2_validation import evaluate_v2_scores


FROZEN_PREPARED_CACHE_SHA256 = "522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5"
FROZEN_PREPARED_MANIFEST_SHA256 = "6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143"
FROZEN_SPEC_BLOB = "77b2d74c9d5f28460037c11cd3a134c6b6cc9d3d"
FROZEN_CACHE_ROWS = 292_633
FROZEN_CACHE_TICKERS = 737
FROZEN_CACHE_FIRST_SESSION = 20
FROZEN_CACHE_LAST_SESSION = 1_250
FRESH_FORWARD_CUTOFF = pd.Timestamp("2026-07-31")
FORWARD_OUTCOME_ACCESS_STARTED = "FORWARD_OUTCOME_ACCESS_STARTED"
FIRST_VERDICT_MATURE_SESSIONS = 100

FROZEN_FEATURE_COLUMNS = tuple(V2_FULL_FEATURE_COLUMNS)
FROZEN_MODEL_CONFIG: dict[str, Any] = {
    "candidate": HGB_XS_MARKET,
    "preprocessing": {
        "transformer": "ColumnTransformer",
        "selected_columns": list(FROZEN_FEATURE_COLUMNS),
        "remainder": "drop",
        "imputer": {
            "strategy": "median",
            "add_indicator": True,
            "keep_empty_features": True,
        },
        "scaler": None,
    },
    "estimator": {
        "class": "HistGradientBoostingClassifier",
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 31,
        "l2_regularization": 1.0,
        "random_state": 42,
    },
    "score_semantics": "logit_of_clipped_predict_proba_positive_class_ranking_only",
    "probability_claim": False,
}

_T = TypeVar("_T")


def _json_default(value: object) -> str:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    return str(value)


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported table format: {path}")


def _normalize_dates(values: Iterable[object]) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
    if dates.tz is not None:
        dates = dates.tz_localize(None)
    dates = dates.normalize().dropna().unique().sort_values()
    if len(dates) == 0:
        raise ValueError("official session/date input must not be empty")
    return dates


def _normalized_date_series(values: pd.Series, *, name: str) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce")
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_localize(None)
    dates = dates.dt.normalize()
    if dates.isna().any():
        raise ValueError(f"{name} contains invalid dates")
    return dates


def _installed_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _runtime_environment(*, source_paths: Iterable[Path], config: Mapping[str, Any]) -> dict[str, Any]:
    environment = environment_manifest(source_paths=source_paths, config=dict(config))
    packages = dict(environment.get("packages", {}))
    packages["scikit-learn"] = _installed_version("scikit-learn")
    packages["joblib"] = _installed_version("joblib")
    environment["packages"] = packages
    environment["runtime"] = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
    }
    environment["manifest_sha256"] = _canonical_hash(environment)
    return environment


def _assert_new_or_empty_directory(path: Path, *, label: str) -> None:
    if path.exists() and any(path.iterdir()):
        raise RuntimeError(f"{label} must be new or empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _timed(name: str, function: Callable[[], _T]) -> tuple[_T, dict[str, Any]]:
    started = time.perf_counter()
    value = function()
    elapsed = time.perf_counter() - started
    return value, {"stage": name, "wall_seconds": float(elapsed)}


def normalize_final_refit_table(table: pd.DataFrame, *, require_frozen_counts: bool = True) -> pd.DataFrame:
    """Validate the exact resolved-primary-H10 table allowed for one final fit."""

    required = {
        "ticker",
        "date",
        "signal_session_index",
        "binary_target",
        "label_status",
        "universe_primary_liquid",
        *FROZEN_FEATURE_COLUMNS,
    }
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"final-refit table missing {sorted(missing)}")

    data = table.loc[:, sorted(required)].copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["date"] = _normalized_date_series(data["date"], name="final-refit date")
    data["signal_session_index"] = pd.to_numeric(data["signal_session_index"], errors="raise").astype(int)
    data["binary_target"] = pd.to_numeric(data["binary_target"], errors="raise").astype(int)
    if not set(data["binary_target"].unique()).issubset({0, 1}):
        raise ValueError("final-refit binary_target must contain only 0/1")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("final-refit table contains duplicate ticker/date rows")
    if not data["universe_primary_liquid"].astype(bool).all():
        raise ValueError("final-refit rows must all be primary-liquid")
    if not data["label_status"].isin(["TP_FIRST", "SL_FIRST"]).all():
        raise ValueError("final-refit rows must all have resolved H10 labels")
    if not data["signal_session_index"].between(
        FROZEN_CACHE_FIRST_SESSION, FROZEN_CACHE_LAST_SESSION
    ).all():
        raise ValueError("final-refit signal sessions must stay inside 20..1250")
    if np.unique(data["binary_target"]).size != 2:
        raise ValueError("final-refit table must contain both target classes")

    if require_frozen_counts:
        facts = {
            "rows": len(data),
            "tickers": data["ticker"].nunique(),
            "first_signal_session_index": int(data["signal_session_index"].min()),
            "last_signal_session_index": int(data["signal_session_index"].max()),
        }
        expected = {
            "rows": FROZEN_CACHE_ROWS,
            "tickers": FROZEN_CACHE_TICKERS,
            "first_signal_session_index": FROZEN_CACHE_FIRST_SESSION,
            "last_signal_session_index": FROZEN_CACHE_LAST_SESSION,
        }
        if facts != expected:
            raise RuntimeError(f"final-refit table facts mismatch: expected={expected} actual={facts}")

    return data.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def _verify_prepared_cache(
    *,
    prepared_table_path: Path,
    expected_cache_sha256: str,
    prepared_manifest_path: Path,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    actual_cache_sha256 = sha256_file(prepared_table_path)
    if actual_cache_sha256 != expected_cache_sha256:
        raise RuntimeError(
            f"prepared-cache hash mismatch: expected={expected_cache_sha256} actual={actual_cache_sha256}"
        )
    actual_manifest_sha256 = sha256_file(prepared_manifest_path)
    if actual_manifest_sha256 != expected_manifest_sha256:
        raise RuntimeError(
            f"prepared-cache manifest hash mismatch: expected={expected_manifest_sha256} "
            f"actual={actual_manifest_sha256}"
        )
    manifest = json.loads(prepared_manifest_path.read_text(encoding="utf-8"))
    checks = {
        "cache_sha256": actual_cache_sha256,
        "manifest_sha256": actual_manifest_sha256,
        "rows": manifest.get("rows"),
        "tickers": manifest.get("tickers"),
        "first_signal_session_index": manifest.get("first_signal_session_index"),
        "last_signal_session_index": manifest.get("last_signal_session_index"),
    }
    expected = {
        "cache_sha256": expected_cache_sha256,
        "manifest_sha256": expected_manifest_sha256,
        "rows": FROZEN_CACHE_ROWS,
        "tickers": FROZEN_CACHE_TICKERS,
        "first_signal_session_index": FROZEN_CACHE_FIRST_SESSION,
        "last_signal_session_index": FROZEN_CACHE_LAST_SESSION,
    }
    if checks != expected:
        raise RuntimeError(f"prepared-cache manifest facts mismatch: expected={expected} actual={checks}")
    return manifest


def run_final_refit(
    *,
    prepared_table_path: Path,
    prepared_manifest_path: Path,
    output_dir: Path,
    code_commit: str,
    expected_cache_sha256: str = FROZEN_PREPARED_CACHE_SHA256,
    expected_manifest_sha256: str = FROZEN_PREPARED_MANIFEST_SHA256,
    spec_blob: str = FROZEN_SPEC_BLOB,
) -> dict[str, Any]:
    """Fit exactly one frozen HGB_XS_MARKET model and hash its artifacts."""

    _assert_new_or_empty_directory(output_dir, label="final-refit output directory")
    timings: list[dict[str, Any]] = []
    prepared_manifest = _verify_prepared_cache(
        prepared_table_path=prepared_table_path,
        expected_cache_sha256=expected_cache_sha256,
        prepared_manifest_path=prepared_manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )

    table, timing = _timed("cache_read_and_normalize", lambda: normalize_final_refit_table(_read_table(prepared_table_path)))
    timings.append(timing)
    model, timing = _timed("final_model_fit", lambda: pointwise_model(HGB_XS_MARKET).fit(table, table["binary_target"].to_numpy()))
    timings.append(timing)

    model_path = output_dir / "ranking_v2_hgb_xs_market_final.joblib"
    _, timing = _timed("model_serialization", lambda: joblib.dump(model, model_path))
    timings.append(timing)
    model_sha256 = sha256_file(model_path)

    source_paths = [
        Path(__file__),
        Path(__file__).with_name("research_v2_models.py"),
        Path(__file__).with_name("research_v2_features.py"),
    ]
    environment = _runtime_environment(
        source_paths=source_paths,
        config={"phase": "RANKING_V2_FINAL_REFIT", "outcome_access": False},
    )
    manifest_payload: dict[str, Any] = {
        "status": "RANKING_V2_FINAL_REFIT_FROZEN",
        "champion": HGB_XS_MARKET,
        "code_commit": code_commit,
        "spec_blob": spec_blob,
        "prepared_cache_path": str(prepared_table_path),
        "prepared_cache_sha256": expected_cache_sha256,
        "prepared_cache_manifest_path": str(prepared_manifest_path),
        "prepared_cache_manifest_sha256": expected_manifest_sha256,
        "prepared_cache_manifest_status": prepared_manifest.get("status"),
        "model_path": str(model_path),
        "model_sha256": model_sha256,
        "rows": int(len(table)),
        "tickers": int(table["ticker"].nunique()),
        "first_signal_session_index": int(table["signal_session_index"].min()),
        "last_signal_session_index": int(table["signal_session_index"].max()),
        "positive_rate": float(table["binary_target"].mean()),
        "feature_columns": list(FROZEN_FEATURE_COLUMNS),
        "model_config": FROZEN_MODEL_CONFIG,
        "environment": environment,
        "profiling": timings,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "independent_validation_claim": False,
    }
    manifest_payload["manifest_content_sha256"] = _canonical_hash(manifest_payload)
    manifest_path = output_dir / "ranking_v2_hgb_xs_market_final_manifest.json"
    write_manifest_atomic(manifest_path, manifest_payload)
    manifest_sha256 = sha256_file(manifest_path)

    summary = {
        "status": "RANKING_V2_FINAL_REFIT_FROZEN",
        "champion": HGB_XS_MARKET,
        "code_commit": code_commit,
        "model_path": str(model_path),
        "model_sha256": model_sha256,
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha256,
        "rows": int(len(table)),
        "tickers": int(table["ticker"].nunique()),
        "first_signal_session_index": int(table["signal_session_index"].min()),
        "last_signal_session_index": int(table["signal_session_index"].max()),
        "prepared_cache_sha256": expected_cache_sha256,
        "prepared_cache_manifest_sha256": expected_manifest_sha256,
        "profiling": timings,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
    }
    summary_path = output_dir / "ranking_v2_hgb_xs_market_final_summary.json"
    write_manifest_atomic(summary_path, summary)
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def verify_final_refit_artifacts(
    *,
    model_path: Path,
    manifest_path: Path,
    expected_model_sha256: str,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    """Verify the frozen final model/manifest pair without reading outcomes."""

    actual_model_sha256 = sha256_file(model_path)
    actual_manifest_sha256 = sha256_file(manifest_path)
    if actual_model_sha256 != expected_model_sha256:
        raise RuntimeError(f"final model hash mismatch: expected={expected_model_sha256} actual={actual_model_sha256}")
    if actual_manifest_sha256 != expected_manifest_sha256:
        raise RuntimeError(
            f"final model manifest hash mismatch: expected={expected_manifest_sha256} actual={actual_manifest_sha256}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("champion") != HGB_XS_MARKET:
        raise RuntimeError("final model manifest champion mismatch")
    if manifest.get("model_sha256") != expected_model_sha256:
        raise RuntimeError("final model manifest does not pin its model hash")
    if manifest.get("fresh_forward_outcomes_accessed") is not False:
        raise RuntimeError("final model manifest has an invalid outcome-access flag")
    if manifest.get("forward_outcome_access_marker_written") is not False:
        raise RuntimeError("final model manifest has an invalid marker flag")
    return {
        "valid": True,
        "model_sha256": actual_model_sha256,
        "manifest_sha256": actual_manifest_sha256,
        "rows": manifest.get("rows"),
        "tickers": manifest.get("tickers"),
        "first_signal_session_index": manifest.get("first_signal_session_index"),
        "last_signal_session_index": manifest.get("last_signal_session_index"),
    }


_FORWARD_REQUIRED_RAW_COLUMNS = {
    "ticker",
    "date",
    "high",
    "low",
    "close",
    "volume",
    "regular_market_value",
}
_OUTCOME_COLUMN_NAMES = {
    "binary_target",
    "label_status",
    "target",
    "outcome",
    "future_outcome",
    "tp_first",
    "sl_first",
}


def assert_outcome_blind_columns(columns: Iterable[object]) -> None:
    offenders = {
        str(column).strip().lower()
        for column in columns
        if str(column).strip().lower() in _OUTCOME_COLUMN_NAMES
    }
    if offenders:
        raise ValueError(f"outcome-blind forward input contains outcome columns: {sorted(offenders)}")


def build_outcome_blind_forward_features(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    listed_from: Mapping[str, object] | None = None,
    cutoff_date: object = FRESH_FORWARD_CUTOFF,
) -> pd.DataFrame:
    """Build post-cutoff V2 features from an outcome-free causal price snapshot.

    The panel must include the historical causal prefix needed for rolling
    features and canonical common-stock, official ACTIVE regular-market rows.
    The function intentionally selects only raw price/liquidity columns before
    feature construction so accidental labels/outcomes cannot be propagated.
    """

    assert_outcome_blind_columns(panel.columns)
    missing = _FORWARD_REQUIRED_RAW_COLUMNS - set(panel.columns)
    if missing:
        raise ValueError(f"outcome-blind forward panel missing {sorted(missing)}")
    data = panel.loc[:, sorted(_FORWARD_REQUIRED_RAW_COLUMNS)].copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["date"] = _normalized_date_series(data["date"], name="forward panel date")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("outcome-blind forward panel contains duplicate ticker/date rows")
    sessions = _normalize_dates(official_sessions)
    if not data["date"].isin(sessions).all():
        raise ValueError("forward panel contains dates outside the official session calendar")
    cutoff = pd.Timestamp(cutoff_date).tz_localize(None).normalize()
    if not (data["date"] > cutoff).any():
        raise ValueError("forward panel contains no post-cutoff signal sessions")

    baseline = build_baseline_features(data, sessions, listed_from=listed_from)
    v2 = build_v2_feature_table(baseline)
    forward = v2[v2["date"] > cutoff].copy().reset_index(drop=True)
    if forward.empty:
        raise ValueError("outcome-blind forward feature build produced no post-cutoff rows")
    return forward


def h10_maturity_diagnostics(
    signal_dates: Iterable[object],
    official_sessions: Iterable[object],
    *,
    complete_evidence: Mapping[object, bool] | pd.Series | None = None,
    horizon: int = 10,
) -> pd.DataFrame:
    """Return label-free H10 maturity/readiness diagnostics."""

    if horizon != 10:
        raise ValueError("this runtime freezes H10 only")
    sessions = _normalize_dates(official_sessions)
    index_by_date = {pd.Timestamp(date): index + 1 for index, date in enumerate(sessions)}
    normalized_signals = _normalize_dates(signal_dates)

    evidence_map: dict[pd.Timestamp, bool] = {}
    if complete_evidence is not None:
        items = complete_evidence.items() if isinstance(complete_evidence, Mapping) else complete_evidence.items()
        for key, value in items:
            evidence_map[pd.Timestamp(key).tz_localize(None).normalize()] = bool(value)

    rows: list[dict[str, Any]] = []
    for signal_date in normalized_signals:
        date = pd.Timestamp(signal_date)
        if date not in index_by_date:
            rows.append(
                {
                    "signal_date": date,
                    "signal_session_index": np.nan,
                    "maturity_date": pd.NaT,
                    "calendar_h10_complete": False,
                    "evidence_complete": False,
                    "mature": False,
                    "reason": "SIGNAL_NOT_OFFICIAL_SESSION",
                }
            )
            continue
        index = index_by_date[date]
        maturity_index = index + horizon
        calendar_complete = maturity_index <= len(sessions)
        maturity_date = sessions[maturity_index - 1] if calendar_complete else pd.NaT
        evidence_complete = evidence_map.get(date, True)
        if not calendar_complete:
            reason = "H10_ENDPOINT_NOT_YET_IN_OFFICIAL_CALENDAR"
        elif not evidence_complete:
            reason = "H10_EVIDENCE_INCOMPLETE"
        else:
            reason = "MATURE"
        rows.append(
            {
                "signal_date": date,
                "signal_session_index": index,
                "maturity_date": maturity_date,
                "calendar_h10_complete": bool(calendar_complete),
                "evidence_complete": bool(evidence_complete),
                "mature": bool(calendar_complete and evidence_complete),
                "reason": reason,
            }
        )
    return pd.DataFrame(rows).sort_values("signal_date", kind="mergesort").reset_index(drop=True)


def first_mature_forward_block(
    maturity: pd.DataFrame,
    *,
    block_size: int = FIRST_VERDICT_MATURE_SESSIONS,
) -> pd.DataFrame | None:
    """Select the first exact consecutive mature-session block, without labels."""

    required = {"signal_date", "signal_session_index", "mature"}
    missing = required - set(maturity.columns)
    if missing:
        raise ValueError(f"maturity table missing {sorted(missing)}")
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    data = maturity[maturity["mature"].astype(bool)].copy()
    if data.empty:
        return None
    data["signal_date"] = _normalized_date_series(data["signal_date"], name="maturity signal date")
    data["signal_session_index"] = pd.to_numeric(data["signal_session_index"], errors="raise").astype(int)
    data = data.sort_values("signal_session_index", kind="mergesort").drop_duplicates(
        "signal_session_index", keep="first"
    )
    session_index = data["signal_session_index"].to_numpy(dtype=int)
    starts = np.r_[0, np.flatnonzero(np.diff(session_index) != 1) + 1]
    ends = np.r_[starts[1:], len(data)]
    for start, end in zip(starts, ends, strict=True):
        if end - start >= block_size:
            return data.iloc[start : start + block_size].reset_index(drop=True)
    return None


def evaluate_frozen_forward_block(
    scored: pd.DataFrame,
    *,
    block_dates: Sequence[object],
    data_gates_pass: bool = True,
) -> dict[str, Any]:
    """Evaluate the fixed 100-session block using historical V2 semantics.

    This function is intentionally not called by the implementation run.  It
    is available for the separately authorized one-shot phase and requires
    caller-supplied resolved labels in ``scored``.
    """

    dates = _normalize_dates(block_dates)
    if len(dates) != FIRST_VERDICT_MATURE_SESSIONS:
        raise ValueError("forward verdict requires exactly 100 mature signal sessions")
    required = {"ticker", "date", "binary_target", "score"}
    missing = required - set(scored.columns)
    if missing:
        raise ValueError(f"scored forward block missing {sorted(missing)}")
    work = scored.copy()
    work["date"] = _normalized_date_series(work["date"], name="scored forward date")
    if set(work["date"].unique()) != set(dates):
        raise ValueError("scored forward rows do not exactly match the frozen 100-session block")
    if work["date"].nunique() != FIRST_VERDICT_MATURE_SESSIONS:
        raise ValueError("scored forward block contains duplicate or missing signal sessions")

    aggregate = evaluate_v2_scores(work, pd.to_numeric(work["score"], errors="raise").to_numpy(dtype=float))
    first_dates = dates[:50]
    last_dates = dates[50:]
    half_metrics: dict[str, dict[str, float]] = {}
    for name, half_dates in (("first_50", first_dates), ("last_50", last_dates)):
        block = work[work["date"].isin(half_dates)].copy()
        half_metrics[name] = evaluate_v2_scores(
            block,
            pd.to_numeric(block["score"], errors="raise").to_numpy(dtype=float),
        )

    finite_values = [
        aggregate["pr_auc_delta_vs_base"],
        aggregate["roc_auc"],
        aggregate["q5_minus_q1"],
        half_metrics["first_50"]["pr_auc_delta_vs_base"],
        half_metrics["first_50"]["q5_minus_q1"],
        half_metrics["last_50"]["pr_auc_delta_vs_base"],
        half_metrics["last_50"]["q5_minus_q1"],
    ]
    finite = bool(np.isfinite(np.asarray(finite_values, dtype=float)).all())
    stability = bool(
        half_metrics["first_50"]["pr_auc_delta_vs_base"] > 0
        and half_metrics["first_50"]["q5_minus_q1"] > 0
        and half_metrics["last_50"]["pr_auc_delta_vs_base"] > 0
        and half_metrics["last_50"]["q5_minus_q1"] > 0
    )
    pass_core = bool(
        data_gates_pass
        and finite
        and aggregate["pr_auc_delta_vs_base"] > 0
        and aggregate["roc_auc"] > 0.5
        and aggregate["q5_minus_q1"] > 0
        and stability
    )
    mixed_core = bool(
        data_gates_pass
        and finite
        and aggregate["pr_auc_delta_vs_base"] > 0
        and aggregate["q5_minus_q1"] > 0
    )
    decision = "PASS" if pass_core else "MIXED" if mixed_core else "FAIL"
    return {
        "decision": decision,
        "aggregate": aggregate,
        "first_50": half_metrics["first_50"],
        "last_50": half_metrics["last_50"],
        "data_gates_pass": bool(data_gates_pass),
        "all_metrics_finite": finite,
        "stability_pass": stability,
        "outcome_access_marker_written": False,
    }


def assert_forward_outcome_access_not_started(snapshot_parent: Path) -> Path:
    marker = snapshot_parent / FORWARD_OUTCOME_ACCESS_STARTED
    if marker.exists():
        raise RuntimeError(f"forward outcome access already started: {marker}")
    return marker


def write_forward_outcome_access_started(
    snapshot_parent: Path,
    *,
    pre_outcome_manifest_sha256: str,
    block_start: object,
    block_end: object,
) -> Path:
    """Atomically consume the one-shot marker in a separately authorized run."""

    marker = assert_forward_outcome_access_not_started(snapshot_parent)
    snapshot_parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "marker": FORWARD_OUTCOME_ACCESS_STARTED,
        "pre_outcome_manifest_sha256": pre_outcome_manifest_sha256,
        "block_start": str(pd.Timestamp(block_start).tz_localize(None).normalize().date()),
        "block_end": str(pd.Timestamp(block_end).tz_localize(None).normalize().date()),
    }
    try:
        with marker.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    except FileExistsError as exc:
        raise RuntimeError(f"forward outcome access already started: {marker}") from exc
    return marker


def write_pre_outcome_manifest(
    *,
    output_dir: Path,
    model_manifest_path: Path,
    code_commit: str,
    forward_snapshot_paths: Mapping[str, Path],
    intended_block: pd.DataFrame | None = None,
    spec_blob: str = FROZEN_SPEC_BLOB,
) -> dict[str, Any]:
    """Create the hashed pre-outcome contract without consuming the marker."""

    _assert_new_or_empty_directory(output_dir, label="pre-outcome manifest directory")
    model_manifest_sha256 = sha256_file(model_manifest_path)
    snapshot_hashes = {name: sha256_file(path) for name, path in forward_snapshot_paths.items()}
    block = None
    if intended_block is not None:
        required = {"signal_date", "signal_session_index"}
        if not required.issubset(intended_block.columns):
            raise ValueError(f"intended forward block missing {sorted(required - set(intended_block.columns))}")
        block = {
            "sessions": int(len(intended_block)),
            "first_signal_date": str(pd.Timestamp(intended_block["signal_date"].min()).date()),
            "last_signal_date": str(pd.Timestamp(intended_block["signal_date"].max()).date()),
            "first_signal_session_index": int(intended_block["signal_session_index"].min()),
            "last_signal_session_index": int(intended_block["signal_session_index"].max()),
        }
    payload: dict[str, Any] = {
        "status": "RANKING_V2_PRE_OUTCOME_MANIFEST_READY",
        "code_commit": code_commit,
        "spec_blob": spec_blob,
        "champion": HGB_XS_MARKET,
        "model_manifest_path": str(model_manifest_path),
        "model_manifest_sha256": model_manifest_sha256,
        "forward_snapshot_sha256": snapshot_hashes,
        "intended_block": block,
        "outcome_access_marker_written": False,
        "fresh_forward_outcomes_accessed": False,
        "environment": _runtime_environment(
            source_paths=[Path(__file__), model_manifest_path],
            config={"phase": "RANKING_V2_PRE_OUTCOME_MANIFEST", "outcome_access": False},
        ),
    }
    payload["manifest_content_sha256"] = _canonical_hash(payload)
    manifest_path = output_dir / "ranking_v2_pre_outcome_manifest.json"
    write_manifest_atomic(manifest_path, payload)
    return {
        "path": str(manifest_path),
        "sha256": sha256_file(manifest_path),
        "outcome_access_marker_written": False,
        "fresh_forward_outcomes_accessed": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Frozen Ranking V2 final-refit and outcome-blind runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)
    refit = subparsers.add_parser("final-refit", help="fit the one frozen HGB_XS_MARKET development model")
    refit.add_argument("--prepared-table", type=Path, required=True)
    refit.add_argument("--prepared-manifest", type=Path, required=True)
    refit.add_argument("--expected-cache-sha256", default=FROZEN_PREPARED_CACHE_SHA256)
    refit.add_argument("--expected-manifest-sha256", default=FROZEN_PREPARED_MANIFEST_SHA256)
    refit.add_argument("--output-dir", type=Path, required=True)
    refit.add_argument("--code-commit", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "final-refit":
        summary = run_final_refit(
            prepared_table_path=args.prepared_table,
            prepared_manifest_path=args.prepared_manifest,
            expected_cache_sha256=args.expected_cache_sha256,
            expected_manifest_sha256=args.expected_manifest_sha256,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default))
        return 0
    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
