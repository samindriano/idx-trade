"""Fail-closed structural verifier for the isolated alpha research knowledge base.

This verifier checks registry shape, manifest counts, evidence-reference
integrity, allowed capability states, and absence of known protected-payload
field names. It does not inspect source datasets, protected outcomes,
providers, or cloud state.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ALLOWED_SOURCE_STATUS = {
    "AVAILABLE",
    "AVAILABLE_BUT_NON_PIT",
    "PARTIAL",
    "BOUNDED",
    "MISSING",
    "UNAUTHORITATIVE",
    "SEMANTICALLY_AMBIGUOUS",
    "BLOCKED",
}
JSONL_SPECS = {
    "experiment_registry.jsonl": {
        "id": "experiment_id",
        "required": {"experiment_id", "question", "method", "result", "limitations", "verdict", "retry_status", "reopen_trigger"},
    },
    "findings_index.jsonl": {
        "id": "finding_id",
        "required": {"finding_id", "statement", "class", "verdict", "evidence_refs", "reopen_trigger"},
    },
    "no_retry_registry.jsonl": {
        "id": "no_retry_id",
        "required": {"no_retry_id", "subject", "reason_code", "scope", "evidence_refs", "decision", "retry_status", "reopen_trigger"},
    },
}
REFERENCE_INTEGRITY_FILENAME = "evidence_reference_integrity_v1.json"
REFERENCE_FIELDS = ("input_refs", "code_refs", "policy_refs", "evidence_refs")
UNAVAILABLE_REFERENCE_CLASSES = {"UNAVAILABLE", "SUPERSEDED", "UNAVAILABLE_SUPERSEDED"}
FORBIDDEN_FIELD_PATTERNS = (
    r"(?i)(?:^|[_\-])(?:h5|h10|target|forward_return|rank_ic|icir|pnl)(?:[_\-]|$).*value",
    r"(?i)(?:^|[_\-])(?:realized_return|forward_return_value|target_value|pnl_value|ic_value|icir_value)(?:$|[_\-])",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path.name}:{line_number}: entry is not an object")
        rows.append(value)
    return rows


def scan_forbidden_fields(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{path}.{key}" if path else key
            if any(re.search(pattern, key) for pattern in FORBIDDEN_FIELD_PATTERNS):
                hits.append(key_path)
            hits.extend(scan_forbidden_fields(child, key_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(scan_forbidden_fields(child, f"{path}[{index}]"))
    return hits


def normalize_reference(reference: str) -> str:
    """Remove an optional trailing line or line-range suffix from a reference."""

    return re.sub(r":[0-9]+(?:-[0-9]+)?$", "", reference)


def _reference_exists(repo_root: Path, reference: str) -> tuple[bool, str]:
    """Resolve a current-tree, absolute, or commit-qualified reference."""

    normalized = normalize_reference(reference)
    if re.match(r"^[A-Za-z]:[\\/]", normalized):
        return Path(normalized).is_file(), "absolute"
    if normalized.startswith("origin/") and ":" in normalized:
        completed = subprocess.run(
            ["git", "cat-file", "-e", normalized],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return completed.returncode == 0, "git"
    candidate = (repo_root / normalized).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError:
        return False, "relative_escape"
    return candidate.is_file(), "relative"


def validate_registry_references(
    repo_root: Path,
    registry_rows: list[tuple[str, dict[str, Any]]],
    integrity: dict[str, Any],
) -> dict[str, int]:
    """Require every durable registry reference to resolve or be classified.

    Current-tree and absolute references must exist. Commit-qualified refs may
    be retained for historical provenance only when the exact unavailable ref
    is listed in the append-only integrity ledger. A ledger entry cannot mask a
    ref that resolves now; that prevents silent historical-reference rot.
    """

    if integrity.get("schema_version") != "1.0":
        raise ValueError("unsupported evidence-reference integrity schema")
    unavailable_rows = integrity.get("unavailable_refs", [])
    if not isinstance(unavailable_rows, list):
        raise ValueError("evidence-reference unavailable_refs must be a list")
    unavailable: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(unavailable_rows, 1):
        if not isinstance(row, dict) or not isinstance(row.get("ref"), str):
            raise ValueError(f"evidence-reference unavailable row {index} is invalid")
        ref = normalize_reference(row["ref"])
        if row.get("classification") not in UNAVAILABLE_REFERENCE_CLASSES:
            raise ValueError(f"evidence-reference unavailable row {index} has invalid classification")
        if ref in unavailable:
            raise ValueError(f"duplicate unavailable evidence reference: {ref}")
        unavailable[ref] = row

    observed: set[str] = set()
    missing: list[str] = []
    resolved_count = 0
    classified_count = 0
    for registry_name, row in registry_rows:
        for field in REFERENCE_FIELDS:
            values = row.get(field, [])
            if values is None:
                continue
            if not isinstance(values, list):
                raise ValueError(f"{registry_name}:{field} must be a list")
            for raw_reference in values:
                if not isinstance(raw_reference, str) or not raw_reference:
                    raise ValueError(f"{registry_name}:{field} contains an invalid reference")
                normalized = normalize_reference(raw_reference)
                observed.add(normalized)
                exists, kind = _reference_exists(repo_root, raw_reference)
                if exists:
                    resolved_count += 1
                    if normalized in unavailable:
                        raise ValueError(f"evidence reference is classified unavailable but resolves: {raw_reference}")
                    continue
                if normalized not in unavailable:
                    missing.append(f"{registry_name}:{field}:{raw_reference}")
                    continue
                if kind != "git":
                    raise ValueError(f"only unavailable historical git refs may be ledger-classified: {raw_reference}")
                classified_count += 1

    if missing:
        raise ValueError(f"unresolved evidence references: {missing}")

    for normalized, row in unavailable.items():
        exists, _ = _reference_exists(repo_root, normalized)
        if exists:
            raise ValueError(f"unavailable evidence reference now resolves: {normalized}")
        if normalized not in observed:
            raise ValueError(f"unavailable evidence reference is not used by a registry: {normalized}")
        if not row.get("reason") or not row.get("replacement_status"):
            raise ValueError(f"unavailable evidence reference lacks classification detail: {normalized}")

    repaired_rows = integrity.get("repaired_refs", [])
    if not isinstance(repaired_rows, list):
        raise ValueError("evidence-reference repaired_refs must be a list")
    for index, row in enumerate(repaired_rows, 1):
        if not isinstance(row, dict) or not isinstance(row.get("ref_after"), str):
            raise ValueError(f"evidence-reference repaired row {index} is invalid")
        exists, _ = _reference_exists(repo_root, row["ref_after"])
        if not exists:
            raise ValueError(f"repaired evidence reference does not resolve: {row['ref_after']}")

    return {
        "registry_references": len(observed),
        "resolved_references": resolved_count,
        "classified_unavailable_references": classified_count,
        "repaired_references": len(repaired_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "research_knowledge")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise ValueError(f"knowledge root does not exist: {root}")

    manifest = load_json(root / "manifest.json")
    matrix = load_json(root / "source_capability_matrix.json")
    integrity = load_json(root / REFERENCE_INTEGRITY_FILENAME)
    if manifest.get("schema_version") != "1.0":
        raise ValueError("unsupported manifest schema")
    if manifest.get("evidence_policy", {}).get("protected_payloads_persisted") is not False:
        raise ValueError("protected payload policy is not explicitly false")
    if manifest.get("eligibility_authority_status") != "POLICY_AUTHORITY_MISSING":
        raise ValueError("eligibility authority status is not fail-closed")
    listed_files = manifest.get("files", [])
    if not isinstance(listed_files, list) or not listed_files:
        raise ValueError("manifest file list is empty")
    missing_listed = [name for name in listed_files if not (root / name).is_file()]
    if missing_listed:
        raise ValueError(f"manifest lists missing files: {missing_listed}")

    counts: dict[str, int] = {}
    all_values: list[Any] = [manifest, matrix, integrity]
    census_path = root / "common_support_census_v1.json"
    census = load_json(census_path)
    if census.get("status") != "PASS" or census.get("scope") != "OUTCOME_BLIND_STRUCTURAL_SUPPORT_ONLY":
        raise ValueError("common support census is not a passing outcome-blind artifact")
    all_values.append(census)
    registry_rows: list[tuple[str, dict[str, Any]]] = []
    for filename, spec in JSONL_SPECS.items():
        path = root / filename
        rows = load_jsonl(path)
        counts[filename] = len(rows)
        seen: set[str] = set()
        for index, row in enumerate(rows, 1):
            missing = sorted(spec["required"] - set(row))
            if missing:
                raise ValueError(f"{filename}:{index}: missing fields {missing}")
            row_id = row[spec["id"]]
            if not isinstance(row_id, str) or not row_id:
                raise ValueError(f"{filename}:{index}: invalid id")
            if row_id in seen:
                raise ValueError(f"{filename}:{index}: duplicate id {row_id}")
            seen.add(row_id)
        all_values.extend(rows)
        registry_rows.extend((filename, row) for row in rows)

    reference_counts = validate_registry_references(root.parent, registry_rows, integrity)

    source_rows = matrix.get("sources")
    if not isinstance(source_rows, list) or not source_rows:
        raise ValueError("source capability matrix is empty")
    for index, row in enumerate(source_rows, 1):
        if row.get("status") not in ALLOWED_SOURCE_STATUS:
            raise ValueError(f"source_capability_matrix.json:{index}: invalid status {row.get('status')!r}")
        if not row.get("source_id") or not row.get("allowed_use") or not row.get("reopen_trigger"):
            raise ValueError(f"source_capability_matrix.json:{index}: incomplete source row")
    counts["source_capability_entries"] = len(source_rows)

    expected = manifest.get("counts", {})
    mapping = {
        "experiment_registry.jsonl": "experiment_registry_entries",
        "findings_index.jsonl": "findings_index_entries",
        "no_retry_registry.jsonl": "no_retry_registry_entries",
        "source_capability_entries": "source_capability_entries",
    }
    for actual_key, manifest_key in mapping.items():
        if expected.get(manifest_key) != counts[actual_key]:
            raise ValueError(f"manifest count mismatch for {manifest_key}: {expected.get(manifest_key)} != {counts[actual_key]}")

    forbidden: list[str] = []
    for value in all_values:
        forbidden.extend(scan_forbidden_fields(value))
    if forbidden:
        raise ValueError(f"protected-looking payload field names found: {forbidden}")

    result = {
        "status": "PASS",
        "knowledge_root": str(root),
        "counts": counts,
        "eligibility_authority_status": manifest["eligibility_authority_status"],
        "protected_payloads_persisted": manifest["evidence_policy"]["protected_payloads_persisted"],
        "source_statuses_valid": True,
        "protected_field_scan": "PASS",
        "evidence_reference_integrity": reference_counts,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(1) from exc
