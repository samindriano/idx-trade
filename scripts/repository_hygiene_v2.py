from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONFIRM_TOKEN = "DELETE_NONCANONICAL_BRANCHES_V2"
DEFAULT_CONFIG = Path("docs/repository_hygiene/BRANCH_RETENTION_V2.json")


def _run(args: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


def _repo_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("not inside a git repository")
    return Path(completed.stdout.strip()).resolve()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_config(root: Path, config_path: Path) -> dict[str, Any]:
    path = config_path if config_path.is_absolute() else root / config_path
    data = json.loads(path.read_text(encoding="utf-8"))
    keep = set(data["keep_branches"])
    archive = set(data["archive_tag_then_delete"])
    overlap = keep & archive
    if overlap:
        raise RuntimeError(f"config overlap between keep/archive: {sorted(overlap)}")
    if "main" not in keep:
        raise RuntimeError("main must be explicitly kept")
    if data.get("default_unlisted_action") != "TOMBSTONE_THEN_DELETE":
        raise RuntimeError("unexpected default_unlisted_action")
    return data


def _fetch(root: Path) -> None:
    _run(["git", "fetch", "origin", "--prune", "--tags"], cwd=root)


def _remote_heads(root: Path) -> dict[str, str]:
    completed = _run(["git", "ls-remote", "--heads", "origin"], cwd=root)
    heads: dict[str, str] = {}
    for raw in completed.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        sha, ref = raw.split("\t", 1)
        prefix = "refs/heads/"
        if not ref.startswith(prefix):
            continue
        heads[ref[len(prefix) :]] = sha
    if "main" not in heads:
        raise RuntimeError("origin/main missing from remote head inventory")
    return heads


def _classify(branch: str, config: dict[str, Any]) -> tuple[str, str]:
    keep = set(config["keep_branches"])
    archive = set(config["archive_tag_then_delete"])
    if branch in keep:
        return "KEEP", "explicit V2 retention allowlist"
    if branch in archive:
        return "ARCHIVE_TAG_THEN_DELETE", "historical exact-code anchor; archive tag required"
    return "TOMBSTONE_THEN_DELETE", "unlisted under aggressive V2 policy; durable value is docs/PR history"


def _tag_name(branch: str, sha: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", branch).strip("-")
    return f"archive/hygiene-v2/{slug}-{sha[:12]}"


def _plan_tag_name(plan_sha256: str) -> str:
    return f"archive/hygiene-v2/deletion-plan-{plan_sha256[:16]}"


def _build_plan(root: Path, config_path: Path, *, fetch: bool) -> dict[str, Any]:
    if fetch:
        _fetch(root)
    config = _load_config(root, config_path)
    heads = _remote_heads(root)

    missing_keep = sorted(set(config["keep_branches"]) - set(heads))
    missing_archive = sorted(set(config["archive_tag_then_delete"]) - set(heads))

    rows: list[dict[str, Any]] = []
    for branch, sha in sorted(heads.items()):
        classification, reason = _classify(branch, config)
        row: dict[str, Any] = {
            "branch": branch,
            "head_sha": sha,
            "classification": classification,
            "reason": reason,
        }
        if classification == "ARCHIVE_TAG_THEN_DELETE":
            row["archive_tag"] = _tag_name(branch, sha)
        rows.append(row)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1

    return {
        "schema_version": 2,
        "policy": config["policy"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "origin_main_sha": heads["main"],
        "remote_branch_count": len(heads),
        "counts": counts,
        "estimated_live_branch_count_after_apply": counts.get("KEEP", 0),
        "missing_configured_keep_branches": missing_keep,
        "missing_configured_archive_branches": missing_archive,
        "rows": rows,
        "apply_authorized": False,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _plan_command(args: argparse.Namespace) -> int:
    root = _repo_root()
    plan = _build_plan(root, Path(args.config), fetch=not args.no_fetch)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    if output.exists() and not args.overwrite:
        raise RuntimeError(f"plan output already exists: {output}")
    _write_json(output, plan)
    digest = _sha256_file(output)

    print(f"PLAN_PATH={output}")
    print(f"PLAN_SHA256={digest}")
    print(f"DELETION_PLAN_TAG={_plan_tag_name(digest)}")
    print(f"ORIGIN_MAIN_SHA={plan['origin_main_sha']}")
    print(f"REMOTE_BRANCH_COUNT={plan['remote_branch_count']}")
    for key in sorted(plan["counts"]):
        print(f"{key}={plan['counts'][key]}")
    print(f"ESTIMATED_LIVE_BRANCH_COUNT={plan['estimated_live_branch_count_after_apply']}")
    if plan["missing_configured_keep_branches"]:
        print("MISSING_KEEP=" + ",".join(plan["missing_configured_keep_branches"]))
    if plan["missing_configured_archive_branches"]:
        print("MISSING_ARCHIVE=" + ",".join(plan["missing_configured_archive_branches"]))
    print("DESTRUCTIVE_APPLY_RUN=FALSE")
    return 0


def _remote_tag_lines(root: Path, tag: str) -> list[tuple[str, str]]:
    completed = _run(
        [
            "git",
            "ls-remote",
            "--tags",
            "origin",
            f"refs/tags/{tag}",
            f"refs/tags/{tag}^{{}}",
        ],
        cwd=root,
    )
    rows: list[tuple[str, str]] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, ref = line.split("\t", 1)
        rows.append((sha, ref))
    return rows


def _verify_remote_lightweight_tag(root: Path, tag: str, expected_sha: str) -> bool:
    rows = _remote_tag_lines(root, tag)
    if not rows:
        return False
    direct = [(sha, ref) for sha, ref in rows if ref == f"refs/tags/{tag}"]
    peeled = [(sha, ref) for sha, ref in rows if ref == f"refs/tags/{tag}^{{}}"]
    if len(direct) != 1 or peeled:
        raise RuntimeError(f"archive tag is not the expected lightweight tag {tag}: {rows}")
    if direct[0][0] != expected_sha:
        raise RuntimeError(
            f"remote archive tag mismatch for {tag}: expected {expected_sha}, got {direct[0][0]}"
        )
    return True


def _verify_remote_annotated_tag_target(root: Path, tag: str, expected_target: str) -> bool:
    rows = _remote_tag_lines(root, tag)
    if not rows:
        return False
    direct = [(sha, ref) for sha, ref in rows if ref == f"refs/tags/{tag}"]
    peeled = [(sha, ref) for sha, ref in rows if ref == f"refs/tags/{tag}^{{}}"]
    if len(direct) != 1 or len(peeled) != 1:
        raise RuntimeError(f"expected annotated deletion-plan tag {tag}, got: {rows}")
    if peeled[0][0] != expected_target:
        raise RuntimeError(
            f"remote deletion-plan tag target mismatch for {tag}: expected {expected_target}, got {peeled[0][0]}"
        )
    return True


def _local_annotated_tag_message(root: Path, tag: str) -> str:
    completed = _run(["git", "cat-file", "-p", f"refs/tags/{tag}"], cwd=root)
    payload = completed.stdout
    if "\n\n" not in payload:
        raise RuntimeError(f"annotated tag payload malformed: {tag}")
    return payload.split("\n\n", 1)[1]


def _prepare_local_lightweight_tag(root: Path, tag: str, sha: str) -> bool:
    local = _run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        cwd=root,
        check=False,
    )
    if local.returncode == 0:
        local_sha = local.stdout.strip()
        if local_sha != sha:
            raise RuntimeError(f"local tag collision for {tag}: expected {sha}, got {local_sha}")
        return False
    # update-ref guarantees a lightweight tag even if the caller has tag.gpgSign configured.
    _run(["git", "update-ref", f"refs/tags/{tag}", sha], cwd=root)
    return True


def _prepare_local_plan_tag(
    root: Path,
    *,
    tag: str,
    target_sha: str,
    plan_path: Path,
) -> bool:
    expected_message = plan_path.read_text(encoding="utf-8")
    local = _run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        cwd=root,
        check=False,
    )
    if local.returncode == 0:
        peeled = _run(["git", "rev-parse", f"refs/tags/{tag}^{{}}"], cwd=root).stdout.strip()
        if peeled != target_sha:
            raise RuntimeError(
                f"local deletion-plan tag target collision for {tag}: expected {target_sha}, got {peeled}"
            )
        if _local_annotated_tag_message(root, tag) != expected_message:
            raise RuntimeError(f"local deletion-plan tag message collision for {tag}")
        return False

    # Verbatim cleanup makes the annotation itself a durable exact copy of plan JSON bytes.
    _run(
        [
            "git",
            "tag",
            "-a",
            "--cleanup=verbatim",
            tag,
            target_sha,
            "-F",
            str(plan_path),
        ],
        cwd=root,
    )
    if _local_annotated_tag_message(root, tag) != expected_message:
        raise RuntimeError(f"created deletion-plan tag does not preserve exact plan bytes: {tag}")
    return True


def _apply_command(args: argparse.Namespace) -> int:
    root = _repo_root()
    plan_path = Path(args.plan)
    if not plan_path.is_absolute():
        plan_path = root / plan_path
    actual_plan_sha = _sha256_file(plan_path)
    if actual_plan_sha != args.plan_sha256:
        raise RuntimeError(
            f"plan SHA mismatch: expected {args.plan_sha256}, got {actual_plan_sha}"
        )
    if args.confirm != CONFIRM_TOKEN:
        raise RuntimeError("destructive confirmation token rejected")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("policy") != "REPOSITORY_HYGIENE_V2_AGGRESSIVE":
        raise RuntimeError("wrong cleanup policy in plan")
    if plan.get("schema_version") != 2:
        raise RuntimeError("cleanup plan schema must be exactly 2")
    if plan.get("apply_authorized") is not False:
        raise RuntimeError("plan payload unexpectedly claims apply authorization")

    _fetch(root)
    current = _remote_heads(root)
    if current.get("main") != plan["origin_main_sha"]:
        raise RuntimeError(
            f"origin/main moved since plan: {plan['origin_main_sha']} -> {current.get('main')}"
        )

    candidate_rows = [
        row
        for row in plan["rows"]
        if row["classification"] in {"ARCHIVE_TAG_THEN_DELETE", "TOMBSTONE_THEN_DELETE"}
    ]
    keep_rows = [row for row in plan["rows"] if row["classification"] == "KEEP"]

    # Full exact-head preflight before any local or remote mutation.
    for row in candidate_rows:
        branch = row["branch"]
        expected = row["head_sha"]
        observed = current.get(branch)
        if observed != expected:
            raise RuntimeError(
                f"candidate branch moved/missing since plan: {branch}: expected {expected}, got {observed}"
            )
        if branch == "main":
            raise RuntimeError("refusing to delete main")
    for row in keep_rows:
        branch = row["branch"]
        expected = row["head_sha"]
        observed = current.get(branch)
        if observed != expected:
            raise RuntimeError(
                f"retained branch moved/missing since plan: {branch}: expected {expected}, got {observed}"
            )

    archive_rows = [row for row in candidate_rows if row["classification"] == "ARCHIVE_TAG_THEN_DELETE"]
    plan_tag = _plan_tag_name(actual_plan_sha)

    # A pre-existing remote deletion-plan tag is not accepted for a fresh apply. If an earlier
    # atomic push succeeded, branch preflight should already fail because candidates are gone.
    if _remote_tag_lines(root, plan_tag):
        raise RuntimeError(f"remote deletion-plan tag already exists before apply: {plan_tag}")

    tags_to_push: list[str] = []
    created_local_tags: list[str] = []
    try:
        for row in archive_rows:
            tag = row["archive_tag"]
            sha = row["head_sha"]
            if _verify_remote_lightweight_tag(root, tag, sha):
                continue
            if _prepare_local_lightweight_tag(root, tag, sha):
                created_local_tags.append(tag)
            tags_to_push.append(tag)

        if _prepare_local_plan_tag(
            root,
            tag=plan_tag,
            target_sha=plan["origin_main_sha"],
            plan_path=plan_path,
        ):
            created_local_tags.append(plan_tag)

        # Archive refs, exact deletion-plan tag and every deletion are one remote transaction.
        # If the server rejects atomic update semantics, the whole apply fails instead of batching.
        refspecs = [
            *[f"refs/tags/{tag}:refs/tags/{tag}" for tag in tags_to_push],
            f"refs/tags/{plan_tag}:refs/tags/{plan_tag}",
            *[f":refs/heads/{row['branch']}" for row in candidate_rows],
        ]
        if not refspecs:
            raise RuntimeError("refusing empty destructive apply")
        _run(["git", "push", "--atomic", "origin", *refspecs], cwd=root)

        for row in archive_rows:
            if not _verify_remote_lightweight_tag(root, row["archive_tag"], row["head_sha"]):
                raise RuntimeError(f"archive tag missing after atomic push: {row['archive_tag']}")
        if not _verify_remote_annotated_tag_target(root, plan_tag, plan["origin_main_sha"]):
            raise RuntimeError(f"deletion-plan tag missing after atomic push: {plan_tag}")

        after = _remote_heads(root)
        branches_to_delete = [row["branch"] for row in candidate_rows]
        survivors = sorted(set(after) & set(branches_to_delete))
        if survivors:
            raise RuntimeError(f"candidate branches still exist after atomic push: {survivors}")
        missing_keep = sorted(row["branch"] for row in keep_rows if row["branch"] not in after)
        if missing_keep:
            raise RuntimeError(f"retained branches disappeared: {missing_keep}")

        result = {
            "schema_version": 2,
            "policy": plan["policy"],
            "plan_sha256": actual_plan_sha,
            "deletion_plan_tag": plan_tag,
            "origin_main_sha": plan["origin_main_sha"],
            "deleted_branch_count": len(branches_to_delete),
            "archive_tag_count": len(archive_rows),
            "remaining_remote_branch_count": len(after),
            "remaining_remote_branches": sorted(after),
            "deleted_branches": branches_to_delete,
            "archive_tags": [
                {
                    "branch": row["branch"],
                    "head_sha": row["head_sha"],
                    "tag": row["archive_tag"],
                }
                for row in archive_rows
            ],
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "remote_ref_update_mode": "ATOMIC_SINGLE_PUSH",
        }
        result_path = Path(args.result_output)
        if not result_path.is_absolute():
            result_path = root / result_path
        if result_path.exists() and not args.overwrite_result:
            raise RuntimeError(f"result output already exists: {result_path}")
        _write_json(result_path, result)
        print(f"RESULT_PATH={result_path}")
        print(f"RESULT_SHA256={_sha256_file(result_path)}")
        print(f"DELETION_PLAN_TAG={plan_tag}")
        print(f"DELETED_BRANCH_COUNT={len(branches_to_delete)}")
        print(f"ARCHIVE_TAG_COUNT={len(archive_rows)}")
        print(f"REMAINING_REMOTE_BRANCH_COUNT={len(after)}")
        print("REMOTE_REF_UPDATE_MODE=ATOMIC_SINGLE_PUSH")
        print("DESTRUCTIVE_APPLY_RUN=TRUE")
        return 0
    except Exception:
        # Local tags are disposable setup state. Never delete or rewrite a remote tag here:
        # a successful --atomic push is all-or-nothing, and post-push verification failures
        # must be returned for independent inspection rather than auto-remediation.
        for tag in reversed(created_local_tags):
            _run(["git", "tag", "-d", tag], cwd=root, check=False)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fail-closed Repository Hygiene V2 branch planner/applier")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="Generate exact remote branch disposition plan; no destructive mutation")
    plan.add_argument("--config", default=str(DEFAULT_CONFIG))
    plan.add_argument("--output", required=True)
    plan.add_argument("--no-fetch", action="store_true")
    plan.add_argument("--overwrite", action="store_true")
    plan.set_defaults(func=_plan_command)

    apply = sub.add_parser("apply", help="Apply an independently authorized exact plan")
    apply.add_argument("--plan", required=True)
    apply.add_argument("--plan-sha256", required=True)
    apply.add_argument("--confirm", required=True)
    apply.add_argument("--result-output", required=True)
    apply.add_argument("--overwrite-result", action="store_true")
    apply.set_defaults(func=_apply_command)
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"REPOSITORY_HYGIENE_V2_FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
