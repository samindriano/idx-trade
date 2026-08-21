from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

EXPECTED_DATE = "2026-08-19"
EXPECTED_CODE = "BBCA"
EXPECTED_TITLE_TERMS = ("dividen", "tunai", "interim")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif value is not None:
        yield str(value)


def _date10(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if len(text) >= 10:
        try:
            return date.fromisoformat(text[:10]).isoformat()
        except Exception:
            pass
    for fmt in ("%Y%m%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except Exception:
            pass
    return None


def _dates_in(value: Any) -> set[str]:
    result: set[str] = set()
    for text in _walk_strings(value):
        # ISO date prefix must match even when immediately followed by 'T'.
        for match in re.findall(r"20\d{2}-\d{2}-\d{2}", text):
            parsed = _date10(match)
            if parsed:
                result.add(parsed)
        for match in re.findall(r"\d{2}/\d{2}/20\d{2}", text):
            parsed = _date10(match)
            if parsed:
                result.add(parsed)
        for match in re.findall(r"20\d{6}", text):
            parsed = _date10(match)
            if parsed:
                result.add(parsed)
    return result


def _attachment_rows(item: dict[str, Any]) -> list[dict[str, Any]]:
    raw = item.get("attachments")
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        result.append(
            {
                "pdf_filename": row.get("PDFFilename"),
                "full_save_path": row.get("FullSavePath"),
                "original_filename": row.get("OriginalFilename"),
                "is_attachment": row.get("IsAttachment"),
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline inspection of the captured BBCA dividend announcement.")
    parser.add_argument("--probe-dir", required=True)
    args = parser.parse_args()

    root = Path(args.probe_dir).expanduser().resolve()
    raw_path = root / "announcements.json"
    if not raw_path.is_file():
        raise SystemExit(f"announcements raw missing: {raw_path}")

    raw = raw_path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    replies = payload.get("Replies") if isinstance(payload, dict) else None
    if not isinstance(replies, list):
        raise SystemExit("ANNOUNCEMENT_REPLIES_NOT_LIST")

    candidates: list[dict[str, Any]] = []
    for item in replies:
        if not isinstance(item, dict):
            continue
        announcement = item.get("pengumuman") if isinstance(item.get("pengumuman"), dict) else {}
        code = str(announcement.get("Kode_Emiten") or "").strip().upper()
        title = str(announcement.get("JudulPengumuman") or announcement.get("PerihalPengumuman") or "").strip()
        text = " ".join(_walk_strings(item)).lower()
        dates = sorted(_dates_in(item))
        title_lower = title.lower()
        relevant = (
            code == EXPECTED_CODE
            and EXPECTED_DATE in dates
            and all(term in title_lower or term in text for term in EXPECTED_TITLE_TERMS)
        )
        if not relevant:
            continue
        candidates.append(
            {
                "id": announcement.get("Id2"),
                "number": announcement.get("NoPengumuman"),
                "announcement_date": _date10(announcement.get("TglPengumuman")),
                "created_date": announcement.get("CreatedDate"),
                "title": title,
                "company_code": code,
                "form_id": announcement.get("Form_Id"),
                "dates_observed": dates,
                "attachments": _attachment_rows(item),
            }
        )

    report = {
        "schema_version": "idx_trade_forward_ca_dividend_announcement_offline_inspection_v1",
        "source_raw_sha256": _sha256(raw_path),
        "announcement_row_count": len(replies),
        "matching_candidate_count": len(candidates),
        "matching_candidates": candidates,
        "announcement_match": len(candidates) == 1,
        "status": (
            "PASS_ANNOUNCEMENT_IDENTIFIED_ATTACHMENT_INSPECTION_READY"
            if len(candidates) == 1
            else "FAIL_ANNOUNCEMENT_NOT_UNIQUE"
        ),
    }
    out = root / "ANNOUNCEMENT_OFFLINE_INSPECTION.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"report={out}")
    return 0 if len(candidates) == 1 else 2


if __name__ == "__main__":
    raise SystemExit(main())
