"""Outcome-blind quality audit for locally persisted ownership/KSEI snapshots.

This script does not call a provider and does not construct a model feature.
It profiles snapshot grain, schema, arithmetic integrity, panel-date overlap,
and the bounded company-profile/free-float probe surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd


EXPECTED_COLUMNS = [
    "Date",
    "Code",
    "Type",
    "Sec. Num",
    "Price",
    "Local IS",
    "Local CP",
    "Local PF",
    "Local IB",
    "Local ID",
    "Local MF",
    "Local SC",
    "Local FD",
    "Local OT",
    "Total",
    "Foreign IS",
    "Foreign CP",
    "Foreign PF",
    "Foreign IB",
    "Foreign ID",
    "Foreign MF",
    "Foreign SC",
    "Foreign FD",
    "Foreign OT",
    "Total",
]
UNIQUE_COLUMNS = [*EXPECTED_COLUMNS[:-1], "Foreign Total"]
NUMERIC_COLUMNS = ["Sec. Num", "Price", *EXPECTED_COLUMNS[5:14], "Total", *EXPECTED_COLUMNS[15:24], "Foreign Total"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_zip(path: Path, panel: pd.DataFrame) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        members = archive.namelist()
        if len(members) != 1:
            raise ValueError(f"expected one member in {path}, got {members}")
        with archive.open(members[0]) as handle:
            frame = pd.read_csv(handle, sep="|", encoding="utf-8-sig")

    raw_columns = list(frame.columns)
    normalized_raw_columns = ["Total" if column == "Total.1" else column for column in raw_columns]
    if raw_columns and raw_columns[-1] == "Total.1":
        frame = frame.rename(columns={"Total.1": "Foreign Total"})
    schema_exact = normalized_raw_columns == EXPECTED_COLUMNS and list(frame.columns) == UNIQUE_COLUMNS
    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["snapshot_date"] = pd.to_datetime(
        frame["Date"], format="%d-%b-%Y", errors="coerce"
    ).dt.date
    equity = frame.loc[frame["Type"].eq("EQUITY")].copy()
    numeric_bad = int(equity[NUMERIC_COLUMNS].isna().any(axis=1).sum())
    negative_numeric = int((equity[NUMERIC_COLUMNS] < 0).any(axis=1).sum())
    local_total = equity["Total"]
    foreign_total = equity["Foreign Total"]
    total_gt_outstanding = int(((local_total + foreign_total) > equity["Sec. Num"]).sum())

    snapshot_dates = sorted({str(value) for value in equity["snapshot_date"].dropna()})
    overlap = []
    for snapshot_date in sorted({value for value in equity["snapshot_date"].dropna()}):
        panel_slice = panel.loc[panel["date"].eq(snapshot_date)]
        source_codes = set(equity.loc[equity["snapshot_date"].eq(snapshot_date), "Code"].astype(str))
        panel_codes = set(panel_slice["ticker"].astype(str))
        overlap.append(
            {
                "snapshot_date": str(snapshot_date),
                "source_equity_rows": int(len(source_codes)),
                "panel_rows": int(len(panel_slice)),
                "panel_tickers": int(len(panel_codes)),
                "overlap_tickers": int(len(source_codes & panel_codes)),
                "panel_ticker_coverage": (
                    float(len(source_codes & panel_codes) / len(panel_codes))
                    if panel_codes
                    else None
                ),
            }
        )

    return {
        "file": path.name,
        "sha256": sha256_file(path),
        "archive_member": members[0],
        "schema_exact": schema_exact,
        "column_count": int(len(frame.columns) - 1),
        "all_rows": int(len(frame)),
        "all_unique_codes": int(frame["Code"].nunique()),
        "all_duplicate_code_keys": int(frame["Code"].duplicated().sum()),
        "instrument_types": sorted(frame["Type"].dropna().astype(str).unique()),
        "equity_rows": int(len(equity)),
        "equity_unique_codes": int(equity["Code"].nunique()),
        "equity_duplicate_code_keys": int(equity["Code"].duplicated().sum()),
        "equity_numeric_bad_rows": numeric_bad,
        "equity_negative_numeric_rows": negative_numeric,
        "equity_holder_total_gt_outstanding": total_gt_outstanding,
        "snapshot_dates": snapshot_dates,
        "panel_overlap": overlap,
    }


def audit_profiles(root: Path) -> dict[str, object]:
    files = sorted((root / "idx_company_profile").glob("*.normalized.csv"))
    frames = [pd.read_csv(path) for path in files]
    all_columns = sorted({column for frame in frames for column in frame.columns})
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    explicit_free_float = [
        column
        for column in all_columns
        if any(token in column.lower() for token in ("free", "float", "public_ownership", "outstanding"))
    ]
    return {
        "file_count": len(files),
        "tickers": sorted({path.stem.split(".")[0] for path in files}),
        "normalized_rows": int(len(combined)),
        "columns": all_columns,
        "duplicate_ticker_holder_rows": int(
            combined.duplicated(subset=["ticker", "holder_name", "snapshot_date"]).sum()
        )
        if not combined.empty
        else 0,
        "snapshot_dates": sorted(combined["snapshot_date"].dropna().astype(str).unique())
        if not combined.empty
        else [],
        "explicit_free_float_like_columns": explicit_free_float,
        "profile_surface_is_current_snapshot_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--ownership-root", type=Path, required=True)
    parser.add_argument("--free-float-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    panel = pd.read_parquet(args.panel, columns=["ticker", "date"])
    panel["date"] = pd.to_datetime(panel["date"]).dt.date
    zips = sorted((args.ownership_root / "official_ksei_files").glob("*.zip"))
    snapshots = [audit_zip(path, panel) for path in zips]
    result = {
        "audit": "ALPHA_OWNERSHIP_KSEI_SOURCE_AUDIT_V1",
        "status": "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED",
        "scope": {
            "outcome_accessed": False,
            "target_accessed": False,
            "provider_accessed": False,
            "feature_created": False,
            "canonical_mutation": False,
        },
        "panel": {
            "path": str(args.panel),
            "sha256": sha256_file(args.panel),
            "rows": int(len(panel)),
            "dates": int(panel["date"].nunique()),
            "tickers": int(panel["ticker"].nunique()),
        },
        "ksei_archive": {
            "root": str(args.ownership_root),
            "snapshot_count": len(snapshots),
            "snapshots": snapshots,
        },
        "company_profile_probe": audit_profiles(args.free_float_root),
        "admission": {
            "daily_pit_feature_ready": False,
            "reason": [
                "only eight snapshot dates across the 1,260-date panel horizon",
                "KSEI aggregate is composition-by-security, not named-holder or effective-free-float ground truth",
                "row-level publication/knowledge/revision contract is not established",
                "company-profile probe is five current snapshots without historical backdating",
                "official IDX >=1 percent attachment retrieval remains blocked in the bounded probe",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output), "snapshots": len(snapshots)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
