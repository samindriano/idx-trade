from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any
import re


PROVIDER_REPOSITORY = "nichsedge/idx-bei"
PROVIDER_COMMIT = "75d6c0f74fa360d225794c70c383348977de6798"
UPSTREAM_BASE_URL = "https://www.idx.co.id/primary"
ANNOUNCEMENT_ENDPOINT = "/ListedCompany/GetAnnouncement"

CASH_DIVIDEND_CANDIDATE = "CASH_DIVIDEND_CANDIDATE"
AMBIGUOUS_DIVIDEND_CANDIDATE = "AMBIGUOUS_DIVIDEND_CANDIDATE"
UNSUPPORTED_NON_CASH_DIVIDEND = "UNSUPPORTED_NON_CASH_DIVIDEND"

_CASH_TERMS = (
    "dividen tunai",
    "cash dividend",
    "dividen interim",
    "interim dividend",
)

_DIVIDEND_TERMS = (
    "dividen",
    "dividend",
)

_NON_CASH_TERMS = (
    "dividen saham",
    "stock dividend",
    "saham bonus",
    "bonus share",
    "bonus shares",
)


class ForwardDividendAcquisitionError(RuntimeError):
    pass


@dataclass(frozen=True)
class DividendAnnouncementCandidate:
    ticker: str
    announcement_id: str
    announcement_number: str
    announcement_timestamp: str
    title: str
    form_id: str
    classification: str
    attachments: tuple[dict[str, Any], ...]


def normalize_ticker(value: object) -> str:
    ticker = str(value or "").strip().upper().replace(".JK", "")
    if not ticker or not re.fullmatch(r"[A-Z0-9]{1,12}", ticker):
        raise ForwardDividendAcquisitionError(
            "FORWARD_DIVIDEND_TICKER_INVALID"
        )
    return ticker


def normalize_date(value: object, code: str) -> str:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except Exception as exc:
        raise ForwardDividendAcquisitionError(code) from exc


def _walk_strings(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif value is not None:
        yield str(value)


def _classification(value: Any) -> str | None:
    text = " ".join(_walk_strings(value)).lower()

    if not any(term in text for term in _DIVIDEND_TERMS):
        return None

    if any(term in text for term in _NON_CASH_TERMS):
        return UNSUPPORTED_NON_CASH_DIVIDEND

    if any(term in text for term in _CASH_TERMS):
        return CASH_DIVIDEND_CANDIDATE

    return AMBIGUOUS_DIVIDEND_CANDIDATE


def extract_dividend_candidates(
    payload: Any,
    *,
    expected_ticker: str,
) -> tuple[DividendAnnouncementCandidate, ...]:
    ticker = normalize_ticker(expected_ticker)

    if not isinstance(payload, dict):
        raise ForwardDividendAcquisitionError(
            "FORWARD_DIVIDEND_RESPONSE_NOT_OBJECT"
        )

    replies = payload.get("Replies")
    if not isinstance(replies, list):
        raise ForwardDividendAcquisitionError(
            "FORWARD_DIVIDEND_REPLIES_NOT_LIST"
        )

    result: list[DividendAnnouncementCandidate] = []
    seen: dict[str, DividendAnnouncementCandidate] = {}

    for item in replies:
        if not isinstance(item, dict):
            raise ForwardDividendAcquisitionError(
                "FORWARD_DIVIDEND_REPLY_INVALID"
            )

        announcement = item.get("pengumuman")
        if not isinstance(announcement, dict):
            continue

        row_ticker_raw = announcement.get("Kode_Emiten")
        if not row_ticker_raw:
            continue

        raw_row_ticker = str(row_ticker_raw).strip().upper()
        # Issuer histories may include rights/warrant/security-class rows such
        # as BABY-R.  They remain preserved in the immutable raw page but are
        # outside this common-share dividend candidate contract.  Other issuer
        # mismatches remain a hard schema error.
        if raw_row_ticker.startswith(ticker + "-"):
            continue

        row_ticker = normalize_ticker(raw_row_ticker)
        if row_ticker != ticker:
            raise ForwardDividendAcquisitionError(
                "FORWARD_DIVIDEND_RESPONSE_TICKER_MISMATCH"
            )

        classification = _classification(item)
        if classification is None:
            continue

        announcement_id = str(
            announcement.get("Id2")
            or announcement.get("Id")
            or ""
        ).strip()
        announcement_number = str(
            announcement.get("NoPengumuman")
            or announcement.get("AnnouncementNo")
            or ""
        ).strip()

        if not announcement_id and not announcement_number:
            raise ForwardDividendAcquisitionError(
                "FORWARD_DIVIDEND_ANNOUNCEMENT_IDENTITY_MISSING"
            )

        identity = announcement_id or announcement_number

        title = str(
            announcement.get("JudulPengumuman")
            or announcement.get("PerihalPengumuman")
            or ""
        ).strip()

        timestamp = str(
            announcement.get("TglPengumuman")
            or announcement.get("CreatedDate")
            or ""
        ).strip()

        if not timestamp:
            raise ForwardDividendAcquisitionError(
                "FORWARD_DIVIDEND_ANNOUNCEMENT_TIMESTAMP_MISSING"
            )

        raw_attachments = item.get("attachments")
        attachments: list[dict[str, Any]] = []

        if isinstance(raw_attachments, list):
            for raw in raw_attachments:
                if not isinstance(raw, dict):
                    continue
                attachments.append(
                    {
                        "pdf_filename": raw.get("PDFFilename"),
                        "full_save_path": raw.get("FullSavePath"),
                        "original_filename": raw.get("OriginalFilename"),
                        "is_attachment": raw.get("IsAttachment"),
                    }
                )

        candidate = DividendAnnouncementCandidate(
            ticker=row_ticker,
            announcement_id=announcement_id,
            announcement_number=announcement_number,
            announcement_timestamp=timestamp,
            title=title,
            form_id=str(announcement.get("Form_Id") or "").strip(),
            classification=classification,
            attachments=tuple(attachments),
        )

        previous = seen.get(identity)
        if previous is not None and previous != candidate:
            raise ForwardDividendAcquisitionError(
                "FORWARD_DIVIDEND_DUPLICATE_ANNOUNCEMENT_CONFLICT"
            )

        seen[identity] = candidate

    result.extend(seen.values())

    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.ticker,
                row.announcement_timestamp,
                row.announcement_id,
                row.announcement_number,
            ),
        )
    )


def candidate_payload(
    rows: tuple[DividendAnnouncementCandidate, ...],
) -> list[dict[str, Any]]:
    return [asdict(row) for row in rows]
