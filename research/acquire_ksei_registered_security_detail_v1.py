"""Acquire ordinary public KSEI registered-security detail pages.

This is a source-preservation utility for the population-wide identity lane.
It does not authenticate, retry, bypass controls, infer identity, or write any
repository/canonical artifact.  Every code is attempted once and every result
(including HTTP errors and empty/invalid pages) is retained with retrieval time
and SHA-256 provenance under the explicitly supplied isolated staging root.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests


CODE_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}$")
KSEI_BASE = "https://web.ksei.co.id/services/registered-securities/shares/lc"
USER_AGENT = "Mozilla/5.0 (IDX-Trade population identity research; ordinary public request)"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize_code(value: Any) -> str | None:
    code = str(value or "").strip().upper()
    return code if CODE_RE.fullmatch(code) else None


class ShareTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.rows: list[list[str]] = []
        self.current: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table" and not self.in_table:
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_row = True
            self.current = []
        elif self.in_row and tag in {"td", "th"}:
            self.in_cell = True
            self.text = []

    def handle_endtag(self, tag: str) -> None:
        if self.in_row and tag in {"td", "th"} and self.in_cell:
            self.current.append(" ".join("".join(self.text).split()))
            self.in_cell = False
        elif self.in_table and tag == "tr" and self.in_row:
            if self.current:
                self.rows.append(self.current)
            self.in_row = False
        elif tag == "table" and self.in_table:
            self.in_table = False

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.text.append(data)


def load_share_codes(path: Path) -> list[dict[str, str]]:
    parser = ShareTableParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    rows: list[dict[str, str]] = []
    for row in parser.rows[1:]:
        if len(row) < 5:
            continue
        code = normalize_code(row[1])
        if code:
            rows.append(
                {
                    "code": code,
                    "description": row[2],
                    "registrar": row[3],
                    "nominal": row[4],
                }
            )
    deduped: dict[str, dict[str, str]] = {row["code"]: row for row in rows}
    return [deduped[code] for code in sorted(deduped)]


def fetch_one(code: str, output_dir: Path, timeout: float) -> dict[str, Any]:
    url = f"{KSEI_BASE}/{code}?setLocale=en-US"
    started = datetime.now(timezone.utc).isoformat()
    raw_path = output_dir / f"{code}.html"
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        payload = response.content
        raw_path.write_bytes(payload)
        return {
            "code": code,
            "url": url,
            "retrieved_at_utc": started,
            "http_status": response.status_code,
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
            "raw_path": str(raw_path),
            "error": None,
        }
    except Exception as exc:  # preserve ordinary transport failures as evidence
        return {
            "code": code,
            "url": url,
            "retrieved_at_utc": started,
            "http_status": None,
            "bytes": 0,
            "sha256": None,
            "raw_path": str(raw_path),
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shares-html", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--delay", type=float, default=0.0)
    args = parser.parse_args()

    staging_root = args.staging_root.resolve()
    if "idx-population-identity-lifecycle-staging-20260920" not in str(staging_root):
        raise ValueError("refusing output outside the isolated population-identity staging root")
    if args.workers < 1 or args.workers > 8:
        raise ValueError("workers must be between 1 and 8")
    output_dir = staging_root / "ksei-registered-security-detail" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir.parent / "acquisition_metadata.jsonl"
    table_path = output_dir.parent / "ksei_share_table_population.json"

    codes = load_share_codes(args.shares_html)
    table_path.write_text(
        json.dumps(
            {
                "source_path": str(args.shares_html.resolve()),
                "source_sha256": sha256_bytes(args.shares_html.read_bytes()),
                "retrieved_from_prior_probe": True,
                "codes": codes,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for row in codes:
            if args.delay:
                time.sleep(args.delay)
            futures[executor.submit(fetch_one, row["code"], output_dir, args.timeout)] = row["code"]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda row: row["code"])
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        for row in results:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": "PASS_KSEI_DETAIL_ATTEMPT_RETAINED",
                "codes_attempted": len(codes),
                "http_200": sum(row["http_status"] == 200 for row in results),
                "http_non_200": sum(row["http_status"] not in {200, None} for row in results),
                "transport_errors": sum(row["error"] is not None for row in results),
                "metadata": str(metadata_path),
                "table": str(table_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
