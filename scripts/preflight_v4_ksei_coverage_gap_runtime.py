"""Zero-network runtime preflight for V4 KSEI coverage-gap remediation."""

from __future__ import annotations

import json
from pathlib import Path

from idx_trade.v4_ksei_coverage_gap import ticker_identity_sha256


CONFIG = Path("config/v4_ksei_coverage_gap_remediation_v1.json")
EXPECTED_GAP_SHA = "1cd050985841519d24f58a38d10014693ff4a843cbd438586237ad4419ffe812"


def main() -> int:
    if not CONFIG.is_file():
        raise RuntimeError(f"CONFIG_MISSING:{CONFIG}")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    tickers = config.get("gap_tickers") or []
    if len(tickers) != 43 or len(set(tickers)) != 43:
        raise RuntimeError("FROZEN_GAP_TICKER_COUNT_CHANGED")
    if ticker_identity_sha256(tickers) != EXPECTED_GAP_SHA:
        raise RuntimeError("FROZEN_GAP_TICKER_IDENTITY_CHANGED")
    provider = config.get("provider") or {}
    if provider.get("transport_library") != "curl_cffi":
        raise RuntimeError("TRANSPORT_LIBRARY_CHANGED")
    try:
        from curl_cffi import requests as curl_requests
    except ImportError as exc:
        raise RuntimeError("CURL_CFFI_REQUIRED_FOR_FROZEN_KSEI_TRANSPORT") from exc
    session = curl_requests.Session(impersonate=str(provider.get("impersonate")))
    close = getattr(session, "close", None)
    if callable(close):
        close()
    print(
        json.dumps(
            {
                "status": "V4_KSEI_COVERAGE_GAP_RUNTIME_PREFLIGHT_PASS",
                "network_calls": 0,
                "gap_tickers": len(tickers),
                "gap_ticker_identity_sha256": EXPECTED_GAP_SHA,
                "transport_library": "curl_cffi",
                "impersonate": provider.get("impersonate"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
