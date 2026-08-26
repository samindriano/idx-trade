from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

import pandas as pd

from .provenance import sha256_file
from .stockbit_intraday_recovery import NO_CHART_404, SKIPPED_IDX_NO_ACTIVITY, SUCCESS
from .stockbit_intraday_runtime import SessionJournal
from .stockbit_intraday_session_v2 import (
    SESSION_SCHEMA,
    StockbitIntradaySessionError,
    load_run_contract,
    verify_bound_gate,
)


_SHA = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_BOUND_FILES = {
    "day_metadata.json",
    "universe_snapshot.csv",
    "session_contract.json",
    "gate/manifest.json",
    "gate/decisions.csv",
    "gate/evidence.json",
}


def _provider_observations_before_gate_reconciliation(
    journal: SessionJournal,
) -> dict[str, dict[str, Any]]:
    """Reconstruct the final provider observation for every SHADOW ticker.

    In SHADOW/SHADOW_RECHECK a zero-activity ticker is still queried. A
    provider ``NO_CHART_404`` may then be followed by an immutable
    ``SKIPPED_IDX_NO_ACTIVITY`` reconciliation event. Rollout metrics must be
    recomputed from the provider observation immediately before that gate
    event, not from the reconciled latest status.
    """

    universe = journal.load_universe()
    result: dict[str, dict[str, Any]] = {}
    for raw_ticker in universe["ticker"].astype(str):
        ticker = raw_ticker.upper()
        provider_status: dict[str, Any] | None = None
        for attempt_dir in journal._attempt_dirs(ticker):
            status = journal._verify_attempt(attempt_dir)
            observed_ticker = str(status.get("ticker") or "").upper()
            if observed_ticker != ticker:
                raise StockbitIntradaySessionError(
                    f"SESSION_MANIFEST_ATTEMPT_TICKER_MISMATCH:{ticker}"
                )
            if str(status.get("status") or "").upper() == SKIPPED_IDX_NO_ACTIVITY:
                continue
            provider_status = status
        if provider_status is not None:
            result[ticker] = provider_status
    return result


def _recompute_shadow_metrics(journal: SessionJournal) -> dict[str, Any]:
    decisions_path = journal.root / "gate" / "decisions.csv"
    decisions = pd.read_csv(decisions_path)
    required = {"ticker", "gate_decision"}
    if decisions.empty or required - set(decisions.columns):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SHADOW_GATE_DECISIONS_INVALID")
    decisions["ticker"] = decisions["ticker"].astype(str).str.upper()
    if decisions["ticker"].duplicated().any():
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SHADOW_GATE_TICKER_DUPLICATE")

    provider_statuses = _provider_observations_before_gate_reconciliation(journal)
    false_negative = 0
    false_positive = 0
    actual_success = 0
    actual_no_chart_404 = 0
    certification_eligible = True

    for _, row in decisions.iterrows():
        ticker = str(row["ticker"])
        observed = str((provider_statuses.get(ticker) or {}).get("status") or "").upper()
        predicted_fetch = str(row["gate_decision"]) != "SKIP_NO_ACTIVITY"
        success = observed == SUCCESS
        if success:
            actual_success += 1
        elif observed == NO_CHART_404:
            actual_no_chart_404 += 1
        else:
            certification_eligible = False
        if not predicted_fetch and success:
            false_negative += 1
        if predicted_fetch and not success:
            false_positive += 1

    if len(provider_statuses) != len(decisions):
        certification_eligible = False

    return {
        "false_negative": false_negative,
        "false_positive": false_positive,
        "actual_success": actual_success,
        "actual_no_chart_404": actual_no_chart_404,
        "certification_eligible": certification_eligible,
    }


def _verify_shadow_metrics(payload: dict[str, Any], journal: SessionJournal) -> None:
    mode = str(payload.get("run_mode") or "")
    metrics = payload.get("shadow_metrics")
    if mode == "ENFORCE":
        if metrics is not None:
            raise StockbitIntradaySessionError("SESSION_MANIFEST_ENFORCE_SHADOW_METRICS_PRESENT")
        return
    if not isinstance(metrics, dict):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SHADOW_METRICS_MISSING")
    for field in ("false_negative", "false_positive", "actual_success", "actual_no_chart_404"):
        value = metrics.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise StockbitIntradaySessionError(f"SESSION_MANIFEST_SHADOW_METRIC_INVALID:{field}")
    if metrics.get("certification_eligible") not in {True, False}:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_CERTIFICATION_ELIGIBLE_INVALID")
    recomputed = _recompute_shadow_metrics(journal)
    if metrics != recomputed:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SHADOW_METRICS_RECOMPUTE_MISMATCH")


def load_verified_session_manifest(journal: SessionJournal) -> tuple[dict[str, Any], str] | None:
    path = journal.root / "session_manifest.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_INVALID") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SESSION_SCHEMA:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SCHEMA_INVALID")
    if payload.get("session_date") != journal.expected_date.isoformat():
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SESSION_MISMATCH")
    if payload.get("status") != "ADMISSIBLE_COMPLETE":
        raise StockbitIntradaySessionError("SESSION_MANIFEST_STATUS_INVALID")
    if payload.get("run_mode") not in {"SHADOW", "SHADOW_RECHECK", "ENFORCE"}:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_MODE_INVALID")
    completion = payload.get("completion")
    if (
        not isinstance(completion, dict)
        or completion.get("admissible_complete") is not True
        or completion.get("complete") is not True
    ):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_COMPLETION_INVALID")
    if (
        payload.get("synthetic_fill_used") is not False
        or payload.get("retroactive_capture_used") is not False
        or payload.get("outcome_accessed") is not False
    ):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SAFETY_GUARD_INVALID")

    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_FILES_INVALID")
    if not _REQUIRED_BOUND_FILES.issubset(set(str(value) for value in files)):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_REQUIRED_BOUND_FILE_MISSING")
    root = journal.root.resolve()
    for relative, declared_sha in files.items():
        text = str(relative).replace("\\", "/")
        posix = PurePosixPath(text)
        if not text or posix.is_absolute() or ".." in posix.parts or "." in posix.parts:
            raise StockbitIntradaySessionError("SESSION_MANIFEST_FILE_PATH_INVALID")
        digest = str(declared_sha or "").strip().lower()
        if not _SHA.fullmatch(digest):
            raise StockbitIntradaySessionError("SESSION_MANIFEST_FILE_SHA_INVALID")
        target = (root / Path(text)).resolve()
        if root not in target.parents or not target.is_file() or sha256_file(target) != digest:
            raise StockbitIntradaySessionError("SESSION_MANIFEST_FILE_SHA_MISMATCH")

    # File hashes are necessary but not sufficient. Re-evaluate the frozen
    # semantic parents and require the final manifest to bind the same values.
    contract = load_run_contract(journal)
    gate = verify_bound_gate(journal)
    gate_sha = sha256_file(journal.root / "gate" / "manifest.json")
    if payload.get("run_mode") != contract.get("run_mode"):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_CONTRACT_MODE_MISMATCH")
    if payload.get("schedule_attestation_sha256") != contract.get("schedule_attestation_sha256"):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_CONTRACT_SCHEDULE_MISMATCH")
    if payload.get("gate_manifest_sha256") != contract.get("gate_manifest_sha256") or payload.get("gate_manifest_sha256") != gate_sha:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_GATE_BINDING_MISMATCH")
    if payload.get("eod_manifest_sha256") != gate.get("eod_manifest_sha256"):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_EOD_BINDING_MISMATCH")

    recomputed = journal.summary()
    if recomputed != completion:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_COMPLETION_RECOMPUTE_MISMATCH")
    _verify_shadow_metrics(payload, journal)
    return payload, sha256_file(path)
