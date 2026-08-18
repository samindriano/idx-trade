"""V3 compatibility entrypoint for the V4 material-six remediation.

Adds narrow, outcome-blind corrections on top of V2:
1. when the frozen KSEI home warmup fails before any security request, retry
   the exact registered-security URL directly in a fresh session using the
   identical strict parser;
2. classify exactly one SMAR Voluntary Conversion row (1 SMAR : 5265 IDR,
   distribution 2026-06-11) as non-blocking security-to-currency semantics,
   matching the already accepted NISP treatment; and
3. do not re-crawl MEGA as a coverage ticker because the frozen 611 support has
   zero MEGA target-window rows. MEGA remains represented only by its already
   pinned issuer-official 2026 bonus-share ex-date evidence.

No alternate provider, no alternate URL, no parser relaxation, no price
inference, no ADRO date inference, and no universe-row waiver are introduced.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = Path(__file__).resolve().parent
for value in (REPO_ROOT / "src", SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import run_v4_ca_material_six_remediation as base
import run_v4_ca_material_six_remediation_v2 as v2
from idx_trade.v4_ca_event_windows import EventSemantic, event_identity, source_dates
from idx_trade.v4_ksei_ca_history import parse_ksei_security_history


_ORIGINAL_RECOVER_TICKER = base.gap_runner.recover_ticker
_ORIGINAL_MATERIAL_CLASSIFIER_FACTORY = base.material_six_classifier
_DIRECT_FALLBACK_TICKERS = {"AVIA", "SMAR", "SCMA", "ADRO"}


def retry_scope_without_zero_support_mega(values: Iterable[str]) -> tuple[str, ...]:
    """Remove only MEGA from provider retry scope; its frozen window count is zero."""

    normalized = tuple(str(value).upper().strip() for value in values)
    if "MEGA" not in normalized:
        raise RuntimeError("MATERIAL_SIX_MEGA_EXPECTED_IN_ORIGINAL_RETRY_SCOPE")
    result = tuple(value for value in normalized if value != "MEGA")
    if set(result) != set(normalized) - {"MEGA"}:
        raise RuntimeError("MATERIAL_SIX_MEGA_RETRY_SCOPE_MUTATION_INVALID")
    return result


def recover_ticker_with_direct_security_fallback(*, ticker: str, provider, raw_root: Path):
    success, records, parsed_rows = _ORIGINAL_RECOVER_TICKER(
        ticker=ticker,
        provider=provider,
        raw_root=raw_root,
    )
    if success is not None:
        return success, records, parsed_rows

    target = str(ticker).upper().strip()
    security_attempts = [
        row for row in records if row.get("request_kind") == "SECURITY_HISTORY"
    ]
    if target not in _DIRECT_FALLBACK_TICKERS or security_attempts:
        return success, records, parsed_rows

    session = base.gap_runner.make_session(provider)
    security_url = str(provider["security_url_template"]).format(ticker=target)
    timeout = float(provider["timeout_seconds"])
    path = raw_root / target / "security_direct_fallback_01.html"
    try:
        response = session.get(security_url, timeout=timeout)
        record = base.gap_runner.capture_response(
            response,
            path=path,
            ticker=target,
            request_kind="SECURITY_HISTORY",
            attempt=1,
            requested_url=security_url,
        )
        record["transport_remediation"] = (
            "DIRECT_EXACT_SECURITY_URL_AFTER_HOME_WARMUP_FAILURE"
        )
        records.append(record)
        if record["status_code"] != 200 or record["bytes"] <= 0:
            record["error"] = (
                f"HTTP_OR_EMPTY:{record['status_code']}:{record['bytes']}"
            )
            return None, records, tuple()
        parsed = parse_ksei_security_history(
            response.content,
            expected_ticker=target,
            source_url=record["final_url"],
            source_sha256=record["sha256"],
        )
        return record, records, parsed.rows
    except Exception as exc:
        if records and records[-1].get("request_kind") == "SECURITY_HISTORY":
            records[-1]["error"] = f"{type(exc).__name__}:{exc}"
            records[-1]["transport_remediation"] = (
                "DIRECT_EXACT_SECURITY_URL_AFTER_HOME_WARMUP_FAILURE"
            )
        else:
            failure = base.gap_runner.error_record(
                ticker=target,
                request_kind="SECURITY_HISTORY",
                attempt=1,
                requested_url=security_url,
                exc=exc,
            )
            failure["transport_remediation"] = (
                "DIRECT_EXACT_SECURITY_URL_AFTER_HOME_WARMUP_FAILURE"
            )
            records.append(failure)
        return None, records, tuple()


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def material_six_classifier_v3(fren_source_sha: str):
    inherited = _ORIGINAL_MATERIAL_CLASSIFIER_FACTORY(fren_source_sha)

    def classify(row, *, official_sessions, schedule_evidence=()) -> EventSemantic:
        base_event = inherited(
            row,
            official_sessions=official_sessions,
            schedule_evidence=schedule_evidence,
        )
        ticker = base.normalize_ticker(row.get("ticker"))
        if ticker != "SMAR":
            return base_event
        if _text(row.get("status")).casefold() != "active":
            return base_event
        if _text(row.get("event_family_source")).casefold() != "voluntary conversion":
            return base_event
        if base.normalize_ticker(row.get("ratio_left_security")) != "SMAR":
            return base_event
        if _text(row.get("ratio_right_security")).upper() != "IDR":
            return base_event
        if _text(row.get("ratio_left_value")) != "1":
            return base_event
        if _text(row.get("ratio_right_value")) != "5265":
            return base_event
        if _text(row.get("distribution_date")) != "2026-06-11":
            return base_event
        if not _text(row.get("source_url")) or not _text(row.get("source_sha256")):
            return base_event
        return EventSemantic(
            event_id=event_identity(row),
            ticker="SMAR",
            source_type=_text(row.get("event_family_source")),
            family="VOLUNTARY_CASH_STATIC_SECURITY_TO_CURRENCY",
            semantic_class="NON_BLOCKING",
            transition_date=None,
            transition_source=None,
            reason="EXACT_OFFICIAL_KSEI_STATIC_SECURITY_TO_IDR_NOT_PRICE_BASIS_REBASE",
            source_dates=source_dates(row),
        )

    return classify


def main() -> int:
    base.gap_runner.recover_ticker = recover_ticker_with_direct_security_fallback
    base.material_six_classifier = material_six_classifier_v3
    base.KSEI_RETRY_TICKERS = retry_scope_without_zero_support_mega(
        base.KSEI_RETRY_TICKERS
    )
    return int(v2.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())