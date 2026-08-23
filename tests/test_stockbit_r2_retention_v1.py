from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.configure_stockbit_r2_retention_v1 import (
    RetentionPolicyError,
    apply_policy,
    build_lifecycle_payload,
    load_policy,
    main,
    payload_sha256,
    preflight_remote_policy,
)


CONFIG = Path("config/stockbit_r2_retention_v1.json")
STORAGE_PREFIX = "stockbit-stream-v2"


def _legacy_delete_rule(rule_id: str, relative_prefix: str) -> dict[str, object]:
    return {
        "id": rule_id,
        "conditions": {"prefix": f"{STORAGE_PREFIX}/{relative_prefix}"},
        "enabled": True,
        "deleteObjectsTransition": {"condition": {"type": "Age", "maxAge": 180 * 86_400}},
    }


def _unrelated_abort_rule() -> dict[str, object]:
    return {
        "id": "Default Multipart Abort Rule",
        "conditions": {"prefix": ""},
        "enabled": True,
        "abortMultipartUploadsTransition": {"condition": {"type": "Age", "maxAge": 604800}},
    }


def test_long_term_policy_has_no_delete_rules_for_research_payloads():
    policy = load_policy(CONFIG)
    payload = build_lifecycle_payload(policy)

    assert policy["schema_version"] == "stockbit_r2_retention_v2"
    assert "retention_days" not in policy
    assert "expire_prefixes" not in policy
    assert set(policy["preserve_prefixes"]) == {
        "raw/",
        "normalized/",
        "manifests/",
        "universe_inputs/",
    }
    assert payload == {"rules": []}
    assert len(payload_sha256(payload)) == 64


def test_manifests_and_universe_inputs_cannot_be_removed_by_project_policy():
    policy = load_policy(CONFIG)
    for forbidden in ("manifests/", "universe_inputs/"):
        policy["preserve_prefixes"] = [prefix for prefix in policy["preserve_prefixes"] if prefix != forbidden]
        with pytest.raises(RetentionPolicyError, match="all Stockbit Stream research prefixes"):
            build_lifecycle_payload(policy)
        policy = load_policy(CONFIG)


def test_dry_run_is_network_free_and_deterministic(capsys, monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("dry-run must not call the Cloudflare API")

    monkeypatch.setattr("scripts.configure_stockbit_r2_retention_v1._request_json", fail_network)
    assert main(["--config", str(CONFIG), "--dry-run"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["lifecycle_payload"] == {"rules": []}
    assert output["lifecycle_payload_sha256"] == payload_sha256(output["lifecycle_payload"])


def test_apply_fails_closed_without_control_plane_token(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.setenv("R2_ACCOUNT_ID", "account")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")
    assert main(["--config", str(CONFIG), "--apply", "--verify"]) == 2


def test_verify_only_fails_closed_without_control_plane_token(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.setenv("R2_ACCOUNT_ID", "account")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")
    assert main(["--config", str(CONFIG), "--verify-only"]) == 2


def test_preflight_removes_only_exact_retired_rules_and_preserves_unrelated_rules():
    policy = load_policy(CONFIG)
    expected = build_lifecycle_payload(policy)
    unrelated = _unrelated_abort_rule()
    response = {
        "success": True,
        "result": {
            "rules": [
                _legacy_delete_rule("stockbit-v2-raw-delete-180d", "raw/"),
                unrelated,
                _legacy_delete_rule("stockbit-v2-normalized-delete-180d", "normalized/"),
            ]
        },
    }

    merged = preflight_remote_policy(response, expected, policy)

    assert merged == {"rules": [unrelated]}


def test_preflight_accepts_already_clean_or_empty_remote_policy():
    policy = load_policy(CONFIG)
    expected = build_lifecycle_payload(policy)
    assert preflight_remote_policy({"success": True, "result": {}}, expected, policy) == expected
    assert preflight_remote_policy({"success": True, "result": expected}, expected, policy) == expected


def test_preflight_rejects_conflicting_retired_rule_id():
    policy = load_policy(CONFIG)
    expected = build_lifecycle_payload(policy)
    conflicting = {
        "rules": [
            {
                "id": "stockbit-v2-raw-delete-180d",
                "conditions": {"prefix": "unexpected/"},
                "enabled": True,
                "deleteObjectsTransition": {"condition": {"type": "Age", "maxAge": 86400}},
            }
        ]
    }
    with pytest.raises(RetentionPolicyError, match="exact old 180-day rule"):
        preflight_remote_policy({"success": True, "result": conflicting}, expected, policy)


def test_preflight_rejects_unowned_delete_for_research_prefix():
    policy = load_policy(CONFIG)
    expected = build_lifecycle_payload(policy)
    conflicting = {
        "rules": [
            {
                "id": "unowned-raw-delete",
                "conditions": {"prefix": f"{STORAGE_PREFIX}/raw/"},
                "enabled": True,
                "deleteObjectsTransition": {"condition": {"type": "Age", "maxAge": 86400}},
            }
        ]
    }
    with pytest.raises(RetentionPolicyError, match="unowned object-delete rule"):
        preflight_remote_policy({"success": True, "result": conflicting}, expected, policy)


def test_preflight_rejects_duplicate_rule_ids():
    policy = load_policy(CONFIG)
    expected = build_lifecycle_payload(policy)
    duplicate = _unrelated_abort_rule()
    with pytest.raises(RetentionPolicyError, match="duplicate rule ids"):
        preflight_remote_policy({"success": True, "result": {"rules": [duplicate, duplicate]}}, expected, policy)


def test_apply_puts_only_preserved_unrelated_rules(monkeypatch):
    policy = load_policy(CONFIG)
    expected = build_lifecycle_payload(policy)
    unrelated = _unrelated_abort_rule()
    preflight_response = {
        "success": True,
        "result": {
            "rules": [
                _legacy_delete_rule("stockbit-v2-raw-delete-180d", "raw/"),
                _legacy_delete_rule("stockbit-v2-normalized-delete-180d", "normalized/"),
                unrelated,
            ]
        },
    }
    verify_response = {"success": True, "result": {"rules": [unrelated]}}
    responses = iter([preflight_response, verify_response])
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_request(method, url, token, payload=None):
        calls.append((method, payload))
        if method == "GET":
            return next(responses)
        assert method == "PUT"
        assert payload == {"rules": [unrelated]}
        return {"success": True, "result": {"rules": [unrelated]}}

    monkeypatch.setattr("scripts.configure_stockbit_r2_retention_v1._request_json", fake_request)
    applied = apply_policy("account", "bucket", "token", expected, policy, verify=True)

    assert applied == {"rules": [unrelated]}
    assert [method for method, _ in calls] == ["GET", "PUT", "GET"]
