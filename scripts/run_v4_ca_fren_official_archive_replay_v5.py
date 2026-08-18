"""Fast bounded issuer-CMS diagnostic entrypoint for FREN archive replay.

This version exists to prevent long silent runs caused by dozens of 45-second
candidate probes. Scientific acceptance is unchanged: a qualifying issuer PDF
must still pass the frozen PMHMETD-V verifier. If bounded CMS discovery does not
find such a PDF quickly, V5 fails closed with diagnostics instead of falling
back to the broad V3 traversal.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import quote

import requests

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_v4_ca_fren_official_archive_replay as v1
import run_v4_ca_fren_official_archive_replay_v2 as v2
import run_v4_ca_fren_official_archive_replay_v3 as v3
import run_v4_ca_fren_official_archive_replay_v4 as v4


CMS_TIMEOUT = (5, 12)
PDF_TIMEOUT = (5, 25)
MAX_PDF_CANDIDATES = 12


def _fast_get(url: str, path: Path, *, pdf: bool = False) -> tuple[bytes, dict[str, Any]]:
    timeout = PDF_TIMEOUT if pdf else CMS_TIMEOUT
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 IDX-Trade-V4-FREN-CMS-Fast/1.0",
                "Accept": "application/json,text/html,application/pdf,*/*;q=0.8",
            },
            timeout=timeout,
            allow_redirects=True,
        )
        payload = bytes(response.content or b"")
    except requests.RequestException as exc:
        raise RuntimeError(f"FREN_FAST_PROBE_TRANSPORT:{type(exc).__name__}:{url}") from exc

    record = {
        "url": url,
        "final_url": str(response.url),
        "status_code": int(response.status_code),
        "bytes": len(payload),
        "timeout": list(timeout),
    }
    if response.status_code != 200 or not payload:
        raise RuntimeError(f"FREN_FAST_PROBE_HTTP:{record}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    record["sha256"] = v1.sha256_file(path)
    return payload, record


def _focused_cms_endpoints() -> tuple[str, ...]:
    base = "https://www.smartfren.com/wp-json/wp/v2/media"
    queries = (
        "PMHMETD",
        "Prospektus PMHMETD",
        "FREN PMHMETD",
        "Prospektus Ringkas FREN",
    )
    return tuple(
        f"{base}?search={quote(query, safe='')}&per_page=100"
        for query in queries
    )


def _candidate_relevance(url: str) -> tuple[int, str]:
    low = url.casefold()
    score = 0
    if "pmhmetd" in low:
        score -= 100
    if "prospektus" in low:
        score -= 80
    if "fren" in low:
        score -= 40
    if ".pdf" in low:
        score -= 20
    if "/app/uploads/2024/" in low:
        score -= 10
    return score, url


def discover_and_verify_rights_pdf_v5(page_payloads, raw_root: Path):
    del page_payloads  # mandatory archive pages are still verified by V1 before this hook.

    endpoint_records: list[dict[str, Any]] = []
    candidates: set[str] = set()
    endpoints = _focused_cms_endpoints()

    for index, url in enumerate(endpoints, start=1):
        print(f"[FREN V5] CMS {index}/{len(endpoints)} {url}", flush=True)
        try:
            payload, record = _fast_get(url, raw_root / f"cms_fast_{index:02d}.json")
        except RuntimeError as exc:
            endpoint_records.append({"url": url, "error": str(exc)})
            continue
        discovered = set(v4.extract_cms_asset_candidates(payload, url))
        focused = {
            candidate
            for candidate in discovered
            if any(token in candidate.casefold() for token in ("pmhmetd", "prospektus", "fren"))
        }
        endpoint_records.append(
            {
                **record,
                "discovered_asset_count": len(discovered),
                "focused_asset_count": len(focused),
            }
        )
        candidates.update(focused)

    ordered = sorted(candidates, key=_candidate_relevance)[:MAX_PDF_CANDIDATES]
    print(f"[FREN V5] focused candidates={len(candidates)} probing={len(ordered)}", flush=True)
    attempts: list[dict[str, Any]] = []

    for index, url in enumerate(ordered, start=1):
        print(f"[FREN V5] candidate {index}/{len(ordered)} {url}", flush=True)
        try:
            payload, record = _fast_get(
                url,
                raw_root / f"candidate_fast_{index:02d}.bin",
                pdf=True,
            )
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
            "discovery_version": "V5_FAST_BOUNDED_ISSUER_CMS",
            "cms_endpoints": endpoint_records,
            "candidate_attempts": attempts,
            "cms_candidate_count": len(candidates),
        }

    raise RuntimeError(
        "FREN_FAST_CMS_NO_QUALIFYING_PDF:"
        + json.dumps(
            {
                "cms_candidate_count": len(candidates),
                "cms_endpoints": endpoint_records,
                "candidate_attempts": attempts,
                "fallback_disabled": True,
                "reason": "FAIL_CLOSED_AVOID_LONG_BROAD_ASSET_TRAVERSAL",
            },
            sort_keys=True,
        )
    )


def main() -> int:
    v1.discover_and_verify_rights_pdf = discover_and_verify_rights_pdf_v5
    return int(v2.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
