"""Materialize the final V4-X clean-input bundle after identity acceptance.

The runner is intentionally unusable without an independently accepted identity
package. It references Stage-A panel bytes rather than rewriting them and never
fits/scores models or accesses numeric targets/outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.v4_x_clean_data_stage_b import (  # noqa: E402
    ACTION_APPLY,
    MATERIALIZATION_POLICY,
    materialize_final_security_master,
    validate_acceptance_contract,
    validate_stage_c_manifest,
)

PROJECT = Path(r"D:\Documents\Project")
DATA_GATE = PROJECT / "idx-trade-data-gate-20260808v"
DEFAULT_STAGE_A_ROOT = DATA_GATE / "v4_x_clean_data_consolidation_v1_20260820"
DEFAULT_OUTPUT = DATA_GATE / "v4_x_clean_data_consolidation_v1_stage_b_20260820"
DEFAULT_CONFIG = REPO_ROOT / "config" / "v4_x_clean_data_stage_b_interface_v1.json"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label}_SHA_MISMATCH:{actual}!={expected}:{path}")
    return actual


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_INVALID:{path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--stage-a-root", type=Path, default=DEFAULT_STAGE_A_ROOT)
    parser.add_argument("--frozen-security-master", type=Path, required=True)
    parser.add_argument("--identity-acceptance", type=Path, required=True)
    parser.add_argument("--stage-c-manifest", type=Path, required=True)
    parser.add_argument("--identity-overlay", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    config_path = args.config.resolve()
    cfg = read_json(config_path, "STAGE_B_CONFIG")
    if cfg.get("status") != "STAGE_B_INTERFACE_FROZEN_WAITING_FOR_IDENTITY_ACCEPTANCE":
        raise RuntimeError("STAGE_B_CONFIG_STATUS_CHANGED")
    if cfg.get("materialization_policy") != MATERIALIZATION_POLICY:
        raise RuntimeError("STAGE_B_MATERIALIZATION_POLICY_CHANGED")
    if cfg.get("stage_b_does_not_rewrite_stage_a_panel") is not True:
        raise RuntimeError("STAGE_B_PANEL_REFERENCE_CONTRACT_CHANGED")
    if cfg.get("model_refit_authorized") is not False:
        raise RuntimeError("STAGE_B_CONFIG_REFIT_GUARD_CHANGED")
    config_guardrails = cfg.get("guardrails") or {}
    if not config_guardrails or any(value is not False for value in config_guardrails.values()):
        raise RuntimeError("STAGE_B_CONFIG_GUARDRAIL_CHANGED")

    stage_a_cfg = cfg.get("stage_a") or {}
    stage_a_root = args.stage_a_root.resolve()
    stage_a_manifest_path = stage_a_root / "MANIFEST.json"
    require_sha(stage_a_manifest_path, str(stage_a_cfg.get("manifest_sha256") or ""), "STAGE_A_MANIFEST")
    stage_a_manifest = read_json(stage_a_manifest_path, "STAGE_A_MANIFEST")
    if stage_a_manifest.get("status") != stage_a_cfg.get("status"):
        raise RuntimeError("STAGE_A_STATUS_CHANGED")
    if stage_a_manifest.get("final_clean_input_authorized") is not False:
        raise RuntimeError("STAGE_A_FINAL_INPUT_GUARD_CHANGED")
    if stage_a_manifest.get("model_refit_authorized") is not False:
        raise RuntimeError("STAGE_A_REFIT_GUARD_CHANGED")

    output_hashes = stage_a_manifest.get("output_hashes") or {}
    expected_outputs = stage_a_cfg.get("output_hashes") or {}
    if output_hashes != expected_outputs:
        raise RuntimeError("STAGE_A_OUTPUT_HASH_SET_CHANGED")

    stage_a_files = {
        "clean_candidate_panel": stage_a_root / "model_safe_signal_research_panel_1260_stage_a_clean_candidate.parquet",
        "field_level_provenance_parquet": stage_a_root / "field_level_provenance_sidecar_v1.parquet",
        "field_level_provenance_csv": stage_a_root / "field_level_provenance_sidecar_v1.csv",
        "correction_ledger": stage_a_root / "clean_data_correction_ledger_v1.csv",
        "summary": stage_a_root / "summary.json",
    }
    for key, path in stage_a_files.items():
        require_sha(path, str(expected_outputs[key]), f"STAGE_A_{key.upper()}")

    frozen_master_path = args.frozen_security_master.resolve()
    require_sha(
        frozen_master_path,
        str(cfg.get("frozen_security_master_sha256") or ""),
        "FROZEN_SECURITY_MASTER",
    )

    acceptance_path = args.identity_acceptance.resolve()
    acceptance = read_json(acceptance_path, "IDENTITY_ACCEPTANCE")
    accepted = validate_acceptance_contract(acceptance)

    stage_c_manifest_path = args.stage_c_manifest.resolve()
    stage_c_manifest_sha = sha256_file(stage_c_manifest_path)
    if stage_c_manifest_sha != accepted["stage_c_manifest_sha256"]:
        raise RuntimeError("STAGE_C_MANIFEST_NOT_PINNED_BY_ACCEPTANCE")
    stage_c_manifest = read_json(stage_c_manifest_path, "STAGE_C_MANIFEST")
    validate_stage_c_manifest(stage_c_manifest, accepted_manifest_sha256=stage_c_manifest_sha)
    if stage_c_manifest.get("decision") != accepted["stage_c_decision"]:
        raise RuntimeError("STAGE_C_DECISION_NOT_PINNED_BY_ACCEPTANCE")

    overlay: pd.DataFrame | None = None
    overlay_sha: str | None = None
    if accepted["action"] == ACTION_APPLY:
        if args.identity_overlay is None:
            raise RuntimeError("APPLY_ACTION_REQUIRES_IDENTITY_OVERLAY_PATH")
        overlay_path = args.identity_overlay.resolve()
        overlay_sha = require_sha(
            overlay_path,
            str(accepted["identity_overlay_sha256"]),
            "IDENTITY_OVERLAY",
        )
        overlay = pd.read_csv(overlay_path, low_memory=False)
    elif args.identity_overlay is not None:
        raise RuntimeError("PRESERVE_ACTION_MUST_NOT_RECEIVE_IDENTITY_OVERLAY_PATH")

    frozen_master = pd.read_csv(frozen_master_path, low_memory=False)
    result = materialize_final_security_master(frozen_master, overlay, acceptance)

    output.mkdir(parents=True, exist_ok=True)
    final_master_path = output / "final_security_master_v1.csv"
    identity_ledger_path = output / "identity_correction_ledger_v1.csv"
    result.final_security_master.to_csv(final_master_path, index=False, date_format="%Y-%m-%d", lineterminator="\n")
    result.identity_ledger.to_csv(identity_ledger_path, index=False, date_format="%Y-%m-%d", lineterminator="\n")

    stage_a_inputs = stage_a_manifest.get("inputs") or {}
    summary = {
        "schema_version": "v4_x_clean_data_stage_b_v1",
        "status": "STAGE_B_CLEAN_INPUT_BUNDLE_MATERIALIZED_REFIT_NOT_AUTHORIZED",
        **result.summary,
        "stage_a_manifest_sha256": sha256_file(stage_a_manifest_path),
        "stage_a_referenced_outputs": {
            key: {"path": str(path), "sha256": sha256_file(path)}
            for key, path in stage_a_files.items()
        },
        "stage_a_frozen_inputs": stage_a_inputs,
        "frozen_security_master": {
            "path": str(frozen_master_path),
            "sha256": sha256_file(frozen_master_path),
        },
        "identity_acceptance": {
            "path": str(acceptance_path),
            "sha256": sha256_file(acceptance_path),
            "stage_c_manifest_sha256": stage_c_manifest_sha,
            "stage_c_decision": accepted["stage_c_decision"],
            "action": accepted["action"],
            "identity_overlay_sha256": overlay_sha,
        },
        "final_security_master": {
            "path": str(final_master_path),
            "sha256": sha256_file(final_master_path),
        },
        "identity_correction_ledger": {
            "path": str(identity_ledger_path),
            "sha256": sha256_file(identity_ledger_path),
        },
        "stage_a_panel_rewritten": False,
        "final_clean_input_bundle_materialized": True,
        "model_refit_authorized": False,
        "next": "INDEPENDENT_REVIEW_THEN_SEPARATELY_FREEZE_DETERMINISTIC_V2_V4_X_REPLAY; DO_NOT_REFIT_AUTOMATICALLY",
        "guardrails": config_guardrails,
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "v4_x_clean_data_stage_b_manifest_v1",
        "status": summary["status"],
        "materialization_policy": MATERIALIZATION_POLICY,
        "stage_a_manifest_sha256": summary["stage_a_manifest_sha256"],
        "stage_a_output_hashes": {
            key: value["sha256"] for key, value in summary["stage_a_referenced_outputs"].items()
        },
        "stage_a_input_hashes": stage_a_inputs,
        "frozen_security_master_sha256": summary["frozen_security_master"]["sha256"],
        "identity_acceptance_sha256": summary["identity_acceptance"]["sha256"],
        "stage_c_manifest_sha256": stage_c_manifest_sha,
        "stage_c_decision": accepted["stage_c_decision"],
        "clean_consolidation_action": accepted["action"],
        "identity_overlay_sha256": overlay_sha,
        "final_security_master_sha256": summary["final_security_master"]["sha256"],
        "identity_correction_ledger_sha256": summary["identity_correction_ledger"]["sha256"],
        "summary_sha256": sha256_file(summary_path),
        "stage_a_panel_rewritten": False,
        "final_clean_input_bundle_materialized": True,
        "model_refit_authorized": False,
        "guardrails": config_guardrails,
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": summary["status"],
                "action": accepted["action"],
                "stage_c_decision": accepted["stage_c_decision"],
                "final_security_master_rows": result.summary["final_security_master_rows"],
                "final_security_master_tickers": result.summary["final_security_master_tickers"],
                "identity_overlay_rows": result.summary["identity_overlay_rows"],
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "model_refit_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
