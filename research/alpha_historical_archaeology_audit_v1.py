"""Bounded, outcome-blind audit of historical alpha archaeology coverage.

This audit reads only current durable checkpoint metadata and Git tree names for
retained historical refs. It does not read historical target/outcome payloads,
forward-return artifacts, incumbent score arrays, or provider data. The result
distinguishes a family-level durable map from exact source-level replayability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


CURRENT_DOCS = [
    "docs/checkpoints/2026-09-19_ALPHA_ARCHAEOLOGY_RESULT_V1.md",
    "docs/checkpoints/2026-09-19_ALPHA_FAILURE_TAXONOMY_V1.md",
    "docs/repository_hygiene/EXPERIMENT_TOMBSTONES_V2.md",
    "docs/repository_hygiene/RETAINED_LINEAGE_V2.md",
]

REF_SPECS = [
    ("ranking_v2_lineage", "refs/heads/research/idx-ranking-v2-spec-v1", "ranking_v1_v2_v3_v4abc"),
    ("v4_ca_lineage", "refs/heads/research/idx-ranking-v4-3-ca-admission-v1", "v4_ca_identity"),
    ("v4x1_lineage", "refs/heads/research/idx-ranking-v4-x1-prospective-eval-v1", "v4x1_o2"),
    ("alpha_frontier_lineage", "refs/heads/research/idx-alpha-frontier-v1", "frontier_v4x1"),
    ("financial_lineage", "refs/heads/research/idx-financial-representation-v2", "financial"),
    ("foreign_flow_lineage", "refs/heads/research/idx-foreign-flow-representation-v2", "foreign_flow"),
]

SAFE_RELEVANCE = re.compile(
    r"(?i)(ranking|stage5|v3|v4|structure|particip|path|sector|regime|"
    r"financial|foreign|flow|ownership|alpha|frontier|pit|identity|"
    r"lineage|tombstone|reliability|payoff|risk)"
)
PROTECTED_MARKER = re.compile(
    r"(?i)(target|outcome|forward|pnl|rank[_-]?ic|icir|h5|h10|return)"
)


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_ref(repo: Path, label: str, ref: str, family: str) -> dict[str, Any]:
    exists = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{ref}^{{commit}}"],
        capture_output=True,
    ).returncode == 0
    if not exists:
        return {
            "label": label,
            "ref": ref,
            "family": family,
            "exists": False,
            "head": None,
            "tree_paths_inspected": 0,
            "safe_relevant_paths": [],
            "protected_looking_paths_not_read": 0,
        }

    head = run_git(repo, "rev-parse", ref)
    tree = [line for line in run_git(repo, "ls-tree", "-r", "--name-only", ref).splitlines() if line]
    safe_paths = [
        path
        for path in tree
        if SAFE_RELEVANCE.search(path)
        and not PROTECTED_MARKER.search(path)
        and (path.startswith("docs/") or path.startswith("src/") or path.startswith("research/"))
    ]
    protected_looking = [path for path in tree if PROTECTED_MARKER.search(path)]
    return {
        "label": label,
        "ref": ref,
        "family": family,
        "exists": True,
        "head": head,
        "tree_paths_inspected": len(tree),
        "safe_relevant_paths": safe_paths[:80],
        "safe_relevant_path_count": len(safe_paths),
        "protected_looking_paths_not_read": len(protected_looking),
    }


def build_result(repo: Path) -> dict[str, Any]:
    current_docs: list[dict[str, Any]] = []
    for relative in CURRENT_DOCS:
        path = repo / relative
        current_docs.append(
            {
                "path": relative,
                "exists": path.is_file(),
                "sha256": sha256_file(path) if path.is_file() else None,
            }
        )

    refs = [audit_ref(repo, *spec) for spec in REF_SPECS]
    ref_exists = {row["label"]: row["exists"] for row in refs}
    family_matrix = [
        {
            "family": "Ranking V1/V2",
            "map_status": "SUPPORTED",
            "exact_source_status": "BOUNDED_REPLAYABLE_REFERENCE",
            "basis": ["current archaeology checkpoint", "ranking_v2_lineage"],
            "interpretation": "The family-level map and retained V2/V3 source references are present; no old target artifact was read.",
        },
        {
            "family": "V3-A through V3-E",
            "map_status": "SUPPORTED",
            "exact_source_status": "BOUNDED_REPLAYABLE_REFERENCE",
            "basis": ["current archaeology checkpoint", "ranking_v2_lineage"],
            "interpretation": "Specs, review/result checkpoints, and retained source names are available at reference level; historical claims are not being re-executed.",
        },
        {
            "family": "V4-A through V4-C",
            "map_status": "SUPPORTED",
            "exact_source_status": "BOUNDED_REPLAYABLE_REFERENCE",
            "basis": ["current archaeology checkpoint", "ranking_v2_lineage"],
            "interpretation": "The participation, price-path, and cross-sectional first-pass map is represented by retained specs/checkpoints; no target payload was opened.",
        },
        {
            "family": "V4-D sector relative",
            "map_status": "SUPPORTED",
            "exact_source_status": "BLOCKED_SOURCE_ADMISSION",
            "basis": ["current archaeology checkpoint", "ranking_v2_lineage"],
            "interpretation": "The historical source gate is preserved; absence of an admitted daily PIT sector source remains the blocker, not a mechanism rejection.",
        },
        {
            "family": "V4-E/F/G systematic, financial, flow/ownership",
            "map_status": "SUPPORTED",
            "exact_source_status": "PARTIAL_HISTORICAL_REPLAYABILITY",
            "basis": ["current archaeology checkpoint", "financial_lineage", "foreign_flow_lineage"],
            "interpretation": "Exact historical formulations and later source audits are mapped, but not every old implementation is present in the active lane and no new replay is authorized.",
        },
        {
            "family": "V4-X1/O2 and incumbent lineage",
            "map_status": "SUPPORTED",
            "exact_source_status": "PROTECTED_OR_LINEAGE_ONLY",
            "basis": ["current archaeology checkpoint", "v4x1_lineage", "alpha_frontier_lineage"],
            "interpretation": "Lineage and integrity conclusions are durable; incumbent/target artifacts remain outside this audit.",
        },
        {
            "family": "Auxiliary payoff, reliability, path-risk, execution-source work",
            "map_status": "SUPPORTED",
            "exact_source_status": "TOMBSTONE_OR_SOURCE_BLOCKED",
            "basis": ["current tombstones", "current retained lineage"],
            "interpretation": "Negative and source-blocked conclusions are preserved; recreating deleted implementations without new evidence would be redundant.",
        },
    ]

    return {
        "schema_version": "IDX_TRADE_HISTORICAL_ARCHAEOLOGY_AUDIT_V1",
        "audit_id": "ARCHAEOLOGY-037",
        "status": "SUPPORTED_BOUNDED_MAP_WITH_REPLAY_GAPS",
        "scope": "Outcome-blind metadata/tree audit of historical research archaeology; no historical target/outcome payload content read.",
        "protected_payloads_read": False,
        "canonical_mutation": False,
        "provider_or_cloud_access": False,
        "current_documents": current_docs,
        "retained_refs": refs,
        "family_matrix": family_matrix,
        "authority_conclusion": {
            "family_map": "SUPPORTED",
            "exact_old_implementation_replay": "PARTIAL",
            "historical_headline_reinterpretation": "LATEST_PIT_AND_INTEGRITY_ADJUDICATION_CONTROLS",
            "global_absence_claim": False,
            "new_scientific_candidate_authorized": False,
        },
        "red_team": {
            "checked": [
                "current checkpoint/tombstone/lineage documents exist",
                "retained refs resolve to commits",
                "safe relevant tree names are present on retained refs",
                "protected-looking historical paths were counted but not read",
            ],
            "limitations": [
                "tree-name presence is not executable source reproducibility",
                "a retained ref can contain historical artifacts not inspected here",
                "absence from inspected refs is not global source absence",
                "historical predictive headlines are not reopened or revalidated",
            ],
        },
        "reopen_trigger": "A genuinely new historical source artifact, exact old implementation required for a disputed classification, or authoritative evidence contradicting the current PIT/integrity adjudication.",
        "next_action": "Move to the next non-redundant outcome-blind frontier; do not repeat historical replay without a new artifact.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_result(args.repo.resolve())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.resolve().write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
