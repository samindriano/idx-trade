from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from pypdf import PdfReader

SCHEMA = "idx_trade_forward_ca_dividend_attachment_capture_v1"
REVIEW_SCHEMA = "idx_trade_forward_ca_dividend_attachment_review_v1"
EXPECTED_SOURCE_ANNOUNCEMENT_SHA256 = "6e8ced1891addecdb9a1029d064c75d072ebcbeb4319ad633d30e43fac004473"
EXPECTED_EVENT = {
    "ticker": "BBCA",
    "gross_dividend_per_share_idr": Decimal("25"),
    "cum_regular_negotiated": "28 Agustus 2026",
    "ex_regular_negotiated": "31 Agustus 2026",
    "record_date": "1 September 2026",
    "payment_date": "16 September 2026",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _extract_pdf_text(path: Path) -> tuple[str, int]:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    return "\n".join(parts), len(reader.pages)


def _contains_date(text: str, day: int, month_name: str, year: int) -> bool:
    month = re.escape(month_name.lower())
    return bool(re.search(rf"\b0?{day}\s+{month}\s+{year}\b", text, flags=re.IGNORECASE))


def _amount_regex(amount: Decimal) -> str:
    """Return a locale-tolerant regex for an exact currency amount.

    IDX disclosure PDFs commonly render an integer cash dividend as `25`,
    `25,00`, or `25.00`.  Keep the match exact while allowing only zero
    fractional digits when the expected amount itself is integral.
    """
    normalized = amount.normalize()
    if normalized == normalized.to_integral():
        integer = re.escape(str(int(normalized)))
        return rf"{integer}(?:[\.,]0+)?"

    canonical = format(normalized, "f")
    whole, frac = canonical.split(".", 1)
    return rf"{re.escape(whole)}[\.,]{re.escape(frac)}"


def _has_dividend_amount(text: str, amount: Decimal) -> bool:
    amount_token = _amount_regex(amount)
    share_unit = r"(?:per\s+(?:lembar\s+)?saham|per\s+share|/\s*(?:lembar\s+)?saham)"
    currency_amount = rf"(?:rp\.?|idr)\s*{amount_token}"

    # Accept the major layouts observed in official IDX/issuer disclosures:
    # - "dividen per saham ... IDR 25"
    # - "dividen interim sebesar Rp25,00 per lembar saham"
    # - "interim dividend of Rp25.00 per share"
    # - table cells where the currency amount precedes "dividen per saham".
    patterns = (
        rf"dividen\s+per\s+saham.{{0,120}}?{currency_amount}(?:\D|$)",
        rf"dividen(?:\s+tunai)?(?:\s+interim)?.{{0,80}}?{currency_amount}\s*{share_unit}",
        rf"interim\s+dividend.{{0,80}}?{currency_amount}\s*{share_unit}",
        rf"dividend.{{0,80}}?{currency_amount}\s*{share_unit}",
        rf"{currency_amount}.{{0,100}}?dividen\s+per\s+saham",
        rf"{currency_amount}\s*{share_unit}",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline semantic review of official IDX dividend PDFs.")
    parser.add_argument("--attachment-dir", required=True)
    args = parser.parse_args()

    root = Path(args.attachment_dir).expanduser().resolve()
    manifest_path = root / "ATTACHMENT_CAPTURE_MANIFEST.json"
    if not manifest_path.is_file():
        raise SystemExit(f"manifest missing: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    warnings: list[str] = []

    if manifest.get("schema_version") != SCHEMA:
        failures.append("MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("status") != "COMPLETE_AWAITING_OFFLINE_REVIEW":
        failures.append("MANIFEST_STATUS_INVALID")
    if manifest.get("source_announcement_raw_sha256") != EXPECTED_SOURCE_ANNOUNCEMENT_SHA256:
        failures.append("SOURCE_ANNOUNCEMENT_SHA_MISMATCH")
    if manifest.get("request_policy") != "ONE_ATTEMPT_PER_ATTACHMENT_NO_RETRY_HELPER":
        failures.append("REQUEST_POLICY_MISMATCH")
    if int(manifest.get("retry_count") or 0) != 0:
        failures.append("RETRY_COUNT_NOT_ZERO")

    announcement = manifest.get("announcement") if isinstance(manifest.get("announcement"), dict) else {}
    if str(announcement.get("code") or "").strip().upper() != EXPECTED_EVENT["ticker"]:
        failures.append("ANNOUNCEMENT_TICKER_MISMATCH")
    if "dividen" not in str(announcement.get("title") or "").lower():
        failures.append("ANNOUNCEMENT_TITLE_NOT_DIVIDEND")

    rows = manifest.get("attachments") if isinstance(manifest.get("attachments"), list) else []
    if not rows:
        failures.append("ATTACHMENTS_EMPTY")

    documents: list[dict[str, Any]] = []
    combined_parts: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            failures.append("ATTACHMENT_ROW_INVALID")
            continue
        filename = str(row.get("pdf_filename") or "")
        path = root / filename
        if not path.is_file():
            failures.append(f"ATTACHMENT_FILE_MISSING:{filename}")
            continue
        actual_sha = _sha256(path)
        if actual_sha != str(row.get("sha256") or ""):
            failures.append(f"ATTACHMENT_SHA_MISMATCH:{filename}")
            continue
        if not path.read_bytes().startswith(b"%PDF-"):
            failures.append(f"ATTACHMENT_NOT_PDF:{filename}")
            continue
        try:
            text, page_count = _extract_pdf_text(path)
        except Exception as exc:
            failures.append(f"PDF_TEXT_EXTRACTION_FAILED:{filename}:{type(exc).__name__}")
            continue
        normalized = _norm(text)
        combined_parts.append(normalized)
        documents.append(
            {
                "pdf_filename": filename,
                "original_filename": row.get("original_filename"),
                "sha256": actual_sha,
                "page_count": page_count,
                "text_char_count": len(text),
                "text_sample": normalized[:1200],
            }
        )

    combined = " ".join(combined_parts)
    ticker_match = "bbca" in combined or "bank central asia" in combined
    dividend_subject_match = "jadwal dividen tunai interim" in combined or "dividen tunai interim" in combined
    amount_match = _has_dividend_amount(combined, EXPECTED_EVENT["gross_dividend_per_share_idr"])
    cum_match = _contains_date(combined, 28, "Agustus", 2026)
    ex_match = _contains_date(combined, 31, "Agustus", 2026)
    record_match = _contains_date(combined, 1, "September", 2026)
    payment_match = _contains_date(combined, 16, "September", 2026)

    if not ticker_match:
        failures.append("PDF_TICKER_NOT_FOUND")
    if not dividend_subject_match:
        failures.append("PDF_DIVIDEND_SUBJECT_NOT_FOUND")
    if not amount_match:
        failures.append("PDF_DIVIDEND_PER_SHARE_25_NOT_FOUND")
    if not cum_match:
        failures.append("PDF_CUM_REGULAR_2026_08_28_NOT_FOUND")
    if not ex_match:
        failures.append("PDF_EX_REGULAR_2026_08_31_NOT_FOUND")
    if not record_match:
        failures.append("PDF_RECORD_DATE_2026_09_01_NOT_FOUND")
    if not payment_match:
        failures.append("PDF_PAYMENT_DATE_2026_09_16_NOT_FOUND")

    report = {
        "schema_version": REVIEW_SCHEMA,
        "status": "PASS_DIRECT_IDX_ANNOUNCEMENT_ATTACHMENT_TERMS_ELIGIBLE_FOR_V1_1" if not failures else "FAIL_DIRECT_IDX_ANNOUNCEMENT_ATTACHMENT_TERMS_NOT_ADMITTED",
        "announcement": announcement,
        "source_announcement_raw_sha256": manifest.get("source_announcement_raw_sha256"),
        "documents": documents,
        "expected_event": {
            "ticker": EXPECTED_EVENT["ticker"],
            "gross_dividend_per_share_idr": str(EXPECTED_EVENT["gross_dividend_per_share_idr"]),
            "cum_regular_negotiated": EXPECTED_EVENT["cum_regular_negotiated"],
            "ex_regular_negotiated": EXPECTED_EVENT["ex_regular_negotiated"],
            "record_date": EXPECTED_EVENT["record_date"],
            "payment_date": EXPECTED_EVENT["payment_date"],
        },
        "semantic_matches": {
            "ticker": ticker_match,
            "dividend_subject": dividend_subject_match,
            "dividend_per_share": amount_match,
            "cum_regular_negotiated": cum_match,
            "ex_regular_negotiated": ex_match,
            "record_date": record_match,
            "payment_date": payment_match,
        },
        "failures": failures,
        "warnings": warnings,
        "authority_recommendation": "DIRECT_IDX_ANNOUNCEMENT_PLUS_HASHED_ATTACHMENT" if not failures else None,
        "link_dividend_role": "LAGGING_CORROBORATION_NOT_FORWARD_AUTHORITY",
        "zapi_role": "OPTIONAL_PARITY_ONLY",
    }
    output = root / "ATTACHMENT_REVIEW.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
