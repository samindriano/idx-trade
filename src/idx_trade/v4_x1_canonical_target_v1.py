"""Canonical V4-X1 target semantics, frozen from retained V4 lineage.

This module is deliberately small and outcome-free.  It records the exact
construction primitives used by the retained V4-1/V4-3 target materializer so
the protected-evaluation gate can bind to semantic identity rather than to a
historical metric value.
"""

from __future__ import annotations

from typing import Final

CANONICAL_TARGET_ID: Final = (
    "CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1"
)
PREDICTION_FIELD: Final = "alpha_consensus"
ENTRY_PRICE: Final = "Open_(t+1)"
HORIZONS: Final = (5, 10)
CONSENSUS_WEIGHTS: Final = {"h5": 0.5, "h10": 0.5}
RANK_TIE_METHOD: Final = "average"
RANK_ASCENDING: Final = True


def raw_return_definition(horizon: int) -> str:
    """Return the frozen raw-return expression for H5 or H10."""

    if int(horizon) not in HORIZONS:
        raise ValueError("V4-X1 target horizon must be 5 or 10")
    return f"Close_(t+{int(horizon)}) / Open_(t+1) - 1"


def normalized_percentile_rank_definition() -> str:
    """Describe the retained average-tie normalized percentile transform."""

    return "(rank(method='average', ascending=True) - 1) / (n - 1); n=1 -> 0.5"
