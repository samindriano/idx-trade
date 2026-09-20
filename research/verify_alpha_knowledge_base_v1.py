"""Fail-closed structural verifier for the isolated alpha research knowledge base.

This verifier checks registry shape, manifest counts, allowed capability states,
and absence of known protected-payload field names. It does not inspect source
datasets, protected outcomes, providers, or cloud state.
"""

from __future__ import annotations

import argparse
import json
import re
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "research_knowledge")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise ValueError(f"knowledge root does not exist: {root}")

    manifest = load_json(root / "manifest.json")
    matrix = load_json(root / "source_capability_matrix.json")
    if manifest.get("schema_version") != "1.0":
        raise ValueError("unsupported manifest schema")
    if manifest.get("evidence_policy", {}).get("protected_payloads_persisted") is not False:
        raise ValueError("protected payload policy is not explicitly false")
    if manifest.get("eligibility_authority_status") != "POLICY_AUTHORITY_MISSING":
        raise ValueError("eligibility authority status is not fail-closed")

    counts: dict[str, int] = {}
    all_values: list[Any] = [manifest, matrix]
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
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(1) from exc
