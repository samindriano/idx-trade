from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.forward_dividend_acquisition_v1 import (
    CASH_DIVIDEND_CANDIDATE,
    PROVIDER_COMMIT,
)
from idx_trade.forward_dividend_semantic_review_v1 import (
    DividendSemanticReviewError,
    analyze_cash_dividend_documents,
)
from idx_trade.forward_dividend_v1 import (
    AUTHORITY,
    REVIEW_STATUS,
)

ATTACHMENT_SCHEMA = (
    "idx_trade_forward_dividend_attachment_capture_v1_1"
)
DISCOVERY_SCHEMA = (
    "idx_trade_forward_dividend_announcement_capture_v1"
)
REVIEW_SCHEMA = (
    "idx_trade_forward_dividend_semantic_review_v1"
)
FAIL_STATUS = (
    "FAIL_DIRECT_IDX_ANNOUNCEMENT_ATTACHMENT_TERMS_NOT_ADMITTED"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)

    return h.hexdigest()


def extract_pdf_text(path: Path) -> tuple[str, int]:
    reader = PdfReader(str(path))
    parts = []

    for page in reader.pages:
        parts.append(page.extract_text() or "")

    return "\n".join(parts), len(reader.pages)


def exact_announcement_raw_sha(
    *,
    discovery_path: Path,
    discovery: dict[str, Any],
    ticker: str,
    announcement_id: str,
) -> str:
    raw_artifacts = discovery.get("raw_artifacts")

    if not isinstance(raw_artifacts, list):
        raise RuntimeError("DISCOVERY_RAW_ARTIFACTS_INVALID")

    matches: list[str] = []

    for row in raw_artifacts:
        if not isinstance(row, dict):
            raise RuntimeError("DISCOVERY_RAW_ARTIFACT_ROW_INVALID")

        if str(row.get("ticker") or "").upper() != ticker:
            continue

        relative = str(row.get("path") or "")

        if not relative:
            raise RuntimeError("DISCOVERY_RAW_ARTIFACT_PATH_MISSING")

        path = discovery_path.parent / relative

        if not path.is_file():
            raise RuntimeError(
                f"DISCOVERY_RAW_ARTIFACT_MISSING:{relative}"
            )

        declared_sha = str(row.get("sha256") or "")
        actual_sha = sha256_path(path)

        if actual_sha != declared_sha:
            raise RuntimeError(
                f"DISCOVERY_RAW_ARTIFACT_SHA_MISMATCH:{relative}"
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(
                f"DISCOVERY_RAW_ARTIFACT_JSON_INVALID:{relative}"
            ) from exc

        replies = payload.get("Replies") if isinstance(payload, dict) else None

        if not isinstance(replies, list):
            raise RuntimeError(
                f"DISCOVERY_RAW_ARTIFACT_REPLIES_INVALID:{relative}"
            )

        found = False

        for item in replies:
            if not isinstance(item, dict):
                continue

            announcement = item.get("pengumuman")

            if not isinstance(announcement, dict):
                continue

            identity = str(
                announcement.get("Id2")
                or announcement.get("Id")
                or ""
            ).strip()

            if identity == announcement_id:
                found = True

        if found:
            matches.append(actual_sha)

    if len(matches) != 1:
        raise RuntimeError(
            f"ANNOUNCEMENT_RAW_PAGE_COUNT_INVALID:{len(matches)}"
        )

    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline generic semantic review of immutable official IDX "
            "cash-dividend attachment bytes."
        )
    )
    parser.add_argument("--attachment-dir", required=True)
    args = parser.parse_args()

    root = Path(args.attachment_dir).expanduser().resolve()

    attachment_manifest_path = (
        root / "ATTACHMENT_CAPTURE_MANIFEST.json"
    )

    if not attachment_manifest_path.is_file():
        raise SystemExit(
            f"STOP: attachment manifest missing: "
            f"{attachment_manifest_path}"
        )

    review_path = root / "ATTACHMENT_REVIEW.json"

    if review_path.exists():
        raise SystemExit(
            f"STOP: review already exists: {review_path}"
        )

    attachment_manifest = json.loads(
        attachment_manifest_path.read_text(encoding="utf-8")
    )

    if (
        attachment_manifest.get("schema_version")
        != ATTACHMENT_SCHEMA
    ):
        raise RuntimeError("ATTACHMENT_MANIFEST_SCHEMA_MISMATCH")

    if (
        attachment_manifest.get("status")
        != "COMPLETE_AWAITING_SEMANTIC_REVIEW"
    ):
        raise RuntimeError("ATTACHMENT_MANIFEST_STATUS_INVALID")

    if attachment_manifest.get("provider_commit") != PROVIDER_COMMIT:
        raise RuntimeError("ATTACHMENT_PROVIDER_COMMIT_MISMATCH")

    if int(attachment_manifest.get("retry_count") or 0) != 0:
        raise RuntimeError("ATTACHMENT_RETRY_COUNT_NOT_ZERO")

    candidate = attachment_manifest.get("candidate")

    if not isinstance(candidate, dict):
        raise RuntimeError("ATTACHMENT_CANDIDATE_INVALID")

    if candidate.get("classification") != CASH_DIVIDEND_CANDIDATE:
        raise RuntimeError("CANDIDATE_NOT_CASH_DIVIDEND")

    ticker = str(candidate.get("ticker") or "").strip().upper()
    announcement_id = str(
        candidate.get("announcement_id") or ""
    ).strip()

    if not ticker or not announcement_id:
        raise RuntimeError("CANDIDATE_IDENTITY_MISSING")

    discovery_path = Path(
        str(
            attachment_manifest.get(
                "source_discovery_manifest_path"
            )
            or ""
        )
    ).expanduser().resolve()

    if not discovery_path.is_file():
        raise RuntimeError("SOURCE_DISCOVERY_MANIFEST_MISSING")

    discovery_bytes = discovery_path.read_bytes()
    discovery_sha = sha256_bytes(discovery_bytes)

    if (
        discovery_sha
        != attachment_manifest.get(
            "source_discovery_manifest_sha256"
        )
    ):
        raise RuntimeError("SOURCE_DISCOVERY_MANIFEST_SHA_MISMATCH")

    discovery = json.loads(discovery_bytes.decode("utf-8"))

    if discovery.get("schema_version") != DISCOVERY_SCHEMA:
        raise RuntimeError("SOURCE_DISCOVERY_SCHEMA_MISMATCH")

    if discovery.get("status") != "COMPLETE":
        raise RuntimeError("SOURCE_DISCOVERY_NOT_COMPLETE")

    discovery_candidates = discovery.get("candidates")

    if not isinstance(discovery_candidates, list):
        raise RuntimeError("SOURCE_DISCOVERY_CANDIDATES_INVALID")

    exact_candidates = [
        row
        for row in discovery_candidates
        if isinstance(row, dict)
        and str(row.get("ticker") or "").strip().upper() == ticker
        and str(row.get("announcement_id") or "").strip()
        == announcement_id
    ]

    if len(exact_candidates) != 1:
        raise RuntimeError(
            f"SOURCE_DISCOVERY_EXACT_CANDIDATE_COUNT:"
            f"{len(exact_candidates)}"
        )

    if exact_candidates[0] != candidate:
        candidate_without_attachments = dict(
            exact_candidates[0]
        )
        candidate_without_attachments.pop("attachments", None)

        if candidate_without_attachments != candidate:
            raise RuntimeError(
                "SOURCE_DISCOVERY_CANDIDATE_METADATA_MISMATCH"
            )

    source_raw_sha = exact_announcement_raw_sha(
        discovery_path=discovery_path,
        discovery=discovery,
        ticker=ticker,
        announcement_id=announcement_id,
    )

    rows = attachment_manifest.get("attachments")

    if not isinstance(rows, list) or not rows:
        raise RuntimeError("ATTACHMENT_ROWS_EMPTY")

    documents: list[dict[str, Any]] = []
    texts: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("ATTACHMENT_ROW_INVALID")

        filename = str(row.get("pdf_filename") or "").strip()

        if not filename or Path(filename).name != filename:
            raise RuntimeError("ATTACHMENT_FILENAME_INVALID")

        path = root / filename

        if not path.is_file():
            raise RuntimeError(
                f"ATTACHMENT_FILE_MISSING:{filename}"
            )

        actual_sha = sha256_path(path)
        declared_sha = str(row.get("sha256") or "")

        if actual_sha != declared_sha:
            raise RuntimeError(
                f"ATTACHMENT_SHA_MISMATCH:{filename}"
            )

        raw = path.read_bytes()

        if not raw.startswith(b"%PDF-"):
            raise RuntimeError(
                f"ATTACHMENT_NOT_PDF:{filename}"
            )

        text, page_count = extract_pdf_text(path)
        texts.append(text)

        normalized_sample = " ".join(text.split())[:1200]

        documents.append(
            {
                "pdf_filename": filename,
                "original_filename": row.get(
                    "original_filename"
                ),
                "sha256": actual_sha,
                "page_count": page_count,
                "text_char_count": len(text),
                "text_sample": normalized_sample,
            }
        )

    failures: list[str] = []

    try:
        semantics = analyze_cash_dividend_documents(
            texts,
            ticker=ticker,
        )
    except DividendSemanticReviewError as exc:
        semantics = None
        failures.append(str(exc))

    if semantics is not None:
        expected_event = {
            "ticker": semantics.ticker,
            "gross_dividend_per_share_idr": (
                semantics.gross_dividend_per_share_idr
            ),
            "cum_regular_negotiated": (
                semantics.cum_regular_negotiated
            ),
            "ex_regular_negotiated": (
                semantics.ex_regular_negotiated
            ),
            "record_date": semantics.record_date,
            "payment_date": semantics.payment_date,
        }

        semantic_matches = {
            "ticker": semantics.ticker_match,
            "dividend_subject": (
                semantics.dividend_subject_match
            ),
            "dividend_per_share": True,
            "cum_regular_negotiated": True,
            "ex_regular_negotiated": True,
            "record_date": True,
            "payment_date": True,
        }

        status = REVIEW_STATUS
        authority = AUTHORITY
    else:
        expected_event = None
        semantic_matches = {
            "ticker": False,
            "dividend_subject": False,
            "dividend_per_share": False,
            "cum_regular_negotiated": False,
            "ex_regular_negotiated": False,
            "record_date": False,
            "payment_date": False,
        }

        status = FAIL_STATUS
        authority = None

    announcement = {
        "id": announcement_id,
        "number": str(
            candidate.get("announcement_number") or ""
        ),
        "date": str(
            candidate.get("announcement_timestamp") or ""
        ),
        "code": ticker,
        "title": str(candidate.get("title") or ""),
        "form_id": str(candidate.get("form_id") or ""),
    }

    report = {
        "schema_version": REVIEW_SCHEMA,
        "status": status,
        "authority_recommendation": authority,
        "source_announcement_raw_sha256": source_raw_sha,
        "source_discovery_manifest_sha256": discovery_sha,
        "source_attachment_manifest_sha256": sha256_path(
            attachment_manifest_path
        ),
        "announcement": announcement,
        "documents": documents,
        "expected_event": expected_event,
        "semantic_matches": semantic_matches,
        "contributing_document_count": (
            semantics.contributing_document_count
            if semantics is not None
            else 0
        ),
        "failures": failures,
        "warnings": [],
        "link_dividend_role": (
            "LAGGING_CORROBORATION_NOT_FORWARD_AUTHORITY"
        ),
        "zapi_role": "OPTIONAL_PARITY_ONLY",
    }

    review_path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, sort_keys=True))

    if failures:
        return 2

    print("GENERIC_DIVIDEND_SEMANTIC_REVIEW_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
