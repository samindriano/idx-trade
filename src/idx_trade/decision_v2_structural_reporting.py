from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd

from .decision_v2_structural_replay import (
    StructuralReplayResult,
    _quantiles,
)
from .decision_v2_structural_source import EXPECTED_REPLAY_CONTRACT_SHA256


def enrich_structural_replay_reporting(
    result: StructuralReplayResult,
) -> StructuralReplayResult:
    """Add preregistered descriptive reporting without changing any gate.

    This function is deliberately downstream of the frozen policy and gate
    evaluator. It only derives additional descriptive statistics from the
    already-produced structural membership/session ledgers.
    """

    summary: dict[str, Any] = deepcopy(result.summary)
    memberships = result.primary.membership_ledger
    sessions = result.primary.session_ledger

    if memberships.empty:
        ranks_gt20 = pd.Series(dtype=float)
    else:
        ranks_gt20 = pd.to_numeric(
            memberships.loc[
                memberships["rank_consensus"].gt(20),
                "rank_consensus",
            ],
            errors="coerce",
        ).dropna()

    if sessions.empty:
        count_per_session = pd.Series(dtype=float)
    else:
        count_per_session = pd.to_numeric(
            sessions["target_rank_gt20_count"],
            errors="coerce",
        ).dropna()

    rank_quality = dict(summary["metrics"]["rank_quality"])
    rank_quality["target_rank_gt20_rank_distribution"] = _quantiles(
        ranks_gt20
    )
    rank_quality["target_rank_gt20_count_per_session_distribution"] = (
        _quantiles(count_per_session)
    )
    rank_quality["target_rank_gt20_unique_tickers"] = (
        int(
            memberships.loc[
                memberships["rank_consensus"].gt(20),
                "ticker",
            ].nunique()
        )
        if not memberships.empty
        else 0
    )
    summary["metrics"] = dict(summary["metrics"])
    summary["metrics"]["rank_quality"] = rank_quality

    summary["source"] = dict(summary["source"])
    summary["source"]["replay_contract_sha256"] = (
        EXPECTED_REPLAY_CONTRACT_SHA256
    )
    summary["reporting"] = {
        "post_gate_descriptive_enrichment_only": True,
        "gate_values_changed": False,
        "rank_gt20_distribution_reported": True,
    }

    return StructuralReplayResult(
        primary=result.primary,
        summary=summary,
    )
