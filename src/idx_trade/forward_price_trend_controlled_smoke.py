"""One-shot zero-provider controlled smoke for bridge-aware Price State V1.

The generic ``run_controlled_smoke`` is testable with synthetic pins.  The CLI
is intentionally locked to the accepted 2026-08-12 -> 2026-08-13 runtime
context and accepted Foreign Flow context-anchor manifest.  It does not install
or modify any scheduler and does not call any provider.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .forward_price_trend_context_anchor import (
    AcceptedContextAnchor,
    approved_2026_08_13_context_anchor,
    attest_price_trend_context_anchor,
    verify_price_trend_context_anchor_attestation,
)
from .forward_price_trend_context_bridge import (
    APPROVED_RUNTIME_ROOT,
    RuntimeContextPins,
    approved_runtime_context_pins,
    produce_price_trend_state_with_context_bridge,
    verify_price_trend_state_context_bridge_strict,
)


CONTROLLED_SOURCE_SESSION = "2026-08-12"
CONTROLLED_FEATURE_SESSION = "2026-08-13"


def run_controlled_smoke(
    *,
    runtime_root: str | Path,
    source_session: str | pd.Timestamp,
    feature_session: str | pd.Timestamp,
    pins: RuntimeContextPins,
    anchor: AcceptedContextAnchor,
) -> dict[str, Any]:
    """Run exactly one mechanical materialization plus idempotent replay."""

    runtime = Path(runtime_root).expanduser().resolve()
    source = pd.Timestamp(source_session).normalize()
    target = pd.Timestamp(feature_session).normalize()

    first = produce_price_trend_state_with_context_bridge(
        runtime_root=runtime,
        source_session=source,
        pins=pins,
    )
    if first.get("source_session") != source.date().isoformat():
        raise RuntimeError("controlled smoke producer returned the wrong source session")
    if first.get("feature_session") != target.date().isoformat():
        raise RuntimeError("controlled smoke producer returned the wrong feature session")
    if first.get("provider_calls") != 0 or first.get("outcome_blind") is not True:
        raise RuntimeError("controlled smoke violated zero-provider/outcome-blind guardrails")
    if not verify_price_trend_state_context_bridge_strict(runtime, target, pins=pins):
        raise RuntimeError("controlled smoke failed bridge-aware strict verification")

    first_attestation = attest_price_trend_context_anchor(
        runtime,
        target,
        pins=pins,
        anchor=anchor,
    )
    if not verify_price_trend_context_anchor_attestation(
        runtime,
        target,
        pins=pins,
        anchor=anchor,
    ):
        raise RuntimeError("controlled smoke failed accepted-context attestation verification")

    second = produce_price_trend_state_with_context_bridge(
        runtime_root=runtime,
        source_session=source,
        pins=pins,
    )
    second_attestation = attest_price_trend_context_anchor(
        runtime,
        target,
        pins=pins,
        anchor=anchor,
    )
    if second.get("created") is not False:
        raise RuntimeError("controlled smoke producer replay was not idempotent")
    if second_attestation.get("created") is not False:
        raise RuntimeError("controlled smoke attestation replay was not idempotent")
    if first.get("artifact_sha256") != second.get("artifact_sha256"):
        raise RuntimeError("controlled smoke artifact hash changed on idempotent replay")
    if first.get("manifest_sha256") != second.get("manifest_sha256"):
        raise RuntimeError("controlled smoke manifest hash changed on idempotent replay")
    if first_attestation.get("attestation_sha256") != second_attestation.get("attestation_sha256"):
        raise RuntimeError("controlled smoke attestation hash changed on idempotent replay")

    manifest_path = Path(str(first["manifest_path"])).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "status": "PRICE_TREND_CONTROLLED_SMOKE_VERIFIED",
        "source_session": source.date().isoformat(),
        "feature_session": target.date().isoformat(),
        "rows": int(first["rows"]),
        "tickers": int(first["tickers"]),
        "artifact_path": first["artifact_path"],
        "artifact_sha256": first["artifact_sha256"],
        "manifest_path": first["manifest_path"],
        "manifest_sha256": first["manifest_sha256"],
        "attestation_path": first_attestation["attestation_path"],
        "attestation_sha256": first_attestation["attestation_sha256"],
        "state_distributions": manifest.get("state_distributions"),
        "runtime_context": first.get("runtime_context"),
        "bridge_strict_verified": True,
        "accepted_context_attested": True,
        "idempotent_replay_verified": True,
        "target_canonical_session_required": False,
        "provider_calls": 0,
        "outcome_blind": True,
        "outcomes_or_labels_accessed": False,
        "model_fit": False,
        "model_scoring": False,
        "trade_recommendation": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the accepted one-shot 2026-08-12 -> 2026-08-13 Price State smoke"
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path(APPROVED_RUNTIME_ROOT),
        help="Existing IDX-Trade runtime/data root. Defaults to the accepted Windows root.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_controlled_smoke(
        runtime_root=args.runtime_root,
        source_session=CONTROLLED_SOURCE_SESSION,
        feature_session=CONTROLLED_FEATURE_SESSION,
        pins=approved_runtime_context_pins(),
        anchor=approved_2026_08_13_context_anchor(),
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
