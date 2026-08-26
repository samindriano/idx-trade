from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any, Mapping

import pandas as pd

from .provenance import sha256_file
from .stockbit_intraday_eod_context import VerifiedIntradayEodContext
from .stockbit_intraday_runtime import SessionJournal


SESSION_SCHEMA = "idx_trade_stockbit_intraday_session_v2"
GATE_SCHEMA = "idx_trade_stockbit_intraday_gate_binding_v2"
CONTRACT_SCHEMA = "idx_trade_stockbit_intraday_run_contract_v2"
_SHA = re.compile(r"^[0-9a-f]{64}$")


class StockbitIntradaySessionError(RuntimeError):
    pass


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        + "\n"
    ).encode("utf-8")


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    stream = io.StringIO()
    frame.to_csv(stream, index=False, lineterminator="\n")
    return stream.getvalue().encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_once(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise StockbitIntradaySessionError(f"SESSION_IMMUTABILITY_CONFLICT:{path}")
        return False
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
    except FileExistsError:
        if path.read_bytes() != payload:
            raise StockbitIntradaySessionError(f"SESSION_IMMUTABILITY_CONFLICT:{path}")
        return False
    if path.read_bytes() != payload:
        raise StockbitIntradaySessionError(f"SESSION_WRITE_VERIFY_FAILED:{path}")
    return True


def _required_sha(value: object, *, label: str) -> str:
    digest = str(value or "").strip().lower()
    if not _SHA.fullmatch(digest):
        raise StockbitIntradaySessionError(f"{label}_SHA_INVALID")
    return digest


def bind_gate_snapshot(journal: SessionJournal, context: VerifiedIntradayEodContext) -> str:
    if context.session_date != journal.expected_date.isoformat():
        raise StockbitIntradaySessionError("GATE_BINDING_SESSION_MISMATCH")
    universe = journal.load_universe()["ticker"].astype(str).sort_values().tolist()
    context_universe = context.universe["ticker"].astype(str).sort_values().tolist()
    if universe != context_universe:
        raise StockbitIntradaySessionError("GATE_BINDING_UNIVERSE_MISMATCH")

    gate_root = journal.root / "gate"
    decisions_path = gate_root / "decisions.csv"
    evidence_path = gate_root / "evidence.json"
    manifest_path = gate_root / "manifest.json"
    decisions = context.gate.decisions.sort_values("ticker").reset_index(drop=True)
    decisions_bytes = _csv_bytes(decisions)
    evidence = {
        "session_date": context.session_date,
        "eod_manifest_sha256": context.eod_manifest_sha256,
        "universe_evidence_sha256": context.universe_evidence_sha256,
        "stock_summary_sha256": context.gate.stock_summary_sha256,
        "stock_summary_raw_sha256": context.gate.stock_summary_raw_sha256,
        "source_ref": context.gate.source_ref,
        "observed_available_at_utc": context.gate.observed_available_at_utc,
    }
    evidence_bytes = _canonical_json_bytes(evidence)
    _write_once(decisions_path, decisions_bytes)
    _write_once(evidence_path, evidence_bytes)
    counts = decisions["gate_decision"].astype(str).value_counts().to_dict()
    manifest = {
        "schema_version": GATE_SCHEMA,
        "session_date": context.session_date,
        "eod_manifest_sha256": context.eod_manifest_sha256,
        "universe_evidence_sha256": context.universe_evidence_sha256,
        "decisions_sha256": _sha_bytes(decisions_bytes),
        "evidence_sha256": _sha_bytes(evidence_bytes),
        "decision_rows": len(decisions),
        "decision_counts": counts,
    }
    encoded = _canonical_json_bytes(manifest)
    _write_once(manifest_path, encoded)
    verify_bound_gate(journal)
    return _sha_bytes(encoded)


def verify_bound_gate(journal: SessionJournal) -> dict[str, Any]:
    gate_root = journal.root / "gate"
    manifest_path = gate_root / "manifest.json"
    decisions_path = gate_root / "decisions.csv"
    evidence_path = gate_root / "evidence.json"
    if not manifest_path.is_file() or not decisions_path.is_file() or not evidence_path.is_file():
        raise StockbitIntradaySessionError("BOUND_GATE_INCOMPLETE")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StockbitIntradaySessionError("BOUND_GATE_MANIFEST_INVALID") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != GATE_SCHEMA:
        raise StockbitIntradaySessionError("BOUND_GATE_SCHEMA_INVALID")
    if manifest.get("session_date") != journal.expected_date.isoformat():
        raise StockbitIntradaySessionError("BOUND_GATE_SESSION_MISMATCH")
    if sha256_file(decisions_path) != _required_sha(manifest.get("decisions_sha256"), label="BOUND_GATE_DECISIONS"):
        raise StockbitIntradaySessionError("BOUND_GATE_DECISIONS_SHA_MISMATCH")
    if sha256_file(evidence_path) != _required_sha(manifest.get("evidence_sha256"), label="BOUND_GATE_EVIDENCE"):
        raise StockbitIntradaySessionError("BOUND_GATE_EVIDENCE_SHA_MISMATCH")
    frame = pd.read_csv(decisions_path)
    if len(frame) != int(manifest.get("decision_rows", -1)):
        raise StockbitIntradaySessionError("BOUND_GATE_ROW_COUNT_MISMATCH")
    if frame.empty or "ticker" not in frame.columns or "gate_decision" not in frame.columns:
        raise StockbitIntradaySessionError("BOUND_GATE_DECISIONS_SCHEMA_INVALID")
    if frame["ticker"].astype(str).duplicated().any():
        raise StockbitIntradaySessionError("BOUND_GATE_TICKER_DUPLICATE")
    return manifest


def bind_run_contract(
    journal: SessionJournal,
    *,
    run_mode: str,
    schedule_attestation_sha256: str,
    gate_manifest_sha256: str,
) -> str:
    if run_mode not in {"SHADOW", "SHADOW_RECHECK", "ENFORCE"}:
        raise StockbitIntradaySessionError("RUN_CONTRACT_MODE_INVALID")
    schedule_sha = _required_sha(schedule_attestation_sha256, label="RUN_CONTRACT_SCHEDULE")
    gate_sha = _required_sha(gate_manifest_sha256, label="RUN_CONTRACT_GATE")
    gate_path = journal.root / "gate" / "manifest.json"
    if not gate_path.is_file() or sha256_file(gate_path) != gate_sha:
        raise StockbitIntradaySessionError("RUN_CONTRACT_GATE_SHA_MISMATCH")
    payload = {
        "schema_version": CONTRACT_SCHEMA,
        "session_date": journal.expected_date.isoformat(),
        "run_mode": run_mode,
        "schedule_attestation_sha256": schedule_sha,
        "gate_manifest_sha256": gate_sha,
        "retroactive_capture_authorized": False,
        "synthetic_fill_authorized": False,
    }
    encoded = _canonical_json_bytes(payload)
    path = journal.root / "session_contract.json"
    _write_once(path, encoded)
    return _sha_bytes(encoded)


def load_run_contract(journal: SessionJournal) -> dict[str, Any]:
    path = journal.root / "session_contract.json"
    if not path.is_file():
        raise StockbitIntradaySessionError("RUN_CONTRACT_MISSING")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StockbitIntradaySessionError("RUN_CONTRACT_INVALID") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != CONTRACT_SCHEMA:
        raise StockbitIntradaySessionError("RUN_CONTRACT_SCHEMA_INVALID")
    if payload.get("session_date") != journal.expected_date.isoformat():
        raise StockbitIntradaySessionError("RUN_CONTRACT_SESSION_MISMATCH")
    if payload.get("run_mode") not in {"SHADOW", "SHADOW_RECHECK", "ENFORCE"}:
        raise StockbitIntradaySessionError("RUN_CONTRACT_MODE_INVALID")
    _required_sha(payload.get("schedule_attestation_sha256"), label="RUN_CONTRACT_SCHEDULE")
    gate_sha = _required_sha(payload.get("gate_manifest_sha256"), label="RUN_CONTRACT_GATE")
    if sha256_file(journal.root / "gate" / "manifest.json") != gate_sha:
        raise StockbitIntradaySessionError("RUN_CONTRACT_GATE_SHA_MISMATCH")
    if payload.get("retroactive_capture_authorized") is not False or payload.get("synthetic_fill_authorized") is not False:
        raise StockbitIntradaySessionError("RUN_CONTRACT_SAFETY_GUARD_INVALID")
    return payload


def finalize_admissible_session(
    journal: SessionJournal,
    *,
    shadow_metrics: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    summary = journal.summary()
    if summary.get("admissible_complete") is not True or summary.get("complete") is not True:
        raise StockbitIntradaySessionError("SESSION_NOT_ADMISSIBLE_COMPLETE")
    gate = verify_bound_gate(journal)
    contract = load_run_contract(journal)

    excluded = {"session_manifest.json"}
    files: dict[str, str] = {}
    for path in sorted(journal.root.rglob("*"), key=lambda value: value.as_posix()):
        if not path.is_file() or path.name in excluded or path.suffix == ".tmp":
            continue
        relative = path.relative_to(journal.root).as_posix()
        files[relative] = sha256_file(path)
    if not files:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_INPUTS_EMPTY")

    payload = {
        "schema_version": SESSION_SCHEMA,
        "session_date": journal.expected_date.isoformat(),
        "status": "ADMISSIBLE_COMPLETE",
        "run_mode": contract["run_mode"],
        "schedule_attestation_sha256": contract["schedule_attestation_sha256"],
        "gate_manifest_sha256": sha256_file(journal.root / "gate" / "manifest.json"),
        "eod_manifest_sha256": gate["eod_manifest_sha256"],
        "completion": summary,
        "shadow_metrics": dict(shadow_metrics) if shadow_metrics is not None else None,
        "files": files,
        "synthetic_fill_used": False,
        "retroactive_capture_used": False,
        "outcome_accessed": False,
    }
    encoded = _canonical_json_bytes(payload)
    path = journal.root / "session_manifest.json"
    _write_once(path, encoded)
    sha = _sha_bytes(encoded)
    if sha256_file(path) != sha:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_WRITE_VERIFY_FAILED")
    return payload, sha
