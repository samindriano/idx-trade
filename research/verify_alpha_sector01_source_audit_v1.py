"""Independent integrity verifier for the SECTOR-01 source audit artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


FROZEN_NAMES = {
    "IDX_IC_2021_Peng-00171.zip",
    "IDX_IC_2022_Peng-00150.zip",
    "IDX_IC_2023_Peng-00156.zip",
    "IDX_IC_2024_Peng-00128-ID.zip",
    "IDX_IC_2025_Peng-00110-ID.zip",
    "IDX_IC_2026_Peng-00100-ID.zip",
    "IDX_IC_BASELINE_2021_idx-industrial-classification.zip",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(root: Path, artifact_path: Path, output_path: Path) -> dict[str, object]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    archives = artifact["archives"]
    sheets = artifact["sheets"]
    checks: dict[str, bool] = {}

    actual_names = {item["name"] for item in archives}
    checks["archive_names_exact"] = actual_names == FROZEN_NAMES
    checks["archive_count_exact"] = len(archives) == len(FROZEN_NAMES)
    checks["source_hashes_exact"] = all(
        item["sha256"] == sha256(root / item["name"])
        for item in archives
    )
    checks["archive_member_inventory_exact"] = all(
        sorted(item["xlsx_members"] + item["pdf_members"])
        == sorted(
            member
            for member in zipfile.ZipFile(root / item["name"]).namelist()
            if member.lower().endswith((".xlsx", ".pdf"))
        )
        for item in archives
    )
    checks["structured_sheets_present"] = len(sheets) == 22
    checks["all_headers_found"] = all(bool(item["header_found"]) for item in sheets)
    checks["all_sheet_tickers_unique"] = all(not item["duplicate_tickers"] for item in sheets)
    recomputed_cross_sheet_duplicates: dict[str, list[str]] = {}
    by_archive_ticker: dict[tuple[str, str], list[str]] = {}
    for item in sheets:
        for ticker in item.get("ticker_values", []):
            by_archive_ticker.setdefault((str(item["archive"]), ticker), []).append(str(item["sheet"]))
    for (archive, ticker), sheet_names in by_archive_ticker.items():
        if len(sheet_names) > 1:
            recomputed_cross_sheet_duplicates[f"{archive}:{ticker}"] = sheet_names
    checks["cross_sheet_duplicate_inventory_exact"] = (
        recomputed_cross_sheet_duplicates == artifact["cross_sheet_duplicates"]
    )
    checks["all_announcement_dates_present"] = all(
        bool(item["announcement_date_text"]) for item in sheets
    )
    checks["all_effective_period_text_present"] = all(
        bool(item["effective_period_text"]) for item in sheets
    )
    checks["no_pit_claim"] = (
        artifact["checks"]["row_level_available_at_present"] is False
        and artifact["checks"]["daily_membership_intervals_present"] is False
        and artifact["checks"]["issuer_security_identity_chain_present"] is False
        and artifact["checks"]["revision_vintage_present"] is False
    )
    checks["no_candidate"] = artifact["candidate_id_created"] is False
    checks["no_outcome_provider"] = (
        artifact["outcome_accessed"] is False
        and artifact["provider_accessed"] is False
        and all(value is False for value in artifact["scope"].values())
    )
    checks["status_expected"] = artifact["interpretation"]["status"] == "SOURCE_PARTIAL_STRUCTURAL_SIGNAL"
    checks["admission_expected"] = artifact["interpretation"]["admissibility"] == "NOT_ADMITTED"

    result = {
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "artifact_sha256": sha256(artifact_path),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "target_accessed": False,
        "outcome_accessed": False,
        "provider_accessed": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["verdict"] != "PASS":
        raise SystemExit(1)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(r"D:\Documents\Project\idx-pit-sector-official-raw-20260811"))
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path(r"D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_sector01_source_audit_v1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(r"D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_sector01_source_audit_v1_independent_verification.json"),
    )
    args = parser.parse_args()
    verify(args.root, args.artifact, args.output)


if __name__ == "__main__":
    main()
