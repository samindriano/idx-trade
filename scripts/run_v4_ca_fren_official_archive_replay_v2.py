"""Transport-hardened entrypoint for the FREN official-archive replay.

Scientific contract is unchanged from V1:
- Smartfren issuer-official archive pages remain mandatory;
- an issuer-official PMHMETD V PDF must explicitly prove the 2024-04-17
  Regular/Negotiated Market ex-right date;
- the already-proven 2025-04-16 merger/security-cessation boundary remains
  mandatory;
- no record-date subtraction, price inference, or EXCL stitching is allowed.

Only KSEI historical-news transport is relaxed from mandatory HTTP-200 to
optional corroboration. The KSEI pages are currently intermittent and may
return HTTP 500 even though the same archived article is publicly indexed.
Non-200 KSEI bodies are never treated as evidence. The final attestation
records whether KSEI corroboration was COMPLETE, PARTIAL, or UNAVAILABLE.

For issuer sources the acceptance rule remains strict. Network exceptions are
only normalized to RuntimeError so bounded discovery callers can record a
failed candidate and continue, while mandatory issuer-page fetches still abort.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

import requests

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_v4_ca_fren_official_archive_replay as v1


_ORIGINAL_GET = v1.get
_ORIGINAL_VERIFY_RIGHT = v1.verify_ksei_right_pages
_ORIGINAL_VERIFY_MERGER = v1.verify_ksei_merger_pages
_ORIGINAL_VERIFY_ARCHIVE = v1.verify_smartfren_archive_pages
_ORIGINAL_COMBINED_SHA = v1.combined_evidence_sha

_KSEI_RESULTS: dict[str, dict[str, Any]] = {}
_KSEI_URLS = {
    v1.KSEI_RIGHT_RECORD_URL,
    v1.KSEI_RIGHT_DISTRIBUTION_URL,
    v1.KSEI_MERGER_RECORD_URL,
    v1.KSEI_MERGER_REPORT_URL,
    v1.KSEI_MERGER_DISTRIBUTION_URL,
}


def _is_ksei_news(url: str) -> bool:
    parsed = urlparse(str(url))
    return parsed.netloc.lower() == "web.ksei.co.id" and "/ksei_news/read/" in parsed.path


def _capture_ksei(url: str, path: Path) -> tuple[bytes, dict[str, Any]]:
    """Retry exact KSEI news URL without ever accepting non-200 bytes as evidence."""

    attempts: list[dict[str, Any]] = []
    candidates = (str(url), f"{url}?setLocale=id-ID")
    for attempt, candidate in enumerate(candidates, start=1):
        try:
            response = requests.get(
                candidate,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/151.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.7,en;q=0.6",
                },
                timeout=45,
                allow_redirects=True,
            )
            payload = bytes(response.content or b"")
            record = {
                "url": str(url),
                "requested_url": candidate,
                "final_url": str(response.url),
                "status_code": int(response.status_code),
                "bytes": len(payload),
                "attempt": attempt,
            }
            attempts.append(record)
            if response.status_code == 200 and payload:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
                record["sha256"] = v1.sha256_file(path)
                record["corroboration_status"] = "AVAILABLE"
                record["attempts"] = attempts
                _KSEI_RESULTS[str(url)] = dict(record)
                return payload, record
        except Exception as exc:  # transport-only evidence; never semantic fallback
            attempts.append(
                {
                    "url": str(url),
                    "requested_url": candidate,
                    "attempt": attempt,
                    "error": f"{type(exc).__name__}:{exc}",
                }
            )

    record = {
        "url": str(url),
        "status_code": int(attempts[-1].get("status_code", 0) or 0),
        "bytes": int(attempts[-1].get("bytes", 0) or 0),
        "corroboration_status": "UNAVAILABLE",
        "evidence_accepted": False,
        "attempts": attempts,
    }
    _KSEI_RESULTS[str(url)] = dict(record)
    # Empty bytes deliberately prevent downstream semantic verification and are
    # filtered out of the combined evidence hash below.
    return b"", record


def get_v2(url: str, path: Path):
    if _is_ksei_news(url):
        return _capture_ksei(url, path)
    # Issuer sources remain strict. Normalize requests transport exceptions so
    # optional discovery probes can record them and continue; mandatory issuer
    # calls still abort because their callers do not catch this RuntimeError.
    try:
        return _ORIGINAL_GET(url, path)
    except requests.RequestException as exc:
        raise RuntimeError(
            f"FREN_ISSUER_TRANSPORT_FAILED:{url}:{type(exc).__name__}:{exc}"
        ) from exc


def verify_ksei_right_pages_v2(record_html: bytes, distribution_html: bytes) -> None:
    if record_html and distribution_html:
        _ORIGINAL_VERIFY_RIGHT(record_html, distribution_html)


def verify_ksei_merger_pages_v2(
    record_html: bytes, report_html: bytes, distribution_html: bytes
) -> None:
    if record_html and report_html and distribution_html:
        _ORIGINAL_VERIFY_MERGER(record_html, report_html, distribution_html)


def _ksei_status() -> dict[str, Any]:
    available = sorted(
        url for url in _KSEI_URLS if (_KSEI_RESULTS.get(url) or {}).get("corroboration_status") == "AVAILABLE"
    )
    unavailable = sorted(url for url in _KSEI_URLS if url not in available)
    if len(available) == len(_KSEI_URLS):
        status = "COMPLETE"
    elif available:
        status = "PARTIAL"
    else:
        status = "UNAVAILABLE"
    return {
        "status": status,
        "available_count": len(available),
        "expected_count": len(_KSEI_URLS),
        "available_urls": available,
        "unavailable_urls": unavailable,
        "transport_records": {url: _KSEI_RESULTS.get(url, {}) for url in sorted(_KSEI_URLS)},
    }


def verify_smartfren_archive_pages_v2(*args, **kwargs):
    result = dict(_ORIGINAL_VERIFY_ARCHIVE(*args, **kwargs))
    ksei = _ksei_status()
    if ksei["status"] == "COMPLETE":
        method = "ISSUER_OFFICIAL_ARCHIVE_PLUS_KSEI_EVENT_CORROBORATION"
    elif ksei["status"] == "PARTIAL":
        method = "ISSUER_OFFICIAL_ARCHIVE_WITH_PARTIAL_KSEI_CORROBORATION"
    else:
        method = "ISSUER_OFFICIAL_ARCHIVE_MECHANICAL_CENSUS_KSEI_NEWS_UNAVAILABLE"
    result["mechanical_census_method"] = method
    result["ksei_news_corroboration"] = ksei
    return result


def combined_evidence_sha_v2(payloads):
    accepted = [payload for payload in payloads if payload]
    if not accepted:
        raise RuntimeError("FREN_NO_ACCEPTED_OFFICIAL_EVIDENCE_PAYLOADS")
    return _ORIGINAL_COMBINED_SHA(accepted)


def main() -> int:
    v1.get = get_v2
    v1.verify_ksei_right_pages = verify_ksei_right_pages_v2
    v1.verify_ksei_merger_pages = verify_ksei_merger_pages_v2
    v1.verify_smartfren_archive_pages = verify_smartfren_archive_pages_v2
    v1.combined_evidence_sha = combined_evidence_sha_v2
    return int(v1.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
