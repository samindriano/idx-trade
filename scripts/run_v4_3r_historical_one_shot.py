"""One-shot historical-development execution for preregistered V4-3R CA80.

This is the first V4-3R runner authorized to materialize historical H5/H10
returns, target ranks, fit models, generate historical validation predictions,
and compute preregistered performance.  It must be executed once against the
exact frozen inputs.  Protected/fresh-forward outcomes are never accessed.

The only scientific delta from inherited V4-3 is the separately preregistered
0.90 -> 0.80 date-level target-support/evaluation coverage threshold.  Row-level
price/CA observability, target formulas, decision universe, folds, purge,
features, learner, hyperparameters, Top30 semantics, metrics, bootstrap, and
promotion gates remain unchanged.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

DEFAULT_CONFIG = REPO_ROOT / "config" / "ranking_v4_3r_historical_execution_v1.json"
SELF_PATH = "scripts/run_v4_3r_historical_one_shot.py"
PIT_SUPPORT_RUNNER = REPO_ROOT / "scripts" / "run_v4_3_pit_support_refresh.py"

from idx_trade.ranking_v4_3_features import (  # noqa: E402
    V4_CONTROL_FEATURE_COLUMNS,
    build_v4_control_feature_table,
)
from idx_trade.ranking_v4_3_model_eval import (  # noqa: E402
    CHALLENGER,
    CONTROL,
    attach_consensus_alpha,
    attach_folds,
    evaluate_absolute_viability_gates,
    evaluate_incremental_promotion_gates,
    fit_v4_head,
    fold_stratified_block_bootstrap_mean,
    paired_date_delta,
    percentile_ci,
    score_v4_head,
    summarize_fold_metrics,
    summarize_paired_deltas,
)
from idx_trade.ranking_v4_3_preregistration import (  # noqa: E402
    SESSION_GEOMETRY_FEATURE_COLUMNS,
)
from idx_trade.ranking_v4_3_target_execution import (  # noqa: E402
    TARGET_BOTH_AVAILABLE,
    TARGET_H10_AVAILABLE,
    TARGET_H5_AVAILABLE,
    build_geometry_from_accepted_open,
    materialize_v4_target_ledger,
)
from idx_trade.ranking_v4_3r_model_eval import (  # noqa: E402
    V4_3R_DATE_TARGET_COVERAGE_GATE,
    evaluate_head_by_date_ca80,
)


def _load_pit_support_runner():
    spec = importlib.util.spec_from_file_location("v4_3_pit_support_frozen", PIT_SUPPORT_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("PIT_SUPPORT_RUNNER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pit_support = _load_pit_support_runner()


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def git_output(repo_root: Path, *args: str, text: bool = True):
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return completed.stdout.strip() if text else completed.stdout


def git_bytes(repo_root: Path, relative: str) -> bytes:
    return git_output(repo_root, "show", f"HEAD:{relative}", text=False)


def package_version(name: str) -> str:
    return importlib.metadata.version(name)


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def normalize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["ticker"] = (
        out["ticker"]
        .astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )
    out["date"] = (
        pd.to_datetime(out["date"], errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    if out["ticker"].eq("").any() or out["date"].isna().any():
        raise RuntimeError("INVALID_TICKER_DATE_IDENTITY")
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-freeze-root", type=Path, required=True)
    parser.add_argument("--prefit-root", type=Path, required=True)
    parser.add_argument("--parent-combined-replay-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--open-derivative-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_git_blobs(repo_root: Path, mapping: dict[str, str]) -> dict[str, str]:
    actual: dict[str, str] = {}
    for relative, expected in mapping.items():
        blob = git_output(repo_root, "rev-parse", f"HEAD:{relative}")
        if blob != expected:
            raise RuntimeError(f"SCIENTIFIC_GIT_BLOB_CHANGED:{relative}:{blob}!={expected}")
        actual[relative] = blob
    return actual


def verify_runtime(repo_root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    ref = cfg["runtime_manifest"]
    raw = git_bytes(repo_root, ref["path"])
    actual_sha = sha256_bytes(raw)
    if actual_sha != ref["sha256"]:
        raise RuntimeError(f"RUNTIME_MANIFEST_SHA_MISMATCH:{actual_sha}!={ref['sha256']}")
    runtime = json.loads(raw.decode("utf-8"))
    expected_python = tuple(runtime["python"]["version_info"][:3])
    actual_python = tuple(sys.version_info[:3])
    if actual_python != expected_python:
        raise RuntimeError(f"PYTHON_VERSION_MISMATCH:{actual_python}!={expected_python}")
    expected_packages = runtime["package_versions"]
    actual_packages = {
        "joblib": package_version("joblib"),
        "numpy": package_version("numpy"),
        "pandas": package_version("pandas"),
        "pyarrow": package_version("pyarrow"),
        "scikit-learn": package_version("scikit-learn"),
        "scipy": package_version("scipy"),
        "threadpoolctl": package_version("threadpoolctl"),
    }
    if actual_packages != expected_packages:
        raise RuntimeError(
            "RUNTIME_PACKAGE_VERSION_MISMATCH:"
            + json.dumps({"actual": actual_packages, "expected": expected_packages}, sort_keys=True)
        )
    return {
        "manifest_sha256": actual_sha,
        "python_version": list(actual_python),
        "package_versions": actual_packages,
        "exact_match": True,
    }


def verify_execution_freeze(root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    path = root / "v4_3r_execution_freeze_manifest.json"
    actual_sha = sha256_file(path)
    expected = cfg["execution_freeze"]
    if actual_sha != expected["manifest_sha256"]:
        raise RuntimeError(
            f"EXECUTION_FREEZE_MANIFEST_SHA_MISMATCH:{actual_sha}!={expected['manifest_sha256']}"
        )
    data = read_json(path, "EXECUTION_FREEZE")
    if data.get("status") != expected["status"]:
        raise RuntimeError("EXECUTION_FREEZE_STATUS_CHANGED")
    if data.get("generation_id") != "V4_3R_CA80" or data.get("outcome_blind") is not True:
        raise RuntimeError("EXECUTION_FREEZE_IDENTITY_CHANGED")
    if data.get("historical_execution_authorized") is not True:
        raise RuntimeError("EXECUTION_FREEZE_NOT_AUTHORIZED")
    if data.get("protected_forward_access_authorized") is not False:
        raise RuntimeError("PROTECTED_FORWARD_UNEXPECTEDLY_AUTHORIZED")
    for key in (
        "historical_target_loaded",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
        "provider_calls",
    ):
        if data.get(key) is not False:
            raise RuntimeError(f"EXECUTION_FREEZE_PREACCESS_GUARD_CHANGED:{key}")
    if float(data.get("support_gate", -1.0)) != 0.80:
        raise RuntimeError("EXECUTION_FREEZE_SUPPORT_GATE_CHANGED")
    return data


def verify_prefit(root: Path, cfg: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    manifest_path = root / "MANIFEST.json"
    training_path = root / "v4_3r_ca80_training_date_sets.csv"
    summary_path = root / "summary.json"
    expected = cfg["prefit_support"]
    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(f"PREFIT_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}")
    manifest = read_json(manifest_path, "PREFIT_MANIFEST")
    summary = read_json(summary_path, "PREFIT_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("PREFIT_STATUS_CHANGED")
    if summary.get("historical_execution_authorized") is not True:
        raise RuntimeError("PREFIT_EXECUTION_NOT_AUTHORIZED")
    for key in ("historical_target_loaded", "model_fit", "performance_computed"):
        if summary.get(key) is not False:
            raise RuntimeError(f"PREFIT_PREACCESS_GUARD_CHANGED:{key}")
    output_hashes = manifest.get("output_hashes") or {}
    hashes = {
        "manifest": actual_manifest,
        "training_dates": sha256_file(training_path),
        "summary": sha256_file(summary_path),
    }
    for key in ("training_dates", "summary"):
        if hashes[key] != clean(output_hashes.get(key)):
            raise RuntimeError(f"PREFIT_CHILD_SHA_MISMATCH:{key}")
    training = pd.read_csv(training_path)
    training["date"] = pd.to_datetime(training["date"], errors="coerce").dt.normalize()
    if training["date"].isna().any():
        raise RuntimeError("PREFIT_TRAINING_DATE_INVALID")
    expected_counts = {
        (int(row["fold"]), str(row["head"])): int(row["training_dates"])
        for row in expected["training_date_counts"]
    }
    actual_counts = training.groupby(["fold", "head"], sort=True).size().to_dict()
    if actual_counts != expected_counts:
        raise RuntimeError(f"PREFIT_TRAINING_COUNTS_CHANGED:{actual_counts}!={expected_counts}")
    return training, hashes


def verify_parent_combined(root: Path, cfg: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    manifest_path = root / "MANIFEST.json"
    continuity_path = root / "v4_3_ca_training_domain_idx_combined_continuity.csv"
    combined_path = root / "v4_3_full_target_support_rows_idx_combined.csv"
    expected = cfg["parent_combined_replay"]
    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(
            f"PARENT_COMBINED_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = read_json(manifest_path, "PARENT_COMBINED_MANIFEST")
    outputs = manifest.get("output_hashes") or {}
    hashes = {
        "manifest": actual_manifest,
        "continuity": sha256_file(continuity_path),
        "combined": sha256_file(combined_path),
    }
    for key in ("continuity", "combined"):
        if hashes[key] != clean(outputs.get(key)):
            raise RuntimeError(f"PARENT_COMBINED_CHILD_SHA_MISMATCH:{key}")
    combined = normalize_identity(pd.read_csv(combined_path))
    continuity = pd.read_csv(continuity_path)
    continuity["ticker"] = (
        continuity["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    continuity["signal_date"] = pd.to_datetime(
        continuity["signal_date"], errors="coerce"
    ).dt.normalize()
    continuity["horizon"] = pd.to_numeric(continuity["horizon"], errors="raise").astype(int)
    if continuity["signal_date"].isna().any():
        raise RuntimeError("PARENT_CONTINUITY_DATE_INVALID")
    if combined.duplicated(["ticker", "date"]).any():
        raise RuntimeError("PARENT_COMBINED_DUPLICATE_IDENTITY")
    if continuity.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise RuntimeError("PARENT_CONTINUITY_DUPLICATE_IDENTITY")
    return combined, continuity, hashes


def load_frozen_market_inputs(args: argparse.Namespace, cfg: dict[str, Any]) -> tuple[dict[str, Path], dict[str, str]]:
    paths = {
        "calendar": args.artifact_root / "official_exchange_sessions_1260.csv",
        "panel": args.artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet",
        "anchors": args.artifact_root / "tradability_anchors_1260.csv",
        "intervals": args.artifact_root / "tradability_intervals_1260.csv",
        "open_derivative_panel": args.open_derivative_root / "execution_open_candidate_panel_yahoo_tradingview.parquet",
        "open_derivative_manifest": args.open_derivative_root / "artifact_manifest.json",
        "overlay_parquet": args.overlay_root / "open_recovery_overlay.parquet",
        "overlay_manifest": args.overlay_root / "manifest.json",
        "security_master": args.security_master,
    }
    hashes: dict[str, str] = {}
    for key, path in paths.items():
        actual = sha256_file(path)
        expected = cfg["market_input_sha256"][key]
        if actual != expected:
            raise RuntimeError(f"MARKET_INPUT_SHA_MISMATCH:{key}:{actual}!={expected}")
        hashes[key] = actual
    return paths, hashes


def load_validation_folds(repo_root: Path, cfg: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    ref = cfg["validation_folds"]
    raw = git_bytes(repo_root, ref["path"])
    actual = sha256_bytes(raw)
    if actual != ref["sha256"]:
        raise RuntimeError(f"VALIDATION_FOLDS_SHA_MISMATCH:{actual}!={ref['sha256']}")
    folds = pd.read_csv(Path(repo_root) / ref["path"])
    folds["date"] = pd.to_datetime(folds["date"], errors="coerce").dt.normalize()
    if len(folds) != 600 or folds["date"].isna().any() or folds["date"].duplicated().any():
        raise RuntimeError("VALIDATION_FOLD_IDENTITY_INVALID")
    counts = folds.groupby("fold").size().sort_index().tolist()
    if counts != [100] * 6:
        raise RuntimeError(f"VALIDATION_FOLD_COUNTS_CHANGED:{counts}")
    return folds, actual


def build_price_evidence(
    panel: pd.DataFrame,
    calendar: pd.DataFrame,
    derivative: pd.DataFrame,
    overlay: pd.DataFrame,
    anchors: pd.DataFrame,
    intervals: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    panel = normalize_identity(panel)
    derivative = normalize_identity(derivative)
    overlay = normalize_identity(overlay)
    if panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("PANEL_DUPLICATE_IDENTITY")
    if derivative.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OPEN_DERIVATIVE_DUPLICATE_IDENTITY")
    if overlay.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OPEN_OVERLAY_DUPLICATE_IDENTITY")
    if len(derivative) != len(panel):
        raise RuntimeError("OPEN_DERIVATIVE_ROW_COUNT_MISMATCH")

    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))
    base = panel[["ticker", "date", "close", "high", "low"]].copy()
    base["session_index"] = base["date"].map(date_to_index)
    if base["session_index"].isna().any():
        raise RuntimeError("PANEL_DATE_OUTSIDE_CALENDAR")
    base["session_index"] = base["session_index"].astype(int)

    right = derivative[["ticker", "date", "open"]].rename(columns={"open": "derivative_open"})
    base = base.merge(right, on=["ticker", "date"], how="left", validate="one_to_one")
    overlay_view = overlay[["ticker", "date", "recovered_open"]].copy()
    base = base.merge(overlay_view, on=["ticker", "date"], how="left", validate="one_to_one")

    derivative_open = pd.to_numeric(base["derivative_open"], errors="coerce").astype(float)
    recovered_open = pd.to_numeric(base["recovered_open"], errors="coerce").astype(float)
    derivative_valid = np.isfinite(derivative_open) & derivative_open.gt(0.0)
    recovered_valid = np.isfinite(recovered_open) & recovered_open.gt(0.0)
    both = derivative_valid & recovered_valid
    if both.any():
        if not np.allclose(
            derivative_open[both].to_numpy(dtype=float),
            recovered_open[both].to_numpy(dtype=float),
            rtol=0.0,
            atol=1e-9,
        ):
            raise RuntimeError("DERIVATIVE_OVERLAY_OPEN_CONFLICT")
    accepted_open = derivative_open.where(derivative_valid, recovered_open)
    open_admitted = np.isfinite(accepted_open) & accepted_open.gt(0.0)

    close = pd.to_numeric(base["close"], errors="coerce").astype(float)
    close_admitted = np.isfinite(close) & close.gt(0.0)

    anchors = anchors.copy()
    anchors["market"] = anchors["market"].astype(str).str.upper()
    anchors["state"] = anchors["state"].astype(str).str.upper()
    intervals = intervals.copy()
    intervals["market"] = intervals["market"].astype(str).str.upper()
    intervals["state"] = intervals["state"].astype(str).str.upper()
    states, conflicts = pit_support.state_map_from_inputs(anchors, intervals, calendar)
    market_state = [
        states.get((ticker, int(index)), "UNKNOWN")
        for ticker, index in base[["ticker", "session_index"]].itertuples(index=False)
    ]

    price = pd.DataFrame(
        {
            "ticker": base["ticker"],
            "date": base["date"],
            "market_state": market_state,
            "accepted_open": accepted_open,
            "open_admitted": open_admitted,
            "close": close,
            "close_admitted": close_admitted,
        }
    )
    stats = {
        "rows": int(len(price)),
        "derivative_open_admitted": int(derivative_valid.sum()),
        "overlay_open_admitted": int(recovered_valid.sum()),
        "overlay_incremental": int((recovered_valid & ~derivative_valid).sum()),
        "final_open_admitted": int(open_admitted.sum()),
        "close_admitted": int(close_admitted.sum()),
        "state_conflicts": int(conflicts),
    }
    return price, stats


def continuity_evidence_from_parent(
    continuity: pd.DataFrame,
    *,
    continuity_sha256: str,
    parent_manifest_sha256: str,
) -> pd.DataFrame:
    required = {"ticker", "signal_date", "horizon", "continuity_status"}
    missing = required - set(continuity.columns)
    if missing:
        raise RuntimeError(f"PARENT_CONTINUITY_MISSING_COLUMNS:{sorted(missing)}")
    out = continuity[["ticker", "signal_date", "horizon", "continuity_status"]].copy()
    out["policy_id"] = "V4_3_CA_IDX_COMBINED_REPLAY_FROZEN"
    out["evidence_id"] = "parent_manifest:" + parent_manifest_sha256
    out["evidence_sha256"] = continuity_sha256
    return out


def prepare_model_frame(
    features: pd.DataFrame,
    combined: pd.DataFrame,
    price_evidence: pd.DataFrame,
) -> pd.DataFrame:
    wanted = [
        "ticker",
        "date",
        "session_index",
        "high",
        "low",
        "close",
        *V4_CONTROL_FEATURE_COLUMNS,
    ]
    missing = set(wanted) - set(features.columns)
    if missing:
        raise RuntimeError(f"FEATURE_TABLE_MISSING_COLUMNS:{sorted(missing)}")
    source = features[wanted].copy()
    identity = combined[["ticker", "date", "session_index"]].copy()
    merged = identity.merge(
        source,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
        suffixes=("_parent", "_feature"),
    )
    if merged[["high", "low", "close"]].isna().any().any():
        raise RuntimeError("PARENT_DECISION_IDENTITY_MISSING_FEATURE_HLC")
    if not (merged["session_index_parent"].astype(int) == merged["session_index_feature"].astype(int)).all():
        raise RuntimeError("FEATURE_SESSION_INDEX_MISMATCH")
    merged = merged.rename(columns={"session_index_parent": "session_index"}).drop(
        columns=["session_index_feature"]
    )

    geometry = build_geometry_from_accepted_open(
        merged[["ticker", "date", "high", "low", "close"]],
        price_evidence,
    )
    geometry_view = geometry[["ticker", "date", *SESSION_GEOMETRY_FEATURE_COLUMNS]].copy()
    merged = merged.merge(
        geometry_view,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    if len(merged) != len(combined):
        raise RuntimeError("MODEL_FRAME_ROW_COUNT_CHANGED")
    if merged.duplicated(["ticker", "date"]).any():
        raise RuntimeError("MODEL_FRAME_DUPLICATE_IDENTITY")
    return merged.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def assert_target_support_parity(target: pd.DataFrame, combined: pd.DataFrame) -> dict[str, int]:
    compare = combined[
        [
            "ticker",
            "date",
            "h5_full_target_support",
            "h10_full_target_support",
            "consensus_full_target_support",
        ]
    ].merge(
        target[
            [
                "ticker",
                "date",
                "target_state_h5",
                "target_state_h10",
                "target_state_consensus",
            ]
        ],
        on=["ticker", "date"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not compare["_merge"].eq("both").all():
        raise RuntimeError("TARGET_PARENT_IDENTITY_MISMATCH")
    expected_h5 = compare["h5_full_target_support"].astype(bool)
    expected_h10 = compare["h10_full_target_support"].astype(bool)
    expected_consensus = compare["consensus_full_target_support"].astype(bool)
    actual_h5 = compare["target_state_h5"].eq(TARGET_H5_AVAILABLE)
    actual_h10 = compare["target_state_h10"].eq(TARGET_H10_AVAILABLE)
    actual_consensus = compare["target_state_consensus"].eq(TARGET_BOTH_AVAILABLE)
    mismatches = {
        "h5": int((expected_h5 != actual_h5).sum()),
        "h10": int((expected_h10 != actual_h10).sum()),
        "consensus": int((expected_consensus != actual_consensus).sum()),
    }
    if any(mismatches.values()):
        raise RuntimeError(f"TARGET_SUPPORT_PARITY_FAILED:{mismatches}")
    return mismatches


def training_frame_for(
    model_frame: pd.DataFrame,
    target_ledger: pd.DataFrame,
    training_dates: pd.DataFrame,
    *,
    fold: int,
    head: str,
) -> tuple[pd.DataFrame, str]:
    if head == "H5":
        state_column = "target_state_h5"
        available_state = TARGET_H5_AVAILABLE
        target_column = "target_rank_h5"
    elif head == "H10":
        state_column = "target_state_h10"
        available_state = TARGET_H10_AVAILABLE
        target_column = "target_rank_h10"
    else:
        raise ValueError(f"UNSUPPORTED_TRAINING_HEAD:{head}")

    date_set = set(
        training_dates.loc[
            (training_dates["fold"].astype(int) == int(fold))
            & training_dates["head"].astype(str).eq(head),
            "date",
        ]
    )
    if not date_set:
        raise RuntimeError(f"EMPTY_TRAINING_DATE_SET:F{fold}:{head}")
    target_rows = target_ledger[
        target_ledger["date"].isin(date_set)
        & target_ledger[state_column].eq(available_state)
    ][["ticker", "date", target_column]].copy()
    frame = target_rows.merge(
        model_frame,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    if frame.empty:
        raise RuntimeError(f"EMPTY_TRAINING_ROWS:F{fold}:{head}")
    if frame[target_column].isna().any():
        raise RuntimeError(f"TRAINING_TARGET_MISSING:F{fold}:{head}")
    return frame, target_column


def run_models(
    model_frame: pd.DataFrame,
    target_ledger: pd.DataFrame,
    training_dates: pd.DataFrame,
    folds: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    scored_parts: dict[str, list[pd.DataFrame]] = defaultdict(list)
    fit_rows: list[dict[str, object]] = []

    for mode in (CONTROL, CHALLENGER):
        for fold in range(1, 7):
            val_dates = set(folds.loc[folds["fold"].astype(int).eq(fold), "date"])
            scoring = model_frame[model_frame["date"].isin(val_dates)].copy()
            if scoring.empty or scoring["date"].nunique() != 100:
                raise RuntimeError(f"VALIDATION_SCORING_DOMAIN_CHANGED:{mode}:F{fold}")

            head_scores: dict[str, pd.DataFrame] = {}
            for head in ("H5", "H10"):
                train, target_column = training_frame_for(
                    model_frame,
                    target_ledger,
                    training_dates,
                    fold=fold,
                    head=head,
                )
                model = fit_v4_head(train, target_column=target_column, mode=mode)
                raw_col = f"raw_{head.lower()}"
                alpha_col = f"alpha_{head.lower()}"
                scored = score_v4_head(
                    model,
                    scoring,
                    mode=mode,
                    raw_score_column=raw_col,
                    alpha_column=alpha_col,
                )
                head_scores[head] = scored[["ticker", "date", raw_col, alpha_col]].copy()
                fit_rows.append(
                    {
                        "mode": mode,
                        "fold": fold,
                        "head": head,
                        "training_dates": int(train["date"].nunique()),
                        "training_rows": int(len(train)),
                        "validation_dates": int(scoring["date"].nunique()),
                        "validation_rows": int(len(scoring)),
                    }
                )

            consensus = attach_consensus_alpha(head_scores["H5"], head_scores["H10"])
            merged = head_scores["H5"].merge(
                head_scores["H10"], on=["ticker", "date"], how="inner", validate="one_to_one"
            ).merge(
                consensus[["ticker", "date", "alpha_consensus"]],
                on=["ticker", "date"],
                how="inner",
                validate="one_to_one",
            )
            merged["fold"] = fold
            merged["mode"] = mode
            scored_parts[mode].append(merged)

    outputs = {
        mode: pd.concat(parts, ignore_index=True).sort_values(
            ["fold", "date", "ticker"], kind="mergesort"
        ).reset_index(drop=True)
        for mode, parts in scored_parts.items()
    }
    for mode, frame in outputs.items():
        if frame["date"].nunique() != 600:
            raise RuntimeError(f"SCORED_VALIDATION_DATE_COUNT_CHANGED:{mode}:{frame['date'].nunique()}")
        if frame.duplicated(["ticker", "date"]).any():
            raise RuntimeError(f"SCORED_DUPLICATE_IDENTITY:{mode}")
    return outputs, pd.DataFrame(fit_rows)


def evaluate_models(
    scores: dict[str, pd.DataFrame],
    target_ledger: pd.DataFrame,
    folds: pd.DataFrame,
    prereg: dict[str, Any],
) -> tuple[
    dict[str, dict[str, pd.DataFrame]],
    dict[str, dict[str, dict[str, Any]]],
    dict[str, pd.DataFrame],
    dict[str, Any],
]:
    fold_metrics: dict[str, dict[str, pd.DataFrame]] = defaultdict(dict)
    summaries: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    for mode in (CONTROL, CHALLENGER):
        for head in ("H5", "H10", "CONSENSUS"):
            metrics = evaluate_head_by_date_ca80(scores[mode], target_ledger, head=head)
            attached = attach_folds(metrics, folds)
            fold_summary, aggregate = summarize_fold_metrics(attached)
            bootstrap_ci = None
            if head == "CONSENSUS":
                bootstrap_ci = percentile_ci(fold_stratified_block_bootstrap_mean(attached))
            gates = evaluate_absolute_viability_gates(
                head=head,
                aggregate=aggregate,
                preregistration=prereg,
                bootstrap_ci=bootstrap_ci,
            )
            fold_metrics[mode][head] = attached
            summaries[mode][head] = {
                "fold_summary": fold_summary.to_dict("records"),
                "aggregate": aggregate,
                "bootstrap_95pct_mean_daily_ic": bootstrap_ci,
                "absolute_gates": gates,
            }

    paired_tables: dict[str, pd.DataFrame] = {}
    paired_summary: dict[str, Any] = {}
    for head in ("H5", "H10", "CONSENSUS"):
        paired = paired_date_delta(
            fold_metrics[CHALLENGER][head],
            fold_metrics[CONTROL][head],
        )
        fold_summary, aggregate = summarize_paired_deltas(paired)
        paired_tables[head] = paired
        paired_summary[head] = {
            "fold_summary": fold_summary.to_dict("records"),
            "aggregate": aggregate,
        }

    consensus_delta_ci = percentile_ci(
        fold_stratified_block_bootstrap_mean(
            paired_tables["CONSENSUS"],
            value_column="delta_daily_ic",
        )
    )
    control_absolute = bool(
        all(summaries[CONTROL][head]["absolute_gates"]["pass"] for head in ("H5", "H10", "CONSENSUS"))
    )
    challenger_absolute = bool(
        all(summaries[CHALLENGER][head]["absolute_gates"]["pass"] for head in ("H5", "H10", "CONSENSUS"))
    )
    promotion = evaluate_incremental_promotion_gates(
        h5_delta=paired_summary["H5"]["aggregate"],
        h10_delta=paired_summary["H10"]["aggregate"],
        consensus_delta=paired_summary["CONSENSUS"]["aggregate"],
        consensus_bootstrap_delta_ci=consensus_delta_ci,
        challenger_absolute_pass=challenger_absolute,
        preregistration=prereg,
    )
    if challenger_absolute and promotion["pass"]:
        decision = "CHALLENGER_PROMOTED_FOR_FRESH_PROSPECTIVE_CONFIRMATION"
        verdict = "V4_3R_CHALLENGER_PROMOTED_FOR_FRESH_PROSPECTIVE_CONFIRMATION"
    elif control_absolute:
        decision = "CONTROL_RETAINED"
        verdict = "V4_3R_CONTROL_RETAINED"
    else:
        decision = "V4_GENERATION_NO_SURVIVOR"
        verdict = "V4_3R_GENERATION_NO_SURVIVOR"

    decision_payload = {
        "verdict": verdict,
        "preregistered_decision": decision,
        "control_absolute_pass": control_absolute,
        "challenger_absolute_pass": challenger_absolute,
        "challenger_incremental_promotion": promotion,
        "consensus_bootstrap_95pct_mean_daily_ic_delta": consensus_delta_ci,
    }
    return fold_metrics, summaries, paired_tables, decision_payload


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config
    if output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{output_dir}")
    if git_output(repo_root, "status", "--porcelain"):
        raise RuntimeError("GIT_WORKTREE_NOT_CLEAN")

    cfg = read_json(config_path, "CONFIG")
    if cfg.get("schema_version") != "ranking_v4_3r_historical_execution_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if cfg.get("generation_id") != "V4_3R_CA80":
        raise RuntimeError("CONFIG_GENERATION_INVALID")
    if float(cfg.get("evaluation_date_target_coverage_gate", -1.0)) != V4_3R_DATE_TARGET_COVERAGE_GATE:
        raise RuntimeError("CONFIG_CA80_EVALUATION_GATE_CHANGED")
    if cfg.get("one_shot") is not True or cfg.get("protected_forward_access_authorized") is not False:
        raise RuntimeError("CONFIG_ONE_SHOT_OR_PROTECTED_BOUNDARY_CHANGED")

    scientific_blobs = verify_git_blobs(repo_root, cfg["scientific_git_blobs"])
    runtime = verify_runtime(repo_root, cfg)
    freeze = verify_execution_freeze(args.execution_freeze_root.resolve(), cfg)
    training_dates, prefit_hashes = verify_prefit(args.prefit_root.resolve(), cfg)
    combined, continuity, parent_hashes = verify_parent_combined(
        args.parent_combined_replay_root.resolve(), cfg
    )
    paths, market_hashes = load_frozen_market_inputs(args, cfg)
    folds, folds_sha = load_validation_folds(repo_root, cfg)

    calendar = pd.read_csv(paths["calendar"])
    calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce").dt.normalize()
    if calendar["date"].isna().any() or calendar["date"].duplicated().any():
        raise RuntimeError("OFFICIAL_CALENDAR_INVALID")
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)

    panel = normalize_identity(pd.read_parquet(paths["panel"]))
    derivative = pd.read_parquet(paths["open_derivative_panel"])
    overlay = pd.read_parquet(paths["overlay_parquet"])
    anchors = pd.read_csv(paths["anchors"])
    intervals = pd.read_csv(paths["intervals"])
    security_master = pd.read_csv(paths["security_master"])

    features, pit_diagnostics = build_v4_control_feature_table(
        panel,
        calendar["date"],
        security_master,
    )
    price_evidence, price_stats = build_price_evidence(
        panel,
        calendar,
        derivative,
        overlay,
        anchors,
        intervals,
    )
    model_frame = prepare_model_frame(features, combined, price_evidence)
    continuity_evidence = continuity_evidence_from_parent(
        continuity,
        continuity_sha256=parent_hashes["continuity"],
        parent_manifest_sha256=parent_hashes["manifest"],
    )

    prereg = json.loads(git_bytes(repo_root, cfg["inherited_preregistration"]["path"]).decode("utf-8"))

    # FIRST HISTORICAL TARGET ACCESS BOUNDARY.  From this point onward the
    # generation is outcome-open and may not be scientifically modified/rescued.
    output_dir.mkdir(parents=True)
    access_marker = {
        "schema_version": "ranking_v4_3r_historical_access_boundary_v1",
        "generation_id": "V4_3R_CA80",
        "status": "HISTORICAL_TARGET_ACCESS_COMMENCED",
        "protected_forward_accessed": False,
        "provider_calls": False,
        "execution_freeze_manifest_sha256": cfg["execution_freeze"]["manifest_sha256"],
        "git_head": git_output(repo_root, "rev-parse", "HEAD"),
    }
    (output_dir / "HISTORICAL_ACCESS_BOUNDARY.json").write_text(
        json.dumps(access_marker, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    target_ledger = materialize_v4_target_ledger(
        combined[["ticker", "date"]],
        calendar["date"],
        price_evidence,
        continuity_evidence,
    )
    parity = assert_target_support_parity(target_ledger, combined)

    scores, fit_log = run_models(model_frame, target_ledger, training_dates, folds)
    fold_metrics, model_summaries, paired_tables, decision = evaluate_models(
        scores,
        target_ledger,
        folds,
        prereg,
    )

    target_path = output_dir / "v4_3r_target_ledger.parquet"
    fit_path = output_dir / "v4_3r_fit_log.csv"
    target_ledger.to_parquet(target_path, index=False)
    fit_log.to_csv(fit_path, index=False, lineterminator="\n")

    output_paths: dict[str, Path] = {
        "access_boundary": output_dir / "HISTORICAL_ACCESS_BOUNDARY.json",
        "target_ledger": target_path,
        "fit_log": fit_path,
    }
    for mode in (CONTROL, CHALLENGER):
        path = output_dir / f"v4_3r_{mode.lower()}_validation_scores.parquet"
        scores[mode].to_parquet(path, index=False)
        output_paths[f"scores_{mode.lower()}"] = path
        for head in ("H5", "H10", "CONSENSUS"):
            metric_path = output_dir / f"v4_3r_{mode.lower()}_{head.lower()}_date_metrics.csv"
            fold_metrics[mode][head].to_csv(metric_path, index=False, lineterminator="\n")
            output_paths[f"metrics_{mode.lower()}_{head.lower()}"] = metric_path
    for head, frame in paired_tables.items():
        path = output_dir / f"v4_3r_paired_{head.lower()}_date_deltas.csv"
        frame.to_csv(path, index=False, lineterminator="\n")
        output_paths[f"paired_{head.lower()}"] = path

    summary = {
        "schema_version": "ranking_v4_3r_historical_one_shot_result_v1",
        "generation_id": "V4_3R_CA80",
        "status": decision["verdict"],
        "historical_development_only": True,
        "historical_target_loaded": True,
        "model_fit": True,
        "prediction_generated": True,
        "performance_computed": True,
        "protected_forward_accessed": False,
        "provider_calls": False,
        "support_gate": 0.80,
        "evaluation_date_target_coverage_gate": 0.80,
        "v4_3_reference_gate": 0.90,
        "support_distribution_disclosure": {
            "below_0.80": 0,
            "0.80_to_below_0.90": 541,
            "at_least_0.90": 59,
        },
        "target_support_parity_mismatches": parity,
        "target_rows": int(len(target_ledger)),
        "target_dates": int(target_ledger["date"].nunique()),
        "target_tickers": int(target_ledger["ticker"].nunique()),
        "fit_count": int(len(fit_log)),
        "fit_log": fit_log.to_dict("records"),
        "price_evidence": price_stats,
        "pit_diagnostics": pit_diagnostics.__dict__,
        "model_summaries": model_summaries,
        "decision": decision,
        "fresh_confirmation_required": True,
        "post_result_rule": cfg["post_result_rule"],
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(json_safe(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_paths["summary"] = summary_path

    output_hashes = {name: sha256_file(path) for name, path in output_paths.items()}
    manifest = {
        "schema_version": "ranking_v4_3r_historical_one_shot_manifest_v1",
        "generation_id": "V4_3R_CA80",
        "status": decision["verdict"],
        "one_shot": True,
        "historical_target_loaded": True,
        "model_fit": True,
        "prediction_generated": True,
        "performance_computed": True,
        "protected_forward_accessed": False,
        "provider_calls": False,
        "git": {
            "head": git_output(repo_root, "rev-parse", "HEAD"),
            "branch": git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
            "worktree_clean_before_run": True,
            "runner_blob": git_output(repo_root, "rev-parse", f"HEAD:{SELF_PATH}"),
        },
        "runtime": runtime,
        "scientific_git_blobs": scientific_blobs,
        "immutable_inputs": {
            "execution_freeze_manifest": cfg["execution_freeze"]["manifest_sha256"],
            "prefit": prefit_hashes,
            "parent_combined_replay": parent_hashes,
            "market_inputs": market_hashes,
            "validation_folds": folds_sha,
        },
        "changed_from_v4_3": {
            "prefit_date_full_target_support_gate": {"v4_3": 0.90, "v4_3r": 0.80},
            "evaluation_date_target_coverage_gate": {"v4_3": 0.90, "v4_3r": 0.80},
        },
        "output_hashes": output_hashes,
        "decision": decision,
        "protected_forward_access_authorized": False,
        "post_result_rule": cfg["post_result_rule"],
    }
    manifest_path = output_dir / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(json_safe(manifest), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": decision["verdict"],
                "preregistered_decision": decision["preregistered_decision"],
                "historical_target_loaded": True,
                "model_fit": True,
                "prediction_generated": True,
                "performance_computed": True,
                "protected_forward_accessed": False,
                "provider_calls": False,
                "fit_count": int(len(fit_log)),
                "target_support_parity_mismatches": parity,
                "control_absolute_pass": decision["control_absolute_pass"],
                "challenger_absolute_pass": decision["challenger_absolute_pass"],
                "challenger_incremental_pass": decision["challenger_incremental_promotion"]["pass"],
                "summary": str(summary_path),
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "next": "STOP_FOR_INDEPENDENT_REVIEW_NO_RESCUE_OR_RETUNE",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
