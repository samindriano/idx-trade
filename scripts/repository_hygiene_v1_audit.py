from __future__ import annotations

import csv
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REMOTE_PREFIX = "refs/remotes/origin/"
STATUSES = {"PLANNED", "ACTIVE", "AUTOMATED", "WAITING", "BLOCKED", "REVIEW", "DONE", "PARKED"}
KEEP_STATUSES = {"PLANNED", "ACTIVE", "AUTOMATED", "WAITING", "BLOCKED", "REVIEW", "PARKED"}
SCIENTIFIC_PREFIXES = ("data/", "research/", "integration/", "review/", "codex/")
TEMP_PREFIXES = ("worker/", "tmp/", "scratch/", "chore/", "ci/", "test/", "fix/", "refactor/", "feature/")
PROTECTED_NAME_TOKENS = ("o2", "foreign-flow", "price-state", "forward", "stockbit", "runtime")


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


def status_from_line(line: str) -> str | None:
    match = re.search(r"\|\s*`?(PLANNED|ACTIVE|AUTOMATED|WAITING|BLOCKED|REVIEW|DONE|PARKED)`?\s*\|", line)
    return match.group(1) if match else None


def branch_slug(branch: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", branch).strip("-").lower()


@dataclass
class Branch:
    name: str
    head: str
    date: str
    ahead: int = 0
    behind: int = 0
    reachable_main: bool = False
    status_refs: list[str] = field(default_factory=list)
    doc_refs: list[str] = field(default_factory=list)
    head_refs: list[str] = field(default_factory=list)
    local_pr_refs: list[str] = field(default_factory=list)
    decision_refs: list[str] = field(default_factory=list)
    acceptance_shas: list[str] = field(default_factory=list)
    classification: str = "NEEDS_MANUAL_REVIEW"
    reason: str = ""
    successor: str = ""
    successor_sha: str = ""

    @property
    def statuses(self) -> set[str]:
        return {s for s in self.status_refs if s in STATUSES}

    @property
    def has_decision_evidence(self) -> bool:
        return bool(self.decision_refs or self.head_refs)


def inventory() -> tuple[list[Branch], str]:
    main_head = git("rev-parse", "refs/remotes/origin/main").strip()
    rows: list[Branch] = []
    raw = git("for-each-ref", "--format=%(refname)|%(objectname)|%(committerdate:iso8601-strict)", "refs/remotes/origin")
    for line in raw.splitlines():
        ref, head, date = line.split("|", 2)
        if not ref.startswith(REMOTE_PREFIX) or ref == f"{REMOTE_PREFIX}HEAD":
            continue
        rows.append(Branch(ref[len(REMOTE_PREFIX) :], head, date))

    status_text = git("show", "origin/main:coordination/TEAM_STATUS.md")
    for row in rows:
        for line in status_text.splitlines():
            if row.name in line:
                status = status_from_line(line)
                if status:
                    row.status_refs.append(status)
                row.doc_refs.append(f"coordination/TEAM_STATUS.md:{status_text.splitlines().index(line) + 1}")

        for query, is_head in ((row.name, False), (row.head, True)):
            result = subprocess.run(
                ["git", "grep", "--no-color", "-n", "-I", "-F", query, "origin/main", "--", "AGENTS.md", "docs", "coordination"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            for match_line in result.stdout.splitlines()[:40]:
                parts = match_line.split(":", 2)
                if len(parts) != 3:
                    continue
                path, line_no, content = parts
                ref = f"{path}:{line_no}"
                if ref not in row.doc_refs:
                    row.doc_refs.append(ref)
                if is_head and ref not in row.head_refs:
                    row.head_refs.append(ref)
                for pr in re.findall(r"PR\s*#\s*\d+", content, flags=re.IGNORECASE):
                    if pr.upper() not in row.local_pr_refs:
                        row.local_pr_refs.append(pr.upper())
                if re.search(r"accept|successor|review", content, flags=re.IGNORECASE):
                    for sha in re.findall(r"\b[0-9a-f]{40}\b", content, flags=re.IGNORECASE):
                        if sha.lower() != row.head.lower() and sha.lower() not in {item.lower() for item in row.acceptance_shas}:
                            row.acceptance_shas.append(sha)
                if re.search(r"accept|reject|verdict|decision|checkpoint|handoff|manifest|spec", content, flags=re.IGNORECASE):
                    if ref not in row.decision_refs:
                        row.decision_refs.append(ref)

    for row in rows:
        counts = git("rev-list", "--left-right", "--count", f"refs/remotes/origin/main...refs/remotes/origin/{row.name}").strip().split()
        row.behind, row.ahead = int(counts[0]), int(counts[1])
        row.reachable_main = subprocess.run(
            ["git", "merge-base", "--is-ancestor", row.head, main_head],
            cwd=ROOT,
            check=False,
        ).returncode == 0

        if row.name == "main":
            row.classification = "KEEP"
            row.reason = "Canonical retained branch and coordination source."
        elif any(token in row.name.lower() for token in PROTECTED_NAME_TOKENS):
            row.classification = "KEEP"
            row.reason = "Protected O2/Foreign-Flow/Price-State/forward/runtime lineage; retain by repository hygiene policy."
        elif row.statuses & KEEP_STATUSES:
            row.classification = "KEEP"
            row.reason = f"Live coordination status {','.join(sorted(row.statuses & KEEP_STATUSES))}; do not retire active or parked work."
        elif row.reachable_main and row.name.startswith(TEMP_PREFIXES) and not row.has_decision_evidence:
            row.classification = "DELETE_SAFE"
            row.reason = "Temporary/engineering branch is fully reachable from main and has no scientific decision reference."
        elif row.statuses == {"DONE"} and row.name.startswith(SCIENTIFIC_PREFIXES) and row.has_decision_evidence:
            row.classification = "ARCHIVE_TAG_THEN_DELETE_BRANCH"
            row.reason = "Scientific lane is DONE and its decision/reference is documented; preserve exact HEAD/verdict with a proposed archive tag before deletion."
        elif row.name.startswith(SCIENTIFIC_PREFIXES) and row.reachable_main and row.has_decision_evidence:
            row.classification = "ARCHIVE_TAG_THEN_DELETE_BRANCH"
            row.reason = "Scientific branch HEAD is retained by main documentation; archive exact HEAD before optional branch deletion."
        elif row.name.startswith(SCIENTIFIC_PREFIXES) and not row.reachable_main and row.has_decision_evidence:
            row.classification = "NEEDS_MANUAL_REVIEW"
            row.reason = "Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor."
        elif row.name.startswith(SCIENTIFIC_PREFIXES) and row.reachable_main:
            row.classification = "NEEDS_MANUAL_REVIEW"
            row.reason = "Scientific branch is merged but no explicit status/decision anchor was found; review manually before retirement."
        elif row.reachable_main and not row.has_decision_evidence:
            row.classification = "DELETE_SAFE"
            row.reason = "HEAD is fully reachable from main and no tracked scientific decision reference was found."
        elif not row.reachable_main and not row.doc_refs:
            row.classification = "ABANDONED_NO_DECISION"
            row.reason = "Not reachable from main and no tracked status/handoff/checkpoint/spec/manifest reference was found."
        else:
            row.classification = "NEEDS_MANUAL_REVIEW"
            row.reason = "Lineage or retention decision remains ambiguous."

    keep_heads = {row.head: row for row in rows if row.classification == "KEEP"}
    for row in rows:
        if row.reachable_main:
            row.successor = "main"
            row.successor_sha = main_head
            continue
        containing = git("for-each-ref", "--contains", row.head, "--format=%(refname)", "refs/remotes/origin").splitlines()
        candidates = [
            ref[len(REMOTE_PREFIX) :]
            for ref in containing
            if ref.startswith(REMOTE_PREFIX)
            and ref != f"{REMOTE_PREFIX}{row.name}"
            and ref[len(REMOTE_PREFIX) :] in {candidate.name for candidate in keep_heads.values()}
        ]
        if candidates:
            candidates.sort(key=lambda name: (0 if name == "main" else 1, len(name), name))
            row.successor = candidates[0]
            row.successor_sha = next(candidate.head for candidate in rows if candidate.name == row.successor)

    return sorted(rows, key=lambda row: row.name), main_head


def write_reports(rows: list[Branch], main_head: str) -> None:
    output = ROOT / "docs" / "repository_hygiene"
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "BRANCH_INVENTORY_V1.csv"
    fields = [
        "branch_name",
        "head_sha",
        "last_commit_date",
        "ahead_vs_main",
        "behind_vs_main",
        "head_reachable_from_main",
        "reachable_from_retained_successor",
        "retained_successor_branch",
        "successor_or_acceptance_sha",
        "related_pr",
        "related_pr_status",
        "team_status_references",
        "repository_document_references",
        "classification",
        "reason",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "branch_name": row.name,
                    "head_sha": row.head,
                    "last_commit_date": row.date,
                    "ahead_vs_main": row.ahead,
                    "behind_vs_main": row.behind,
                    "head_reachable_from_main": str(row.reachable_main).lower(),
                    "reachable_from_retained_successor": str(bool(row.successor)).lower(),
                    "retained_successor_branch": row.successor,
                    "successor_or_acceptance_sha": row.successor_sha or ";".join(row.acceptance_shas[:8]),
                    "related_pr": ";".join(row.local_pr_refs) or "UNAVAILABLE_GITHUB_AUTH",
                    "related_pr_status": "UNAVAILABLE_GITHUB_AUTH",
                    "team_status_references": ";".join(sorted(set(row.status_refs))) or "NONE_FOUND",
                    "repository_document_references": ";".join(sorted(set(row.doc_refs))) or "NONE_FOUND",
                    "classification": row.classification,
                    "reason": row.reason,
                }
            )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row.classification] = counts.get(row.classification, 0) + 1
    archive_rows = [row for row in rows if row.classification == "ARCHIVE_TAG_THEN_DELETE_BRANCH"]
    delete_rows = [row for row in rows if row.classification == "DELETE_SAFE"]
    manual_rows = [row for row in rows if row.classification == "NEEDS_MANUAL_REVIEW"]

    plan_path = output / "BRANCH_CLEANUP_PLAN_V1.md"
    with plan_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Repository Hygiene V1 — Dry-Run Cleanup Plan\n\n")
        handle.write("## Scope and safety\n\n")
        unique_names = len({row.name for row in rows})
        handle.write(
            "This is an audit-only snapshot generated from the fully fetched/pruned local `origin` refs. "
            "It makes no branch deletion, tag creation, PR closure, history rewrite, or force-push. "
            f"Remote branch inventory count: **{len(rows)}**; unique branch names: **{unique_names}**; generated CSV rows: **{len(rows)}**; main HEAD: `{main_head}`.\n\n"
        )
        if any(row.name == "codex/repository-hygiene-v1" for row in rows):
            handle.write(
                "The audit branch is included in this snapshot. Because committing a regenerated report advances "
                "that branch, its self-row records the branch HEAD observed immediately before this report commit; "
                "the inventory count remains the authoritative no-missed-branch check.\n\n"
            )
        handle.write(
            "GitHub PR/Issue metadata could not be authenticated in this environment (`gh` returned HTTP 401; "
            "the public Issue #30 URL was not retrievable). The CSV therefore records `UNAVAILABLE_GITHUB_AUTH` "
            "rather than inferring PR numbers or states.\n\n"
        )
        handle.write("## Classification summary\n\n")
        handle.write("| Classification | Count |\n|---|---:|\n")
        for key in ("KEEP", "ARCHIVE_TAG_THEN_DELETE_BRANCH", "DELETE_SAFE", "ABANDONED_NO_DECISION", "NEEDS_MANUAL_REVIEW"):
            handle.write(f"| `{key}` | {counts.get(key, 0)} |\n")
        handle.write("\n")
        handle.write("## Proposed archive tags — not created\n\n")
        if archive_rows:
            for row in archive_rows:
                handle.write(f"- `{row.name}` → `archive/{branch_slug(row.name)}-{row.head[:12]}` (`{row.head}`)\n")
        else:
            handle.write("- None in this snapshot.\n")
        handle.write("\n## Proposed DELETE_SAFE candidates — not deleted\n\n")
        if delete_rows:
            for row in delete_rows:
                handle.write(f"- `{row.name}` at `{row.head}` — {row.reason}\n")
        else:
            handle.write("- None in this snapshot.\n")
        handle.write("\n## Proposed stale PR closures — not performed\n\n")
        handle.write(
            "No PR closure is proposed as an executable action because authenticated PR metadata is unavailable. "
            "After an authenticated lookup, review only the non-KEEP candidates above; preserve any PR carrying "
            "an unresolved scientific decision or active handoff.\n\n"
        )
        handle.write("## Manual-review queue\n\n")
        if manual_rows:
            for row in manual_rows:
                refs = "; ".join(sorted(set(row.doc_refs))) or "no tracked document reference"
                handle.write(f"- `{row.name}` at `{row.head}` — {row.reason} References: {refs}.\n")
        else:
            handle.write("- None in this snapshot.\n")
        handle.write("\n## Interpretation rules applied\n\n")
        handle.write(
            "- Active, automated, review, waiting, blocked, planned, and parked lanes remain `KEEP`.\n"
            "- A failed experiment is not deleted merely because it failed; a scientific branch is archive-tag eligible only when its exact HEAD/decision is retained or the status explicitly marks it DONE.\n"
            "- Fully merged temporary/engineering branches with no tracked decision reference are `DELETE_SAFE`.\n"
            "- Unreachable or ambiguous scientific lineage is `NEEDS_MANUAL_REVIEW`; `ABANDONED_NO_DECISION` is a classification, not permission to delete without review.\n"
            "- `main` is retained and is used as a successor when it contains a branch HEAD.\n"
        )


if __name__ == "__main__":
    branch_rows, main = inventory()
    write_reports(branch_rows, main)
    print(f"remote_branch_count={len(branch_rows)}")
    print(f"main_head={main}")
    for classification in ("KEEP", "ARCHIVE_TAG_THEN_DELETE_BRANCH", "DELETE_SAFE", "ABANDONED_NO_DECISION", "NEEDS_MANUAL_REVIEW"):
        print(f"{classification}={sum(row.classification == classification for row in branch_rows)}")
