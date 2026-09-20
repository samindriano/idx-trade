"""Outcome-blind crosswalk of acquired official IDX surfaces.

This audit is deliberately a read-only bridge between the newly acquired raw
surfaces and the existing research corpus.  It does not overwrite any source,
canonical panel, or accepted financial bundle.  The XBRL projection is a
structural materialization only: it preserves report-period and context
metadata, but it does not manufacture publication/knowledge-time or identity
authority.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable
import xml.etree.ElementTree as ET

import pandas as pd


STAGING_MARKER = "idx-alpha-available-data-staging-20260919"
FORBIDDEN_MARKERS = ("h5", "h10", "icir", "pnl", "target", "outcome", "holdout")
REPORT_YEARS = tuple(str(year) for year in range(2019, 2026))
XBRL_FIELD_TAGS: dict[str, set[str]] = {
    "total_assets": {"Assets"},
    "total_liabilities": {"Liabilities"},
    "total_equity": {"Equity", "EquityAttributableToEquityOwnersOfParentEntity"},
    "cash_and_equivalents": {"CashAndCashEquivalents"},
    "revenue": {"SalesAndRevenue", "Revenue"},
    "net_income": {"ProfitLoss", "ProfitLossAttributableToParentEntity"},
    "operating_cash_flow": {
        "NetCashFlowsReceivedFromUsedInOperatingActivities",
        "CashGeneratedFromUsedInOperations",
    },
}
TAG_TO_FIELD = {tag: field for field, tags in XBRL_FIELD_TAGS.items() for tag in tags}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_code(value: Any) -> str:
    return str(value or "").strip().upper()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def raw_files(directory: Path, pattern: str = "*.raw") -> list[Path]:
    return sorted(directory.glob(pattern))


def report_rows(index_dir: Path, years: Iterable[str], period_kind: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(index_dir.glob("*.raw")):
        payload = load_json(path)
        search = payload.get("Search", {})
        if period_kind == "annual" and str(search.get("Periode") or "").lower() not in ("", "audit"):
            continue
        if period_kind == "quarterly" and search.get("Periode") not in {"TW1", "TW2", "TW3"}:
            continue
        year = str(search.get("Year") or "")
        if year not in set(years):
            continue
        for row in payload.get("Results", []):
            if isinstance(row, dict):
                rows.append(row)
    return rows


def instance_attachment(row: dict[str, Any]) -> dict[str, Any] | None:
    attachments = row.get("Attachments") or []
    candidates = [
        attachment
        for attachment in attachments
        if isinstance(attachment, dict)
        and str(attachment.get("File_Name", "")).lower() == "instance.zip"
    ]
    return candidates[0] if candidates else None


def file_modified_lag_audit(annual_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure report-period to File_Modified distance without calling it PIT time."""

    records: list[dict[str, Any]] = []
    for row in annual_rows:
        year = str(row.get("Report_Year") or "")
        modified = pd.to_datetime(row.get("File_Modified"), errors="coerce")
        period_end = pd.to_datetime(f"{year}-12-31", errors="coerce")
        if pd.isna(modified) or pd.isna(period_end):
            continue
        records.append(
            {
                "ticker": normalize_code(row.get("KodeEmiten")),
                "report_year": year,
                "file_modified": str(row.get("File_Modified")),
                "lag_days": float((modified - period_end).total_seconds() / 86400),
            }
        )
    lags = [record["lag_days"] for record in records]
    if not lags:
        return {
            "status": "NO_VALID_FILE_MODIFIED_LAGS",
            "rows_with_valid_dates": 0,
            "rows_without_valid_dates": len(annual_rows),
        }
    return {
        "status": "DESCRIPTIVE_FILE_MODIFIED_LAG_ONLY",
        "rows_with_valid_dates": len(records),
        "rows_without_valid_dates": len(annual_rows) - len(records),
        "lag_days_min": round(min(lags), 6),
        "lag_days_median": round(float(pd.Series(lags).median()), 6),
        "lag_days_max": round(max(lags), 6),
        "lag_days_negative_count": sum(lag < 0 for lag in lags),
        "lag_days_over_180_count": sum(lag > 180 for lag in lags),
        "lag_days_over_365_count": sum(lag > 365 for lag in lags),
        "lag_days_over_730_count": sum(lag > 730 for lag in lags),
        "largest_lag_samples": sorted(records, key=lambda record: record["lag_days"], reverse=True)[:5],
        "interpretation": (
            "File_Modified is a descriptive source timestamp relative to the annual period end. "
            "The lag distribution does not prove publication, available-at, knowledge-time, or revision "
            "semantics and must not be used as a PIT admission substitute."
        ),
    }


def report_inventory(index_dir: Path, annual_xbrl_dir: Path, quarterly_years: Iterable[str]) -> dict[str, Any]:
    annual = report_rows(index_dir, REPORT_YEARS, "annual")
    quarterly = report_rows(index_dir, quarterly_years, "quarterly")
    annual_expected = [
        {
            "code": normalize_code(row.get("KodeEmiten")),
            "year": str(row.get("Report_Year") or ""),
            "period": row.get("Report_Period"),
            "file_modified": row.get("File_Modified"),
            "instance_file_id": (instance_attachment(row) or {}).get("File_ID"),
            "instance_path": (instance_attachment(row) or {}).get("File_Path"),
        }
        for row in annual
    ]
    expected_keys = {(row["year"], row["code"]) for row in annual_expected if row["code"]}
    downloaded: dict[tuple[str, str], Path] = {}
    archive_dirs = list(annual_xbrl_dir.glob("*-audit"))
    sibling_2023 = annual_xbrl_dir.parent / "2023-audit"
    if sibling_2023.is_dir():
        archive_dirs.append(sibling_2023)
    for archive_dir in sorted(archive_dirs):
        year_match = re.match(r"(\d{4})-audit$", archive_dir.name)
        if not year_match:
            continue
        for path in sorted(archive_dir.glob("*.instance.zip")):
            code = path.name.removesuffix(".instance.zip").upper()
            downloaded[(year_match.group(1), code)] = path
    missing_instance_rows = [row for row in annual_expected if not row["instance_file_id"]]
    expected_with_instance = {(row["year"], row["code"]) for row in annual_expected if row["instance_file_id"]}
    downloaded_unexpected = sorted(set(downloaded) - expected_with_instance)
    return {
        "annual_index_rows": len(annual),
        "annual_index_code_union": sorted({row["code"] for row in annual_expected if row["code"]}),
        "annual_index_rows_by_year": dict(sorted(Counter(row["year"] for row in annual_expected).items())),
        "annual_file_modified_lag_audit": file_modified_lag_audit(annual),
        "annual_rows_without_instance_attachment": missing_instance_rows,
        "annual_rows_with_instance_attachment": len(expected_with_instance),
        "annual_downloaded_instance_archives": len(downloaded),
        "annual_downloaded_keys_not_in_index": [list(key) for key in downloaded_unexpected],
        "annual_expected_instance_keys_not_downloaded": [
            list(key) for key in sorted(expected_with_instance - set(downloaded))
        ],
        "quarterly_index_rows": len(quarterly),
        "quarterly_index_code_union": sorted({normalize_code(row.get("KodeEmiten")) for row in quarterly}),
        "quarterly_index_rows_by_period": dict(
            sorted(Counter(str(row.get("Report_Period") or "") for row in quarterly).items())
        ),
        "quarterly_index_rows_by_year_period": {
            f"{year}:{period}": count
            for (year, period), count in sorted(
                Counter(
                    (str(row.get("Report_Year") or ""), str(row.get("Report_Period") or ""))
                    for row in quarterly
                ).items()
            )
        },
        "quarterly_xbrl_materialized": False,
        "quarterly_xbrl_reason": "Quarterly index metadata was acquired, but this lane did not download quarterly archives.",
    }, downloaded


def read_ratio_inventory(ratio_dir: Path) -> dict[str, Any]:
    snapshots: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    for path in sorted(ratio_dir.glob("*.raw")):
        payload = load_json(path)
        rows = [row for row in payload.get("data", []) if isinstance(row, dict)]
        all_rows.extend(rows)
        snapshots.append(
            {
                "file": path.name,
                "sha256": sha256_file(path),
                "rows": len(rows),
                "codes": len({normalize_code(row.get("code")) for row in rows if row.get("code")}),
                "fs_date_min": min((str(row.get("fsDate")) for row in rows if row.get("fsDate")), default=None),
                "fs_date_max": max((str(row.get("fsDate")) for row in rows if row.get("fsDate")), default=None),
                "required_field_missing_rows": sum(
                    any(row.get(field) is None for field in ("code", "fsDate", "assets", "liabilities", "equity", "sales", "profitPeriod"))
                    for row in rows
                ),
            }
        )
    return {
        "snapshot_count": len(snapshots),
        "total_rows": len(all_rows),
        "code_union": sorted({normalize_code(row.get("code")) for row in all_rows if row.get("code")}),
        "fs_date_min": min((str(row.get("fsDate")) for row in all_rows if row.get("fsDate")), default=None),
        "fs_date_max": max((str(row.get("fsDate")) for row in all_rows if row.get("fsDate")), default=None),
        "required_field_missing_rows": sum(item["required_field_missing_rows"] for item in snapshots),
        "snapshots": snapshots,
    }


def ratio_classification_audit(ratio_dir: Path) -> dict[str, Any]:
    """Describe observed classification stability without assigning PIT meaning.

    The endpoint returns classification fields alongside financial-period rows.
    This audit compares the fields across retained response snapshots only.  It
    intentionally does not treat ``fsDate`` as a classification effective date
    or the response filename as a knowledge-time contract.
    """

    classification_fields = (
        "sector",
        "subSector",
        "industry",
        "subIndustry",
        "sectorCode",
        "subSectorCode",
        "industryCode",
        "subIndustryCode",
    )
    named_fields = classification_fields[:4]
    code_fields = classification_fields[4:]
    snapshot_rows: list[tuple[str, list[dict[str, Any]]]] = []
    for path in sorted(ratio_dir.glob("*.raw")):
        payload = load_json(path)
        rows = [row for row in payload.get("data", []) if isinstance(row, dict)]
        snapshot_rows.append((path.name, rows))

    code_snapshot_values: dict[str, dict[str, tuple[Any, ...]]] = defaultdict(dict)
    field_observed_values: dict[str, set[str]] = {field: set() for field in classification_fields}
    complete_named_rows = 0
    complete_code_rows = 0
    nonempty_row_counts: Counter[str] = Counter()
    duplicate_code_snapshots = 0
    for filename, rows in snapshot_rows:
        seen_codes: set[str] = set()
        for row in rows:
            code = normalize_code(row.get("code"))
            if not code:
                continue
            if code in seen_codes:
                duplicate_code_snapshots += 1
            seen_codes.add(code)
            values = tuple(row.get(field) for field in classification_fields)
            code_snapshot_values[code][filename] = values
            if all(value not in (None, "") for value in values[:4]):
                complete_named_rows += 1
            if all(value not in (None, "") for value in values[4:]):
                complete_code_rows += 1
            for field, value in zip(classification_fields, values):
                if value not in (None, ""):
                    nonempty_row_counts[field] += 1
                    field_observed_values[field].add(str(value))

    changed_by_field: dict[str, list[str]] = {field: [] for field in classification_fields}
    any_changed_codes: set[str] = set()
    change_samples: list[dict[str, Any]] = []
    for code, snapshots in sorted(code_snapshot_values.items()):
        ordered = sorted(snapshots.items())
        for (previous_name, previous_values), (current_name, current_values) in zip(ordered, ordered[1:]):
            changed_fields = [
                field
                for field, previous, current in zip(classification_fields, previous_values, current_values)
                if previous != current
            ]
            if not changed_fields:
                continue
            any_changed_codes.add(code)
            for field in changed_fields:
                changed_by_field[field].append(code)
            if len(change_samples) < 40:
                change_samples.append(
                    {
                        "ticker": code,
                        "previous_snapshot": previous_name,
                        "current_snapshot": current_name,
                        "changed_fields": changed_fields,
                        "previous_values": dict(zip(classification_fields, previous_values)),
                        "current_values": dict(zip(classification_fields, current_values)),
                    }
                )

    return {
        "status": "BOUNDED_SNAPSHOT_CLASSIFICATION_ONLY",
        "classification_fields": list(classification_fields),
        "snapshot_count": len(snapshot_rows),
        "observed_code_count": len(code_snapshot_values),
        "code_snapshot_observations": sum(len(values) for values in code_snapshot_values.values()),
        "rows_with_complete_named_classification": complete_named_rows,
        "rows_with_complete_code_classification": complete_code_rows,
        "nonempty_row_counts": dict(nonempty_row_counts),
        "duplicate_code_snapshots": duplicate_code_snapshots,
        "distinct_value_counts": {field: len(values) for field, values in field_observed_values.items()},
        "codes_with_adjacent_snapshot_change_by_field": {
            field: len(set(codes)) for field, codes in changed_by_field.items()
        },
        "codes_with_any_adjacent_snapshot_change": len(any_changed_codes),
        "change_samples": change_samples,
        "interpretation": (
            "Classification fields are observed on retained ratio response snapshots and can be compared "
            "for stability. The snapshot label is an acquisition/query label, while fsDate is a financial "
            "period field; neither establishes classification effective time, available-at time, revision "
            "lineage, or historical PIT sector membership."
        ),
    }


def read_trading_inventory(history_dir: Path) -> tuple[dict[str, Any], set[str]]:
    codes: set[str] = set()
    rows = 0
    dates: list[str] = []
    zero_volume = 0
    foreign_nonzero = 0
    files: list[dict[str, Any]] = []
    for path in sorted(history_dir.glob("*.json")):
        payload = load_json(path)
        requested = normalize_code(payload.get("KodeEmiten") or path.stem)
        code_rows = [row for row in payload.get("replies", []) if isinstance(row, dict)]
        codes.add(requested)
        rows += len(code_rows)
        dates.extend(str(row.get("Date", ""))[:10] for row in code_rows if row.get("Date"))
        zero_volume += sum(float(row.get("Volume") or 0) == 0 for row in code_rows)
        foreign_nonzero += sum(float(row.get("ForeignBuy") or 0) != 0 or float(row.get("ForeignSell") or 0) != 0 for row in code_rows)
        files.append({"code": requested, "rows": len(code_rows), "sha256": sha256_file(path), "path": path.name})
    return {
        "raw_files": len(files),
        "code_union": sorted(codes),
        "raw_rows": rows,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "zero_volume_rows": zero_volume,
        "foreign_nonzero_rows": foreign_nonzero,
        "files_sha256": hashlib.sha256("\n".join(json.dumps(row, sort_keys=True) for row in files).encode()).hexdigest(),
    }, codes


def trading_panel_key_crosswalk(history_dir: Path, panel: pd.DataFrame) -> dict[str, Any]:
    """Compare the official raw daily keys/fields to the current panel window."""

    panel = panel.copy()
    panel["ticker"] = panel["ticker"].map(normalize_code)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce")
    min_date = panel["date"].min()
    max_date = panel["date"].max()
    panel_window = panel.loc[panel["date"].between(min_date, max_date)].copy()
    panel_keys = {
        (row.ticker, row.date.date().isoformat())
        for row in panel_window[["ticker", "date"]].itertuples(index=False)
        if pd.notna(row.date)
    }
    panel_values = {
        (normalize_code(row.ticker), row.date.date().isoformat()): row
        for row in panel_window.itertuples(index=False)
        if pd.notna(row.date)
    }
    official_keys: set[tuple[str, str]] = set()
    mismatch_counts: Counter[str] = Counter()
    conflict_samples: list[dict[str, Any]] = []
    duplicate_keys: Counter[tuple[str, str]] = Counter()
    conflict_keys: set[tuple[str, str]] = set()
    field_map = {"high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
    for path in sorted(history_dir.glob("*.json")):
        payload = load_json(path)
        code = normalize_code(payload.get("KodeEmiten") or path.stem)
        for raw in payload.get("replies", []) or []:
            if not isinstance(raw, dict) or not raw.get("Date"):
                continue
            date = str(raw["Date"])[:10]
            if date < min_date.date().isoformat() or date > max_date.date().isoformat():
                continue
            key = (code, date)
            duplicate_keys[key] += 1
            official_keys.add(key)
            panel_row = panel_values.get(key)
            if panel_row is None:
                continue
            mismatched_fields: list[str] = []
            for panel_field, raw_field in field_map.items():
                panel_value = getattr(panel_row, panel_field, None)
                raw_value = raw.get(raw_field)
                if pd.isna(panel_value) and (raw_value is None or raw_value == ""):
                    continue
                try:
                    equal = float(panel_value) == float(raw_value)
                except (TypeError, ValueError):
                    equal = panel_value == raw_value
                if not equal:
                    mismatch_counts[panel_field] += 1
                    mismatched_fields.append(panel_field)
            if mismatched_fields and len(conflict_samples) < 20:
                conflict_samples.append({"ticker": code, "date": date, "fields": mismatched_fields})
            if mismatched_fields:
                conflict_keys.add(key)
    intersection = panel_keys & official_keys
    panel_missing = panel_keys - official_keys
    official_only = official_keys - panel_keys
    return {
        "panel_window_date_min": min_date.date().isoformat(),
        "panel_window_date_max": max_date.date().isoformat(),
        "panel_window_keys": len(panel_keys),
        "official_trading_keys_in_same_window": len(official_keys),
        "exact_key_intersection": len(intersection),
        "panel_keys_missing_from_official_trading": len(panel_missing),
        "official_trading_keys_not_in_panel": len(official_only),
        "panel_missing_by_ticker": dict(sorted(Counter(key[0] for key in panel_missing).items())),
        "official_only_by_ticker_top10": dict(Counter(key[0] for key in official_only).most_common(10)),
        "panel_missing_sample": [list(key) for key in sorted(panel_missing)[:50]],
        "official_only_sample": [list(key) for key in sorted(official_only)[:50]],
        "field_mismatch_counts_on_intersection": dict(sorted(mismatch_counts.items())),
        "conflicting_key_count_on_intersection": len(conflict_keys),
        "conflicting_keys_sample": conflict_samples,
        "duplicate_official_keys_in_window": sum(count > 1 for count in duplicate_keys.values()),
        "comparison_status": "STRUCTURAL_KEY_AND_RAW_FIELD_CROSSWALK_ONLY",
    }


def read_issued_inventory(issued_dir: Path) -> tuple[dict[str, Any], set[str]]:
    codes: set[str] = set()
    rows = 0
    empty: list[str] = []
    actions: Counter[str] = Counter()
    dates: list[str] = []
    for path in sorted(issued_dir.glob("*.json")):
        payload = load_json(path)
        code = normalize_code(path.stem)
        data = [row for row in payload.get("data", []) if isinstance(row, dict)]
        codes.add(code)
        rows += len(data)
        if not data:
            empty.append(code)
        for row in data:
            action = str(row.get("JenisTindakan") or "")
            if action:
                actions[action] += 1
            if row.get("TanggalPencatatan"):
                dates.append(str(row["TanggalPencatatan"])[:10])
    return {
        "raw_files": len(codes),
        "code_union": sorted(codes),
        "raw_rows": rows,
        "empty_history_codes": sorted(empty),
        "nonempty_history_codes": sorted(codes - set(empty)),
        "action_counts": dict(sorted(actions.items())),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
    }, codes


def read_profile_inventory(profile_dir: Path) -> tuple[dict[str, Any], set[str]]:
    codes: set[str] = set()
    empty: list[str] = []
    populated = 0
    listing_dates = 0
    stock_isin_fields: set[str] = set()
    bond_isin_rows = 0
    for path in sorted(profile_dir.glob("*.json")):
        payload = load_json(path)
        code = normalize_code(path.stem)
        codes.add(code)
        profiles = [row for row in payload.get("Profiles", []) if isinstance(row, dict)]
        if not profiles:
            empty.append(code)
            continue
        populated += 1
        listing_dates += bool(profiles[0].get("TanggalPencatatan"))
        for key in profiles[0]:
            if "isin" in key.lower():
                stock_isin_fields.add(key)
        for row in payload.get("BondsAndSukuk", []) or []:
            if isinstance(row, dict) and row.get("ISINCode"):
                bond_isin_rows += 1
    return {
        "raw_files": len(codes),
        "code_union": sorted(codes),
        "profiles_found": populated,
        "profiles_empty": sorted(empty),
        "listing_date_present": listing_dates,
        "stock_profile_isin_fields": sorted(stock_isin_fields),
        "bond_rows_with_isin": bond_isin_rows,
    }, codes


def period_from_context(context: ET.Element) -> dict[str, Any]:
    period = next((child for child in context if child.tag.rsplit("}", 1)[-1] == "period"), None)
    values = {child.tag.rsplit("}", 1)[-1]: (child.text or "").strip() for child in (list(period) if period is not None else [])}
    dimensions = sum(
        1
        for element in context.iter()
        if element.tag.rsplit("}", 1)[-1] in {"explicitMember", "typedMember"}
    )
    return {
        "start": values.get("startDate"),
        "end": values.get("endDate"),
        "instant": values.get("instant"),
        "has_dimensions": dimensions > 0,
        "dimension_count": dimensions,
    }


def numeric_value(text: str | None) -> float | None:
    if text is None or not text.strip():
        return None
    try:
        value = float(text.strip().replace(",", ""))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def materialize_xbrl(
    archives: dict[tuple[str, str], Path],
    output_jsonl: Path,
    limit: int | None = None,
) -> dict[str, Any]:
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    field_archive_counts: Counter[str] = Counter()
    field_fact_counts: Counter[str] = Counter()
    field_period_keys: dict[str, set[tuple[str, str, str, str]]] = defaultdict(set)
    parsed_archives = 0
    parse_errors: list[dict[str, str]] = []
    with output_jsonl.open("w", encoding="utf-8", newline="\n") as sink:
        for index, ((year, code), archive) in enumerate(sorted(archives.items())):
            if limit is not None and index >= limit:
                break
            try:
                with zipfile.ZipFile(archive) as zf:
                    instance_name = next(name for name in zf.namelist() if name.lower().endswith(".xbrl"))
                    archive_sha256 = sha256_file(archive)
                    contexts: dict[str, dict[str, Any]] = {}
                    archive_fields: set[str] = set()
                    with zf.open(instance_name) as stream:
                        for event, element in ET.iterparse(stream, events=("end",)):
                            local = element.tag.rsplit("}", 1)[-1]
                            if local == "context":
                                context_id = element.get("id")
                                if context_id:
                                    contexts[context_id] = period_from_context(element)
                                element.clear()
                                continue
                            field = TAG_TO_FIELD.get(local)
                            if field is None:
                                if local not in {
                                    "identifier",
                                    "period",
                                    "startDate",
                                    "endDate",
                                    "instant",
                                    "segment",
                                    "scenario",
                                    "explicitMember",
                                    "typedMember",
                                }:
                                    element.clear()
                                continue
                            context_id = element.get("contextRef")
                            context = contexts.get(context_id or "")
                            value = numeric_value(element.text)
                            if context is None or value is None or context["has_dimensions"]:
                                element.clear()
                                continue
                            period_end = context.get("instant") or context.get("end")
                            period_start = context.get("start")
                            shape = "INSTANT" if context.get("instant") else "DURATION"
                            if not period_end:
                                element.clear()
                                continue
                            row = {
                                "ticker": code,
                                "report_year": year,
                                "report_period": "FY",
                                "field": field,
                                "concept": local,
                                "value": value,
                                "unit_ref": element.get("unitRef"),
                                "decimals": element.get("decimals"),
                                "context_ref": context_id,
                                "period_shape": shape,
                                "period_start": period_start,
                                "period_end": period_end,
                                "source_archive": str(archive),
                                "source_archive_sha256": archive_sha256,
                            }
                            sink.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
                            field_fact_counts[field] += 1
                            field_archive_counts[field] += field not in archive_fields
                            archive_fields.add(field)
                            field_period_keys[field].add((code, year, period_end, shape))
                            element.clear()
                    parsed_archives += 1
            except (OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
                parse_errors.append({"ticker": code, "year": year, "archive": str(archive), "error": str(exc)})
    return {
        "archives_requested": min(len(archives), limit) if limit is not None else len(archives),
        "archives_parsed": parsed_archives,
        "parse_errors": parse_errors,
        "field_archive_counts": dict(sorted(field_archive_counts.items())),
        "field_fact_counts": dict(sorted(field_fact_counts.items())),
        "field_distinct_code_year_period_counts": {
            field: len(values) for field, values in sorted(field_period_keys.items())
        },
        "materialized_jsonl": str(output_jsonl),
        "materialized_jsonl_sha256": sha256_file(output_jsonl),
    }


def summarize_materialized_xbrl(path: Path, archives: dict[tuple[str, str], Path]) -> dict[str, Any]:
    """Re-index an already materialized local projection without reparsing XML."""

    field_archive_keys: dict[str, set[str]] = defaultdict(set)
    field_fact_counts: Counter[str] = Counter()
    field_period_keys: dict[str, set[tuple[str, str, str, str]]] = defaultdict(set)
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        field = str(row["field"])
        field_archive_keys[field].add(str(row["source_archive"]))
        field_fact_counts[field] += 1
        field_period_keys[field].add(
            (
                str(row["ticker"]),
                str(row["report_year"]),
                str(row["period_end"]),
                str(row["period_shape"]),
            )
        )
    return {
        "archives_requested": len(archives),
        "archives_parsed": len({archive for values in field_archive_keys.values() for archive in values}),
        "parse_errors": [],
        "field_archive_counts": {
            field: len(values) for field, values in sorted(field_archive_keys.items())
        },
        "field_fact_counts": dict(sorted(field_fact_counts.items())),
        "field_distinct_code_year_period_counts": {
            field: len(values) for field, values in sorted(field_period_keys.items())
        },
        "materialized_jsonl": str(path),
        "materialized_jsonl_sha256": sha256_file(path),
        "reused_existing_projection": True,
    }


def xbrl_semantic_collision_audit(path: Path) -> dict[str, Any]:
    """Count concept/unit/key multiplicity in the raw structural projection."""

    concepts: dict[str, set[str]] = defaultdict(set)
    units: dict[str, set[str]] = defaultdict(set)
    shapes: dict[str, set[str]] = defaultdict(set)
    period_keys: dict[str, Counter[tuple[str, str, str]]] = defaultdict(Counter)
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        field = str(row["field"])
        concepts[field].add(str(row.get("concept")))
        units[field].add(str(row.get("unit_ref")))
        shapes[field].add(str(row.get("period_shape")))
        period_keys[field][
            (str(row["ticker"]), str(row["report_year"]), str(row["period_end"]))
        ] += 1
    duplicate_groups = {
        field: sum(count > 1 for count in keys.values())
        for field, keys in sorted(period_keys.items())
    }
    max_facts = {
        field: max(keys.values(), default=0) for field, keys in sorted(period_keys.items())
    }
    return {
        "status": "SEMANTIC_COLLISION_AUDIT_ONLY",
        "concepts_by_field": {field: sorted(values) for field, values in sorted(concepts.items())},
        "units_by_field": {field: sorted(values) for field, values in sorted(units.items())},
        "period_shapes_by_field": {field: sorted(values) for field, values in sorted(shapes.items())},
        "duplicate_code_year_period_groups": duplicate_groups,
        "max_facts_per_code_year_period": max_facts,
        "interpretation": (
            "Multiple concepts, units, or undimensioned facts can map to one candidate field and period. "
            "This audit demonstrates why structural parsing is not semantic normalization; it does not choose "
            "a concept, unit, consolidation, restatement, or issuer identity policy."
        ),
    }


def crosswalk(
    staging_root: Path,
    panel_path: Path,
    financial_bundle_path: Path,
    xbrl_limit: int | None,
    output: Path,
    reuse_xbrl: bool = False,
) -> dict[str, Any]:
    if STAGING_MARKER not in str(output):
        raise ValueError("output must stay inside the isolated alpha staging root")
    for path in (panel_path, financial_bundle_path):
        if any(marker in str(path).lower() for marker in FORBIDDEN_MARKERS):
            raise ValueError(f"refusing protected-looking input path: {path}")
    index_dir = staging_root / "public-source-probes" / "idx-financial-reports" / "annual-index"
    quarterly_index_dir = staging_root / "public-source-probes" / "idx-financial-reports" / "quarterly-index"
    xbrl_dir = staging_root / "public-source-probes" / "idx-financial-reports" / "xbrl" / "annual"
    ratio_dir = staging_root / "public-source-probes" / "idx-trading-routes" / "financial-ratio" / "monthly"
    history_dir = staging_root / "public-source-probes" / "idx-trading-routes" / "history" / "all-983"
    issued_dir = staging_root / "public-source-probes" / "idx-trading-routes" / "issued-history" / "all-financial-union"
    profile_dir = staging_root / "public-source-probes" / "idx-trading-routes" / "profile-detail" / "all-observed-union"
    inventory, archives = report_inventory(index_dir, xbrl_dir, REPORT_YEARS)
    quarterly_rows = report_rows(quarterly_index_dir, REPORT_YEARS, "quarterly")
    inventory["quarterly_index_rows"] = len(quarterly_rows)
    inventory["quarterly_index_code_union"] = sorted(
        {normalize_code(row.get("KodeEmiten")) for row in quarterly_rows if row.get("KodeEmiten")}
    )
    inventory["quarterly_index_rows_by_period"] = dict(
        sorted(Counter(str(row.get("Report_Period") or "") for row in quarterly_rows).items())
    )
    inventory["quarterly_index_rows_by_year_period"] = {
        f"{year}:{period}": count
        for (year, period), count in sorted(
            Counter(
                (str(row.get("Report_Year") or ""), str(row.get("Report_Period") or ""))
                for row in quarterly_rows
            ).items()
        )
    }
    ratio = read_ratio_inventory(ratio_dir)
    ratio["classification_audit"] = ratio_classification_audit(ratio_dir)
    trading, trading_codes = read_trading_inventory(history_dir)
    issued, issued_codes = read_issued_inventory(issued_dir)
    profile, profile_codes = read_profile_inventory(profile_dir)

    panel = pd.read_parquet(panel_path, columns=["ticker", "date", "high", "low", "close", "volume"])
    panel["ticker"] = panel["ticker"].map(normalize_code)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce")
    panel_codes = set(panel["ticker"])
    financial = pd.read_parquet(
        financial_bundle_path,
        columns=["ticker", "date", "bundle_status", "core3_available", "all_five_available", "bundle_period_stratum"],
    )
    financial["ticker"] = financial["ticker"].map(normalize_code)
    financial_codes = set(financial["ticker"])
    current_rows = {
        "panel_rows": len(panel),
        "panel_key_count": int(panel.drop_duplicates(["ticker", "date"]).shape[0]),
        "panel_ticker_count": len(panel_codes),
        "panel_date_min": panel["date"].min().date().isoformat() if panel["date"].notna().any() else None,
        "panel_date_max": panel["date"].max().date().isoformat() if panel["date"].notna().any() else None,
        "financial_bundle_rows": len(financial),
        "financial_bundle_ticker_count": len(financial_codes),
        "financial_bundle_core3_rows": int(financial["core3_available"].fillna(False).astype(bool).sum()),
        "financial_bundle_all_five_rows": int(financial["all_five_available"].fillna(False).astype(bool).sum()),
        "financial_bundle_period_strata": dict(Counter(financial["bundle_period_stratum"].fillna("<NA>").astype(str))),
    }
    trading_window = trading_panel_key_crosswalk(history_dir, panel)
    unions = {
        "panel": panel_codes,
        "annual_report": set(inventory["annual_index_code_union"]),
        "quarterly_report": set(inventory["quarterly_index_code_union"]),
        "ratio": set(ratio["code_union"]),
        "trading": trading_codes,
        "issued": issued_codes,
        "profile": profile_codes,
        "financial_bundle": financial_codes,
    }
    pairwise: dict[str, dict[str, Any]] = {}
    for left_name, left in unions.items():
        pairwise[left_name] = {}
        for right_name, right in unions.items():
            pairwise[left_name][right_name] = {
                "intersection": len(left & right),
                "left_only": len(left - right),
                "right_only": len(right - left),
            }
    materialized_path = output.with_name("alpha_idx_xbrl_candidate_facts_v1.jsonl")
    if reuse_xbrl and materialized_path.is_file():
        xbrl = summarize_materialized_xbrl(materialized_path, archives)
    else:
        xbrl = materialize_xbrl(archives, materialized_path, xbrl_limit)
    xbrl["semantic_collision_audit"] = xbrl_semantic_collision_audit(materialized_path)
    result = {
        "schema_version": "IDX_TRADE_AUTHORITY_CROSSWALK_V1",
        "as_of": datetime.now().astimezone().isoformat(),
        "status": "RAW_STRUCTURAL_CROSSWALK_NO_ADMISSION",
        "protected_boundary": "CLOSED",
        "inputs": {
            "staging_root": str(staging_root),
            "panel": {"path": str(panel_path), "sha256": sha256_file(panel_path)},
            "financial_bundle": {"path": str(financial_bundle_path), "sha256": sha256_file(financial_bundle_path)},
        },
        "report_surface": inventory,
        "ratio_surface": ratio,
        "trading_surface": trading,
        "trading_panel_crosswalk": trading_window,
        "issued_surface": issued,
        "profile_surface": profile,
        "current_corpus": current_rows,
        "code_universe_crosswalk": {
            "sets": {name: {"count": len(values), "codes": sorted(values)} for name, values in unions.items()},
            "pairwise_counts": pairwise,
            "residuals": {
                "trading_without_profile": sorted(trading_codes - profile_codes),
                "issued_without_profile": sorted(issued_codes - profile_codes),
                "panel_without_trading": sorted(panel_codes - trading_codes),
                "trading_without_panel": sorted(trading_codes - panel_codes),
                "annual_report_without_panel": sorted(unions["annual_report"] - panel_codes),
                "panel_without_annual_report": sorted(panel_codes - unions["annual_report"]),
                "ratio_without_panel": sorted(unions["ratio"] - panel_codes),
                "panel_without_ratio": sorted(panel_codes - unions["ratio"]),
            },
        },
        "financial_materialization": {
            "raw_report_indexes": {
                "annual_rows": inventory["annual_index_rows"],
                "quarterly_rows": inventory["quarterly_index_rows"],
                "quarterly_periods": inventory["quarterly_index_rows_by_year_period"],
            },
            "structurally_materialized_xbrl": xbrl,
            "semantically_usable": {
                "status": "NOT_CERTIFIED",
                "reason": "Concept mapping preserves values and periods but does not resolve taxonomy, units, consolidation, restatement, or revision semantics.",
            },
            "pit_usable": {
                "status": "NOT_CERTIFIED",
                "reason": "File_Modified/report period do not establish historical availability or knowledge time.",
            },
            "existing_v2_bundle": {
                "status": "SEPARATE_EXISTING_BUNDLE",
                "reason": "Existing V2 rows retain explicit reporting and knowledge-time fields; raw XBRL is not substituted into that bundle.",
            },
        },
        "authority_matrix": {
            "official_annual_report_index": "RAW_DISCOVERY_AND_COVERAGE_ONLY",
            "official_quarterly_report_index": "RAW_DISCOVERY_ONLY_Q1_H1_9M",
            "official_xbrl_projection": "STRUCTURAL_FACT_COVERAGE_ONLY",
            "official_ratio_snapshots": "RAW_SNAPSHOT_AND_FIELD_COVERAGE_ONLY",
            "official_trading_history": "RAW_DAILY_FIELD_COVERAGE_ONLY",
            "official_issued_history": "RAW_LIFECYCLE_EVENT_DISCOVERY_ONLY",
            "official_profile_detail": "CURRENT_IDENTITY_CROSSCHECK_ONLY",
            "existing_financial_v2_bundle": "CAPABILITY_DIAGNOSTICS_ONLY_UNTIL_POLICY_AND_SOURCE_AUTHORITY_CLOSED",
        },
        "findings": [
            "The annual report index and quarterly report index are broader discovery surfaces than the observed price panel; code-set overlap is not historical population completeness.",
            "The six annual index rows without a retained instance attachment remain explicit residuals; no missing archive is silently imputed from a different period or file type.",
            "The official Q1/H1/9M index rows are present, but this lane did not download quarterly XBRL, so quarterly field materialization remains an acquisition residual.",
            "The official XBRL projection is structurally useful for concept/period coverage and raw field availability, but semantic and PIT usability remain uncertified.",
            "Trading-history codes without current profiles and profile-empty codes are identity-surface residuals, not evidence of delisting, ticker reuse, or issuer continuity.",
            "The existing V2 financial bundle and new raw official surfaces must remain separate until a report-availability, revision, taxonomy, unit, and identity contract exists.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--financial-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--xbrl-limit", type=int, default=None)
    parser.add_argument("--reuse-xbrl", action="store_true")
    args = parser.parse_args()
    result = crosswalk(
        args.staging_root.resolve(),
        args.panel.resolve(),
        args.financial_bundle.resolve(),
        args.xbrl_limit,
        args.output.resolve(),
        args.reuse_xbrl,
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
