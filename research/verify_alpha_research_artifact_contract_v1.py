"""Fail-closed hash contract verifier for isolated alpha research artifacts.

The verifier reads one JSON artifact and only the explicitly supplied code,
input, and optional manifest files. It does not discover providers, targets,
outcomes, cloud state, or repository data implicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_assignment(value: str) -> tuple[str, Path]:
    name, separator, path = value.partition("=")
    if not separator or not name or not path:
        raise ValueError(f"expected NAME=PATH, got {value!r}")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise ValueError(f"invalid input name {name!r}")
    return name, Path(path)


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def declared_hashes(artifact: dict[str, Any]) -> dict[str, set[str]]:
    """Collect supported declarations without silently resolving conflicts."""

    result: dict[str, set[str]] = {}

    def add(name: str, value: Any) -> None:
        if not isinstance(value, str):
            return
        key = normalized(name.removesuffix("_sha256"))
        result.setdefault(key, set()).add(value.lower())

    for container_name in ("source_hashes", "inputs", "files"):
        container = artifact.get(container_name)
        if isinstance(container, dict):
            for name, value in container.items():
                add(str(name), value)

    for name, value in artifact.items():
        if str(name).endswith("_sha256"):
            add(str(name), value)
    return result


def resolve_declared_hash(
    declarations: dict[str, set[str]], expected_name: str, input_path: Path
) -> tuple[str | None, list[str]]:
    candidates = {
        normalized(expected_name),
        normalized(input_path.name),
        normalized(input_path.stem),
    }
    matches: set[str] = set()
    matched_keys: list[str] = []
    for key, values in declarations.items():
        if key in candidates:
            matches.update(values)
            matched_keys.append(key)
    if len(matches) == 1:
        return next(iter(matches)), sorted(matched_keys)
    if not matches:
        return None, []
    return "__CONFLICT__", sorted(matched_keys)


def verify(
    artifact_path: Path,
    code_path: Path,
    input_assignments: list[str],
    manifest_path: Path | None,
    require_manifest: bool,
) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    if not isinstance(artifact, dict):
        raise ValueError("artifact root must be a JSON object")

    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}
    artifact_hash = sha256_file(artifact_path)
    code_hash = sha256_file(code_path)

    code_candidates: list[tuple[str, str]] = []
    for field in ("code_sha256", "feature_code_sha256"):
        value = artifact.get(field)
        if isinstance(value, str):
            code_candidates.append((field, value.lower()))
    code_values = {value for _, value in code_candidates}
    checks["artifact_code_hash_declared"] = bool(code_values)
    checks["artifact_code_hash_not_conflicting"] = len(code_values) <= 1
    checks["artifact_code_hash_matches"] = code_hash in code_values if code_values else False
    details["code"] = {
        "path": str(code_path),
        "actual_sha256": code_hash,
        "declared": dict(code_candidates),
    }

    declarations = declared_hashes(artifact)
    input_details: dict[str, Any] = {}
    for assignment in input_assignments:
        name, input_path = parse_assignment(assignment)
        actual = sha256_file(input_path)
        declared, matched_keys = resolve_declared_hash(declarations, name, input_path)
        key = f"input:{name}"
        checks[f"{key}:declared"] = declared not in (None, "__CONFLICT__")
        checks[f"{key}:not_conflicting"] = declared != "__CONFLICT__"
        checks[f"{key}:matches"] = declared == actual
        input_details[name] = {
            "path": str(input_path),
            "actual_sha256": actual,
            "declared_sha256": None if declared in (None, "__CONFLICT__") else declared,
            "matched_declaration_keys": matched_keys,
        }
    details["inputs"] = input_details

    declared_manifest = artifact.get("manifest_sha256")
    if not isinstance(declared_manifest, str):
        manifest_container = artifact.get("source_hashes")
        if isinstance(manifest_container, dict):
            declared_manifest = manifest_container.get("manifest")
    manifest_declared = isinstance(declared_manifest, str)
    if require_manifest:
        checks["manifest_declaration_present"] = manifest_declared
        checks["manifest_path_supplied"] = manifest_path is not None
    if manifest_declared:
        checks["manifest_path_supplied"] = manifest_path is not None
        if manifest_path is not None:
            manifest_hash = sha256_file(manifest_path)
            checks["manifest_hash_matches"] = manifest_hash == declared_manifest.lower()
            details["manifest"] = {
                "path": str(manifest_path),
                "actual_sha256": manifest_hash,
                "declared_sha256": declared_manifest.lower(),
            }
    elif manifest_path is not None:
        checks["manifest_declaration_present"] = False
        details["manifest"] = {"path": str(manifest_path), "declared_sha256": None}
    else:
        checks["manifest_contract_not_applicable"] = True

    checks["artifact_is_json_object"] = True
    passed = all(checks.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "contract": "ISOLATED_ALPHA_RESEARCH_ARTIFACT_HASH_BINDING_V1",
        "artifact": str(artifact_path),
        "artifact_sha256": artifact_hash,
        "checks": checks,
        "details": details,
        "scope": {
            "reads_only_explicit_paths": True,
            "provider_accessed": False,
            "target_accessed": False,
            "outcome_accessed": False,
            "cloud_accessed": False,
        },
        "verifier_code_sha256": sha256_file(Path(__file__)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="explicit input path whose declared artifact hash must match",
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--require-manifest",
        action="store_true",
        help="fail unless the artifact declares and binds an explicit manifest",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = verify(args.artifact, args.code, args.input, args.manifest, args.require_manifest)
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
