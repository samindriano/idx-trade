from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from . import forward_ca_attestation_v1 as forward_ca
from . import forward_dividend_v1 as dividend
from .v4_x1_decision_v1_contract import DecisionV1Error, _normalize_ticker
from .v4_x1_execution_v1_verify import (
    VerifiedCorporateActionAttestation,
    VerifiedOpenExecutionInputs,
    _CA_ATTESTATION_TOKEN,
    verify_corporate_action_attestation,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERIFIED_DIVIDEND_EVIDENCE_TOKEN = object()
_DIVIDEND_RECONCILIATION_TOKEN = object()
_JAKARTA = ZoneInfo("Asia/Jakarta")

_CASH_DIVIDEND_KEYWORDS = (
    "dividen tunai",
    "cash dividend",
    "cash dividends",
    "dividen interim",
    "interim dividend",
    "interim dividends",
    "dividen",
    "dividend",
)

_NON_CASH_CA_KEYWORDS = (
    "stock split",
    "reverse stock",
    "pemecahan saham",
    "penggabungan nilai nominal",
    "hmetd",
    "hak memesan efek terlebih dahulu",
    "rights issue",
    "right issue",
    "pmthmetd",
    "private placement",
    "tanpa hmetd",
    "saham bonus",
    "bonus share",
    "bonus shares",
    "dividen saham",
    "stock dividend",
    "buyback",
    "pembelian kembali saham",
    "merger",
    "penggabungan usaha",
    "konversi saham",
    "partial delisting",
    "delisting sebagian",
    "capital reduction",
    "pengurangan modal",
    "waran",
    "warrant",
)


@dataclass(frozen=True)
class VerifiedCashDividendEvidence:
    event: dividend.CertifiedCashDividend
    review_path: Path
    review_sha256: str
    announcement_id: str
    announcement_number: str
    _verification_token: object = field(repr=False, compare=False)
    evidence_version: str = "V1.1"


@dataclass(frozen=True)
class VerifiedDividendCAReconciliation:
    from_session_date: str
    through_session_date: str
    covered_tickers: frozenset[str]
    original_status: str
    relevant_tickers: frozenset[str]
    certified_events: tuple[dividend.CertifiedCashDividend, ...]
    legacy_attestation: VerifiedCorporateActionAttestation
    attestation_path: Path
    attestation_sha256: str
    source_path: Path
    source_sha256: str
    _verification_token: object = field(repr=False, compare=False)
    v12_journal_path: Path | None = None
    v12_journal_sha256: str | None = None
    verified_evidence: tuple[VerifiedCashDividendEvidence, ...] = ()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_utc_capture_timestamp(value: object, code: str) -> datetime:
    text = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DecisionV1Error(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DecisionV1Error(code)
    return parsed.astimezone(timezone.utc)


def _knowledge_timestamp_utc(event: dividend.CertifiedCashDividend) -> datetime:
    text = str(event.knowledge_at_timestamp or event.announcement_timestamp or "")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DecisionV1Error("DIVIDEND_V1_2_KNOWLEDGE_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        # IDX announcement timestamps historically arrive without an offset;
        # the canonical source timezone is Asia/Jakarta.
        parsed = parsed.replace(tzinfo=_JAKARTA)
    return parsed.astimezone(timezone.utc)


def _verify_v12_knowledge_cutoff(
    payload: Mapping[str, Any],
    phase: Mapping[str, Any],
    events: Sequence[dividend.CertifiedCashDividend],
) -> None:
    capture = _parse_utc_capture_timestamp(
        payload.get("capture_timestamp_utc"),
        "DIVIDEND_V1_2_CAPTURE_TIMESTAMP_INVALID",
    )
    phase_capture = _parse_utc_capture_timestamp(
        phase.get("capture_timestamp_utc"),
        "DIVIDEND_V1_2_PHASE_CAPTURE_TIMESTAMP_INVALID",
    )
    if phase_capture != capture:
        raise DecisionV1Error("DIVIDEND_V1_2_CAPTURE_TIMESTAMP_PHASE_MISMATCH")
    for event in events:
        if _knowledge_timestamp_utc(event) > capture:
            raise DecisionV1Error(
                "DIVIDEND_V1_2_EVENT_AFTER_CAPTURE_CUTOFF:" + event.event_id
            )


def _iso_date(value: object, code: str) -> str:
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except Exception as exc:
        raise DecisionV1Error(code) from exc


def _blob(value: Any) -> str:
    return " ".join(x.lower() for x in forward_ca._walk_strings(value))


def _is_cash_dividend_only(value: Any) -> bool:
    text = _blob(value)
    if any(keyword in text for keyword in _NON_CASH_CA_KEYWORDS):
        return False
    return any(keyword in text for keyword in _CASH_DIVIDEND_KEYWORDS)


def verify_cash_dividend_evidence_for_execution(
    *,
    review_path: str | Path,
    attachment_dir: str | Path,
) -> VerifiedCashDividendEvidence:
    review_file = Path(review_path).expanduser().resolve()
    try:
        review_payload = json.loads(review_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV1Error("DIVIDEND_V1_1_REVIEW_INVALID") from exc
    if isinstance(review_payload, dict) and review_payload.get(
        "schema_version"
    ) == "idx_trade_forward_dividend_semantic_review_v1_2":
        return verify_cash_dividend_evidence_for_execution_v1_2(
            review_path=review_file,
            attachment_dir=attachment_dir,
        )
    event = dividend.certify_direct_idx_dividend_from_attachment_review(
        review_file,
        attachment_dir,
    )
    payload = review_payload
    announcement = payload.get("announcement")
    if not isinstance(announcement, dict):
        raise DecisionV1Error("DIVIDEND_V1_1_ANNOUNCEMENT_METADATA_MISSING")
    announcement_id = str(announcement.get("id") or announcement.get("Id") or "").strip()
    announcement_number = str(
        announcement.get("number")
        or announcement.get("AnnouncementNo")
        or announcement.get("NoPengumuman")
        or ""
    ).strip()
    if not announcement_id and not announcement_number:
        raise DecisionV1Error("DIVIDEND_V1_1_ANNOUNCEMENT_IDENTITY_MISSING")
    return VerifiedCashDividendEvidence(
        event=event,
        review_path=review_file,
        review_sha256=_sha256(review_file),
        announcement_id=announcement_id,
        announcement_number=announcement_number,
        evidence_version="V1.1",
        _verification_token=_VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
    )


def verify_cash_dividend_evidence_for_execution_v1_2(
    *,
    review_path: str | Path,
    attachment_dir: str | Path,
) -> VerifiedCashDividendEvidence:
    """Verify a V1.2 review through its immutable source/PDF replay chain."""
    review_file = Path(review_path).expanduser().resolve()
    try:
        from .forward_dividend_provenance_v1_2 import (
            certify_direct_idx_dividend_from_attachment_review_v1_2,
        )

        event = certify_direct_idx_dividend_from_attachment_review_v1_2(
            review_file,
            Path(attachment_dir).expanduser().resolve(),
        )
    except Exception as exc:
        raise DecisionV1Error("DIVIDEND_V1_2_EXECUTION_PROVENANCE_INVALID") from exc
    try:
        payload = json.loads(review_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV1Error("DIVIDEND_V1_2_REVIEW_INVALID") from exc
    announcement = payload.get("announcement")
    if not isinstance(announcement, dict):
        raise DecisionV1Error("DIVIDEND_V1_2_ANNOUNCEMENT_METADATA_MISSING")
    announcement_id = str(
        announcement.get("id") or announcement.get("Id") or ""
    ).strip()
    announcement_number = str(
        announcement.get("number")
        or announcement.get("AnnouncementNo")
        or announcement.get("NoPengumuman")
        or ""
    ).strip()
    if not announcement_id and not announcement_number:
        raise DecisionV1Error("DIVIDEND_V1_2_ANNOUNCEMENT_IDENTITY_MISSING")
    return VerifiedCashDividendEvidence(
        event=event,
        review_path=review_file,
        review_sha256=_sha256(review_file),
        announcement_id=announcement_id,
        announcement_number=announcement_number,
        evidence_version="V1.2",
        _verification_token=_VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
    )


def _require_verified_dividend_evidence(
    rows: Sequence[VerifiedCashDividendEvidence],
) -> tuple[VerifiedCashDividendEvidence, ...]:
    out: dict[str, VerifiedCashDividendEvidence] = {}
    ticker_cum: dict[tuple[str, str], str] = {}
    for row in rows:
        if (
            not isinstance(row, VerifiedCashDividendEvidence)
            or row._verification_token is not _VERIFIED_DIVIDEND_EVIDENCE_TOKEN
        ):
            raise DecisionV1Error("DIVIDEND_V1_1_VERIFIED_EVIDENCE_REQUIRED")
        event = dividend._validated_event(row.event)
        if row.review_sha256 != _sha256(row.review_path):
            raise DecisionV1Error("DIVIDEND_V1_1_REVIEW_SHA_MISMATCH")
        if event.event_id in out and out[event.event_id] != row:
            raise DecisionV1Error("DIVIDEND_V1_1_DUPLICATE_EVENT_CONFLICT")
        key = (event.ticker, event.cum_date)
        existing = ticker_cum.get(key)
        if existing is not None and existing != event.event_id:
            raise DecisionV1Error("DIVIDEND_V1_1_CONFLICTING_EVENT_SAME_TICKER_CUM")
        ticker_cum[key] = event.event_id
        out[event.event_id] = row
    return tuple(sorted(out.values(), key=lambda x: x.event.event_id))


def _event_intersects_window(
    event: dividend.CertifiedCashDividend,
    *,
    from_date: str,
    through_date: str,
) -> bool:
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(through_date)
    announced = date.fromisoformat(event.announcement_timestamp[:10])
    if start <= announced <= end:
        return True
    return any(
        start < date.fromisoformat(value) <= end
        for value in (event.cum_date, event.ex_date, event.record_date, event.payment_date)
    )


def _verify_relevant_ticker_cash_dividend_only(
    ticker: str,
    *,
    from_date: str,
    through_date: str,
    phases: Mapping[str, Mapping[str, Any]],
) -> None:
    saw_relevant = False
    for phase in phases.values():
        for payload in forward_ca._artifact_payloads(phase, "issued_history"):
            rows = payload.get("data", []) if isinstance(payload, dict) else []
            if not isinstance(rows, list):
                raise DecisionV1Error("DIVIDEND_V1_1_ISSUED_HISTORY_SCHEMA_INVALID")
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if str(row.get("KodeEmiten") or "").strip().upper() != ticker:
                    continue
                event_date = str(row.get("TanggalPencatatan") or "")[:10]
                try:
                    in_window = forward_ca._date_in_window(
                        event_date,
                        from_date,
                        through_date,
                        include_from=False,
                    )
                except Exception as exc:
                    raise DecisionV1Error("DIVIDEND_V1_1_ISSUED_HISTORY_DATE_INVALID") from exc
                if in_window:
                    raise DecisionV1Error(
                        f"DIVIDEND_V1_1_NON_CASH_CA_ISSUED_HISTORY:{ticker}"
                    )

        for payload in forward_ca._artifact_payloads(phase, "announcements"):
            items = payload.get("Items", []) if isinstance(payload, dict) else []
            if not isinstance(items, list):
                raise DecisionV1Error("DIVIDEND_V1_1_ANNOUNCEMENT_SCHEMA_INVALID")
            for item in items:
                if not isinstance(item, dict) or not forward_ca._contains_ticker(item, ticker):
                    continue
                if not forward_ca._contains_ca_keyword(item):
                    continue
                if not forward_ca._date_in_window(
                    item, from_date, through_date, include_from=True
                ):
                    continue
                saw_relevant = True
                if not _is_cash_dividend_only(item):
                    raise DecisionV1Error(
                        f"DIVIDEND_V1_1_NON_CASH_CA_ANNOUNCEMENT:{ticker}"
                    )

        for payload in forward_ca._artifact_payloads(phase, "calendar"):
            items = payload.get("Results", []) if isinstance(payload, dict) else []
            if not isinstance(items, list):
                raise DecisionV1Error("DIVIDEND_V1_1_CALENDAR_SCHEMA_INVALID")
            for item in items:
                if not isinstance(item, dict) or not forward_ca._contains_ticker(item, ticker):
                    continue
                if not forward_ca._contains_ca_keyword(item):
                    continue
                if not forward_ca._date_in_window(
                    item, from_date, through_date, include_from=False
                ):
                    continue
                saw_relevant = True
                if not _is_cash_dividend_only(item):
                    raise DecisionV1Error(
                        f"DIVIDEND_V1_1_NON_CASH_CA_CALENDAR:{ticker}"
                    )
    if not saw_relevant:
        raise DecisionV1Error(f"DIVIDEND_V1_1_RELEVANT_EVENT_NOT_REPRODUCED:{ticker}")


def _load_and_verify_post_eod_attestation_v1_2(
    *,
    path: Path,
    expected_from_session_date: str,
    expected_through_session_date: str,
    required_tickers: Sequence[str],
) -> tuple[
    dict[str, Any],
    str,
    str,
    set[str],
    set[str],
    Path,
    str,
    Mapping[str, Mapping[str, Any]],
]:
    """Verify a POST_EOD-only CA phase without requiring a future PREOPEN leg."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV1Error("DIVIDEND_V1_2_CA_ATTESTATION_INVALID") from exc
    if not isinstance(payload, dict):
        raise DecisionV1Error("DIVIDEND_V1_2_CA_ATTESTATION_NOT_OBJECT")
    if payload.get("schema_version") != forward_ca.ATTESTATION_SCHEMA_V1_2:
        raise DecisionV1Error("DIVIDEND_V1_2_CA_ATTESTATION_SCHEMA_CHANGED")
    if payload.get("capture_phase") != "POST_EOD":
        raise DecisionV1Error("DIVIDEND_V1_2_CA_CAPTURE_PHASE_INVALID")
    if payload.get("provider_repository") != forward_ca.PROVIDER_REPOSITORY:
        raise DecisionV1Error("DIVIDEND_V1_2_CA_PROVIDER_REPOSITORY_MISMATCH")
    if payload.get("provider_commit") != forward_ca.PROVIDER_COMMIT:
        raise DecisionV1Error("DIVIDEND_V1_2_CA_PROVIDER_COMMIT_MISMATCH")
    if payload.get("upstream_base_url") != forward_ca.UPSTREAM_BASE_URL:
        raise DecisionV1Error("DIVIDEND_V1_2_CA_UPSTREAM_MISMATCH")
    if payload.get("calendar_schema_fingerprint") != forward_ca.EXPECTED_CALENDAR_SCHEMA_FINGERPRINT:
        raise DecisionV1Error("DIVIDEND_V1_2_CA_CALENDAR_SCHEMA_FINGERPRINT_MISMATCH")

    from_date = _iso_date(payload.get("from_session_date"), "DIVIDEND_V1_2_CA_FROM_DATE_INVALID")
    through_date = _iso_date(payload.get("through_session_date"), "DIVIDEND_V1_2_CA_THROUGH_DATE_INVALID")
    if from_date != _iso_date(expected_from_session_date, "DIVIDEND_V1_2_CA_EXPECTED_FROM_INVALID"):
        raise DecisionV1Error("DIVIDEND_V1_2_CA_FROM_DATE_MISMATCH")
    if through_date != _iso_date(expected_through_session_date, "DIVIDEND_V1_2_CA_EXPECTED_THROUGH_INVALID"):
        raise DecisionV1Error("DIVIDEND_V1_2_CA_THROUGH_DATE_MISMATCH")

    phase_raw = Path(str(payload.get("phase_manifest_path") or ""))
    phase_path = phase_raw if phase_raw.is_absolute() else (path.parent / phase_raw).resolve()
    declared_phase_sha = str(payload.get("phase_manifest_sha256") or "")
    if not phase_path.is_file() or not _SHA256_RE.fullmatch(declared_phase_sha):
        raise DecisionV1Error("DIVIDEND_V1_2_CA_PHASE_MANIFEST_MISSING")
    actual_phase_sha = _sha256(phase_path)
    if actual_phase_sha != declared_phase_sha:
        raise DecisionV1Error("DIVIDEND_V1_2_CA_PHASE_MANIFEST_SHA_MISMATCH")
    try:
        phase = forward_ca.verify_phase_manifest(phase_path)
    except forward_ca.ForwardCAError as exc:
        raise DecisionV1Error(f"DIVIDEND_V1_2_CA_PHASE_CHAIN_INVALID:{exc}") from exc
    if phase.get("phase") != "POST_EOD":
        raise DecisionV1Error("DIVIDEND_V1_2_CA_PHASE_ORDER_INVALID")
    if phase.get("from_session_date") != from_date or phase.get("through_session_date") != through_date:
        raise DecisionV1Error("DIVIDEND_V1_2_CA_PHASE_SCOPE_MISMATCH")
    _parse_utc_capture_timestamp(
        payload.get("capture_timestamp_utc"),
        "DIVIDEND_V1_2_CAPTURE_TIMESTAMP_INVALID",
    )
    _parse_utc_capture_timestamp(
        phase.get("capture_timestamp_utc"),
        "DIVIDEND_V1_2_PHASE_CAPTURE_TIMESTAMP_INVALID",
    )

    rows = payload.get("evidence_rows")
    if not isinstance(rows, list):
        raise DecisionV1Error("DIVIDEND_V1_2_CA_EVIDENCE_ROWS_MISSING")
    covered: set[str] = set()
    relevant: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise DecisionV1Error("DIVIDEND_V1_2_CA_EVIDENCE_ROW_INVALID")
        ticker = _normalize_ticker(row.get("ticker"))
        if ticker in covered:
            raise DecisionV1Error("DIVIDEND_V1_2_CA_EVIDENCE_DUPLICATE_TICKER")
        status = str(row.get("status") or "")
        if status not in {forward_ca.NO_EVENT, forward_ca.RELEVANT}:
            raise DecisionV1Error("DIVIDEND_V1_2_CA_EVIDENCE_STATUS_INVALID")
        reasons = row.get("reasons")
        if not isinstance(reasons, list) or (status == forward_ca.NO_EVENT and reasons):
            raise DecisionV1Error("DIVIDEND_V1_2_CA_EVIDENCE_REASONS_INVALID")
        if status == forward_ca.RELEVANT and not reasons:
            raise DecisionV1Error("DIVIDEND_V1_2_CA_RELEVANT_WITHOUT_REASON")
        covered.add(ticker)
        if status == forward_ca.RELEVANT:
            relevant.add(ticker)
    required = {_normalize_ticker(x) for x in required_tickers}
    if not required.issubset(covered):
        raise DecisionV1Error(f"DIVIDEND_V1_2_CA_COVERAGE_INCOMPLETE:{sorted(required-covered)}")
    if (str(payload.get("status") or "") == "RELEVANT_EVENT_DETECTED") != bool(relevant):
        raise DecisionV1Error("DIVIDEND_V1_2_CA_STATUS_ROW_MISMATCH")
    phase_tickers = {_normalize_ticker(x) for x in phase.get("required_tickers", [])}
    if phase_tickers != covered:
        raise DecisionV1Error("DIVIDEND_V1_2_CA_PHASE_TICKER_COVERAGE_MISMATCH")
    payload["_v12_post_eod"] = True
    return payload, from_date, through_date, covered, relevant, phase_path, actual_phase_sha, {"POST_EOD": phase}


def _load_and_verify_attestation_common(
    *,
    attestation_path: str | Path,
    expected_from_session_date: str,
    expected_through_session_date: str,
    required_tickers: Sequence[str],
) -> tuple[
    dict[str, Any],
    str,
    str,
    set[str],
    set[str],
    Path,
    str,
    Mapping[str, Mapping[str, Any]],
]:
    path = Path(attestation_path).expanduser().resolve()
    if not path.is_file():
        raise DecisionV1Error(f"DIVIDEND_V1_1_CA_ATTESTATION_MISSING:{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV1Error("DIVIDEND_V1_1_CA_ATTESTATION_INVALID") from exc
    if not isinstance(payload, dict):
        raise DecisionV1Error("DIVIDEND_V1_1_CA_ATTESTATION_NOT_OBJECT")
    if payload.get("schema_version") == forward_ca.ATTESTATION_SCHEMA_V1_2:
        return _load_and_verify_post_eod_attestation_v1_2(
            path=path,
            expected_from_session_date=expected_from_session_date,
            expected_through_session_date=expected_through_session_date,
            required_tickers=required_tickers,
        )
    if payload.get("schema_version") != forward_ca.ATTESTATION_SCHEMA:
        raise DecisionV1Error("DIVIDEND_V1_1_CA_ATTESTATION_SCHEMA_CHANGED")
    if payload.get("provider_repository") != forward_ca.PROVIDER_REPOSITORY:
        raise DecisionV1Error("DIVIDEND_V1_1_CA_PROVIDER_REPOSITORY_MISMATCH")
    if payload.get("provider_commit") != forward_ca.PROVIDER_COMMIT:
        raise DecisionV1Error("DIVIDEND_V1_1_CA_PROVIDER_COMMIT_MISMATCH")
    if payload.get("upstream_base_url") != forward_ca.UPSTREAM_BASE_URL:
        raise DecisionV1Error("DIVIDEND_V1_1_CA_UPSTREAM_MISMATCH")
    if (
        payload.get("calendar_schema_fingerprint")
        != forward_ca.EXPECTED_CALENDAR_SCHEMA_FINGERPRINT
    ):
        raise DecisionV1Error("DIVIDEND_V1_1_CA_CALENDAR_SCHEMA_FINGERPRINT_MISMATCH")

    from_date = _iso_date(
        payload.get("from_session_date"),
        "DIVIDEND_V1_1_CA_FROM_DATE_INVALID",
    )
    through_date = _iso_date(
        payload.get("through_session_date"),
        "DIVIDEND_V1_1_CA_THROUGH_DATE_INVALID",
    )
    if from_date != _iso_date(
        expected_from_session_date,
        "DIVIDEND_V1_1_EXPECTED_FROM_DATE_INVALID",
    ):
        raise DecisionV1Error("DIVIDEND_V1_1_CA_FROM_DATE_MISMATCH")
    if through_date != _iso_date(
        expected_through_session_date,
        "DIVIDEND_V1_1_EXPECTED_THROUGH_DATE_INVALID",
    ):
        raise DecisionV1Error("DIVIDEND_V1_1_CA_THROUGH_DATE_MISMATCH")

    status = str(payload.get("status") or "")
    if status not in {"NO_RELEVANT_EVENTS", "RELEVANT_EVENT_DETECTED"}:
        raise DecisionV1Error(
            f"DIVIDEND_V1_1_CA_STATUS_NOT_ADMISSIBLE:{status or 'UNKNOWN'}"
        )
    rows = payload.get("evidence_rows")
    if not isinstance(rows, list):
        raise DecisionV1Error("DIVIDEND_V1_1_CA_EVIDENCE_ROWS_MISSING")
    covered: set[str] = set()
    relevant: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise DecisionV1Error("DIVIDEND_V1_1_CA_EVIDENCE_ROW_INVALID")
        ticker = _normalize_ticker(row.get("ticker"))
        if ticker in covered:
            raise DecisionV1Error("DIVIDEND_V1_1_CA_EVIDENCE_DUPLICATE_TICKER")
        row_status = str(row.get("status") or "")
        if row_status not in {forward_ca.NO_EVENT, forward_ca.RELEVANT}:
            raise DecisionV1Error("DIVIDEND_V1_1_CA_EVIDENCE_STATUS_INVALID")
        reasons = row.get("reasons")
        if not isinstance(reasons, list):
            raise DecisionV1Error("DIVIDEND_V1_1_CA_REASONS_INVALID")
        if row_status == forward_ca.RELEVANT:
            if not reasons:
                raise DecisionV1Error("DIVIDEND_V1_1_CA_RELEVANT_WITHOUT_REASON")
            relevant.add(ticker)
        elif reasons:
            raise DecisionV1Error("DIVIDEND_V1_1_CA_NO_EVENT_WITH_REASONS")
        covered.add(ticker)

    if (status == "RELEVANT_EVENT_DETECTED") != bool(relevant):
        raise DecisionV1Error("DIVIDEND_V1_1_CA_STATUS_ROW_MISMATCH")
    required = {_normalize_ticker(x) for x in required_tickers}
    if not required.issubset(covered):
        raise DecisionV1Error(
            f"DIVIDEND_V1_1_CA_COVERAGE_INCOMPLETE:{sorted(required-covered)}"
        )

    raw_source = Path(str(payload.get("source_path") or ""))
    source_path = raw_source if raw_source.is_absolute() else (path.parent / raw_source).resolve()
    if not source_path.is_file():
        raise DecisionV1Error("DIVIDEND_V1_1_CA_SOURCE_ARTIFACT_MISSING")
    declared_source_sha = str(payload.get("source_sha256") or "")
    if not _SHA256_RE.fullmatch(declared_source_sha):
        raise DecisionV1Error("DIVIDEND_V1_1_CA_SOURCE_SHA_INVALID")
    actual_source_sha = _sha256(source_path)
    if actual_source_sha != declared_source_sha:
        raise DecisionV1Error("DIVIDEND_V1_1_CA_SOURCE_SHA_MISMATCH")
    try:
        source_payload, phases = forward_ca.verify_source_manifest(source_path)
    except forward_ca.ForwardCAError as exc:
        raise DecisionV1Error(f"DIVIDEND_V1_1_CA_SOURCE_CHAIN_INVALID:{exc}") from exc
    if source_payload.get("from_session_date") != from_date:
        raise DecisionV1Error("DIVIDEND_V1_1_CA_SOURCE_FROM_DATE_MISMATCH")
    if source_payload.get("through_session_date") != through_date:
        raise DecisionV1Error("DIVIDEND_V1_1_CA_SOURCE_THROUGH_DATE_MISMATCH")
    source_tickers = {_normalize_ticker(x) for x in source_payload.get("required_tickers", [])}
    if source_tickers != covered:
        raise DecisionV1Error("DIVIDEND_V1_1_CA_SOURCE_TICKER_COVERAGE_MISMATCH")
    if source_payload.get("calendar_schema_fingerprints") != [
        forward_ca.EXPECTED_CALENDAR_SCHEMA_FINGERPRINT
    ]:
        raise DecisionV1Error("DIVIDEND_V1_1_CA_SOURCE_CALENDAR_SCHEMA_MISMATCH")
    return (
        payload,
        from_date,
        through_date,
        covered,
        relevant,
        source_path,
        actual_source_sha,
        phases,
    )


def reconcile_corporate_action_attestation_v1_1(
    *,
    attestation_path: str | Path,
    expected_from_session_date: str,
    expected_through_session_date: str,
    required_tickers: Sequence[str],
    dividend_evidence: Sequence[VerifiedCashDividendEvidence] = (),
) -> VerifiedDividendCAReconciliation:
    evidence = _require_verified_dividend_evidence(dividend_evidence)
    (
        payload,
        from_date,
        through_date,
        covered,
        relevant,
        source_path,
        source_sha,
        phases,
    ) = _load_and_verify_attestation_common(
        attestation_path=attestation_path,
        expected_from_session_date=expected_from_session_date,
        expected_through_session_date=expected_through_session_date,
        required_tickers=required_tickers,
    )
    path = Path(attestation_path).expanduser().resolve()
    original_status = str(payload["status"])
    if payload.get("schema_version") == forward_ca.ATTESTATION_SCHEMA_V1_2:
        _verify_v12_knowledge_cutoff(payload, phases["POST_EOD"], tuple(row.event for row in evidence))

    if original_status == "NO_RELEVANT_EVENTS":
        if payload.get("schema_version") == forward_ca.ATTESTATION_SCHEMA_V1_2:
            legacy = VerifiedCorporateActionAttestation(
                from_session_date=from_date,
                through_session_date=through_date,
                covered_tickers=frozenset(covered),
                status="NO_RELEVANT_EVENTS",
                attestation_path=path,
                attestation_sha256=_sha256(path),
                source_path=source_path,
                source_sha256=source_sha,
                _verification_token=_CA_ATTESTATION_TOKEN,
            )
        else:
            legacy = verify_corporate_action_attestation(
                attestation_path=path,
                expected_from_session_date=from_date,
                expected_through_session_date=through_date,
                required_tickers=required_tickers,
            )
    else:
        events_by_ticker: dict[str, list[dividend.CertifiedCashDividend]] = {}
        for row in evidence:
            event = dividend._validated_event(row.event)
            events_by_ticker.setdefault(event.ticker, []).append(event)
        for ticker in sorted(relevant):
            events = events_by_ticker.get(ticker, [])
            if not events:
                raise DecisionV1Error(
                    f"DIVIDEND_V1_1_RELEVANT_TICKER_WITHOUT_CERTIFIED_DIVIDEND:{ticker}"
                )
            if not any(
                _event_intersects_window(event, from_date=from_date, through_date=through_date)
                for event in events
            ):
                raise DecisionV1Error(
                    f"DIVIDEND_V1_1_CERTIFIED_DIVIDEND_OUTSIDE_CA_WINDOW:{ticker}"
                )
            row = next(
                x for x in payload["evidence_rows"]
                if _normalize_ticker(x.get("ticker")) == ticker
            )
            reasons = tuple(str(x) for x in row["reasons"])
            if any(":ISSUED_HISTORY:" in reason for reason in reasons):
                raise DecisionV1Error(
                    f"DIVIDEND_V1_1_NON_CASH_CA_REASON_ISSUED_HISTORY:{ticker}"
                )
            if any(
                ":ANNOUNCEMENT:" not in reason and ":CALENDAR_EVENT:" not in reason
                for reason in reasons
            ):
                raise DecisionV1Error(
                    f"DIVIDEND_V1_1_UNRECOGNIZED_CA_REASON:{ticker}"
                )
            _verify_relevant_ticker_cash_dividend_only(
                ticker,
                from_date=from_date,
                through_date=through_date,
                phases=phases,
            )

        legacy = VerifiedCorporateActionAttestation(
            from_session_date=from_date,
            through_session_date=through_date,
            covered_tickers=frozenset(covered),
            status="NO_RELEVANT_EVENTS",
            attestation_path=path,
            attestation_sha256=_sha256(path),
            source_path=source_path,
            source_sha256=source_sha,
            _verification_token=_CA_ATTESTATION_TOKEN,
        )

    events = tuple(
        sorted(
            (dividend._validated_event(row.event) for row in evidence),
            key=lambda x: x.event_id,
        )
    )
    return VerifiedDividendCAReconciliation(
        from_session_date=from_date,
        through_session_date=through_date,
        covered_tickers=frozenset(covered),
        original_status=original_status,
        relevant_tickers=frozenset(relevant),
        certified_events=events,
        legacy_attestation=legacy,
        attestation_path=path,
        attestation_sha256=_sha256(path),
        source_path=source_path,
        source_sha256=source_sha,
        _verification_token=_DIVIDEND_RECONCILIATION_TOKEN,
    )


def reconcile_corporate_action_attestation_v1_2_journal(
    *,
    attestation_path: str | Path,
    journal_path: str | Path,
    expected_from_session_date: str,
    expected_through_session_date: str,
    required_tickers: Sequence[str],
) -> VerifiedDividendCAReconciliation:
    """Bind execution to the immutable V1.2 acquisition journal state.

    The legacy CA attestation remains the source for non-dividend CA coverage;
    the journal is authoritative for dividend candidates, certified events,
    and live blockers. Each journal entry carries its own evidence directory.
    """
    from .forward_dividend_orchestration_v1 import load_journal_document

    journal_file = Path(journal_path).expanduser().resolve()
    document = load_journal_document(journal_file)
    journal = document.journal
    required = {str(x).strip().upper() for x in required_tickers}
    if not required.issubset(set(journal.required_tickers)):
        raise DecisionV1Error("DIVIDEND_V1_2_JOURNAL_REQUIRED_TICKER_COVERAGE_MISMATCH")
    blockers = {
        row.ticker for row in journal.blockers
        if row.ticker in required
    }
    if blockers:
        raise DecisionV1Error(
            "DIVIDEND_V1_2_JOURNAL_LIVE_BLOCKER:" + ",".join(sorted(blockers))
        )

    evidence: list[VerifiedCashDividendEvidence] = []
    for row in journal.certified_events:
        review_path = Path(row.evidence_dir).expanduser().resolve() / row.review_filename
        verified = verify_cash_dividend_evidence_for_execution(
            review_path=review_path,
            attachment_dir=review_path.parent,
        )
        if (
            verified.event.event_id != row.event_id
            or verified.event.source_evidence_sha256 != row.event_sha256
            or verified.event.ticker != row.ticker
            or verified.review_sha256 != row.review_sha256
        ):
            raise DecisionV1Error("DIVIDEND_V1_2_JOURNAL_EVENT_BINDING_MISMATCH")
        evidence.append(verified)

    base = reconcile_corporate_action_attestation_v1_1(
        attestation_path=attestation_path,
        expected_from_session_date=expected_from_session_date,
        expected_through_session_date=expected_through_session_date,
        required_tickers=required_tickers,
        dividend_evidence=tuple(evidence),
    )
    return replace(
        base,
        v12_journal_path=document.path,
        v12_journal_sha256=document.file_sha256,
        verified_evidence=tuple(evidence),
    )


def execute_open_v1_1_reconciled(
    order_plan: dividend.DividendAwareExecutionOrderPlan,
    state: dividend.DividendAwarePaperState,
    *,
    open_inputs: VerifiedOpenExecutionInputs,
    reconciliation: VerifiedDividendCAReconciliation,
    historical_states_by_date: Mapping[str, dividend.DividendAwarePaperState] | None = None,
) -> dividend.DividendAwareExecutionResult:
    if (
        not isinstance(reconciliation, VerifiedDividendCAReconciliation)
        or reconciliation._verification_token is not _DIVIDEND_RECONCILIATION_TOKEN
    ):
        raise DecisionV1Error("DIVIDEND_V1_1_VERIFIED_RECONCILIATION_REQUIRED")
    if reconciliation.from_session_date != order_plan.base_plan.decision_session_date:
        raise DecisionV1Error("DIVIDEND_V1_1_RECONCILIATION_FROM_DATE_MISMATCH")
    if reconciliation.through_session_date != order_plan.base_plan.execution_session_date:
        raise DecisionV1Error("DIVIDEND_V1_1_RECONCILIATION_THROUGH_DATE_MISMATCH")
    if open_inputs.session_date != order_plan.base_plan.execution_session_date:
        raise DecisionV1Error("DIVIDEND_V1_1_OPEN_SESSION_DATE_MISMATCH")

    result = dividend.execute_open_v1_1(
        order_plan,
        state,
        open_inputs=open_inputs,
        ca_attestation=reconciliation.legacy_attestation,
    )
    processed = dividend.process_dividend_eod(
        result.state_after,
        reconciliation.certified_events,
        session_date=result.base_result.execution_session_date,
        historical_states_by_date=historical_states_by_date,
    )
    return dividend.DividendAwareExecutionResult(
        base_result=result.base_result,
        state_after=processed,
    )
