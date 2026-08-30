"""Create the bounded retained decomposition for CAPITAL_RESTRUCTURING=19.

This is a local, outcome-blind decomposition of the controlling successor
ledger.  It groups retained IDX issued-share mechanics into the two observed
shapes and records why neither shape proves an old-to-new market transition.
No provider acquisition or taxonomy promotion is performed here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping


INPUT_MANIFEST_SHA256 = "f379d04f979c72d0b6f2c17ea5020cfe90f5c3e5d2dc4d24b5391a1962c22d31"
AUDIT_DATE = "2026-08-31"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field, "") for field in fields})


def verify_manifest(root: Path) -> None:
    manifest_path = root / "MANIFEST.json"
    if sha256_file(manifest_path) != INPUT_MANIFEST_SHA256:
        raise RuntimeError("controlling Phase-B manifest hash mismatch")
    manifest = read_json(manifest_path)
    for item in manifest.get("files", []):
        path = root / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"controlling file is not manifest-bound: {path}")


def git_head(repo_root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True).strip()


def build(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve()
    output_root = args.output_root.resolve()
    verify_manifest(input_root)
    if output_root.exists():
        raise FileExistsError(f"refuse overwrite existing decomposition root: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"staging decomposition root already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        sources = read_csv(input_root / "source_evidence_ledger.csv")
        events = read_csv(input_root / "economic_event_ledger.csv")
        source_by_id = {row["source_event_id"]: row for row in sources}
        targets = []
        for event in events:
            if event.get("economic_family") != "CAPITAL_RESTRUCTURING":
                continue
            source_ids = [value for value in event.get("source_event_ids", "").split("|") if value]
            if len(source_ids) != 1 or source_ids[0] not in source_by_id:
                raise RuntimeError("capital event must have exactly one retained source")
            source = source_by_id[source_ids[0]]
            raw = Path(source["raw_capture_path"])
            if not raw.is_file() or source.get("source_hash_matches_bytes", "").lower() != "true" or sha256_file(raw) != source["evidence_sha256"].lower():
                raise RuntimeError(f"capital source bytes are not hash-matched: {source_ids[0]}")
            if event.get("transition_status") != "UNRESOLVED" or source.get("source_kind") != "IDX_GET_ISSUED_HISTORY":
                raise RuntimeError("unexpected retained capital state")
            shares = source.get("idx_shares", "")
            shares_after = source.get("idx_shares_after", "")
            if shares == "0.0" and shares_after == "0.0":
                group = "ZERO_TO_ZERO_ISSUED_SHARE_MECHANICS"
            elif shares and shares_after and shares != "0.0" and shares_after != "0.0":
                group = "NONZERO_ISSUED_SHARE_CHANGE"
            else:
                raise RuntimeError(f"unclassified retained capital mechanics: {source_ids[0]}")
            targets.append({
                "economic_event_id": event["economic_event_id"],
                "source_event_id": source_ids[0],
                "ticker": source["ticker"],
                "candidate_date": source["candidate_date"],
                "idx_action_id": source["idx_action_id"],
                "idx_date_native": source["idx_date_native"],
                "idx_shares": shares,
                "idx_shares_after": shares_after,
                "mechanics_group": group,
                "basis_effect": event["basis_effect"],
                "transition_status": "UNRESOLVED",
                "missing_semantics": "receiving security, ratio, old-to-new identity, and accepted regular-market transition are absent from retained source",
                "source_ref": source["source_ref"],
                "evidence_sha256": source["evidence_sha256"].lower(),
                "raw_capture_path": source["raw_capture_path"],
            })
        if len(targets) != 19 or {row["mechanics_group"] for row in targets} != {"ZERO_TO_ZERO_ISSUED_SHARE_MECHANICS", "NONZERO_ISSUED_SHARE_CHANGE"}:
            raise RuntimeError("retained CAPITAL_RESTRUCTURING scope is not the expected 6+13 decomposition")
        group_counts = {group: sum(row["mechanics_group"] == group for row in targets) for group in sorted({row["mechanics_group"] for row in targets})}
        if group_counts != {"NONZERO_ISSUED_SHARE_CHANGE": 13, "ZERO_TO_ZERO_ISSUED_SHARE_MECHANICS": 6}:
            raise RuntimeError(f"unexpected capital decomposition: {group_counts}")
        write_csv(staging / "capital_restructuring_decomposition.csv", sorted(targets, key=lambda row: (row["mechanics_group"], row["ticker"])), list(targets[0]))
        write_json(staging / "input_provenance.json", {
            "controlling_root": str(input_root),
            "controlling_manifest_sha256": INPUT_MANIFEST_SHA256,
            "source_rows_consumed": 19,
            "provider_calls": False,
            "outcome_blind": True,
        })
        summary = {
            "schema_version": "inc001_capital_restructuring_decomposition_v1",
            "audit_date": AUDIT_DATE,
            "status": "LOCAL_PHASE_C_RETAINED_DECOMPOSITION_COMPLETE_NO_SCIENTIFIC_ADMISSION",
            "repository": {"head": git_head(args.repo_root.resolve()), "script": "scripts/build_inc001_capital_restructuring_decomposition_v1.py"},
            "controlling_predecessor": {"root": str(input_root), "manifest_sha256": INPUT_MANIFEST_SHA256},
            "scope": {"economic_family": "CAPITAL_RESTRUCTURING", "event_count": 19, "mechanics_group_counts": group_counts},
            "disposition": "All 19 events remain CAPITAL_RESTRUCTURING and UNRESOLVED. Retained IDX issued-share mechanics do not prove a receiving security or accepted regular-market transition.",
            "targeted_acquisition": {"performed": False, "reason": "No subgroup has retained event-specific transition semantics sufficient to authorize a narrower acquisition; broad crawl is not authorized."},
            "scientific_verdict": {"DATA_ADMISSION": "FAIL", "RESEARCH_ADMISSION": "FAIL", "MODEL_PROMOTION": "NOT_EVALUATED", "REFIT_AUTHORIZED": False, "COUNTER_ACTION": "NONE"},
            "guardrails": {"provider_calls": False, "outcomes_or_targets": False, "fit_refit_score": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False},
        }
        validation = {
            "input_manifest_verified": True,
            "source_rows": len(targets) == 19,
            "raw_hashes_verified": True,
            "zero_to_zero_count": group_counts["ZERO_TO_ZERO_ISSUED_SHARE_MECHANICS"] == 6,
            "nonzero_change_count": group_counts["NONZERO_ISSUED_SHARE_CHANGE"] == 13,
            "all_transitions_unresolved": all(row["transition_status"] == "UNRESOLVED" for row in targets),
            "no_provider_calls": True,
            "no_scientific_admission": True,
        }
        write_json(staging / "reconciliation_summary.json", summary)
        write_json(staging / "validation_report.json", validation)
        manifest = {"schema_version": "inc001_capital_restructuring_decomposition_v1_manifest", "audit_date": AUDIT_DATE, "predecessor_manifest_sha256": INPUT_MANIFEST_SHA256, "files": [], "self_hash_policy": "MANIFEST.json excluded from its own hash"}
        for path in sorted(staging.rglob("*")):
            if path.is_file() and path.name != "MANIFEST.json":
                manifest["files"].append({"path": path.relative_to(staging).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        write_json(staging / "MANIFEST.json", manifest)
        staging.rename(output_root)
        return {"summary": summary, "validation": validation, "manifest_sha256": sha256_file(output_root / "MANIFEST.json")}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
