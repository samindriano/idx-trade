from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from pypdf import PdfReader

from .forward_dividend_v1 import CertifiedCashDividend


REVIEW_SCHEMA_V1_2 = "idx_trade_forward_dividend_semantic_review_v1_2"
CERTIFICATION_SCHEMA_V1_2 = "idx_trade_cash_dividend_certification_v1_2"

AUTHORITY_V1_2 = "DIRECT_IDX_ANNOUNCEMENT_PLUS_HASHED_ATTACHMENT"
REVIEW_STATUS_V1_2 = (
    "PASS_DIRECT_IDX_ANNOUNCEMENT_RECORD_ATTACHMENT_TERMS_ELIGIBLE_FOR_V1_2"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TICKER_RE = re.compile(r"^[A-Z0-9]{1,12}$")


class ForwardDividendProvenanceV12Error(RuntimeError):
    pass


@dataclass(frozen=True)
class ExactAnnouncementProvenance:
    announcement_record: dict[str, Any]
    announcement_record_sha256: str
    source_raw_page_sha256: tuple[str, ...]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)

    return h.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def resolve_file_by_sha_within_root_v1_2(
    *,
    declared_path: Path,
    declared_sha256: str,
    search_root: Path,
    missing_code: str,
    mismatch_code: str,
    ambiguous_code: str,
) -> Path:
    """
    Resolve an immutable artifact without trusting a stale staging path.

    Rules:
    1. If declared_path exists, it MUST hash to declared_sha256.
    2. If declared_path no longer exists (for example after atomic
       .partial -> final batch rename), search only below search_root.
    3. Candidate basename must match the declared basename.
    4. Exactly one SHA-identical match is required.
    5. Zero matches or multiple matches fail closed.

    The SHA is the authority. Path recovery is transport/durability
    plumbing only and never changes canonical economic identity.
    """

    declared = Path(declared_path).expanduser()
    root = Path(search_root).expanduser()

    expected_sha = _sha(
        declared_sha256,
        mismatch_code,
    )

    if declared.is_file():
        actual_sha = sha256_path(declared)

        if actual_sha != expected_sha:
            raise ForwardDividendProvenanceV12Error(
                mismatch_code
            )

        return declared.resolve()

    if not root.is_dir():
        raise ForwardDividendProvenanceV12Error(
            missing_code
        )

    basename = declared.name

    if not basename:
        raise ForwardDividendProvenanceV12Error(
            missing_code
        )

    matches: list[Path] = []

    for candidate in root.rglob(basename):
        if not candidate.is_file():
            continue

        try:
            actual_sha = sha256_path(candidate)
        except OSError:
            continue

        if actual_sha == expected_sha:
            matches.append(candidate.resolve())

    unique_matches = sorted(
        set(matches),
        key=lambda value: str(value).lower(),
    )

    if not unique_matches:
        raise ForwardDividendProvenanceV12Error(
            missing_code
        )

    if len(unique_matches) != 1:
        raise ForwardDividendProvenanceV12Error(
            ambiguous_code
        )

    return unique_matches[0]


def discovery_search_root_from_declared_path_v1_2(
    declared_path: Path,
) -> Path:
    """
    Bound stale discovery-manifest recovery to its acquisition
    `batches` directory. Never scan arbitrary drives.
    """

    declared = Path(declared_path).expanduser()

    parts = declared.parts

    batches_index = None

    for index, part in enumerate(parts):
        if part.lower() == "batches":
            batches_index = index
            break

    if batches_index is None:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DISCOVERY_BATCH_ROOT_UNRESOLVED"
        )

    if batches_index == 0:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DISCOVERY_BATCH_ROOT_UNRESOLVED"
        )

    root = Path(*parts[: batches_index + 1])

    return root


def resolve_discovery_manifest_path_v1_2(
    *,
    declared_path: Path,
    declared_sha256: str,
) -> Path:
    search_root = discovery_search_root_from_declared_path_v1_2(
        declared_path
    )

    return resolve_file_by_sha_within_root_v1_2(
        declared_path=declared_path,
        declared_sha256=declared_sha256,
        search_root=search_root,
        missing_code=(
            "DIVIDEND_V1_2_SOURCE_DISCOVERY_MANIFEST_MISSING"
        ),
        mismatch_code=(
            "DIVIDEND_V1_2_SOURCE_DISCOVERY_MANIFEST_SHA_MISMATCH"
        ),
        ambiguous_code=(
            "DIVIDEND_V1_2_SOURCE_DISCOVERY_MANIFEST_AMBIGUOUS"
        ),
    )


def _ticker(value: object) -> str:
    symbol = str(value or "").strip().upper().replace(".JK", "")

    if not _TICKER_RE.fullmatch(symbol):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_TICKER_INVALID"
        )

    return symbol


def _sha(value: object, code: str) -> str:
    text = str(value or "").strip()

    if not _SHA256_RE.fullmatch(text):
        raise ForwardDividendProvenanceV12Error(code)

    return text


def _iso_date(value: object, code: str) -> str:
    text = str(value or "").strip()

    try:
        parsed = date.fromisoformat(text[:10])
    except Exception as exc:
        raise ForwardDividendProvenanceV12Error(code) from exc

    return parsed.isoformat()


def _timestamp(value: object) -> str:
    text = str(value or "").strip()

    if not text:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ANNOUNCEMENT_TIMESTAMP_INVALID"
        )

    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ANNOUNCEMENT_TIMESTAMP_INVALID"
        ) from exc

    return text


def canonical_decimal_string(value: object) -> str:
    text = str(value or "").strip()

    if not text:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_AMOUNT_INVALID"
        )

    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_AMOUNT_INVALID"
        ) from exc

    if not parsed.is_finite() or parsed <= 0:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_AMOUNT_INVALID"
        )

    normalized = parsed.normalize()

    if normalized == normalized.to_integral():
        return str(int(normalized))

    return format(normalized, "f")


def announcement_identity_from_record(
    record: Mapping[str, Any],
) -> tuple[str, str]:
    announcement_id = str(
        record.get("Id2")
        or record.get("Id")
        or ""
    ).strip()

    announcement_number = str(
        record.get("NoPengumuman")
        or record.get("AnnouncementNo")
        or ""
    ).strip()

    if not announcement_id and not announcement_number:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ANNOUNCEMENT_IDENTITY_MISSING"
        )

    return announcement_id, announcement_number


def announcement_projection(
    record: Mapping[str, Any],
) -> dict[str, str]:
    announcement_id, announcement_number = (
        announcement_identity_from_record(record)
    )

    ticker = _ticker(record.get("Kode_Emiten"))

    timestamp = str(
        record.get("TglPengumuman")
        or record.get("CreatedDate")
        or ""
    ).strip()

    if not timestamp:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ANNOUNCEMENT_TIMESTAMP_MISSING"
        )

    title = str(
        record.get("JudulPengumuman")
        or record.get("PerihalPengumuman")
        or ""
    ).strip()

    return {
        "ticker": ticker,
        "announcement_id": announcement_id,
        "announcement_number": announcement_number,
        "announcement_timestamp": timestamp,
        "title": title,
        "form_id": str(record.get("Form_Id") or "").strip(),
    }


def candidate_identity(
    candidate: Mapping[str, Any],
) -> tuple[str, str]:
    announcement_id = str(
        candidate.get("announcement_id") or ""
    ).strip()

    announcement_number = str(
        candidate.get("announcement_number") or ""
    ).strip()

    if not announcement_id and not announcement_number:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_CANDIDATE_IDENTITY_MISSING"
        )

    return announcement_id, announcement_number


def record_matches_candidate(
    record: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> bool:
    expected_ticker = _ticker(candidate.get("ticker"))

    try:
        projection = announcement_projection(record)
    except ForwardDividendProvenanceV12Error:
        return False

    if projection["ticker"] != expected_ticker:
        return False

    candidate_id, candidate_number = candidate_identity(candidate)

    # ID is preferred whenever the candidate possesses one.
    if candidate_id:
        return projection["announcement_id"] == candidate_id

    return (
        bool(candidate_number)
        and projection["announcement_number"] == candidate_number
    )


def validate_candidate_against_record(
    *,
    candidate: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    if not record_matches_candidate(record, candidate):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_CANDIDATE_RECORD_IDENTITY_MISMATCH"
        )

    projection = announcement_projection(record)

    expected_fields = (
        "ticker",
        "announcement_id",
        "announcement_number",
        "announcement_timestamp",
        "title",
        "form_id",
    )

    for field in expected_fields:
        candidate_value = str(candidate.get(field) or "").strip()
        record_value = str(projection.get(field) or "").strip()

        # Discovery candidate can legitimately lack one of the optional
        # identity aliases. If populated, however, it must match exactly.
        if candidate_value and candidate_value != record_value:
            raise ForwardDividendProvenanceV12Error(
                f"DIVIDEND_V1_2_CANDIDATE_RECORD_FIELD_MISMATCH:{field}"
            )


def resolve_exact_announcement_provenance(
    *,
    discovery_path: Path,
    discovery: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> ExactAnnouncementProvenance:
    raw_artifacts = discovery.get("raw_artifacts")

    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DISCOVERY_RAW_ARTIFACTS_INVALID"
        )

    expected_ticker = _ticker(candidate.get("ticker"))

    records_by_sha: dict[str, dict[str, Any]] = {}
    raw_page_shas: set[str] = set()

    for row in raw_artifacts:
        if not isinstance(row, dict):
            raise ForwardDividendProvenanceV12Error(
                "DIVIDEND_V1_2_DISCOVERY_RAW_ARTIFACT_ROW_INVALID"
            )

        row_ticker = str(row.get("ticker") or "").strip().upper()

        if row_ticker and row_ticker != expected_ticker:
            continue

        relative = str(row.get("path") or "").strip()

        if not relative:
            raise ForwardDividendProvenanceV12Error(
                "DIVIDEND_V1_2_DISCOVERY_RAW_ARTIFACT_PATH_MISSING"
            )

        declared_sha = _sha(
            row.get("sha256"),
            "DIVIDEND_V1_2_DISCOVERY_RAW_ARTIFACT_SHA_INVALID",
        )

        declared_raw_path = Path(relative).expanduser()

        if not declared_raw_path.is_absolute():
            declared_raw_path = (
                discovery_path.parent / declared_raw_path
            )

        path = resolve_file_by_sha_within_root_v1_2(
            declared_path=declared_raw_path,
            declared_sha256=declared_sha,
            search_root=discovery_path.parent,
            missing_code=(
                "DIVIDEND_V1_2_DISCOVERY_RAW_ARTIFACT_MISSING:"
                f"{relative}"
            ),
            mismatch_code=(
                "DIVIDEND_V1_2_DISCOVERY_RAW_ARTIFACT_SHA_MISMATCH:"
                f"{relative}"
            ),
            ambiguous_code=(
                "DIVIDEND_V1_2_DISCOVERY_RAW_ARTIFACT_AMBIGUOUS:"
                f"{relative}"
            ),
        )

        actual_sha = sha256_path(path)

        if actual_sha != declared_sha:
            raise ForwardDividendProvenanceV12Error(
                f"DIVIDEND_V1_2_DISCOVERY_RAW_ARTIFACT_SHA_MISMATCH:{relative}"
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ForwardDividendProvenanceV12Error(
                f"DIVIDEND_V1_2_DISCOVERY_RAW_ARTIFACT_JSON_INVALID:{relative}"
            ) from exc

        replies = (
            payload.get("Replies")
            if isinstance(payload, dict)
            else None
        )

        if not isinstance(replies, list):
            raise ForwardDividendProvenanceV12Error(
                f"DIVIDEND_V1_2_DISCOVERY_RAW_ARTIFACT_REPLIES_INVALID:{relative}"
            )

        page_contains_match = False

        for item in replies:
            if not isinstance(item, dict):
                continue

            record = item.get("pengumuman")

            if not isinstance(record, dict):
                continue

            if not record_matches_candidate(record, candidate):
                continue

            page_contains_match = True

            record_copy = json.loads(
                canonical_json_bytes(record).decode("utf-8")
            )
            record_sha = canonical_sha256(record_copy)

            previous = records_by_sha.get(record_sha)

            if previous is not None and previous != record_copy:
                raise ForwardDividendProvenanceV12Error(
                    "DIVIDEND_V1_2_ANNOUNCEMENT_CANONICAL_HASH_COLLISION"
                )

            records_by_sha[record_sha] = record_copy

        if page_contains_match:
            raw_page_shas.add(actual_sha)

    if not records_by_sha:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_EXACT_ANNOUNCEMENT_NOT_FOUND"
        )

    if len(records_by_sha) != 1:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_EXACT_ANNOUNCEMENT_CONFLICT"
        )

    record_sha, record = next(iter(records_by_sha.items()))

    validate_candidate_against_record(
        candidate=candidate,
        record=record,
    )

    if not raw_page_shas:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_SOURCE_RAW_PAGE_MISSING"
        )

    return ExactAnnouncementProvenance(
        announcement_record=record,
        announcement_record_sha256=record_sha,
        source_raw_page_sha256=tuple(sorted(raw_page_shas)),
    )


def _event_dates(
    *,
    cum_date: object,
    ex_date: object,
    record_date: object,
    payment_date: object,
) -> tuple[str, str, str, str]:
    cum = _iso_date(cum_date, "DIVIDEND_V1_2_CUM_DATE_INVALID")
    ex = _iso_date(ex_date, "DIVIDEND_V1_2_EX_DATE_INVALID")
    record = _iso_date(
        record_date,
        "DIVIDEND_V1_2_RECORD_DATE_INVALID",
    )
    payment = _iso_date(
        payment_date,
        "DIVIDEND_V1_2_PAYMENT_DATE_INVALID",
    )

    if not (cum < ex <= record <= payment):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DATE_ORDER_INVALID"
        )

    return cum, ex, record, payment


def canonical_event_evidence_v1_2(
    *,
    announcement_record_sha256: str,
    document_sha256: Sequence[str],
    ticker: object,
    announcement_timestamp: object,
    gross_dividend_per_share_idr: object,
    cum_date: object,
    ex_date: object,
    record_date: object,
    payment_date: object,
) -> dict[str, object]:
    record_sha = _sha(
        announcement_record_sha256,
        "DIVIDEND_V1_2_ANNOUNCEMENT_RECORD_SHA_INVALID",
    )

    docs = tuple(
        sorted(
            {
                _sha(
                    value,
                    "DIVIDEND_V1_2_DOCUMENT_SHA_INVALID",
                )
                for value in document_sha256
            }
        )
    )

    if not docs:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DOCUMENTS_EMPTY"
        )

    symbol = _ticker(ticker)
    announced = _timestamp(announcement_timestamp)
    amount = canonical_decimal_string(
        gross_dividend_per_share_idr
    )

    cum, ex, record, payment = _event_dates(
        cum_date=cum_date,
        ex_date=ex_date,
        record_date=record_date,
        payment_date=payment_date,
    )

    # A correction/revision may be published after the economic cum-date
    # while correcting an already effective schedule.  Knowledge time remains
    # the announcement timestamp; the historical event is never backdated
    # into the runtime merely because its cum-date is earlier.

    return {
        "schema_version": CERTIFICATION_SCHEMA_V1_2,
        "authority": AUTHORITY_V1_2,
        "announcement_record_sha256": record_sha,
        "document_sha256": list(docs),
        "ticker": symbol,
        "announcement_timestamp": announced,
        "gross_dividend_per_share_idr": amount,
        "cum_date": cum,
        "ex_date": ex,
        "record_date": record,
        "payment_date": payment,
    }


def event_sha256_v1_2(evidence: Mapping[str, Any]) -> str:
    return canonical_sha256(dict(evidence))


def certify_direct_idx_dividend_from_attachment_review_v1_2(
    review_path: str | Path,
    attachment_dir: str | Path,
) -> CertifiedCashDividend:
    review_file = Path(review_path).expanduser().resolve()
    root = Path(attachment_dir).expanduser().resolve()

    if not review_file.is_file():
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_REVIEW_MISSING"
        )

    try:
        review = json.loads(
            review_file.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_REVIEW_INVALID"
        ) from exc

    if review.get("schema_version") != REVIEW_SCHEMA_V1_2:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_REVIEW_SCHEMA_MISMATCH"
        )

    if review.get("status") != REVIEW_STATUS_V1_2:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_REVIEW_NOT_ADMITTED"
        )

    if review.get("authority_recommendation") != AUTHORITY_V1_2:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_AUTHORITY_MISMATCH"
        )

    transport = review.get("transport_provenance")

    if not isinstance(transport, dict):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_TRANSPORT_PROVENANCE_MISSING"
        )

    announcement_provenance = review.get(
        "announcement_provenance"
    )

    if not isinstance(announcement_provenance, dict):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ANNOUNCEMENT_PROVENANCE_MISSING"
        )

    exact_record = announcement_provenance.get(
        "exact_announcement_record"
    )
    declared_record_sha = _sha(
        announcement_provenance.get(
            "announcement_record_sha256"
        ),
        "DIVIDEND_V1_2_ANNOUNCEMENT_RECORD_SHA_INVALID",
    )

    if not isinstance(exact_record, dict):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_EXACT_ANNOUNCEMENT_RECORD_INVALID"
        )

    if canonical_sha256(exact_record) != declared_record_sha:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ANNOUNCEMENT_RECORD_SHA_MISMATCH"
        )

    announcement = review.get("announcement")

    if not isinstance(announcement, dict):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ANNOUNCEMENT_PROJECTION_MISSING"
        )

    validate_candidate_against_record(
        candidate={
            "ticker": announcement.get("code"),
            "announcement_id": announcement.get("id"),
            "announcement_number": announcement.get("number"),
            "announcement_timestamp": announcement.get("date"),
            "title": announcement.get("title"),
            "form_id": announcement.get("form_id"),
        },
        record=exact_record,
    )

    # Revalidate the complete source chain instead of trusting hashes merely
    # embedded in the review JSON. The reviewer records both absolute legacy
    # paths and the resolved path; the latter is required for V1.2. Existing
    # V1.1 artifacts remain supported by their original verifier.
    declared_discovery_relpath = str(
        transport.get("source_discovery_manifest_relpath") or ""
    ).strip()
    declared_discovery = str(
        transport.get("source_discovery_manifest_resolved_path")
        or transport.get("source_discovery_manifest_declared_path")
        or ""
    ).strip()
    if declared_discovery_relpath:
        declared_discovery_path = (
            root / declared_discovery_relpath
        ).resolve()
    else:
        declared_discovery_path = Path(declared_discovery)
    declared_discovery_sha = str(
        transport.get("source_discovery_manifest_sha256") or ""
    ).strip().lower()
    declared_attachment_sha = str(
        transport.get("source_attachment_manifest_sha256") or ""
    ).strip().lower()
    declared_raw_shas = tuple(sorted({
        str(value).strip().lower()
        for value in (transport.get("source_raw_page_sha256") or ())
        if str(value).strip()
    }))

    if not declared_discovery and not declared_discovery_relpath:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DISCOVERY_BINDING_INCOMPLETE"
        )
    if not _SHA256_RE.fullmatch(declared_discovery_sha):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DISCOVERY_BINDING_INCOMPLETE"
        )

    discovery_path = resolve_discovery_manifest_path_v1_2(
        declared_path=declared_discovery_path,
        declared_sha256=declared_discovery_sha,
    )
    discovery_bytes = discovery_path.read_bytes()
    if sha256_bytes(discovery_bytes) != declared_discovery_sha:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DISCOVERY_MANIFEST_SHA_MISMATCH"
        )

    try:
        discovery = json.loads(discovery_bytes.decode("utf-8"))
    except Exception as exc:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DISCOVERY_MANIFEST_JSON_INVALID"
        ) from exc

    provenance = resolve_exact_announcement_provenance(
        discovery_path=discovery_path,
        discovery=discovery,
        candidate={
            "ticker": announcement.get("code"),
            "announcement_id": announcement.get("id"),
            "announcement_number": announcement.get("number"),
            "announcement_timestamp": announcement.get("date"),
            "title": announcement.get("title"),
            "form_id": announcement.get("form_id"),
        },
    )
    if provenance.announcement_record_sha256 != declared_record_sha:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DISCOVERY_RECORD_SHA_MISMATCH"
        )
    if tuple(provenance.source_raw_page_sha256) != declared_raw_shas:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_RAW_PAGE_SHA_MISMATCH"
        )

    attachment_manifest_path = root / "ATTACHMENT_CAPTURE_MANIFEST.json"
    if not attachment_manifest_path.is_file() or not _SHA256_RE.fullmatch(
        declared_attachment_sha
    ):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ATTACHMENT_MANIFEST_BINDING_INCOMPLETE"
        )
    if sha256_path(attachment_manifest_path) != declared_attachment_sha:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ATTACHMENT_MANIFEST_SHA_MISMATCH"
        )
    try:
        attachment_manifest = json.loads(
            attachment_manifest_path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ATTACHMENT_MANIFEST_JSON_INVALID"
        ) from exc
    if attachment_manifest.get("status") != "COMPLETE_AWAITING_SEMANTIC_REVIEW":
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ATTACHMENT_MANIFEST_STATUS_INVALID"
        )

    manifest_candidate = attachment_manifest.get("candidate")
    if not isinstance(manifest_candidate, dict):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ATTACHMENT_CANDIDATE_INVALID"
        )
    if (
        str(manifest_candidate.get("ticker") or "").strip().upper()
        != str(announcement.get("code") or "").strip().upper()
        or str(manifest_candidate.get("announcement_id") or "").strip()
        != str(announcement.get("id") or "").strip()
        or str(manifest_candidate.get("announcement_number") or "").strip()
        != str(announcement.get("number") or "").strip()
    ):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ATTACHMENT_CANDIDATE_MISMATCH"
        )

    semantic = review.get("semantic_matches")

    required_semantics = {
        "ticker",
        "dividend_subject",
        "dividend_per_share",
        "cum_regular_negotiated",
        "ex_regular_negotiated",
        "record_date",
        "payment_date",
    }

    if (
        not isinstance(semantic, dict)
        or any(
            semantic.get(key) is not True
            for key in required_semantics
        )
    ):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_SEMANTIC_GATE_INCOMPLETE"
        )

    documents = review.get("documents")

    if not isinstance(documents, list) or not documents:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_DOCUMENTS_MISSING"
        )

    document_shas: list[str] = []
    seen_filenames: set[str] = set()
    review_documents: dict[str, str] = {}

    for row in documents:
        if not isinstance(row, dict):
            raise ForwardDividendProvenanceV12Error(
                "DIVIDEND_V1_2_DOCUMENT_ROW_INVALID"
            )

        filename = str(
            row.get("pdf_filename") or ""
        ).strip()

        if (
            not filename
            or Path(filename).name != filename
            or filename in seen_filenames
        ):
            raise ForwardDividendProvenanceV12Error(
                "DIVIDEND_V1_2_DOCUMENT_FILENAME_INVALID"
            )

        seen_filenames.add(filename)

        declared_sha = _sha(
            row.get("sha256"),
            "DIVIDEND_V1_2_DOCUMENT_SHA_INVALID",
        )

        path = root / filename

        if not path.is_file():
            raise ForwardDividendProvenanceV12Error(
                f"DIVIDEND_V1_2_DOCUMENT_MISSING:{filename}"
            )

        if sha256_path(path) != declared_sha:
            raise ForwardDividendProvenanceV12Error(
                f"DIVIDEND_V1_2_DOCUMENT_SHA_MISMATCH:{filename}"
            )

        document_shas.append(declared_sha)
        review_documents[filename] = declared_sha

    manifest_documents = attachment_manifest.get("attachments")
    if not isinstance(manifest_documents, list):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ATTACHMENT_ROWS_INVALID"
        )
    manifest_by_filename = {
        str(row.get("pdf_filename") or "").strip(): str(
            row.get("sha256") or ""
        ).strip().lower()
        for row in manifest_documents
        if isinstance(row, dict)
    }
    if manifest_by_filename != review_documents:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_ATTACHMENT_DOCUMENT_BINDING_MISMATCH"
        )

    expected = review.get("expected_event")

    if not isinstance(expected, dict):
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_EXPECTED_EVENT_MISSING"
        )

    if str(expected.get("ticker") or "").strip().upper() != str(
        announcement.get("code") or ""
    ).strip().upper():
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_EXPECTED_EVENT_TICKER_MISMATCH"
        )

    # Re-run the semantic authority on the immutable PDFs. This prevents a
    # modified review JSON from changing amount or date semantics while all
    # transport hashes still look self-consistent.
    try:
        from .forward_dividend_semantic_review_v1_2 import (
            analyze_cash_dividend_documents_v1_2,
        )

        texts = []
        for filename in review_documents:
            reader = PdfReader(str(root / filename))
            texts.append("\n".join(page.extract_text() or "" for page in reader.pages))
        semantic = analyze_cash_dividend_documents_v1_2(
            texts,
            ticker=str(announcement.get("code") or ""),
        )
    except Exception as exc:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_SEMANTIC_REPLAY_FAILED"
        ) from exc

    expected_amount = canonical_decimal_string(
        expected.get("gross_dividend_per_share_idr")
    )
    actual_amount = canonical_decimal_string(
        semantic.gross_dividend_per_share_idr
    )
    expected_schedule = (
        str(expected.get("cum_regular_negotiated") or ""),
        str(expected.get("ex_regular_negotiated") or ""),
        str(expected.get("record_date") or ""),
        str(expected.get("payment_date") or ""),
    )
    actual_schedule = (
        semantic.cum_regular_negotiated,
        semantic.ex_regular_negotiated,
        semantic.record_date,
        semantic.payment_date,
    )
    if actual_amount != expected_amount or actual_schedule != expected_schedule:
        raise ForwardDividendProvenanceV12Error(
            "DIVIDEND_V1_2_SEMANTIC_REVIEW_MISMATCH"
        )

    evidence = canonical_event_evidence_v1_2(
        announcement_record_sha256=declared_record_sha,
        document_sha256=document_shas,
        ticker=expected.get("ticker"),
        announcement_timestamp=announcement.get("date"),
        gross_dividend_per_share_idr=expected.get(
            "gross_dividend_per_share_idr"
        ),
        cum_date=expected.get("cum_regular_negotiated"),
        ex_date=expected.get("ex_regular_negotiated"),
        record_date=expected.get("record_date"),
        payment_date=expected.get("payment_date"),
    )

    evidence_sha = event_sha256_v1_2(evidence)

    return CertifiedCashDividend(
        event_id=(
            f"CASH_DIVIDEND_{evidence['ticker']}_"
            f"{evidence_sha[:24]}"
        ),
        ticker=str(evidence["ticker"]),
        announcement_timestamp=str(
            evidence["announcement_timestamp"]
        ),
        gross_dividend_per_share_idr=float(
            Decimal(
                str(
                    evidence[
                        "gross_dividend_per_share_idr"
                    ]
                )
            )
        ),
        cum_date=str(evidence["cum_date"]),
        ex_date=str(evidence["ex_date"]),
        record_date=str(evidence["record_date"]),
        payment_date=str(evidence["payment_date"]),
        source_evidence_sha256=evidence_sha,
        knowledge_at_timestamp=str(evidence["announcement_timestamp"]),
    )
