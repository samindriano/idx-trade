"""Read-only audit of the locally staged official IDX-IC sector archive."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
TICKER_RE = re.compile(r"^[A-Z0-9]{4,5}$")
DATE_RE = re.compile(r"tanggal\s+([0-9]{1,2}\s+[A-Za-zÀ-ÿ-]+\s+[0-9]{4})", re.I)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def shared_strings(book: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in book.namelist():
        return []
    root = ET.fromstring(book.read("xl/sharedStrings.xml"))
    return [
        clean("".join(text.text or "" for text in item.iter(f"{{{NS['m']}}}t")))
        for item in root.findall("m:si", NS)
    ]


def cell_value(cell: ET.Element, strings: list[str]) -> str:
    value = cell.find(f"{{{NS['m']}}}v")
    if value is None or value.text is None:
        return ""
    raw = value.text
    if cell.attrib.get("t") == "s":
        index = int(raw)
        return strings[index] if 0 <= index < len(strings) else ""
    return clean(raw)


def sheet_rows(book: zipfile.ZipFile, target: str, strings: list[str]) -> list[dict[str, str]]:
    root = ET.fromstring(book.read(target))
    rows: list[dict[str, str]] = []
    for row in root.findall(".//m:sheetData/m:row", NS):
        values: dict[str, str] = {}
        for cell in row.findall("m:c", NS):
            ref = cell.attrib.get("r", "")
            column = re.match(r"[A-Z]+", ref)
            if column:
                values[column.group(0)] = cell_value(cell, strings)
        if any(values.values()):
            rows.append(values)
    return rows


def workbook_sheets(data: bytes) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        strings = shared_strings(book)
        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        relationships = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        relation_map = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        for sheet in workbook.find("m:sheets", NS):
            relation_id = sheet.attrib[f"{{{NS['r']}}}id"]
            target = relation_map[relation_id]
            target = posixpath.normpath(posixpath.join("xl", target))
            rows = sheet_rows(book, target, strings)
            flattened = [clean(value) for row in rows for value in row.values() if clean(value)]
            announcement = next((match.group(1) for value in flattened if (match := DATE_RE.search(value))), None)
            effective_values = [
                " ".join(clean(value) for value in row.values() if clean(value))
                for row in rows
                if any("Periode Efektif Konsituen" in clean(value) for value in row.values())
            ]

            header_index = None
            code_column = None
            for index, row in enumerate(rows):
                for column, value in row.items():
                    if clean(value) == "Kode":
                        header_index = index
                        code_column = column
                        break
                if header_index is not None:
                    break

            constituent_rows: list[str] = []
            exit_rows: list[str] = []
            if header_index is not None and code_column is not None:
                exit_marker_index = next(
                    (
                        index
                        for index, row in enumerate(rows[header_index + 1 :], start=header_index + 1)
                        if "konstituen yang keluar" in " ".join(clean(value) for value in row.values()).lower()
                    ),
                    None,
                )
                current_end = exit_marker_index if exit_marker_index is not None else len(rows)
                for row in rows[header_index + 1 : current_end]:
                    joined = " ".join(clean(value) for value in row.values())
                    ticker = clean(row.get(code_column, ""))
                    if TICKER_RE.fullmatch(ticker):
                        constituent_rows.append(ticker)
                if exit_marker_index is not None:
                    exit_header_index = next(
                        (
                            index
                            for index, row in enumerate(rows[exit_marker_index + 1 :], start=exit_marker_index + 1)
                            if any(clean(value) == "Kode" for value in row.values())
                        ),
                        None,
                    )
                    if exit_header_index is not None:
                        exit_code_column = next(
                            column
                            for column, value in rows[exit_header_index].items()
                            if clean(value) == "Kode"
                        )
                        for row in rows[exit_header_index + 1 :]:
                            ticker = clean(row.get(exit_code_column, ""))
                            if TICKER_RE.fullmatch(ticker):
                                exit_rows.append(ticker)

            counts: dict[str, int] = {}
            for ticker in constituent_rows:
                counts[ticker] = counts.get(ticker, 0) + 1
            result.append(
                {
                    "sheet": sheet.attrib.get("name", ""),
                    "nonempty_rows": len(rows),
                    "announcement_date_text": announcement,
                    "effective_period_text": effective_values,
                    "header_found": header_index is not None,
                    "constituent_rows": len(constituent_rows),
                    "unique_tickers": len(counts),
                    "duplicate_tickers": sorted(ticker for ticker, count in counts.items() if count > 1),
                    "ticker_values": sorted(counts),
                    "ticker_samples": sorted(counts)[:5],
                    "exit_rows": len(exit_rows),
                    "exit_ticker_values": sorted(set(exit_rows)),
                    "exit_ticker_samples": sorted(set(exit_rows))[:5],
                }
            )
    return result


def audit_archive(root: Path, output: Path) -> dict[str, object]:
    frozen_names = [
        "IDX_IC_2021_Peng-00171.zip",
        "IDX_IC_2022_Peng-00150.zip",
        "IDX_IC_2023_Peng-00156.zip",
        "IDX_IC_2024_Peng-00128-ID.zip",
        "IDX_IC_2025_Peng-00110-ID.zip",
        "IDX_IC_2026_Peng-00100-ID.zip",
        "IDX_IC_BASELINE_2021_idx-industrial-classification.zip",
    ]
    archives: list[dict[str, object]] = []
    sheets: list[dict[str, object]] = []
    for name in frozen_names:
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(path)
        with zipfile.ZipFile(path) as archive:
            members = archive.namelist()
            xlsx_members = [member for member in members if member.lower().endswith(".xlsx")]
            pdf_members = [member for member in members if member.lower().endswith(".pdf")]
            for member in xlsx_members:
                if "sektor" in member.lower():
                    for item in workbook_sheets(archive.read(member)):
                        item.update({"archive": name, "member": member})
                        sheets.append(item)
            archives.append(
                {
                    "name": name,
                    "sha256": sha256(path),
                    "member_count": len(members),
                    "xlsx_members": xlsx_members,
                    "pdf_members": pdf_members,
                    "structured_sector_workbook_members": [
                        member for member in xlsx_members if "sektor" in member.lower()
                    ],
                }
            )

    structured_rows = sum(int(item["constituent_rows"]) for item in sheets)
    structured_exit_rows = sum(int(item["exit_rows"]) for item in sheets)
    structured_tickers = sorted(
        {
            ticker
            for item in sheets
            for ticker in item.get("ticker_values", [])
        }
    )
    all_duplicate_sheets = [item for item in sheets if item["duplicate_tickers"]]
    all_header_failures = [item for item in sheets if not item["header_found"]]
    all_effective_missing = [item for item in sheets if not item["effective_period_text"]]
    all_announcement_missing = [item for item in sheets if not item["announcement_date_text"]]
    by_archive_ticker: dict[tuple[str, str], list[str]] = {}
    for item in sheets:
        for ticker in item.get("ticker_values", []):
            by_archive_ticker.setdefault((str(item["archive"]), ticker), []).append(str(item["sheet"]))
    cross_sheet_duplicates = {
        f"{archive}:{ticker}": sheet_names
        for (archive, ticker), sheet_names in by_archive_ticker.items()
        if len(sheet_names) > 1
    }

    artifact: dict[str, object] = {
        "hypothesis_id": "SECTOR-01",
        "stage": "OFFICIAL_IDX_IC_SECTOR_ARCHIVE_SOURCE_AUDIT",
        "code_sha256": sha256(Path(__file__).resolve()),
        "candidate_id_created": False,
        "outcome_accessed": False,
        "provider_accessed": False,
        "scope": {
            "cloud_accessed": False,
            "incumbent_predictive_accessed": False,
            "outcome_accessed": False,
            "provider_accessed": False,
        },
        "source": {
            "archive_count": len(archives),
            "archives_with_structured_sector_workbook": sum(
                bool(item["structured_sector_workbook_members"]) for item in archives
            ),
            "structured_sector_workbooks": len(
                {
                    (item["archive"], item["member"])
                    for item in sheets
                }
            ),
            "structured_sector_sheets": len(sheets),
            "structured_constituent_rows": structured_rows,
            "structured_exit_rows": structured_exit_rows,
            "structured_total_ticker_rows_including_exits": structured_rows + structured_exit_rows,
            "structured_unique_ticker_count": len(structured_tickers),
            "cross_sheet_duplicate_ticker_count": len(cross_sheet_duplicates),
            "sheets_with_duplicate_tickers": len(all_duplicate_sheets),
            "sheets_with_header_failure": len(all_header_failures),
            "sheets_with_effective_period_missing": len(all_effective_missing),
            "sheets_with_announcement_date_missing": len(all_announcement_missing),
            "pdf_only_or_unparsed_archive_count": sum(
                not bool(item["structured_sector_workbook_members"]) for item in archives
            ),
        },
        "checks": {
            "all_frozen_archives_present": True,
            "archive_hashes_recorded": True,
            "structured_sector_sheets_found": bool(sheets),
            "all_structured_headers_found": not all_header_failures,
            "all_structured_tickers_unique_within_sheet": not all_duplicate_sheets,
            "cross_sheet_sector_partition_is_unique": not cross_sheet_duplicates,
            "announcement_dates_present": not all_announcement_missing,
            "effective_period_text_present": not all_effective_missing,
            "row_level_available_at_present": False,
            "daily_membership_intervals_present": False,
            "issuer_security_identity_chain_present": False,
            "revision_vintage_present": False,
        },
        "interpretation": {
            "status": "SOURCE_PARTIAL_STRUCTURAL_SIGNAL",
            "admissibility": "NOT_ADMITTED",
            "predictive_claim": False,
            "publication_semantics_status": "UNKNOWN_ANNOUNCEMENT_DATE_IS_NOT_ROW_LEVEL_AVAILABLE_AT",
            "membership_semantics_status": "UNKNOWN_INDEX_CONSTITUENT_NOT_DAILY_SECTOR_MEMBERSHIP",
            "identity_status": "UNKNOWN_NO_ISSUER_OR_ISIN_TRANSITION_CHAIN",
            "sector_partition_status": (
                "UNKNOWN_CROSS_SHEET_DUPLICATES"
                if cross_sheet_duplicates
                else "NO_CROSS_SHEET_DUPLICATES_OBSERVED"
            ),
            "status_change_authorized": False,
        },
        "archives": archives,
        "sheets": sheets,
        "cross_sheet_duplicates": cross_sheet_duplicates,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(r"D:\Documents\Project\idx-pit-sector-official-raw-20260811"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            r"D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_sector01_source_audit_v1.json"
        ),
    )
    args = parser.parse_args()
    artifact = audit_archive(args.root, args.output)
    print(json.dumps({"status": artifact["interpretation"]["status"], "source": artifact["source"]}, indent=2))


if __name__ == "__main__":
    main()
