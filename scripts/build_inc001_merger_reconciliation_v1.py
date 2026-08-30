"""Build the bounded INC-001 MERGER successor after official acquisition.

The acquisition result is deliberately conservative: discovery failure is not
historical negative authority and cannot change a retained MERGER event.  This
builder creates one immutable successor that preserves the Phase-A ledgers,
embeds the bounded request evidence, and records all five events as unresolved.
It does not infer merger mechanics or a market transition.
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


COMPOSITE_MANIFEST_SHA256 = "3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030"
ACQUISITION_MANIFEST_SHA256 = "8c853dc0ea7528a35edf97d00ce99fe9db786c30fedb0bec1ae889e40558e5d7"
AUDIT_DATE = "2026-08-31"
EXPECTED_TICKERS = {"ADMF", "EXCL", "JARR", "MORA", "PGUN"}
EXPECTED_CLASSES = {"PROVIDER_DISCOVERY_FAILURE"}


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


def verify_manifest(root: Path, expected_sha256: str) -> dict[str, Any]:
    manifest_path = root / "MANIFEST.json"
    if sha256_file(manifest_path) != expected_sha256:
        raise RuntimeError(f"manifest hash mismatch: {manifest_path}")
    manifest = read_json(manifest_path)
    for item in manifest.get("files", []):
        path = root / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"manifest-bound file mismatch: {path}")
    return manifest


def copy_tree_without_manifest(source: Path, target: Path) -> None:
    for path in source.rglob("*"):
        if not path.is_file() or path.name == "MANIFEST.json":
            continue
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def git_head(repo_root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True).strip()


def build(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    input_root = args.input_root.resolve()
    acquisition_root = args.acquisition_root.resolve()
    output_root = args.output_root.resolve()
    predecessor_manifest = verify_manifest(input_root, COMPOSITE_MANIFEST_SHA256)
    acquisition_manifest = verify_manifest(acquisition_root, ACQUISITION_MANIFEST_SHA256)
    if output_root.exists():
        raise FileExistsError(f"refuse overwrite existing successor root: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"staging successor root already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        results = read_csv(acquisition_root / "target_event_results.csv")
        if len(results) != 5 or {row["ticker"] for row in results} != EXPECTED_TICKERS:
            raise RuntimeError("acquisition scope is not exactly the five retained MERGER events")
        if {row["result_classification"] for row in results} != EXPECTED_CLASSES:
            raise RuntimeError("MERGER acquisition did not remain uniformly fail-closed")
        if any(row.get("transition_date") or row.get("authority_evidence_sha256") for row in results):
            raise RuntimeError("a transition or authority was unexpectedly admitted")

        event_rows = read_csv(input_root / "economic_event_ledger.csv")
        merger_rows = [row for row in event_rows if row.get("economic_family") == "MERGER"]
        if len(merger_rows) != 5 or any(row.get("transition_status") != "UNRESOLVED" for row in merger_rows):
            raise RuntimeError("controlling MERGER state is not exactly five unresolved events")
        summary_before = read_json(input_root / "reconciliation_summary.json")
        counts_before = summary_before.get("counts", {})
        if counts_before.get("economic_event_count") != 387 or counts_before.get("resolved_transitions") != 163 or counts_before.get("unresolved_transitions") != 178:
            raise RuntimeError("unexpected Phase-A predecessor counts")

        copy_tree_without_manifest(input_root, staging)
        copy_tree_without_manifest(acquisition_root, staging / "official_merger_acquisition")
        review_rows = []
        for row in sorted(results, key=lambda value: value["ticker"]):
            review_rows.append({
                "economic_event_id": row["economic_event_id"],
                "source_event_id": row["source_event_id"],
                "ticker": row["ticker"],
                "candidate_date": row["candidate_date"],
                "acquisition_classification": row["result_classification"],
                "transition_status": "UNRESOLVED",
                "scientific_admission": "FALSE",
                "historical_negative_authority": "FALSE",
                "decision": "RETAIN_MERGER_UNRESOLVED",
                "reason": "official discovery returned HTTP 403; no retry; no event-specific transition evidence was available",
            })
        write_csv(staging / "merger_event_review.csv", review_rows, list(review_rows[0]))
        summary = {
            "schema_version": "inc001_merger_reconciliation_v1",
            "audit_date": AUDIT_DATE,
            "status": "LOCAL_PHASE_B_MERGER_RECONCILIATION_COMPLETE_NO_SCIENTIFIC_ADMISSION",
            "repository": {"head": git_head(repo_root), "script": "scripts/build_inc001_merger_reconciliation_v1.py"},
            "controlling_predecessor": {"root": str(input_root), "manifest_sha256": COMPOSITE_MANIFEST_SHA256},
            "official_acquisition": {"root": str(acquisition_root), "manifest_sha256": ACQUISITION_MANIFEST_SHA256, "request_count": 5, "provider_calls": True, "no_retry": True},
            "scope": {"economic_family": "MERGER", "event_count": 5, "tickers": sorted(EXPECTED_TICKERS)},
            "disposition": "All five retained MERGER events remain UNRESOLVED. HTTP 403 is a discovery failure, not negative historical authority.",
            "counts_preserved": counts_before,
            "scientific_verdict": {"DATA_ADMISSION": "FAIL", "RESEARCH_ADMISSION": "FAIL", "MODEL_PROMOTION": "NOT_EVALUATED", "REFIT_AUTHORIZED": False, "COUNTER_ACTION": "NONE"},
            "guardrails": {"outcomes_or_targets": False, "fit_refit_score": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False},
        }
        validation = {
            "predecessor_manifest_verified": True,
            "acquisition_manifest_verified": True,
            "five_event_scope_verified": True,
            "all_acquisition_results_fail_closed": True,
            "no_transition_admitted": True,
            "merger_state_preserved_unresolved": True,
            "predecessor_counts_preserved": True,
            "not_historical_negative_authority": True,
            "no_scientific_admission": True,
        }
        write_json(staging / "reconciliation_summary.json", summary)
        write_json(staging / "validation_report.json", validation)
        manifest = {
            "schema_version": "inc001_merger_reconciliation_v1_manifest",
            "audit_date": AUDIT_DATE,
            "predecessor_manifest_sha256": COMPOSITE_MANIFEST_SHA256,
            "acquisition_manifest_sha256": ACQUISITION_MANIFEST_SHA256,
            "files": [],
            "self_hash_policy": "MANIFEST.json excluded from its own hash",
        }
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
    parser.add_argument("--acquisition-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
