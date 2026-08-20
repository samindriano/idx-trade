"""Execution wrapper for the clean V4-X1 Phase-B final refit.

The clean primary feature frame may contain observations after the frozen V4-3R
historical boundary. Phase B is authorized to access numeric historical targets
only for the frozen historical training corpus. This wrapper therefore filters
decision rows *before* target materialization to the exact frozen validation
boundary, then delegates to the prepared four-fit core runner.

It never scores a model, evaluates historical performance, accesses protected or
fresh-forward outcomes, calls providers/network, or mutates the forward counter.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_RUNNER = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_b_final_refit.py"
EXPECTED_CORE_BLOB = "d18e23375076ca56d4a236217a2481c6f1c62f98"
VALIDATION_FOLDS_PATH = "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_validation_folds.csv"
EXPECTED_VALIDATION_FOLDS_SHA256 = "91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915"
SELF_PATH = "scripts/run_v4_x1_clean_phase_b_final_refit_freeze.py"

_TARGET_BOUNDARY_STATS: dict[str, Any] | None = None


def _git_output(*args: str, text: bool = True):
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return completed.stdout.strip() if text else completed.stdout


def _git_blob(path: str) -> str:
    return _git_output("rev-parse", f"HEAD:{path}")


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_core():
    spec = importlib.util.spec_from_file_location("v4_x1_clean_phase_b_core_frozen", CORE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_FREEZE_CORE_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_validation_boundary() -> tuple[pd.DataFrame, int, str]:
    raw = _git_output("show", f"HEAD:{VALIDATION_FOLDS_PATH}", text=False)
    sha = _sha256_bytes(raw)
    if sha != EXPECTED_VALIDATION_FOLDS_SHA256:
        raise RuntimeError(
            f"V4_X1_CLEAN_PHASE_B_VALIDATION_FOLDS_SHA_CHANGED:{sha}!={EXPECTED_VALIDATION_FOLDS_SHA256}"
        )
    folds = pd.read_csv(REPO_ROOT / VALIDATION_FOLDS_PATH)
    required = {"date", "session_index", "fold"}
    missing = required - set(folds.columns)
    if missing:
        raise RuntimeError(f"V4_X1_CLEAN_PHASE_B_VALIDATION_FOLDS_COLUMNS_MISSING:{sorted(missing)}")
    folds["date"] = pd.to_datetime(folds["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    folds["session_index"] = pd.to_numeric(folds["session_index"], errors="raise").astype(int)
    folds["fold"] = pd.to_numeric(folds["fold"], errors="raise").astype(int)
    if len(folds) != 600 or folds["date"].isna().any() or folds["date"].duplicated().any():
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_VALIDATION_FOLDS_INVALID")
    if set(folds["fold"]) != set(range(1, 7)):
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_VALIDATION_FOLD_IDS_CHANGED")
    if not all(int((folds["fold"] == fold).sum()) == 100 for fold in range(1, 7)):
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_VALIDATION_FOLD_SIZE_CHANGED")
    return folds, int(folds["session_index"].max()), sha


def _postprocess(output_dir: Path, *, wrapper_blob: str, boundary_stats: dict[str, Any]) -> str:
    boundary_path = output_dir / "CLEAN_PHASE_B_FINAL_REFIT_BOUNDARY.json"
    summary_path = output_dir / "summary.json"
    manifest_path = output_dir / "MANIFEST.json"
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for payload, label in ((boundary, "BOUNDARY"), (summary, "SUMMARY"), (manifest, "MANIFEST")):
        for key in (
            "historical_prediction_generated",
            "historical_performance_computed",
            "protected_forward_accessed",
            "fresh_forward_accessed",
            "provider_calls",
            "network_calls",
            "forward_counter_mutated",
        ):
            if payload.get(key) is not False:
                raise RuntimeError(f"V4_X1_CLEAN_PHASE_B_POSTPROCESS_SAFETY_CHANGED:{label}:{key}")
    if summary.get("model_scoring_performed") is not False or manifest.get("model_scoring_performed") is not False:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_POSTPROCESS_MODEL_SCORING_CHANGED")
    if int(summary.get("fit_count", -1)) != 4 or int(manifest.get("required_fit_count", -1)) != 4:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_POSTPROCESS_FIT_COUNT_CHANGED")

    wrapper_meta = {
        "policy_id": "FROZEN_HISTORICAL_TARGET_BOUNDARY_BEFORE_MATERIALIZATION_V1",
        "wrapper_git_blob": wrapper_blob,
        "core_runner_git_blob": EXPECTED_CORE_BLOB,
        **boundary_stats,
    }
    for payload in (boundary, summary, manifest):
        payload["frozen_target_boundary"] = wrapper_meta
        payload["fresh_forward_training_target_accessed"] = False
        payload["frozen_historical_end_session_index"] = int(boundary_stats["frozen_end_session_index"])
        payload["frozen_historical_end_date"] = str(boundary_stats["frozen_end_date"])

    boundary_path.write_text(json.dumps(boundary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest.setdefault("git", {})["execution_wrapper_blob"] = wrapper_blob
    manifest.setdefault("output_hashes", {})["boundary"] = _sha256_file(boundary_path)
    manifest.setdefault("output_hashes", {})["summary"] = _sha256_file(summary_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return _sha256_file(manifest_path)


def main() -> int:
    if _git_blob("scripts/run_v4_x1_clean_phase_b_final_refit.py") != EXPECTED_CORE_BLOB:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_CORE_RUNNER_CHANGED")

    folds, frozen_end_index, folds_sha = _load_validation_boundary()
    frozen_row = folds.loc[folds["session_index"].idxmax()]
    frozen_end_date = pd.Timestamp(frozen_row["date"]).strftime("%Y-%m-%d")

    core = _load_core()
    original_materialize = core.materialize_v4_target_ledger

    def frozen_materialize(decision_rows, official_sessions, price_evidence, continuity_evidence):
        global _TARGET_BOUNDARY_STATS
        sessions = pd.DatetimeIndex(pd.to_datetime(list(official_sessions), errors="coerce")).tz_localize(None).normalize()
        if sessions.isna().any() or len(sessions) == 0:
            raise RuntimeError("V4_X1_CLEAN_PHASE_B_OFFICIAL_SESSIONS_INVALID")
        date_to_index = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
        decision = decision_rows.copy()
        decision["date"] = pd.to_datetime(decision["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
        if decision["date"].isna().any():
            raise RuntimeError("V4_X1_CLEAN_PHASE_B_DECISION_DATE_INVALID")
        index = decision["date"].map(date_to_index)
        if index.isna().any():
            raise RuntimeError("V4_X1_CLEAN_PHASE_B_DECISION_OUTSIDE_CALENDAR")
        keep = index.astype(int).le(int(frozen_end_index))
        retained = decision.loc[keep].copy()
        dropped = decision.loc[~keep].copy()
        if retained.empty:
            raise RuntimeError("V4_X1_CLEAN_PHASE_B_FROZEN_TARGET_DOMAIN_EMPTY")
        if not dropped.empty and not pd.to_datetime(dropped["date"]).gt(pd.Timestamp(frozen_end_date)).all():
            raise RuntimeError("V4_X1_CLEAN_PHASE_B_TARGET_BOUNDARY_FILTER_INCONSISTENT")
        _TARGET_BOUNDARY_STATS = {
            "validation_folds_sha256": folds_sha,
            "frozen_end_session_index": int(frozen_end_index),
            "frozen_end_date": frozen_end_date,
            "decision_rows_before_boundary": int(len(decision)),
            "decision_rows_materialized": int(len(retained)),
            "decision_rows_excluded_post_freeze": int(len(dropped)),
            "post_freeze_numeric_target_accessed": False,
        }
        return original_materialize(retained, official_sessions, price_evidence, continuity_evidence)

    core.materialize_v4_target_ledger = frozen_materialize
    sys.argv = [sys.argv[0], *sys.argv[1:]]
    result = int(core.main())
    if result != 0:
        return result
    if _TARGET_BOUNDARY_STATS is None:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_TARGET_BOUNDARY_NOT_APPLIED")

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--output-dir", type=Path, required=True)
    known, _ = parser.parse_known_args(sys.argv[1:])
    output_dir = known.output_dir.resolve()
    wrapper_blob = _git_blob(SELF_PATH)
    final_sha = _postprocess(
        output_dir,
        wrapper_blob=wrapper_blob,
        boundary_stats=_TARGET_BOUNDARY_STATS,
    )
    manifest = json.loads((output_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "status": manifest.get("status"),
                "fit_count": manifest.get("required_fit_count"),
                "manifest": str(output_dir / "MANIFEST.json"),
                "manifest_sha256": final_sha,
                "frozen_target_boundary": _TARGET_BOUNDARY_STATS,
                "historical_prediction_generated": False,
                "historical_performance_computed": False,
                "model_scoring_performed": False,
                "protected_forward_accessed": False,
                "fresh_forward_accessed": False,
                "fresh_forward_training_target_accessed": False,
                "provider_calls": False,
                "network_calls": False,
                "forward_counter_mutated": False,
                "prospective_scoring_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
