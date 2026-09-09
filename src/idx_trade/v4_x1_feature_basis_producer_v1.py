"""Outcome-blind forward feature-basis evidence producer for V4-X1.

The producer is deliberately a pre-scorer side effect of the existing
``PopulationScoreGate``.  It captures the already-approved IDX corporate
action source for the complete same-session model-input population, then writes
an immutable evidence file and detached manifest.  It never changes the frozen
feature builder, model, score formula, or counter.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Mapping, Sequence
from uuid import uuid4

import pandas as pd

from . import forward_ca_attestation_v1 as forward_ca
from . import v4_x1_population_admission_v1 as gate
from .forward_monitoring import runtime_paths
from .provenance import sha256_file


PRODUCER_IMPLEMENTATION_PATH = Path(__file__).resolve()
TRUST_CONFIG_ENV = "E2E_CLOUD_FEATURE_BASIS_TRUST_CONTRACT"
TRUST_CONFIG_RELATIVE_PATH = Path("config/forward_feature_basis_trusted_producer_v1.json")
CAPTURE_PHASE = "POST_EOD"
CAPTURE_DIRNAME = "feature_basis_ca"
CAPTURE_MANIFEST_NAME = "MANIFEST.json"
CAPTURE_ATTESTATION_NAME = "attestation.json"
FAILURE_DIRNAME = "feature_basis_attempts"
FAILURE_PREFIX = "capture_failure_"
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


class FeatureBasisProducerError(RuntimeError):
    """A source or producer precondition could not be proven."""


def _json_bytes(value: object, *, indent: int | None = None) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":") if indent is None else None,
            indent=indent,
        )
        + "\n"
    ).encode("utf-8")


def _write_immutable(path: Path, payload: bytes) -> str:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(payload).hexdigest()
    if path.exists():
        if path.read_bytes() != payload:
            raise FeatureBasisProducerError(f"IMMUTABLE_ARTIFACT_CONFLICT:{path}")
        return digest
    temporary = path.with_name(f".{path.name}.{digest[:12]}.{uuid4().hex}.tmp")
    temporary.write_bytes(payload)
    try:
        if path.exists():
            if path.read_bytes() != payload:
                raise FeatureBasisProducerError(f"IMMUTABLE_ARTIFACT_CONFLICT:{path}")
        else:
            temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return digest


def _write_json(path: Path, value: object, *, indent: int = 2) -> str:
    return _write_immutable(path, _json_bytes(value, indent=indent))


def load_trusted_producer_contract(repo_root: str | Path) -> dict[str, Any] | None:
    """Load the external trust anchor; the admission gate verifies its digest."""

    configured = os.getenv(TRUST_CONFIG_ENV, "").strip()
    path = (
        Path(configured).expanduser().resolve()
        if configured
        else (Path(repo_root).expanduser().resolve() / TRUST_CONFIG_RELATIVE_PATH)
    )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def _parse_observed(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise FeatureBasisProducerError("OBSERVED_AT_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FeatureBasisProducerError("OBSERVED_AT_NOT_TIMEZONE_AWARE")
    return parsed


def _session_from_observed(observed: datetime) -> str:
    return observed.astimezone(gate.JAKARTA).date().isoformat()


def _safe_tickers(model_input: pd.DataFrame, session: str) -> tuple[str, ...]:
    required = {"ticker", "date"}
    if not required.issubset(model_input.columns):
        raise FeatureBasisProducerError("MODEL_INPUT_COLUMNS_MISSING")
    dates = pd.to_datetime(model_input["date"], errors="coerce")
    if dates.isna().any():
        raise FeatureBasisProducerError("MODEL_INPUT_DATE_INVALID")
    try:
        dates = dates.dt.tz_localize(None).dt.normalize()
    except TypeError:
        dates = dates.dt.normalize()
    if not dates.eq(pd.Timestamp(session)).all():
        raise FeatureBasisProducerError("MODEL_INPUT_SESSION_MISMATCH")
    tickers = tuple(sorted({gate._safe_ticker(value) for value in model_input["ticker"]}))
    if not tickers:
        raise FeatureBasisProducerError("MODEL_INPUT_POPULATION_EMPTY")
    if model_input.duplicated(["ticker", "date"]).any():
        raise FeatureBasisProducerError("MODEL_INPUT_DUPLICATE")
    return tickers


def _candidate_context(
    runtime_root: str | Path,
    *,
    clean_panel: str | Path,
    observed_by: str,
) -> dict[str, Any]:
    observed = _parse_observed(observed_by)
    session = _session_from_observed(observed)
    paths = runtime_paths(runtime_root)
    session_root = (paths.session_root / session).resolve()
    eod_path = session_root / "manifest.json"
    if not eod_path.is_file():
        raise FeatureBasisProducerError("SAME_SESSION_EOD_MANIFEST_MISSING")
    try:
        eod = json.loads(eod_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FeatureBasisProducerError("SAME_SESSION_EOD_MANIFEST_INVALID") from exc
    if (
        not isinstance(eod, Mapping)
        or eod.get("status") != "DATA_READY"
        or str(eod.get("session_date") or "") != session
        or eod.get("outcome_blind") is not True
        or eod.get("forward_outcomes_accessed") is not False
    ):
        raise FeatureBasisProducerError("SAME_SESSION_EOD_NOT_DATA_READY")
    model_input_path = Path(str(eod.get("snapshot_path") or "")).expanduser().resolve()
    candidate_path = Path(str(eod.get("session_ohlcv_path") or "")).expanduser().resolve()
    panel_path = Path(clean_panel).expanduser().resolve()
    security_master_path = (paths.listings_root / "security_master.csv").resolve()
    if (
        not model_input_path.is_file()
        or not candidate_path.is_file()
        or not panel_path.is_file()
        or not security_master_path.is_file()
    ):
        raise FeatureBasisProducerError("FEATURE_BASIS_INPUT_ARTIFACT_MISSING")
    model_input = pd.read_parquet(model_input_path)
    tickers = _safe_tickers(model_input, session)
    expected_candidate_sha = str(eod.get("session_ohlcv_sha256") or "").lower()
    if not expected_candidate_sha:
        raise FeatureBasisProducerError("FEATURE_BASIS_CANDIDATE_HASH_MISSING")
    candidate_sources = gate._verify_candidate_session_ohlcv(
        candidate_path,
        expected_candidate_sha,
        session,
        pd.Timestamp(observed),
        tickers,
    )
    panel_dates = pd.to_datetime(
        pd.read_parquet(panel_path, columns=["date"])["date"], errors="coerce"
    )
    if panel_dates.isna().any():
        raise FeatureBasisProducerError("CLEAN_PANEL_DATE_INVALID")
    try:
        panel_dates = panel_dates.dt.tz_localize(None).dt.normalize()
    except TypeError:
        panel_dates = panel_dates.dt.normalize()
    if panel_dates.empty:
        raise FeatureBasisProducerError("CLEAN_PANEL_EMPTY")
    historical_end = panel_dates.max().date().isoformat()
    official, calendar_sources = gate._canonical_scoring_calendar(paths, session)
    if session not in official:
        raise FeatureBasisProducerError("FEATURE_BASIS_SESSION_NOT_OFFICIAL")
    target_index = official.index(session)
    # The producer captures the clean boundary itself as well as every official
    # session needed by the longest (59-session) dependency span.
    capture_from = (
        pd.Timestamp(historical_end) - pd.Timedelta(days=1)
    ).date().isoformat()
    return {
        "observed": observed,
        "session": session,
        "paths": paths,
        "session_root": session_root,
        "eod": dict(eod),
        "eod_path": eod_path,
        "model_input_path": model_input_path,
        "model_input": model_input,
        "candidate_path": candidate_path,
        "candidate_sources": candidate_sources,
        "security_master_path": security_master_path,
        "panel_path": panel_path,
        "tickers": tickers,
        "historical_end": historical_end,
        "official": tuple(official),
        "calendar_sources": calendar_sources,
        "target_index": target_index,
        "capture_from": capture_from,
    }


def _capture_paths(context: Mapping[str, Any]) -> tuple[Path, Path]:
    root = Path(context["session_root"]) / CAPTURE_DIRNAME / CAPTURE_PHASE
    return root / CAPTURE_MANIFEST_NAME, root / CAPTURE_ATTESTATION_NAME


def _verify_capture(
    context: Mapping[str, Any], manifest_path: Path, attestation_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        phase = forward_ca.verify_phase_manifest(manifest_path)
        from .forward_dividend_execution_v1_1 import (
            _load_and_verify_post_eod_attestation_v1_2,
        )

        attestation, from_date, through_date, covered, _, phase_path, phase_sha, _ = (
            _load_and_verify_post_eod_attestation_v1_2(
                path=attestation_path,
                expected_from_session_date=str(context["capture_from"]),
                expected_through_session_date=str(context["session"]),
                required_tickers=context["tickers"],
            )
        )
    except Exception as exc:
        raise FeatureBasisProducerError(f"CA_CAPTURE_VERIFICATION_FAILED:{exc}") from exc
    if (
        phase_path.resolve() != manifest_path.resolve()
        or phase_sha != sha256_file(manifest_path)
        or from_date != str(context["capture_from"])
        or through_date != str(context["session"])
        or covered != set(context["tickers"])
    ):
        raise FeatureBasisProducerError("CA_CAPTURE_SCOPE_BINDING_INVALID")
    return phase, attestation


def _capture_ca_source(context: Mapping[str, Any], repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path, attestation_path = _capture_paths(context)
    if manifest_path.is_file() and attestation_path.is_file():
        return _verify_capture(context, manifest_path, attestation_path)
    if manifest_path.exists() or attestation_path.exists():
        raise FeatureBasisProducerError("CA_CAPTURE_PARTIAL_PUBLICATION")

    provider = os.getenv("E2E_CLOUD_PROVIDER_CHECKOUT", "").strip()
    if not provider:
        raise FeatureBasisProducerError("CA_CAPTURE_PROVIDER_CHECKOUT_MISSING")
    provider_root = Path(provider).expanduser().resolve()
    provider_project = provider_root / "python"
    uv_name = os.getenv("E2E_CLOUD_UV_COMMAND", "uv")
    uv = shutil.which(uv_name)
    capture_script = (repo_root / "scripts" / "capture_forward_ca_idx_bei.py").resolve()
    if not provider_project.is_dir() or uv is None or not capture_script.is_file():
        raise FeatureBasisProducerError("CA_CAPTURE_RUNTIME_CONFIGURATION_MISSING")

    capture_root = manifest_path.parent
    command = [
        uv,
        "run",
        "--project",
        str(provider_project),
        "python",
        str(capture_script),
        "--provider-checkout",
        str(provider_root),
        "--phase",
        CAPTURE_PHASE,
        "--from-session",
        str(context["capture_from"]),
        "--through-session",
        str(context["session"]),
        "--tickers",
        ",".join(context["tickers"]),
        "--output-dir",
        str(capture_root),
        "--attestation-output",
        str(attestation_path),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=900,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FeatureBasisProducerError("CA_CAPTURE_PROCESS_FAILED") from exc
    process_payload = {
        "schema_version": "idx_trade_v4_x1_feature_basis_capture_process_v1",
        "phase": CAPTURE_PHASE,
        "session_date": context["session"],
        "command": command,
        "returncode": completed.returncode,
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
        "outcome_accessed": False,
    }
    _write_json(capture_root / "capture_process.json", process_payload)
    if completed.returncode != 0:
        raise FeatureBasisProducerError(
            f"CA_CAPTURE_PROCESS_NONZERO:{completed.returncode}"
        )
    return _verify_capture(context, manifest_path, attestation_path)


def _dates(value: object) -> list[str]:
    found: list[str] = []
    for match in ISO_DATE_RE.finditer(str(value)):
        try:
            found.append(pd.Timestamp(match.group(1)).date().isoformat())
        except ValueError:
            continue
    return found


def _event_dates(
    ticker: str,
    *,
    phase: Mapping[str, Any],
    from_date: str,
    through_date: str,
) -> tuple[list[str], list[str]]:
    dates: set[str] = set()
    reasons: set[str] = set()
    for payload in forward_ca._artifact_payloads(phase, "issued_history"):
        rows = payload.get("data", []) if isinstance(payload, Mapping) else []
        if not isinstance(rows, list):
            raise FeatureBasisProducerError("CA_ISSUED_HISTORY_SCHEMA_INVALID")
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            if str(row.get("KodeEmiten") or "").strip().upper() != ticker:
                continue
            event_date = str(row.get("TanggalPencatatan") or "")[:10]
            if forward_ca._date_in_window(event_date, from_date, through_date, include_from=False):
                parsed = _dates(event_date)
                if parsed:
                    dates.update(parsed)
                    reasons.add(
                        f"ISSUED_HISTORY:{row.get('JenisTindakan') or 'UNKNOWN'}:{parsed[0]}"
                    )
    for leg in ("announcements", "calendar"):
        for payload in forward_ca._artifact_payloads(phase, leg):
            rows = payload.get("Items" if leg == "announcements" else "Results", []) if isinstance(payload, Mapping) else []
            if not isinstance(rows, list):
                raise FeatureBasisProducerError(f"CA_{leg.upper()}_SCHEMA_INVALID")
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                if not forward_ca._contains_ticker(row, ticker) or not forward_ca._contains_ca_keyword(row):
                    continue
                candidate_dates = [
                    value
                    for value in _dates(row)
                    if forward_ca._date_in_window(
                        value,
                        from_date,
                        through_date,
                        include_from=leg == "announcements",
                    )
                ]
                if candidate_dates:
                    dates.update(candidate_dates)
                    reasons.add(f"{leg.upper()}:{candidate_dates[0]}")
                else:
                    # A relevant CA record without an exact usable date is an
                    # unresolved transition, never a no-event certificate.
                    reasons.add(f"{leg.upper()}:DATE_UNRESOLVED")
    return sorted(dates), sorted(reasons)


def _child(
    root: Path,
    child_root: Path,
    *,
    evidence_id: str,
    kind: str,
    source_ref: str,
    payload: object,
    extension: str = ".json",
) -> dict[str, str]:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", evidence_id)
    path = child_root / f"{safe_id}{extension}"
    digest = _write_immutable(path, _json_bytes(payload, indent=2) if extension == ".json" else bytes(payload))
    return {
        "evidence_id": evidence_id,
        "kind": kind,
        "path": path.relative_to(root).as_posix(),
        "sha256": digest,
        "source_ref": source_ref,
    }


def _producer_claim(trusted: Mapping[str, Any] | None) -> dict[str, Any]:
    claim = dict(trusted or {})
    try:
        commit = subprocess.run(
            ["git", "-C", str(PRODUCER_IMPLEMENTATION_PATH.parents[1]), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip().lower()
    except (OSError, subprocess.CalledProcessError):
        commit = "0" * 40
    claim.setdefault("producer_id", gate.FEATURE_BASIS_PRODUCER_ID)
    claim.setdefault("implementation_repository", "samindriano/idx-trade")
    claim.setdefault("implementation_ref", "untrusted-local")
    claim.setdefault("implementation_commit", commit)
    claim.setdefault("policy_id", gate.FEATURE_BASIS_POLICY_ID)
    claim.setdefault("schema_version", gate.FEATURE_BASIS_SCHEMA_VERSION)
    claim["implementation_sha256"] = hashlib.sha256(PRODUCER_IMPLEMENTATION_PATH.read_bytes()).hexdigest()
    return claim


def _write_capture_failure(context: Mapping[str, Any], error: Exception) -> Path:
    root = Path(context["session_root"]) / FAILURE_DIRNAME
    path = root / f"{FAILURE_PREFIX}{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_{uuid4().hex[:8]}.json"
    _write_json(
        path,
        {
            "schema_version": "idx_trade_v4_x1_feature_basis_capture_failure_v1",
            "session_date": context["session"],
            "observed_at": context["observed"].isoformat(),
            "error_code": type(error).__name__.upper(),
            "error_message": str(error),
            "model_input_path": str(context["model_input_path"]),
            "model_input_sha256": sha256_file(context["model_input_path"]),
            "model_input_set_sha256": gate._set_hash(context["tickers"]),
            "outcome_accessed": False,
        },
    )
    return path


def _write_bundle(
    context: Mapping[str, Any],
    *,
    repo_root: Path,
    trusted: Mapping[str, Any] | None,
    phase: Mapping[str, Any] | None,
    attestation: Mapping[str, Any] | None,
    capture_error: str | None,
) -> dict[str, Any]:
    root = Path(context["session_root"])
    evidence_path = root / gate.FEATURE_BASIS_EVIDENCE_FILENAME
    manifest_path = root / gate.FEATURE_BASIS_MANIFEST_FILENAME
    if evidence_path.exists() or manifest_path.exists():
        if not evidence_path.is_file() or not manifest_path.is_file():
            raise FeatureBasisProducerError("FEATURE_BASIS_PARTIAL_PUBLICATION")
        return {
            "status": "REUSED",
            "evidence_path": str(evidence_path.resolve()),
            "manifest_path": str(manifest_path.resolve()),
        }

    child_root = root / "feature_basis_children"
    children: list[dict[str, str]] = []
    producer = _producer_claim(trusted)
    producer_id = "producer_implementation"
    producer_child = _child(
        root,
        child_root,
        evidence_id=producer_id,
        kind="producer_implementation",
        source_ref=(
            f"git://github.com/samindriano/idx-trade/{producer.get('implementation_commit', '')}"
            f":src/idx_trade/v4_x1_feature_basis_producer_v1.py"
        ),
        payload=PRODUCER_IMPLEMENTATION_PATH.read_bytes(),
        extension=".py",
    )
    children.append(producer_child)

    candidate_path = Path(context["candidate_path"])
    candidate_frame = pd.read_parquet(candidate_path)
    candidate_rows = {
        gate._safe_ticker(row.ticker): row
        for row in candidate_frame.itertuples(index=False)
    }
    if tuple(sorted(candidate_rows)) != tuple(context["tickers"]):
        raise FeatureBasisProducerError("CANDIDATE_OPEN_POPULATION_MISMATCH")

    ca_manifest_path = None
    ca_attestation_path = None
    if phase is not None and attestation is not None:
        ca_manifest_path, ca_attestation_path = _capture_paths(context)
        for evidence_id, path, kind, source_ref in (
            ("ca-phase-manifest", ca_manifest_path, "ca_phase_manifest", "idx://ca/phase-manifest"),
            ("ca-attestation", ca_attestation_path, "ca_attestation", "idx://ca/attestation"),
        ):
            children.append(
                {
                    "evidence_id": evidence_id,
                    "kind": kind,
                    "path": path.relative_to(root).as_posix(),
                    "sha256": sha256_file(path),
                    "source_ref": source_ref,
                }
            )
        for raw in phase.get("raw_artifacts", []):
            if not isinstance(raw, Mapping):
                continue
            raw_path = Path(str(raw.get("path") or ""))
            if not raw_path.is_absolute():
                raw_path = ca_manifest_path.parent / raw_path
            if raw_path.is_file():
                raw_id = f"ca-raw-{raw.get('name') or uuid4().hex}"
                children.append(
                    {
                        "evidence_id": raw_id,
                        "kind": "ca_raw_artifact",
                        "path": raw_path.relative_to(root).as_posix(),
                        "sha256": sha256_file(raw_path),
                        "source_ref": str(raw.get("endpoint") or "idx://ca/raw"),
                    }
                )

    children.append(
        {
            "evidence_id": "session-ohlcv",
            "kind": "session_ohlcv",
            "path": candidate_path.relative_to(root).as_posix(),
            "sha256": sha256_file(candidate_path),
            "source_ref": f"idx://forward/{context['session']}/session_ohlcv",
        }
    )

    authority_payload = {
        "name": "IDX_OFFICIAL_CORPORATE_ACTION_AUTHORITY",
        "ref": "https://www.idx.co.id",
        "session_date": context["session"],
        "ca_phase_manifest_sha256": sha256_file(ca_manifest_path) if ca_manifest_path else None,
        "ca_attestation_sha256": sha256_file(ca_attestation_path) if ca_attestation_path else None,
        "capture_error": capture_error,
    }
    authority_child = _child(
        root,
        child_root,
        evidence_id="authority",
        kind="authority",
        source_ref="https://www.idx.co.id",
        payload=authority_payload,
    )
    children.append(authority_child)

    attestation_children: dict[str, dict[str, str]] = {}
    for name, payload in (
        (
            "identity_attestation",
            {
                "status": "VERIFIED" if capture_error is None else "UNVERIFIED",
                "ref": f"idx://identity/{context['session']}",
                "session_date": context["session"],
                "model_input_sha256": sha256_file(context["model_input_path"]),
                "security_master_sha256": sha256_file(context["security_master_path"]),
            },
        ),
        (
            "calendar_attestation",
            {
                "status": "VERIFIED" if context["calendar_sources"] else "UNVERIFIED",
                "ref": f"idx://calendar/{context['session']}",
                "session_date": context["session"],
                "calendar_sources": context["calendar_sources"],
            },
        ),
        (
            "revision_attestation",
            {
                "status": "VERIFIED" if phase is not None else "UNVERIFIED",
                "ref": str(ca_manifest_path or "idx://ca/missing"),
                "session_date": context["session"],
                "phase_manifest_sha256": sha256_file(ca_manifest_path) if ca_manifest_path else None,
            },
        ),
        (
            "pit_attestation",
            {
                "status": "VERIFIED" if capture_error is None else "UNVERIFIED",
                "ref": str(ca_attestation_path or "idx://ca/missing"),
                "session_date": context["session"],
                "knowledge_at": context["observed"].astimezone(gate.JAKARTA).isoformat(),
                "attestation_sha256": sha256_file(ca_attestation_path) if ca_attestation_path else None,
            },
        ),
    ):
        child = _child(
            root,
            child_root,
            evidence_id=name,
            kind="attestation",
            source_ref=str(payload["ref"]),
            payload=payload,
        )
        children.append(child)
        attestation_children[name] = child

    field_children: dict[tuple[str, str], dict[str, str]] = {}
    open_children: dict[str, dict[str, str]] = {}
    records: list[dict[str, Any]] = []
    event_summary: dict[str, Any] = {}
    for ticker in context["tickers"]:
        row = candidate_rows[ticker]
        source = str(getattr(row, "source", "") or "").strip()
        source_ref = str(getattr(row, "source_ref", "") or "").strip()
        source_sha = str(getattr(row, "source_sha256", "") or "").lower().strip()
        retrieved = str(getattr(row, "observed_retrieved_at_utc", "") or "").strip()
        open_payload = {
            "ticker": ticker,
            "session_date": context["session"],
            "source": source,
            "source_ref": source_ref,
            "source_sha256": source_sha,
            "observed_retrieved_at_utc": retrieved,
            "session_ohlcv_sha256": sha256_file(candidate_path),
        }
        open_child = _child(
            root,
            child_root,
            evidence_id=f"open-source-{ticker}",
            kind="open_source",
            source_ref=source_ref or f"idx://open/{context['session']}/{ticker}",
            payload=open_payload,
        )
        children.append(open_child)
        open_children[ticker] = open_child

        dates: list[str] = []
        reasons: list[str] = []
        if phase is not None:
            dates, reasons = _event_dates(
                ticker,
                phase=phase,
                from_date=str(context["capture_from"]),
                through_date=str(context["session"]),
            )
        if capture_error is not None:
            state = "BASIS_UNKNOWN"
            field_state = "SOURCE_CAPTURE_UNRESOLVED"
        elif reasons and not dates:
            state = "BASIS_UNKNOWN"
            field_state = "CERTIFIED_SAME_BASIS"
        elif dates:
            state = "CERTIFIED_TRANSITION"
            field_state = "CERTIFIED_SAME_BASIS"
        else:
            state = "CERTIFIED_SAME_BASIS"
            field_state = "CERTIFIED_SAME_BASIS"
        event_summary[ticker] = {"state": state, "transition_dates": dates, "reasons": reasons}

        source_ids: dict[str, str] = {}
        source_hashes: dict[str, str] = {}
        source_refs: list[str] = []
        for field in gate.FEATURE_BASIS_FIELDS:
            field_ref = f"idx://feature-basis/{context['session']}/{ticker}/{field}"
            field_payload = {
                "ticker": ticker,
                "field": field,
                "session_date": context["session"],
                "state": field_state,
                "clean_panel_path": str(Path(context["panel_path"]).resolve()),
                "clean_panel_sha256": sha256_file(context["panel_path"]),
                "candidate_session_ohlcv_path": str(candidate_path),
                "candidate_session_ohlcv_sha256": sha256_file(candidate_path),
                "model_input_sha256": sha256_file(context["model_input_path"]),
                "ca_capture_manifest_sha256": sha256_file(ca_manifest_path) if ca_manifest_path else None,
                "source_ref": field_ref,
            }
            field_child = _child(
                root,
                child_root,
                evidence_id=f"field-{ticker}-{field}",
                kind="field_source",
                source_ref=field_ref,
                payload=field_payload,
            )
            children.append(field_child)
            field_children[(ticker, field)] = field_child
            source_ids[field] = field_child["evidence_id"]
            source_hashes[field] = field_child["sha256"]
            source_refs.append(field_ref)
        records.append(
            {
                "ticker": ticker,
                "state": state,
                "field_states": {field: field_state for field in gate.FEATURE_BASIS_FIELDS},
                "transition_dates": dates,
                "authority": {
                    "name": authority_payload["name"],
                    "ref": authority_child["source_ref"],
                    "sha256": authority_child["sha256"],
                    "evidence_id": authority_child["evidence_id"],
                },
                "source_refs": source_refs,
                "source_evidence_ids": source_ids,
                "source_hashes": source_hashes,
            }
        )

    model_input_set_sha = gate._set_hash(context["tickers"])
    open_bindings = {
        ticker: {
            "source": str(getattr(candidate_rows[ticker], "source", "") or "").strip(),
            "source_ref": str(getattr(candidate_rows[ticker], "source_ref", "") or "").strip(),
            "source_sha256": str(getattr(candidate_rows[ticker], "source_sha256", "") or "").lower().strip(),
            "observed_retrieved_at_utc": str(getattr(candidate_rows[ticker], "observed_retrieved_at_utc", "") or "").strip(),
            "open_evidence_sha256": open_children[ticker]["sha256"],
            "evidence_id": open_children[ticker]["evidence_id"],
        }
        for ticker in context["tickers"]
    }
    first_open = open_bindings[context["tickers"][0]]
    evidence: dict[str, Any] = {
        "schema_version": gate.FEATURE_BASIS_SCHEMA_VERSION,
        "policy_id": gate.FEATURE_BASIS_POLICY_ID,
        "status": "SOURCE_CAPTURE_UNRESOLVED" if capture_error else "PRODUCED",
        "session_date": context["session"],
        "knowledge_at": context["observed"].astimezone(gate.JAKARTA).isoformat(),
        "root_manifest_path": str(manifest_path.resolve()),
        "model_input_path": str(Path(context["model_input_path"]).resolve()),
        "model_input_sha256": sha256_file(context["model_input_path"]),
        "model_input_set_sha256": model_input_set_sha,
        "clean_panel_path": str(Path(context["panel_path"]).resolve()),
        "clean_panel_sha256": sha256_file(context["panel_path"]),
        "scorer_boundary": {
            "source": "MAX_DATE_FROM_CLEAN_PANEL",
            "historical_end": context["historical_end"],
            "clean_panel_sha256": sha256_file(context["panel_path"]),
        },
        "identity_attestation": {
            "status": "VERIFIED" if capture_error is None else "UNVERIFIED",
            "ref": attestation_children["identity_attestation"]["source_ref"],
            "sha256": attestation_children["identity_attestation"]["sha256"],
            "evidence_id": "identity_attestation",
        },
        "calendar_attestation": {
            "status": "VERIFIED" if capture_error is None else "UNVERIFIED",
            "ref": attestation_children["calendar_attestation"]["source_ref"],
            "sha256": attestation_children["calendar_attestation"]["sha256"],
            "evidence_id": "calendar_attestation",
        },
        "revision_attestation": {
            "status": "VERIFIED" if capture_error is None else "UNVERIFIED",
            "ref": attestation_children["revision_attestation"]["source_ref"],
            "sha256": attestation_children["revision_attestation"]["sha256"],
            "evidence_id": "revision_attestation",
        },
        "pit_attestation": {
            "status": "VERIFIED" if capture_error is None else "UNVERIFIED",
            "ref": attestation_children["pit_attestation"]["source_ref"],
            "sha256": attestation_children["pit_attestation"]["sha256"],
            "evidence_id": "pit_attestation",
            "knowledge_at": context["observed"].astimezone(gate.JAKARTA).isoformat(),
        },
        "geometry_open": {
            "status": "CERTIFIED_SAME_BASIS" if capture_error is None else "BASIS_UNKNOWN",
            "session_ohlcv_path": str(candidate_path),
            "session_ohlcv_sha256": sha256_file(candidate_path),
            "session_ohlcv_evidence_id": "session-ohlcv",
            "session_date": context["session"],
            "knowledge_at": context["observed"].astimezone(gate.JAKARTA).isoformat(),
            "ticker_set_sha256": model_input_set_sha,
            "open_source_identity": first_open,
            "open_source_bindings": open_bindings,
        },
        "window_contract": gate._feature_basis_window_contract_payload(),
        "window_contract_sha256": gate._feature_basis_window_contract_sha256(),
        "capture": {
            "phase": CAPTURE_PHASE,
            "from_session_date": context["capture_from"],
            "through_session_date": context["session"],
            "full_population": True,
            "required_tickers": list(context["tickers"]),
            "phase_manifest_path": str(ca_manifest_path) if ca_manifest_path else None,
            "phase_manifest_sha256": sha256_file(ca_manifest_path) if ca_manifest_path else None,
            "attestation_path": str(ca_attestation_path) if ca_attestation_path else None,
            "attestation_sha256": sha256_file(ca_attestation_path) if ca_attestation_path else None,
            "error": capture_error,
        },
        "records": records,
        "event_summary": event_summary,
        "guards": {"outcome_accessed": False, "provider_calls_from_scorer": False},
    }
    manifest: dict[str, Any] = {
        "schema_version": gate.FEATURE_BASIS_MANIFEST_SCHEMA_VERSION,
        "policy_id": gate.FEATURE_BASIS_POLICY_ID,
        "evidence_path": evidence_path.relative_to(root).as_posix(),
        "evidence_sha256": "0" * 64,
        "producer": {
            "producer_id": producer.get("producer_id"),
            "implementation_repository": producer.get("implementation_repository"),
            "implementation_ref": producer.get("implementation_ref"),
            "implementation_commit": producer.get("implementation_commit"),
            "implementation_sha256": producer_child["sha256"],
            "implementation_evidence_id": producer_id,
        },
        "children": children,
    }
    manifest["manifest_id"] = gate._feature_basis_manifest_identity(manifest)
    evidence["root_manifest_id"] = manifest["manifest_id"]
    _write_json(evidence_path, evidence)
    manifest["evidence_sha256"] = sha256_file(evidence_path)
    _write_json(manifest_path, manifest)
    return {
        "status": "SOURCE_CAPTURE_UNRESOLVED" if capture_error else "PRODUCED",
        "evidence_path": str(evidence_path.resolve()),
        "evidence_sha256": sha256_file(evidence_path),
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": sha256_file(manifest_path),
        "population": len(context["tickers"]),
        "capture_error": capture_error,
    }


def produce_feature_basis_evidence(
    runtime_root: str | Path,
    *,
    clean_panel: str | Path,
    repo_root: str | Path,
    observed_by: str,
    trusted_producer_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Capture and publish one immutable same-session basis bundle.

    A source failure is retained as a separate immutable attempt record and is
    returned to the gate as an unresolved/missing-certificate condition.  The
    canonical certificate is never fabricated from a failed or partial source.
    """

    context = _candidate_context(
        runtime_root, clean_panel=clean_panel, observed_by=observed_by
    )
    root = Path(context["session_root"])
    evidence_path = root / gate.FEATURE_BASIS_EVIDENCE_FILENAME
    manifest_path = root / gate.FEATURE_BASIS_MANIFEST_FILENAME
    if evidence_path.is_file() and manifest_path.is_file():
        return {
            "status": "REUSED",
            "session_date": context["session"],
            "evidence_path": str(evidence_path),
            "manifest_path": str(manifest_path),
            "evidence_sha256": sha256_file(evidence_path),
            "manifest_sha256": sha256_file(manifest_path),
            "population": len(context["tickers"]),
        }
    if evidence_path.exists() or manifest_path.exists():
        raise FeatureBasisProducerError("FEATURE_BASIS_PARTIAL_PUBLICATION")
    try:
        phase, attestation = _capture_ca_source(context, Path(repo_root).expanduser().resolve())
    except Exception as exc:
        failure_path = _write_capture_failure(context, exc)
        return {
            "status": "SOURCE_CAPTURE_UNRESOLVED",
            "session_date": context["session"],
            "capture_failure_path": str(failure_path),
            "capture_error": str(exc),
            "population": len(context["tickers"]),
        }
    return _write_bundle(
        context,
        repo_root=Path(repo_root).expanduser().resolve(),
        trusted=trusted_producer_contract,
        phase=phase,
        attestation=attestation,
        capture_error=None,
    )


__all__ = [
    "FeatureBasisProducerError",
    "load_trusted_producer_contract",
    "produce_feature_basis_evidence",
]
