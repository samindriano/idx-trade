from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class V43CAAdmissionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise V43CAAdmissionError(f"{label}_MISSING:{path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - surfaced with stable class
        raise V43CAAdmissionError(f"{label}_INVALID_JSON:{path}") from exc
    if not isinstance(value, dict):
        raise V43CAAdmissionError(f"{label}_NOT_OBJECT:{path}")
    return value


def _require_sha(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise V43CAAdmissionError(f"{label}_MISSING:{path}")
    actual = sha256_file(path)
    if actual != expected:
        raise V43CAAdmissionError(
            f"{label}_SHA_MISMATCH:{actual}!={expected}"
        )
    return actual


def _require_bool(payload: dict[str, Any], key: str, expected: bool, label: str) -> None:
    if payload.get(key) is not expected:
        raise V43CAAdmissionError(
            f"{label}_{key.upper()}_MISMATCH:{payload.get(key)!r}!={expected!r}"
        )


def _manifest_candidate(root: Path) -> Path:
    for name in ("manifest.json", "MANIFEST.json"):
        path = root / name
        if path.is_file():
            return path
    raise V43CAAdmissionError(f"PIT_SUPPORT_MANIFEST_MISSING:{root}")


def verify_v4_3_ca_admission_inputs(
    *,
    contract: dict[str, Any],
    ca_root: Path,
    pit_support_root: Path,
    execution_code_root: Path,
) -> dict[str, Any]:
    if contract.get("schema_version") != "ranking_v4_3_ca_admission_v1":
        raise V43CAAdmissionError("CA_ADMISSION_CONTRACT_SCHEMA_CHANGED")
    if contract.get("status") != "V4_3_CA_ADMISSION_FROZEN_PRE_TARGET_ACCESS":
        raise V43CAAdmissionError("CA_ADMISSION_CONTRACT_NOT_FROZEN")
    if contract.get("outcome_blind") is not True:
        raise V43CAAdmissionError("CA_ADMISSION_CONTRACT_NOT_OUTCOME_BLIND")
    if contract.get("scientific_config_mutable") is not False:
        raise V43CAAdmissionError("SCIENTIFIC_CONFIG_MUST_REMAIN_FROZEN")

    pins = contract["parents"]
    gate = contract["ca_gate"]
    guardrails = contract["required_guardrails"]

    # Previously accepted pre-target engineering lineage.
    pit_manifest_path = _manifest_candidate(pit_support_root)
    pit_manifest_sha = _require_sha(
        pit_manifest_path,
        pins["v4_3_pit_support_manifest_sha256"],
        "PIT_SUPPORT_MANIFEST",
    )

    execution_manifest_path = (
        execution_code_root / "v4_3_execution_code_manifest.json"
    )
    execution_manifest_sha = _require_sha(
        execution_manifest_path,
        pins["v4_3_execution_code_manifest_sha256"],
        "EXECUTION_CODE_MANIFEST",
    )
    execution = _load_json(execution_manifest_path, "EXECUTION_CODE_MANIFEST")
    if execution.get("schema_version") != "ranking_v4_3_execution_code_manifest_v1":
        raise V43CAAdmissionError("EXECUTION_CODE_MANIFEST_SCHEMA_CHANGED")
    if execution.get("status") != "V4_3_EXECUTION_CODE_IDENTITY_CAPTURED_NO_HISTORICAL_TARGET_ACCESS":
        raise V43CAAdmissionError("EXECUTION_CODE_MANIFEST_STATUS_CHANGED")
    _require_bool(execution, "outcome_blind", True, "EXECUTION_CODE")
    _require_bool(execution, "historical_target_loaded", False, "EXECUTION_CODE")
    _require_bool(execution, "historical_model_fit", False, "EXECUTION_CODE")
    _require_bool(execution, "historical_prediction_generated", False, "EXECUTION_CODE")
    _require_bool(execution, "historical_performance_computed", False, "EXECUTION_CODE")
    _require_bool(execution, "provider_calls", False, "EXECUTION_CODE")
    runtime = execution.get("runtime") or {}
    if runtime.get("accepted_manifest_sha256") != pins["v4_3_prefit_runtime_manifest_sha256"]:
        raise V43CAAdmissionError("PREFIT_RUNTIME_MANIFEST_PIN_MISMATCH")
    if runtime.get("exact_match") is not True:
        raise V43CAAdmissionError("PREFIT_RUNTIME_NOT_EXACT_MATCH")
    if len(execution.get("canonical_git_source_sha256") or {}) != 16:
        raise V43CAAdmissionError("EXECUTION_CODE_SOURCE_COUNT_CHANGED")

    # Final Corporate Action result: byte pin first, then semantic assertions.
    ca_manifest_path = ca_root / "MANIFEST.json"
    ca_manifest_sha = _require_sha(
        ca_manifest_path,
        pins["v4_ca_final_manifest_sha256"],
        "CA_FINAL_MANIFEST",
    )
    ca_manifest = _load_json(ca_manifest_path, "CA_FINAL_MANIFEST")
    if ca_manifest.get("schema_version") != "v4_ca_fren_ksei_exact_manifest_v1":
        raise V43CAAdmissionError("CA_FINAL_MANIFEST_SCHEMA_CHANGED")
    if ca_manifest.get("status") != "V4_CA_FREN_KSEI_EXACT_REPLAY_COMPLETE":
        raise V43CAAdmissionError("CA_FINAL_MANIFEST_STATUS_CHANGED")
    _require_bool(ca_manifest, "outcome_blind", True, "CA_FINAL_MANIFEST")
    _require_bool(ca_manifest, "offline_replay", True, "CA_FINAL_MANIFEST")

    overlay_path = ca_root / "fren_ksei_exact_overlay.json"
    overlay = _load_json(overlay_path, "CA_FINAL_OVERLAY")
    overlay_sha = sha256_file(overlay_path)
    if overlay_sha != ca_manifest.get("overlay_sha256"):
        raise V43CAAdmissionError("CA_FINAL_OVERLAY_SHA_MISMATCH")

    replay_root = ca_root / "final_continuity_611_fren_ksei_exact"
    summary_path = replay_root / "summary.json"
    summary_sha = _require_sha(
        summary_path,
        pins["v4_ca_final_continuity_summary_sha256"],
        "CA_FINAL_CONTINUITY_SUMMARY",
    )
    summary = _load_json(summary_path, "CA_FINAL_CONTINUITY_SUMMARY")

    ledger_path = replay_root / "v4_frozen_continuity_ledger_event_window.csv"
    ledger_sha = _require_sha(
        ledger_path,
        pins["v4_ca_final_continuity_ledger_sha256"],
        "CA_FINAL_CONTINUITY_LEDGER",
    )

    if summary.get("verdict") != gate["required_verdict"]:
        raise V43CAAdmissionError("CA_CONTINUITY_VERDICT_NOT_CERTIFIED")
    if summary.get("corporate_action_continuity_certified") is not gate[
        "required_corporate_action_continuity_certified"
    ]:
        raise V43CAAdmissionError("CA_CONTINUITY_CERTIFICATION_FALSE")

    exact_scalars = {
        "frozen_dates": gate["required_frozen_dates"],
        "frozen_rows": gate["required_frozen_rows"],
        "frozen_tickers": gate["required_frozen_tickers"],
        "coverage_certified_tickers": gate["expected_coverage_certified_tickers"],
        "coverage_unresolved_tickers": gate["expected_coverage_unresolved_tickers"],
    }
    for key, expected in exact_scalars.items():
        if int(summary.get(key, -1)) != int(expected):
            raise V43CAAdmissionError(
                f"CA_{key.upper()}_MISMATCH:{summary.get(key)!r}!={expected!r}"
            )

    conflicts = summary.get("cross_source_conflict_tickers")
    if not isinstance(conflicts, list):
        raise V43CAAdmissionError("CA_CROSS_SOURCE_CONFLICTS_NOT_LIST")
    if len(conflicts) != int(gate["required_cross_source_conflict_tickers"]):
        raise V43CAAdmissionError("CA_CROSS_SOURCE_CONFLICTS_PRESENT")

    per_date = summary.get("per_date") or {}
    required_gate_dates = gate["required_gate_dates"]
    date_fields = {
        "h5": ("h5_gate_dates", "h5_min_rate"),
        "h10": ("h10_gate_dates", "h10_min_rate"),
        "consensus": ("consensus_gate_dates", "consensus_min_rate"),
    }
    minimum = float(gate["minimum_per_date_rate"])
    observed_rates: dict[str, float] = {}
    for name, (count_key, rate_key) in date_fields.items():
        if int(per_date.get(count_key, -1)) != int(required_gate_dates[name]):
            raise V43CAAdmissionError(f"CA_{name.upper()}_GATE_DATE_COUNT_FAILED")
        rate = float(per_date.get(rate_key, -1.0))
        if rate < minimum:
            raise V43CAAdmissionError(
                f"CA_{name.upper()}_MIN_RATE_FAILED:{rate}<{minimum}"
            )
        observed_rates[name] = rate

    # Guardrails are asserted from the final overlay produced by the successful
    # offline replay. The exact root manifest pins this overlay byte identity.
    for key, expected in guardrails.items():
        if overlay.get(key) is not expected:
            raise V43CAAdmissionError(
                f"CA_GUARDRAIL_{key.upper()}_MISMATCH:{overlay.get(key)!r}!={expected!r}"
            )
    if overlay.get("per_date_sha256") != pins["v4_ca_final_per_date_sha256"]:
        raise V43CAAdmissionError("CA_FINAL_PER_DATE_PIN_MISMATCH")
    if overlay.get("rights_pdf_sha256") != "5af9284d88a7621f3b400fe7f9a28e104459ae6e710e47bf765974c940daaa91":
        raise V43CAAdmissionError("FREN_RIGHTS_EVIDENCE_PIN_MISMATCH")
    if overlay.get("rights_transition_date") != "2024-04-17":
        raise V43CAAdmissionError("FREN_RIGHTS_TRANSITION_CHANGED")
    if overlay.get("merger_transition_date") != "2025-04-16":
        raise V43CAAdmissionError("FREN_MERGER_TRANSITION_CHANGED")

    return {
        "pit_support_manifest_path": str(pit_manifest_path),
        "pit_support_manifest_sha256": pit_manifest_sha,
        "execution_code_manifest_path": str(execution_manifest_path),
        "execution_code_manifest_sha256": execution_manifest_sha,
        "ca_final_manifest_path": str(ca_manifest_path),
        "ca_final_manifest_sha256": ca_manifest_sha,
        "ca_continuity_summary_path": str(summary_path),
        "ca_continuity_summary_sha256": summary_sha,
        "ca_continuity_ledger_path": str(ledger_path),
        "ca_continuity_ledger_sha256": ledger_sha,
        "ca_per_date_min_rates": observed_rates,
        "coverage_certified_tickers": int(summary["coverage_certified_tickers"]),
        "coverage_unresolved_tickers": int(summary["coverage_unresolved_tickers"]),
        "frozen_dates": int(summary["frozen_dates"]),
        "frozen_rows": int(summary["frozen_rows"]),
        "frozen_tickers": int(summary["frozen_tickers"]),
    }
