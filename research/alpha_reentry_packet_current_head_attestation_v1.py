"""Current-head attestation for the outcome-blind future evaluation packet.

This companion does not rewrite the packet, contract, source manifest, or
registry. It binds the prior producer pin P and packet-attestation commit Q to
the current repository head R, checks that packet-bound Git files did not
change from Q through R, and rechecks current hashes of explicitly declared
source files. External source bytes are reported separately: a current hash
match is not retroactive proof that those bytes were attested at Q.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def git_exit_code(repo: Path, *args: str) -> int:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    ).returncode


def resolve(repo: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo / path


def repo_relative(repo: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return None


def declared_files(repo: Path, contract: dict[str, Any], contract_path: Path, packet_path: Path, verifier_path: Path) -> list[str]:
    paths: list[Path] = [contract_path, packet_path, verifier_path]
    for container_name in ("implementation_bindings",):
        for binding in contract.get(container_name, {}).values():
            if isinstance(binding, dict) and isinstance(binding.get("path"), str):
                paths.append(resolve(repo, binding["path"]))
    for evidence in contract.get("robustness_evidence", []):
        if isinstance(evidence, dict) and isinstance(evidence.get("path"), str):
            paths.append(resolve(repo, evidence["path"]))
    relative = {item for path in paths if (item := repo_relative(repo, path)) is not None}
    return sorted(relative)


def source_hashes(contract: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    records: dict[str, Any] = {}
    all_match = True
    for name, binding in contract.get("source_bindings", {}).items():
        path = Path(binding["path"])
        exists = path.is_file()
        actual = sha256_file(path) if exists else None
        match = bool(exists and actual == binding.get("sha256"))
        all_match = all_match and match
        records[name] = {
            "path": str(path),
            "exists": exists,
            "declared_sha256": binding.get("sha256"),
            "actual_sha256": actual,
            "matches": match,
        }
    return records, all_match


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--verifier", type=Path, required=True)
    parser.add_argument("--producer-commit", required=True)
    parser.add_argument("--packet-attestation-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")

    contract_path = args.contract.resolve()
    packet_path = args.packet.resolve()
    verifier_path = args.verifier.resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    head = git(repo, "rev-parse", "HEAD")
    producer = git(repo, "rev-parse", args.producer_commit)
    packet_attestation = git(repo, "rev-parse", args.packet_attestation_commit)
    dirty = git(repo, "status", "--porcelain")
    changed_since_q = [line for line in git(repo, "diff", "--name-only", f"{packet_attestation}..{head}").splitlines() if line]
    bound_files = declared_files(repo, contract, contract_path, packet_path, verifier_path)
    changed_bound_files = sorted(set(changed_since_q) & set(bound_files))
    sources, sources_match = source_hashes(contract)

    checks = {
        "worktree_clean": dirty == "",
        "producer_commit_resolves": bool(producer),
        "packet_attestation_commit_resolves": bool(packet_attestation),
        "producer_is_ancestor_of_current_head": git_exit_code(repo, "merge-base", "--is-ancestor", producer, head) == 0,
        "packet_attestation_is_ancestor_of_current_head": git_exit_code(repo, "merge-base", "--is-ancestor", packet_attestation, head) == 0,
        "packet_bound_git_files_unchanged_since_q": not changed_bound_files,
        "current_source_binding_hashes_match_contract": sources_match,
        "packet_file_exists": packet_path.is_file(),
        "contract_file_exists": contract_path.is_file(),
        "verifier_file_exists": verifier_path.is_file(),
    }

    packet_hashes = {
        "packet_sha256": sha256_file(packet_path) if packet_path.is_file() else None,
        "contract_sha256": sha256_file(contract_path) if contract_path.is_file() else None,
        "verifier_sha256": sha256_file(verifier_path) if verifier_path.is_file() else None,
    }
    hard_pass = all(checks.values())
    result = {
        "status": "PASS_PACKET_BYTE_FRESHNESS / FULL_SOURCE_FRESHNESS_UNKNOWN" if hard_pass else "FAIL",
        "attestation_type": "CURRENT_HEAD_REENTRY_PACKET_ATTESTATION_V1",
        "repo": str(repo),
        "producer_commit_P": producer,
        "packet_attestation_commit_Q": packet_attestation,
        "current_head_R": head,
        "checks": checks,
        "packet_bound_git_files": bound_files,
        "changed_packet_bound_git_files_since_Q": changed_bound_files,
        "packet_hashes": packet_hashes,
        "current_source_bindings": sources,
        "source_freshness_interpretation": {
            "current_source_hashes_match_contract": sources_match,
            "full_source_freshness": "UNKNOWN",
            "reason": "source bytes are external to the Q..R Git diff; current hash equality does not prove they were attested at Q",
        },
        "scope": {
            "outcome_accessed": False,
            "target_accessed": False,
            "provider_accessed": False,
            "network_used": False,
            "canonical_mutation": False,
            "packet_mutated": False,
            "contract_mutated": False,
            "registry_mutated": False,
        },
        "code_sha256": sha256_file(Path(__file__)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))
    if not hard_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
