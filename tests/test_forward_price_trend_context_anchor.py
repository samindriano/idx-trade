from __future__ import annotations

import json
from pathlib import Path

import pytest

from idx_trade.forward_price_trend_context_anchor import (
    ATTESTATION_FILENAME,
    AcceptedContextAnchor,
    attest_price_trend_context_anchor,
    verify_price_trend_context_anchor_attestation,
)
from idx_trade.forward_price_trend_context_bridge import (
    produce_price_trend_state_with_context_bridge,
    verify_price_trend_state_context_bridge_strict,
)
from idx_trade.provenance import sha256_file

# Reuse the synthetic bridge/canonical fixture from the adjacent adapter test;
# this module is collected from the same tests directory under pytest.
from test_forward_price_trend_context_bridge import _fixture


def _accepted_anchor_from_price_result(result: dict[str, object], tmp_path: Path) -> AcceptedContextAnchor:
    price_manifest_path = Path(str(result["manifest_path"]))
    price_manifest = json.loads(price_manifest_path.read_text(encoding="utf-8"))
    provenance = price_manifest["input_provenance"]

    extension_sources = []
    for source in provenance["extension_session_sources"]:
        if source["kind"] == "BRIDGE_ONLY":
            extension_sources.append(
                {
                    "kind": "BRIDGE_ONLY",
                    "session_date": source["session_date"],
                    "manifest_path": source["manifest_path"],
                    "manifest_sha256": source["manifest_sha256"],
                    "market_context_path": source["market_context_path"],
                    "market_context_sha256": source["market_context_sha256"],
                    "foreign_flow_path": source["foreign_flow_path"],
                    "foreign_flow_sha256": source["foreign_flow_sha256"],
                }
            )
        else:
            extension_sources.append(
                {
                    "kind": "CANONICAL_EOD",
                    "session_date": source["session_date"],
                    "market": {
                        "session_date": source["session_date"],
                        "parent_manifest_path": source["parent_manifest_path"],
                        "parent_manifest_sha256": source["parent_manifest_sha256"],
                    },
                    "flow": {"fixture": True},
                }
            )

    anchor_artifact = tmp_path / "foreign_flow_representation_v2.parquet"
    anchor_artifact.write_bytes(b"accepted-anchor-artifact-fixture")
    anchor_manifest = tmp_path / "foreign_flow_representation_v2.manifest.json"
    payload = {
        "status": "FOREIGN_FLOW_REPRESENTATION_V2_FORWARD_READY",
        "flow_through_session": price_manifest["source_session"],
        "feature_session": price_manifest["feature_session"],
        "artifact_path": str(anchor_artifact.resolve()),
        "artifact_sha256": sha256_file(anchor_artifact),
        "input_provenance": {
            "historical_panel_path": provenance["historical_panel_path"],
            "historical_panel_sha256": provenance["historical_panel_sha256"],
            "historical_sessions_path": provenance["historical_calendar_path"],
            "historical_sessions_sha256": provenance["historical_calendar_sha256"],
            "bridge_sessions_path": provenance["bridge_calendar_path"],
            "bridge_sessions_sha256": provenance["bridge_calendar_sha256"],
            "combined_session_set_sha256": provenance["combined_session_set_sha256"],
            "combined_session_count": provenance["combined_session_count"],
            "combined_session_first": provenance["combined_session_first"],
            "combined_session_last": provenance["combined_session_last"],
            "source_session": price_manifest["source_session"],
            "feature_session": price_manifest["feature_session"],
            "extension_session_sources": extension_sources,
        },
        "outcome_blind": True,
        "fresh_forward_accessed": False,
        "outcomes_or_labels_accessed": False,
        "model_fit": False,
        "model_scoring": False,
        "provider_calls": 0,
    }
    anchor_manifest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return AcceptedContextAnchor(anchor_manifest, sha256_file(anchor_manifest))


def test_optional_context_anchor_attestation_binds_both_manifests(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = produce_price_trend_state_with_context_bridge(
        runtime_root=fixture["runtime"], source_session=fixture["source"], pins=fixture["pins"]
    )
    anchor = _accepted_anchor_from_price_result(result, tmp_path)

    first = attest_price_trend_context_anchor(
        fixture["runtime"], fixture["target"], pins=fixture["pins"], anchor=anchor
    )
    second = attest_price_trend_context_anchor(
        fixture["runtime"], fixture["target"], pins=fixture["pins"], anchor=anchor
    )

    assert first["created"] is True
    assert second["created"] is False
    assert first["attestation_sha256"] == second["attestation_sha256"]
    assert verify_price_trend_context_anchor_attestation(
        fixture["runtime"], fixture["target"], pins=fixture["pins"], anchor=anchor
    ) is True


def test_sidecar_remains_valid_without_optional_attestation(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    produce_price_trend_state_with_context_bridge(
        runtime_root=fixture["runtime"], source_session=fixture["source"], pins=fixture["pins"]
    )
    directory = (
        fixture["runtime"]
        / "forward_monitoring"
        / "prospective"
        / "price_trend_confirmation_state_v1"
        / "2026-08-13"
    )
    assert not (directory / ATTESTATION_FILENAME).exists()
    assert verify_price_trend_state_context_bridge_strict(
        fixture["runtime"], fixture["target"], pins=fixture["pins"]
    ) is True


def test_anchor_manifest_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = produce_price_trend_state_with_context_bridge(
        runtime_root=fixture["runtime"], source_session=fixture["source"], pins=fixture["pins"]
    )
    anchor = _accepted_anchor_from_price_result(result, tmp_path)
    bad = AcceptedContextAnchor(anchor.manifest_path, "0" * 64)

    with pytest.raises(RuntimeError, match="context-anchor manifest missing or hash-mismatched"):
        attest_price_trend_context_anchor(
            fixture["runtime"], fixture["target"], pins=fixture["pins"], anchor=bad
        )


def test_rehashed_anchor_with_different_market_context_fails(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = produce_price_trend_state_with_context_bridge(
        runtime_root=fixture["runtime"], source_session=fixture["source"], pins=fixture["pins"]
    )
    anchor = _accepted_anchor_from_price_result(result, tmp_path)
    payload = json.loads(anchor.manifest_path.read_text(encoding="utf-8"))
    payload["input_provenance"]["extension_session_sources"][0]["market_context_sha256"] = "f" * 64
    anchor.manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    repinned = AcceptedContextAnchor(anchor.manifest_path, sha256_file(anchor.manifest_path))

    with pytest.raises(RuntimeError, match="source identity mismatch"):
        attest_price_trend_context_anchor(
            fixture["runtime"], fixture["target"], pins=fixture["pins"], anchor=repinned
        )
