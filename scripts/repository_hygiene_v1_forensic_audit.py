from __future__ import annotations

import csv
import re
import subprocess
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

# Batch-3 forensic overrides for the surviving rows that Batch 2 classified as
# ABANDONED_NO_DECISION.  These are evidence-backed dispositions from the
# read-only forensic pass, not cleanup actions.  A completed scientific/data
# lane with a meaningful result is archiveable; an unresolved current lane is
# manual; a pure engineering attempt gets a compact tombstone proposal.
ABANDONED_TOMBSTONE = {
    "ci/quality-gates",
    "data/idx-data-002c-codex-cache",
    "data/idx-data-005-1260-prep",
}
ABANDONED_MANUAL = {
    "data/idx-delisting-effective-date-semantics-v1",
    "integration/personal-ksei-bounded-auth-design-v1",
    "integration/schema-contract-prep-v1",
    "integration/schema-review-v1",
}
ABANDONED_DELETE_SAFE = {"docs/model-architecture"}
ABANDONED_KEEP = {"review/idx-joint-setup-readiness-state-v1-acceptance"}


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
            "AGENTS.md",
            "docs",
            "coordination",
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


def branch_slug(branch: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", branch).strip("-").lower()


def load_prior() -> dict[str, dict[str, str]]:
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
        all_hits = branch_hits + [hit for hit in head_hits if hit not in branch_hits]
        decision_hits = [hit for hit in all_hits if re.search(r"accept|reject|verdict|decision|checkpoint|handoff|manifest|spec", hit[1], re.I)]
        verdict_hits = [hit for hit in all_hits if re.search(r"accepted|rejected|verdict|no_go|pass|fail", hit[1], re.I)]
        counts = git("rev-list", "--left-right", "--count", f"{main}...{head}").strip().split()
        behind, ahead = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (0, 0)
        reachable_main = git_ok("merge-base", "--is-ancestor", head, main)
        paths = unique_paths(head, main)
        messages = unique_messages(head, main)
        source_paths = [path for path in paths if path.startswith(("src/", "apps/", "frontend/", "tests/", "config/"))]
        protected = any(token in branch.lower() for token in PROTECTED_TOKENS)
        has_decision = bool(decision_hits or verdict_hits or "DONE" in statuses)
        old_class = prior.get(branch, {}).get("classification", "NEW_NOT_IN_PRIOR_AUDIT")
        initial.append(
            {
                "branch_name": branch,
                "head_sha": head,
                "last_commit_date": date,
                "ahead_vs_main": str(ahead),
                "behind_vs_main": str(behind),
                "head_reachable_from_main": str(reachable_main).lower(),
                "prior_classification": old_class,
                "team_status": ";".join(statuses) or "NONE",
                "status_references": ";".join(f"coordination/TEAM_STATUS.md:{status_lines.index(line) + 1}" for line in matching_status_lines),
                "document_references": ";".join(sorted({ref for ref, _ in all_hits})),
                "head_sha_references": ";".join(sorted({ref for ref, text in head_hits})),
                "archive_tags": ";".join(archive_tags_for(head, all_tags)),
                "unique_commit_count": str(ahead),
                "unique_changed_paths": ";".join(paths[:80]),
                "unique_commit_messages": " || ".join(messages),
                "scientific_decision": "VALID_DECISION_EVIDENCE" if has_decision else "NO_SCIENTIFIC_DECISION_EVIDENCE",
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
        prior_abandoned = row["prior_classification"] == "ABANDONED_NO_DECISION"
        if prior_abandoned and branch in ABANDONED_KEEP:
            proposed = "KEEP"
            reason = "Current acceptance/reference lineage is still explicitly used by retained successors; keep the exact branch anchor."
        elif prior_abandoned and branch in ABANDONED_MANUAL:
            proposed = "NEEDS_MANUAL_REVIEW"
            reason = "Current/security-sensitive or recent lineage has unresolved ownership or status; do not archive from branch history alone."
        elif prior_abandoned and branch in ABANDONED_DELETE_SAFE:
            proposed = "DELETE_SAFE"
            reason = "Unique engineering/document attempt is reachable from current main with no independent scientific decision or reusable implementation."
        elif prior_abandoned and branch in ABANDONED_TOMBSTONE:
            proposed = "TOMBSTONE_THEN_DELETE"
            reason = "Unmerged attempt has no valid scientific decision and no retained implementation; propose one compact historical tombstone before deletion."
        elif prior_abandoned:
            proposed = "ARCHIVE_TAG_THEN_DELETE"
            reason = "Completed/rejected historical lane has meaningful forensic evidence or a scientific/data lesson; preserve exact HEAD with a proposed archive tag before any later deletion."
        elif branch == "main" or row["protected_lineage"] == "YES" or any(status in LIVE_STATUSES for status in row["team_status"].split(";")):
            proposed = "KEEP"
            reason = "Live/protected/canonical coordination lineage; retain by policy."
        elif row["scientific_decision"] == "VALID_DECISION_EVIDENCE":
            proposed = "ARCHIVE_TAG_THEN_DELETE"
            reason = "Meaningful decision/verdict or explicit DONE evidence is retained in current documentation; preserve exact HEAD with a proposed archive tag."
        elif row["reusable_implementation"] == "YES":
            proposed = "NEEDS_MANUAL_REVIEW"
            reason = "No valid scientific decision was found, but unique source/test/config implementation may be reusable; do not tombstone without review."
        elif row["head_reachable_from_main"] == "true":
            proposed = "DELETE_SAFE"
            reason = "HEAD is reachable from current main and no independent decision or unique implementation evidence was found."
        else:
            proposed = "TOMBSTONE_THEN_DELETE"
            reason = "Unmerged unique attempt has no valid scientific decision and no reusable implementation; preserve one compact tombstone before deletion."
        row["proposed_classification"] = proposed
        row["reason"] = reason
        row["archive_tag_suggestion"] = f"archive/{branch_slug(branch)}-{head[:12]}" if proposed == "ARCHIVE_TAG_THEN_DELETE" else ""
        row["tombstone_text"] = f"branch={branch}; HEAD={head}; attempted_scope={row['unique_commit_messages'][:180] or 'unknown'}; why_abandoned={reason}; NO_SCIENTIFIC_DECISION" if proposed == "TOMBSTONE_THEN_DELETE" else ""
        containing = git("for-each-ref", "--contains", head, "--format=%(refname)", "refs/remotes/origin", check=False).splitlines()
        successors = [ref.removeprefix(REMOTE_PREFIX) for ref in containing if ref.startswith(REMOTE_PREFIX) and ref.removeprefix(REMOTE_PREFIX) in keep_names and ref.removeprefix(REMOTE_PREFIX) != branch]
        successors.sort(key=lambda name: (0 if name == "main" else 1, len(name), name))
        row["retained_successor_branch"] = successors[0] if successors else ""
        row["reachable_from_retained_successor"] = str(bool(successors)).lower()
    return initial, main


def write_reports(rows: list[dict[str, str]], main: str) -> None:
    output = ROOT / "docs" / "repository_hygiene"
    output.mkdir(parents=True, exist_ok=True)
    fields = [
        "branch_name", "head_sha", "last_commit_date", "ahead_vs_main", "behind_vs_main",
        "head_reachable_from_main", "reachable_from_retained_successor", "retained_successor_branch",
        "prior_classification", "team_status", "status_references", "document_references",
        "head_sha_references", "archive_tags", "unique_commit_count", "unique_changed_paths",
        "unique_commit_messages", "scientific_decision", "verdict_evidence", "reusable_implementation",
        "reusable_paths", "protected_lineage", "proposed_classification", "archive_tag_suggestion",
        "tombstone_text", "reason",
    ]
    with (output / "BRANCH_FORENSIC_INVENTORY_V1.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

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
        "## Proposed archive tags",
        "",
    ]
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
            "The CSV records exact current HEAD/date, ahead/behind, main/successor reachability, unique commit count, changed paths, commit-message summaries, current-main references, exact HEAD references, archive tags, scientific-decision evidence, and reusable implementation paths. GitHub PR metadata is documented separately in `PR_FORENSIC_PLAN_V1.csv`; unknown metadata remains unknown.",
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
