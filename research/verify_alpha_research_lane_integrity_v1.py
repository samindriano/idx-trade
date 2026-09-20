"""Fail-closed process-scope attestation for the isolated alpha research lane.

This is a path/branch/worktree/staging-scope control. It does not prove that a
runtime never accessed protected data; that limitation is explicit in output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


EXPECTED_BRANCH = "codex/alpha-available-data-20260919"
EXPECTED_WORKTREE = Path(r"C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919")
EXPECTED_STAGING = Path(
    r"D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded"
)
# Durable outcome-blind knowledge is an explicitly allowed research surface.
# Protected/canonical/production paths remain outside this allowlist.
ALLOWED_DELTA_PREFIXES = ("docs/checkpoints/", "research/", "research_knowledge/", "tests/")
FORBIDDEN_STAGING_PATTERNS = (
    r"outcome[_-]?vault",
    r"protected[_-]?(?:outcome|target|forward)",
    r"forward[_-]?(?:return|label|target|outcome)",
    r"(?:^|[\\/])counter(?:[._-]|$)",
)


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    staging = args.staging_root.resolve()
    output = args.output.resolve()
    if output.parent != staging:
        raise ValueError("lane attestation output must be directly inside the isolated staging root")
    if staging != EXPECTED_STAGING:
        raise ValueError("unexpected isolated staging root")
    output.parent.mkdir(parents=True, exist_ok=True)

    branch = git(repo, "branch", "--show-current")
    head = git(repo, "rev-parse", "HEAD")
    top_level = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    dirty = git(repo, "status", "--porcelain")
    baseline_probe = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{args.baseline}^{{commit}}"],
        capture_output=True,
    )
    baseline_exists = baseline_probe.returncode == 0
    ancestor = (
        subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", args.baseline, head],
            capture_output=True,
        ).returncode
        == 0
        if baseline_exists
        else False
    )
    delta = (
        git(repo, "diff", "--name-only", f"{args.baseline}..{head}").splitlines()
        if baseline_exists
        else []
    )
    normalized_delta = [path.replace("\\", "/") for path in delta if path]
    delta_allowed = all(path.startswith(ALLOWED_DELTA_PREFIXES) for path in normalized_delta)

    staging_files = sorted(
        path.relative_to(staging).as_posix()
        for path in staging.rglob("*")
        if path.is_file()
    )
    forbidden_staging = [
        path
        for path in staging_files
        if any(re.search(pattern, path.lower()) for pattern in FORBIDDEN_STAGING_PATTERNS)
    ]

    checks = {
        "expected_branch": branch == EXPECTED_BRANCH,
        "expected_worktree": top_level == EXPECTED_WORKTREE,
        "baseline_commit_exists": baseline_exists,
        "baseline_is_ancestor": ancestor,
        "delta_is_nonempty": bool(normalized_delta),
        "delta_scope_research_only": delta_allowed,
        "worktree_clean": dirty == "",
        "expected_staging_root": staging == EXPECTED_STAGING,
        "staging_files_present": bool(staging_files),
        "staging_has_no_protected_name": not forbidden_staging,
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "attestation_type": "isolated_alpha_research_process_scope_only",
        "runtime_access_absence_proven": False,
        "checks": checks,
        "repo": {
            "path": str(repo),
            "branch": branch,
            "head": head,
            "baseline": args.baseline,
            "delta_paths": normalized_delta,
            "dirty": dirty,
        },
        "staging": {
            "root": str(staging),
            "file_count": len(staging_files),
            "forbidden_name_paths": forbidden_staging,
            "file_name_digest": sha256_bytes("\n".join(staging_files).encode("utf-8")),
        },
        "scope": {
            "outcome_accessed": False,
            "provider_accessed": False,
            "target_accessed": False,
            "cloud_accessed": False,
            "canonical_mutation": False,
        },
        "limitations": [
            "This artifact attests path/branch/worktree scope only.",
            "It is not independent proof that a runtime never accessed protected data.",
            "All protected target and outcome boundaries remain in force.",
        ],
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
