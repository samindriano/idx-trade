"""Optional accepted-context attestation for a controlled Price State smoke.

The prospective Price State sidecar is already immutable.  This module does
not rewrite that manifest.  Instead it can create a sibling attestation that
binds the Price State manifest SHA to an independently accepted Foreign Flow
Representation V2 manifest SHA when both were built from the same historical
market/calendar/extension-session context.

This is deliberately optional and intended for controlled mechanical smokes.
Future live Price State sessions do not depend on the 2026-08-13 Foreign Flow
manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .forward_price_trend_context_bridge import (
    ARTIFACT_FILENAME,
    MANIFEST_FILENAME,
    RuntimeContextPins,
    _date,
    verify_price_trend_state_context_bridge_strict,
)
from .provenance import sha256_file


ATTESTATION_SCHEMA = "idx-trade/price-trend-context-anchor-attestation-v1"
ATTESTATION_STATUS = "PRICE_TREND_CONTEXT_ANCHOR_ATTESTED"
ATTESTATION_FILENAME = "price_trend_context_anchor.attestation.json"

APPROVED_2026_08_13_CONTEXT_ANCHOR_MANIFEST = (
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective"
    r"\foreign_flow_representation_v2\2026-08-13\foreign_flow_representation_v2.manifest.json"
)
APPROVED_2026_08_13_CONTEXT_ANCHOR_MANIFEST_SHA256 = (
    "4095fbfd39a9ef9459bfa68f6ea8560449683133b882671d3176eb070bcbb51d"
)


@dataclass(frozen=True)
class AcceptedContextAnchor:
    manifest_path: Path
    manifest_sha256: str


def approved_2026_08_13_context_anchor() -> AcceptedContextAnchor:
    return AcceptedContextAnchor(
        manifest_path=Path(APPROVED_2026_08_13_CONTEXT_ANCHOR_MANIFEST),
        manifest_sha256=APPROVED_2026_08_13_CONTEXT_ANCHOR_MANIFEST_SHA256,
    )


def _price_directory(runtime_root: Path, feature_session: pd.Timestamp) -> Path:
    return (
        runtime_root
        / "forward_monitoring"
        / "prospective"
        / "price_trend_confirmation_state_v1"
        / feature_session.date().isoformat()
    ).resolve()


def _load_pinned_anchor(anchor: AcceptedContextAnchor) -> tuple[Path, dict[str, Any]]:
    path = anchor.manifest_path.expanduser().resolve()
    expected = str(anchor.manifest_sha256).lower()
    if len(expected) != 64 or not path.is_file() or sha256_file(path) != expected:
        raise RuntimeError("accepted context-anchor manifest missing or hash-mismatched")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("accepted context-anchor manifest is not an object")
    if payload.get("status") != "FOREIGN_FLOW_REPRESENTATION_V2_FORWARD_READY":
        raise RuntimeError("accepted context-anchor status mismatch")
    if payload.get("outcome_blind") is not True:
        raise RuntimeError("accepted context-anchor is not outcome-blind")
    if payload.get("fresh_forward_accessed") is not False:
        raise RuntimeError("accepted context-anchor accessed fresh-forward outcomes")
    if payload.get("outcomes_or_labels_accessed") is not False:
        raise RuntimeError("accepted context-anchor accessed outcomes/labels")
    if payload.get("model_fit") is not False or payload.get("model_scoring") is not False:
        raise RuntimeError("accepted context-anchor contains model access")
    if int(payload.get("provider_calls", -1)) != 0:
        raise RuntimeError("accepted context-anchor was not zero-provider")
    artifact = Path(str(payload.get("artifact_path") or "")).expanduser().resolve()
    expected_artifact_sha = str(payload.get("artifact_sha256") or "").lower()
    if len(expected_artifact_sha) != 64 or not artifact.is_file() or sha256_file(artifact) != expected_artifact_sha:
        raise RuntimeError("accepted context-anchor representation artifact missing or hash-mismatched")
    return path, payload


def _require_equal(left: object, right: object, label: str) -> None:
    if left != right:
        raise RuntimeError(f"accepted context-anchor mismatch: {label}")


def _anchor_source_market_identity(anchor_meta: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(anchor_meta.get("kind") or "")
    if kind == "BRIDGE_ONLY":
        return {
            "kind": kind,
            "session_date": str(anchor_meta.get("session_date") or ""),
            "manifest_path": anchor_meta.get("manifest_path"),
            "manifest_sha256": anchor_meta.get("manifest_sha256"),
            "market_context_path": anchor_meta.get("market_context_path"),
            "market_context_sha256": anchor_meta.get("market_context_sha256"),
        }
    if kind == "CANONICAL_EOD":
        market = anchor_meta.get("market")
        if not isinstance(market, Mapping):
            raise RuntimeError("accepted context-anchor canonical market metadata is missing")
        return {
            "kind": kind,
            "session_date": str(anchor_meta.get("session_date") or ""),
            "parent_manifest_path": market.get("parent_manifest_path"),
            "parent_manifest_sha256": market.get("parent_manifest_sha256"),
        }
    raise RuntimeError(f"accepted context-anchor has unsupported source kind: {kind}")


def _price_source_market_identity(price_meta: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(price_meta.get("kind") or "")
    if kind == "BRIDGE_ONLY":
        return {
            "kind": kind,
            "session_date": str(price_meta.get("session_date") or ""),
            "manifest_path": price_meta.get("manifest_path"),
            "manifest_sha256": price_meta.get("manifest_sha256"),
            "market_context_path": price_meta.get("market_context_path"),
            "market_context_sha256": price_meta.get("market_context_sha256"),
        }
    if kind == "CANONICAL_EOD":
        return {
            "kind": kind,
            "session_date": str(price_meta.get("session_date") or ""),
            "parent_manifest_path": price_meta.get("parent_manifest_path"),
            "parent_manifest_sha256": price_meta.get("parent_manifest_sha256"),
        }
    raise RuntimeError(f"Price State provenance has unsupported source kind: {kind}")


def _match_contexts(price_manifest: Mapping[str, Any], anchor_manifest: Mapping[str, Any]) -> dict[str, Any]:
    price_provenance = price_manifest.get("input_provenance")
    anchor_provenance = anchor_manifest.get("input_provenance")
    if not isinstance(price_provenance, Mapping) or not isinstance(anchor_provenance, Mapping):
        raise RuntimeError("Price/anchor input provenance is missing")

    source = str(price_manifest.get("source_session") or "")
    target = str(price_manifest.get("feature_session") or "")
    _require_equal(anchor_manifest.get("flow_through_session"), source, "source session")
    _require_equal(anchor_manifest.get("feature_session"), target, "feature session")
    _require_equal(anchor_provenance.get("source_session"), source, "anchor provenance source session")
    _require_equal(anchor_provenance.get("feature_session"), target, "anchor provenance feature session")

    direct_pairs = (
        ("historical_panel_path", "historical_panel_path"),
        ("historical_panel_sha256", "historical_panel_sha256"),
        ("historical_calendar_path", "historical_sessions_path"),
        ("historical_calendar_sha256", "historical_sessions_sha256"),
        ("bridge_calendar_path", "bridge_sessions_path"),
        ("bridge_calendar_sha256", "bridge_sessions_sha256"),
        ("combined_session_set_sha256", "combined_session_set_sha256"),
        ("combined_session_count", "combined_session_count"),
        ("combined_session_first", "combined_session_first"),
        ("combined_session_last", "combined_session_last"),
    )
    for price_key, anchor_key in direct_pairs:
        _require_equal(price_provenance.get(price_key), anchor_provenance.get(anchor_key), price_key)

    price_sources = price_provenance.get("extension_session_sources")
    anchor_sources = anchor_provenance.get("extension_session_sources")
    if not isinstance(price_sources, list) or not isinstance(anchor_sources, list):
        raise RuntimeError("Price/anchor extension-session provenance is missing")
    if len(price_sources) != len(anchor_sources):
        raise RuntimeError("accepted context-anchor extension-session count mismatch")

    matched: list[dict[str, Any]] = []
    for position, (price_meta, anchor_meta) in enumerate(zip(price_sources, anchor_sources, strict=True)):
        if not isinstance(price_meta, Mapping) or not isinstance(anchor_meta, Mapping):
            raise RuntimeError("Price/anchor extension-session metadata is invalid")
        price_identity = _price_source_market_identity(price_meta)
        anchor_identity = _anchor_source_market_identity(anchor_meta)
        if price_identity != anchor_identity:
            raise RuntimeError(f"accepted context-anchor source identity mismatch at position {position}")
        matched.append(price_identity)

    return {
        "source_session": source,
        "feature_session": target,
        "historical_panel_sha256": str(price_provenance.get("historical_panel_sha256")),
        "historical_calendar_sha256": str(price_provenance.get("historical_calendar_sha256")),
        "bridge_calendar_sha256": str(price_provenance.get("bridge_calendar_sha256")),
        "combined_session_set_sha256": str(price_provenance.get("combined_session_set_sha256")),
        "matched_extension_sessions": matched,
    }


def _write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def attest_price_trend_context_anchor(
    runtime_root: str | Path,
    feature_session: str | pd.Timestamp,
    *,
    pins: RuntimeContextPins,
    anchor: AcceptedContextAnchor,
) -> dict[str, Any]:
    """Create/reuse one immutable attestation binding Price State to an accepted context manifest."""

    runtime = Path(runtime_root).expanduser().resolve()
    target = _date(feature_session)
    if not verify_price_trend_state_context_bridge_strict(runtime, target, pins=pins):
        raise RuntimeError("Price State sidecar failed bridge-aware strict verification before attestation")

    directory = _price_directory(runtime, target)
    price_manifest_path = directory / MANIFEST_FILENAME
    price_artifact_path = directory / ARTIFACT_FILENAME
    price_manifest = json.loads(price_manifest_path.read_text(encoding="utf-8"))
    anchor_path, anchor_manifest = _load_pinned_anchor(anchor)
    matched = _match_contexts(price_manifest, anchor_manifest)

    anchor_artifact_path = Path(str(anchor_manifest.get("artifact_path"))).expanduser().resolve()
    attestation = {
        "status": ATTESTATION_STATUS,
        "schema": ATTESTATION_SCHEMA,
        "source_session": matched["source_session"],
        "feature_session": matched["feature_session"],
        "price_state_manifest_path": str(price_manifest_path),
        "price_state_manifest_sha256": sha256_file(price_manifest_path),
        "price_state_artifact_path": str(price_artifact_path),
        "price_state_artifact_sha256": sha256_file(price_artifact_path),
        "accepted_context_anchor_manifest_path": str(anchor_path),
        "accepted_context_anchor_manifest_sha256": str(anchor.manifest_sha256).lower(),
        "accepted_context_anchor_artifact_path": str(anchor_artifact_path),
        "accepted_context_anchor_artifact_sha256": str(anchor_manifest.get("artifact_sha256")).lower(),
        "matched_context": matched,
        "optional_controlled_smoke_anchor": True,
        "future_runtime_dependency": False,
        "provider_calls": 0,
        "outcome_blind": True,
        "outcomes_or_labels_accessed": False,
        "model_fit": False,
        "model_scoring": False,
    }
    path = directory / ATTESTATION_FILENAME
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8"))
        if stored != attestation:
            raise RuntimeError("immutable Price State context-anchor attestation revision conflict")
        created = False
    else:
        _write_json_exclusive(path, attestation)
        created = True

    if not verify_price_trend_context_anchor_attestation(runtime, target, pins=pins, anchor=anchor):
        raise RuntimeError("new Price State context-anchor attestation failed verification")
    return {
        "status": ATTESTATION_STATUS,
        "created": created,
        "source_session": matched["source_session"],
        "feature_session": matched["feature_session"],
        "attestation_path": str(path),
        "attestation_sha256": sha256_file(path),
        "provider_calls": 0,
        "outcome_blind": True,
    }


def verify_price_trend_context_anchor_attestation(
    runtime_root: str | Path,
    feature_session: str | pd.Timestamp,
    *,
    pins: RuntimeContextPins,
    anchor: AcceptedContextAnchor,
) -> bool:
    """Re-establish both context lineages and verify the immutable attestation."""

    runtime = Path(runtime_root).expanduser().resolve()
    target = _date(feature_session)
    directory = _price_directory(runtime, target)
    path = directory / ATTESTATION_FILENAME
    if not path.is_file():
        return False
    try:
        if not verify_price_trend_state_context_bridge_strict(runtime, target, pins=pins):
            return False
        price_manifest_path = directory / MANIFEST_FILENAME
        price_artifact_path = directory / ARTIFACT_FILENAME
        price_manifest = json.loads(price_manifest_path.read_text(encoding="utf-8"))
        anchor_path, anchor_manifest = _load_pinned_anchor(anchor)
        matched = _match_contexts(price_manifest, anchor_manifest)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != ATTESTATION_STATUS or payload.get("schema") != ATTESTATION_SCHEMA:
            return False
        if payload.get("source_session") != matched["source_session"] or payload.get("feature_session") != matched["feature_session"]:
            return False
        if Path(str(payload.get("price_state_manifest_path") or "")).expanduser().resolve() != price_manifest_path:
            return False
        if payload.get("price_state_manifest_sha256") != sha256_file(price_manifest_path):
            return False
        if Path(str(payload.get("price_state_artifact_path") or "")).expanduser().resolve() != price_artifact_path:
            return False
        if payload.get("price_state_artifact_sha256") != sha256_file(price_artifact_path):
            return False
        if Path(str(payload.get("accepted_context_anchor_manifest_path") or "")).expanduser().resolve() != anchor_path:
            return False
        if payload.get("accepted_context_anchor_manifest_sha256") != str(anchor.manifest_sha256).lower():
            return False
        anchor_artifact = Path(str(anchor_manifest.get("artifact_path"))).expanduser().resolve()
        if Path(str(payload.get("accepted_context_anchor_artifact_path") or "")).expanduser().resolve() != anchor_artifact:
            return False
        if payload.get("accepted_context_anchor_artifact_sha256") != str(anchor_manifest.get("artifact_sha256")).lower():
            return False
        if payload.get("matched_context") != matched:
            return False
        if payload.get("optional_controlled_smoke_anchor") is not True or payload.get("future_runtime_dependency") is not False:
            return False
        if int(payload.get("provider_calls", -1)) != 0 or payload.get("outcome_blind") is not True:
            return False
        if payload.get("outcomes_or_labels_accessed") is not False:
            return False
        if payload.get("model_fit") is not False or payload.get("model_scoring") is not False:
            return False
        return True
    except Exception:
        return False
