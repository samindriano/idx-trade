from __future__ import annotations

import csv
import re
import subprocess
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REMOTE_PREFIX = "refs/remotes/origin/"
LIVE_STATUSES = {"PLANNED", "ACTIVE", "AUTOMATED", "WAITING", "BLOCKED", "REVIEW", "PARKED"}
PROTECTED_TOKENS = (
    "o2",
    "foreign-flow",
    "price-state",
    "forward",
    "stockbit",
    "runtime",
)


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def git_ok(*args: str) -> bool:
    return subprocess.run(["git", *args], cwd=ROOT, check=False).returncode == 0


def current_refs() -> dict[str, str]:
    result: dict[str, str] = {}
    raw = git(
        "for-each-ref",
        "--format=%(refname)|%(objectname)|%(committerdate:iso8601-strict)",
        "refs/remotes/origin",
    )
    for line in raw.splitlines():
        ref, sha, date = line.split("|", 2)
        if ref == f"{REMOTE_PREFIX}HEAD" or not ref.startswith(REMOTE_PREFIX):
            continue
        result[ref[len(REMOTE_PREFIX) :]] = f"{sha}|{date}"
    return result


def parse_status(line: str) -> str | None:
    match = re.search(
        r"\|\s*`?(PLANNED|ACTIVE|AUTOMATED|WAITING|BLOCKED|REVIEW|DONE|PARKED)`?\s*\|",
        line,
    )
    return match.group(1) if match else None


def grep_refs(query: str) -> list[tuple[str, str]]:
    result = subprocess.run(
        [
            "git",
            "grep",
            "--no-color",
            "-n",
            "-I",
            "-F",
            query,
            "origin/main",
            "--",
            "docs/checkpoints",
            "coordination/handoffs",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    hits: list[tuple[str, str]] = []
    for line in result.stdout.splitlines()[:80]:
        parts = line.split(":", 3)
        if len(parts) == 4:
            hits.append((f"{parts[0]}:{parts[1]}", parts[3].strip()))
    return hits


def branch_evidence(ref: str) -> list[tuple[str, str]]:
    """Read decision/provenance evidence from the branch itself."""
    result = subprocess.run(
        [
            "git",
            "grep",
            "--no-color",
            "-n",
            "-I",
            "-E",
            r"accept|reject|verdict|decision|checkpoint|handoff|manifest|spec",
            ref,
            "--",
            "docs/checkpoints",
            "coordination/handoffs",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    hits: list[tuple[str, str]] = []
    for line in result.stdout.splitlines()[:160]:
        parts = line.split(":", 3)
        if len(parts) == 4:
            hits.append((f"{parts[0]}:{parts[1]}", parts[3].strip()))
    return hits


_EXPLICIT_DECISION_RE = re.compile(
    r"\b(?:accepted|rejected|verdict|no[ _-]?(?:go|survivor|decision)|"
    r"decision[ _-]?(?:valid|accepted|rejected)|scientific[ _-]?(?:decision|verdict)|"
    r"final[ _-]?(?:decision|verdict))\b",
    re.IGNORECASE,
)
_RESULT_RE = re.compile(
    r"\b(?:PASS(?:ED)?(?![-_])|FAIL(?:ED)?(?![-_])|BLOCKED|NO[ _-]?(?:GO|SURVIVOR))\b",
    re.IGNORECASE,
)
_NEGATED_RESULT_RE = re.compile(
    r"\b(?:do not|don't|must not|never|if|unless|should|could|would|not be interpreted as)\b",
    re.IGNORECASE,
)


def is_scientific_decision_evidence(ref: str, text: str) -> bool:
    """Accept explicit decisions, not generic policy/spec/test vocabulary."""
    if _EXPLICIT_DECISION_RE.search(text):
        return True
    # A bare PASS/FAIL/BLOCKED is decision evidence only in a result-bearing
    # checkpoint or handoff line, and not when it is merely a future gate or
    # a prohibition.  This prevents orchestration prose such as "decision"
    # and "do not interpret as PASS" from becoming scientific verdicts.
    if ("docs/checkpoints/" in ref or "coordination/handoffs/" in ref) and _RESULT_RE.search(text):
        return not _NEGATED_RESULT_RE.search(text)
    return False


def unique_paths(head: str, main: str) -> list[str]:
    # ``main...branch`` also includes paths changed only on main. For forensic
    # lineage, report paths touched by commits reachable from the branch but
    # not from current main: ``main..branch``.
    raw = git("log", "--format=", "--name-only", f"{main}..{head}", check=False)
    return sorted({line.strip() for line in raw.splitlines() if line.strip()})


def unique_messages(head: str, main: str) -> list[str]:
    raw = git("log", "--format=%s", "--max-count=8", f"{main}..{head}", check=False)
    return [line.strip() for line in raw.splitlines() if line.strip()]


def archive_tags_for(head: str, tags: list[tuple[str, str]]) -> list[str]:
    return [name for name, peeled in tags if peeled.lower() == head.lower()]


@lru_cache(maxsize=None)
def blob_id(ref: str, path: str) -> str:
    """Return a tree blob identity without treating a missing path as equal."""
    return git("rev-parse", f"{ref}:{path}", check=False).strip()


def preservation_evidence(
    head: str,
    main: str,
    successors: list[str],
    preservation_paths: list[str],
) -> tuple[str, str, str, list[str]]:
    """Prove preservation by ancestry first, then exact file-content equality."""
    candidates: list[tuple[str, str]] = [("main", main)]
    candidates.extend((name, f"{REMOTE_PREFIX}{name}") for name in successors)
    for name, ref in candidates:
        if git_ok("merge-base", "--is-ancestor", head, ref):
            return "YES", name, "ANCESTOR", []
    if preservation_paths:
        for name, ref in candidates:
            mismatches = [
                path for path in preservation_paths
                if not blob_id(head, path) or blob_id(head, path) != blob_id(ref, path)
            ]
            if not mismatches:
                return "YES", name, "FILE_CONTENT_EQUIVALENT", []
        unpreserved = [
            path for path in preservation_paths
            if not any(
                blob_id(head, path) and blob_id(head, path) == blob_id(ref, path)
                for _, ref in candidates
            )
        ]
        return "NO", "", "NONE", unpreserved
    return "NOT_APPLICABLE", "", "NONE", []


def branch_slug(branch: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", branch).strip("-").lower()


def load_prior() -> dict[str, dict[str, str]]:
    # Pin the comparison source to the reviewed remediation parent.  The
    # report is written before the consistency gate completes, so reading the
    # mutable output file here could accidentally compare against a partial
    # failed run instead of bf04167.
    raw = git(
        "show",
        "bf04167fff3615b98e291ac9f3be5947cdb24b7f:docs/repository_hygiene/BRANCH_FORENSIC_INVENTORY_V1.csv",
        check=False,
    )
    if raw and not raw.startswith("fatal:"):
        return {row["branch_name"]: row for row in csv.DictReader(raw.splitlines())}
    path = ROOT / "docs" / "repository_hygiene" / "BRANCH_INVENTORY_V1.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["branch_name"]: row for row in csv.DictReader(handle)}


def build_inventory() -> tuple[list[dict[str, str]], str]:
    refs = current_refs()
    main = git("rev-parse", "refs/remotes/origin/main").strip()
    status_text = git("show", "origin/main:coordination/TEAM_STATUS.md")
    status_lines = status_text.splitlines()
    prior = load_prior()
    tag_lines = git("for-each-ref", "--format=%(refname)|%(objectname)", "refs/tags").splitlines()
    all_tags: list[tuple[str, str]] = []
    for line in tag_lines:
        ref, tag_object = line.split("|", 1)
        if ref.endswith("^{}"):
            continue
        tag_name = ref.removeprefix("refs/tags/")
        peeled = git("rev-parse", f"{ref}^{{commit}}", check=False).strip()
        if peeled:
            all_tags.append((tag_name, peeled))

    initial: list[dict[str, str]] = []
    for branch, ref_value in sorted(refs.items()):
        head, date = ref_value.split("|", 1)
        matching_status_lines = [line for line in status_lines if branch in line]
        statuses = sorted({status for line in matching_status_lines if (status := parse_status(line))})
        branch_hits = grep_refs(branch)
        head_hits = grep_refs(head)
        branch_local_hits = branch_evidence(head)
        all_hits = branch_hits + [hit for hit in head_hits if hit not in branch_hits]
        all_hits += [hit for hit in branch_local_hits if hit not in all_hits]
        decision_hits = [hit for hit in all_hits if is_scientific_decision_evidence(*hit)]
        verdict_hits = decision_hits
        counts = git("rev-list", "--left-right", "--count", f"{main}...{head}").strip().split()
        behind, ahead = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (0, 0)
        reachable_main = git_ok("merge-base", "--is-ancestor", head, main)
        paths = unique_paths(head, main)
        messages = unique_messages(head, main)
        source_paths = [
            path for path in paths
            if path.startswith(("src/", "apps/", "frontend/", "tests/", "config/", ".github/"))
            or path == "pyproject.toml"
        ]
        protected = any(token in branch.lower() for token in PROTECTED_TOKENS)
        has_decision = bool(decision_hits)
        prior_row = prior.get(branch, {})
        old_class = prior_row.get("prior_classification") or prior_row.get("classification") or "NEW_NOT_IN_PRIOR_AUDIT"
        prior_forensic_class = prior_row.get("proposed_classification", "")
        initial.append(
            {
                "branch_name": branch,
                "head_sha": head,
                "last_commit_date": date,
                "ahead_vs_main": str(ahead),
                "behind_vs_main": str(behind),
                "head_reachable_from_main": str(reachable_main).lower(),
                "prior_classification": old_class,
                "previous_forensic_classification": prior_forensic_class,
                "team_status": ";".join(statuses) or "NONE",
                "status_references": ";".join(f"coordination/TEAM_STATUS.md:{status_lines.index(line) + 1}" for line in matching_status_lines),
                "document_references": ";".join(sorted({ref for ref, _ in all_hits})),
                "branch_document_references": ";".join(sorted({ref for ref, _ in branch_local_hits})),
                "head_sha_references": ";".join(sorted({ref for ref, text in head_hits})),
                "archive_tags": ";".join(archive_tags_for(head, all_tags)),
                "unique_commit_count": str(ahead),
                "unique_changed_paths": ";".join(paths[:80]),
                "all_unique_changed_paths": ";".join(paths),
                "unique_commit_messages": " || ".join(messages),
                "scientific_decision": "VALID_DECISION_EVIDENCE" if has_decision else "NO_SCIENTIFIC_DECISION_EVIDENCE",
                "decision_evidence_source": "+".join(
                    source for source, hits in (
                        ("CURRENT_MAIN", branch_hits + head_hits),
                        ("BRANCH_LOCAL", branch_local_hits),
                    ) if hits and any(is_scientific_decision_evidence(ref, text) for ref, text in hits)
                ) or "NONE",
                "verdict_evidence": " || ".join(text for _, text in verdict_hits[:8]),
                "reusable_implementation": "YES" if source_paths else "NO",
                "reusable_paths": ";".join(source_paths[:40]),
                "protected_lineage": "YES" if protected else "NO",
            }
        )

    keep_names = {
        row["branch_name"]
        for row in initial
        if row["branch_name"] == "main"
        or row["protected_lineage"] == "YES"
        or any(status in LIVE_STATUSES for status in row["team_status"].split(";"))
    }
    for row in initial:
        head = row["head_sha"]
        branch = row["branch_name"]
        containing = git("for-each-ref", "--contains", head, "--format=%(refname)", "refs/remotes/origin", check=False).splitlines()
        successors = [
            ref.removeprefix(REMOTE_PREFIX)
            for ref in containing
            if ref.startswith(REMOTE_PREFIX)
            and ref.removeprefix(REMOTE_PREFIX) in keep_names
            and ref.removeprefix(REMOTE_PREFIX) != branch
        ]
        successors.sort(key=lambda name: (0 if name == "main" else 1, len(name), name))
        row["retained_successor_branch"] = successors[0] if successors else ""
        row["reachable_from_retained_successor"] = str(bool(successors)).lower()

        all_paths = [path for path in row["all_unique_changed_paths"].split(";") if path]
        preservation_paths = [
            path for path in all_paths
            if path.startswith(("src/", "apps/", "frontend/", "tests/", "config/", ".github/"))
            or path in {"AGENTS.md", "pyproject.toml"}
        ]
        preserved, preserved_by, preservation_method, unpreserved = preservation_evidence(
            head, main, successors, preservation_paths
        )
        row["implementation_preserved"] = preserved
        row["preserved_by_branch"] = preserved_by
        row["preservation_method"] = preservation_method
        row["unpreserved_unique_paths"] = ";".join(unpreserved)
        row["unpreserved_unique_path_count"] = str(len(unpreserved))

        has_live_status = any(status in LIVE_STATUSES for status in row["team_status"].split(";"))
        if branch == "main" or row["protected_lineage"] == "YES" or has_live_status:
            proposed = "KEEP"
            reason = "Live/protected/canonical coordination lineage; retain by policy."
        elif row["scientific_decision"] == "VALID_DECISION_EVIDENCE":
            proposed = "ARCHIVE_TAG_THEN_DELETE"
            reason = "Meaningful decision/verdict or explicit DONE evidence is retained in current documentation; preserve exact HEAD with a proposed archive tag."
        elif row["reusable_implementation"] == "YES" and preserved != "YES":
            proposed = "NEEDS_MANUAL_REVIEW"
            reason = "Unique source/test/config implementation is not proven preserved by main or a retained successor; do not tombstone or delete-safe."
        elif preservation_method in {"ANCESTOR", "FILE_CONTENT_EQUIVALENT"} and row["scientific_decision"] != "VALID_DECISION_EVIDENCE":
            proposed = "DELETE_SAFE"
            reason = f"No independent scientific decision; unique implementation preservation is proven by {preservation_method} via {preserved_by}."
        elif row["reusable_implementation"] == "NO" and row["scientific_decision"] != "VALID_DECISION_EVIDENCE":
            proposed = "TOMBSTONE_THEN_DELETE"
            reason = "No valid scientific decision and no reusable source/test/config implementation; preserve one compact tombstone before deletion."
        else:
            proposed = "NEEDS_MANUAL_REVIEW"
            reason = "Lineage or preservation evidence is insufficient for a safe automated disposition."
        row["proposed_classification"] = proposed
        row["reason"] = reason
        row["archive_tag_suggestion"] = f"archive/{branch_slug(branch)}-{head[:12]}" if proposed == "ARCHIVE_TAG_THEN_DELETE" else ""
        row["tombstone_text"] = f"branch={branch}; HEAD={head}; attempted_scope={row['unique_commit_messages'][:180] or 'unknown'}; why_abandoned={reason}; NO_SCIENTIFIC_DECISION" if proposed == "TOMBSTONE_THEN_DELETE" else ""
    return initial, main


def load_pr_metadata() -> list[dict[str, str]]:
    """Reuse the authenticated PR snapshot; this pass must not mutate GitHub."""
    path = ROOT / "docs" / "repository_hygiene" / "PR_FORENSIC_PLAN_V1.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def derive_pr_plan(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_branch = {row["branch_name"]: row for row in rows}
    result: list[dict[str, str]] = []
    for old in load_pr_metadata():
        branch = old.get("head_branch", "")
        row = by_branch.get(branch)
        branch_head = row["head_sha"] if row else ""
        pr_head = old.get("pr_head_sha", "")
        head_match = str(bool(branch_head and pr_head and branch_head.lower() == pr_head.lower())).upper()
        disposition = row["proposed_classification"] if row else "UNKNOWN_BRANCH"
        state = old.get("state", "UNKNOWN")
        if state != "OPEN":
            recommendation = "ALREADY_CLOSED_NO_ACTION"
            reason = "PR is already closed; no PR mutation is part of this dry run."
        elif not row or head_match != "TRUE":
            recommendation = "NEEDS_REVIEW"
            reason = "Open PR branch is missing or PR head SHA differs from the current remote branch; do not silently plan a mutation."
        elif disposition == "KEEP":
            recommendation = "KEEP_OPEN"
            reason = "Final branch disposition is KEEP."
        elif disposition == "ARCHIVE_TAG_THEN_DELETE":
            recommendation = "CLOSE_AFTER_ARCHIVE"
            reason = "Final branch disposition is ARCHIVE_TAG_THEN_DELETE; archive/tag verification must precede any later PR closure."
        elif disposition == "TOMBSTONE_THEN_DELETE":
            recommendation = "CLOSE_AFTER_TOMBSTONE"
            reason = "Final branch disposition is TOMBSTONE_THEN_DELETE; write/verify the compact tombstone before any later PR closure."
        elif disposition == "DELETE_SAFE":
            recommendation = "CLOSE_BEFORE_DELETE"
            reason = "Final branch disposition is DELETE_SAFE; PR closure remains a separate authorized action before any later branch deletion."
        else:
            recommendation = "NEEDS_REVIEW"
            reason = "Final branch disposition remains NEEDS_MANUAL_REVIEW."
        result.append(
            {
                "pr_number": old.get("pr_number", ""),
                "state": state,
                "draft": old.get("draft", ""),
                "merged": old.get("merged", ""),
                "head_branch": branch,
                "pr_head_sha": pr_head,
                "current_remote_head": branch_head,
                "head_match": head_match,
                "base_branch": old.get("base_branch", ""),
                "branch_disposition": disposition,
                "recommendation": recommendation,
                "reason": reason,
            }
        )
    return result


def consistency_gate(rows: list[dict[str, str]], prs: list[dict[str, str]]) -> None:
    by_branch = {row["branch_name"]: row for row in rows}
    for row in rows:
        disposition = row["proposed_classification"]
        if disposition == "TOMBSTONE_THEN_DELETE" and row["reusable_implementation"] == "YES":
            raise RuntimeError(f"consistency gate: tombstone has reusable implementation: {row['branch_name']}")
        if disposition == "DELETE_SAFE":
            if row["scientific_decision"] == "VALID_DECISION_EVIDENCE":
                raise RuntimeError(f"consistency gate: delete-safe has independent decision: {row['branch_name']}")
            if row["preservation_method"] not in {"ANCESTOR", "FILE_CONTENT_EQUIVALENT"}:
                raise RuntimeError(f"consistency gate: delete-safe lacks preservation proof: {row['branch_name']}")
        if row["reusable_implementation"] == "YES" and row["implementation_preserved"] != "YES" and disposition in {"TOMBSTONE_THEN_DELETE", "DELETE_SAFE"}:
            raise RuntimeError(f"consistency gate: unpreserved implementation disposition: {row['branch_name']}")

    for pr in prs:
        row = by_branch.get(pr["head_branch"])
        if not row:
            continue
        disposition = row["proposed_classification"]
        recommendation = pr["recommendation"]
        if disposition == "KEEP" and recommendation == "CLOSE_AFTER_ARCHIVE":
            raise RuntimeError(f"consistency gate: KEEP PR proposed for archive closure: PR {pr['pr_number']}")
        if disposition == "ARCHIVE_TAG_THEN_DELETE" and recommendation == "KEEP_OPEN":
            raise RuntimeError(f"consistency gate: archive branch PR kept open without exception: PR {pr['pr_number']}")
        if pr["state"] == "OPEN" and pr["head_match"] != "TRUE" and recommendation != "NEEDS_REVIEW":
            raise RuntimeError(f"consistency gate: open PR head mismatch ignored: PR {pr['pr_number']}")
        if pr["state"] == "OPEN" and disposition == "TOMBSTONE_THEN_DELETE" and recommendation not in {"CLOSE_AFTER_TOMBSTONE", "NEEDS_REVIEW"}:
            raise RuntimeError(f"consistency gate: tombstone PR recommendation mismatch: PR {pr['pr_number']}")
        if pr["state"] == "OPEN" and disposition == "DELETE_SAFE" and recommendation not in {"CLOSE_BEFORE_DELETE", "NEEDS_REVIEW"}:
            raise RuntimeError(f"consistency gate: delete-safe PR recommendation mismatch: PR {pr['pr_number']}")


def write_reports(rows: list[dict[str, str]], main: str) -> None:
    output = ROOT / "docs" / "repository_hygiene"
    output.mkdir(parents=True, exist_ok=True)
    fields = [
        "branch_name", "head_sha", "last_commit_date", "ahead_vs_main", "behind_vs_main",
        "head_reachable_from_main", "reachable_from_retained_successor", "retained_successor_branch",
        "prior_classification", "previous_forensic_classification", "team_status", "status_references", "document_references",
        "branch_document_references",
        "head_sha_references", "archive_tags", "unique_commit_count", "unique_changed_paths",
        "all_unique_changed_paths",
        "unique_commit_messages", "scientific_decision", "decision_evidence_source", "verdict_evidence", "reusable_implementation",
        "reusable_paths", "protected_lineage", "implementation_preserved", "preserved_by_branch",
        "preservation_method", "unpreserved_unique_paths", "unpreserved_unique_path_count",
        "proposed_classification", "archive_tag_suggestion",
        "tombstone_text", "reason",
    ]
    with (output / "BRANCH_FORENSIC_INVENTORY_V1.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    pr_rows = derive_pr_plan(rows)
    consistency_gate(rows, pr_rows)
    pr_fields = [
        "pr_number", "state", "draft", "merged", "head_branch", "pr_head_sha",
        "current_remote_head", "head_match", "base_branch", "branch_disposition",
        "recommendation", "reason",
    ]
    with (output / "PR_FORENSIC_PLAN_V1.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=pr_fields)
        writer.writeheader()
        writer.writerows(pr_rows)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["proposed_classification"]] = counts.get(row["proposed_classification"], 0) + 1
    current_count = len(rows)
    archive_count = counts.get("ARCHIVE_TAG_THEN_DELETE", 0)
    tombstone_count = counts.get("TOMBSTONE_THEN_DELETE", 0)
    delete_count = counts.get("DELETE_SAFE", 0)
    plan_lines = [
        "# Repository Hygiene V1 — Batch 3 Forensic / Dry-Run Plan",
        "",
        "## Scope and safety",
        "",
        f"Current remote branch inventory: **{current_count}** unique branches; current `origin/main`: `{main}`.",
        "This is a forensic dry run only. No branch, tag, PR, history, source, runtime, model, or data mutation is authorized or performed.",
        "The prior 160-branch classification is retained only as a comparison column; proposed classes below are recomputed from the current remote refs, current-main references, exact HEAD evidence, reachability, and lineage inspection.",
        "",
        "## Proposed class counts and estimated branch counts",
        "",
        "| Proposed class | Count | Estimated count after this class only |",
        "|---|---:|---:|",
        f"| KEEP | {counts.get('KEEP', 0)} | {current_count} |",
        f"| ARCHIVE_TAG_THEN_DELETE | {archive_count} | {current_count - archive_count} |",
        f"| TOMBSTONE_THEN_DELETE | {tombstone_count} | {current_count - archive_count - tombstone_count} |",
        f"| DELETE_SAFE | {delete_count} | {current_count - archive_count - tombstone_count - delete_count} |",
        f"| NEEDS_MANUAL_REVIEW | {counts.get('NEEDS_MANUAL_REVIEW', 0)} | retained pending review |",
        "",
        "Counts are estimates only; no proposed cleanup action is executed in this pass.",
        "",
        "## Internal consistency gate",
        "",
        "PASS — tombstones have no reusable source/test/config implementation; DELETE_SAFE rows have ancestry or exact file-content preservation proof and no independent scientific decision; PR recommendations are derived from the final branch disposition; open PR head mismatches are explicit NEEDS_REVIEW.",
        "",
        "## Disposition changes from the previous forensic snapshot",
        "",
    ]
    changed_rows = [
        row for row in rows
        if row["previous_forensic_classification"]
        and row["previous_forensic_classification"] != row["proposed_classification"]
    ]
    new_rows = [row for row in rows if not row["previous_forensic_classification"]]
    plan_lines.extend(
        f"- `{row['branch_name']}`: `{row['previous_forensic_classification']}` -> `{row['proposed_classification']}`; preservation=`{row['preservation_method']}`; unpreserved_unique_paths={row['unpreserved_unique_path_count']}."
        for row in changed_rows
    )
    plan_lines.extend(
        f"- NEW `{row['branch_name']}`: `{row['proposed_classification']}`; preservation=`{row['preservation_method']}`."
        for row in new_rows
    )
    if not changed_rows and not new_rows:
        plan_lines.append("- None.")
    pr_counts: dict[str, int] = {}
    for pr in pr_rows:
        pr_counts[pr["recommendation"]] = pr_counts.get(pr["recommendation"], 0) + 1
    plan_lines.extend(
        [
            "",
            "## PR disposition derivation",
            "",
            "Recommendations: " + ", ".join(f"{key}={value}" for key, value in sorted(pr_counts.items())) + ".",
            "Every PR row records current remote head, PR head, explicit head_match, final branch disposition, and derived recommendation.",
            "",
        ]
    )
    plan_lines.extend([
        "## Proposed archive tags",
        "",
    ])
    archive_rows = [row for row in rows if row["proposed_classification"] == "ARCHIVE_TAG_THEN_DELETE"]
    plan_lines.extend(
        f"- `{row['branch_name']}` at `{row['head_sha']}` -> `{row['archive_tag_suggestion']}` — {row['reason']}"
        for row in archive_rows
    )
    if not archive_rows:
        plan_lines.append("- None.")
    plan_lines.extend(["", "## Proposed tombstones (not created)", ""])
    tombstone_rows = [row for row in rows if row["proposed_classification"] == "TOMBSTONE_THEN_DELETE"]
    plan_lines.extend(f"- `{row['tombstone_text']}`" for row in tombstone_rows)
    if not tombstone_rows:
        plan_lines.append("- None.")
    plan_lines.extend(["", "## NEEDS_MANUAL_REVIEW queue", ""])
    manual_rows = [row for row in rows if row["proposed_classification"] == "NEEDS_MANUAL_REVIEW"]
    plan_lines.extend(
        f"- `{row['branch_name']}` at `{row['head_sha']}` — {row['reason']} Unique paths: `{row['reusable_paths'] or 'none'}`."
        for row in manual_rows
    )
    if not manual_rows:
        plan_lines.append("- None.")
    plan_lines.extend(
        [
            "",
            "## Sensitive lineage notes",
            "",
            "Old Stage3/4/4B/5, OPEN/Yahoo/Wildan, forward/runtime, free-float/HSC/LBRE, data-foundation, and review branches are not auto-deleted merely because they are old or failed. Any branch with live/protected status, a valid verdict, or unique implementation remains KEEP, ARCHIVE_TAG_THEN_DELETE, or NEEDS_MANUAL_REVIEW pending explicit review.",
            "",
            "## Evidence contract",
            "",
            "The CSV records exact current HEAD/date, ahead/behind, main/successor reachability, unique commit count, changed paths, commit-message summaries, current-main and branch-local document references, exact HEAD references, archive tags, scientific-decision source, reusable implementation paths, implementation_preserved, preserved_by_branch, preservation_method, and unpreserved unique paths/count. GitHub PR metadata is derived from the final branch disposition in `PR_FORENSIC_PLAN_V1.csv`; branch/PR head mismatches are explicit.",
            "",
        ]
    )
    (output / "BRANCH_FORENSIC_PLAN_V1.md").write_text("\n".join(plan_lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    rows, main_head = build_inventory()
    write_reports(rows, main_head)
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["proposed_classification"]] = counts.get(item["proposed_classification"], 0) + 1
    print(f"remote_branch_count={len(rows)}")
    print(f"main_head={main_head}")
    for key in ("KEEP", "ARCHIVE_TAG_THEN_DELETE", "TOMBSTONE_THEN_DELETE", "DELETE_SAFE", "NEEDS_MANUAL_REVIEW"):
        print(f"{key}={counts.get(key, 0)}")
