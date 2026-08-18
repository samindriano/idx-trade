"""Outcome-blind FREN mechanical-event attestation from official archives.

The static KSEI registered-security page for legacy FREN no longer yields a
certifiable FREN history after the 2025 merger.  This module therefore does not
pretend that source recovered.  It defines a narrow archival route that may
certify only the mechanical price-basis events on FREN's frozen support:

- PMHMETD V / Rights Issue V in April 2024; and
- merger/security cessation on 2025-04-16.

The rights transition is accepted only when issuer-official Smartfren material
explicitly states the Regular/Negotiated Market ex-right date and official KSEI
reminders corroborate the record/distribution identity.  No record-date
subtraction, price inference, or EXCL price stitching is permitted.
"""

from __future__ import annotations

import hashlib
import html
from io import BytesIO
import re
from typing import Iterable
from urllib.parse import urljoin, urlparse

import pandas as pd
from pypdf import PdfReader

from idx_trade.v4_ca_event_windows import EventSemantic


FREN_RIGHT_EX_DATE = pd.Timestamp("2024-04-17")
FREN_RIGHT_RECORD_DATE = pd.Timestamp("2024-04-18")
FREN_RIGHT_DISTRIBUTION_DATE = pd.Timestamp("2024-04-19")
FREN_RIGHT_TRADING_START = pd.Timestamp("2024-04-22")
FREN_RIGHT_TRADING_END = pd.Timestamp("2024-05-06")
FREN_RIGHT_RATIO_OLD = "178"
FREN_RIGHT_RATIO_RIGHT = "75"
FREN_MERGER_DATE = pd.Timestamp("2025-04-16")

SMARTFREN_CORPORATE_ACTION_2024_URL = (
    "https://www.smartfren.com/connect-with-us/whats-new/yearcategory/aksi-korporasi-2024/"
)
SMARTFREN_DISCLOSURE_2024_URL = (
    "https://www.smartfren.com/connect-with-us/whats-new/yearcategory/keterbukaan-informasi-2024/"
)
SMARTFREN_PROSPECTUS_PAGE_URL = (
    "https://www.smartfren.com/en/connect-with-us/whats-new/year/"
    "prospektus-pmhmetd-v-pt-smartfren-telecom-tbk/"
)
SMARTFREN_INVESTOR_ABOUT_URL = "https://www.smartfren.com/en/investor-tentang-kami/"
SMARTFREN_ANNUAL_REPORT_URL = "https://www.smartfren.com/en/investor-laporan-tahunan/"
SMARTFREN_2024_ANNUAL_REPORT_PDF = (
    "https://www.smartfren.com/en/app/uploads/2025/03/Smartfren-AR-2024-250312-v2.pdf"
)
SMARTFREN_MERGER_ARCHIVE_URL = (
    "https://www.smartfren.com/connect-with-us/whats-new/category/info-merger/"
)

KSEI_RIGHT_RECORD_URL = (
    "https://web.ksei.co.id/ksei_news/read/16972/Reminder-Corporate-Action-Recording-Date-"
    "ARNA-ITMG-IFSH-ASAI01C1MF-SMKSSA01A-SICO-FREN-WIKA-IDSR190424182S-BFIN05ACN4-WOMF-HEAL-LTLS-MLPL"
)
KSEI_RIGHT_DISTRIBUTION_URL = (
    "https://web.ksei.co.id/ksei_news/read/16975/Reminder-CA-Pendistribusian-Laporan-dan-"
    "Pendistribusian-Hak-CA-melalui-C-BEST-per-tanggal-19-April-2024"
)
KSEI_MERGER_RECORD_URL = (
    "https://web.ksei.co.id/ksei_news/read/17420/Reminder-Corporate-Action-Recording-Date-"
    "SHAI06XXSCFS-INAB01XXSCFS-INAB02XXSCFS-SGRO-RBMS-PORI01XXSCFS-NZIA-POWR-FREN-"
    "SIISAT03DCN2-ISAT03DCN2-ALII-HAIS-SDRA-BBTN-IDVB0617042025-BBNI-BEXI04FCN4-"
    "ASDF06CCN3-BEXI04ECN4-BEXI04DCN4-ASDF06BCN3-RALS"
)
KSEI_MERGER_REPORT_URL = (
    "https://web.ksei.co.id/ksei_news/read/17421/Reminder-CA-Pendistribusian-Laporan-dan-"
    "Pendistribusian-Hak-CA-melalui-C-BEST-per-tanggal-16-April-2025"
)
KSEI_MERGER_DISTRIBUTION_URL = (
    "https://web.ksei.co.id/ksei_news/read/17423/Reminder-CA-Pendistribusian-Laporan-dan-"
    "Pendistribusian-Hak-CA-melalui-C-BEST-per-tanggal-17-April-2025"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def norm_text(value: str | bytes) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    value = html.unescape(str(value))
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\u00a0", " ").replace("\u00ad", " ")
    return " ".join(value.split()).casefold()


def pdf_text(payload: bytes) -> str:
    if not payload:
        raise RuntimeError("FREN_OFFICIAL_PDF_EMPTY")
    reader = PdfReader(BytesIO(payload))
    return " ".join((page.extract_text() or "") for page in reader.pages)


def extract_official_pdf_urls(payload: bytes, base_url: str) -> tuple[str, ...]:
    raw = payload.decode("utf-8", errors="ignore")
    candidates: set[str] = set()
    for match in re.finditer(r'''(?:href|src|data-src|data-url|url)\s*=\s*["']([^"']+)["']''', raw, re.I):
        candidates.add(html.unescape(match.group(1)))
    for match in re.finditer(r'''https?://[^\s"'<>]+?\.pdf(?:\?[^\s"'<>]*)?''', raw, re.I):
        candidates.add(html.unescape(match.group(0)))
    output: list[str] = []
    for candidate in candidates:
        url = urljoin(base_url, candidate)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if not parsed.netloc.lower().endswith("smartfren.com"):
            continue
        if ".pdf" not in parsed.path.lower():
            continue
        output.append(url)
    return tuple(sorted(set(output)))


def verify_smartfren_archive_pages(
    corporate_action_html: bytes,
    disclosure_html: bytes,
    merger_archive_html: bytes,
    investor_about_html: bytes,
) -> dict[str, object]:
    action = norm_text(corporate_action_html)
    disclosure = norm_text(disclosure_html)
    merger = norm_text(merger_archive_html)
    about = norm_text(investor_about_html)

    if "aksi korporasi 2024" not in action or "prospektus pmhmetd v pt smartfren telecom tbk" not in action:
        raise RuntimeError("FREN_ISSUER_2024_CORPORATE_ACTION_ARCHIVE_IDENTITY_MISSING")
    forbidden_2024 = (
        "stock split", "reverse stock", "saham bonus", "bonus shares", "dividen saham",
        "mandatory conversion", "voluntary conversion", "merger",
    )
    observed_forbidden = [token for token in forbidden_2024 if token in action]
    if observed_forbidden:
        raise RuntimeError(f"FREN_ISSUER_2024_ARCHIVE_ADDITIONAL_MECHANICAL_FAMILY:{observed_forbidden}")

    required_disclosure = (
        "perubahan jadwal pmhmetd v",
        "informasi tambahan pmhmetd v fren",
        "prospektus ringkas pmhmetd v fren",
    )
    missing = [token for token in required_disclosure if token not in disclosure]
    if missing:
        raise RuntimeError(f"FREN_ISSUER_2024_DISCLOSURE_SET_MISSING:{missing}")

    if "merger" not in merger or "fren" not in merger:
        raise RuntimeError("FREN_ISSUER_MERGER_ARCHIVE_IDENTITY_MISSING")
    if "16 april 2025" not in about or "pt smartfren telecom tbk" not in about or "pt xl axiata tbk" not in about:
        raise RuntimeError("FREN_ISSUER_MERGER_EFFECTIVE_DATE_MISSING")
    return {
        "mechanical_census_method": "ISSUER_OFFICIAL_ARCHIVE_PLUS_KSEI_EVENT_CORROBORATION",
        "issuer_2024_mechanical_families": ["PMHMETD_V_RIGHTS_ISSUE"],
        "issuer_2025_terminal_family": "MERGER_SECURITY_CESSATION",
    }


def verify_ksei_right_pages(record_html: bytes, distribution_html: bytes) -> None:
    record = norm_text(record_html)
    distribution = norm_text(distribution_html)
    record_required = (
        "18 april 2024",
        "fren",
        "smartfren telecom",
        "distribusi right/ efek",
    )
    distribution_required = (
        "19 april 2024",
        "fren",
        "smartfren telecom",
        "distribusi right/ efek",
        "member entitlement",
    )
    missing_record = [token for token in record_required if token not in record]
    missing_distribution = [token for token in distribution_required if token not in distribution]
    if missing_record or missing_distribution:
        raise RuntimeError(
            f"FREN_KSEI_RIGHT_IDENTITY_MISSING:record={missing_record}:distribution={missing_distribution}"
        )


def verify_ksei_merger_pages(record_html: bytes, report_html: bytes, distribution_html: bytes) -> None:
    record = norm_text(record_html)
    report = norm_text(report_html)
    distribution = norm_text(distribution_html)
    if not all(token in record for token in ("16 april 2025", "fren", "stock split/ reverse stock/ amortisasi")):
        raise RuntimeError("FREN_KSEI_MERGER_RECORD_IDENTITY_MISSING")
    if not all(token in report for token in ("16 april 2025", "fren", "voluntary conversion")):
        raise RuntimeError("FREN_KSEI_MERGER_REPORT_IDENTITY_MISSING")
    if not all(token in distribution for token in ("17 april 2025", "fren", "stock split/ reverse stock/ amortisasi")):
        raise RuntimeError("FREN_KSEI_MERGER_DISTRIBUTION_IDENTITY_MISSING")


def verify_rights_prospectus(payload: bytes) -> dict[str, object]:
    text = norm_text(pdf_text(payload))
    required = (
        "178",
        "75",
        "18 april 2024",
        "22 april 2024",
        "6 mei 2024",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError(f"FREN_RIGHTS_PROSPECTUS_CORE_SCHEDULE_MISSING:{missing}")

    date_index = text.find("17 april 2024")
    if date_index < 0:
        raise RuntimeError("FREN_RIGHTS_EX_DATE_NOT_EXPLICIT_IN_ISSUER_PDF")
    context = text[max(0, date_index - 350): date_index + 350]
    if "ex" not in context or not any(token in context for token in ("reguler", "regular")):
        raise RuntimeError("FREN_RIGHTS_EX_DATE_CONTEXT_NOT_REGULAR_MARKET")
    if not any(token in context for token in ("negosiasi", "negotiated")):
        raise RuntimeError("FREN_RIGHTS_EX_DATE_CONTEXT_NOT_NEGOTIATED_MARKET")

    return {
        "transition_date": FREN_RIGHT_EX_DATE.date().isoformat(),
        "transition_semantic": "OFFICIAL_ISSUER_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE",
        "ratio": "178_OLD_TO_75_HMETD",
        "record_date": FREN_RIGHT_RECORD_DATE.date().isoformat(),
        "distribution_date": FREN_RIGHT_DISTRIBUTION_DATE.date().isoformat(),
        "trading_start": FREN_RIGHT_TRADING_START.date().isoformat(),
        "trading_end": FREN_RIGHT_TRADING_END.date().isoformat(),
        "source_sha256": sha256_bytes(payload),
    }


def combined_evidence_sha(payloads: Iterable[bytes]) -> str:
    digest = hashlib.sha256()
    for payload in payloads:
        digest.update(hashlib.sha256(payload).digest())
    return digest.hexdigest()


def synthetic_fren_rights_event(source_sha256: str) -> EventSemantic:
    event_id = hashlib.sha256(
        f"FREN|PMHMETD_V|2024-04-17|178:75|{source_sha256}".encode("utf-8")
    ).hexdigest()
    return EventSemantic(
        event_id=event_id,
        ticker="FREN",
        source_type="OFFICIAL_ISSUER_PMHMETD_V",
        family="RIGHT_DISTRIBUTION_PMHMETD_V",
        semantic_class="EXACT_TRANSITION",
        transition_date=FREN_RIGHT_EX_DATE,
        transition_source="OFFICIAL_ISSUER_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE",
        reason="EXACT_FREN_PMHMETD_V_EX_RIGHT_2024-04-17_NO_RECORD_DATE_INFERENCE",
        source_dates=(FREN_RIGHT_RECORD_DATE, FREN_RIGHT_DISTRIBUTION_DATE),
    )
