from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from idx_trade.ranking_v4_3_ca_schedule_reuse import (
    CONFLICT,
    RESOLVED_NON_BLOCKING,
    RESOLVED_TRANSITION,
    UNRESOLVED,
    event_inventory_identity,
    normalize_current_events,
    residual_document_claims,
    resolve_existing_claims,
    schedule_claims,
)


def _sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3"],
            "ticker": ["AAA", "BBB", "CCC"],
            "semantic_class": ["SCHEDULE_REQUIRED"] * 3,
            "source_type": ["Stock Split", "Voluntary Conversion", "Merger"],
            "family": ["STOCK_SPLIT", "VOLUNTARY_CONVERSION", "MERGER"],
        }
    )


def test_exact_identity_only_and_no_fuzzy_reuse() -> None:
    events = normalize_current_events(_events(), expected_count=3)
    schedule = pd.DataFrame(
        {
            "event_id": ["e1", "wrong-id"],
            "ticker": ["AAA", "CCC"],
            "linkage_status": ["EXACT", "EXACT"],
            "transition_date": ["2024-01-03", "2024-01-05"],
            "transition_semantic": ["REGULAR_MARKET_EX_DATE", "REGULAR_MARKET_EX_DATE"],
            "ksei_reference": ["KSEI-1", "KSEI-2"],
            "source_sha256": ["a" * 64, "b" * 64],
        }
    )
    residual = pd.DataFrame(
        {
            "event_id": ["e2"],
            "ticker": ["BBB"],
            "linkage_status": ["EXACT_NON_BLOCKING"],
            "transition_date": [""],
            "transition_semantic": [""],
            "ksei_reference": ["KSEI-3"],
            "source_sha256": ["c" * 64],
        }
    )
    census, _ = resolve_existing_claims(
        events,
        [schedule_claims(schedule, "SCHEDULE"), residual_document_claims(residual, "RESIDUAL")],
    )
    status = dict(zip(census["event_id"], census["reuse_status"]))
    assert status == {
        "e1": RESOLVED_TRANSITION,
        "e2": RESOLVED_NON_BLOCKING,
        "e3": UNRESOLVED,
    }


def test_conflicting_existing_claims_fail_closed() -> None:
    events = normalize_current_events(_events().iloc[[0]].copy(), expected_count=1)
    schedule = pd.DataFrame(
        {
            "event_id": ["e1", "e1"],
            "ticker": ["AAA", "AAA"],
            "linkage_status": ["EXACT", "EXACT"],
            "transition_date": ["2024-01-03", "2024-01-04"],
            "transition_semantic": ["REGULAR_MARKET_EX_DATE", "REGULAR_MARKET_EX_DATE"],
            "ksei_reference": ["KSEI-1", "KSEI-2"],
            "source_sha256": ["a" * 64, "b" * 64],
        }
    )
    census, _ = resolve_existing_claims(events, [schedule_claims(schedule, "SCHEDULE")])
    assert census.iloc[0]["reuse_status"] == CONFLICT


def test_event_inventory_identity_is_order_independent() -> None:
    events = _events()
    assert event_inventory_identity(events) == event_inventory_identity(
        events.sample(frac=1.0, random_state=7).reset_index(drop=True)
    )


def test_pinned_promoted_evidence_hashes_match_repo_bytes() -> None:
    config = json.loads(
        Path("config/v4_3_ca_training_domain_schedule_80_reuse_v1.json").read_text(
            encoding="utf-8"
        )
    )
    for source in config["existing_evidence"].values():
        assert _sha(source["manifest_path"]) == source["manifest_sha256"]
        assert _sha(source["evidence_path"]) == source["evidence_sha256"]


def test_runner_has_no_provider_target_or_model_path() -> None:
    source = Path(
        "scripts/run_v4_3_ca_training_domain_schedule_80_reuse_census.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "requests.get",
        "curl_cffi",
        "urllib.request",
        "materialize_v4_target_ledger",
        "fit_v4_head",
        "score_v4_head",
        "HistGradientBoostingRegressor",
    )
    for token in forbidden:
        assert token not in source
