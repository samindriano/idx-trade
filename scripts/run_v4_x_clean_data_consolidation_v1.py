"""Materialize V4-X clean-data consolidation Stage A offline and outcome-blind."""
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

from idx_trade.v4_x_clean_data_consolidation import consolidate_stage_a  # noqa: E402

PROJECT = Path(r"D:\Documents\Project")
DATA_GATE = PROJECT / "idx-trade-data-gate-20260808v"
RESEARCH_ROOT = DATA_GATE / "research_feasibility_1260_20260809"
DEFAULT_PANEL = RESEARCH_ROOT / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet"
DEFAULT_CALENDAR = RESEARCH_ROOT / "official_exchange_sessions_1260.csv"
DEFAULT_HLC_ROOT = DATA_GATE / "price_basis_remediation_v1_20260820"
DEFAULT_OPEN_ROOT = DATA_GATE / "price_basis_open_remediation_v1_20260820"
DEFAULT_INTEGRITY_ROOT = DATA_GATE / "frozen_panel_official_idx_integrity_audit_v1_20260820"
DEFAULT_VALUE_ROOT = DATA_GATE / "regular_market_value_basis_audit_v1_20260820"
DEFAULT_OUTPUT = DATA_GATE / "v4_x_clean_data_consolidation_v1_20260820"
DEFAULT_CONFIG = REPO_ROOT / "config" / "v4_x_clean_data_consolidation_v1.json"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require_sha(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label}_SHA_MISMATCH:{actual}!={expected}:{path}")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_EXPECTED:{path}")
    return value


def require_parent_output_hash(root: Path, manifest: dict[str, Any], key: str, filename: str, label: str) -> Path:
    hashes = manifest.get("output_hashes") or {}
    expected = str(hashes.get(key) or "")
    if not expected:
        raise RuntimeError(f"{label}_OUTPUT_HASH_MISSING:{key}")
    path = root / filename
    require_sha(path, expected, f"{label}_{key}")
    return path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    p.add_argument("--calendar", type=Path, default=DEFAULT_CALENDAR)
    p.add_argument("--hlc-root", type=Path, default=DEFAULT_HLC_ROOT)
    p.add_argument("--open-root", type=Path, default=DEFAULT_OPEN_ROOT)
    p.add_argument("--integrity-root", type=Path, default=DEFAULT_INTEGRITY_ROOT)
    p.add_argument("--value-audit-root", type=Path, default=DEFAULT_VALUE_ROOT)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.resolve()
    panel_path = args.panel.resolve()
    calendar_path = args.calendar.resolve()
    hlc_root = args.hlc_root.resolve()
    open_root = args.open_root.resolve()
    integrity_root = args.integrity_root.resolve()
    value_root = args.value_audit_root.resolve()
    output = args.output_dir.resolve()

    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    cfg = read_json(config_path)
    if cfg.get("status") != "STAGE_A_PROTOCOL_FROZEN_WAITING_FOR_OFFLINE_RUNTIME":
        raise RuntimeError("CONSOLIDATION_CONFIG_STATUS_CHANGED")
    pins = cfg.get("frozen_inputs") or {}
    expected = cfg.get("expected_population") or {}

    require_sha(panel_path, str(pins["panel_sha256"]), "FROZEN_PANEL")
    require_sha(calendar_path, str(pins["calendar_sha256"]), "OFFICIAL_CALENDAR")
    require_sha(hlc_root / "MANIFEST.json", str(pins["hlc_remediation_manifest_sha256"]), "HLC_REMEDIATION_MANIFEST")
    require_sha(open_root / "MANIFEST.json", str(pins["open_remediation_manifest_sha256"]), "OPEN_REMEDIATION_MANIFEST")
    require_sha(integrity_root / "MANIFEST.json", str(pins["official_integrity_manifest_sha256"]), "OFFICIAL_INTEGRITY_MANIFEST")
    require_sha(value_root / "MANIFEST.json", str(pins["regular_market_value_audit_manifest_sha256"]), "REGULAR_VALUE_AUDIT_MANIFEST")

    hlc_manifest = read_json(hlc_root / "MANIFEST.json")
    open_manifest = read_json(open_root / "MANIFEST.json")
    if hlc_manifest.get("status") != "PRICE_BASIS_HLC_REMEDIATION_MATERIALIZED_REFIT_NOT_AUTHORIZED":
        raise RuntimeError("HLC_REMEDIATION_STATUS_CHANGED")
    if open_manifest.get("status") != "OPEN_PRICE_BASIS_REMEDIATION_MATERIALIZED_CROSS_LANE_CONSOLIDATION_REQUIRED_BEFORE_REFIT":
        raise RuntimeError("OPEN_REMEDIATION_STATUS_CHANGED")
    if open_manifest.get("policy") != "IDX_OPENPRICE_PRIMARY_CA_FACTOR_FALLBACK_FAIL_CLOSED_V1":
        raise RuntimeError("OPEN_REMEDIATION_POLICY_CHANGED")

    hlc_overlay_path = require_parent_output_hash(
        hlc_root, hlc_manifest, "overlay", "price_basis_hlc_overlay_v1.csv", "HLC_REMEDIATION"
    )
    open_overlay_path = require_parent_output_hash(
        open_root, open_manifest, "overlay_csv", "open_price_basis_overlay_v1.csv", "OPEN_REMEDIATION"
    )
    open_fail_path = require_parent_output_hash(
        open_root, open_manifest, "fail_closed", "open_price_basis_fail_closed_rows_v1.csv", "OPEN_REMEDIATION"
    )

    parent = pd.read_parquet(panel_path)
    hlc_overlay = pd.read_csv(hlc_overlay_path, low_memory=False)
    open_overlay = pd.read_csv(open_overlay_path, low_memory=False)
    open_fail = pd.read_csv(open_fail_path, low_memory=False)

    result = consolidate_stage_a(
        parent,
        hlc_overlay,
        open_overlay,
        open_fail,
        expected={key: int(value) for key, value in expected.items()},
    )

    output.mkdir(parents=True, exist_ok=True)
    panel_out = output / "model_safe_signal_research_panel_1260_stage_a_clean_candidate.parquet"
    provenance_parquet = output / "field_level_provenance_sidecar_v1.parquet"
    provenance_csv = output / "field_level_provenance_sidecar_v1.csv"
    ledger_csv = output / "clean_data_correction_ledger_v1.csv"

    result.panel.to_parquet(panel_out, index=False)
    result.provenance.to_parquet(provenance_parquet, index=False)
    result.provenance.to_csv(provenance_csv, index=False, lineterminator="\n")
    result.correction_ledger.to_csv(ledger_csv, index=False, lineterminator="\n")

    guardrails = dict(cfg.get("guardrails") or {})
    if any(bool(value) for value in guardrails.values()):
        raise RuntimeError(f"CONFIG_GUARDRAIL_TRUE:{guardrails}")

    summary = {
        "schema_version": "v4_x_clean_data_consolidation_stage_a_v1",
        **result.summary,
        "frozen_input_hashes": {
            "panel": sha256_file(panel_path),
            "calendar": sha256_file(calendar_path),
            "hlc_remediation_manifest": sha256_file(hlc_root / "MANIFEST.json"),
            "open_remediation_manifest": sha256_file(open_root / "MANIFEST.json"),
            "official_integrity_manifest": sha256_file(integrity_root / "MANIFEST.json"),
            "regular_market_value_audit_manifest": sha256_file(value_root / "MANIFEST.json"),
            "consolidation_config": sha256_file(config_path),
        },
        "parent_output_hashes_verified": {
            "hlc_overlay": sha256_file(hlc_overlay_path),
            "open_overlay": sha256_file(open_overlay_path),
            "open_fail_closed": sha256_file(open_fail_path),
        },
        "artifacts": {
            "clean_candidate_panel": str(panel_out),
            "field_level_provenance_parquet": str(provenance_parquet),
            "field_level_provenance_csv": str(provenance_csv),
            "correction_ledger": str(ledger_csv),
        },
        "guardrails": guardrails,
        "final_clean_input_authorized": False,
        "model_refit_authorized": False,
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    outputs = {
        "clean_candidate_panel": panel_out,
        "field_level_provenance_parquet": provenance_parquet,
        "field_level_provenance_csv": provenance_csv,
        "correction_ledger": ledger_csv,
        "summary": summary_path,
    }
    manifest = {
        "schema_version": "v4_x_clean_data_consolidation_stage_a_manifest_v1",
        "status": summary["status"],
        "policy": summary["policy"],
        "inputs": summary["frozen_input_hashes"],
        "verified_parent_outputs": summary["parent_output_hashes_verified"],
        "guardrails": guardrails,
        "final_clean_input_authorized": False,
        "model_refit_authorized": False,
        "output_hashes": {key: sha256_file(path) for key, path in outputs.items()},
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                **summary,
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
