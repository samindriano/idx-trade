from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib

import pandas as pd
import requests


KSEI_HOLDING_COMPOSITION_BASE_URL = "https://web.ksei.co.id/Download"


@dataclass(frozen=True)
class KSEIHoldingCompositionCapture:
    snapshot_date: str
    source_ref: str
    raw_bytes: bytes
    retrieval_started_at_utc: str
    observed_available_at_utc: str

    @property
    def raw_sha256(self) -> str:
        return hashlib.sha256(self.raw_bytes).hexdigest()

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result.pop("raw_bytes", None)
        result["raw_sha256"] = self.raw_sha256
        return result


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def holding_composition_url(snapshot_date: str | pd.Timestamp) -> str:
    day = pd.Timestamp(snapshot_date).normalize()
    if pd.isna(day):
        raise ValueError("invalid KSEI holding-composition snapshot date")
    return f"{KSEI_HOLDING_COMPOSITION_BASE_URL}/BalanceposEfek{day.strftime('%Y%m%d')}.zip"


def fetch_holding_composition_zip(
    snapshot_date: str | pd.Timestamp,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> KSEIHoldingCompositionCapture:
    """Fetch one official KSEI monthly holding-composition ZIP as raw evidence.

    This source is an ownership-composition archive, not a named-holder >1%
    disclosure and not a statutory/effective free-float series. Parsing is kept
    separate until the ZIP member schema is independently audited.
    """

    day = pd.Timestamp(snapshot_date).normalize()
    if pd.isna(day):
        raise ValueError("invalid KSEI holding-composition snapshot date")
    url = holding_composition_url(day)
    client = session or requests.Session()
    started = _utc_now()
    response = client.get(
        url,
        headers={
            "Accept": "application/zip, application/octet-stream, */*",
            "Referer": "https://web.ksei.co.id/archive_download/holding_composition",
            "User-Agent": "Mozilla/5.0 idx-trade-research/2.0",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    raw = bytes(response.content)
    if len(raw) < 4 or raw[:2] != b"PK":
        raise ValueError("KSEI holding-composition response is not a ZIP archive")
    observed = _utc_now()
    return KSEIHoldingCompositionCapture(
        snapshot_date=day.date().isoformat(),
        source_ref=str(getattr(response, "url", "") or url),
        raw_bytes=raw,
        retrieval_started_at_utc=started,
        observed_available_at_utc=observed,
    )
