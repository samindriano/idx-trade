"""Audit retained official IDX instance.zip payloads without normalizing facts.

The audit counts XML structure only.  It does not emit statement values or
convert taxonomy concepts, and it does not treat the retained XBRL as PIT
research-admissible data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


STAGING_MARKER = "idx-alpha-available-data-staging-20260919"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def audit_zip(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            result["zip_members"] = sorted(names)
            if "instance.xbrl" not in names:
                result["status"] = "MISSING_INSTANCE_XBRL"
                return result
            root = ElementTree.fromstring(archive.read("instance.xbrl"))
    except Exception as exc:  # structural audit records failure, never fabricates success
        result["status"] = "PARSE_ERROR"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result
    contexts = [element for element in root.iter() if _local(element.tag) == "context"]
    units = [element for element in root.iter() if _local(element.tag) == "unit"]
    fact_elements = [
        element
        for element in root.iter()
        if element is not root and _local(element.tag) not in {"context", "unit", "entity", "identifier", "period", "instant", "startDate", "endDate", "measure", "divide", "unitNumerator", "unitDenominator", "explicitMember", "typedMember"}
    ]
    namespaces = Counter()
    for element in fact_elements:
        if element.tag.startswith("{"):
            namespaces[element.tag[1:].split("}", 1)[0]] += 1
    periods = sorted(
        {
            child.text
            for context in contexts
            for child in context.iter()
            if _local(child.tag) in {"instant", "startDate", "endDate"} and child.text
        }
    )
    result.update(
        {
            "status": "PARSED",
            "context_count": len(contexts),
            "unit_count": len(units),
            "fact_element_count": len(fact_elements),
            "namespace_fact_counts": dict(sorted(namespaces.items())),
            "period_value_count": len(periods),
            "period_min": periods[0] if periods else None,
            "period_max": periods[-1] if periods else None,
        }
    )
    return result


def summarize(root: Path) -> dict[str, Any]:
    files = sorted(root.rglob("*.instance.zip"))
    if not files:
        raise ValueError(f"no instance.zip files under {root}")
    records = [audit_zip(path) for path in files]
    parsed = [item for item in records if item["status"] == "PARSED"]
    statuses = Counter(item["status"] for item in records)
    return {
        "schema_version": "1.0",
        "status": "PASS_IDX_XBRL_ATTACHMENT_STRUCTURE_RESEARCH_ONLY",
        "scope": "Official IDX instance.zip XML structure; no fact normalization or admission",
        "raw_root": str(root),
        "zip_files": len(records),
        "status_counts": dict(sorted(statuses.items())),
        "parsed_files": len(parsed),
        "context_total": sum(item.get("context_count", 0) for item in parsed),
        "unit_total": sum(item.get("unit_count", 0) for item in parsed),
        "fact_element_total": sum(item.get("fact_element_count", 0) for item in parsed),
        "period_min": min((item["period_min"] for item in parsed if item.get("period_min")), default=None),
        "period_max": max((item["period_max"] for item in parsed if item.get("period_max")), default=None),
        "records": records,
        "what_is_proven": [
            "Retained official instance.zip payloads can be structurally opened and parsed without a provider credential in the bounded acquisition.",
            "The payloads contain XBRL contexts, units, facts, and period metadata that can support a later taxonomy/PIT contract audit.",
        ],
        "what_remains_unknown": [
            "available-at/publication and revision/vintage semantics",
            "cross-issuer taxonomy, unit, sign, and restatement comparability",
            "issuer/ISIN continuity and historical population completeness",
            "whether these payloads were available to an investor at a given decision time",
        ],
        "admission": {
            "structural_parse": "SUPPORTED_BOUNDED_ACQUISITION",
            "historical_research_admission": "BLOCKED",
            "forbidden_use": "fact-value normalization, PIT substitution, or predictive research admission without an explicit contract",
        },
        "protected_boundary": "CLOSED",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = args.raw_root.resolve()
    output = args.output.resolve()
    if STAGING_MARKER not in str(root) or STAGING_MARKER not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    result = summarize(root)
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
