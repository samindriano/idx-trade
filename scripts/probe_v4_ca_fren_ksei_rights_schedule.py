from __future__ import annotations

import argparse
import hashlib
import html
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from pypdf import PdfReader
import requests


KSEI_RIGHTS_APRIL_2024_URL = (
    "https://web.ksei.co.id/publications/corporate-action-schedules/"
    "rights-distribution?Month=04&Year=2024"
)
MAX_PDF_FETCHES = 3
TIMEOUT = (5, 15)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _norm(value: str) -> str:
    value = html.unescape(value).replace("\u00a0", " ")
    return " ".join(value.split()).casefold()


def extract_fren_pdf_links(payload: bytes, base_url: str = KSEI_RIGHTS_APRIL_2024_URL) -> tuple[str, ...]:
    raw = payload.decode("utf-8", errors="ignore")
    rows = re.findall(r"<tr\b[^>]*>.*?</tr>", raw, flags=re.I | re.S)
    matches = [row for row in rows if "fren" in row.casefold() or "smartfren telecom" in row.casefold()]
    urls: set[str] = set()
    for row in matches:
        for href in re.findall(r'''href\s*=\s*["']([^"']+)["']''', row, flags=re.I):
            url = urljoin(base_url, html.unescape(href))
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                continue
            if not parsed.netloc.casefold().endswith("ksei.co.id"):
                continue
            if "/announcement/files/" not in parsed.path.casefold() or not parsed.path.casefold().endswith(".pdf"):
                continue
            urls.add(url)
    return tuple(sorted(urls))


def pdf_text(payload: bytes) -> str:
    if not payload.startswith(b"%PDF"):
        raise RuntimeError("FREN_KSEI_SCHEDULE_NOT_PDF_BYTES")
    reader = PdfReader(BytesIO(payload))
    return " ".join((page.extract_text() or "") for page in reader.pages)


def verify_ksei_fren_schedule_text(text: str) -> dict[str, Any]:
    norm = _norm(text)
    required = [
        "smartfren telecom",
        "fren",
        "hmetd",
        "17 april 2024",
        "16 april 2024",
        "18 april 2024",
        "19 april 2024",
        "22 april 2024",
        "178",
        "75",
    ]
    missing = [token for token in required if token not in norm]
    if missing:
        raise RuntimeError(f"FREN_KSEI_SCHEDULE_CORE_MARKER_MISSING:{missing}")

    ex_label_ok = any(
        token in norm
        for token in (
            "tanggal ex di pasar regular dan pasar negosiasi",
            "tanggal ex di pasar reguler dan pasar negosiasi",
            "ex hmetd di pasar regular dan pasar negosiasi",
            "ex hmetd di pasar reguler dan pasar negosiasi",
        )
    )
    if not ex_label_ok:
        raise RuntimeError("FREN_KSEI_EX_RIGHT_LABEL_MISSING")

    cum_label_ok = any(
        token in norm
        for token in (
            "tanggal cum di pasar regular dan pasar negosiasi",
            "tanggal cum di pasar reguler dan pasar negosiasi",
            "cum hmetd di pasar regular dan pasar negosiasi",
            "cum hmetd di pasar reguler dan pasar negosiasi",
        )
    )
    if not cum_label_ok:
        raise RuntimeError("FREN_KSEI_CUM_RIGHT_LABEL_MISSING")

    if "tanggal pencatatan" not in norm and "recording date" not in norm:
        raise RuntimeError("FREN_KSEI_RECORD_DATE_LABEL_MISSING")
    if "tanggal distribusi" not in norm and "distribution" not in norm:
        raise RuntimeError("FREN_KSEI_DISTRIBUTION_LABEL_MISSING")
    if not re.search(r"178.{0,250}75.{0,120}hmetd", norm):
        raise RuntimeError("FREN_KSEI_RIGHT_RATIO_CONTEXT_MISSING")
    if "6 mei 2024" not in norm and "6 may 2024" not in norm:
        raise RuntimeError("FREN_KSEI_RIGHT_TRADING_END_MISSING")

    ref_match = re.search(r"ksei-\d+/[a-z]+/\d{4}", norm, flags=re.I)
    return {
        "transition_date": "2024-04-17",
        "transition_semantic": "OFFICIAL_KSEI_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE",
        "cum_regular_negotiated": "2024-04-16",
        "record_date": "2024-04-18",
        "distribution_date": "2024-04-19",
        "trading_start": "2024-04-22",
        "trading_end": "2024-05-06",
        "ratio": "178_OLD_TO_75_HMETD",
        "reference_no": ref_match.group(0).upper() if ref_match else None,
    }


def _get(url: str) -> tuple[bytes, dict[str, Any]]:
    headers = {"User-Agent": "idx-trade-v4-ca-fren-ksei-schedule-probe/1.0"}
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as exc:
        raise RuntimeError(f"FREN_KSEI_FETCH_ERROR:{type(exc).__name__}:{exc}") from exc
    payload = response.content
    record = {
        "url": url,
        "final_url": response.url,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
    }
    if response.status_code != 200:
        raise RuntimeError(f"FREN_KSEI_FETCH_NON_200:{record}")
    return payload, record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    index_payload, index_record = _get(KSEI_RIGHTS_APRIL_2024_URL)
    (args.raw_dir / "ksei_rights_april_2024.html").write_bytes(index_payload)
    links = extract_fren_pdf_links(index_payload)

    result: dict[str, Any] = {
        "schema_version": "fren_ksei_official_rights_schedule_probe_v1",
        "index": index_record,
        "fren_pdf_links": list(links),
        "bounded_pdf_fetch_limit": MAX_PDF_FETCHES,
        "attempts": [],
        "verified": False,
    }

    if not links:
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        raise RuntimeError("FREN_KSEI_APRIL_2024_SCHEDULE_ROW_OR_PDF_MISSING")

    for index, url in enumerate(links[:MAX_PDF_FETCHES], start=1):
        attempt: dict[str, Any] = {"url": url}
        try:
            payload, record = _get(url)
            raw_path = args.raw_dir / f"fren_ksei_schedule_{index:02d}.pdf"
            raw_path.write_bytes(payload)
            semantics = verify_ksei_fren_schedule_text(pdf_text(payload))
            attempt.update(record)
            attempt["raw_path"] = str(raw_path)
            attempt["semantics"] = semantics
            result["attempts"].append(attempt)
            result["verified"] = True
            result["verified_pdf"] = attempt
            break
        except Exception as exc:
            attempt["error"] = f"{type(exc).__name__}:{exc}"
            result["attempts"].append(attempt)

    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["verified"]:
        raise RuntimeError("FREN_KSEI_OFFICIAL_RIGHTS_SCHEDULE_NOT_VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
