from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd

from .decision_v3_structural_replay import StructuralReplayResult, _quantiles
from .decision_v3_structural_source import (
    EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256,
    canonical_json_sha256,
)


def _count_distribution(values: pd.Series) -> dict[str, int]:
    if values.empty:
        return {}
    counts = values.astype(int).value_counts().sort_index()
    return {str(int(key)): int(value) for key, value in counts.items()}


def enrich_structural_replay_reporting(
    result: StructuralReplayResult,
    contract_path: str | Path,
) -> StructuralReplayResult:
    """Add descriptive-only reporting without changing any gate value.

    This runs strictly after gate evaluation. It may expose distributions useful
    for diagnosis, but it cannot alter thresholds, conditions, or the verdict.
    """
    summary = deepcopy(result.summary)
    membership = result.primary.membership_ledger
    sessions = result.primary.session_ledger

    ranks = pd.to_numeric(membership["rank_consensus"], errors="coerce").dropna()
    gt20 = ranks.loc[ranks.gt(20)]
    gt50 = ranks.loc[ranks.gt(50)]

    contract_payload = __import__("json").loads(
        Path(contract_path).read_text(encoding="utf-8")
    )
    actual_contract_sha = canonical_json_sha256(contract_payload)
    if actual_contract_sha != EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256:
        raise RuntimeError(
            "DECISION_V3_REPORTING_CONTRACT_SHA_MISMATCH:"
            f"{actual_contract_sha}!={EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256}"
        )

    summary["reporting"] = {
        "replay_contract_canonical_sha256": actual_contract_sha,
        "gate_values_changed": False,
        "target_rank_gt20_distribution": _quantiles(gt20),
        "target_rank_gt50_distribution": _quantiles(gt50),
        "rank_gt20_count_per_session_distribution": _count_distribution(
            sessions["target_rank_gt20_count"]
        ),
        "rank_gt50_count_per_session_distribution": _count_distribution(
            sessions["target_rank_gt50_count"]
        ),
        "tier_c_diagnostics_descriptive_only": True,
        "high_churn_attribution_descriptive_only": True,
    }
    return replace(result, summary=summary)
