from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "research" / "alpha_candidate_era_authority_v1.py"
SPEC = importlib.util.spec_from_file_location("alpha_candidate_era_authority_v1", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_summarize_keeps_era_descriptive_and_candidate_specific() -> None:
    rows = []
    for year in (2025, 2026):
        for ticker in ("AAA", "BBB"):
            rows.append(
                {
                    "ticker": ticker,
                    "date": f"{year}-01-02",
                    "eligible_decision_universe": True,
                    "C1_residual_reversal_5_v1": 0.1,
                    "C2_participation_confirmation_5_v1": 0.2,
                    "C3_financial_quality_growth_v1": None if year == 2025 else 0.3,
                    "C4_path_efficiency_reversal_20_v1": 0.4,
                    "financial_pit_valid": year == 2026,
                }
            )
    result = MODULE.summarize(pd.DataFrame(rows), pd.Index(["2025-01-02", "2026-01-02"]))
    assert result["status"] == "PASS_STRUCTURAL_ERA_AND_DEPENDENCY_MAP"
    assert result["eras"]["2025"]["candidates"]["C3"]["finite_rows"] == 0
    assert result["eras"]["2026"]["candidates"]["C3"]["finite_rows"] == 2
    assert result["admission"]["era_admitted"] is False


def test_duplicate_keys_fail_closed() -> None:
    row = {
        "ticker": "AAA",
        "date": "2025-01-02",
        "eligible_decision_universe": True,
        "C1_residual_reversal_5_v1": 0.1,
        "C2_participation_confirmation_5_v1": 0.2,
        "C3_financial_quality_growth_v1": 0.3,
        "C4_path_efficiency_reversal_20_v1": 0.4,
        "financial_pit_valid": True,
    }
    with pytest.raises(ValueError, match="duplicate"):
        MODULE.summarize(pd.DataFrame([row, row]), pd.Index(["2025-01-02"]))
