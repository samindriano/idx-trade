"""Deterministic controller boundary for the live PAPER E2E runtime.

The controller is deliberately a consumer of the existing forward EOD, X1,
official Open, and dividend runtimes.  It does not create a provider, score,
ledger, or outcome path.  Until the existing V1.2 CA acquisition outputs are
present and explicitly configured, it records a fail-closed waiting state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from .e2e_operational_guard_v1 import (
    E2EOperationalGuardError,
    JAKARTA,
    attest_deployment,
    exclusive_run_lock,
    load_session_dates,
    require_phase_window,
    write_phase_attestation,
    write_status_atomic,
)
from .e2e_paper_orchestration_v1 import (
    bootstrap_t0,
    derive_required_execution_tickers,
    load_score_manifest,
)
from .forward_dividend_orchestration_v1 import load_journal_document
from .v4_x1_execution_v1_verify import verify_eod_execution_inputs


@dataclass(frozen=True)
class OperationalControllerConfig:
    runtime_root: Path
    forward_runtime_root: Path
    calendar_path: Path
    official_open_root: Path
    repo_root: Path
    expected_branch: str
    expected_commit: str
    provider_checkout: Path | None = None
    provider_expected_commit: str | None = None
    uv_exe: Path | None = None
    python_exe: Path | None = None
    ca_attestation_path: Path | None = None
    ca_attestation_sha256: str | None = None
    initial_journal_path: Path | None = None
    initial_journal_sha256: str | None = None
    preopen_capture_start: time = time(8, 30)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise E2EOperationalGuardError("E2E_OPERATIONAL_UPSTREAM_POINTER_MISSING")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_UPSTREAM_POINTER_INVALID") from exc
    if not isinstance(value, dict):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_UPSTREAM_POINTER_INVALID")
    return value


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise E2EOperationalGuardError("E2E_OPERATIONAL_ARTIFACT_MISSING")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    ).hexdigest()


def _pipeline_pointer(config: OperationalControllerConfig) -> dict[str, Any]:
    pointer = _read_json(
        config.forward_runtime_root
        / "forward_monitoring"
        / "eod_automation"
        / "v4_x1_pipeline"
        / "latest.json"
    )
    run_log_path = Path(str(pointer.get("run_log_path") or "")).expanduser().resolve()
    declared_run_log_sha = str(pointer.get("run_log_sha256") or "")
    pipeline_root = (
        config.forward_runtime_root
        / "forward_monitoring"
        / "eod_automation"
        / "v4_x1_pipeline"
    ).resolve()
    if (
        run_log_path.parent != (pipeline_root / "runs").resolve()
        or not run_log_path.is_file()
        or _sha256(run_log_path) != declared_run_log_sha
    ):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_UPSTREAM_LOG_HASH_MISMATCH")
    return pointer


def _verify_score_pointer(
    pointer: dict[str, Any],
    session: str,
    *,
    expected_forward_root: Path | None = None,
) -> dict[str, Any]:
    score = pointer.get("x1_score")
    if not isinstance(score, dict):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_SCORE_POINTER_MISSING")
    path = Path(str(score.get("manifest_path") or "")).expanduser().resolve()
    model_root = None
    if expected_forward_root is not None:
        model_root = (
            Path(expected_forward_root).expanduser().resolve()
            / "forward_monitoring"
            / "model_runs"
        )
        if model_root not in path.parents:
            raise E2EOperationalGuardError("E2E_OPERATIONAL_SCORE_MANIFEST_ROOT_MISMATCH")
    if not path.is_file() or _sha256(path) != str(score.get("manifest_sha256") or ""):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_SCORE_MANIFEST_HASH_MISMATCH")
    artifact_value = score.get("artifact_path")
    if artifact_value is not None:
        artifact = Path(str(artifact_value)).expanduser().resolve()
        if path.parent not in artifact.parents or not artifact.is_file() or _sha256(artifact) != str(score.get("artifact_sha256") or ""):
            raise E2EOperationalGuardError("E2E_OPERATIONAL_SCORE_ARTIFACT_HASH_MISMATCH")
    if str(score.get("session_date") or "") != session:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_SCORE_SESSION_MISMATCH")
    return score


def _write_json_immutable(path: Path, payload: Mapping[str, Any]) -> str:
    target = path.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(dict(payload), sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if target.exists():
        if target.read_bytes() != encoded:
            raise E2EOperationalGuardError("E2E_OPERATIONAL_IMMUTABLE_ARTIFACT_CONFLICT")
        return hashlib.sha256(encoded).hexdigest()
    temporary = target.with_name(f".{target.name}.{hashlib.sha256(encoded).hexdigest()[:12]}.tmp")
    temporary.write_bytes(encoded)
    try:
        if target.exists():
            if target.read_bytes() != encoded:
                raise E2EOperationalGuardError("E2E_OPERATIONAL_IMMUTABLE_ARTIFACT_CONFLICT")
        else:
            temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(encoded).hexdigest()


def _config_missing(config: OperationalControllerConfig) -> str | None:
    required = (
        ("provider_checkout", config.provider_checkout),
        ("provider_expected_commit", config.provider_expected_commit),
        ("uv_exe", config.uv_exe),
        ("python_exe", config.python_exe),
        ("ca_attestation_path", config.ca_attestation_path),
        ("ca_attestation_sha256", config.ca_attestation_sha256),
    )
    missing = [name for name, value in required if not value]
    if missing:
        return "MISSING_OPERATIONAL_CONFIG:" + ",".join(missing)
    provider = Path(config.provider_checkout).expanduser().resolve()
    if not (provider / "python").is_dir():
        return "PROVIDER_PROJECT_MISSING"
    for name, value in (("uv_exe", config.uv_exe), ("python_exe", config.python_exe)):
        if not Path(value).expanduser().resolve().is_file():
            return "OPERATIONAL_EXECUTABLE_MISSING:" + name
    attestation = Path(config.ca_attestation_path).expanduser().resolve()
    if not attestation.is_file() or _sha256(attestation) != str(config.ca_attestation_sha256).lower():
        return "CA_ATTESTATION_HASH_MISMATCH"
    if config.initial_journal_path is not None:
        if not config.initial_journal_sha256:
            return "INITIAL_JOURNAL_SHA_MISSING"
        initial = Path(config.initial_journal_path).expanduser().resolve()
        if not initial.is_file() or _sha256(initial) != str(config.initial_journal_sha256).lower():
            return "INITIAL_JOURNAL_HASH_MISMATCH"
    try:
        actual = subprocess.run(
            ["git", "-C", str(provider), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip().lower()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise E2EOperationalGuardError("E2E_PROVIDER_COMMIT_ATTESTATION_FAILED") from exc
    if actual != str(config.provider_expected_commit).strip().lower():
        return "PROVIDER_COMMIT_MISMATCH"
    try:
        dirty = subprocess.run(
            ["git", "-C", str(provider), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise E2EOperationalGuardError("E2E_PROVIDER_WORKTREE_ATTESTATION_FAILED") from exc
    if dirty:
        return "PROVIDER_WORKTREE_DIRTY"
    return None


def _session_manifest(config: OperationalControllerConfig, session: str) -> dict[str, Any]:
    manifest_path = (
        config.forward_runtime_root
        / "forward_monitoring"
        / "sessions"
        / session
        / "manifest.json"
    )
    manifest = _read_json(manifest_path)
    if (
        manifest.get("status") != "DATA_READY"
        or manifest.get("session_date") != session
        or manifest.get("forward_outcomes_accessed") is not False
    ):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_EOD_MANIFEST_INVALID")
    calendar_path = Path(str(manifest.get("calendar_path") or "")).expanduser().resolve()
    if calendar_path != config.calendar_path.expanduser().resolve():
        raise E2EOperationalGuardError("E2E_OPERATIONAL_EOD_CALENDAR_PATH_MISMATCH")
    if _sha256(calendar_path) != str(manifest.get("calendar_sha256") or ""):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_EOD_CALENDAR_HASH_MISMATCH")
    session_root = manifest_path.parent.resolve()
    for path_key, sha_key in (
        ("session_ohlcv_path", "session_ohlcv_sha256"),
        ("snapshot_path", "snapshot_sha256"),
    ):
        path = Path(str(manifest.get(path_key) or "")).expanduser().resolve()
        if session_root not in path.parents or not path.is_file() or _sha256(path) != str(manifest.get(sha_key) or ""):
            raise E2EOperationalGuardError("E2E_OPERATIONAL_EOD_ARTIFACT_HASH_MISMATCH:" + path_key)
    return {
        "manifest_path": manifest_path.resolve(),
        "session_ohlcv": Path(str(manifest["session_ohlcv_path"])).expanduser().resolve(),
        "model_input": Path(str(manifest["snapshot_path"])).expanduser().resolve(),
        "calendar": calendar_path,
    }


def _previous_score_manifest(config: OperationalControllerConfig, current_session: str) -> Path | None:
    meta_dir = config.runtime_root / "state" / "decisions"
    rows: list[tuple[str, Path, str]] = []
    if not meta_dir.is_dir():
        return None
    for path in sorted(meta_dir.glob("*.json")):
        payload = _read_json(path)
        body = dict(payload)
        declared = str(body.pop("payload_sha256") or "")
        if not declared or _canonical_hash(body) != declared:
            raise E2EOperationalGuardError("E2E_OPERATIONAL_META_HASH_MISMATCH")
        session = str(payload.get("last_score_session_date") or "")
        if session and session < current_session:
            rows.append((
                session,
                Path(str(payload.get("last_score_manifest_path") or "")).expanduser().resolve(),
                str(payload.get("last_score_manifest_sha256") or "").lower(),
            ))
    if not rows:
        return None
    latest_session = max(session for session, _, _ in rows)
    latest = [(path, sha) for session, path, sha in rows if session == latest_session]
    if len({(str(path), sha) for path, sha in latest}) != 1:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_PREVIOUS_SCORE_AMBIGUOUS")
    path, expected_sha = latest[0]
    if not path.is_file():
        raise E2EOperationalGuardError("E2E_OPERATIONAL_PREVIOUS_SCORE_MISSING")
    verified = load_score_manifest(path)
    if not expected_sha or verified.manifest_sha256 != expected_sha:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_PREVIOUS_SCORE_SHA_MISMATCH")
    return path


def _process_log(config: OperationalControllerConfig, label: str, command: Sequence[str], proc: subprocess.CompletedProcess[str], started: datetime, finished: datetime) -> str:
    safe = {
        "schema_version": "idx_trade_e2e_operational_process_v1",
        "label": label,
        "command": [str(value) for value in command],
        "returncode": proc.returncode,
        "started_at_jakarta": started.isoformat(),
        "finished_at_jakarta": finished.isoformat(),
        "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(proc.stderr.encode()).hexdigest(),
    }
    target = config.runtime_root / "operational" / "processes" / f"{finished.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_{label}.json"
    return _write_json_immutable(target, safe)


def _run_child(config: OperationalControllerConfig, label: str, command: list[str], *, timeout_seconds: int = 900) -> None:
    started = datetime.now(tz=JAKARTA)
    try:
        proc = subprocess.run(
            command,
            cwd=config.repo_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CHILD_PROCESS_FAILED:" + label) from exc
    finished = datetime.now(tz=JAKARTA)
    _process_log(config, label, command, proc, started, finished)
    if proc.returncode != 0:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CHILD_PROCESS_FAILED:" + label)


def _journal_paths(config: OperationalControllerConfig, session: str, phase: str) -> tuple[Path, Path]:
    stem = f"{session}_{phase}"
    return (
        config.runtime_root / "dividend_acquisition_v1" / "batches" / stem,
        config.runtime_root / "dividend_acquisition_v1" / "journals" / f"{stem}.json",
    )


def _phase_sidecar_path(config: OperationalControllerConfig, session: str, phase: str) -> Path:
    return config.runtime_root / "operational" / "ca_phase" / f"{session}_{phase}.json"


def _verify_phase_sidecar(config: OperationalControllerConfig, session: str, phase: str) -> dict[str, Any]:
    path = _phase_sidecar_path(config, session, phase)
    payload = _read_json(path)
    body = dict(payload)
    declared = str(body.pop("payload_sha256") or "")
    if not declared or _canonical_hash(body) != declared:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_SIDECAR_HASH_MISMATCH")
    batch, journal = _journal_paths(config, session, phase)
    if (
        payload.get("phase") != phase
        or payload.get("session_date") != session
        or Path(str(payload.get("journal_path") or "")).expanduser().resolve() != journal.resolve()
        or not journal.is_file()
        or _sha256(journal) != str(payload.get("journal_sha256") or "")
        or not batch.is_dir()
        or not (batch / "BATCH_MANIFEST.json").is_file()
    ):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_SIDECAR_PARENT_MISMATCH")
    journal_doc = load_journal_document(journal)
    batch_manifest = _read_json(batch / "BATCH_MANIFEST.json")
    batch_body = dict(batch_manifest)
    batch_declared = str(batch_body.pop("batch_payload_sha256") or "")
    if (
        batch_manifest.get("status") != "COMPLETE"
        or not batch_declared
        or _canonical_hash(batch_body) != batch_declared
        or Path(str(batch_manifest.get("batch_root") or "")).expanduser().resolve() != batch.resolve()
        or Path(str(batch_manifest.get("journal_target") or "")).expanduser().resolve() != journal.resolve()
        or str(batch_manifest.get("journal_sha256") or "") != journal_doc.journal_sha256
    ):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CA_BATCH_MANIFEST_INVALID")
    if (
        str(payload.get("provider_commit") or "").lower()
        != str(config.provider_expected_commit or "").lower()
        or Path(str(payload.get("ca_attestation_path") or "")).expanduser().resolve()
        != Path(config.ca_attestation_path).expanduser().resolve()
        or str(payload.get("ca_attestation_sha256") or "").lower()
        != str(config.ca_attestation_sha256 or "").lower()
    ):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_SIDECAR_CONFIG_MISMATCH")
    return payload


def _ensure_ca_phase(
    config: OperationalControllerConfig,
    *,
    session: str,
    phase: str,
    required_tickers: Sequence[str],
    now: datetime,
) -> str:
    batch, journal = _journal_paths(config, session, phase)
    sidecar = _phase_sidecar_path(config, session, phase)
    if sidecar.is_file():
        payload = _verify_phase_sidecar(config, session, phase)
        expected_tickers = sorted({str(value).strip().upper() for value in required_tickers})
        if list(payload.get("required_tickers") or []) != expected_tickers:
            raise E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_TICKER_SCOPE_CHANGED")
        if phase == "PREOPEN" and str(payload.get("finished_at_jakarta") or ""):
            finished = datetime.fromisoformat(str(payload["finished_at_jakarta"]))
            if finished.astimezone(JAKARTA).time() >= time(9, 2):
                raise E2EOperationalGuardError("E2E_OPERATIONAL_PREOPEN_CA_CAPTURE_AFTER_CUTOFF")
        return "REUSED"
    if journal.exists() or batch.exists():
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_PARTIAL")
    if phase == "PREOPEN":
        if now.time() < config.preopen_capture_start:
            return "WAITING_PREOPEN_CAPTURE_WINDOW"
        if now.time() >= time(9, 2):
            return "MISSED_PREOPEN_CA_CAPTURE"
    missing = _config_missing(config)
    if missing:
        raise E2EOperationalGuardError(missing)
    prior: Path | None = None
    if phase == "POST_EOD":
        prior = config.initial_journal_path
    else:
        _, post_journal = _journal_paths(config, session, "POST_EOD")
        if not post_journal.is_file():
            raise E2EOperationalGuardError("E2E_PREOPEN_POST_EOD_JOURNAL_MISSING")
        prior = post_journal
    command = [
        str(Path(config.python_exe).expanduser().resolve()),
        str((config.repo_root / "scripts" / "run_forward_dividend_acquisition_batch_v1.py").resolve()),
        "--provider-checkout", str(Path(config.provider_checkout).expanduser().resolve()),
        "--runtime-root", str(config.runtime_root.expanduser().resolve()),
        "--as-of-date", session,
        "--capture-phase", phase,
        "--uv-exe", str(Path(config.uv_exe).expanduser().resolve()),
        "--python-exe", str(Path(config.python_exe).expanduser().resolve()),
    ]
    for ticker in sorted({str(value).strip().upper() for value in required_tickers}):
        command.extend(("--ticker", ticker))
    if prior is not None:
        command.extend(("--prior-journal", str(prior.expanduser().resolve())))
    started = datetime.now(tz=JAKARTA)
    _run_child(config, f"ca_{phase.lower()}", command)
    finished = datetime.now(tz=JAKARTA)
    if not journal.is_file() or not batch.is_dir():
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_OUTPUT_MISSING")
    journal_doc = load_journal_document(journal)
    if journal_doc.journal.as_of_date != session or journal_doc.journal.capture_phase != phase:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_OUTPUT_MISMATCH")
    body: dict[str, Any] = {
        "schema_version": "idx_trade_e2e_operational_ca_phase_v1",
        "phase": phase,
        "session_date": session,
        "started_at_jakarta": started.isoformat(),
        "finished_at_jakarta": finished.isoformat(),
        "required_tickers": sorted({str(value).strip().upper() for value in required_tickers}),
        "journal_path": str(journal.resolve()),
        "journal_sha256": _sha256(journal),
        "batch_root": str(batch.resolve()),
        "provider_commit": str(config.provider_expected_commit).lower(),
        "ca_attestation_path": str(Path(config.ca_attestation_path).expanduser().resolve()),
        "ca_attestation_sha256": str(config.ca_attestation_sha256).lower(),
    }
    body["payload_sha256"] = _canonical_hash(body)
    _write_json_immutable(sidecar, body)
    if phase == "PREOPEN" and finished.time() >= time(9, 2):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_PREOPEN_CA_CAPTURE_AFTER_CUTOFF")
    return "CAPTURED"


def _status_path(config: OperationalControllerConfig) -> Path:
    return config.runtime_root / "operational" / "latest.json"


def _prepared_for_session(config: OperationalControllerConfig, session: str) -> list[Path]:
    prepared_dir = config.runtime_root / "prepared"
    candidates: list[Path] = []
    for path in sorted(prepared_dir.glob("*.json")) if prepared_dir.is_dir() else ():
        try:
            payload = _read_json(path)
        except E2EOperationalGuardError:
            continue
        if str(payload.get("schema_version") or "") != "idx_trade_e2e_paper_prepared_execution_v1":
            continue
        declared = str(payload.get("payload_sha256") or "")
        body = dict(payload)
        body.pop("payload_sha256", None)
        if not declared or _canonical_hash(body) != declared:
            continue
        if str(payload.get("execution_session_date") or "") != session:
            continue
        eod = payload.get("eod_inputs")
        if not isinstance(eod, dict):
            continue
        valid_refs = True
        for key in ("ohlcv", "model_input", "calendar"):
            ref = eod.get(key)
            if not isinstance(ref, dict):
                valid_refs = False
                break
            ref_path = Path(str(ref.get("path") or "")).expanduser().resolve()
            if not ref_path.is_file() or _sha256(ref_path) != str(ref.get("sha256") or ""):
                valid_refs = False
                break
        if valid_refs:
            candidates.append(path)
    return candidates


def _run_operational_cycle_legacy(
    config: OperationalControllerConfig,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run one no-backfill controller pass and persist its operational state."""

    deployment = attest_deployment(
        config.repo_root,
        expected_branch=config.expected_branch,
        expected_commit=config.expected_commit,
    )
    config.runtime_root.mkdir(parents=True, exist_ok=True)
    lock_path = config.runtime_root / "operational" / "controller.lock"
    with exclusive_run_lock(lock_path):
        current = (now or datetime.now(tz=JAKARTA)).astimezone(JAKARTA)
        today = current.date().isoformat()
        status: dict[str, Any] = {
            "controller_status": "RUNNING",
            "started_at_jakarta": current.isoformat(),
            "decision_session_date": None,
            "execution_session_date": None,
            "deployment": {
                "repo_root": str(deployment.repo_root),
                "branch": deployment.branch,
                "head": deployment.head,
                "expected_commit": deployment.expected_commit,
                "clean": deployment.clean,
            },
            "provider_calls": False,
            "model_refit": False,
            "model_rescore": False,
            "outcome_access": False,
        }
        try:
            sessions = load_session_dates(config.calendar_path)
            status["calendar_path"] = str(config.calendar_path.resolve())
            status["calendar_session_count"] = len(sessions)
            if today not in sessions:
                status.update({
                    "controller_status": "WEEKEND_OR_HOLIDAY_NOOP",
                    "reason": "NO_OFFICIAL_SESSION_TODAY",
                })
            elif current.time().hour < 9 or (
                current.time().hour == 9 and current.time().minute < 2
            ):
                status.update({
                    "controller_status": "WAITING_PREOPEN_WINDOW",
                    "reason": "PREOPEN_NOT_OPEN",
                    "execution_session_date": today,
                })
            elif current.time() <= time(9, 22, 59):
                prepared = _prepared_for_session(config, today)
                status["execution_session_date"] = today
                if len(prepared) > 1:
                    status.update({
                        "controller_status": "FAIL_CLOSED_AMBIGUOUS_PREPARED_PARENT",
                        "prepared_candidates": [str(p) for p in prepared],
                    })
                elif not prepared:
                    status.update({
                        "controller_status": "WAITING_PREPARED_EXECUTION",
                        "reason": "NO_PREPARED_EXECUTION_FOR_TODAY",
                    })
                else:
                    open_manifest = config.official_open_root / today / "manifest.json"
                    status["prepared_path"] = str(prepared[0])
                    if not open_manifest.is_file():
                        status.update({
                            "controller_status": "WAITING_OFFICIAL_OPEN",
                            "reason": "CERTIFIED_OPEN_MANIFEST_MISSING",
                        })
                    else:
                        status.update({
                            "controller_status": "WAITING_CA_RECONCILIATION",
                            "reason": "CA_PREOPEN_INPUT_NOT_CONFIGURED",
                            "open_manifest_path": str(open_manifest),
                        })
            elif current.time() < time(18, 0):
                status.update({
                    "controller_status": "PREOPEN_WINDOW_MISSED_NO_EXECUTION",
                    "reason": "NO_RETROACTIVE_PAPER_EXECUTION",
                    "execution_session_date": today,
                })
            else:
                pointer = _pipeline_pointer(config)
                score = _verify_score_pointer(
                    pointer,
                    today,
                    expected_forward_root=config.forward_runtime_root,
                )
                eod = pointer.get("eod") if isinstance(pointer.get("eod"), dict) else {}
                status["upstream_pointer_path"] = str(
                    config.forward_runtime_root
                    / "forward_monitoring"
                    / "eod_automation"
                    / "v4_x1_pipeline"
                    / "latest.json"
                )
                if (
                    eod.get("status") != "NO_MISSING_SESSION"
                    or score.get("status") not in {"V4_X1_SCORE_ALREADY_DONE_VERIFIED", "V4_X1_PROSPECTIVE_SCORE_DONE"}
                    or str(score.get("session_date") or "") != today
                ):
                    status.update({
                        "controller_status": "WAITING_UPSTREAM_EOD_SCORE",
                        "reason": "CANONICAL_EOD_OR_SAME_DAY_SCORE_NOT_READY",
                    })
                else:
                    status["calendar_sha256"] = _sha256(config.calendar_path)
                    status.update({
                        "controller_status": "WAITING_CA_RECONCILIATION",
                        "reason": "CA_POST_EOD_INPUT_NOT_CONFIGURED",
                        "decision_session_date": today,
                        "score_manifest_path": score.get("manifest_path"),
                        "score_manifest_sha256": score.get("manifest_sha256"),
                    })
            status["finished_at_jakarta"] = datetime.now(tz=JAKARTA).isoformat()
            status["status_sha256"] = write_status_atomic(_status_path(config), status)
            return status
        except Exception as error:
            status.update({
                "controller_status": "FAIL_CLOSED",
                "error_code": type(error).__name__.upper(),
                "error_message": str(error),
                "finished_at_jakarta": datetime.now(tz=JAKARTA).isoformat(),
            })
            status["status_sha256"] = write_status_atomic(_status_path(config), status)
            raise


def run_operational_cycle(
    config: OperationalControllerConfig,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run one controller-owned, no-backfill PAPER operational pass.

    The controller is the only production path that can issue a phase
    attestation.  Existing CA acquisition and guarded POST_EOD/PREOPEN
    consumers remain the implementation of each phase.
    """

    deployment = attest_deployment(
        config.repo_root,
        expected_branch=config.expected_branch,
        expected_commit=config.expected_commit,
    )
    config.runtime_root.mkdir(parents=True, exist_ok=True)
    lock_path = config.runtime_root / "operational" / "controller.lock"
    with exclusive_run_lock(lock_path):
        current = (now or datetime.now(tz=JAKARTA)).astimezone(JAKARTA)
        today = current.date().isoformat()
        status: dict[str, Any] = {
            "controller_status": "RUNNING",
            "started_at_jakarta": current.isoformat(),
            "decision_session_date": None,
            "execution_session_date": None,
            "deployment": {
                "repo_root": str(deployment.repo_root),
                "branch": deployment.branch,
                "head": deployment.head,
                "expected_commit": deployment.expected_commit,
                "clean": deployment.clean,
            },
            "provider_calls": False,
            "model_refit": False,
            "model_rescore": False,
            "outcome_access": False,
        }

        def finish(**updates: Any) -> dict[str, Any]:
            status.update(updates)
            status["finished_at_jakarta"] = datetime.now(tz=JAKARTA).isoformat()
            status["status_sha256"] = write_status_atomic(_status_path(config), status)
            return status

        try:
            sessions = load_session_dates(config.calendar_path)
            status["calendar_path"] = str(config.calendar_path.resolve())
            status["calendar_session_count"] = len(sessions)
            if today not in sessions:
                return finish(
                    controller_status="WEEKEND_OR_HOLIDAY_NOOP",
                    reason="NO_OFFICIAL_SESSION_TODAY",
                )

            prepared = _prepared_for_session(config, today)
            status["execution_session_date"] = today
            if current.time() < time(9, 2):
                if len(prepared) > 1:
                    return finish(
                        controller_status="FAIL_CLOSED_AMBIGUOUS_PREPARED_PARENT",
                        prepared_candidates=[str(path) for path in prepared],
                    )
                if not prepared:
                    return finish(
                        controller_status="WAITING_PREPARED_EXECUTION",
                        reason="NO_PREPARED_EXECUTION_FOR_TODAY",
                    )
                if current.time() < config.preopen_capture_start:
                    return finish(
                        controller_status="WAITING_PREOPEN_CAPTURE_WINDOW",
                        reason="PREOPEN_CA_CAPTURE_NOT_OPEN",
                        prepared_path=str(prepared[0]),
                    )
                missing = _config_missing(config)
                if missing:
                    return finish(
                        controller_status="WAITING_OPERATIONAL_CONFIGURATION",
                        reason=missing,
                        prepared_path=str(prepared[0]),
                    )
                payload = _read_json(prepared[0])
                ca_status = _ensure_ca_phase(
                    config,
                    session=today,
                    phase="PREOPEN",
                    required_tickers=tuple(payload.get("required_tickers") or ()),
                    now=current,
                )
                return finish(
                    controller_status="PREOPEN_CA_READY" if ca_status in {"CAPTURED", "REUSED"} else ca_status,
                    phase="PREOPEN",
                    ca_phase_status=ca_status,
                    provider_calls=ca_status == "CAPTURED",
                    prepared_path=str(prepared[0]),
                )

            if current.time() <= time(9, 22, 59):
                if len(prepared) > 1:
                    return finish(
                        controller_status="FAIL_CLOSED_AMBIGUOUS_PREPARED_PARENT",
                        prepared_candidates=[str(path) for path in prepared],
                    )
                if not prepared:
                    return finish(
                        controller_status="WAITING_PREPARED_EXECUTION",
                        reason="NO_PREPARED_EXECUTION_FOR_TODAY",
                    )
                missing = _config_missing(config)
                if missing:
                    return finish(
                        controller_status="WAITING_OPERATIONAL_CONFIGURATION",
                        reason=missing,
                        prepared_path=str(prepared[0]),
                    )
                try:
                    sidecar = _verify_phase_sidecar(config, today, "PREOPEN")
                except E2EOperationalGuardError as exc:
                    return finish(
                        controller_status="WAITING_PREOPEN_CA_CAPTURE",
                        reason=str(exc),
                        prepared_path=str(prepared[0]),
                    )
                open_manifest = config.official_open_root / today / "manifest.json"
                if not open_manifest.is_file():
                    return finish(
                        controller_status="WAITING_OFFICIAL_OPEN",
                        reason="CERTIFIED_OPEN_MANIFEST_MISSING",
                        prepared_path=str(prepared[0]),
                        ca_phase_sidecar=str(_phase_sidecar_path(config, today, "PREOPEN")),
                    )
                payload = _read_json(prepared[0])
                current_score_path = Path(str(payload["current_score"]["manifest_path"])).expanduser().resolve()
                previous_ref = payload.get("previous_score")
                previous_score_path = None if not isinstance(previous_ref, Mapping) else Path(str(previous_ref["manifest_path"])).expanduser().resolve()
                eod = payload["eod_inputs"]
                before_execution = config.runtime_root / "executions" / f"{today}.json"
                was_complete = before_execution.is_file()
                phase_attestation_path, _ = write_phase_attestation(
                    config.runtime_root,
                    phase="PREOPEN",
                    session_date=today,
                    expected_branch=config.expected_branch,
                    expected_commit=config.expected_commit,
                    issued_at=current,
                )
                command = [
                    str(Path(config.python_exe).expanduser().resolve()),
                    str((config.repo_root / "scripts" / "run_e2e_paper_preopen_v1.py").resolve()),
                    "--runtime-root", str(config.runtime_root.resolve()),
                    "--prepared", str(prepared[0].resolve()),
                    "--current-score-manifest", str(current_score_path),
                    "--session-ohlcv", str(Path(str(eod["ohlcv"]["path"])).expanduser().resolve()),
                    "--model-input", str(Path(str(eod["model_input"]["path"])).expanduser().resolve()),
                    "--calendar", str(Path(str(eod["calendar"]["path"])).expanduser().resolve()),
                    "--open-manifest", str(open_manifest.resolve()),
                    "--ca-attestation", str(Path(config.ca_attestation_path).expanduser().resolve()),
                    "--expected-branch", config.expected_branch,
                    "--expected-commit", config.expected_commit,
                    "--phase-attestation", str(phase_attestation_path.resolve()),
                    "--ca-journal", str(_journal_paths(config, today, "PREOPEN")[1].resolve()),
                ]
                if previous_score_path is not None:
                    command.extend(("--previous-score-manifest", str(previous_score_path)))
                _run_child(config, "preopen", command)
                execution = _read_json(before_execution)
                return finish(
                    controller_status="ALREADY_COMPLETE" if was_complete else "EXECUTION_COMPLETE",
                    phase="PREOPEN",
                    ca_phase_sidecar=str(_phase_sidecar_path(config, today, "PREOPEN")),
                    execution_path=str(before_execution.resolve()),
                    execution_sha256=_sha256(before_execution),
                    execution_status=execution.get("status"),
                )

            execution = config.runtime_root / "executions" / f"{today}.json"
            if current.time() < time(18, 0):
                if execution.is_file():
                    return finish(
                        controller_status="ALREADY_COMPLETE",
                        phase="PREOPEN",
                        execution_path=str(execution.resolve()),
                        execution_sha256=_sha256(execution),
                    )
                return finish(
                    controller_status="PREOPEN_WINDOW_MISSED_NO_EXECUTION",
                    reason="NO_RETROACTIVE_PAPER_EXECUTION",
                )

            pointer = _pipeline_pointer(config)
            score_ref = _verify_score_pointer(
                pointer,
                today,
                expected_forward_root=config.forward_runtime_root,
            )
            eod_ref = pointer.get("eod") if isinstance(pointer.get("eod"), dict) else {}
            status["upstream_pointer_path"] = str(
                config.forward_runtime_root
                / "forward_monitoring"
                / "eod_automation"
                / "v4_x1_pipeline"
                / "latest.json"
            )
            if (
                eod_ref.get("status") != "NO_MISSING_SESSION"
                or score_ref.get("status") not in {"V4_X1_SCORE_ALREADY_DONE_VERIFIED", "V4_X1_PROSPECTIVE_SCORE_DONE"}
                or score_ref.get("session_date") != today
            ):
                return finish(
                    controller_status="WAITING_UPSTREAM_EOD_SCORE",
                    reason="CANONICAL_EOD_OR_SAME_DAY_SCORE_NOT_READY",
                )
            missing = _config_missing(config)
            if missing:
                return finish(
                    controller_status="WAITING_OPERATIONAL_CONFIGURATION",
                    reason=missing,
                    decision_session_date=today,
                    score_manifest_path=score_ref.get("manifest_path"),
                    score_manifest_sha256=score_ref.get("manifest_sha256"),
                )
            eod_paths = _session_manifest(config, today)
            current_score = load_score_manifest(score_ref["manifest_path"])
            previous_path = _previous_score_manifest(config, today)
            previous_score = None if previous_path is None else load_score_manifest(previous_path)
            required = tuple(sorted({str(value).strip().upper() for value in current_score.scores["ticker"].tolist()}))
            eod_inputs = verify_eod_execution_inputs(
                session_ohlcv_path=eod_paths["session_ohlcv"],
                model_input_path=eod_paths["model_input"],
                official_calendar_path=eod_paths["calendar"],
                decision_session_date=today,
                required_tickers=required,
            )
            bootstrap_t0(config.runtime_root, session_date=today)
            required = derive_required_execution_tickers(
                config.runtime_root,
                current_score=current_score,
                previous_score=previous_score,
                eod_inputs=eod_inputs,
            )
            ca_status = _ensure_ca_phase(
                config,
                session=today,
                phase="POST_EOD",
                required_tickers=required,
                now=current,
            )
            phase_attestation_path, _ = write_phase_attestation(
                config.runtime_root,
                phase="POST_EOD",
                session_date=today,
                expected_branch=config.expected_branch,
                expected_commit=config.expected_commit,
                issued_at=current,
            )
            command = [
                str(Path(config.python_exe).expanduser().resolve()),
                str((config.repo_root / "scripts" / "run_e2e_paper_post_eod_v1.py").resolve()),
                "--runtime-root", str(config.runtime_root.resolve()),
                "--current-score-manifest", str(current_score.manifest_path.resolve()),
                "--session-ohlcv", str(eod_paths["session_ohlcv"]),
                "--model-input", str(eod_paths["model_input"]),
                "--calendar", str(eod_paths["calendar"]),
                "--ca-attestation", str(Path(config.ca_attestation_path).expanduser().resolve()),
                "--expected-branch", config.expected_branch,
                "--expected-commit", config.expected_commit,
                "--phase-attestation", str(phase_attestation_path.resolve()),
                "--ca-journal", str(_journal_paths(config, today, "POST_EOD")[1].resolve()),
            ]
            if previous_path is not None:
                command.extend(("--previous-score-manifest", str(previous_path)))
            _run_child(config, "post_eod", command)
            prepared_after = _prepared_for_session(config, eod_inputs.next_official_session_date)
            if len(prepared_after) != 1:
                raise E2EOperationalGuardError("E2E_OPERATIONAL_PREPARED_OUTPUT_INVALID")
            prepared_sha = _sha256(prepared_after[0])
            return finish(
                controller_status="POST_EOD_PREPARED",
                phase="POST_EOD",
                provider_calls=ca_status == "CAPTURED",
                ca_phase_status=ca_status,
                prepared_path=str(prepared_after[0].resolve()),
                prepared_sha256=prepared_sha,
                decision_session_date=today,
                execution_session_date=eod_inputs.next_official_session_date,
            )
        except Exception as error:
            return finish(
                controller_status="FAIL_CLOSED",
                error_code=type(error).__name__.upper(),
                error_message=str(error),
            )


__all__ = ["OperationalControllerConfig", "run_operational_cycle"]
