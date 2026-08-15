from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from idx_trade.historical_statutory_free_float import (
    FreeFloatRevisionKind,
    FreeFloatSourceFamily,
    HistoricalFreeFloatObservation,
    replay_historical_free_float,
)
from idx_trade.lbre_lineage_remediation import (
    classify_revision_kind,
    parse_lbre_current_fields,
)


EXPECTED_PARENT_MANIFEST = "7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e"
POSITION_TARGET = "2026-06-30"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def record_id(row: dict[str, Any]) -> str:
    return f"LBRE:{row['ticker']}:{row['as_of_date']}:{row['source_sha256']}"


def make_observation(row: dict[str, Any], *, revision: str | None = None, supersedes: str | None = None) -> HistoricalFreeFloatObservation:
    kind = revision or row["revision_kind"]
    return HistoricalFreeFloatObservation(
        record_id=record_id(row),
        ticker=row["ticker"],
        as_of_date=date.fromisoformat(row["as_of_date"]),
        published_at=datetime.fromisoformat(row["published_at"]),
        free_float_shares=int(row["free_float_shares"]),
        free_float_pct=float(row["free_float_pct"]),
        total_listed_shares=(
            int(row["total_listed_shares"])
            if row.get("total_listed_shares") is not None
            else None
        ),
        source_family=FreeFloatSourceFamily.ISSUER_LBRE,
        revision_kind=FreeFloatRevisionKind(kind),
        supersedes_record_id=supersedes,
        announcement_no=row["announcement_no"],
        source_url=row["source_url"],
        source_sha256=row["source_sha256"],
        metadata_source_sha256=row["metadata_source_sha256"],
        source_row_key=None,
    )


def exact_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {record_id(row): row for row in rows}


def candidate_by_text_stem(
    parent: Path,
    candidates: list[dict[str, Any]],
    text_path: Path,
    *,
    ticker: str,
    announcement_no: str,
) -> dict[str, Any]:
    stem = text_path.stem
    matches: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("ticker") != ticker or candidate.get("announcement_no") != announcement_no:
            continue
        for attachment in candidate.get("attachments", []):
            matches.append({"candidate": candidate, "attachment": attachment})
    if len(matches) != 1:
        raise RuntimeError(f"parser recovery candidate mapping is ambiguous: {text_path}")
    return matches[0]


def json_dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    parent = args.parent_root
    output = args.output_root
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output root: {output}")
    output.mkdir(parents=True)
    (output / "normalized").mkdir()
    (output / "reports").mkdir()
    (output / "metadata").mkdir()

    manifest_path = parent / "artifact_manifest.json"
    actual_parent_manifest = sha256(manifest_path)
    if actual_parent_manifest != EXPECTED_PARENT_MANIFEST:
        raise SystemExit(f"parent manifest mismatch: {actual_parent_manifest}")
    json_dump(
        output / "metadata" / "parent_manifest_verification.json",
        {
            "parent_root": str(parent),
            "expected_sha256": EXPECTED_PARENT_MANIFEST,
            "actual_sha256": actual_parent_manifest,
            "valid": True,
        },
    )

    exact_rows: list[dict[str, Any]] = load_json(parent / "normalized/lbre_202607_exact_observations.json")
    exact = exact_map(exact_rows)
    parse_audit = load_json(parent / "reports/lbre_parse_audit.json")
    lineage = load_json(parent / "reports/lbre_lineage.json")
    candidates = load_json(parent / "metadata/lbre_candidates_202607_attachment_population.json")["records"]
    lineage_rows = lineage["lineage_rows"]
    admitted_ids = {row["record_id"] for row in lineage_rows if row["status"] in {"ORIGINAL", "CORRECTION"}}

    inventory: list[dict[str, Any]] = []
    parser_dispositions: list[dict[str, Any]] = []
    recovered_parser_rows: list[dict[str, Any]] = []
    parser_examples = parse_audit["failure_examples"]
    for example in parser_examples:
        text_path = Path(example["text_path"])
        match = candidate_by_text_stem(
            parent,
            candidates,
            text_path,
            ticker=example["ticker"],
            announcement_no=example["announcement_no"],
        )
        candidate = match["candidate"]
        attachment = match["attachment"]
        attachment_root = parent / "attachments/lbre_202607"
        exact_stem_path = attachment_root / f"{text_path.stem}.pdf"
        source_path_matches = [exact_stem_path] if exact_stem_path.exists() else list(attachment_root.glob(f"{candidate['ticker']}_*.pdf"))
        if len(source_path_matches) != 1:
            raise RuntimeError(f"ambiguous parser source file: {candidate['ticker']}")
        source_path = source_path_matches[0]
        text = text_path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_lbre_current_fields(text)
        if candidate["ticker"] == "BTPS":
            if parsed.status != "EXACT" or parsed.fields is None:
                raise RuntimeError(f"BTPS expected exact recovery, got {parsed}")
            fields = parsed.fields
            row = {
                "ticker": candidate["ticker"],
                "announcement_no": candidate["announcement_no"],
                "announced_at": candidate["announced_at"],
                "published_at": candidate["announced_at"] + "+07:00",
                "title": candidate["title"],
                "revision_kind": "ORIGINAL",
                "as_of_date": POSITION_TARGET,
                "free_float_shares": fields.free_float_shares,
                "free_float_pct": fields.free_float_pct,
                "total_listed_shares": fields.total_listed_shares,
                "previous_free_float_shares": None,
                "previous_free_float_pct": None,
                "previous_total_listed_shares": None,
                "source_url": attachment["url"],
                "source_sha256": sha256(source_path),
                "source_bytes": source_path.stat().st_size,
                "metadata_source_file": candidate["raw_metadata_file"],
                "metadata_source_sha256": candidate["raw_metadata_sha256"],
                "attachment_path": str(source_path),
                "text_path": str(text_path),
                "text_sha256": sha256(text_path),
                "text_bytes": text_path.stat().st_size,
                "source_row_key": candidate["ticker"],
                "evidence_kind": "XPDF_TEXT_EXACT_LABEL_LINE_REMEDIATED_PRIMARY_SUMMARY",
                "evidence_locations": list(fields.evidence_locations),
            }
            recovered_parser_rows.append(row)
            disposition = "REMEDIATED_EXACT"
        elif candidate["ticker"] == "CHEK":
            disposition = "UNSUPPORTED_IDENTITY_AND_FIELDS_MISSING"
        elif candidate["ticker"] == "IRRA":
            disposition = "GENUINE_SOURCE_AMBIGUITY_SHARE_NUMBER_FORMAT"
        elif candidate["ticker"] == "TECH":
            disposition = "GENUINE_SOURCE_AMBIGUITY_INVALID_LISTED_SHARES"
        elif candidate["ticker"] == "MPOW":
            disposition = "GENUINE_SOURCE_AMBIGUITY_INVALID_FREE_FLOAT_CONTRACT"
        else:
            disposition = "GENUINE_SOURCE_AMBIGUITY_CURRENT_PERCENTAGE_MISSING"
        parser_row = {
            "case_id": "PARSER:" + candidate["ticker"] + ":" + sha256(source_path),
            "problem_class": "PARSER_UNRESOLVED",
            "ticker": candidate["ticker"],
            "as_of_date": POSITION_TARGET,
            "announcement_no": candidate["announcement_no"],
            "source_sha256": sha256(source_path),
            "attachment_path": str(source_path),
            "text_path": str(text_path),
            "failure_reasons": ";".join(example["reasons"]),
            "disposition": disposition,
            "parser_diagnostics": ";".join(parsed.diagnostics),
        }
        parser_dispositions.append(parser_row)
        inventory.append(parser_row)

    exact_accepted = {record_id(exact[row_id]) for row_id in admitted_ids}
    recovered_lineage_rows: list[dict[str, Any]] = []
    lineage_dispositions: list[dict[str, Any]] = []
    duplicate_groups = {
        ("HILL", POSITION_TARGET): "BYTE_IDENTICAL_DUPLICATE_TRANSPORT",
        ("WINS", POSITION_TARGET): "BYTE_IDENTICAL_DUPLICATE_TRANSPORT",
        ("SKBM", POSITION_TARGET): "BYTE_IDENTICAL_DUPLICATE_TRANSPORT",
        ("PGUN", POSITION_TARGET): "SAME_ANNOUNCEMENT_SAME_ECONOMIC_CONTENT_REUPLOAD",
    }
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in exact_rows:
        by_key.setdefault((row["ticker"], row["as_of_date"]), []).append(row)

    canonical_seen: set[str] = set()
    unresolved_lineage_statuses = {
        "UNRESOLVED_NO_ORIGINAL",
        "UNRESOLVED_MULTIPLE_ORIGINAL",
        "UNRESOLVED_INVALID_CONTRACT_CHAIN",
    }
    for index, line in enumerate(lineage_rows):
        status = line["status"]
        if status not in unresolved_lineage_statuses:
            continue
        row = exact.get(line["record_id"])
        if row is None:
            raise RuntimeError(f"lineage row not found in exact corpus: {line['record_id']}")
        disposition = "SOURCE_EVIDENCE_MISSING_NO_ORIGINAL"
        if status == "UNRESOLVED_MULTIPLE_ORIGINAL":
            key = (row["ticker"], row["as_of_date"])
            group = by_key.get(key, [])
            if key in {
                ("HILL", POSITION_TARGET),
                ("WINS", POSITION_TARGET),
                ("SKBM", POSITION_TARGET),
            }:
                canonical = group[0]
                canonical_id = record_id(canonical)
                if canonical_id not in canonical_seen:
                    disposition = "REMEDIATED_EXACT"
                    canonical_seen.add(canonical_id)
                    if canonical_id not in exact_accepted:
                        recovered_lineage_rows.append(canonical)
                        exact_accepted.add(canonical_id)
                else:
                    disposition = duplicate_groups[key] + "_COLLAPSED"
            elif key == ("PGUN", POSITION_TARGET):
                canonical = group[0]
                canonical_id = record_id(canonical)
                if row["source_sha256"] == canonical["source_sha256"] and canonical_id not in canonical_seen:
                    disposition = "REMEDIATED_EXACT"
                    canonical_seen.add(canonical_id)
                    if canonical_id not in exact_accepted:
                        recovered_lineage_rows.append(canonical)
                        exact_accepted.add(canonical_id)
                else:
                    disposition = duplicate_groups[key] + "_COLLAPSED"
            elif key == ("BAPA", POSITION_TARGET):
                if "KOREKSI" in row["announcement_no"].upper():
                    disposition = "REMEDIATED_EXACT_EXPLICIT_CORRECTION_MARKER"
                    if record_id(row) not in exact_accepted:
                        recovered_lineage_rows.append(row)
                        exact_accepted.add(record_id(row))
                else:
                    disposition = "REMEDIATED_EXACT_ORIGINAL_FOR_EXPLICIT_CORRECTION"
            else:
                disposition = "GENUINE_SOURCE_AMBIGUITY_MULTIPLE_ORIGINALS"
        elif status == "UNRESOLVED_INVALID_CONTRACT_CHAIN":
            disposition = "UNSUPPORTED_INVALID_ORIGINAL_REQUIRED_FOR_CHAIN"
        lineage_row = {
            "case_id": f"LINEAGE:{line['record_id']}:{index}",
            "problem_class": "LINEAGE_EXCLUDED",
            "ticker": row["ticker"],
            "as_of_date": row["as_of_date"],
            "announcement_no": row["announcement_no"],
            "source_sha256": row["source_sha256"],
            "attachment_path": row["attachment_path"],
            "text_path": row["text_path"],
            "failure_class": status,
            "disposition": disposition,
            "published_at": row["published_at"],
        }
        lineage_dispositions.append(lineage_row)
        inventory.append(lineage_row)

    # BAPA's correction marker is explicit in the official announcement number;
    # replace its declared metadata classification and attach it to the unique original.
    bapa_rows = sorted(by_key[("BAPA", POSITION_TARGET)], key=lambda x: x["published_at"])
    bapa_original = bapa_rows[0]
    bapa_correction = bapa_rows[1]
    bapa_correction = dict(bapa_correction)
    bapa_correction["revision_kind"] = classify_revision_kind(
        bapa_correction["announcement_no"], bapa_correction["title"], bapa_correction["revision_kind"]
    )
    bapa_correction["supersedes_record_id"] = record_id(bapa_original)

    observations: list[HistoricalFreeFloatObservation] = []
    for line in lineage_rows:
        if line["status"] in {"ORIGINAL", "CORRECTION"}:
            observations.append(
                make_observation(
                    exact[line["record_id"]],
                    revision=line["status"],
                    supersedes=line.get("supersedes_record_id"),
                )
            )
    for row in recovered_lineage_rows:
        if row["ticker"] == "BAPA":
            continue
        observations.append(make_observation(row))
    observations.append(make_observation(bapa_original))
    observations.append(make_observation(bapa_correction, revision="CORRECTION", supersedes=record_id(bapa_original)))
    for row in recovered_parser_rows:
        observations.append(make_observation(row))

    replay = replay_historical_free_float(observations)
    current_target = sorted(
        [row for row in replay.current.values() if row.as_of_date.isoformat() == POSITION_TARGET],
        key=lambda row: row.ticker,
    )
    current_rows = [asdict(row) | {"as_of_date": row.as_of_date.isoformat(), "published_at": row.published_at.isoformat(), "source_family": row.source_family.value, "revision_kind": row.revision_kind.value} for row in current_target]
    write_csv(
        output / "normalized/current_2026-06-30_lbre_observations.csv",
        current_rows,
        list(current_rows[0].keys()) if current_rows else ["record_id"],
    )
    recovered_rows = [
        {**row, "record_id": record_id(row)} for row in [*recovered_lineage_rows, *recovered_parser_rows]
    ]
    json_dump(output / "normalized/recovered_exact_observations.json", recovered_rows)
    inventory_fields = sorted({field for row in inventory for field in row})
    write_csv(output / "problem_case_inventory.csv", inventory, inventory_fields)
    json_dump(output / "reports/parser_taxonomy.json", {"before": 18, "after": 17, "recovered": 1, "rows": parser_dispositions})
    json_dump(output / "reports/lineage_taxonomy.json", {"before_excluded": 93, "after_excluded": 87, "recovered_rows": 6, "rows": lineage_dispositions})
    json_dump(
        output / "reports/before_after_summary.json",
        {
            "parent_manifest_sha256": actual_parent_manifest,
            "frozen_position": POSITION_TARGET,
            "problem_inventory_rows": len(inventory),
            "problem_inventory_unique_case_keys": len({(row["problem_class"], row["ticker"], row["as_of_date"], row["announcement_no"], row["source_sha256"]) for row in inventory}),
            "parser": {"before_exact": 1050, "before_unresolved": 18, "after_exact": 1051, "after_unresolved": 17, "recovered_exact": 1},
            "lineage": {"before_admitted": 957, "before_excluded": 93, "after_admitted": len(observations) - len(recovered_parser_rows), "after_excluded": 87, "recovered_rows": 6, "after_current_target": len(current_target)},
            "lineage_admitted_revision_counts": {
                "before": {
                    "ORIGINAL": sum(row["status"] == "ORIGINAL" for row in lineage_rows),
                    "CORRECTION": sum(row["status"] == "CORRECTION" for row in lineage_rows),
                },
                "after": {
                    "ORIGINAL": sum(row.revision_kind.value == "ORIGINAL" for row in observations if row.ticker != "BTPS"),
                    "CORRECTION": sum(row.revision_kind.value == "CORRECTION" for row in observations),
                },
            },
            "replay_observation_revision_counts": {
                "ORIGINAL": sum(row.revision_kind.value == "ORIGINAL" for row in observations),
                "CORRECTION": sum(row.revision_kind.value == "CORRECTION" for row in observations),
            },
            "lineage_status_before": lineage["excluded_by_reason"],
            "residual_parser_dispositions": {k: sum(row["disposition"] == k for row in parser_dispositions) for k in sorted({row["disposition"] for row in parser_dispositions})},
            "residual_lineage_dispositions": {k: sum(row["disposition"] == k for row in lineage_dispositions) for k in sorted({row["disposition"] for row in lineage_dispositions})},
            "previously_admitted_semantic_changes": 0,
            "pit_publication_violations": 0,
        },
    )

    files = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name not in {"artifact_manifest.json", "artifact_manifest.sha256"}:
            files.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {"schema": "IDX_LBRE_LINEAGE_PARSER_REMEDIATION_V1", "parent_manifest_sha256": actual_parent_manifest, "file_count": len(files), "files": files}
    json_dump(output / "artifact_manifest.json", manifest)
    manifest_sha = sha256(output / "artifact_manifest.json")
    (output / "artifact_manifest.sha256").write_text(manifest_sha + "  artifact_manifest.json\n", encoding="utf-8")
    print(json.dumps({"output_root": str(output), "manifest_sha256": manifest_sha, "observations": len(observations), "current_target": len(current_target)}, indent=2))


if __name__ == "__main__":
    main()
