"""Frozen final historical refit for O2 full-three geometry."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import joblib
import pandas as pd
import sklearn

from .ohlcv_o1_research import (
    EXPECTED_ACCEPTED_OPEN_PANEL_SHA256,
    EXPECTED_ACCEPTED_OPEN_PROVENANCE_SHA256,
    EXPECTED_CALENDAR_SHA256,
    EXPECTED_COMMON_SUPPORT_ROWS,
    EXPECTED_PANEL_SHA256,
    EXPECTED_SECURITY_MASTER_SHA256,
    EXPECTED_TRAINING_MANIFEST_SHA256,
    EXPECTED_TRAINING_TABLE_SHA256,
    EXPECTED_V3_B_FEATURE_ORDER_SHA256,
    HGB_PARAMS,
    V3_B_FEATURE_COLUMNS,
    _stable_key_hash,
    _verify_file,
    feature_order_hash,
    load_common_support,
)
from .ohlcv_o2_geometry_research import (
    EXPECTED_COMMON_SUPPORT_KEY_SHA256,
    EXPECTED_O2_FEATURE_ORDER_SHA256,
    O2_FEATURE_COLUMNS,
    _attach_geometry,
    o2_hgb_pipeline,
)


CANDIDATE_ID = "O2-GEOMETRY-FULL3-V1-CANDIDATE-001"
RUNTIME_STATUS = "O2_FULL_3_FINAL_REFIT_COMPLETE_PENDING_INDEPENDENT_REVIEW"
EXPECTED_O2_ARTIFACT_MANIFEST_SHA256 = "cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a"
EXPECTED_ROBUSTNESS_MANIFEST_SHA256 = "ba685239991ad820c45955c2116f56dd00a077b54a8d052c49adb2f97be438bd"
EXPECTED_MINIMALITY_MANIFEST_SHA256 = "919e35bb8d2fe68588db331e3de25f6c2a490c2727aea9f68e1179c0bcbe5183"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_artifact_bundle(
    path: Path,
    expected_sha256: str,
    expected_schema: str,
    expected_status: str | None = None,
) -> dict[str, object]:
    manifest_sha = _verify_file(path, expected_sha256, "accepted artifact manifest")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != expected_schema:
        raise RuntimeError(f"artifact manifest schema mismatch: {path}")
    if expected_status is not None and manifest.get("status") != expected_status:
        raise RuntimeError(f"artifact manifest status mismatch: {path}")
    artifact_hashes = manifest.get("artifact_sha256", {})
    if not isinstance(artifact_hashes, dict) or not artifact_hashes:
        raise RuntimeError(f"artifact manifest has no listed artifacts: {path}")
    for name, expected in sorted(artifact_hashes.items()):
        _verify_file(path.parent / str(name), str(expected), f"accepted artifact {name}")
    return {
        "path": str(path),
        "sha256": manifest_sha,
        "schema": expected_schema,
        "status": manifest.get("status"),
        "artifact_count": int(len(artifact_hashes)),
        "artifact_hashes_verified": True,
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str), encoding="utf-8")


def run_final_refit(
    *,
    coverage_path: Path,
    training_table_path: Path,
    training_manifest_path: Path,
    o1_artifact_manifest_path: Path,
    o2_artifact_manifest_path: Path,
    robustness_artifact_manifest_path: Path,
    minimality_artifact_manifest_path: Path,
    output_dir: Path,
    immutable_panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    accepted_open_panel_path: Path,
    accepted_open_provenance_path: Path,
) -> dict[str, object]:
    if (output_dir / "artifact_manifest.json").exists():
        raise RuntimeError(f"refusing to overwrite existing final-refit runtime: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    input_contract: dict[str, object] = {}
    for label, path, expected in (
        ("immutable_panel", immutable_panel_path, EXPECTED_PANEL_SHA256),
        ("official_calendar", calendar_path, EXPECTED_CALENDAR_SHA256),
        ("security_master", security_master_path, EXPECTED_SECURITY_MASTER_SHA256),
        ("accepted_open_panel", accepted_open_panel_path, EXPECTED_ACCEPTED_OPEN_PANEL_SHA256),
        ("accepted_open_provenance", accepted_open_provenance_path, EXPECTED_ACCEPTED_OPEN_PROVENANCE_SHA256),
        ("v3_b_training_table", training_table_path, EXPECTED_TRAINING_TABLE_SHA256),
        ("v3_b_training_manifest", training_manifest_path, EXPECTED_TRAINING_MANIFEST_SHA256),
        ("o1_artifact_manifest", o1_artifact_manifest_path, "2441f9fcadc9a496ed5d15306bb7bbcb87c9978ecdc26033f5bd7619c2d08714"),
    ):
        input_contract[f"{label}_path"] = str(path)
        input_contract[f"{label}_sha256"] = _verify_file(path, expected, label)

    input_contract["accepted_o2_artifact_manifest"] = _verify_artifact_bundle(
        o2_artifact_manifest_path,
        EXPECTED_O2_ARTIFACT_MANIFEST_SHA256,
        "idx-trade/ohlcv-o2-geometry-research-artifacts-v1",
        "O2_SURVIVOR",
    )
    input_contract["accepted_robustness_audit_manifest"] = _verify_artifact_bundle(
        robustness_artifact_manifest_path,
        EXPECTED_ROBUSTNESS_MANIFEST_SHA256,
        "idx-trade/ohlcv-o2-robustness-audit-v1",
        "O2_ROBUSTNESS_PASS_MINIMALITY_AUDIT_RECOMMENDED",
    )
    input_contract["accepted_minimality_manifest"] = _verify_artifact_bundle(
        minimality_artifact_manifest_path,
        EXPECTED_MINIMALITY_MANIFEST_SHA256,
        "idx-trade/ohlcv-o2-minimality-artifacts-v1",
        "O2_MINIMALITY_EVIDENCE_COMPLETE",
    )

    support, support_contract = load_common_support(
        coverage_path=coverage_path,
        training_table_path=training_table_path,
        training_manifest_path=training_manifest_path,
    )
    if support_contract["common_support_key_sha256"] != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("final refit common-support key differs from accepted O2 population")
    support, formula_errors = _attach_geometry(support, coverage_path)
    if len(support) != EXPECTED_COMMON_SUPPORT_ROWS:
        raise RuntimeError(f"final refit population changed: {len(support)}")
    if _stable_key_hash(support) != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("final refit row identity hash mismatch")
    if support["date"].max() > pd.Timestamp("2026-07-31"):
        raise RuntimeError("final refit contains post-boundary rows")

    input_contract.update(support_contract)
    input_contract.update(
        {
            "candidate_id": CANDIDATE_ID,
            "common_support_rows": int(len(support)),
            "common_support_tickers": int(support["ticker"].nunique()),
            "common_support_key_sha256": _stable_key_hash(support),
            "v3_b_feature_columns": list(V3_B_FEATURE_COLUMNS),
            "v3_b_feature_order_sha256": feature_order_hash(V3_B_FEATURE_COLUMNS),
            "o2_feature_columns": list(O2_FEATURE_COLUMNS),
            "o2_feature_order_sha256": feature_order_hash(O2_FEATURE_COLUMNS),
            "geometry_formula_max_abs_error": formula_errors,
            "hgb_parameters": HGB_PARAMS,
            "h10_labels": support_contract["h10_labels"],
            "historical_boundary": "2026-07-31",
            "fresh_forward_outcomes_accessed": False,
            "forward_outcome_access_marker_written": False,
            "provider_calls": False,
        }
    )
    if input_contract["v3_b_feature_order_sha256"] != EXPECTED_V3_B_FEATURE_ORDER_SHA256:
        raise RuntimeError("canonical V3-B feature-order hash mismatch")
    if input_contract["o2_feature_order_sha256"] != EXPECTED_O2_FEATURE_ORDER_SHA256:
        raise RuntimeError("accepted O2 feature-order hash mismatch")

    identity_frame = pd.DataFrame(
        {
            "ticker": support["ticker"],
            "date": support["date"].dt.strftime("%Y-%m-%d"),
            "signal_session_index": support["signal_session_index"],
        }
    ).sort_values(["ticker", "date"], kind="mergesort")
    identity_frame.to_csv(output_dir / "final_training_rows.csv", index=False)
    _write_json(output_dir / "feature_manifest.json", {
        "candidate_id": CANDIDATE_ID,
        "feature_columns": list(O2_FEATURE_COLUMNS),
        "feature_order_sha256": EXPECTED_O2_FEATURE_ORDER_SHA256,
        "v3_b_feature_order_sha256": EXPECTED_V3_B_FEATURE_ORDER_SHA256,
        "geometry_features": ["open_position", "open_to_high", "open_to_low"],
        "hgb_parameters": HGB_PARAMS,
    })
    _write_json(output_dir / "training_contract.json", input_contract)
    _write_json(output_dir / "environment_manifest.json", {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {
            "joblib": joblib.__version__,
            "numpy": __import__("numpy").__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
    })

    model = o2_hgb_pipeline(O2_FEATURE_COLUMNS)
    model.fit(support[list(O2_FEATURE_COLUMNS)], support["binary_target"].astype(int).to_numpy())
    model_path = output_dir / "o2_geometry_full3_final_model.joblib"
    joblib.dump(model, model_path)
    model_sha = sha256_file(model_path)

    model_manifest = {
        "candidate_id": CANDIDATE_ID,
        "model_path": str(model_path),
        "model_sha256": model_sha,
        "feature_order_sha256": EXPECTED_O2_FEATURE_ORDER_SHA256,
        "training_rows": int(len(support)),
        "training_tickers": int(support["ticker"].nunique()),
        "training_row_identity_sha256": _stable_key_hash(support),
        "h10_target_semantics": support_contract["h10_labels"],
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "canonical_v3b_overwritten": False,
        "independent_forward_validation_passed": False,
        "execution_grade_promoted": False,
    }
    _write_json(output_dir / "model_manifest.json", model_manifest)
    _write_json(output_dir / "forward_scoring_contract.json", {
        "signal_timestamp": "after session-t close",
        "geometry_availability": "session-t Open/High/Low only after session-t is complete",
        "eligibility": "canonical V3-B eligibility/universe plus valid causal Open geometry availability",
        "feature_order_sha256": EXPECTED_O2_FEATURE_ORDER_SHA256,
        "model_artifact_sha256": model_sha,
        "outcomes_required_for_scoring": False,
        "missing_or_invalid_geometry": "ticker/session is ineligible; no synthetic fill",
        "execution": "not executed in this lane",
    })

    summary = {
        "status": RUNTIME_STATUS,
        "candidate_id": CANDIDATE_ID,
        "common_support_rows": int(len(support)),
        "common_support_tickers": int(support["ticker"].nunique()),
        "common_support_key_sha256": _stable_key_hash(support),
        "feature_order_sha256": EXPECTED_O2_FEATURE_ORDER_SHA256,
        "model_sha256": model_sha,
        "training_runtime_seconds": float(time.perf_counter() - started),
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "canonical_v3b_overwritten": False,
        "independent_forward_validation_passed": False,
        "execution_grade_promoted": False,
        "provider_calls": False,
    }
    _write_json(output_dir / "runtime_summary.json", summary)

    artifact_hashes: dict[str, str] = {}
    for path in sorted(output_dir.iterdir()):
        if path.name != "artifact_manifest.json" and path.is_file():
            artifact_hashes[path.name] = sha256_file(path)
    artifact_manifest = {
        "schema": "idx-trade/ohlcv-o2-final-refit-artifacts-v1",
        "status": RUNTIME_STATUS,
        "artifact_sha256": artifact_hashes,
        "input_contract": input_contract,
        "model_manifest": model_manifest,
        "summary": summary,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {"joblib": joblib.__version__, "pandas": pd.__version__, "scikit_learn": sklearn.__version__},
        },
    }
    artifact_manifest_path = output_dir / "artifact_manifest.json"
    _write_json(artifact_manifest_path, artifact_manifest)
    return {
        **summary,
        "artifact_manifest_path": str(artifact_manifest_path),
        "artifact_manifest_sha256": sha256_file(artifact_manifest_path),
        "artifact_count": len(artifact_hashes),
        "final_training_rows_sha256": artifact_hashes["final_training_rows.csv"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "coverage_path",
        "training_table_path",
        "training_manifest_path",
        "o1_artifact_manifest_path",
        "o2_artifact_manifest_path",
        "robustness_artifact_manifest_path",
        "minimality_artifact_manifest_path",
        "output_dir",
        "immutable_panel_path",
        "calendar_path",
        "security_master_path",
        "accepted_open_panel_path",
        "accepted_open_provenance_path",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_final_refit(**vars(args))
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
