"""Fail-closed validation for the canonical IDX source registry.

The registry is an evidence index, not an approval mechanism.  In particular,
an official provider, a matching transport response, or a non-empty artifact
does not upgrade unknown PIT timing or revision semantics.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence


REGISTRY_SCHEMA_VERSION = "1.0.0"
_ID_RE = re.compile(r"^[A-Z0-9_]+$")
_HASH_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ROOT_KEYS = {
    "schema_version",
    "registry_id",
    "as_of",
    "source_count",
    "checkpoint_count",
    "sources",
    "controlling_checkpoints",
    "maintenance",
}
_SOURCE_KEYS = {
    "source_id",
    "family",
    "name",
    "provider",
    "authority",
    "authority_role",
    "status",
    "granularity",
    "coverage",
    "timing",
    "pit_status",
    "revision_risk",
    "raw_provenance",
    "permitted_uses",
    "prohibited_uses",
    "controlling_checkpoint_ids",
    "unresolved_findings",
    "supersession",
    "freshness",
    "notes",
}
_CHECKPOINT_KEYS = {
    "checkpoint_id",
    "status",
    "repository",
    "git_ref",
    "commit",
    "path",
    "blob_sha1",
    "accepted_claims",
    "notes",
}
_STATUSES = {
    "CERTIFIED_BOUNDED",
    "ACCEPTED_CONDITIONAL",
    "DISCOVERY_ONLY",
    "AUDIT_ONLY",
    "SHADOW",
    "BLOCKED",
    "REJECTED",
    "PARKED",
    "AUTOMATED_FORWARD",
}
_PIT_STATUSES = {
    "PIT_CERTIFIED",
    "PIT_PARTIAL",
    "PIT_UNRESOLVED",
    "PIT_BLOCKED",
    "NOT_PIT",
    "UNKNOWN",
}
_AUTHORITY_ROLES = {
    "PRIMARY_AUTHORITY",
    "SECONDARY_TRANSPORT",
    "CROSS_CHECK",
    "DERIVED_RESEARCH",
    "DISCOVERY_LAYER",
    "MIXED",
}
_AUTHORITY_NAMES = {
    "OFFICIAL_IDX",
    "OFFICIAL_KSEI",
    "OFFICIAL_ISSUER",
    "OFFICIAL_CSD",
    "OFFICIAL_REGULATOR",
    "MIXED_OFFICIAL",
    "SECONDARY_PROVIDER",
    "SECONDARY_TRANSPORT",
    "DERIVED",
    "UNKNOWN",
}
_REVISION_LEVELS = {"LOW", "MEDIUM", "HIGH", "UNKNOWN", "NOT_APPLICABLE"}
_VERSIONING = {"IMMUTABLE", "VINTAGED", "UNVINTAGED", "NOT_APPLICABLE", "UNKNOWN"}
_OVERWRITE = {
    "APPEND_ONLY",
    "PRESERVE_VERSIONS",
    "CREATE_ONCE",
    "NO_OVERWRITE",
    "NOT_APPLICABLE",
    "UNKNOWN",
}
_CHECKPOINT_STATUSES = {"CONTROLLING", "SUPERSEDED", "RETIRED"}
_REQUIRED_TIMING_KEYS = {"effective_date", "publication", "observation"}
_TIMING_STATUSES = {
    "EXPLICIT",
    "SESSION_DATE",
    "CAPTURE_DATE",
    "CAPTURE_TIME_RECORDED",
    "DERIVED_NOT_EFFECTIVE",
    "UNKNOWN",
    "NOT_APPLICABLE",
    "NOT_ESTABLISHED",
}


@dataclass(frozen=True)
class ValidationIssue:
    """One deterministic validation finding."""

    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} at {self.path}: {self.message}"


class RegistryValidationError(ValueError):
    """Raised by the assert/load helpers when registry validation fails."""

    def __init__(self, issues: Sequence[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__("\n".join(map(str, self.issues)))


def _issue(issues: list[ValidationIssue], code: str, path: str, message: str) -> None:
    issues.append(ValidationIssue(code, path, message))


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _check_keys(
    issues: list[ValidationIssue], value: Mapping[str, Any], allowed: set[str], path: str
) -> None:
    for key in sorted(set(value) - allowed):
        _issue(issues, "UNKNOWN_FIELD", f"{path}.{key}", "field is not in the registry contract")


def _require_string(
    issues: list[ValidationIssue], value: Mapping[str, Any], key: str, path: str
) -> str | None:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        _issue(issues, "MISSING_OR_INVALID", f"{path}.{key}", "expected a non-empty string")
        return None
    return item


def _check_date(issues: list[ValidationIssue], value: Any, path: str, *, allow_null: bool = False) -> None:
    if value is None and allow_null:
        return
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        _issue(issues, "INVALID_DATE", path, "expected YYYY-MM-DD")
        return
    try:
        date.fromisoformat(value)
    except ValueError:
        _issue(issues, "INVALID_DATE", path, "date is not calendar-valid")


def _check_id(issues: list[ValidationIssue], value: Any, path: str) -> None:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        _issue(issues, "INVALID_IDENTIFIER", path, "expected uppercase ASCII identifier")


def _check_relative_path(issues: list[ValidationIssue], value: Any, path: str) -> None:
    if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
        _issue(issues, "INVALID_REPOSITORY_PATH", path, "path must be repository-relative and traversal-free")


def _check_enum(issues: list[ValidationIssue], value: Any, path: str, allowed: set[str]) -> None:
    if value not in allowed:
        _issue(issues, "UNSUPPORTED_VALUE", path, f"expected one of {sorted(allowed)}")


def _validate_timing(issues: list[ValidationIssue], timing: Any, path: str) -> None:
    if not _is_mapping(timing):
        _issue(issues, "MISSING_OR_INVALID", path, "expected timing mapping")
        return
    if set(timing) != _REQUIRED_TIMING_KEYS:
        _issue(issues, "MISSING_OR_INVALID", path, "timing must contain effective_date, publication, observation only")
    for key in sorted(_REQUIRED_TIMING_KEYS):
        item = timing.get(key)
        item_path = f"{path}.{key}"
        if not _is_mapping(item):
            _issue(issues, "MISSING_OR_INVALID", item_path, "expected timing-status mapping")
            continue
        allowed = {"status", "field", "timezone", "semantics"}
        _check_keys(issues, item, allowed, item_path)
        status = item.get("status")
        _check_enum(issues, status, f"{item_path}.status", _TIMING_STATUSES)
        field = item.get("field")
        if field is not None and not isinstance(field, str):
            _issue(issues, "MISSING_OR_INVALID", f"{item_path}.field", "field must be string or null")
        if status in {"UNKNOWN", "NOT_ESTABLISHED", "NOT_APPLICABLE"} and field is not None:
            _issue(issues, "CONTRADICTORY_TIMING", item_path, "unresolved timing status cannot name a source field")
        if status not in {"UNKNOWN", "NOT_ESTABLISHED", "NOT_APPLICABLE"} and field is None:
            _issue(issues, "MISSING_OR_INVALID", item_path, "resolved timing status must name its field")
        for text_key in ("timezone", "semantics"):
            if not isinstance(item.get(text_key), str) or not item[text_key].strip():
                _issue(issues, "MISSING_OR_INVALID", f"{item_path}.{text_key}", "expected non-empty string")


def _validate_coverage(issues: list[ValidationIssue], coverage: Any, path: str) -> None:
    if not _is_mapping(coverage):
        _issue(issues, "MISSING_OR_INVALID", path, "expected coverage mapping")
        return
    allowed = {"kind", "start", "end", "unit", "scope", "completeness", "notes"}
    _check_keys(issues, coverage, allowed, path)
    for key in ("kind", "unit", "scope", "completeness", "notes"):
        _require_string(issues, coverage, key, path)
    for key in ("start", "end"):
        _check_date(issues, coverage.get(key), f"{path}.{key}", allow_null=True)
    start, end = coverage.get("start"), coverage.get("end")
    if isinstance(start, str) and isinstance(end, str) and start > end:
        _issue(issues, "CONTRADICTORY_COVERAGE", path, "coverage start is after coverage end")


def _validate_raw_provenance(issues: list[ValidationIssue], raw: Any, path: str) -> None:
    if not _is_mapping(raw):
        _issue(issues, "MISSING_OR_INVALID", path, "expected raw provenance mapping")
        return
    allowed = {"retrieval_method", "raw_bytes_status", "canonical_locators", "transport_locators", "artifact_hashes", "preservation"}
    _check_keys(issues, raw, allowed, path)
    for key in ("retrieval_method", "raw_bytes_status", "preservation"):
        _require_string(issues, raw, key, path)
    for key in ("canonical_locators", "transport_locators"):
        item = raw.get(key)
        if not isinstance(item, list) or not all(isinstance(v, str) and v for v in item):
            _issue(issues, "MISSING_OR_INVALID", f"{path}.{key}", "expected a list of non-empty strings")
    hashes = raw.get("artifact_hashes")
    if not isinstance(hashes, list):
        _issue(issues, "MISSING_OR_INVALID", f"{path}.artifact_hashes", "expected a list")
        return
    for index, item in enumerate(hashes):
        item_path = f"{path}.artifact_hashes[{index}]"
        if not _is_mapping(item):
            _issue(issues, "MISSING_OR_INVALID", item_path, "expected artifact-hash mapping")
            continue
        _check_keys(issues, item, {"label", "algorithm", "hash", "location", "immutable"}, item_path)
        for key in ("label", "algorithm", "hash", "location"):
            _require_string(issues, item, key, item_path)
        if item.get("algorithm") not in {"sha1", "sha256"}:
            _issue(issues, "UNSUPPORTED_VALUE", f"{item_path}.algorithm", "only sha1 and sha256 are allowed")
        if not isinstance(item.get("hash"), str) or not _HASH_RE.fullmatch(item["hash"]):
            _issue(issues, "INVALID_HASH", f"{item_path}.hash", "expected hexadecimal SHA-1/SHA-256")
        if not isinstance(item.get("immutable"), bool):
            _issue(issues, "MISSING_OR_INVALID", f"{item_path}.immutable", "expected boolean")


def _validate_source(
    issues: list[ValidationIssue],
    source: Any,
    index: int,
    checkpoint_map: Mapping[str, Mapping[str, Any]],
    as_of: str,
) -> None:
    path = f"sources[{index}]"
    if not _is_mapping(source):
        _issue(issues, "MISSING_OR_INVALID", path, "expected source mapping")
        return
    _check_keys(issues, source, _SOURCE_KEYS, path)
    required = (
        "source_id", "family", "name", "provider", "authority", "authority_role", "status",
        "granularity", "coverage", "timing", "pit_status", "revision_risk", "raw_provenance",
        "permitted_uses", "prohibited_uses", "controlling_checkpoint_ids", "unresolved_findings",
        "supersession", "freshness", "notes",
    )
    for key in required:
        if key not in source:
            _issue(issues, "MISSING_FIELD", f"{path}.{key}", "required registry field is absent")
    source_id = source.get("source_id")
    _check_id(issues, source_id, f"{path}.source_id")
    for key in ("family", "name", "provider", "granularity", "notes"):
        _require_string(issues, source, key, path)
    _check_enum(issues, source.get("authority"), f"{path}.authority", _AUTHORITY_NAMES)
    _check_enum(issues, source.get("authority_role"), f"{path}.authority_role", _AUTHORITY_ROLES)
    _check_enum(issues, source.get("status"), f"{path}.status", _STATUSES)
    _check_enum(issues, source.get("pit_status"), f"{path}.pit_status", _PIT_STATUSES)
    for key in ("coverage", "timing", "raw_provenance"):
        if key in source:
            if key == "coverage":
                _validate_coverage(issues, source[key], f"{path}.{key}")
            elif key == "timing":
                _validate_timing(issues, source[key], f"{path}.{key}")
            else:
                _validate_raw_provenance(issues, source[key], f"{path}.{key}")

    revision = source.get("revision_risk")
    revision_path = f"{path}.revision_risk"
    if not _is_mapping(revision):
        _issue(issues, "MISSING_OR_INVALID", revision_path, "expected revision-risk mapping")
    else:
        _check_keys(issues, revision, {"level", "versioning", "overwrite_policy", "notes"}, revision_path)
        _check_enum(issues, revision.get("level"), f"{revision_path}.level", _REVISION_LEVELS)
        _check_enum(issues, revision.get("versioning"), f"{revision_path}.versioning", _VERSIONING)
        _check_enum(issues, revision.get("overwrite_policy"), f"{revision_path}.overwrite_policy", _OVERWRITE)
        _require_string(issues, revision, "notes", revision_path)

    for key in ("permitted_uses", "prohibited_uses", "unresolved_findings", "controlling_checkpoint_ids"):
        item = source.get(key)
        item_path = f"{path}.{key}"
        if not isinstance(item, list) or not all(isinstance(v, str) and v.strip() for v in item):
            _issue(issues, "MISSING_OR_INVALID", item_path, "expected a list of non-empty strings")
    permitted = set(source.get("permitted_uses", [])) if isinstance(source.get("permitted_uses"), list) else set()
    prohibited = set(source.get("prohibited_uses", [])) if isinstance(source.get("prohibited_uses"), list) else set()
    overlap = permitted & prohibited
    if overlap:
        _issue(issues, "CONTRADICTORY_USE_POLICY", f"{path}.permitted_uses", f"uses appear in both lists: {sorted(overlap)}")
    if source.get("pit_status") != "PIT_CERTIFIED" and permitted & {"PIT_MODEL_FEATURE", "PIT_LABEL_BUILDING", "PIT_REPLAY", "HISTORICAL_PIT_UNIVERSE"}:
        _issue(issues, "PIT_OVERCLAIM", path, "non-certified PIT source permits a PIT-sensitive use")
    if source.get("status") in {"BLOCKED", "REJECTED", "SHADOW"} and permitted & {"MODEL_FEATURE", "PIT_MODEL_FEATURE", "PERFORMANCE_METRIC", "PROMOTION_DECISION", "CANONICAL_EOD"}:
        _issue(issues, "STATUS_USE_CONTRADICTION", path, "blocked/rejected/shadow source permits a prohibited operational use")
    if source.get("status") == "SHADOW" and "CANONICAL_EOD" not in prohibited:
        _issue(issues, "MISSING_FAIL_CLOSED_PROHIBITION", f"{path}.prohibited_uses", "SHADOW source must prohibit CANONICAL_EOD")
    if source.get("pit_status") != "PIT_CERTIFIED" and "PIT_REPLAY" not in prohibited:
        _issue(issues, "MISSING_FAIL_CLOSED_PROHIBITION", f"{path}.prohibited_uses", "non-certified PIT source must prohibit PIT_REPLAY")
    if source.get("status") == "CERTIFIED_BOUNDED" and source.get("unresolved_findings"):
        _issue(issues, "OVERSTATED_STATUS", path, "CERTIFIED_BOUNDED source cannot retain unresolved findings")

    checkpoint_ids = source.get("controlling_checkpoint_ids", [])
    if isinstance(checkpoint_ids, list):
        for checkpoint_id in checkpoint_ids:
            if checkpoint_id not in checkpoint_map:
                _issue(issues, "UNKNOWN_CHECKPOINT", f"{path}.controlling_checkpoint_ids", f"unknown checkpoint {checkpoint_id}")
            elif checkpoint_map[checkpoint_id].get("status") != "CONTROLLING":
                _issue(issues, "NONCONTROLLING_CHECKPOINT", f"{path}.controlling_checkpoint_ids", f"checkpoint {checkpoint_id} is not CONTROLLING")

    freshness = source.get("freshness")
    freshness_path = f"{path}.freshness"
    if not _is_mapping(freshness):
        _issue(issues, "MISSING_OR_INVALID", freshness_path, "expected freshness mapping")
    else:
        _check_keys(issues, freshness, {"policy", "last_reviewed", "stale_after_days"}, freshness_path)
        _require_string(issues, freshness, "policy", freshness_path)
        _check_date(issues, freshness.get("last_reviewed"), f"{freshness_path}.last_reviewed")
        stale_after = freshness.get("stale_after_days")
        if stale_after is not None and (not isinstance(stale_after, int) or isinstance(stale_after, bool) or stale_after < 0):
            _issue(issues, "MISSING_OR_INVALID", f"{freshness_path}.stale_after_days", "expected non-negative integer or null")
        elif stale_after is not None and isinstance(freshness.get("last_reviewed"), str):
            age = (date.fromisoformat(as_of) - date.fromisoformat(freshness["last_reviewed"])).days
            if age < 0:
                _issue(issues, "FUTURE_REVIEW_DATE", freshness_path, "last_reviewed is after registry as_of")
            elif age > stale_after:
                _issue(issues, "STALE_ENTRY", freshness_path, f"entry is {age} days old; limit is {stale_after}")

    supersession = source.get("supersession")
    supersession_path = f"{path}.supersession"
    if not _is_mapping(supersession):
        _issue(issues, "MISSING_OR_INVALID", supersession_path, "expected supersession mapping")
    else:
        _check_keys(issues, supersession, {"supersedes", "superseded_by", "authority_over", "transport_for"}, supersession_path)
        for key in ("supersedes", "superseded_by", "authority_over", "transport_for"):
            item = supersession.get(key)
            if not isinstance(item, list) or not all(isinstance(v, str) and v.strip() for v in item):
                _issue(issues, "MISSING_OR_INVALID", f"{supersession_path}.{key}", "expected a list of strings")
            elif source_id in item:
                _issue(issues, "CONTRADICTORY_SUPERSESSION", supersession_path, "source cannot reference itself")


def _validate_checkpoints(issues: list[ValidationIssue], checkpoints: Any) -> dict[str, Mapping[str, Any]]:
    checkpoint_map: dict[str, Mapping[str, Any]] = {}
    if not isinstance(checkpoints, list):
        _issue(issues, "MISSING_OR_INVALID", "controlling_checkpoints", "expected a list")
        return checkpoint_map
    for index, checkpoint in enumerate(checkpoints):
        path = f"controlling_checkpoints[{index}]"
        if not _is_mapping(checkpoint):
            _issue(issues, "MISSING_OR_INVALID", path, "expected checkpoint mapping")
            continue
        _check_keys(issues, checkpoint, _CHECKPOINT_KEYS, path)
        required = ("checkpoint_id", "status", "repository", "git_ref", "commit", "path", "blob_sha1", "accepted_claims", "notes")
        for key in required:
            if key not in checkpoint:
                _issue(issues, "MISSING_FIELD", f"{path}.{key}", "required checkpoint field is absent")
        checkpoint_id = checkpoint.get("checkpoint_id")
        _check_id(issues, checkpoint_id, f"{path}.checkpoint_id")
        if isinstance(checkpoint_id, str):
            if checkpoint_id in checkpoint_map:
                _issue(issues, "DUPLICATE_IDENTIFIER", f"{path}.checkpoint_id", f"duplicate checkpoint {checkpoint_id}")
            else:
                checkpoint_map[checkpoint_id] = checkpoint
        _check_enum(issues, checkpoint.get("status"), f"{path}.status", _CHECKPOINT_STATUSES)
        for key in ("repository", "git_ref", "commit", "blob_sha1", "notes"):
            _require_string(issues, checkpoint, key, path)
        _check_relative_path(issues, checkpoint.get("path"), f"{path}.path")
        if not isinstance(checkpoint.get("commit"), str) or not re.fullmatch(r"[0-9a-fA-F]{40}", checkpoint.get("commit", "")):
            _issue(issues, "INVALID_COMMIT", f"{path}.commit", "expected a full 40-character commit SHA")
        if not isinstance(checkpoint.get("blob_sha1"), str) or not re.fullmatch(r"[0-9a-fA-F]{40}", checkpoint.get("blob_sha1", "")):
            _issue(issues, "INVALID_HASH", f"{path}.blob_sha1", "expected a full SHA-1 blob id")
        claims = checkpoint.get("accepted_claims")
        if not isinstance(claims, list) or not all(isinstance(v, str) and v.strip() for v in claims):
            _issue(issues, "MISSING_OR_INVALID", f"{path}.accepted_claims", "expected a non-empty list of strings")
    return checkpoint_map


def _verify_checkpoint_blobs(issues: list[ValidationIssue], checkpoints: Sequence[Any], repo_root: Path) -> None:
    for index, checkpoint in enumerate(checkpoints):
        if not _is_mapping(checkpoint) or checkpoint.get("status") != "CONTROLLING":
            continue
        commit, path, expected = checkpoint.get("commit"), checkpoint.get("path"), checkpoint.get("blob_sha1")
        if not all(isinstance(v, str) for v in (commit, path, expected)):
            continue
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", f"{commit}:{path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        item_path = f"controlling_checkpoints[{index}]"
        if result.returncode != 0:
            _issue(issues, "CHECKPOINT_NOT_IN_REPOSITORY", item_path, result.stderr.strip() or "git object was not found")
        elif result.stdout.strip().lower() != expected.lower():
            _issue(issues, "CHECKPOINT_HASH_MISMATCH", item_path, f"expected {expected}, got {result.stdout.strip()}")


def validate_source_registry(
    registry: Any,
    *,
    repo_root: str | Path | None = None,
    verify_git: bool = False,
    as_of: str | None = None,
) -> tuple[ValidationIssue, ...]:
    """Return sorted issues; an empty tuple means the registry is valid."""

    issues: list[ValidationIssue] = []
    if not _is_mapping(registry):
        return (ValidationIssue("MISSING_OR_INVALID", "$", "registry must be a mapping"),)
    _check_keys(issues, registry, _ROOT_KEYS, "$")
    if registry.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        _issue(issues, "UNSUPPORTED_SCHEMA", "$.schema_version", f"expected {REGISTRY_SCHEMA_VERSION}")
    _check_id(issues, registry.get("registry_id"), "$.registry_id")
    registry_as_of = as_of or registry.get("as_of")
    _check_date(issues, registry_as_of, "$.as_of")
    if not isinstance(registry_as_of, str) or not _DATE_RE.fullmatch(registry_as_of):
        registry_as_of = "1970-01-01"
    for key in ("source_count", "checkpoint_count"):
        if not isinstance(registry.get(key), int) or isinstance(registry.get(key), bool) or registry[key] < 0:
            _issue(issues, "MISSING_OR_INVALID", f"$.{key}", "expected non-negative integer")

    checkpoint_map = _validate_checkpoints(issues, registry.get("controlling_checkpoints"))
    sources = registry.get("sources")
    if not isinstance(sources, list):
        _issue(issues, "MISSING_OR_INVALID", "$.sources", "expected a list")
        sources = []
    if isinstance(registry.get("source_count"), int) and registry["source_count"] != len(sources):
        _issue(issues, "COUNT_MISMATCH", "$.source_count", f"declared {registry['source_count']} but found {len(sources)}")
    if isinstance(registry.get("checkpoint_count"), int) and registry["checkpoint_count"] != len(checkpoint_map):
        _issue(issues, "COUNT_MISMATCH", "$.checkpoint_count", f"declared {registry['checkpoint_count']} but found {len(checkpoint_map)}")
    seen_sources: set[str] = set()
    for index, source in enumerate(sources):
        _validate_source(issues, source, index, checkpoint_map, registry_as_of)
        if _is_mapping(source) and isinstance(source.get("source_id"), str):
            source_id = source["source_id"]
            if source_id in seen_sources:
                _issue(issues, "DUPLICATE_IDENTIFIER", f"sources[{index}].source_id", f"duplicate source {source_id}")
            seen_sources.add(source_id)

    maintenance = registry.get("maintenance")
    if not _is_mapping(maintenance):
        _issue(issues, "MISSING_OR_INVALID", "$.maintenance", "expected maintenance mapping")
    else:
        _check_keys(issues, maintenance, {"owner", "review_cadence", "rules"}, "$.maintenance")
        for key in ("owner", "review_cadence", "rules"):
            if not isinstance(maintenance.get(key), str) or not maintenance[key].strip():
                _issue(issues, "MISSING_OR_INVALID", f"$.maintenance.{key}", "expected non-empty string")

    if verify_git:
        root = Path(repo_root) if repo_root is not None else Path.cwd()
        _verify_checkpoint_blobs(issues, registry.get("controlling_checkpoints", []), root)
    return tuple(sorted(issues, key=lambda item: (item.path, item.code, item.message)))


def assert_source_registry(
    registry: Any,
    *,
    repo_root: str | Path | None = None,
    verify_git: bool = False,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Validate and return the registry, raising on any issue."""

    issues = validate_source_registry(registry, repo_root=repo_root, verify_git=verify_git, as_of=as_of)
    if issues:
        raise RegistryValidationError(issues)
    return registry


def load_source_registry(
    path: str | Path,
    *,
    repo_root: str | Path | None = None,
    verify_git: bool = False,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Load JSON and fail closed if it is malformed or unsupported."""

    registry_path = Path(path)
    try:
        with registry_path.open("r", encoding="utf-8") as handle:
            registry = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryValidationError((ValidationIssue("INVALID_JSON", str(registry_path), str(exc)),)) from exc
    return assert_source_registry(registry, repo_root=repo_root, verify_git=verify_git, as_of=as_of)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the IDX source provenance registry")
    parser.add_argument("registry", type=Path)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--verify-git", action="store_true")
    args = parser.parse_args(argv)
    try:
        load_source_registry(args.registry, repo_root=args.repo_root, verify_git=args.verify_git)
    except RegistryValidationError as exc:
        for issue in exc.issues:
            print(issue)
        return 1
    print(f"VALID {args.registry}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
