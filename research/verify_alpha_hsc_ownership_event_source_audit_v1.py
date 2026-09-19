"""Independent envelope verifier for the HSC ownership event source audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--events-csv", type=Path, required=True)
    parser.add_argument("--events-json", type=Path, required=True)
    parser.add_argument("--capture-index", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--current-target", type=Path, required=True)
    parser.add_argument("--july-target", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifact: dict[str, Any] = json.loads(args.artifact.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    with args.events_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    json_rows = json.loads(args.events_json.read_text(encoding="utf-8"))
    capture = json.loads(args.capture_index.read_text(encoding="utf-8"))
    replay = json.loads(args.replay.read_text(encoding="utf-8"))
    current_target = json.loads(args.current_target.read_text(encoding="utf-8"))
    july_target = json.loads(args.july_target.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {
        "status_is_structural_only_admission_blocked": artifact.get("status") == "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED",
        "scope_is_outcome_blind": all(artifact.get("scope", {}).get(key) is False for key in ("outcome_accessed", "target_accessed", "provider_accessed", "network_used")),
        "all_integrity_checks_true": bool(artifact.get("integrity_checks")) and all(artifact["integrity_checks"].values()),
        "manifest_count_exact": manifest.get("event_count") == 59 and len(manifest.get("artifacts", [])) == 137,
        "event_csv_count_exact": len(csv_rows) == 59,
        "event_json_csv_exact": csv_rows == json_rows,
        "event_ids_unique": len({row.get("event_id") for row in csv_rows}) == 59,
        "capture_count_exact": len(capture.get("records", [])) == 59,
        "replay_passes": bool(replay) and all(item.get("status") == "PASS" for item in replay) and replay[-1].get("active_count") == 55,
        "current_target_count_exact": current_target.get("ticker_count") == 55,
        "july_target_count_exact": july_target.get("ticker_count") == 51,
        "event_only_not_panel": artifact.get("source_contract", {}).get("daily_population_panel_available") is False and artifact.get("source_contract", {}).get("event_ledger_available") is True,
        "no_feature_or_candidate": artifact.get("scope", {}).get("feature_created") is False and artifact.get("scope", {}).get("candidate_created") is False,
    }
    declared = artifact.get("source_hashes", {})
    files = {"manifest": args.manifest, "events_csv": args.events_csv, "events_json": args.events_json, "capture_index": args.capture_index, "replay_checkpoints": args.replay}
    source_files: dict[str, Any] = {}
    for name, path in files.items():
        actual = sha256_file(path)
        expected = declared.get(name)
        checks[f"{name}_hash_matches"] = actual == expected
        source_files[name] = {"path": str(path), "actual_sha256": actual, "declared_sha256": expected, "matches": actual == expected}
    checks["code_hash_matches"] = sha256_file(args.code) == artifact.get("code_sha256")
    result = {"status": "PASS" if all(checks.values()) else "FAIL", "verification_type": "INDEPENDENT_HSC_OWNERSHIP_EVENT_SOURCE_AUDIT_ENVELOPE_V1", "artifact_sha256": sha256_file(args.artifact), "verifier_code_sha256": sha256_file(Path(__file__)), "checks": checks, "source_files": source_files, "scope": {"outcome_accessed": False, "target_accessed": False, "provider_accessed": False, "network_used": False, "canonical_mutation": False}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
