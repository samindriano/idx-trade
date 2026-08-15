"""Fail-closed attestation for legacy canonical EOD calendar parents.

Canonical EOD manifests are immutable.  A later calendar sync can replace the
shared calendar bytes that a historical manifest referenced, so this module
records an independent, content-addressed provenance edge without pretending
that the replacement calendar is byte-identical to the lost parent.

The writer is deliberately explicit and the default CLI is read-only.  The
attestation is accepted only when every non-calendar canonical artifact still
passes its original manifest hash/semantic checks and an already accepted
bridge calendar proves the session and its immediate official neighbors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .provenance import sha256_file


ATTESTATION_SCHEMA = "idx-trade/canonical-eod-calendar-parent-attestation-v1"
ATTESTATION_STATUS = "CANONICAL_EOD_CALENDAR_PARENT_ATTESTED"
CALENDAR_BYTES_UNRECOVERED = "DECLARED_CAPTURE_TIME_CALENDAR_BYTES_UNRECOVERED"
ATTESTATION_FILENAME = "attestation.json"
ATTESTATION_NAMESPACE = "forward_monitoring/provenance_attestations/canonical_eod_calendar_parent_v1"

# This is the bridge identity accepted by the independent Price/Trend review.
# It is intentionally not inferred from a current mutable runtime calendar.
ACCEPTED_BRIDGE_CALENDAR_SHA256 = "51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e"


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fingerprint(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _date(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("Asia/Jakarta").tz_localize(None)
    return timestamp.normalize()


def _calendar_sessions(path: Path) -> pd.DatetimeIndex:
    frame = pd.read_csv(path)
    column = "date" if "date" in frame.columns else "session_date" if "session_date" in frame.columns else None
    if column is None:
        raise RuntimeError(f"calendar has no date column: {path}")
    values = pd.to_datetime(frame[column], errors="coerce")
    if values.isna().any():
        raise RuntimeError(f"calendar has malformed dates: {path}")
    sessions = pd.DatetimeIndex(values.dt.normalize())
    if len(sessions) == 0 or sessions.has_duplicates or not sessions.is_monotonic_increasing:
        raise RuntimeError(f"calendar is empty, duplicated, or unordered: {path}")
    return sessions


def _find_matching_files(root: Path, expected_sha256: str) -> list[Path]:
    matches: list[Path] = []
    expected = expected_sha256.lower()
    if not root.is_dir():
        return matches
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            if sha256_file(path).lower() == expected:
                matches.append(path.resolve())
        except OSError:
            continue
    return sorted(matches, key=lambda item: str(item).lower())


def _assert_frame_session(path: Path, *, session: str, date_columns: tuple[str, ...]) -> dict[str, Any]:
    frame = pd.read_parquet(path)
    column = next((name for name in date_columns if name in frame.columns), None)
    if column is None:
        raise RuntimeError(f"{path.name} has no session-date column")
    dates = pd.to_datetime(frame[column], errors="coerce")
    if dates.isna().any() or not dates.dt.normalize().eq(_date(session)).all():
        raise RuntimeError(f"{path.name} contains a session other than {session}")
    return {"rows": int(len(frame)), "date_column": column}


def _artifact_contract(
    manifest: Mapping[str, Any],
    *,
    session_dir: Path,
    session: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Verify declared canonical artifacts without consulting calendar bytes."""

    if manifest.get("status") != "DATA_READY" or str(manifest.get("session_date")) != session:
        raise RuntimeError("canonical session is not exact DATA_READY")
    if manifest.get("outcome_blind") is not True or manifest.get("forward_outcomes_accessed") is not False:
        raise RuntimeError("canonical session is not outcome-blind")
    for key in (
        "outcomes_or_labels_accessed",
        "outcome_metrics_computed",
        "model_fit",
        "model_scoring",
        "trade_recommendation",
    ):
        if key in manifest and manifest.get(key) is not False:
            raise RuntimeError(f"canonical session has prohibited flag: {key}")

    expected_files = (
        ("snapshot_path", "snapshot_sha256", "model_input.parquet"),
        ("evidence_path", "evidence_sha256", "session_evidence.parquet"),
        ("session_ohlcv_path", "session_ohlcv_sha256", "session_ohlcv.parquet"),
        ("stock_summary_path", "stock_summary_sha256", "idx_stock_summary.csv"),
        ("stock_summary_raw_path", "stock_summary_raw_sha256", "idx_stock_summary.raw.json"),
        ("index_summary_path", "index_summary_sha256", "idx_index_summary.csv"),
        ("index_summary_raw_path", "index_summary_raw_sha256", "idx_index_summary.raw.json"),
    )
    artifacts: dict[str, Any] = {}
    paths: dict[str, str] = {}
    for path_key, hash_key, filename in expected_files:
        declared_value = manifest.get(path_key)
        hash_value = manifest.get(hash_key)
        if declared_value is None and hash_value is None:
            continue
        if not isinstance(declared_value, str) or not isinstance(hash_value, str) or len(hash_value) != 64:
            raise RuntimeError(f"canonical artifact declaration is incomplete: {path_key}")
        declared = Path(declared_value).expanduser().resolve()
        expected = (session_dir / filename).resolve()
        if declared != expected:
            raise RuntimeError(f"canonical artifact path identity mismatch: {path_key}")
        if not declared.is_file() or sha256_file(declared).lower() != hash_value.lower():
            raise RuntimeError(f"canonical artifact hash mismatch: {path_key}")
        artifacts[path_key] = {"path": str(declared), "sha256": hash_value.lower()}
        paths[path_key] = str(declared)

    snapshot = Path(paths["snapshot_path"])
    artifacts["snapshot_semantics"] = _assert_frame_session(
        snapshot,
        session=session,
        date_columns=("session_date", "date"),
    )
    if "evidence_path" in paths:
        artifacts["evidence_semantics"] = _assert_frame_session(
            Path(paths["evidence_path"]),
            session=session,
            date_columns=("session_date", "date"),
        )
    if "session_ohlcv_path" in paths:
        artifacts["session_ohlcv_semantics"] = _assert_frame_session(
            Path(paths["session_ohlcv_path"]),
            session=session,
            date_columns=("session_date", "date"),
        )

    for source_key in ("stock_summary_source", "index_summary_source"):
        source = manifest.get(source_key)
        if source is None:
            continue
        if not isinstance(source, Mapping) or str(source.get("session_date")) != session:
            raise RuntimeError(f"{source_key} has invalid session identity")
        if str(source.get("completeness_status", "")).startswith("COMPLETE") is not True:
            raise RuntimeError(f"{source_key} is not complete")

    return artifacts, paths


def _bridge_proof(
    bridge_calendar_path: Path,
    bridge_calendar_sha256: str,
    session: str,
) -> dict[str, Any]:
    path = bridge_calendar_path.expanduser().resolve()
    expected = bridge_calendar_sha256.lower()
    if len(expected) != 64 or not path.is_file() or sha256_file(path).lower() != expected:
        raise RuntimeError("accepted bridge calendar missing or hash-mismatched")
    sessions = _calendar_sessions(path)
    target = _date(session)
    positions = [index for index, value in enumerate(sessions) if value == target]
    if len(positions) != 1:
        raise RuntimeError("session is absent or duplicated in accepted bridge calendar")
    index = positions[0]
    if index == 0 or index == len(sessions) - 1:
        raise RuntimeError("accepted bridge calendar lacks neighboring ordering proof")
    predecessor = sessions[index - 1]
    successor = sessions[index + 1]
    if not predecessor < target < successor:
        raise RuntimeError("accepted bridge calendar ordering proof is invalid")
    return {
        "accepted_bridge_calendar_path": str(path),
        "accepted_bridge_calendar_sha256": expected,
        "accepted_bridge_calendar_session_count": int(len(sessions)),
        "bridge_session_index": int(index),
        "predecessor_session": predecessor.date().isoformat(),
        "session": target.date().isoformat(),
        "successor_session": successor.date().isoformat(),
        "ordered_consecutive": True,
    }


def audit_canonical_eod_calendar_parent(
    *,
    runtime_root: str | Path,
    session: str | pd.Timestamp,
    accepted_bridge_calendar_path: str | Path,
    accepted_bridge_calendar_sha256: str = ACCEPTED_BRIDGE_CALENDAR_SHA256,
) -> dict[str, Any]:
    """Audit one canonical EOD session without writing runtime artifacts."""

    runtime = Path(runtime_root).expanduser().resolve()
    target = _date(session)
    key = target.date().isoformat()
    directory = (runtime / "forward_monitoring" / "sessions" / key).resolve()
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"canonical manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise RuntimeError("canonical manifest is not an object")

    artifacts, paths = _artifact_contract(manifest, session_dir=directory, session=key)
    calendar_path = Path(str(manifest.get("calendar_path") or "")).expanduser().resolve()
    declared_sha = str(manifest.get("calendar_sha256") or "").lower()
    if len(declared_sha) != 64 or not calendar_path:
        raise RuntimeError("canonical capture-time calendar declaration is invalid")
    current_sha = sha256_file(calendar_path).lower() if calendar_path.is_file() else None
    matches = _find_matching_files(runtime, declared_sha)
    calendar_recovered = bool(matches)
    if current_sha == declared_sha and calendar_path.resolve() not in matches:
        matches = sorted(set(matches + [calendar_path.resolve()]), key=lambda item: str(item).lower())
        calendar_recovered = True

    bridge_proof = _bridge_proof(
        Path(accepted_bridge_calendar_path),
        accepted_bridge_calendar_sha256,
        key,
    )
    return {
        "schema": ATTESTATION_SCHEMA,
        "session_date": key,
        "canonical_manifest_path": str(manifest_path),
        "canonical_manifest_sha256": sha256_file(manifest_path).lower(),
        "canonical_snapshot_path": paths["snapshot_path"],
        "canonical_snapshot_sha256": artifacts["snapshot_path"]["sha256"],
        "canonical_evidence_path": paths.get("evidence_path"),
        "canonical_evidence_sha256": artifacts.get("evidence_path", {}).get("sha256"),
        "declared_capture_time_calendar_path": str(calendar_path),
        "declared_capture_time_calendar_sha256": declared_sha,
        "current_declared_calendar_path_sha256": current_sha,
        "declared_capture_time_calendar_bytes_recovered": calendar_recovered,
        "declared_capture_time_calendar_bytes_unrecovered": not calendar_recovered,
        "declared_capture_time_calendar_status": (
            "RECOVERED" if calendar_recovered else CALENDAR_BYTES_UNRECOVERED
        ),
        "declared_calendar_sha256_matches": [str(path) for path in matches],
        "bridge_calendar_is_byte_identical_to_declared": False,
        "calendar_parent_substituted": False,
        "canonical_session_rewritten": False,
        "provider_calls": 0,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "outcomes_or_labels_accessed": False,
        "model_fit": False,
        "model_scoring": False,
        "trade_recommendation": False,
        "artifact_inventory": artifacts,
        **bridge_proof,
    }


def _attestation_payload(report: Mapping[str, Any]) -> dict[str, Any]:
    if report.get("declared_capture_time_calendar_status") != CALENDAR_BYTES_UNRECOVERED:
        raise RuntimeError("attestation requires unrecoverable capture-time calendar bytes")
    if report.get("declared_capture_time_calendar_bytes_recovered") is not False:
        raise RuntimeError("capture-time calendar bytes are recoverable")
    payload = {
        "schema": ATTESTATION_SCHEMA,
        "status": ATTESTATION_STATUS,
        "session_date": report["session_date"],
        "canonical_manifest_path": report["canonical_manifest_path"],
        "canonical_manifest_sha256": report["canonical_manifest_sha256"],
        "canonical_snapshot_path": report["canonical_snapshot_path"],
        "canonical_snapshot_sha256": report["canonical_snapshot_sha256"],
        "canonical_evidence_path": report.get("canonical_evidence_path"),
        "canonical_evidence_sha256": report.get("canonical_evidence_sha256"),
        "declared_capture_time_calendar_path": report["declared_capture_time_calendar_path"],
        "declared_capture_time_calendar_sha256": report["declared_capture_time_calendar_sha256"],
        "declared_capture_time_calendar_status": CALENDAR_BYTES_UNRECOVERED,
        "current_declared_calendar_path_sha256": report.get("current_declared_calendar_path_sha256"),
        "accepted_bridge_calendar_path": report["accepted_bridge_calendar_path"],
        "accepted_bridge_calendar_sha256": report["accepted_bridge_calendar_sha256"],
        "accepted_bridge_calendar_session_count": report["accepted_bridge_calendar_session_count"],
        "bridge_session_index": report["bridge_session_index"],
        "predecessor_session": report["predecessor_session"],
        "session": report["session"],
        "successor_session": report["successor_session"],
        "ordered_consecutive": True,
        "bridge_calendar_is_byte_identical_to_declared": False,
        "calendar_parent_substituted": False,
        "canonical_session_rewritten": False,
        "provider_calls": 0,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "outcomes_or_labels_accessed": False,
        "model_fit": False,
        "model_scoring": False,
        "trade_recommendation": False,
    }
    payload["attestation_fingerprint"] = _fingerprint(payload)
    return payload


def create_canonical_eod_calendar_parent_attestation(
    *,
    report: Mapping[str, Any],
    output_path: str | Path,
) -> Path:
    """Write one immutable attestation; never overwrite a different one."""

    payload = _attestation_payload(report)
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if destination.exists():
        existing = destination.read_text(encoding="utf-8")
        if existing != encoded:
            raise RuntimeError("existing attestation is immutable and differs")
        return destination
    destination.write_text(encoded, encoding="utf-8", newline="\n")
    return destination


def verify_canonical_eod_calendar_parent_attestation(
    attestation_path: str | Path,
    *,
    expected_session: str | pd.Timestamp | None = None,
    expected_bridge_calendar_path: str | Path | None = None,
    expected_bridge_calendar_sha256: str = ACCEPTED_BRIDGE_CALENDAR_SHA256,
) -> bool:
    """Strictly verify an attestation and all immutable canonical identities."""

    try:
        path = Path(attestation_path).expanduser().resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            return False
        if payload.get("schema") != ATTESTATION_SCHEMA or payload.get("status") != ATTESTATION_STATUS:
            return False
        if expected_session is not None and str(payload.get("session_date")) != _date(expected_session).date().isoformat():
            return False
        if payload.get("declared_capture_time_calendar_status") != CALENDAR_BYTES_UNRECOVERED:
            return False
        if payload.get("bridge_calendar_is_byte_identical_to_declared") is not False:
            return False
        if payload.get("calendar_parent_substituted") is not False:
            return False
        if payload.get("canonical_session_rewritten") is not False:
            return False
        for key in ("provider_calls",):
            if payload.get(key) != 0:
                return False
        for key in (
            "outcome_blind",
            "forward_outcomes_accessed",
            "outcomes_or_labels_accessed",
            "model_fit",
            "model_scoring",
            "trade_recommendation",
        ):
            if payload.get(key) is not (True if key == "outcome_blind" else False):
                return False
        fingerprint = payload.get("attestation_fingerprint")
        if not isinstance(fingerprint, str) or fingerprint != _fingerprint(
            {key: value for key, value in payload.items() if key != "attestation_fingerprint"}
        ):
            return False

        manifest = Path(str(payload.get("canonical_manifest_path") or "")).expanduser().resolve()
        if not manifest.is_file() or sha256_file(manifest).lower() != str(payload.get("canonical_manifest_sha256")).lower():
            return False
        raw_manifest = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(raw_manifest, Mapping):
            return False
        session = str(payload.get("session_date"))
        directory = manifest.parent.resolve()
        artifacts, paths = _artifact_contract(raw_manifest, session_dir=directory, session=session)
        if paths.get("snapshot_path") != str(payload.get("canonical_snapshot_path")):
            return False
        if artifacts["snapshot_path"]["sha256"] != str(payload.get("canonical_snapshot_sha256")).lower():
            return False
        if paths.get("evidence_path") != payload.get("canonical_evidence_path"):
            return False
        if artifacts.get("evidence_path", {}).get("sha256") != payload.get("canonical_evidence_sha256"):
            return False

        calendar_path = Path(str(payload.get("declared_capture_time_calendar_path") or "")).expanduser().resolve()
        declared_sha = str(payload.get("declared_capture_time_calendar_sha256") or "").lower()
        current_sha = sha256_file(calendar_path).lower() if calendar_path.is_file() else None
        if current_sha == declared_sha:
            return False
        if payload.get("current_declared_calendar_path_sha256") != current_sha:
            return False
        if _find_matching_files(manifest.parents[3], declared_sha):
            return False

        bridge_path = Path(str(payload.get("accepted_bridge_calendar_path") or "")).expanduser().resolve()
        if expected_bridge_calendar_path is not None and bridge_path != Path(expected_bridge_calendar_path).expanduser().resolve():
            return False
        if str(payload.get("accepted_bridge_calendar_sha256")).lower() != expected_bridge_calendar_sha256.lower():
            return False
        proof = _bridge_proof(bridge_path, expected_bridge_calendar_sha256, session)
        for key in (
            "accepted_bridge_calendar_path",
            "accepted_bridge_calendar_sha256",
            "accepted_bridge_calendar_session_count",
            "bridge_session_index",
            "predecessor_session",
            "session",
            "successor_session",
            "ordered_consecutive",
        ):
            if payload.get(key) != proof.get(key):
                return False
        return True
    except Exception:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit legacy canonical EOD calendar-parent provenance")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--bridge-calendar", type=Path, required=True)
    parser.add_argument("--bridge-calendar-sha256", default=ACCEPTED_BRIDGE_CALENDAR_SHA256)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = audit_canonical_eod_calendar_parent(
        runtime_root=args.runtime_root,
        session=args.session,
        accepted_bridge_calendar_path=args.bridge_calendar,
        accepted_bridge_calendar_sha256=args.bridge_calendar_sha256,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
