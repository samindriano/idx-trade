"""Exact FREN PMHMETD V semantics from the official KSEI rights schedule.

This module is intentionally narrow.  It accepts only the pinned KSEI PDF that
explicitly states the Regular/Negotiated Market cum/ex-right schedule for FREN
PMHMETD V.  The 2024-04-17 transition is therefore never derived from the
2024-04-18 record date.
"""

from __future__ import annotations

import hashlib
import re

import pandas as pd

from idx_trade.v4_ca_event_windows import EventSemantic
from idx_trade.v4_ca_fren_archive_semantics import (
    FREN_RIGHT_DISTRIBUTION_DATE,
    FREN_RIGHT_EX_DATE,
    FREN_RIGHT_RECORD_DATE,
    FREN_RIGHT_TRADING_END,
    FREN_RIGHT_TRADING_START,
    norm_text,
    pdf_text,
)


KSEI_RIGHTS_SCHEDULE_URL = (
    "https://web.ksei.co.id/Announcement/Files/"
    "165545_ksei_7000_jku_0424_202404041510.pdf"
)
EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256 = (
    "5af9284d88a7621f3b400fe7f9a28e104459ae6e710e47bf765974c940daaa91"
)
EXPECTED_KSEI_RIGHTS_INDEX_SHA256 = (
    "b53cfa79bece2d989019c5b00f1f6df8fb80f970022911977e3f6de4994093aa"
)
KSEI_RIGHTS_REFERENCE = "KSEI-7000/JKU/0424"
FREN_RIGHT_CUM_DATE = pd.Timestamp("2024-04-16")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify_ksei_fren_rights_schedule_pdf(payload: bytes) -> dict[str, object]:
    digest = sha256_bytes(payload)
    if digest != EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256:
        raise RuntimeError(f"FREN_KSEI_RIGHTS_SCHEDULE_SHA_CHANGED:{digest}")

    text = norm_text(pdf_text(payload))
    required = (
        "smartfren telecom",
        "fren",
        "hmetd",
        "16 april 2024",
        "17 april 2024",
        "18 april 2024",
        "19 april 2024",
        "22 april 2024",
        "6 mei 2024",
        "178",
        "75",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError(f"FREN_KSEI_RIGHTS_SCHEDULE_CORE_MARKER_MISSING:{missing}")

    ex_labels = (
        "tanggal ex di pasar regular dan pasar negosiasi",
        "tanggal ex di pasar reguler dan pasar negosiasi",
        "ex hmetd di pasar regular dan pasar negosiasi",
        "ex hmetd di pasar reguler dan pasar negosiasi",
    )
    if not any(token in text for token in ex_labels):
        raise RuntimeError("FREN_KSEI_EX_RIGHT_LABEL_MISSING")

    cum_labels = (
        "tanggal cum di pasar regular dan pasar negosiasi",
        "tanggal cum di pasar reguler dan pasar negosiasi",
        "cum hmetd di pasar regular dan pasar negosiasi",
        "cum hmetd di pasar reguler dan pasar negosiasi",
    )
    if not any(token in text for token in cum_labels):
        raise RuntimeError("FREN_KSEI_CUM_RIGHT_LABEL_MISSING")

    if "tanggal pencatatan" not in text and "recording date" not in text:
        raise RuntimeError("FREN_KSEI_RECORD_DATE_LABEL_MISSING")
    if "tanggal distribusi" not in text and "distribution" not in text:
        raise RuntimeError("FREN_KSEI_DISTRIBUTION_LABEL_MISSING")
    if not re.search(r"178.{0,250}75.{0,120}hmetd", text):
        raise RuntimeError("FREN_KSEI_RIGHT_RATIO_CONTEXT_MISSING")

    ref_match = re.search(r"ksei-\d+/[a-z]+/\d{4}", text, flags=re.I)
    reference = ref_match.group(0).upper() if ref_match else None
    if reference != KSEI_RIGHTS_REFERENCE:
        raise RuntimeError(f"FREN_KSEI_RIGHTS_REFERENCE_CHANGED:{reference}")

    return {
        "transition_date": FREN_RIGHT_EX_DATE.date().isoformat(),
        "transition_semantic": "OFFICIAL_KSEI_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE",
        "cum_regular_negotiated": FREN_RIGHT_CUM_DATE.date().isoformat(),
        "record_date": FREN_RIGHT_RECORD_DATE.date().isoformat(),
        "distribution_date": FREN_RIGHT_DISTRIBUTION_DATE.date().isoformat(),
        "trading_start": FREN_RIGHT_TRADING_START.date().isoformat(),
        "trading_end": FREN_RIGHT_TRADING_END.date().isoformat(),
        "ratio": "178_OLD_TO_75_HMETD",
        "reference_no": reference,
        "source_url": KSEI_RIGHTS_SCHEDULE_URL,
        "source_sha256": digest,
    }


def synthetic_fren_rights_event_ksei(source_sha256: str) -> EventSemantic:
    if source_sha256 != EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256:
        raise RuntimeError("FREN_KSEI_RIGHTS_EVENT_SOURCE_SHA_NOT_PINNED")
    event_id = hashlib.sha256(
        f"FREN|PMHMETD_V|2024-04-17|178:75|KSEI|{source_sha256}".encode("utf-8")
    ).hexdigest()
    return EventSemantic(
        event_id=event_id,
        ticker="FREN",
        source_type="OFFICIAL_KSEI_RIGHTS_SCHEDULE",
        family="RIGHT_DISTRIBUTION_PMHMETD_V",
        semantic_class="EXACT_TRANSITION",
        transition_date=FREN_RIGHT_EX_DATE,
        transition_source="OFFICIAL_KSEI_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE",
        reason="EXACT_FREN_PMHMETD_V_KSEI_EX_RIGHT_2024-04-17_NO_RECORD_DATE_INFERENCE",
        source_dates=(
            FREN_RIGHT_CUM_DATE,
            FREN_RIGHT_RECORD_DATE,
            FREN_RIGHT_DISTRIBUTION_DATE,
            FREN_RIGHT_TRADING_START,
            FREN_RIGHT_TRADING_END,
        ),
    )
