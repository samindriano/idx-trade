"""Render and optionally apply the bounded Stockbit R2 lifecycle policy.

This is a control-plane utility only.  It never lists, reads, or deletes R2
objects.  Applying the policy requires an explicitly supplied Cloudflare API
token and performs a PUT followed by a strict GET verification of the bucket
lifecycle rules.
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


SECONDS_PER_DAY = 86_400
DEFAULT_CONFIG = Path("config/stockbit_r2_retention_v1.json")
API_ROOT = "https://api.cloudflare.com/client/v4"


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
    if policy.get("schema_version") != "stockbit_r2_retention_v1":
        raise RetentionPolicyError("unsupported retention policy schema")
    storage_prefix = _require_nonempty_string(policy.get("storage_prefix"), "storage_prefix").strip("/")
    if not storage_prefix or storage_prefix.startswith(".") or ".." in Path(storage_prefix).parts:
        raise RetentionPolicyError("storage_prefix must be a safe non-empty prefix")
    try:
        retention_days = int(policy["retention_days"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RetentionPolicyError("retention_days must be an integer") from exc
    if retention_days <= 0:
        raise RetentionPolicyError("retention_days must be positive")
    preserve = _normalise_prefixes(policy.get("preserve_prefixes", []), "preserve_prefixes")
    expire = _normalise_prefixes(policy.get("expire_prefixes", []), "expire_prefixes")
    if not preserve or not expire:
        raise RetentionPolicyError("preserve_prefixes and expire_prefixes must both be non-empty")
    full_preserve = [f"{storage_prefix}/{value}" for value in preserve]
    full_expire = [f"{storage_prefix}/{value}" for value in expire]
    for preserve_prefix in full_preserve:
        for expire_prefix in full_expire:
            if preserve_prefix.startswith(expire_prefix) or expire_prefix.startswith(preserve_prefix):
                raise RetentionPolicyError("preserve and expire prefixes overlap")
    return {
        "schema_version": policy["schema_version"],
        "storage_prefix": storage_prefix,
        "retention_days": retention_days,
        "preserve_prefixes": preserve,
        "expire_prefixes": expire,
        "policy_intent": policy.get("policy_intent", ""),
    }


def build_lifecycle_payload(policy: dict[str, Any]) -> dict[str, Any]:
    """Build the exact Cloudflare R2 REST lifecycle payload."""
    validated = {
        "schema_version": policy.get("schema_version"),
        "storage_prefix": policy.get("storage_prefix"),
        "retention_days": policy.get("retention_days"),
        "preserve_prefixes": policy.get("preserve_prefixes"),
        "expire_prefixes": policy.get("expire_prefixes"),
        "policy_intent": policy.get("policy_intent", ""),
    }
    # Reuse the same validation path for callers that pass an in-memory policy.
    storage_prefix = _require_nonempty_string(validated["storage_prefix"], "storage_prefix").strip("/")
    try:
        retention_days = int(validated["retention_days"])
    except (TypeError, ValueError) as exc:
        raise RetentionPolicyError("retention_days must be an integer") from exc
    if retention_days <= 0:
        raise RetentionPolicyError("retention_days must be positive")
    preserve = _normalise_prefixes(validated["preserve_prefixes"] or [], "preserve_prefixes")
    expire = _normalise_prefixes(validated["expire_prefixes"] or [], "expire_prefixes")
    if not preserve or not expire:
        raise RetentionPolicyError("preserve_prefixes and expire_prefixes must both be non-empty")
    full_preserve = [f"{storage_prefix}/{value}" for value in preserve]
    full_expire = [f"{storage_prefix}/{value}" for value in expire]
    for preserve_prefix in full_preserve:
        for expire_prefix in full_expire:
            if preserve_prefix.startswith(expire_prefix) or expire_prefix.startswith(preserve_prefix):
                raise RetentionPolicyError("preserve and expire prefixes overlap")
    max_age = retention_days * SECONDS_PER_DAY
    rules = []
    for relative_prefix in expire:
        full_prefix = f"{storage_prefix}/{relative_prefix}"
        rule_slug = relative_prefix.rstrip("/").replace("/", "-")
        rules.append(
            {
                "id": f"stockbit-v2-{rule_slug}-delete-{retention_days}d",
                "conditions": {"prefix": full_prefix},
                "enabled": True,
                "deleteObjectsTransition": {
                    "condition": {"type": "Age", "maxAge": max_age}
                },
            }
        )
    return {"rules": rules}


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


def verify_remote_policy(account_id: str, bucket_name: str, token: str, expected: dict[str, Any]) -> None:
    response = _request_json("GET", lifecycle_url(account_id, bucket_name), token)
    observed = {"rules": _rules_from_response(response, allow_empty=False)}
    expected_sorted = {"rules": sorted(expected.get("rules", []), key=lambda rule: str(rule.get("id", "")))}
    if observed != expected_sorted:
        raise RetentionPolicyError("remote lifecycle rules do not match the pinned policy")


def preflight_remote_policy(response: dict[str, Any], expected: dict[str, Any]) -> None:
    """Reject unknown rules before a PUT that replaces bucket lifecycle state."""
    observed_rules = _rules_from_response(response, allow_empty=True)
    expected_rules = sorted(expected.get("rules", []), key=lambda rule: str(rule.get("id", "")))
    if observed_rules not in ([], expected_rules):
        raise RetentionPolicyError("remote lifecycle contains unowned rules; refusing to replace it")


def apply_policy(account_id: str, bucket_name: str, token: str, payload: dict[str, Any], verify: bool) -> None:
    if not token:
        raise RetentionPolicyError("CLOUDFLARE_API_TOKEN is required for --apply")
    preflight = _request_json("GET", lifecycle_url(account_id, bucket_name), token)
    preflight_remote_policy(preflight, payload)
    _request_json("PUT", lifecycle_url(account_id, bucket_name), token, payload)
    if verify:
        verify_remote_policy(account_id, bucket_name, token, payload)


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
            verify_remote_policy(account_id, bucket_name, token, payload)
            print(json.dumps({"status": "VERIFIED", "lifecycle_payload_sha256": payload_sha256(payload)}, sort_keys=True))
            return 0
        apply_policy(account_id, bucket_name, token, payload, verify=args.verify)
        print(json.dumps({"status": "APPLIED_AND_VERIFIED" if args.verify else "APPLIED", "lifecycle_payload_sha256": payload_sha256(payload)}, sort_keys=True))
        return 0
    except RetentionPolicyError as exc:
        print(f"RETENTION_POLICY_FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
