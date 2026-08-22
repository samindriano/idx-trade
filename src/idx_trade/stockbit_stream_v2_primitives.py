"""V2-only provider primitives that harden legacy Stockbit archive behavior.

Kept separate from the V1 archive module so the red-team remediation does not
silently mutate legacy evidence contracts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from idx_trade.stockbit_stream_archive import (
    STREAM_COUNT,
    STREAM_ENDPOINT,
    StreamArchiveError,
    ZapiClient,
    parse_stream_payload,
)


def parse_stream_payload_v2(
    raw: bytes, status_code: int, requested_symbol: str
) -> tuple[str, dict[str, Any] | None, list[dict[str, Any]]]:
    classification, data, items = parse_stream_payload(raw, status_code, requested_symbol)
    if classification != "OK":
        return classification, data, items
    if not isinstance(data, dict) or data.get("provider") != "stockbit":
        return "PROVIDER_MISMATCH_FAIL_CLOSED", data, []
    return classification, data, items


class V2ZapiClient(ZapiClient):
    """Conservative PIT timestamping plus V2 provider provenance validation."""

    def stream(self, symbol: str) -> tuple[requests.Response, bytes, datetime]:
        response = self.session.get(
            STREAM_ENDPOINT,
            params={"symbol": symbol, "count": STREAM_COUNT},
            headers={"x-api-key": self.api_key},
            timeout=self.timeout_seconds,
        )
        observed = datetime.now(timezone.utc)
        raw = bytes(response.content)
        if response.status_code == 200:
            classification, _, _ = parse_stream_payload_v2(raw, response.status_code, symbol)
            if classification == "PROVIDER_MISMATCH_FAIL_CLOSED":
                raise StreamArchiveError("Stockbit Stream provider provenance mismatch")
        return response, raw, observed
