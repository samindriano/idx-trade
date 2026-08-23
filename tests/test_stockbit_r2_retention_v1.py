from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.configure_stockbit_r2_retention_v1 import (
    RetentionPolicyError,
    build_lifecycle_payload,
    load_policy,
    main,
    payload_sha256,
    preflight_remote_policy,
)


CONFIG = Path("config/stockbit_r2_retention_v1.json")


def test_pinned_policy_expires_only_raw_and_normalized_after_180_days():
    policy = load_policy(CONFIG)
    payload = build_lifecycle_payload(policy)
    assert [rule["conditions"]["prefix"] for rule in payload["rules"]] == [
        "stockbit-stream-v2/raw/",
        "stockbit-stream-v2/normalized/",
    ]
    assert [rule["deleteObjectsTransition"]["condition"] for rule in payload["rules"]] == [
        {"type": "Age", "maxAge": 180 * 86_400},
        {"type": "Age", "maxAge": 180 * 86_400},
    ]
    assert all("manifests/" not in rule["conditions"]["prefix"] for rule in payload["rules"])
    assert all("universe_inputs/" not in rule["conditions"]["prefix"] for rule in payload["rules"])
    assert len(payload_sha256(payload)) == 64


def test_policy_rejects_overlapping_preserve_and_expire_prefixes():
    policy = load_policy(CONFIG)
    policy["expire_prefixes"] = ["manifests/archive/"]
    with pytest.raises(RetentionPolicyError, match="overlap"):
        build_lifecycle_payload(policy)


def test_dry_run_is_network_free_and_deterministic(capsys, monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("dry-run must not call the Cloudflare API")

    monkeypatch.setattr("scripts.configure_stockbit_r2_retention_v1._request_json", fail_network)
    assert main(["--config", str(CONFIG), "--dry-run"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["lifecycle_payload"]["rules"][0]["enabled"] is True
    assert output["lifecycle_payload_sha256"] == payload_sha256(output["lifecycle_payload"])


def test_apply_fails_closed_without_control_plane_token(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.setenv("R2_ACCOUNT_ID", "account")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")
    assert main(["--config", str(CONFIG), "--apply", "--verify"]) == 2


def test_preflight_rejects_unowned_remote_lifecycle_rule():
    policy = load_policy(CONFIG)
    expected = build_lifecycle_payload(policy)
    foreign = {
        "rules": [
            {
                "id": "unrelated-rule",
                "conditions": {"prefix": "stockbit-stream-v1/"},
                "enabled": True,
                "deleteObjectsTransition": {"condition": {"type": "Age", "maxAge": 86400}},
            }
        ]
    }
    with pytest.raises(RetentionPolicyError, match="unowned"):
        preflight_remote_policy({"success": True, "result": foreign}, expected)


def test_preflight_accepts_empty_or_exact_owned_policy():
    policy = load_policy(CONFIG)
    expected = build_lifecycle_payload(policy)
    preflight_remote_policy({"success": True, "result": {}}, expected)
    preflight_remote_policy({"success": True, "result": expected}, expected)
