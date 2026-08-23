"""Render and optionally apply the Stockbit R2 long-term retention policy.

This is a control-plane utility only.  It never lists, reads, or deletes R2
objects. Applying the policy removes only the exact project-owned 180-day
expiry rules, preserves unrelated rules verbatim, and performs a PUT followed
by a strict GET verification of the bucket lifecycle rules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_CONFIG = Path("config/stockbit_r2_retention_v1.json")
API_ROOT = "https://api.cloudflare.com/client/v4"
SUPPORTED_SCHEMA = "stockbit_r2_retention_v2"
RAW_PREFIX = "raw/"
NORMALIZED_PREFIX = "normalized/"
PROJECT_OWNED_RULE_IDS = {
    "stockbit-v2-raw-delete-180d",
    "stockbit-v2-normalized-delete-180d",
}


class RetentionPolicyError(RuntimeError):
    """The lifecycle policy is invalid or could not be verified."""


def _require_nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RetentionPolicyError(f"{name} must be a non-empty string")
    return value.strip()


def _normalise_relative_prefix(value: Any, name: str) -> str:
    prefix = _require_nonempty_string(value, name).replace("\\", "/")
    if prefix.startswith("/") or ".." in Path(prefix).parts:
        raise RetentionPolicyError(f"{name} must be a safe relative prefix")
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix


def _normalise_prefixes(values: Any, name: str) -> list[str]:
    if not isinstance(values, list):
        raise RetentionPolicyError(f"{name} must be a list")
    return [_normalise_relative_prefix(value, name) for value in values]


def load_policy(path: Path) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RetentionPolicyError(f"cannot read retention policy: {path}") from exc
    if not isinstance(policy, dict):
        raise RetentionPolicyError("retention policy must be a JSON object")
    if policy.get("schema_version") != SUPPORTED_SCHEMA:
        raise RetentionPolicyError("unsupported retention policy schema")
    storage_prefix = _require_nonempty_string(policy.get("storage_prefix"), "storage_prefix").strip("/")
    if not storage_prefix or storage_prefix.startswith(".") or ".." in Path(storage_prefix).parts:
        raise RetentionPolicyError("storage_prefix must be a safe non-empty prefix")
    preserve = _normalise_prefixes(policy.get("preserve_prefixes", []), "preserve_prefixes")
    if set(preserve) != {RAW_PREFIX, NORMALIZED_PREFIX, "manifests/", "universe_inputs/"}:
        raise RetentionPolicyError("preserve_prefixes must cover all Stockbit Stream research prefixes")
    retired_ids = policy.get("retired_project_rule_ids")
    if not isinstance(retired_ids, list) or set(retired_ids) != PROJECT_OWNED_RULE_IDS:
        raise RetentionPolicyError("retired_project_rule_ids must exactly match the retired project-owned rules")
    return {
        "schema_version": policy["schema_version"],
        "storage_prefix": storage_prefix,
        "preserve_prefixes": preserve,
        "retired_project_rule_ids": sorted(retired_ids),
        "policy_intent": policy.get("policy_intent", ""),
    }


def build_lifecycle_payload(policy: dict[str, Any]) -> dict[str, Any]:
    """Build the exact Cloudflare R2 REST lifecycle payload."""
    # Reuse the same strict validation path for callers that pass an in-memory policy.
    load_policy_from_mapping(policy)
    return {"rules": []}


def load_policy_from_mapping(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise RetentionPolicyError("retention policy must be a JSON object")
    if policy.get("schema_version") != SUPPORTED_SCHEMA:
        raise RetentionPolicyError("unsupported retention policy schema")
    storage_prefix = _require_nonempty_string(policy.get("storage_prefix"), "storage_prefix").strip("/")
    if not storage_prefix or storage_prefix.startswith(".") or ".." in Path(storage_prefix).parts:
        raise RetentionPolicyError("storage_prefix must be a safe non-empty prefix")
    preserve = _normalise_prefixes(policy.get("preserve_prefixes", []), "preserve_prefixes")
    if set(preserve) != {RAW_PREFIX, NORMALIZED_PREFIX, "manifests/", "universe_inputs/"}:
        raise RetentionPolicyError("preserve_prefixes must cover all Stockbit Stream research prefixes")
    retired_ids = policy.get("retired_project_rule_ids")
    if not isinstance(retired_ids, list) or set(retired_ids) != PROJECT_OWNED_RULE_IDS:
        raise RetentionPolicyError("retired_project_rule_ids must exactly match the retired project-owned rules")
    return {
        "schema_version": SUPPORTED_SCHEMA,
        "storage_prefix": storage_prefix,
        "preserve_prefixes": preserve,
        "retired_project_rule_ids": sorted(retired_ids),
        "policy_intent": policy.get("policy_intent", ""),
    }


def canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def payload_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload_bytes(payload)).hexdigest()


def lifecycle_url(account_id: str, bucket_name: str) -> str:
    account = _require_nonempty_string(account_id, "account_id")
    bucket = _require_nonempty_string(bucket_name, "bucket_name")
    return f"{API_ROOT}/accounts/{quote(account, safe='')}/r2/buckets/{quote(bucket, safe='')}/lifecycle"


def _request_json(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else canonical_payload_bytes(payload)
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read()
    except HTTPError as exc:
        raise RetentionPolicyError(f"Cloudflare lifecycle {method} failed: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RetentionPolicyError(f"Cloudflare lifecycle {method} transport failed") from exc
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RetentionPolicyError("Cloudflare lifecycle response was not valid JSON") from exc
    if not isinstance(parsed, dict) or parsed.get("success") is not True:
        raise RetentionPolicyError("Cloudflare lifecycle response was not successful")
    return parsed


def _rules_from_response(response: dict[str, Any], *, allow_empty: bool) -> list[dict[str, Any]]:
    result = response.get("result")
    if not isinstance(result, dict):
        raise RetentionPolicyError("Cloudflare lifecycle response did not contain rules")
    if "rules" not in result:
        if allow_empty and result == {}:
            return []
        raise RetentionPolicyError("Cloudflare lifecycle response did not contain rules")
    rules = result["rules"]
    if not isinstance(rules, list):
        raise RetentionPolicyError("Cloudflare lifecycle response contains malformed rules")
    if not all(isinstance(rule, dict) for rule in rules):
        raise RetentionPolicyError("Cloudflare lifecycle response contains malformed rules")
    return sorted(rules, key=lambda rule: str(rule.get("id", "")))


def _safe_rule_summary(rule: dict[str, Any]) -> dict[str, Any]:
    conditions = rule.get("conditions") if isinstance(rule.get("conditions"), dict) else {}
    transition = rule.get("deleteObjectsTransition") if isinstance(rule.get("deleteObjectsTransition"), dict) else {}
    transition_condition = transition.get("condition") if isinstance(transition.get("condition"), dict) else {}
    return {
        "id": rule.get("id"),
        "prefix": conditions.get("prefix"),
        "enabled": rule.get("enabled"),
        "delete_type": transition_condition.get("type"),
        "delete_max_age": transition_condition.get("maxAge"),
    }


def _retired_rule_shapes(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validated = load_policy_from_mapping(policy)
    storage_prefix = validated["storage_prefix"]
    max_age = 180 * 86_400
    return {
        "stockbit-v2-raw-delete-180d": {
            "id": "stockbit-v2-raw-delete-180d",
            "conditions": {"prefix": f"{storage_prefix}/{RAW_PREFIX}"},
            "enabled": True,
            "deleteObjectsTransition": {"condition": {"type": "Age", "maxAge": max_age}},
        },
        "stockbit-v2-normalized-delete-180d": {
            "id": "stockbit-v2-normalized-delete-180d",
            "conditions": {"prefix": f"{storage_prefix}/{NORMALIZED_PREFIX}"},
            "enabled": True,
            "deleteObjectsTransition": {"condition": {"type": "Age", "maxAge": max_age}},
        },
    }


def _targets_retired_prefix(rule: dict[str, Any], policy: dict[str, Any]) -> bool:
    conditions = rule.get("conditions")
    if not isinstance(conditions, dict):
        return False
    prefix = conditions.get("prefix")
    storage_prefix = load_policy_from_mapping(policy)["storage_prefix"]
    return prefix in {f"{storage_prefix}/{RAW_PREFIX}", f"{storage_prefix}/{NORMALIZED_PREFIX}"}


def _has_object_delete_transition(rule: dict[str, Any]) -> bool:
    return isinstance(rule.get("deleteObjectsTransition"), dict)


def verify_remote_policy(
    account_id: str,
    bucket_name: str,
    token: str,
    expected: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    response = _request_json("GET", lifecycle_url(account_id, bucket_name), token)
    observed = {"rules": _rules_from_response(response, allow_empty=True)}
    expected_sorted = preflight_remote_policy(response, expected, policy)
    if observed != expected_sorted:
        raise RetentionPolicyError("remote lifecycle rules do not match the long-term policy")


def preflight_remote_policy(
    response: dict[str, Any],
    expected: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Remove exact retired rules and preserve every unrelated rule verbatim."""
    observed_rules = _rules_from_response(response, allow_empty=True)
    expected_rules = sorted(expected.get("rules", []), key=lambda rule: str(rule.get("id", "")))
    retired_shapes = _retired_rule_shapes(policy)
    observed_ids: list[str] = []
    for rule in observed_rules:
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            raise RetentionPolicyError("remote lifecycle contains a rule without a stable id")
        if rule_id in observed_ids:
            raise RetentionPolicyError("remote lifecycle contains duplicate rule ids")
        observed_ids.append(rule_id)
    preserved_rules: list[dict[str, Any]] = []
    for rule in observed_rules:
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            raise RetentionPolicyError("remote lifecycle contains a rule without a stable id")
        if rule_id in retired_shapes:
            if rule != retired_shapes[rule_id]:
                summary = _safe_rule_summary(rule)
                raise RetentionPolicyError(
                    "remote lifecycle retired-rule id does not match the exact old 180-day rule; "
                    f"observed_rule={json.dumps(summary, sort_keys=True, separators=(',', ':'))}"
                )
            continue
        if _targets_retired_prefix(rule, policy) and _has_object_delete_transition(rule):
            summary = _safe_rule_summary(rule)
            raise RetentionPolicyError(
                "remote lifecycle contains an unowned object-delete rule for a Stockbit research prefix; "
                f"observed_rule={json.dumps(summary, sort_keys=True, separators=(',', ':'))}"
            )
        preserved_rules.append(rule)
    return {"rules": sorted([*preserved_rules, *expected_rules], key=lambda rule: str(rule.get("id", "")))}


def apply_policy(
    account_id: str,
    bucket_name: str,
    token: str,
    payload: dict[str, Any],
    policy: dict[str, Any],
    verify: bool,
) -> dict[str, Any]:
    if not token:
        raise RetentionPolicyError("CLOUDFLARE_API_TOKEN is required for --apply")
    preflight = _request_json("GET", lifecycle_url(account_id, bucket_name), token)
    applied_payload = preflight_remote_policy(preflight, payload, policy)
    _request_json("PUT", lifecycle_url(account_id, bucket_name), token, applied_payload)
    if verify:
        verify_remote_policy(account_id, bucket_name, token, payload, policy)
    return applied_payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="render policy without network access")
    mode.add_argument("--apply", action="store_true", help="apply policy through the Cloudflare REST API")
    mode.add_argument("--verify-only", action="store_true", help="verify the existing remote policy only")
    parser.add_argument("--verify", action="store_true", help="GET and compare policy after --apply")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        policy = load_policy(args.config)
        payload = build_lifecycle_payload(policy)
        result = {
            "schema_version": policy["schema_version"],
            "policy": policy,
            "lifecycle_payload": payload,
            "lifecycle_payload_sha256": payload_sha256(payload),
        }
        if args.dry_run:
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
            return 0
        account_id = os.environ.get("R2_ACCOUNT_ID", "")
        bucket_name = os.environ.get("R2_BUCKET_NAME", "")
        token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
        if args.verify_only:
            if not token:
                raise RetentionPolicyError("CLOUDFLARE_API_TOKEN is required for --verify-only")
            verify_remote_policy(account_id, bucket_name, token, payload, policy)
            print(json.dumps({"status": "VERIFIED", "lifecycle_payload_sha256": payload_sha256(payload)}, sort_keys=True))
            return 0
        applied_payload = apply_policy(account_id, bucket_name, token, payload, policy, verify=args.verify)
        print(json.dumps({"status": "APPLIED_AND_VERIFIED" if args.verify else "APPLIED", "lifecycle_payload_sha256": payload_sha256(applied_payload)}, sort_keys=True))
        return 0
    except RetentionPolicyError as exc:
        print(f"RETENTION_POLICY_FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
