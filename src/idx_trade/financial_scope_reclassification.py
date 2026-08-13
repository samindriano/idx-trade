"""Offline statement-scope reclassification for the accepted Financial PIT census.

The runner in this module consumes only immutable local census captures.  It
does not construct a transport, make provider calls, download attachments, or
extract financial facts.  A join is PIT-ready only when the original
publication/hash chain is intact and the accepted content resolver returns an
explicit statement scope.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from .financial_pit_adapter import _choose_report_attachments
from .financial_scope_resolver import (
    ScopeResolution,
    ScopeResolutionResult,
    resolve_statement_scope,
)


PERIOD_ORDER = ("audit", "tw1", "tw2", "tw3")
PERIOD_LABELS = {"audit": "FY", "tw1": "Q1", "tw2": "H1", "tw3": "9M"}
OUTSIDE_SCOPE_STATUSES = {
    "ATTACHMENT_AMBIGUOUS",
    "ATTACHMENT_HASH_CONFLICT",
    "HTTP_FAILURE",
}


class OfflineReclassificationError(RuntimeError):
    """Raised when a local input is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class JoinClassification:
    ticker: str
    year: int
    period: str
    period_label: str
    publication_at_utc: str | None
    source_attachment_sha256: str | None
    source_chain_hashes: tuple[str, ...]
    source_refs: tuple[str, ...]
    representation_format: str
    source_attachment_path: str
    scope: str
    evidence: tuple[dict[str, str], ...]
    resolver_detail: str
    prior_chain_gates_pass: bool
    file_hash_matches_chain: bool
    pit_ready: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfflineReclassificationError(f"invalid local JSON: {path}: {exc}") from exc


def _load_report_inventory(census_root: Path) -> dict[tuple[str, int, str], list[Mapping[str, Any]]]:
    inventory: dict[tuple[str, int, str], list[Mapping[str, Any]]] = defaultdict(list)
    raw_dir = census_root / "raw"
    for path in sorted(raw_dir.glob("financial_reports_*.json")):
        try:
            payload = _load_json(path)
        except OfflineReclassificationError:
            # The accepted census contains a deliberately non-JSON hash sidecar;
            # only valid report payloads can establish an attachment path.
            continue
        stem_parts = path.stem.split("_")
        if len(stem_parts) < 4 or not stem_parts[2].isdigit():
            continue
        year = int(stem_parts[2])
        period = "_".join(stem_parts[3:])
        if not isinstance(payload, Mapping) or not isinstance(payload.get("Results"), list):
            raise OfflineReclassificationError(f"invalid report payload shape: {path}")
        for report in payload["Results"]:
            if not isinstance(report, Mapping):
                raise OfflineReclassificationError(f"invalid report row in {path}")
            ticker = str(report.get("KodeEmiten") or "").strip().upper()
            if ticker:
                inventory[(ticker, year, period)].append(report)
    return inventory


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise OfflineReclassificationError(
                        f"invalid coverage JSON at line {line_number}: {exc}"
                    ) from exc
                if not isinstance(row, dict):
                    raise OfflineReclassificationError(f"coverage row {line_number} is not an object")
                rows.append(row)
    except OSError as exc:
        raise OfflineReclassificationError(f"cannot read coverage rows: {path}: {exc}") from exc
    return rows


def _attachment_path(census_root: Path, row: Mapping[str, Any], report: Mapping[str, Any]) -> Path:
    chosen = _choose_report_attachments(report.get("Attachments") or [])
    if len(chosen) != 1:
        raise OfflineReclassificationError(
            f"expected one deterministic attachment for {row.get('ticker')} "
            f"{row.get('year')} {row.get('period')}, got {len(chosen)}"
        )
    file_path = str(chosen[0].get("File_Path") or "").strip()
    file_name = PurePosixPath(file_path).name
    if not file_name:
        raise OfflineReclassificationError(
            f"attachment has no basename for {row.get('ticker')} {row.get('year')} {row.get('period')}"
        )
    return census_root / "attachments" / (
        f"report_{row['ticker']}_{row['year']}_{row['period']}_{file_name}"
    )


def _representation(result: ScopeResolutionResult) -> str:
    return {
        "XLSX": "XLSX",
        "XBRL_ZIP": "XBRL",
        "PDF": "PDF",
    }.get(result.file_format, "UNSUPPORTED")


def _evidence_payload(result: ScopeResolutionResult) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "location": item.location,
            "evidence_kind": item.evidence_kind,
            "text": item.text,
            "scope": item.scope.value,
        }
        for item in result.evidence
    )


def _has_mixed_authoritative_scope(evidence: Iterable[Mapping[str, str]]) -> bool:
    """Return true only when one filing has both authoritative scope values."""

    scopes = {item.get("scope") for item in evidence}
    return scopes == {
        ScopeResolution.CONSOLIDATED.value,
        ScopeResolution.SEPARATE.value,
    }


def _prior_chain_gates(row: Mapping[str, Any]) -> bool:
    hashes = tuple(str(value) for value in (row.get("source_sha256") or ()) if str(value))
    refs = tuple(str(value) for value in (row.get("source_refs") or ()) if str(value))
    return bool(
        row.get("report_found")
        and row.get("announcement_found")
        and row.get("exact_attachment_join")
        and row.get("publication_at_utc")
        and len(hashes) >= 2
        and len(set(hashes)) == 1
        and refs
    )


def classify_exact_join(
    *,
    census_root: Path,
    row: Mapping[str, Any],
    report_inventory: Mapping[tuple[str, int, str], list[Mapping[str, Any]]],
) -> JoinClassification:
    ticker = str(row.get("ticker") or "").strip().upper()
    year = int(row["year"])
    period = str(row["period"])
    key = (ticker, year, period)
    reports = report_inventory.get(key, [])
    if len(reports) != 1:
        raise OfflineReclassificationError(f"local report inventory is not unique for {key}: {len(reports)}")
    path = _attachment_path(census_root, row, reports[0])
    if not path.is_file():
        raise OfflineReclassificationError(f"accepted exact join attachment is missing: {path}")
    payload = path.read_bytes()
    actual_hash = _sha256_bytes(payload)
    chain_hashes = tuple(str(value) for value in (row.get("source_sha256") or ()))
    hash_matches = actual_hash in chain_hashes and len(chain_hashes) >= 2 and len(set(chain_hashes)) == 1
    if not hash_matches:
        raise OfflineReclassificationError(
            f"local attachment hash disagrees with accepted chain for {key}: "
            f"actual={actual_hash} chain={chain_hashes}"
        )
    result = resolve_statement_scope(payload, file_name=path.name, file_type=path.suffix)
    evidence = _evidence_payload(result)
    return JoinClassification(
        ticker=ticker,
        year=year,
        period=period,
        period_label=PERIOD_LABELS.get(period, period),
        publication_at_utc=row.get("publication_at_utc"),
        source_attachment_sha256=actual_hash,
        source_chain_hashes=chain_hashes,
        source_refs=tuple(str(value) for value in (row.get("source_refs") or ())),
        representation_format=_representation(result),
        source_attachment_path=str(path.relative_to(census_root)),
        scope=result.scope.value,
        evidence=evidence,
        resolver_detail=result.detail,
        prior_chain_gates_pass=_prior_chain_gates(row),
        file_hash_matches_chain=hash_matches,
        pit_ready=_prior_chain_gates(row) and result.scope is not ScopeResolution.UNRESOLVED,
    )


def _classification_json(item: JoinClassification) -> dict[str, Any]:
    value = asdict(item)
    value["source_chain_hashes"] = list(item.source_chain_hashes)
    value["source_refs"] = list(item.source_refs)
    value["evidence"] = list(item.evidence)
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_offline_reclassification(
    *, census_root: str | Path, output_root: str | Path
) -> dict[str, Any]:
    """Apply scope resolution to all accepted exact joins and write artifacts."""

    census = Path(census_root)
    output = Path(output_root)
    rows_path = census / "coverage_rows.jsonl"
    source_manifest = census / "MANIFEST__rerun_v6.json"
    if not census.is_dir() or not rows_path.is_file() or not source_manifest.is_file():
        raise OfflineReclassificationError("accepted census root is incomplete")
    if output.exists() and any(output.iterdir()):
        raise OfflineReclassificationError(f"output directory must be new and empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    all_rows = _load_rows(rows_path)
    exact_rows = [row for row in all_rows if row.get("exact_attachment_join")]
    if len(exact_rows) != 6108:
        raise OfflineReclassificationError(f"expected 6108 exact joins, found {len(exact_rows)}")
    inventory = _load_report_inventory(census)
    classified = [
        classify_exact_join(census_root=census, row=row, report_inventory=inventory)
        for row in sorted(exact_rows, key=lambda item: (int(item["year"]), str(item["period"]), str(item["ticker"])))
    ]

    scope_counts = Counter(item.scope for item in classified)
    representation_counts = Counter(item.representation_format for item in classified)
    mixed_conflicts = sum(_has_mixed_authoritative_scope(item.evidence) for item in classified)
    period_rows: dict[tuple[int, str], list[JoinClassification]] = defaultdict(list)
    for item in classified:
        period_rows[(item.year, item.period)].append(item)
    all_period_rows: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        all_period_rows[(int(row["year"]), str(row["period"]))].append(row)

    by_period = []
    for (year, period), full_group in sorted(all_period_rows.items()):
        group = period_rows.get((year, period), [])
        by_period.append(
            {
                "year": year,
                "period": period,
                "period_label": PERIOD_LABELS.get(period, period),
                "expected_issuer_periods": len(full_group),
                "exact_attachment_joins": len(group),
                "consolidated": sum(item.scope == ScopeResolution.CONSOLIDATED.value for item in group),
                "separate": sum(item.scope == ScopeResolution.SEPARATE.value for item in group),
                "unresolved": sum(item.scope == ScopeResolution.UNRESOLVED.value for item in group),
                "mixed_conflicting_authoritative_scope": sum(
                    _has_mixed_authoritative_scope(item.evidence) for item in group
                ),
                "pit_ready": sum(item.pit_ready for item in group),
                "pit_ready_percentage_of_expected_issuer_periods": round(
                    100 * sum(item.pit_ready for item in group) / len(full_group), 6
                ),
                "outside_scope_or_prior_gate_failures": len(full_group) - len(group),
            }
        )

    output_rows = output / "scope_reclassification_rows.jsonl"
    with output_rows.open("w", encoding="utf-8", newline="\n") as handle:
        for item in classified:
            handle.write(json.dumps(_classification_json(item), sort_keys=True) + "\n")
    summary = {
        "contract": "FINANCIAL_PIT_OFFLINE_SCOPE_RECLASSIFICATION_V1",
        "input": {
            "coverage_rows": str(rows_path),
            "coverage_rows_sha256": sha256_file(rows_path),
            "source_manifest": str(source_manifest),
            "source_manifest_sha256": sha256_file(source_manifest),
            "total_rows": len(all_rows),
            "exact_attachment_joins": len(classified),
        },
        "scope_counts": {
            "CONSOLIDATED": scope_counts[ScopeResolution.CONSOLIDATED.value],
            "SEPARATE": scope_counts[ScopeResolution.SEPARATE.value],
            "UNRESOLVED": scope_counts[ScopeResolution.UNRESOLVED.value],
            "mixed_conflicting_authoritative_scope": mixed_conflicts,
        },
        "representation_counts": {
            "XLSX": representation_counts["XLSX"],
            "XBRL": representation_counts["XBRL"],
            "PDF": representation_counts["PDF"],
            "unsupported": representation_counts["UNSUPPORTED"],
        },
        "pit_ready": {
            "count": sum(item.pit_ready for item in classified),
            "percentage_of_exact_joins": round(
                100 * sum(item.pit_ready for item in classified) / len(classified), 6
            ),
            "percentage_of_all_expected_issuer_periods": round(
                100 * sum(item.pit_ready for item in classified) / len(all_rows), 6
            ),
        },
        "outside_exact_join_set": {
            "ATTACHMENT_AMBIGUOUS": sum(row.get("status") == "ATTACHMENT_AMBIGUOUS" for row in all_rows),
            "ATTACHMENT_HASH_CONFLICT": sum(row.get("status") == "ATTACHMENT_HASH_CONFLICT" for row in all_rows),
            "HTTP_FAILURE": sum(row.get("status") == "HTTP_FAILURE" for row in all_rows),
            "publication_or_attachment_linkage_gaps": sum(
                row.get("status") in {"REPORT_NOT_FOUND", "ATTACHMENT_NOT_MATCHED"} for row in all_rows
            ),
        },
        "by_year_period": by_period,
        "resolver_contract": {
            "explicit_scope_required": True,
            "scope_values": ["CONSOLIDATED", "SEPARATE", "UNRESOLVED"],
            "financial_fact_extraction": False,
            "network_calls": False,
        },
    }
    summary_path = output / "scope_reclassification_summary.json"
    _write_json(summary_path, summary)
    manifest = {
        "contract": summary["contract"],
        "scope_reclassification_rows": {
            "path": output_rows.name,
            "sha256": sha256_file(output_rows),
            "rows": len(classified),
        },
        "summary": {
            "path": summary_path.name,
            "sha256": sha256_file(summary_path),
        },
        "input": summary["input"],
        "scope_counts": summary["scope_counts"],
        "representation_counts": summary["representation_counts"],
        "pit_ready": summary["pit_ready"],
    }
    manifest_path = output / "MANIFEST.json"
    _write_json(manifest_path, manifest)
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    _write_json(output / "MANIFEST_SHA256.json", {"sha256": manifest["manifest_sha256"]})
    return {"output_root": str(output), "manifest": manifest, "summary": summary}
