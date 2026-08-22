from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.forward_dividend_acquisition_v1 import (
    AMBIGUOUS_DIVIDEND_CANDIDATE,
    CASH_DIVIDEND_CANDIDATE,
    UNSUPPORTED_NON_CASH_DIVIDEND,
)
from idx_trade.forward_dividend_execution_v1_1 import (
    verify_cash_dividend_evidence_for_execution,
)
from idx_trade.forward_dividend_disposition_v1_2 import (
    BLOCKED_LIVE_UNRESOLVED,
    CERTIFIED_LIVE,
    CORROBORATING_ONLY,
    HISTORICAL_OBSERVED,
    SUPERSEDED,
    DividendDispositionCandidate,
    apply_temporal_disposition,
    candidate_from_review,
)
from idx_trade.forward_dividend_provenance_v1_2 import (
    ForwardDividendProvenanceV12Error,
    canonical_sha256,
    certify_direct_idx_dividend_from_attachment_review_v1_2,
    resolve_discovery_manifest_path_v1_2,
    resolve_exact_announcement_provenance,
)
from idx_trade.forward_dividend_orchestration_v1 import (
    BLOCKER_RESOLUTION_CERTIFIED_LIVE,
    BLOCKER_RESOLUTION_HISTORICAL_OBSERVED,
    BlockingDividendJournalEntry,
    CertifiedDividendJournalEntry,
    DividendAcquisitionJournal,
    DividendBlockerResolutionEntry,
    DividendCoverage,
    POST_EOD,
    PREOPEN,
    advance_coverage,
    journal_from_payload,
    journal_hash,
    journal_payload,
    load_journal_document,
    merge_journal_state,
    normalize_capture_phase,
    normalize_tickers,
    plan_discovery,
    write_journal_document,
)

SCHEMA = "idx_trade_forward_dividend_acquisition_batch_v1"
SEMANTIC_FAILURE = "CASH_DIVIDEND_SEMANTIC_REVIEW_FAILED"
REVIEW_FILENAME_V1_2 = "ATTACHMENT_REVIEW_V1_2.json"

PHASE_ORDER = {
    PREOPEN: 0,
    POST_EOD: 1,
}


class DividendAcquisitionBatchError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)

    return h.hexdigest()


def canonical_hash(value: object) -> str:
    raw = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")

    return sha256_bytes(raw)


def canonical_announcement_identity(
    candidate: dict[str, Any],
) -> str:
    ticker = str(
        candidate.get("ticker") or ""
    ).strip().upper()

    number = str(
        candidate.get("announcement_number") or ""
    ).strip()

    announcement_id = str(
        candidate.get("announcement_id") or ""
    ).strip()

    if not ticker:
        raise DividendAcquisitionBatchError(
            "BATCH_CANDIDATE_TICKER_MISSING"
        )

    # Journal identity prefers announcement number because it remains
    # stable even when IDX later populates an internal announcement id.
    if number:
        return f"{ticker}|NUMBER|{number}"

    if announcement_id:
        return f"{ticker}|ID|{announcement_id}"

    raise DividendAcquisitionBatchError(
        "BATCH_CANDIDATE_IDENTITY_MISSING"
    )


def candidate_selector_args(
    candidate: dict[str, Any],
) -> list[str]:
    announcement_id = str(
        candidate.get("announcement_id") or ""
    ).strip()

    number = str(
        candidate.get("announcement_number") or ""
    ).strip()

    if announcement_id:
        return [
            "--announcement-id",
            announcement_id,
        ]

    if number:
        return [
            "--announcement-number",
            number,
        ]

    raise DividendAcquisitionBatchError(
        "BATCH_CANDIDATE_SELECTOR_MISSING"
    )


def candidate_directory_name(
    candidate: dict[str, Any],
) -> str:
    ticker = str(
        candidate.get("ticker") or ""
    ).strip().upper()

    identity = canonical_announcement_identity(
        candidate
    )

    digest = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()[:16]

    return f"{ticker}_{digest}"


def seal_batch_manifest(
    payload: dict[str, Any],
) -> dict[str, Any]:
    if "batch_payload_sha256" in payload:
        raise DividendAcquisitionBatchError(
            "BATCH_MANIFEST_ALREADY_SEALED"
        )

    result = dict(payload)
    result["batch_payload_sha256"] = canonical_hash(
        payload
    )

    return result


def verify_batch_manifest_payload(
    payload: object,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DividendAcquisitionBatchError(
            "BATCH_MANIFEST_NOT_OBJECT"
        )

    if payload.get("schema_version") != SCHEMA:
        raise DividendAcquisitionBatchError(
            "BATCH_MANIFEST_SCHEMA_MISMATCH"
        )

    declared = str(
        payload.get("batch_payload_sha256") or ""
    )

    unhashed = dict(payload)
    unhashed.pop(
        "batch_payload_sha256",
        None,
    )

    actual = canonical_hash(unhashed)

    if actual != declared:
        raise DividendAcquisitionBatchError(
            "BATCH_MANIFEST_HASH_MISMATCH"
        )

    return payload


def journal_order(
    journal: DividendAcquisitionJournal,
) -> tuple[date, int]:
    phase = normalize_capture_phase(
        journal.capture_phase
    )

    return (
        date.fromisoformat(
            journal.as_of_date
        ),
        PHASE_ORDER[phase],
    )


def run_process(
    command: list[str],
    *,
    allowed_exit_codes: set[int] = {0},
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if proc.returncode not in allowed_exit_codes:
        raise DividendAcquisitionBatchError(
            "BATCH_CHILD_PROCESS_FAILED\n"
            + "COMMAND="
            + " ".join(command)
            + "\nSTDOUT=\n"
            + proc.stdout[-6000:]
            + "\nSTDERR=\n"
            + proc.stderr[-6000:]
        )

    return proc


def latest_prior_journal(
    journal_dir: Path,
    *,
    as_of_date: str,
    capture_phase: str,
) -> Path | None:
    if not journal_dir.is_dir():
        return None

    target = (
        date.fromisoformat(as_of_date),
        PHASE_ORDER[
            normalize_capture_phase(
                capture_phase
            )
        ],
    )

    candidates = []
    same_order: dict[tuple[date, int], list[tuple[Path, str]]] = {}

    for path in journal_dir.glob("*.json"):
        verified = load_journal_document(
            path
        )

        order = journal_order(
            verified.journal
        )

        same_order.setdefault(order, []).append(
            (path.resolve(), verified.file_sha256)
        )

        if order < target:
            candidates.append(
                (order, path)
            )

    if not candidates:
        return None

    for order, rows in same_order.items():
        hashes = {sha for _, sha in rows}
        if len(rows) > 1 and len(hashes) > 1:
            raise DividendAcquisitionBatchError(
                "BATCH_JOURNAL_FORK_SAME_ORDER:"
                + str(order)
            )

    candidates.sort(
        key=lambda row: row[0]
    )

    return candidates[-1][1]


def verify_discovery_manifest(
    path: Path,
    *,
    expected_tickers: tuple[str, ...],
    expected_from: str,
    expected_to: str,
) -> dict[str, Any]:
    if not path.is_file():
        raise DividendAcquisitionBatchError(
            "BATCH_DISCOVERY_MANIFEST_MISSING"
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if payload.get("status") != "COMPLETE":
        raise DividendAcquisitionBatchError(
            "BATCH_DISCOVERY_NOT_COMPLETE"
        )

    required = tuple(
        payload.get(
            "required_tickers"
        )
        or ()
    )

    if tuple(required) != expected_tickers:
        raise DividendAcquisitionBatchError(
            "BATCH_DISCOVERY_TICKER_MISMATCH"
        )

    if (
        payload.get("date_from")
        != expected_from
        or payload.get("date_to")
        != expected_to
    ):
        raise DividendAcquisitionBatchError(
            "BATCH_DISCOVERY_WINDOW_MISMATCH"
        )

    candidates = payload.get(
        "candidates"
    )

    if not isinstance(candidates, list):
        raise DividendAcquisitionBatchError(
            "BATCH_DISCOVERY_CANDIDATES_INVALID"
        )

    identities: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise DividendAcquisitionBatchError(
                "BATCH_DISCOVERY_CANDIDATE_INVALID"
            )
        identity = canonical_announcement_identity(candidate)
        if identity in identities:
            raise DividendAcquisitionBatchError(
                "BATCH_DISCOVERY_DUPLICATE_CANDIDATE:" + identity
            )
        identities.add(identity)

    raw_artifacts = payload.get("raw_artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise DividendAcquisitionBatchError(
            "BATCH_DISCOVERY_RAW_ARTIFACTS_INVALID"
        )

    return payload


def _verify_declared_file(
    path: Path,
    declared_sha: object,
    code: str,
) -> None:
    if not path.is_file():
        raise DividendAcquisitionBatchError(code + ":MISSING")
    expected = str(declared_sha or "").strip().lower()
    if len(expected) != 64 or sha256_path(path) != expected:
        raise DividendAcquisitionBatchError(code + ":SHA_MISMATCH")


def _verify_attachment_directory(
    evidence_dir: Path,
    *,
    review_filename: str,
    review_sha256: object,
    expected_event_id: str | None = None,
    expected_event_sha256: str | None = None,
) -> None:
    manifest_path = evidence_dir / "ATTACHMENT_CAPTURE_MANIFEST.json"
    _verify_declared_file(
        manifest_path,
        sha256_path(manifest_path) if manifest_path.is_file() else "",
        "BATCH_ATTACHMENT_MANIFEST",
    )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DividendAcquisitionBatchError(
            "BATCH_ATTACHMENT_MANIFEST_JSON_INVALID"
        ) from exc
    rows = manifest.get("attachments")
    if manifest.get("status") not in {
        "COMPLETE_AWAITING_SEMANTIC_REVIEW",
    } or not isinstance(rows, list) or not rows:
        raise DividendAcquisitionBatchError(
            "BATCH_ATTACHMENT_MANIFEST_INVALID"
        )
    for row in rows:
        if not isinstance(row, dict):
            raise DividendAcquisitionBatchError(
                "BATCH_ATTACHMENT_ROW_INVALID"
            )
        filename = str(row.get("pdf_filename") or "").strip()
        if not filename or Path(filename).name != filename:
            raise DividendAcquisitionBatchError(
                "BATCH_ATTACHMENT_FILENAME_INVALID"
            )
        _verify_declared_file(
            evidence_dir / filename,
            row.get("sha256"),
            "BATCH_ATTACHMENT_DOCUMENT:" + filename,
        )
    review_path = evidence_dir / review_filename
    _verify_declared_file(
        review_path,
        review_sha256,
        "BATCH_ATTACHMENT_REVIEW",
    )
    if review_filename == REVIEW_FILENAME_V1_2:
        _verify_v1_2_review_transport(
            review_path,
            evidence_dir,
            manifest_path,
            manifest,
        )
    if review_filename == REVIEW_FILENAME_V1_2 and expected_event_id is not None:
        try:
            event = certify_direct_idx_dividend_from_attachment_review_v1_2(
                review_path,
                evidence_dir,
            )
        except ForwardDividendProvenanceV12Error as exc:
            raise DividendAcquisitionBatchError(
                "BATCH_ATTACHMENT_V1_2_CERTIFICATION_INVALID"
            ) from exc
        if expected_event_id is not None and event.event_id != expected_event_id:
            raise DividendAcquisitionBatchError(
                "BATCH_ATTACHMENT_EVENT_ID_MISMATCH"
            )
        if (
            expected_event_sha256 is not None
            and event.source_evidence_sha256 != expected_event_sha256
        ):
            raise DividendAcquisitionBatchError(
                "BATCH_ATTACHMENT_EVENT_SHA_MISMATCH"
            )


def _verify_v1_2_review_transport(
    review_path: Path,
    evidence_dir: Path,
    attachment_manifest_path: Path,
    attachment_manifest: dict[str, Any],
) -> None:
    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DividendAcquisitionBatchError(
            "BATCH_V1_2_REVIEW_JSON_INVALID"
        ) from exc

    transport = review.get("transport_provenance")
    announcement = review.get("announcement")
    provenance = review.get("announcement_provenance")
    if not isinstance(transport, dict) or not isinstance(announcement, dict) or not isinstance(provenance, dict):
        raise DividendAcquisitionBatchError(
            "BATCH_V1_2_REVIEW_TRANSPORT_INVALID"
        )

    if str(transport.get("source_attachment_manifest_sha256") or "").strip().lower() != sha256_path(attachment_manifest_path):
        raise DividendAcquisitionBatchError(
            "BATCH_V1_2_ATTACHMENT_MANIFEST_REVIEW_SHA_MISMATCH"
        )

    discovery_sha = str(transport.get("source_discovery_manifest_sha256") or "").strip().lower()
    raw_shas = tuple(sorted({str(value).strip().lower() for value in (transport.get("source_raw_page_sha256") or ()) if str(value).strip()}))
    declared_relpath = str(transport.get("source_discovery_manifest_relpath") or "").strip()
    declared_path = str(transport.get("source_discovery_manifest_resolved_path") or transport.get("source_discovery_manifest_declared_path") or "").strip()
    if declared_relpath:
        discovery_declared_path = (evidence_dir / declared_relpath).resolve()
    elif declared_path:
        discovery_declared_path = Path(declared_path).expanduser()
    else:
        raise DividendAcquisitionBatchError(
            "BATCH_V1_2_DISCOVERY_BINDING_MISSING"
        )

    try:
        discovery_path = resolve_discovery_manifest_path_v1_2(
            declared_path=discovery_declared_path,
            declared_sha256=discovery_sha,
        )
        discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
        exact_record = provenance.get("exact_announcement_record")
        record_sha = str(provenance.get("announcement_record_sha256") or "").strip().lower()
        candidate = {
            "ticker": announcement.get("code"),
            "announcement_id": announcement.get("id"),
            "announcement_number": announcement.get("number"),
            "announcement_timestamp": announcement.get("date"),
            "title": announcement.get("title"),
            "form_id": announcement.get("form_id"),
        }
        resolved = resolve_exact_announcement_provenance(
            discovery_path=discovery_path,
            discovery=discovery,
            candidate=candidate,
        )
    except Exception as exc:
        raise DividendAcquisitionBatchError(
            "BATCH_V1_2_SOURCE_CHAIN_INVALID"
        ) from exc

    if not isinstance(exact_record, dict) or canonical_sha256(exact_record) != record_sha:
        raise DividendAcquisitionBatchError(
            "BATCH_V1_2_REVIEW_RECORD_SHA_INVALID"
        )
    if resolved.announcement_record_sha256 != record_sha or tuple(resolved.source_raw_page_sha256) != raw_shas:
        raise DividendAcquisitionBatchError(
            "BATCH_V1_2_REVIEW_SOURCE_CHAIN_MISMATCH"
        )

    review_documents = {
        str(row.get("pdf_filename") or "").strip(): str(row.get("sha256") or "").strip().lower()
        for row in (review.get("documents") or ())
        if isinstance(row, dict)
    }
    manifest_documents = {
        str(row.get("pdf_filename") or "").strip(): str(row.get("sha256") or "").strip().lower()
        for row in (attachment_manifest.get("attachments") or ())
        if isinstance(row, dict)
    }
    if review_documents != manifest_documents:
        raise DividendAcquisitionBatchError(
            "BATCH_V1_2_REVIEW_ATTACHMENT_BINDING_MISMATCH"
        )


def verify_complete_batch_contents(
    *,
    batch_root: Path,
    payload: dict[str, Any],
    journal_target: Path,
    expected_as_of: str | None = None,
    expected_phase: str | None = None,
    expected_tickers: tuple[str, ...] | None = None,
) -> None:
    if payload.get("status") != "COMPLETE":
        raise DividendAcquisitionBatchError("BATCH_STATUS_NOT_COMPLETE")
    if expected_as_of is not None and payload.get("as_of_date") != expected_as_of:
        raise DividendAcquisitionBatchError("BATCH_AS_OF_MISMATCH")
    if expected_phase is not None and payload.get("capture_phase") != expected_phase:
        raise DividendAcquisitionBatchError("BATCH_PHASE_MISMATCH")
    if expected_tickers is not None and tuple(payload.get("required_tickers") or ()) != expected_tickers:
        raise DividendAcquisitionBatchError("BATCH_TICKER_MISMATCH")

    discovery_relpath = str(payload.get("discovery_manifest_relpath") or "").strip()
    discovery_path = (batch_root / discovery_relpath).resolve()
    if discovery_path.parent != (batch_root / "discovery").resolve():
        raise DividendAcquisitionBatchError("BATCH_DISCOVERY_PATH_INVALID")
    _verify_declared_file(
        discovery_path,
        payload.get("discovery_manifest_sha256"),
        "BATCH_DISCOVERY_MANIFEST",
    )
    try:
        discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DividendAcquisitionBatchError("BATCH_DISCOVERY_JSON_INVALID") from exc
    verify_discovery_manifest(
        discovery_path,
        expected_tickers=tuple(payload.get("required_tickers") or ()),
        expected_from=str(payload.get("discovery_plan", {}).get("date_from") or ""),
        expected_to=str(payload.get("discovery_plan", {}).get("date_to") or ""),
    )
    discovery_identities = {
        canonical_announcement_identity(row)
        for row in (discovery.get("candidates") or ())
        if isinstance(row, dict)
    }

    dispositions = payload.get("dispositions")
    if not isinstance(dispositions, list):
        raise DividendAcquisitionBatchError("BATCH_DISPOSITIONS_INVALID")
    live_ids: set[str] = set()
    blocker_ids: set[str] = set()
    disposition_ids: set[str] = set()
    for row in dispositions:
        if not isinstance(row, dict):
            raise DividendAcquisitionBatchError("BATCH_DISPOSITION_ROW_INVALID")
        status = str(row.get("status") or "")
        identity = str(row.get("announcement_identity") or "").strip()
        if not identity or identity in disposition_ids:
            raise DividendAcquisitionBatchError(
                "BATCH_DISPOSITION_IDENTITY_INVALID_OR_DUPLICATE"
            )
        disposition_ids.add(identity)
        evidence_relpath = str(row.get("evidence_relpath") or "").strip()
        review_sha = row.get("review_sha256")
        if evidence_relpath:
            evidence_dir = (batch_root / evidence_relpath).resolve()
            if batch_root not in evidence_dir.parents:
                raise DividendAcquisitionBatchError("BATCH_EVIDENCE_PATH_ESCAPE")
            review_filename = str(
                row.get("review_filename") or REVIEW_FILENAME_V1_2
            )
            _verify_attachment_directory(
                evidence_dir,
                review_filename=review_filename,
                review_sha256=review_sha,
                expected_event_id=row.get("event_id"),
                expected_event_sha256=row.get("event_sha256"),
            )
        if status == CERTIFIED_LIVE:
            live_ids.add(str(row.get("announcement_identity") or ""))
        if status == BLOCKED_LIVE_UNRESOLVED:
            blocker_ids.add(identity)

    if disposition_ids != discovery_identities:
        raise DividendAcquisitionBatchError(
            "BATCH_DISPOSITION_DISCOVERY_IDENTITY_MISMATCH"
        )

    journal_payload_value = payload.get("journal")
    journal = journal_from_payload(journal_payload_value)
    if journal_hash(journal) != payload.get("journal_sha256"):
        raise DividendAcquisitionBatchError("BATCH_JOURNAL_HASH_MISMATCH")
    journal_live_ids = {row.announcement_identity for row in journal.certified_events}
    journal_blocker_ids = {row.announcement_identity for row in journal.blockers}
    if journal_live_ids != live_ids or journal_blocker_ids != blocker_ids:
        raise DividendAcquisitionBatchError("BATCH_DISPOSITION_JOURNAL_MISMATCH")
    if journal_target.exists():
        loaded = load_journal_document(journal_target)
        if loaded.journal_sha256 != payload.get("journal_sha256"):
            raise DividendAcquisitionBatchError("BATCH_JOURNAL_TARGET_MISMATCH")


def recover_existing_batch(
    *,
    batch_root: Path,
    journal_target: Path,
) -> None:
    manifest_path = (
        batch_root
        / "BATCH_MANIFEST.json"
    )

    if not manifest_path.is_file():
        raise DividendAcquisitionBatchError(
            "BATCH_EXISTS_WITHOUT_MANIFEST"
        )

    payload = verify_batch_manifest_payload(
        json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )
    )

    declared_batch_root = Path(
        str(
            payload.get(
                "batch_root"
            )
            or ""
        )
    ).expanduser().resolve()

    if declared_batch_root != batch_root:
        raise DividendAcquisitionBatchError(
            "BATCH_ROOT_MISMATCH"
        )

    declared_journal_target = Path(
        str(
            payload.get(
                "journal_target"
            )
            or ""
        )
    ).expanduser().resolve()

    if declared_journal_target != journal_target:
        raise DividendAcquisitionBatchError(
            "BATCH_JOURNAL_TARGET_MISMATCH"
        )

    verify_complete_batch_contents(
        batch_root=batch_root,
        payload=payload,
        journal_target=journal_target,
    )

    journal = journal_from_payload(
        payload.get("journal")
    )

    if (
        journal_hash(journal)
        != payload.get(
            "journal_sha256"
        )
    ):
        raise DividendAcquisitionBatchError(
            "BATCH_JOURNAL_HASH_MISMATCH"
        )

    prior = payload.get(
        "prior_journal"
    )

    prior_path = None

    if prior is not None:
        if not isinstance(prior, dict):
            raise DividendAcquisitionBatchError(
                "BATCH_PRIOR_METADATA_INVALID"
            )

        prior_path = Path(
            str(
                prior.get("path")
                or ""
            )
        ).expanduser().resolve()

        if not prior_path.is_file():
            raise DividendAcquisitionBatchError(
                "BATCH_PRIOR_JOURNAL_MISSING"
            )

        if (
            sha256_path(prior_path)
            != str(
                prior.get(
                    "file_sha256"
                )
                or ""
            )
        ):
            raise DividendAcquisitionBatchError(
                "BATCH_PRIOR_JOURNAL_SHA_CHANGED"
            )

    written = write_journal_document(
        journal_target,
        journal,
        previous_journal_path=(
            prior_path
            if prior_path is not None
            else None
        ),
    )

    print(
        "DIVIDEND_ACQUISITION_BATCH_RECOVERED"
    )
    print(
        f"journal={written.path}"
    )
    print(
        f"journal_sha256="
        f"{written.journal_sha256}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Restart-safe prospective IDX dividend "
            "acquisition batch."
        )
    )

    parser.add_argument(
        "--provider-checkout",
        required=True,
    )

    parser.add_argument(
        "--runtime-root",
        required=True,
    )

    parser.add_argument(
        "--as-of-date",
        required=True,
    )

    parser.add_argument(
        "--capture-phase",
        required=True,
        choices=[
            PREOPEN,
            POST_EOD,
        ],
    )

    parser.add_argument(
        "--ticker",
        action="append",
        required=True,
    )

    parser.add_argument(
        "--prior-journal",
    )

    parser.add_argument(
        "--uv-exe",
    )

    parser.add_argument(
        "--python-exe",
        default=sys.executable,
    )

    args = parser.parse_args()

    as_of = date.fromisoformat(
        args.as_of_date
    ).isoformat()

    phase = normalize_capture_phase(
        args.capture_phase
    )

    tickers = normalize_tickers(
        args.ticker
    )

    provider = Path(
        args.provider_checkout
    ).expanduser().resolve()

    provider_project = (
        provider / "python"
    )

    if not provider_project.is_dir():
        raise SystemExit(
            "STOP: provider python project missing"
        )

    runtime_root = Path(
        args.runtime_root
    ).expanduser().resolve()

    acquisition_root = (
        runtime_root
        / "dividend_acquisition_v1"
    )

    batch_dir = (
        acquisition_root
        / "batches"
    )

    journal_dir = (
        acquisition_root
        / "journals"
    )

    batch_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    journal_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stem = (
        f"{as_of}_{phase}"
    )

    final_batch = (
        batch_dir / stem
    ).resolve()

    journal_target = (
        journal_dir
        / f"{stem}.json"
    ).resolve()

    if final_batch.exists():
        recover_existing_batch(
            batch_root=final_batch,
            journal_target=journal_target,
        )
        return 0

    if journal_target.exists():
        raise SystemExit(
            "STOP: journal exists without immutable batch"
        )

    if args.prior_journal:
        prior_path = Path(
            args.prior_journal
        ).expanduser().resolve()
    else:
        prior_path = latest_prior_journal(
            journal_dir,
            as_of_date=as_of,
            capture_phase=phase,
        )

    prior = (
        load_journal_document(
            prior_path
        )
        if prior_path is not None
        else None
    )

    if prior is not None and journal_order(prior.journal) >= (
        date.fromisoformat(as_of),
        PHASE_ORDER[phase],
    ):
        raise DividendAcquisitionBatchError(
            "BATCH_PRIOR_JOURNAL_ORDER_NOT_PRIOR"
        )

    prior_coverage = (
        prior.journal.coverage
        if prior is not None
        else ()
    )

    plan = plan_discovery(
        as_of_date=as_of,
        required_tickers=tickers,
        prior_coverage=prior_coverage,
    )

    uv_exe = (
        str(args.uv_exe)
        if args.uv_exe
        else shutil.which("uv")
    )

    if not uv_exe:
        raise SystemExit(
            "STOP: uv executable not found"
        )

    python_exe = str(
        Path(
            args.python_exe
        ).expanduser().resolve()
    )

    partial_stages = sorted(
        batch_dir.glob(f".{stem}.partial.*"),
        key=lambda path: str(path).lower(),
    )
    if partial_stages:
        raise DividendAcquisitionBatchError(
            "BATCH_PARTIAL_STAGE_REQUIRES_REVIEW:"
            + ",".join(str(path) for path in partial_stages)
        )

    stage = Path(
        tempfile.mkdtemp(
            prefix=f".{stem}.partial.",
            dir=batch_dir,
        )
    )

    try:
        discovery_root = (
            stage / "discovery"
        )

        discovery_command = [
            uv_exe,
            "run",
            "--project",
            str(provider_project),
            "python",
            str(
                REPO_ROOT
                / "scripts"
                / "capture_forward_dividend_announcements_v1.py"
            ),
            "--provider-checkout",
            str(provider),
            "--output-dir",
            str(discovery_root),
            "--date-from",
            plan.date_from,
            "--date-to",
            plan.date_to,
        ]

        for ticker in tickers:
            discovery_command.extend(
                [
                    "--ticker",
                    ticker,
                ]
            )

        run_process(
            discovery_command
        )

        discovery_manifest = (
            discovery_root
            / "DISCOVERY_MANIFEST.json"
        )

        discovery = verify_discovery_manifest(
            discovery_manifest,
            expected_tickers=tickers,
            expected_from=plan.date_from,
            expected_to=plan.date_to,
        )

        candidates = discovery[
            "candidates"
        ]

        prior_certified = {}
        prior_blockers = {}

        if prior is not None:
            prior_certified = {
                row.announcement_identity: row
                for row in (
                    prior.journal.certified_events
                )
            }

            prior_blockers = {
                row.announcement_identity: row
                for row in prior.journal.blockers
            }

        current_certified = []
        current_blockers = []
        current_blocker_resolutions = []
        dispositions = []
        disposition_inputs = []
        evidence_by_identity = {}
        event_by_identity = {}

        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise DividendAcquisitionBatchError("BATCH_CANDIDATE_INVALID")

            ticker = str(candidate.get("ticker") or "").strip().upper()
            if ticker not in tickers:
                raise DividendAcquisitionBatchError(
                    "BATCH_CANDIDATE_OUTSIDE_REQUIRED_UNIVERSE"
                )
            classification = str(candidate.get("classification") or "").strip()
            identity = canonical_announcement_identity(candidate)

            if classification in {
                AMBIGUOUS_DIVIDEND_CANDIDATE,
                UNSUPPORTED_NON_CASH_DIVIDEND,
            }:
                disposition_inputs.append(candidate_from_review(candidate))
                dispositions.append({
                    "announcement_identity": identity,
                    "ticker": ticker,
                    "classification": classification,
                    "evidence_relpath": None,
                    "review_sha256": None,
                    "review_filename": None,
                    "semantic_failures": [classification],
                })
                continue

            if classification != CASH_DIVIDEND_CANDIDATE:
                raise DividendAcquisitionBatchError(
                    "BATCH_CANDIDATE_CLASSIFICATION_UNKNOWN:" + classification
                )

            evidence_relative = Path("evidence") / candidate_directory_name(candidate)
            evidence_stage = stage / evidence_relative
            attachment_command = [
                uv_exe, "run", "--project", str(provider_project), "python",
                str(REPO_ROOT / "scripts" / "capture_forward_dividend_candidate_attachments_v1.py"),
                "--provider-checkout", str(provider),
                "--discovery-manifest", str(discovery_manifest),
                "--ticker", ticker, *candidate_selector_args(candidate),
                "--output-dir", str(evidence_stage),
            ]
            run_process(attachment_command)

            review_command = [
                python_exe,
                str(REPO_ROOT / "scripts" / "review_forward_dividend_candidate_attachments_v1_2.py"),
                "--attachment-dir", str(evidence_stage),
            ]
            review_proc = run_process(review_command, allowed_exit_codes={0, 2})
            review_path = evidence_stage / REVIEW_FILENAME_V1_2
            if not review_path.is_file():
                raise DividendAcquisitionBatchError("BATCH_REVIEW_FILE_MISSING")
            review_payload = json.loads(review_path.read_text(encoding="utf-8"))
            review_sha = sha256_path(review_path)
            evidence_by_identity[identity] = evidence_relative

            if review_proc.returncode == 2:
                disposition_inputs.append(
                    candidate_from_review(candidate, review=review_payload)
                )
                dispositions.append({
                    "announcement_identity": identity,
                    "ticker": ticker,
                    "classification": classification,
                    "evidence_relpath": str(evidence_relative),
                    "review_sha256": review_sha,
                    "review_filename": REVIEW_FILENAME_V1_2,
                    "semantic_failures": review_payload.get("failures") or [],
                })
                continue

            try:
                event = certify_direct_idx_dividend_from_attachment_review_v1_2(
                    review_path, evidence_stage
                )
            except ForwardDividendProvenanceV12Error as exc:
                raise DividendAcquisitionBatchError(
                    "BATCH_V1_2_CERTIFICATION_FAILED:" + identity
                ) from exc
            if event.ticker != ticker:
                raise DividendAcquisitionBatchError("BATCH_CERTIFIED_EVENT_TICKER_MISMATCH")
            event_by_identity[identity] = event
            disposition_inputs.append(
                candidate_from_review(candidate, review=review_payload, event=event)
            )
            dispositions.append({
                "announcement_identity": identity,
                "ticker": ticker,
                "classification": classification,
                "evidence_relpath": str(evidence_relative),
                "review_sha256": review_sha,
                "review_filename": REVIEW_FILENAME_V1_2,
                "semantic_failures": [],
            })

        disposition_result = apply_temporal_disposition(
            disposition_inputs,
            as_of_date=as_of,
        )
        disposition_by_identity = {
            row.announcement_identity: row
            for row in disposition_result.dispositions
        }
        for row in dispositions:
            disposition = disposition_by_identity[row["announcement_identity"]]
            row.update({
                "status": disposition.category,
                "reason": disposition.reason,
                "superseded_by": disposition.superseded_by,
                "event_id": disposition.event_id,
                "event_sha256": disposition.event_sha256,
            })
            identity = row["announcement_identity"]
            event = event_by_identity.get(identity)
            if disposition.category == CERTIFIED_LIVE:
                if event is None:
                    raise DividendAcquisitionBatchError(
                        "BATCH_LIVE_DISPOSITION_WITHOUT_EVENT:" + identity
                    )
                prior_row = prior_certified.get(identity)
                if prior_row is not None and (
                    prior_row.event_id != event.event_id
                    or prior_row.event_sha256 != event.source_evidence_sha256
                ):
                    raise DividendAcquisitionBatchError(
                        "BATCH_PRIOR_CERTIFIED_EVENT_CHANGED:" + identity
                    )
                final_evidence_dir = (final_batch / evidence_by_identity[identity]).resolve()
                current_certified.append(CertifiedDividendJournalEntry(
                    announcement_identity=identity,
                    ticker=row["ticker"],
                    event_id=event.event_id,
                    event_sha256=event.source_evidence_sha256,
                    evidence_dir=str(final_evidence_dir),
                    review_sha256=str(row["review_sha256"]),
                    review_filename=REVIEW_FILENAME_V1_2,
                ))
            elif disposition.category == BLOCKED_LIVE_UNRESOLVED:
                if identity in prior_certified:
                    raise DividendAcquisitionBatchError(
                        "BATCH_PRIOR_CERTIFIED_NOW_BLOCKING:" + identity
                    )
                current_blockers.append(BlockingDividendJournalEntry(
                    announcement_identity=identity,
                    ticker=row["ticker"],
                    classification=SEMANTIC_FAILURE,
                ))
            elif disposition.category == SUPERSEDED:
                resolver_identity = disposition.superseded_by

                if resolver_identity in prior_blockers:
                    resolver_row = disposition_by_identity.get(
                        resolver_identity
                    )
                    resolver_event = event_by_identity.get(
                        resolver_identity
                    )

                    if resolver_row is None or resolver_event is None:
                        raise DividendAcquisitionBatchError(
                            "BATCH_BLOCKER_RESOLUTION_RESOLVER_MISSING:"
                            + identity
                        )

                    if resolver_row.category not in {
                        CERTIFIED_LIVE,
                        HISTORICAL_OBSERVED,
                    }:
                        raise DividendAcquisitionBatchError(
                            "BATCH_BLOCKER_RESOLUTION_RESOLVER_NOT_PAYABLE:"
                            + resolver_identity
                        )

                    resolver_evidence_relpath = evidence_by_identity.get(
                        resolver_identity
                    )
                    resolver_review_sha = next(
                        (
                            row["review_sha256"]
                            for row in dispositions
                            if row["announcement_identity"]
                            == resolver_identity
                        ),
                        None,
                    )

                    if (
                        resolver_evidence_relpath is None
                        or not resolver_review_sha
                    ):
                        raise DividendAcquisitionBatchError(
                            "BATCH_BLOCKER_RESOLUTION_EVIDENCE_MISSING:"
                            + resolver_identity
                        )

                    blocker = prior_blockers[identity]
                    current_blocker_resolutions.append(
                        DividendBlockerResolutionEntry(
                            blocker_announcement_identity=identity,
                            blocker_ticker=blocker.ticker,
                            blocker_classification=blocker.classification,
                            resolver_announcement_identity=resolver_identity,
                            resolver_ticker=resolver_event.ticker,
                            resolver_event_id=resolver_event.event_id,
                            resolver_event_sha256=(
                                resolver_event.source_evidence_sha256
                            ),
                            resolver_evidence_dir=str(
                                (
                                    final_batch
                                    / resolver_evidence_relpath
                                ).resolve()
                            ),
                            resolver_review_sha256=str(
                                resolver_review_sha
                            ),
                            resolver_status=(
                                BLOCKER_RESOLUTION_CERTIFIED_LIVE
                                if resolver_row.category == CERTIFIED_LIVE
                                else BLOCKER_RESOLUTION_HISTORICAL_OBSERVED
                            ),
                            resolver_review_filename=REVIEW_FILENAME_V1_2,
                        )
                    )

        coverage_base = (
            prior.journal
            if prior is not None
            else DividendAcquisitionJournal(
                as_of_date=as_of,
                required_tickers=tickers,
                coverage=(),
                capture_phase=phase,
            )
        )

        new_coverage = advance_coverage(
            journal=coverage_base,
            successful_tickers=tickers,
            covered_through=as_of,
        )

        merged = merge_journal_state(
            prior_journal=(
                prior.journal
                if prior is not None
                else None
            ),
            as_of_date=as_of,
            capture_phase=phase,
            required_tickers=tickers,
            coverage=new_coverage,
            current_certified=tuple(
                current_certified
            ),
            current_blockers=tuple(
                current_blockers
            ),
            current_blocker_resolutions=tuple(
                current_blocker_resolutions
            ),
        )

        prior_metadata = None

        if prior is not None:
            prior_metadata = {
                "path": str(
                    prior.path
                ),
                "file_sha256": (
                    prior.file_sha256
                ),
                "journal_sha256": (
                    prior.journal_sha256
                ),
                "as_of_date": (
                    prior.journal.as_of_date
                ),
                "capture_phase": (
                    prior.journal.capture_phase
                ),
            }

        batch_payload = {
            "schema_version": SCHEMA,
            "status": "COMPLETE",
            "commit_policy": (
                "IMMUTABLE_BATCH_FIRST_JOURNAL_COMMIT_LAST"
            ),
            "batch_root": str(
                final_batch
            ),
            "journal_target": str(
                journal_target
            ),
            "as_of_date": as_of,
            "capture_phase": phase,
            "required_tickers": list(
                tickers
            ),
            "discovery_plan": {
                "date_from": (
                    plan.date_from
                ),
                "date_to": plan.date_to,
            },
            "discovery_manifest_relpath": (
                "discovery/DISCOVERY_MANIFEST.json"
            ),
            "discovery_manifest_sha256": (
                sha256_path(
                    discovery_manifest
                )
            ),
            "prior_journal": (
                prior_metadata
            ),
            "dispositions": dispositions,
            "journal": journal_payload(
                merged
            ),
            "journal_sha256": (
                journal_hash(
                    merged
                )
            ),
        }

        sealed = seal_batch_manifest(
            batch_payload
        )

        batch_manifest_stage = (
            stage
            / "BATCH_MANIFEST.json"
        )

        batch_manifest_stage.write_text(
            json.dumps(
                sealed,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        verify_batch_manifest_payload(
            json.loads(
                batch_manifest_stage.read_text(
                    encoding="utf-8"
                )
            )
        )

        if final_batch.exists():
            raise DividendAcquisitionBatchError(
                "BATCH_TARGET_APPEARED_DURING_RUN"
            )

        os.replace(
            stage,
            final_batch,
        )

        # COMMIT LAST:
        # only after the full immutable acquisition batch exists.
        written = write_journal_document(
            journal_target,
            merged,
            previous_journal_path=(
                prior.path
                if prior is not None
                else None
            ),
        )

    except Exception:
        if stage.exists():
            print(
                f"FAILED_BATCH_STAGE_PRESERVED={stage}",
                file=sys.stderr,
            )

        raise

    print(
        "DIVIDEND_ACQUISITION_BATCH_PASS"
    )
    print(
        f"batch={final_batch}"
    )
    print(
        f"journal={written.path}"
    )
    print(
        f"journal_sha256="
        f"{written.journal_sha256}"
    )
    print(
        f"candidate_count="
        f"{len(candidates)}"
    )
    print(
        f"certified_live="
        f"{sum(x['status'] == CERTIFIED_LIVE for x in dispositions)}"
    )
    print(
        f"historical_observed="
        f"{sum(x['status'] == HISTORICAL_OBSERVED for x in dispositions)}"
    )
    print(
        f"corroborating_only="
        f"{sum(x['status'] == CORROBORATING_ONLY for x in dispositions)}"
    )
    print(
        f"superseded="
        f"{sum(x['status'] == SUPERSEDED for x in dispositions)}"
    )
    print(
        f"blocked_live_unresolved="
        f"{sum(x['status'] == BLOCKED_LIVE_UNRESOLVED for x in dispositions)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
