from __future__ import annotations

import pytest

from research.verify_alpha_knowledge_base_v1 import validate_registry_references


def test_missing_current_tree_reference_fails_closed(tmp_path) -> None:
    rows = [("findings_index.jsonl", {"finding_id": "F-TEST", "evidence_refs": ["missing.md"]})]
    integrity = {"schema_version": "1.0", "unavailable_refs": [], "repaired_refs": []}

    with pytest.raises(ValueError, match="unresolved evidence references"):
        validate_registry_references(tmp_path, rows, integrity)


def test_unavailable_historical_git_reference_requires_explicit_classification(tmp_path) -> None:
    reference = "origin/old-object:docs/old.md"
    rows = [("experiment_registry.jsonl", {"experiment_id": "E-TEST", "input_refs": [reference]})]
    integrity = {
        "schema_version": "1.0",
        "unavailable_refs": [
            {
                "ref": reference,
                "classification": "UNAVAILABLE",
                "reason": "Historical commit object is not present in this checkout.",
                "replacement_status": "SUPERSEDED_OR_NONEXACT",
            }
        ],
        "repaired_refs": [],
    }

    result = validate_registry_references(tmp_path, rows, integrity)

    assert result["classified_unavailable_references"] == 1


def test_repaired_reference_must_resolve(tmp_path) -> None:
    rows = [("findings_index.jsonl", {"finding_id": "F-TEST", "evidence_refs": []})]
    integrity = {
        "schema_version": "1.0",
        "unavailable_refs": [],
        "repaired_refs": [{"ref_before": "old.md", "ref_after": "still-missing.md"}],
    }

    with pytest.raises(ValueError, match="repaired evidence reference does not resolve"):
        validate_registry_references(tmp_path, rows, integrity)
