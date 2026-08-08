from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Iterable

import pandas as pd
import requests
from pypdf import PdfReader

from ..security_master import canonicalize_tradability_intervals, normalise_market, normalise_ticker


PARSER_VERSION = "idx-tradability-v1"
EVENT_COLUMNS = (
    "ticker", "market", "action", "effective_date", "announced_at", "announcement_no",
    "source", "source_ref", "document_sha256", "parser_version",
)

INDONESIAN_MONTHS = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}


class TradabilityAction(StrEnum):
    SUSPEND = "SUSPEND"
    RESUME = "RESUME"


@dataclass(frozen=True)
class ParseResult:
    events: pd.DataFrame
    status: str
    diagnostic: str


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _parse_indonesian_date(value: str) -> pd.Timestamp:
    match = re.search(r"(?i)\b(\d{1,2})\s+([a-z]+)\s+(\d{4})\b", value)
    if not match:
        raise ValueError(f"Cannot parse Indonesian date: {value!r}")
    day, month_name, year = match.groups()
    month = INDONESIAN_MONTHS.get(month_name.lower())
    if month is None:
        raise ValueError(f"Unknown Indonesian month: {month_name}")
    return pd.Timestamp(year=int(year), month=month, day=int(day)).normalize()


def _announcement_number(text: str) -> str:
    match = re.search(r"\bPeng-(?:SPT|UPT)-[A-Z0-9./-]+", text, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def _tickers(text: str) -> list[str]:
    # Warrants normally appear as e.g. (INET-W); this intentionally accepts only
    # four-character equity symbols enclosed by parentheses.
    values = re.findall(r"\(([A-Z0-9]{4})\)", text.upper())
    return list(dict.fromkeys(normalise_ticker(value) for value in values))


def _markets(text: str) -> list[str]:
    """Extract the equity market scope conservatively.

    A common IDX document says the stock is suspended in Regular/Cash while a
    warrant in the same document is suspended in All Markets. Explicit named
    stock markets therefore take precedence over a generic `Seluruh Pasar`
    mention elsewhere in the document.
    """

    lowered = text.lower()
    result: list[str] = []
    if "pasar reguler" in lowered:
        result.append("REGULAR")
    if "pasar tunai" in lowered:
        result.append("CASH")
    if "pasar negosiasi" in lowered:
        result.append("NEGOTIATED")
    if result:
        return list(dict.fromkeys(result))
    if "seluruh pasar" in lowered:
        return ["ALL"]
    return []


def _resume_date(text: str) -> pd.Timestamp | None:
    patterns = [
        r"(?i)dibuka kembali.{0,180}?tanggal\s+(\d{1,2}\s+[a-z]+\s+\d{4})",
        r"(?i)unsuspensi.{0,180}?tanggal\s+(\d{1,2}\s+[a-z]+\s+\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _parse_indonesian_date(match.group(1))
    return None


def _suspend_date(text: str) -> pd.Timestamp | None:
    patterns = [
        r"(?i)(?:mulai\s+)?sesi\s+i.{0,80}?tanggal\s+(\d{1,2}\s+[a-z]+\s+\d{4})",
        r"(?i)mulai.{0,80}?tanggal\s+(\d{1,2}\s+[a-z]+\s+\d{4})",
        r"(?i)perdagangan.{0,100}?pada tanggal\s+(\d{1,2}\s+[a-z]+\s+\d{4})",
        r"(?i)pada tanggal\s+(\d{1,2}\s+[a-z]+\s+\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _parse_indonesian_date(match.group(1))
    return None


def _is_complex_intraday_document(text: str) -> bool:
    lowered = text.lower()
    has_open = "membuka penghentian sementara" in lowered or "dibuka kembali" in lowered
    has_resuspend = "suspensi" in lowered and "kembali" in lowered
    has_clock = bool(re.search(r"\b\d{1,2}[.:]\d{2}\s*wib\b", lowered))
    return has_open and has_resuspend and has_clock


def parse_idx_tradability_announcement(
    text: str,
    *,
    source_ref: str = "",
    announced_at: pd.Timestamp | str | None = None,
) -> ParseResult:
    """Parse a text-extractable IDX suspension/unsuspension announcement.

    This parser is deliberately conservative. Documents containing multiple
    intraday state changes are rejected for manual review rather than flattened
    into a false daily state.
    """

    clean = _normalise_text(text)
    if not clean:
        return ParseResult(pd.DataFrame(columns=EVENT_COLUMNS), "REJECTED", "EMPTY_TEXT")
    if _is_complex_intraday_document(clean):
        return ParseResult(pd.DataFrame(columns=EVENT_COLUMNS), "MANUAL_REVIEW", "MULTI_ACTION_INTRADAY_DOCUMENT")

    tickers = _tickers(clean)
    markets = _markets(clean)
    if not tickers:
        return ParseResult(pd.DataFrame(columns=EVENT_COLUMNS), "MANUAL_REVIEW", "TICKER_NOT_FOUND")
    if not markets:
        return ParseResult(pd.DataFrame(columns=EVENT_COLUMNS), "MANUAL_REVIEW", "MARKET_SCOPE_NOT_FOUND")

    lowered = clean.lower()
    resume_language = "dibuka kembali" in lowered or "unsuspensi" in lowered
    if resume_language:
        action = TradabilityAction.RESUME
        effective = _resume_date(clean)
    elif "penghentian sementara" in lowered or "suspensi" in lowered:
        action = TradabilityAction.SUSPEND
        effective = _suspend_date(clean)
    else:
        return ParseResult(pd.DataFrame(columns=EVENT_COLUMNS), "REJECTED", "TRADABILITY_ACTION_NOT_FOUND")

    if effective is None:
        return ParseResult(pd.DataFrame(columns=EVENT_COLUMNS), "MANUAL_REVIEW", "EFFECTIVE_DATE_NOT_FOUND")

    announced = pd.to_datetime(announced_at, errors="coerce") if announced_at is not None else pd.NaT
    digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()
    rows = []
    for ticker in tickers:
        for market in markets:
            rows.append(
                {
                    "ticker": ticker,
                    "market": normalise_market(market),
                    "action": action.value,
                    "effective_date": effective,
                    "announced_at": announced,
                    "announcement_no": _announcement_number(clean),
                    "source": "IDX_EXCHANGE_ANNOUNCEMENT",
                    "source_ref": source_ref,
                    "document_sha256": digest,
                    "parser_version": PARSER_VERSION,
                }
            )
    return ParseResult(pd.DataFrame(rows, columns=EVENT_COLUMNS), "PARSED", "OK")


def fetch_pdf_text(url: str, *, timeout: int = 30) -> tuple[str, str]:
    """Download a text-based IDX PDF and return extracted text + byte hash.

    Scanned/image-only PDFs intentionally fail; the research pipeline must not
    silently OCR or invent exchange-state evidence.
    """

    response = requests.get(
        url,
        headers={"Referer": "https://www.idx.id/", "User-Agent": "idx-trade-research/2.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.content
    digest = hashlib.sha256(payload).hexdigest()
    reader = PdfReader(io.BytesIO(payload))
    text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if not text:
        raise ValueError(f"IDX announcement PDF has no extractable text: {url}")
    return text, digest


def ingest_announcement_manifest(
    manifest: pd.DataFrame,
    *,
    fetcher: Callable[[str], tuple[str, str]] = fetch_pdf_text,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch and parse an explicit manifest of official IDX announcement URLs.

    URL discovery/completeness is intentionally separate. A manifest can be
    audited and hashed; successful parsing does not by itself prove historical
    suspension coverage is complete.
    """

    required = {"source_ref"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"Announcement manifest columns missing: {sorted(missing)}")

    event_frames: list[pd.DataFrame] = []
    diagnostics: list[dict[str, object]] = []
    for row in manifest.itertuples(index=False):
        source_ref = str(row.source_ref)
        announced_at = getattr(row, "announced_at", None)
        try:
            text, byte_hash = fetcher(source_ref)
            result = parse_idx_tradability_announcement(
                text, source_ref=source_ref, announced_at=announced_at
            )
            events = result.events.copy()
            if not events.empty:
                events["document_sha256"] = byte_hash
                event_frames.append(events)
            diagnostics.append(
                {
                    "source_ref": source_ref,
                    "status": result.status,
                    "diagnostic": result.diagnostic,
                    "event_rows": len(events),
                    "document_sha256": byte_hash,
                }
            )
        except Exception as error:
            diagnostics.append(
                {
                    "source_ref": source_ref,
                    "status": "ERROR",
                    "diagnostic": str(error),
                    "event_rows": 0,
                    "document_sha256": "",
                }
            )

    events = pd.concat(event_frames, ignore_index=True) if event_frames else pd.DataFrame(columns=EVENT_COLUMNS)
    if not events.empty:
        events["effective_date"] = pd.to_datetime(events["effective_date"]).dt.normalize()
        events = events.drop_duplicates(["ticker", "market", "action", "effective_date", "source_ref"])
        events = events.sort_values(["ticker", "market", "effective_date", "action"]).reset_index(drop=True)
    return events, pd.DataFrame(diagnostics)


def compile_suspension_intervals(
    events: pd.DataFrame,
    *,
    markets: Iterable[str] = ("REGULAR", "CASH", "NEGOTIATED"),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compile suspension events into non-active market intervals.

    `ALL` events are exploded to concrete markets. RESUME closes the most recent
    open suspension for that market. We intentionally emit only SUSPENDED
    intervals; ACTIVE is inferred only inside separately audited complete
    coverage windows.
    """

    concrete_markets = tuple(normalise_market(value) for value in markets)
    if events.empty:
        return canonicalize_tradability_intervals(pd.DataFrame()), pd.DataFrame()

    required = {"ticker", "market", "action", "effective_date", "source", "source_ref"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"Tradability event columns missing: {sorted(missing)}")

    expanded: list[dict[str, object]] = []
    for row in events.to_dict(orient="records"):
        market = normalise_market(row["market"])
        targets = concrete_markets if market == "ALL" else (market,)
        for target in targets:
            item = dict(row)
            item["market"] = target
            item["ticker"] = normalise_ticker(item["ticker"])
            item["effective_date"] = pd.Timestamp(item["effective_date"]).normalize()
            item["action"] = TradabilityAction(str(item["action"]))
            expanded.append(item)

    frame = pd.DataFrame(expanded).sort_values(["ticker", "market", "effective_date", "action"])
    intervals: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []

    for (ticker, market), group in frame.groupby(["ticker", "market"], sort=False):
        open_suspend: dict[str, object] | None = None
        for row in group.to_dict(orient="records"):
            action = TradabilityAction(row["action"])
            effective = pd.Timestamp(row["effective_date"]).normalize()
            if action is TradabilityAction.SUSPEND:
                if open_suspend is not None:
                    diagnostics.append(
                        {
                            "ticker": ticker,
                            "market": market,
                            "effective_date": effective,
                            "status": "REDUNDANT_SUSPEND",
                            "source_ref": row.get("source_ref", ""),
                        }
                    )
                    continue
                open_suspend = row
                continue

            if open_suspend is None:
                diagnostics.append(
                    {
                        "ticker": ticker,
                        "market": market,
                        "effective_date": effective,
                        "status": "UNMATCHED_RESUME",
                        "source_ref": row.get("source_ref", ""),
                    }
                )
                continue

            start = pd.Timestamp(open_suspend["effective_date"]).normalize()
            if effective <= start:
                diagnostics.append(
                    {
                        "ticker": ticker,
                        "market": market,
                        "effective_date": effective,
                        "status": "INVALID_RESUME_ORDER",
                        "source_ref": row.get("source_ref", ""),
                    }
                )
                open_suspend = None
                continue
            intervals.append(
                {
                    "ticker": ticker,
                    "market": market,
                    "state": "SUSPENDED",
                    "effective_from": start,
                    "effective_to": effective - pd.Timedelta(days=1),
                    "announced_at": open_suspend.get("announced_at", pd.NaT),
                    "source": "IDX_EXCHANGE_ANNOUNCEMENT",
                    "source_ref": f"{open_suspend.get('source_ref', '')}|{row.get('source_ref', '')}",
                }
            )
            open_suspend = None

        if open_suspend is not None:
            intervals.append(
                {
                    "ticker": ticker,
                    "market": market,
                    "state": "SUSPENDED",
                    "effective_from": pd.Timestamp(open_suspend["effective_date"]).normalize(),
                    "effective_to": pd.NaT,
                    "announced_at": open_suspend.get("announced_at", pd.NaT),
                    "source": "IDX_EXCHANGE_ANNOUNCEMENT",
                    "source_ref": open_suspend.get("source_ref", ""),
                }
            )

    output = canonicalize_tradability_intervals(pd.DataFrame(intervals))
    diagnostic_frame = pd.DataFrame(diagnostics)
    return output, diagnostic_frame
