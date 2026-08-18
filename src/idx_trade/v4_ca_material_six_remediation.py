"""Outcome-blind helpers for the six material V4 corporate-action remediations.

Targets are exactly FREN, ADRO, MEGA, SCMA, AVIA, and SMAR.  The helpers keep
all frozen CA semantics fail-closed: no price inference, no record/distribution
fallback to an ex-date, and no source substitution.  FREN and MEGA admit only
issuer-official exact boundaries; ADRO deliberately remains unresolved unless
an explicit regular-market ex/first-new-basis date is supplied by primary
official evidence.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
from pypdf import PdfReader

from idx_trade.v4_ca_event_windows import EventSemantic
from idx_trade.v4_ksei_ca_history import MECHANICAL_FAMILIES, is_active_status, row_dates
from idx_trade.v4_ksei_coverage_gap import parse_bool_series


MATERIAL_SIX = ("FREN", "ADRO", "MEGA", "SCMA", "AVIA", "SMAR")
KSEI_RETRY_TICKERS = ("AVIA", "SMAR", "MEGA", "SCMA", "FREN", "ADRO")
EXPECTED_PARENT_TICKERS = 610
EXPECTED_PARENT_CERTIFIED = 599
EXPECTED_PARENT_UNRESOLVED = frozenset(
    {"AMAN", "AVIA", "AYAM", "BCIP", "PRIM", "SKRN", "SLIS", "SMAR", "SNLK", "SOCI", "SOFA"}
)
EXPECTED_AFTER_AVIA_SMAR_UNRESOLVED = EXPECTED_PARENT_UNRESOLVED - {"AVIA", "SMAR"}

FREN_EFFECTIVE_DATE = pd.Timestamp("2025-04-16")
MEGA_REGULAR_EX_BONUS_DATE = pd.Timestamp("2026-04-10")
SCMA_PRIOR_ACTION_ID = "82840"
SCMA_PRIOR_CANDIDATE_DATE = pd.Timestamp("2026-08-10")

FREN_OFFICIAL_DISCLOSURE_URL = (
    "https://static-cms-xlsmart.xlaxiata.my.id/production/uploads/"
    "13a35c6c-965e-48a6-9030-713167b2b5f7.pdf"
)
MEGA_OFFICIAL_BONUS_URL = (
    "https://cdn.bankmega.com/prod.mega.cms.media/filer_public/46/ab/"
    "46ab339f-9c9a-4a72-a783-0e440e2f69b3/ki_rencana_pembagian_saham_bonus_ind_final.pdf"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize_ticker(value: Any) -> str:
    return str(value or "").upper().replace(".JK", "").strip()


def normalize_parent_coverage(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker", "coverage_status", "coverage_certified", "attempt_count",
        "final_http_status", "source_url", "source_sha256", "ca_rows",
        "active_ca_rows", "active_mechanical_rows", "active_unknown_rows",
        "earliest_ca_date", "latest_ca_date", "failure_reason",
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"MATERIAL_SIX_PARENT_COVERAGE_COLUMNS_MISSING:{sorted(missing)}")
    result = frame.copy()
    result["ticker"] = result["ticker"].map(normalize_ticker)
    result["coverage_certified"] = parse_bool_series(
        result["coverage_certified"], label="material_six_parent_coverage_certified"
    )
    if len(result) != EXPECTED_PARENT_TICKERS or result["ticker"].nunique() != EXPECTED_PARENT_TICKERS:
        raise RuntimeError("MATERIAL_SIX_PARENT_610_IDENTITY_CHANGED")
    if int(result["coverage_certified"].sum()) != EXPECTED_PARENT_CERTIFIED:
        raise RuntimeError("MATERIAL_SIX_PARENT_CERTIFIED_COUNT_CHANGED")
    unresolved = set(result.loc[~result["coverage_certified"], "ticker"])
    if unresolved != EXPECTED_PARENT_UNRESOLVED:
        raise RuntimeError(f"MATERIAL_SIX_PARENT_UNRESOLVED_SET_CHANGED:{sorted(unresolved)}")
    return result.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def parsed_history_stats(rows: Sequence[Mapping[str, Any]], ticker: str) -> dict[str, Any]:
    target = normalize_ticker(ticker)
    if not rows:
        raise RuntimeError(f"MATERIAL_SIX_STRICT_PARSE_EMPTY:{target}")
    for row in rows:
        if normalize_ticker(row.get("ticker")) != target:
            raise RuntimeError(f"MATERIAL_SIX_PARSED_TICKER_MISMATCH:{target}")
        if not str(row.get("source_url") or "").strip() or not str(row.get("source_sha256") or "").strip():
            raise RuntimeError(f"MATERIAL_SIX_PARSED_PROVENANCE_MISSING:{target}")
    active = [row for row in rows if is_active_status(str(row.get("status") or ""))]
    active_mechanical = [row for row in active if str(row.get("event_family") or "") in MECHANICAL_FAMILIES]
    active_unknown = [row for row in active if str(row.get("event_family") or "") == "UNKNOWN"]
    dates = sorted({date for row in rows for date in row_dates(dict(row))})
    return {
        "ca_rows": len(rows),
        "active_ca_rows": len(active),
        "active_mechanical_rows": len(active_mechanical),
        "active_unknown_rows": len(active_unknown),
        "earliest_ca_date": dates[0] if dates else "",
        "latest_ca_date": dates[-1] if dates else "",
        "event_families": sorted({str(row.get("event_family") or "") for row in rows}),
        "event_source_types": sorted({str(row.get("event_family_source") or "") for row in rows}),
    }


def refreshed_coverage_row(
    parent_row: Mapping[str, Any], *, ticker: str, success_record: Mapping[str, Any],
    security_attempt_count: int, stats: Mapping[str, Any],
) -> dict[str, Any]:
    target = normalize_ticker(ticker)
    if normalize_ticker(parent_row.get("ticker")) != target:
        raise RuntimeError(f"MATERIAL_SIX_REFRESH_PARENT_TICKER_MISMATCH:{target}")
    if int(success_record.get("status_code") or 0) != 200:
        raise RuntimeError(f"MATERIAL_SIX_REFRESH_HTTP_NOT_200:{target}")
    if security_attempt_count < 1 or security_attempt_count > 2:
        raise RuntimeError(f"MATERIAL_SIX_REFRESH_ATTEMPTS_OUT_OF_BOUNDS:{target}")
    result = dict(parent_row)
    result.update({
        "coverage_status": "COVERAGE_CERTIFIED",
        "coverage_certified": True,
        "attempt_count": security_attempt_count,
        "final_http_status": 200,
        "source_url": str(success_record.get("final_url") or ""),
        "source_sha256": str(success_record.get("sha256") or ""),
        "ca_rows": int(stats["ca_rows"]),
        "active_ca_rows": int(stats["active_ca_rows"]),
        "active_mechanical_rows": int(stats["active_mechanical_rows"]),
        "active_unknown_rows": int(stats["active_unknown_rows"]),
        "earliest_ca_date": str(stats["earliest_ca_date"]),
        "latest_ca_date": str(stats["latest_ca_date"]),
        "failure_reason": "",
    })
    return result


def new_fren_coverage_row(
    columns: Sequence[str], *, success_record: Mapping[str, Any] | None,
    security_attempt_count: int, stats: Mapping[str, Any] | None, failure_reason: str,
) -> dict[str, Any]:
    row = {column: "" for column in columns}
    row["ticker"] = "FREN"
    if success_record is None or stats is None:
        row.update({
            "coverage_status": "COVERAGE_UNRESOLVED",
            "coverage_certified": False,
            "attempt_count": security_attempt_count,
            "final_http_status": 0,
            "source_url": "https://web.ksei.co.id/services/registered-securities/shares/lc/FREN?setLocale=en-US",
            "source_sha256": "",
            "ca_rows": 0,
            "active_ca_rows": 0,
            "active_mechanical_rows": 0,
            "active_unknown_rows": 0,
            "earliest_ca_date": "",
            "latest_ca_date": "",
            "failure_reason": failure_reason or "FREN_KSEI_COMPLETE_HISTORY_UNAVAILABLE",
        })
        return row
    row.update({
        "coverage_status": "COVERAGE_CERTIFIED",
        "coverage_certified": True,
        "attempt_count": security_attempt_count,
        "final_http_status": 200,
        "source_url": str(success_record.get("final_url") or ""),
        "source_sha256": str(success_record.get("sha256") or ""),
        "ca_rows": int(stats["ca_rows"]),
        "active_ca_rows": int(stats["active_ca_rows"]),
        "active_mechanical_rows": int(stats["active_mechanical_rows"]),
        "active_unknown_rows": int(stats["active_unknown_rows"]),
        "earliest_ca_date": str(stats["earliest_ca_date"]),
        "latest_ca_date": str(stats["latest_ca_date"]),
        "failure_reason": "",
    })
    return row


def replace_history_ticker(
    parent_rows: Sequence[Mapping[str, Any]], new_rows: Sequence[Mapping[str, Any]], ticker: str,
) -> list[dict[str, Any]]:
    target = normalize_ticker(ticker)
    if any(normalize_ticker(row.get("ticker")) != target for row in new_rows):
        raise RuntimeError(f"MATERIAL_SIX_REFRESH_HISTORY_SCOPE:{target}")
    kept = [dict(row) for row in parent_rows if normalize_ticker(row.get("ticker")) != target]
    return [*kept, *(dict(row) for row in new_rows)]


def pdf_text(payload: bytes) -> str:
    if not payload:
        raise RuntimeError("MATERIAL_SIX_OFFICIAL_PDF_EMPTY")
    reader = PdfReader(BytesIO(payload))
    return " ".join((page.extract_text() or "") for page in reader.pages).replace("\u00a0", " ")


def verify_fren_official_disclosure(payload: bytes) -> dict[str, Any]:
    text = " ".join(pdf_text(payload).split())
    required = (
        "Tanggal Kejadian 16 April 2025",
        "PT Smartfren Telecom Tbk",
        "status SF serta ST berakhir karena hukum",
        "Penggabungan Usaha antara XL, SF dan ST telah efektif",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError(f"FREN_OFFICIAL_DISCLOSURE_SEMANTICS_MISSING:{missing}")
    return {
        "transition_date": FREN_EFFECTIVE_DATE.date().isoformat(),
        "transition_semantic": "OFFICIAL_MERGER_EFFECTIVE_SECURITY_CESSATION",
        "source_url": FREN_OFFICIAL_DISCLOSURE_URL,
        "source_sha256": sha256_bytes(payload),
        "no_excl_price_stitching": True,
    }


def verify_mega_official_bonus(payload: bytes) -> dict[str, Any]:
    text = " ".join(pdf_text(payload).split())
    required = (
        "Rasio Pembagian Saham Bonus 1 (satu) saham lama akan memperoleh 1 (satu) saham Bonus",
        "9 April 2026",
        "10 April 2026",
        "30 April 2026",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError(f"MEGA_OFFICIAL_BONUS_SEMANTICS_MISSING:{missing}")
    return {
        "transition_date": MEGA_REGULAR_EX_BONUS_DATE.date().isoformat(),
        "transition_semantic": "REGULAR_MARKET_EX_BONUS_DATE",
        "ratio": "1_OLD_TO_1_BONUS",
        "source_url": MEGA_OFFICIAL_BONUS_URL,
        "source_sha256": sha256_bytes(payload),
    }


def validate_scma_halo_only(prior: pd.DataFrame, *, max_terminal: pd.Timestamp) -> dict[str, Any]:
    work = prior.copy()
    work["ticker"] = work["ticker"].map(normalize_ticker)
    work["candidate_date"] = pd.to_datetime(work["candidate_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    scma = work[work["ticker"].eq("SCMA")].copy()
    exact = scma[
        scma.get("source_action_id", pd.Series(index=scma.index, dtype=str)).astype(str).eq(SCMA_PRIOR_ACTION_ID)
        & scma["candidate_date"].eq(SCMA_PRIOR_CANDIDATE_DATE)
    ]
    if len(exact) != 1:
        raise RuntimeError(f"SCMA_EXACT_PRIOR_CANDIDATE_IDENTITY_CHANGED:{len(exact)}")
    in_period = scma[scma["candidate_date"] <= pd.Timestamp(max_terminal).normalize()]
    if not in_period.empty:
        raise RuntimeError("SCMA_HAS_IN_PERIOD_PRIOR_CANDIDATE_CANNOT_HALO_CLEAR")
    return {
        "source_action_id": SCMA_PRIOR_ACTION_ID,
        "candidate_date": SCMA_PRIOR_CANDIDATE_DATE.date().isoformat(),
        "max_frozen_terminal_date": pd.Timestamp(max_terminal).date().isoformat(),
        "classification": "OUTSIDE_FROZEN_TARGET_PERIOD_NONBLOCKING_HALO_ONLY",
    }


def synthetic_fren_event(source_sha256: str) -> EventSemantic:
    event_id = hashlib.sha256(
        f"FREN|MERGER_CESSATION|2025-04-16|{source_sha256}".encode("utf-8")
    ).hexdigest()
    return EventSemantic(
        event_id=event_id,
        ticker="FREN",
        source_type="OFFICIAL_XLSMART_MERGER_EFFECTIVE",
        family="MERGER_OR_RESTRUCTURING",
        semantic_class="EXACT_TRANSITION",
        transition_date=FREN_EFFECTIVE_DATE,
        transition_source="OFFICIAL_ISSUER_MATERIAL_DISCLOSURE",
        reason="SMARTFREN_CEASES_BY_OPERATION_OF_LAW_NO_EXCL_PRICE_STITCHING",
        source_dates=(FREN_EFFECTIVE_DATE,),
    )


def synthetic_mega_event(source_sha256: str) -> EventSemantic:
    event_id = hashlib.sha256(
        f"MEGA|BONUS_SHARES|2026-04-10|{source_sha256}".encode("utf-8")
    ).hexdigest()
    return EventSemantic(
        event_id=event_id,
        ticker="MEGA",
        source_type="OFFICIAL_ISSUER_BONUS_SHARES",
        family="BONUS_SHARES",
        semantic_class="EXACT_TRANSITION",
        transition_date=MEGA_REGULAR_EX_BONUS_DATE,
        transition_source="OFFICIAL_ISSUER_REGULAR_MARKET_EX_DATE",
        reason="EXACT_2026_REGULAR_MARKET_EX_BONUS_DATE",
        source_dates=(pd.Timestamp("2026-04-09"), pd.Timestamp("2026-04-13"), pd.Timestamp("2026-04-30")),
    )
