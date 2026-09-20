from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "research" / "alpha_candidate_era_mechanics_v1.py"
SPEC = importlib.util.spec_from_file_location("alpha_candidate_era_mechanics_v1", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_summarize_reports_year_mechanics_without_admission() -> None:
    rows = []
    for year in (2025, 2026):
        for ticker, rank in (("AAA", 3.0), ("BBB", 2.0), ("CCC", 1.0)):
            rows.append(
                {
                    "ticker": ticker,
                    "date": f"{year}-01-02",
                    "eligible_decision_universe": True,
                    "rank_C1_residual_reversal_5_v1": rank,
                    "rank_C2_participation_confirmation_5_v1": rank,
                    "rank_C3_financial_quality_growth_v1": rank if year == 2026 else None,
                    "rank_C4_path_efficiency_reversal_20_v1": rank,
                }
            )
    result = MODULE.summarize(pd.DataFrame(rows), pd.Series(["2025-01-02", "2026-01-02"]), top_k=3)
    assert result["status"] == "PASS_STRUCTURAL_ERA_MECHANICS"
    assert result["candidate_eras"]["C3"]["2025"]["finite_rows"] == 0
    assert result["candidate_eras"]["C3"]["2026"]["usable_top30_dates"] == 1
    assert result["between_era_selection_overlap"]["C3"]["2025__2026"]["comparable"] is False
    assert result["between_era_selection_overlap"]["C3"]["2025__2026"]["jaccard"] is None
    assert result["admission"]["era_admitted"] is False


def test_duplicate_keys_fail_closed() -> None:
    row = {
        "ticker": "AAA",
        "date": "2025-01-02",
        "eligible_decision_universe": True,
        "rank_C1_residual_reversal_5_v1": 1.0,
        "rank_C2_participation_confirmation_5_v1": 1.0,
        "rank_C3_financial_quality_growth_v1": 1.0,
        "rank_C4_path_efficiency_reversal_20_v1": 1.0,
    }
    with pytest.raises(ValueError, match="duplicate"):
        MODULE.summarize(pd.DataFrame([row, row]), pd.Series(["2025-01-02"]), top_k=1)
