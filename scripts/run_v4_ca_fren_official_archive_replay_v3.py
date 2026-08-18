"""Attachment-discovery hardened entrypoint for FREN official-archive replay.

Builds on V2 without changing the scientific acceptance rule.  It only hardens
issuer-asset discovery for legacy Smartfren pages that expose download targets
through escaped JSON/attributes and for locale-prefixed ``/en/app/uploads``
paths that resolve to HTML shells instead of the canonical ``/app/uploads``
asset path.

The accepted rights boundary still requires an issuer-official PDF whose text
explicitly proves 2024-04-17 as the Regular/Negotiated Market ex-right date,
with the frozen 178:75 PMHMETD V identity and final April/May 2024 schedule.
"""

from __future__ import annotations

from collections import deque
import html
from pathlib import Path
import re
import sys
from urllib.parse import urljoin, urlparse

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_v4_ca_fren_official_archive_replay as v1
import run_v4_ca_fren_official_archive_replay_v2 as v2


_MAX_CANDIDATE_FETCHES = 60
_MAX_DETAIL_FETCHES = 16


def _decoded_html(payload: bytes) -> str:
    raw = payload.decode("utf-8", errors="ignore")
    raw = html.unescape(raw)
    # WordPress/JS payloads often JSON-escape slash characters.
    raw = raw.replace("\\/", "/")
    raw = raw.replace("\\u002F", "/").replace("\\u002f", "/")
    raw = raw.replace("\\u003A", ":").replace("\\u003a", ":")
    return raw


def _looks_like_locator(value: str) -> bool:
    """Reject JSON/property keys while retaining actual URL/path-like values."""

    candidate = html.unescape(str(value or "")).strip().strip('"\'')
    if not candidate or any(char.isspace() for char in candidate):
        return False
    low = candidate.casefold()
    if low.startswith(("http://", "https://", "//", "/", "./", "../")):
        return True
    # Relative attachment values commonly contain path separators or a filename
    # extension. A bare key such as ``attachment`` must never become
    # ``https://www.smartfren.com/attachment`` via urljoin.
    if "/" in candidate or "\\" in candidate:
        return True
    return bool(re.search(r"\.[a-z0-9]{2,8}(?:[?#].*)?$", candidate, flags=re.I))


def _canonical_asset_variants(url: str, base_url: str) -> tuple[str, ...]:
    value = html.unescape(str(url or "")).strip().strip('"\'')
    if not value or not _looks_like_locator(value):
        return tuple()
    value = value.replace("\\/", "/")
    value = value.replace("\\u002F", "/").replace("\\u002f", "/")
    value = urljoin(base_url, value)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return tuple()
    if not parsed.netloc.lower().endswith("smartfren.com"):
        return tuple()

    variants = {value}
    for locale in ("/en/app/uploads/", "/id/app/uploads/"):
        if locale in parsed.path:
            variants.add(value.replace(locale, "/app/uploads/", 1))
    # Legacy URLs are sometimes emitted with a trailing slash after .pdf.
    variants |= {item[:-1] for item in list(variants) if item.lower().endswith(".pdf/")}
    return tuple(sorted(variants))


def extract_hidden_asset_candidates(payload: bytes, base_url: str) -> tuple[str, ...]:
    """Extract same-domain asset/download targets from HTML + escaped JSON."""

    raw = _decoded_html(payload)
    tokens: set[str] = set()

    # Absolute URLs anywhere in scripts/JSON/markup.
    for match in re.finditer(r"https?://[^\s\"'<>\\]+", raw, flags=re.I):
        tokens.add(match.group(0))

    # Quoted relative/absolute values likely to carry an attachment target.
    # Bare JSON/property keys such as ``attachment`` are deliberately rejected
    # before urljoin so they cannot become fake same-domain candidates.
    for match in re.finditer(r'''["']([^"']+)["']''', raw):
        value = match.group(1)
        low = value.casefold()
        if not _looks_like_locator(value):
            continue
        if any(
            marker in low
            for marker in (
                "app/uploads",
                "/uploads/",
                "download",
                "attachment",
                "pmhmetd",
                "prospektus",
                ".pdf",
            )
        ):
            tokens.add(value)

    # CSS url(...) and JS window/open style fragments.
    for match in re.finditer(r"url\(([^)]+)\)", raw, flags=re.I):
        value = match.group(1).strip().strip('"\'')
        if _looks_like_locator(value):
            tokens.add(value)

    output: set[str] = set()
    for token in tokens:
        for candidate in _canonical_asset_variants(token, base_url):
            low = candidate.casefold()
            if any(
                marker in low
                for marker in (
                    "app/uploads",
                    "/uploads/",
                    "download",
                    "attachment",
                    "pmhmetd",
                    "prospektus",
                    ".pdf",
                )
            ):
                output.add(candidate)
    return tuple(sorted(output))


def _priority(url: str) -> tuple[int, int, str]:
    low = url.casefold()
    if "pmhmetd" in low or "prospektus" in low:
        family = 0
    elif "/app/uploads/" in low:
        family = 1
    elif "annual" in low or "ar-2024" in low or "smartfren-ar" in low:
        family = 2
    else:
        family = 3
    pdf_rank = 0 if ".pdf" in low else 1
    return family, pdf_rank, url


def discover_and_verify_rights_pdf_v3(
    page_payloads: list[tuple[str, bytes]],
    raw_root: Path,
):
    """Bounded issuer-only attachment traversal with exact PDF verification."""

    candidates: set[str] = set()
    detail_urls: set[str] = set()
    forensic_counts: dict[str, int] = {}

    # The pre-existing annual-report candidate is retained, but fix any locale
    # prefix before probing.  It can only pass if its PDF text independently
    # satisfies the same strict PMHMETD-V schedule verifier.
    for candidate in _canonical_asset_variants(
        v1.SMARTFREN_2024_ANNUAL_REPORT_PDF,
        v1.SMARTFREN_ANNUAL_REPORT_URL,
    ):
        candidates.add(candidate)

    for base_url, payload in page_payloads:
        direct = set(v1.extract_official_pdf_urls(payload, base_url))
        hidden = set(extract_hidden_asset_candidates(payload, base_url))
        forensic_counts[base_url] = len(direct | hidden)
        for item in direct | hidden:
            candidates.update(_canonical_asset_variants(item, base_url))
        for link in v1.hrefs(payload, base_url):
            low = link.casefold()
            if "pmhmetd" in low or "prospektus" in low:
                detail_urls.add(link)

    # Known issuer detail page is within the already frozen discovery surface.
    detail_urls.add(v1.SMARTFREN_PROSPECTUS_PAGE_URL)

    detail_records: list[dict[str, object]] = []
    for index, url in enumerate(sorted(detail_urls)[:_MAX_DETAIL_FETCHES], start=1):
        try:
            payload, record = v1.get(url, raw_root / f"detail_v3_{index:02d}.html")
        except RuntimeError as exc:
            detail_records.append({"url": url, "error": str(exc)})
            continue
        nested = set(v1.extract_official_pdf_urls(payload, url))
        nested |= set(extract_hidden_asset_candidates(payload, url))
        detail_records.append({**record, "discovered_asset_count": len(nested)})
        for item in nested:
            candidates.update(_canonical_asset_variants(item, url))

    attempts: list[dict[str, object]] = []
    queue = deque(sorted(candidates, key=_priority))
    seen: set[str] = set()
    fetch_index = 0

    while queue and fetch_index < _MAX_CANDIDATE_FETCHES:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        fetch_index += 1
        try:
            payload, record = v1.get(url, raw_root / f"candidate_v3_{fetch_index:02d}.bin")
        except RuntimeError as exc:
            attempts.append({"url": url, "error": str(exc)})
            continue

        if payload.startswith(b"%PDF"):
            try:
                semantics = v1.verify_rights_prospectus(payload)
            except Exception as exc:
                attempts.append({**record, "error": f"{type(exc).__name__}:{exc}"})
                continue
            return payload, record, {
                **semantics,
                "discovery_version": "V3_ESCAPED_ATTACHMENT_AND_CANONICAL_UPLOAD_PATH",
                "candidate_attempts": attempts,
                "detail_pages": detail_records,
                "initial_page_asset_counts": forensic_counts,
            }

        # An attachment-like URL can itself return an HTML wrapper.  Traverse
        # only issuer-owned nested asset targets; never infer semantics from it.
        nested = extract_hidden_asset_candidates(payload, url)
        attempts.append(
            {
                **record,
                "error": "NOT_PDF_BYTES",
                "nested_asset_count": len(nested),
            }
        )
        for item in nested:
            for candidate in _canonical_asset_variants(item, url):
                if candidate not in seen:
                    queue.append(candidate)

    raise RuntimeError(
        "FREN_NO_ISSUER_PDF_PROVES_EX_RIGHT_DATE_V3:"
        + repr(
            {
                "candidate_count": len(candidates),
                "seen_count": len(seen),
                "attempts": attempts,
                "detail_pages": detail_records,
                "initial_page_asset_counts": forensic_counts,
            }
        )
    )


def main() -> int:
    # V2 installs its KSEI optional-corroboration transport before entering V1.
    # Our function is invoked inside V1.main after that monkeypatch is active.
    v1.discover_and_verify_rights_pdf = discover_and_verify_rights_pdf_v3
    return int(v2.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
