from __future__ import annotations

import argparse
import hashlib
import json
import os
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
from idx_trade.forward_dividend_provenance_v1_2 import (
    AUTHORITY_V1_2,
    REVIEW_SCHEMA_V1_2,
    REVIEW_STATUS_V1_2,
    resolve_discovery_manifest_path_v1_2,
    resolve_exact_announcement_provenance,
    sha256_bytes,
    sha256_path,
)


ATTACHMENT_SCHEMA = (
    "idx_trade_forward_dividend_attachment_capture_v1_1"
)
DISCOVERY_SCHEMA = (
    "idx_trade_forward_dividend_announcement_capture_v1"
)
FAIL_STATUS = (
    "FAIL_DIRECT_IDX_ANNOUNCEMENT_RECORD_ATTACHMENT_TERMS_NOT_ADMITTED_V1_2"
)


def extract_pdf_text(path: Path) -> tuple[str, int]:
    reader = PdfReader(str(path))
    parts: list[str] = []

    for page in reader.pages:
        parts.append(page.extract_text() or "")

    return "\n".join(parts), len(reader.pages)


def _semantic_analyzer():
    from idx_trade import (
        forward_dividend_semantic_review_v1_2 as semantic_v1_2,
    )

    for name in (
        "analyze_cash_dividend_documents",
        "analyze_cash_dividend_documents_v1_2",
    ):
        function = getattr(semantic_v1_2, name, None)

        if callable(function):
            return function

    raise RuntimeError(
        "DIVIDEND_V1_2_SEMANTIC_ANALYZER_NOT_FOUND"
    )


def _semantic_error_type():
    from idx_trade import (
        forward_dividend_semantic_review_v1_2 as semantic_v1_2,
    )

    for name in (
        "DividendSemanticReviewError",
        "DividendSemanticReviewV12Error",
    ):
        error_type = getattr(semantic_v1_2, name, None)

        if (
            isinstance(error_type, type)
            and issubclass(error_type, Exception)
        ):
            return error_type

    return Exception


def _candidate_match(
    row: dict[str, Any],
    candidate: dict[str, Any],
) -> bool:
    if (
        str(row.get("ticker") or "").strip().upper()
        != str(candidate.get("ticker") or "").strip().upper()
    ):
        return False

    expected_id = str(
        candidate.get("announcement_id") or ""
    ).strip()
    expected_number = str(
        candidate.get("announcement_number") or ""
    ).strip()

    row_id = str(
        row.get("announcement_id") or ""
    ).strip()
    row_number = str(
        row.get("announcement_number") or ""
    ).strip()

    if expected_id:
        return row_id == expected_id

    return bool(expected_number) and row_number == expected_number


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline V1.2 semantic review with stable exact IDX "
            "announcement-record provenance."
        )
    )
    parser.add_argument("--attachment-dir", required=True)
    args = parser.parse_args()

    root = Path(
        args.attachment_dir
    ).expanduser().resolve()

    attachment_manifest_path = (
        root / "ATTACHMENT_CAPTURE_MANIFEST.json"
    )

    if not attachment_manifest_path.is_file():
        raise SystemExit(
            f"STOP: attachment manifest missing: "
            f"{attachment_manifest_path}"
        )

    review_path = root / "ATTACHMENT_REVIEW_V1_2.json"

    if review_path.exists():
        raise SystemExit(
            f"STOP: V1.2 review already exists: {review_path}"
        )

    attachment_manifest_bytes = (
        attachment_manifest_path.read_bytes()
    )
    attachment_manifest = json.loads(
        attachment_manifest_bytes.decode("utf-8")
    )

    if (
        attachment_manifest.get("schema_version")
        != ATTACHMENT_SCHEMA
    ):
        raise RuntimeError(
            "ATTACHMENT_MANIFEST_SCHEMA_MISMATCH"
        )

    if (
        attachment_manifest.get("status")
        != "COMPLETE_AWAITING_SEMANTIC_REVIEW"
    ):
        raise RuntimeError(
            "ATTACHMENT_MANIFEST_STATUS_INVALID"
        )

    if (
        attachment_manifest.get("provider_commit")
        != PROVIDER_COMMIT
    ):
        raise RuntimeError(
            "ATTACHMENT_PROVIDER_COMMIT_MISMATCH"
        )

    if int(
        attachment_manifest.get("retry_count") or 0
    ) != 0:
        raise RuntimeError(
            "ATTACHMENT_RETRY_COUNT_NOT_ZERO"
        )

    candidate = attachment_manifest.get("candidate")

    if not isinstance(candidate, dict):
        raise RuntimeError(
            "ATTACHMENT_CANDIDATE_INVALID"
        )

    if (
        candidate.get("classification")
        != CASH_DIVIDEND_CANDIDATE
    ):
        raise RuntimeError(
            "CANDIDATE_NOT_CASH_DIVIDEND"
        )

    ticker = str(
        candidate.get("ticker") or ""
    ).strip().upper()

    announcement_id = str(
        candidate.get("announcement_id") or ""
    ).strip()

    announcement_number = str(
        candidate.get("announcement_number") or ""
    ).strip()

    if (
        not ticker
        or (
            not announcement_id
            and not announcement_number
        )
    ):
        raise RuntimeError(
            "CANDIDATE_IDENTITY_MISSING"
        )

    declared_discovery_path = Path(
        str(
            attachment_manifest.get(
                "source_discovery_manifest_relpath"
            )
            or attachment_manifest.get(
                "source_discovery_manifest_path"
            )
            or ""
        )
    ).expanduser()

    if not declared_discovery_path.is_absolute():
        declared_discovery_path = (
            root / declared_discovery_path
        ).resolve()

    declared_discovery_sha = str(
        attachment_manifest.get(
            "source_discovery_manifest_sha256"
        )
        or ""
    ).strip()

    discovery_path = (
        resolve_discovery_manifest_path_v1_2(
            declared_path=declared_discovery_path,
            declared_sha256=declared_discovery_sha,
        )
    )

    discovery_bytes = discovery_path.read_bytes()
    discovery_sha = sha256_bytes(discovery_bytes)

    if discovery_sha != declared_discovery_sha:
        raise RuntimeError(
            "SOURCE_DISCOVERY_MANIFEST_SHA_MISMATCH"
        )

    discovery = json.loads(
        discovery_bytes.decode("utf-8")
    )

    if (
        discovery.get("schema_version")
        != DISCOVERY_SCHEMA
    ):
        raise RuntimeError(
            "SOURCE_DISCOVERY_SCHEMA_MISMATCH"
        )

    if discovery.get("status") != "COMPLETE":
        raise RuntimeError(
            "SOURCE_DISCOVERY_NOT_COMPLETE"
        )

    discovery_candidates = discovery.get(
        "candidates"
    )

    if not isinstance(discovery_candidates, list):
        raise RuntimeError(
            "SOURCE_DISCOVERY_CANDIDATES_INVALID"
        )

    exact_candidates = [
        row
        for row in discovery_candidates
        if isinstance(row, dict)
        and _candidate_match(row, candidate)
    ]

    if len(exact_candidates) != 1:
        raise RuntimeError(
            "SOURCE_DISCOVERY_EXACT_CANDIDATE_COUNT:"
            f"{len(exact_candidates)}"
        )

    discovery_candidate = exact_candidates[0]

    candidate_without_attachments = dict(
        discovery_candidate
    )
    candidate_without_attachments.pop(
        "attachments",
        None,
    )

    attachment_candidate = dict(candidate)
    attachment_candidate.pop(
        "attachments",
        None,
    )

    if (
        candidate_without_attachments
        != attachment_candidate
    ):
        raise RuntimeError(
            "SOURCE_DISCOVERY_CANDIDATE_METADATA_MISMATCH"
        )

    provenance = (
        resolve_exact_announcement_provenance(
            discovery_path=discovery_path,
            discovery=discovery,
            candidate=candidate,
        )
    )

    rows = attachment_manifest.get("attachments")

    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            "ATTACHMENT_ROWS_EMPTY"
        )

    documents: list[dict[str, Any]] = []
    texts: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(
                "ATTACHMENT_ROW_INVALID"
            )

        filename = str(
            row.get("pdf_filename") or ""
        ).strip()

        if (
            not filename
            or Path(filename).name != filename
        ):
            raise RuntimeError(
                "ATTACHMENT_FILENAME_INVALID"
            )

        path = root / filename

        if not path.is_file():
            raise RuntimeError(
                f"ATTACHMENT_FILE_MISSING:{filename}"
            )

        actual_sha = sha256_path(path)
        declared_sha = str(
            row.get("sha256") or ""
        )

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

        normalized_sample = (
            " ".join(text.split())[:1200]
        )

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
    analyzer = _semantic_analyzer()
    semantic_error = _semantic_error_type()

    try:
        semantics = analyzer(
            texts,
            ticker=ticker,
        )
    except semantic_error as exc:
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

        status = REVIEW_STATUS_V1_2
        authority = AUTHORITY_V1_2
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
        "number": announcement_number,
        "date": str(
            candidate.get(
                "announcement_timestamp"
            )
            or ""
        ),
        "code": ticker,
        "title": str(
            candidate.get("title") or ""
        ),
        "form_id": str(
            candidate.get("form_id") or ""
        ),
    }

    discovery_relpath = os.path.relpath(
        discovery_path,
        start=root,
    ).replace("\\", "/")

    report = {
        "schema_version": REVIEW_SCHEMA_V1_2,
        "status": status,
        "authority_recommendation": authority,
        "transport_provenance": {
            "source_raw_page_sha256": list(
                provenance.source_raw_page_sha256
            ),
            "source_discovery_manifest_relpath": discovery_relpath,
            # Keep legacy fields durable too.  A staging absolute path is
            # operationally useful only during the child process and must
            # never become part of a final immutable batch artifact.
            "source_discovery_manifest_declared_path": discovery_relpath,
            "source_discovery_manifest_resolved_path": discovery_relpath,
            "source_discovery_manifest_sha256": (
                discovery_sha
            ),
            "source_attachment_manifest_sha256": (
                sha256_path(
                    attachment_manifest_path
                )
            ),
        },
        "announcement_provenance": {
            "exact_announcement_record": (
                provenance.announcement_record
            ),
            "announcement_record_sha256": (
                provenance.announcement_record_sha256
            ),
        },
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

    review_bytes = (
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")
    review_tmp = review_path.with_name(
        f".{review_path.name}.partial"
    )
    review_tmp.write_bytes(review_bytes)
    os.replace(review_tmp, review_path)

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
    )

    if failures:
        return 2

    print(
        "GENERIC_DIVIDEND_SEMANTIC_REVIEW_V1_2_PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
