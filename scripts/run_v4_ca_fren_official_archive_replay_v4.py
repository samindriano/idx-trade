"""Issuer-CMS attachment discovery for the FREN official-archive replay.

Builds on V3/V2 without changing scientific acceptance. Before the broader
legacy-page traversal, query bounded Smartfren WordPress REST search/media
endpoints for PMHMETD-related attachments. Only same-domain issuer assets are
considered and every candidate must still pass the frozen PMHMETD-V PDF
verifier (178:75, explicit 2024-04-17 Regular/Negotiated Market ex-right,
record/distribution/trading schedule). REST/CMS discovery itself is optional;
mandatory issuer archive pages remain enforced by V1/V2.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import quote

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_v4_ca_fren_official_archive_replay as v1
import run_v4_ca_fren_official_archive_replay_v2 as v2
import run_v4_ca_fren_official_archive_replay_v3 as v3


CMS_QUERIES = (
    "PMHMETD V",
    "Prospektus PMHMETD V",
    "Prospektus Ringkas PMHMETD V FREN",
    "Informasi Tambahan PMHMETD V FREN",
    "Perubahan Jadwal PMHMETD V",
)


def _walk_json(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)
    elif isinstance(value, str):
        yield value


def extract_cms_asset_candidates(payload: bytes, base_url: str) -> tuple[str, ...]:
    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception:
        return tuple()

    output: set[str] = set()
    for value in _walk_json(data):
        low = value.casefold()
        if not any(marker in low for marker in (".pdf", "app/uploads", "attachment", "download", "pmhmetd", "prospektus")):
            continue
        for candidate in v3._canonical_asset_variants(value, base_url):
            parsed_low = candidate.casefold()
            if any(marker in parsed_low for marker in (".pdf", "app/uploads", "download", "attachment")):
                output.add(candidate)
    return tuple(sorted(output))


def _cms_endpoints() -> tuple[str, ...]:
    base = "https://www.smartfren.com/wp-json/wp/v2"
    endpoints: list[str] = []
    for query in CMS_QUERIES:
        encoded = quote(query, safe="")
        endpoints.append(f"{base}/media?search={encoded}&per_page=100")
        endpoints.append(f"{base}/search?search={encoded}&per_page=100")
    return tuple(endpoints)


def discover_and_verify_rights_pdf_v4(page_payloads, raw_root: Path):
    endpoint_records: list[dict[str, Any]] = []
    candidates: set[str] = set()

    for index, url in enumerate(_cms_endpoints(), start=1):
        try:
            payload, record = v1.get(url, raw_root / f"cms_{index:02d}.json")
        except RuntimeError as exc:
            endpoint_records.append({"url": url, "error": str(exc)})
            continue
        discovered = extract_cms_asset_candidates(payload, url)
        endpoint_records.append({**record, "discovered_asset_count": len(discovered)})
        candidates.update(discovered)

    attempts: list[dict[str, Any]] = []
    for index, url in enumerate(sorted(candidates, key=v3._priority)[:40], start=1):
        try:
            payload, record = v1.get(url, raw_root / f"cms_candidate_{index:02d}.bin")
        except RuntimeError as exc:
            attempts.append({"url": url, "error": str(exc)})
            continue
        if not payload.startswith(b"%PDF"):
            attempts.append({**record, "error": "NOT_PDF_BYTES"})
            continue
        try:
            semantics = v1.verify_rights_prospectus(payload)
        except Exception as exc:
            attempts.append({**record, "error": f"{type(exc).__name__}:{exc}"})
            continue
        return payload, record, {
            **semantics,
            "discovery_version": "V4_ISSUER_WORDPRESS_CMS_MEDIA_SEARCH",
            "cms_endpoints": endpoint_records,
            "candidate_attempts": attempts,
            "cms_candidate_count": len(candidates),
        }

    # Preserve the exact V3 acceptance rule and bounded legacy traversal if CMS
    # metadata is unavailable or contains no qualifying attachment.
    try:
        return v3.discover_and_verify_rights_pdf_v3(page_payloads, raw_root / "v3_fallback")
    except RuntimeError as exc:
        raise RuntimeError(
            "FREN_NO_ISSUER_PDF_PROVES_EX_RIGHT_DATE_V4:"
            + repr(
                {
                    "cms_candidate_count": len(candidates),
                    "cms_endpoints": endpoint_records,
                    "cms_attempts": attempts,
                    "v3_fallback_error": str(exc),
                }
            )
        ) from exc


def main() -> int:
    v1.discover_and_verify_rights_pdf = discover_and_verify_rights_pdf_v4
    return int(v2.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
