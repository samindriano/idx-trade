from __future__ import annotations

from typing import Literal

import pandas as pd

from . import ranking_v4_3_model_eval as base


V4_3_REFERENCE_DATE_TARGET_COVERAGE_GATE = 0.90
V4_3R_DATE_TARGET_COVERAGE_GATE = 0.80


def evaluate_head_by_date_ca80(
    scored_population: pd.DataFrame,
    target_ledger: pd.DataFrame,
    *,
    head: Literal["H5", "H10", "CONSENSUS"],
) -> pd.DataFrame:
    """Run the frozen V4 evaluator with only the preregistered 90% -> 80% delta.

    The inherited V4-3 evaluator blob is intentionally left unchanged.  This
    wrapper temporarily supplies the V4-3R date-level target-coverage threshold,
    calls the exact inherited evaluator, and restores the original module state
    before returning.  Row-level target observability, Top30/no-refill rules,
    metrics, folds, and promotion gates are untouched.
    """

    actual = float(base.DATE_TARGET_COVERAGE_GATE)
    if actual != V4_3_REFERENCE_DATE_TARGET_COVERAGE_GATE:
        raise RuntimeError(
            "V4_3_REFERENCE_EVALUATION_GATE_CHANGED:"
            f"{actual}!={V4_3_REFERENCE_DATE_TARGET_COVERAGE_GATE}"
        )

    try:
        base.DATE_TARGET_COVERAGE_GATE = V4_3R_DATE_TARGET_COVERAGE_GATE
        result = base.evaluate_head_by_date(
            scored_population,
            target_ledger,
            head=head,
        )
    finally:
        base.DATE_TARGET_COVERAGE_GATE = V4_3_REFERENCE_DATE_TARGET_COVERAGE_GATE

    if float(base.DATE_TARGET_COVERAGE_GATE) != V4_3_REFERENCE_DATE_TARGET_COVERAGE_GATE:
        raise RuntimeError("V4_3_REFERENCE_EVALUATION_GATE_NOT_RESTORED")
    return result
