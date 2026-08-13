"""Recover exact current-period boundaries from accepted IDX filings.

This is an offline provenance sidecar.  It intentionally does not derive
dates from fiscal labels, filenames, publication dates, or report years.  The
only accepted XLSX evidence is the visible IDX metadata sheet's current-period
date cells.  The only accepted inline-XBRL evidence is the explicit IDX-DEI
current-period date fact in the current-year context.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .financial_fact_table import _visible_xlsx_cells


CONTRACT_VERSION = "financial_period_boundaries_v1"
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
)
_DATE_LABELS = {
    "tanggal awal periode berjalan": "duration_start",
    "current period start date": "duration_start",
    "tanggal akhir periode berjalan": "duration_end",
    "current period end date": "duration_end",
}
_NON_NUMERIC = re.compile(
    r"<ix:nonNumeric\b(?P<attrs>[^>]*)>(?P<body>.*?)</ix:nonNumeric\s*>",
    re.IGNORECASE | re.DOTALL,
)
_ATTR = re.compile(r"(?P<key>[A-Za-z_:][\w:.-]*)\s*=\s*(?P<q>[\"'])(?P<value>.*?)(?P=q)", re.DOTALL)
_TAG = re.compile(r"<[^>]+>")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _norm(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip().casefold()


def _parse_date(value: Any) -> str | None:
    text = html.unescape(str(value or "")).strip()
    text = _TAG.sub("", text)
    text = " ".join(text.split())
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _attachment_path(attachments_root: Path, source_attachment_path: str) -> Path:
    # The accepted diagnostics use an external relative path such as
    # attachments\\report_AADI_....  Only its basename is resolved under the
    # already accepted immutable attachment root.
    name = str(source_attachment_path or "").replace("\\", "/").split("/")[-1]
    return attachments_root / name


def _same_row_date_candidates(cells: list[Any], label: Any) -> list[tuple[Any, str]]:
    """Return all parseable same-row date cells, on either side of label."""

    return sorted(
        ((cell, parsed) for cell in cells if cell.sheet == label.sheet and cell.row == label.row and cell is not label and cell.value.strip() for parsed in [_parse_date(cell.value)] if parsed),
        key=lambda item: item[0].column,
    )


def _xlsx_boundaries(payload: bytes) -> dict[str, Any]:
    cells, _ = _visible_xlsx_cells(payload)
    metadata = [cell for cell in cells if cell.sheet == "1000000"]
    evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    values: dict[str, set[str]] = defaultdict(set)
    for label in metadata:
        kind = _DATE_LABELS.get(_norm(label.value))
        if kind is None:
            continue
        candidates = _same_row_date_candidates(metadata, label)
        if not candidates:
            evidence[kind].append({
                "source_location": f"sheet=1000000;label_cell={label.coordinate}",
                "label": label.value,
                "status": "MISSING_DATE_VALUE",
            })
            continue
        for value_cell, parsed in candidates:
            location = {
                "source_location": f"sheet=1000000;label_cell={label.coordinate};value_cell={value_cell.coordinate}",
                "label": label.value,
                "value": value_cell.value,
            }
            location["date"] = parsed
            location["status"] = "RECOVERED"
            evidence[kind].append(location)
            values[kind].add(parsed)

    def resolve(kind: str) -> tuple[str | None, str, tuple[dict[str, Any], ...]]:
        rows = tuple(evidence.get(kind, ()))
        dates = values.get(kind, set())
        if len(dates) == 1 and rows and all(row.get("status") == "RECOVERED" for row in rows):
            return next(iter(dates)), "RECOVERED", rows
        if len(dates) > 1:
            return None, "CONFLICTING_DATE_EVIDENCE", rows
        if rows:
            return None, "INVALID_OR_MISSING_DATE", rows
        return None, "MISSING_DATE_EVIDENCE", rows

    start, start_status, start_evidence = resolve("duration_start")
    end, end_status, end_evidence = resolve("duration_end")
    instant = end if end_status == "RECOVERED" else None
    instant_status = "RECOVERED" if instant else end_status
    duration_status = "RECOVERED" if start and end else (
        "CONFLICTING_DATE_EVIDENCE" if "CONFLICTING_DATE_EVIDENCE" in {start_status, end_status} else "MISSING_OR_INVALID_BOUNDARY"
    )
    if start and end and date.fromisoformat(start) >= date.fromisoformat(end):
        # Preserve the exact source evidence, but do not expose an impossible
        # duration boundary as recovered.  The end date remains usable as the
        # instant boundary because it is independently authoritative.
        start = None
        duration_status = "INVALID_BOUNDARY_CHRONOLOGY"
    return {
        "instant_date": instant,
        "period_start": start,
        "period_end": end,
        "instant_status": instant_status,
        "duration_status": duration_status,
        "instant_evidence": list(end_evidence),
        "duration_evidence": list(start_evidence + end_evidence),
        "evidence_kind": "xlsx_visible_1000000_current_period_date_cells",
    }


def _attrs(raw: str) -> dict[str, str]:
    return {match.group("key"): html.unescape(match.group("value")) for match in _ATTR.finditer(raw)}


def _xbrl_boundaries(payload: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        html_names = [name for name in archive.namelist() if name.lower().endswith((".html", ".xhtml"))]
        start_rows: list[dict[str, Any]] = []
        end_rows: list[dict[str, Any]] = []
        for name in sorted(html_names):
            text = archive.read(name).decode("utf-8", "ignore")
            namespace_match = re.search(
                r'xmlns:idx-dei=["\']https?://www\.idx\.co\.id/xbrl/taxonomy/\d{4}-\d{2}-\d{2}/dei["\']',
                text,
                re.IGNORECASE,
            )
            if namespace_match is None:
                continue
            for ordinal, match in enumerate(_NON_NUMERIC.finditer(text), start=1):
                attrs = _attrs(match.group("attrs"))
                context = attrs.get("contextRef", "")
                fact_name = attrs.get("name", "")
                if context != "CurrentYearInstant":
                    continue
                body = _TAG.sub("", html.unescape(match.group("body")))
                body = " ".join(body.split())
                row = {
                    "source_location": f"{name};tag=ix:nonNumeric;name={fact_name};contextRef={context};occurrence={ordinal}",
                    "name": fact_name,
                    "context_ref": context,
                    "value": body,
                }
                if fact_name == "idx-dei:CurrentPeriodStartDate":
                    parsed = _parse_date(body)
                    row["date"] = parsed
                    row["status"] = "RECOVERED" if parsed else "INVALID_DATE_VALUE"
                    start_rows.append(row)
                elif fact_name == "idx-dei:CurrentPeriodEndDate":
                    parsed = _parse_date(body)
                    row["date"] = parsed
                    row["status"] = "RECOVERED" if parsed else "INVALID_DATE_VALUE"
                    end_rows.append(row)

    def resolve(rows: list[dict[str, Any]]) -> tuple[str | None, str, tuple[dict[str, Any], ...]]:
        dates = {row["date"] for row in rows if row.get("status") == "RECOVERED" and row.get("date")}
        if len(dates) == 1:
            return next(iter(dates)), "RECOVERED", tuple(rows)
        if len(dates) > 1:
            return None, "CONFLICTING_DATE_EVIDENCE", tuple(rows)
        return None, "MISSING_OR_INVALID_BOUNDARY", tuple(rows)

    start, start_status, start_evidence = resolve(start_rows)
    end, end_status, end_evidence = resolve(end_rows)
    instant = end if end_status == "RECOVERED" else None
    duration_status = "RECOVERED" if start and end else "MISSING_OR_INVALID_BOUNDARY"
    if start and end and date.fromisoformat(start) >= date.fromisoformat(end):
        start = None
        duration_status = "INVALID_BOUNDARY_CHRONOLOGY"
    return {
        "instant_date": instant,
        "period_start": start,
        "period_end": end,
        "instant_status": "RECOVERED" if instant else end_status,
        "duration_status": duration_status,
        "instant_evidence": list(end_evidence),
        "duration_evidence": list(start_evidence + end_evidence),
        "evidence_kind": "xbrl_idx_dei_current_period_date_facts",
    }


def recover_period_boundary_rows(
    filing_diagnostics_path: Path,
    attachments_root: Path,
    *,
    output_root: Path | None = None,
    fact_records_path: Path | None = None,
) -> dict[str, Any]:
    diagnostics = [json.loads(line) for line in filing_diagnostics_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if fact_records_path is not None and not fact_records_path.is_file():
        raise FileNotFoundError(fact_records_path)
    rows: list[dict[str, Any]] = []
    for diagnostic in diagnostics:
        source_path = str(diagnostic.get("source_attachment_path") or "")
        path = _attachment_path(attachments_root, source_path)
        expected_sha = str(diagnostic.get("source_attachment_sha256") or diagnostic.get("attachment_sha256") or "").lower()
        base = {
            "version_id": diagnostic.get("version_id"),
            "ticker": diagnostic.get("ticker"),
            "fiscal_year": diagnostic.get("fiscal_year"),
            "fiscal_period": diagnostic.get("fiscal_period"),
            "normalized_period": {"tw1": "Q1", "tw2": "H1", "tw3": "9M", "audit": "FY"}.get(str(diagnostic.get("fiscal_period", "")).lower()),
            "statement_scope": diagnostic.get("scope") or diagnostic.get("statement_scope"),
            "industry_class": diagnostic.get("industry_class") or diagnostic.get("template_or_industry_family"),
            "template_or_industry_family": diagnostic.get("template_or_industry_family") or diagnostic.get("industry_class"),
            "representation_format": diagnostic.get("representation_format"),
            "attachment_sha256": expected_sha,
            "source_attachment_path": source_path,
            "source_file_sha256": None,
            "status": "UNRESOLVED_SOURCE",
            "source_evidence": [],
        }
        if not path.is_file():
            base["status"] = "SOURCE_FILE_MISSING"
            rows.append(base)
            continue
        source_sha = _sha256_file(path)
        base["source_file_sha256"] = source_sha
        if expected_sha != source_sha:
            base["status"] = "SOURCE_HASH_MISMATCH"
            rows.append(base)
            continue
        payload = path.read_bytes()
        try:
            evidence = _xlsx_boundaries(payload) if path.suffix.casefold() == ".xlsx" else _xbrl_boundaries(payload) if path.suffix.casefold() == ".zip" else None
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            base["status"] = "SOURCE_PARSE_ERROR"
            base["detail"] = str(exc)
            rows.append(base)
            continue
        if evidence is None:
            base["status"] = "UNSUPPORTED_FORMAT"
            rows.append(base)
            continue
        base.update(evidence)
        base["status"] = "RECOVERED" if base["instant_status"] == "RECOVERED" and base["duration_status"] == "RECOVERED" else "PARTIAL_OR_UNRESOLVED"
        rows.append(base)

    coverage: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        key = "|".join(str(row.get(field) or "UNKNOWN") for field in ("fiscal_year", "normalized_period", "statement_scope", "representation_format", "template_or_industry_family"))
        coverage[key]["versions"] += 1
        coverage[key]["instant_recovered"] += row.get("instant_status") == "RECOVERED"
        coverage[key]["duration_recovered"] += row.get("duration_status") == "RECOVERED"
        coverage[key]["fully_recovered"] += row.get("status") == "RECOVERED"
    summary = {
        "status": "FINANCIAL_PIT_PERIOD_BOUNDARY_SIDECAR_AUDIT",
        "contract_version": CONTRACT_VERSION,
        "source_diagnostics": {"path": str(filing_diagnostics_path), "sha256": _sha256_file(filing_diagnostics_path)},
        "source_fact_records": {"path": str(fact_records_path), "sha256": _sha256_file(fact_records_path)} if fact_records_path else None,
        "attachments_root": str(attachments_root),
        "total_versions": len(rows),
        "representation_counts": dict(Counter(str(row.get("representation_format") or "UNKNOWN") for row in rows)),
        "status_counts": dict(Counter(str(row.get("status")) for row in rows)),
        "instant_status_counts": dict(Counter(str(row.get("instant_status")) for row in rows)),
        "duration_status_counts": dict(Counter(str(row.get("duration_status")) for row in rows)),
        "coverage_by_year_period_scope_representation_template": {key: dict(sorted(value.items())) for key, value in sorted(coverage.items())},
        "network_calls": 0,
        "redownloads": 0,
        "protected_outcomes_accessed": False,
        "feature_values_materialized": False,
        "model_work": False,
    }
    if output_root is not None:
        if output_root.exists() and any(output_root.iterdir()):
            raise ValueError(f"output root must be new and empty: {output_root}")
        output_root.mkdir(parents=True, exist_ok=True)
        sidecar_path = output_root / "period_boundaries.jsonl"
        sidecar_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
        summary["artifact_hashes"] = {"period_boundaries.jsonl": _sha256_file(sidecar_path)}
        summary_path = output_root / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest = {
            "manifest_version": f"{CONTRACT_VERSION}_sidecar",
            "files": {
                "period_boundaries.jsonl": {"bytes": sidecar_path.stat().st_size, "sha256": _sha256_file(sidecar_path)},
                "summary.json": {"bytes": summary_path.stat().st_size, "sha256": _sha256_file(summary_path)},
            },
            "source_diagnostics": summary["source_diagnostics"],
            "source_fact_records": summary["source_fact_records"],
            "total_versions": len(rows),
            "network_calls": 0,
            "protected_outcomes_accessed": False,
        }
        manifest_path = output_root / "MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary["artifact_hashes"]["summary.json"] = _sha256_file(summary_path)
        summary["artifact_hashes"]["MANIFEST.json"] = _sha256_file(manifest_path)
    return summary


def validate_period_sidecar(
    sidecar_path: Path,
    manifest_path: Path,
    filing_diagnostics_path: Path,
    fact_records_path: Path,
) -> dict[str, Any]:
    """Validate the sidecar as an exact, manifest-pinned filing join."""

    sidecar_rows = [json.loads(line) for line in sidecar_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    diagnostics = [json.loads(line) for line in filing_diagnostics_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    diagnostic_by_id = {str(row.get("version_id") or ""): row for row in diagnostics}
    if len(diagnostic_by_id) != len(diagnostics):
        raise ValueError("diagnostics contain duplicate or missing version_id")
    sidecar_by_id: dict[str, Mapping[str, Any]] = {}
    for row in sidecar_rows:
        version_id = str(row.get("version_id") or "")
        if not version_id or version_id in sidecar_by_id:
            raise ValueError(f"sidecar contains duplicate or missing version_id: {version_id}")
        sidecar_by_id[version_id] = row
    if set(sidecar_by_id) != set(diagnostic_by_id):
        missing = sorted(set(diagnostic_by_id) - set(sidecar_by_id))[:5]
        extra = sorted(set(sidecar_by_id) - set(diagnostic_by_id))[:5]
        raise ValueError(f"sidecar/diagnostic key-set mismatch; missing={missing}, extra={extra}")

    def iso_date(value: Any, field: str) -> date:
        text = str(value or "")
        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"invalid {field}: {value!r}") from exc

    complete = 0
    for version_id, row in sidecar_by_id.items():
        diagnostic = diagnostic_by_id[version_id]
        expected_sha = str(diagnostic.get("source_attachment_sha256") or diagnostic.get("attachment_sha256") or "").lower()
        for field in ("ticker", "fiscal_year", "fiscal_period", "statement_scope", "representation_format", "attachment_sha256"):
            if str(row.get(field) or "").upper() != str((diagnostic.get("scope") if field == "statement_scope" else diagnostic.get(field) or expected_sha) or "").upper():
                raise ValueError(f"sidecar metadata mismatch for {version_id}: {field}")
        normalized = {"tw1": "Q1", "tw2": "H1", "tw3": "9M", "audit": "FY"}.get(str(row.get("fiscal_period") or "").casefold())
        if row.get("normalized_period") != normalized:
            raise ValueError(f"sidecar normalized period mismatch for {version_id}")
        if str(row.get("source_file_sha256") or "").lower() != expected_sha:
            raise ValueError(f"sidecar source byte hash mismatch for {version_id}")
        instant = row.get("instant_date")
        start = row.get("period_start")
        end = row.get("period_end")
        if instant:
            iso_date(instant, "instant_date")
        if start:
            iso_date(start, "period_start")
        if end:
            iso_date(end, "period_end")
        if instant and end and instant != end:
            raise ValueError(f"instant/end disagreement for {version_id}")
        if start and end and date.fromisoformat(start) >= date.fromisoformat(end):
            raise ValueError(f"duration boundary chronology invalid for {version_id}")
        if row.get("instant_status") == "RECOVERED":
            if not instant or not row.get("instant_evidence") or not all(item.get("source_location") for item in row["instant_evidence"]):
                raise ValueError(f"recovered instant lacks exact evidence for {version_id}")
        if row.get("duration_status") == "RECOVERED":
            if not start or not end or not row.get("duration_evidence") or not all(item.get("source_location") for item in row["duration_evidence"]):
                raise ValueError(f"recovered duration lacks exact evidence for {version_id}")
            complete += 1

    fact_version_ids: set[str] = set()
    with fact_records_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                fact_version_ids.add(str(json.loads(line).get("version_id") or ""))
    if not fact_version_ids <= set(diagnostic_by_id):
        raise ValueError("fact records contain version IDs absent from diagnostics")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files") or {}
    pinned_sidecar = str((files.get(sidecar_path.name) or {}).get("sha256") or "").lower()
    actual_sidecar = _sha256_file(sidecar_path)
    if pinned_sidecar != actual_sidecar:
        raise ValueError("period sidecar manifest hash mismatch")
    if (manifest.get("source_diagnostics") or {}).get("sha256") != _sha256_file(filing_diagnostics_path):
        raise ValueError("manifest diagnostic source hash mismatch")
    if (manifest.get("source_fact_records") or {}).get("sha256") != _sha256_file(fact_records_path):
        raise ValueError("manifest fact source hash mismatch")
    return {
        "total_versions": len(sidecar_rows),
        "fully_recovered_duration_versions": complete,
        "sidecar_sha256": actual_sidecar,
        "manifest_sha256": _sha256_file(manifest_path),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostics", type=Path, required=True)
    parser.add_argument("--attachments-root", type=Path, required=True)
    parser.add_argument("--fact-records", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = recover_period_boundary_rows(args.diagnostics, args.attachments_root, output_root=args.output_root, fact_records_path=args.fact_records)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["CONTRACT_VERSION", "recover_period_boundary_rows"]
