from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_a_open_lineage_remediation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("phase_a_open_lineage_remediation_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fixtures():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
    parent = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "CCC"],
            "date": dates,
            "session_index": [1, 2, 3, 4],
            "market_state": ["ACTIVE"] * 4,
            "accepted_open": [10.0, 20.0, 30.0, 40.0],
            "open_admitted": [True, True, True, True],
            "close": [11.0, 21.0, 31.0, 41.0],
            "close_admitted": [True] * 4,
        }
    )
    clean = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "CCC"],
            "date": dates,
            # Row 2 is admitted remediation, row 3 is fail-closed remediation.
            # Rows 1 and 4 deliberately differ from parent executable Open to
            # prove that non-candidate panel Open is ignored by this layer.
            "open": [999.0, 22.0, np.nan, 777.0],
            "close": [11.0, 21.5, 31.5, 41.0],
        }
    )
    provenance = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "CCC"],
            "date": dates,
            "open_repaired": [False, True, False, False],
            "open_fail_closed_candidate": [False, False, True, False],
            "hlc_repaired": [False, True, True, False],
            "open_source": [
                "PARENT_UNCHANGED_OPEN_PROVENANCE_UNSPECIFIED",
                "IDX_OFFICIAL_OPENPRICE",
                "FAIL_CLOSED_UNAVAILABLE",
                "PARENT_UNCHANGED_OPEN_PROVENANCE_UNSPECIFIED",
            ],
        }
    )
    return parent, clean, provenance


def test_preserves_parent_executable_open_outside_candidates():
    module = load_module()
    parent, clean, provenance = fixtures()
    result, stats = module.apply_clean_open_lineage(
        parent,
        clean,
        provenance,
        expected_candidate_rows=2,
        expected_admitted_rows=1,
        expected_fail_closed_rows=1,
    )
    # Non-candidate rows remain parent executable Open even though clean-panel
    # raw Open deliberately differs.
    assert result.loc[0, "accepted_open"] == 10.0
    assert result.loc[3, "accepted_open"] == 40.0
    assert bool(result.loc[0, "open_admitted"])
    assert bool(result.loc[3, "open_admitted"])
    assert stats["non_candidate_open_value_exact_parity"] is True
    assert stats["non_candidate_open_admission_exact_parity"] is True


def test_overrides_only_admitted_and_fail_closed_candidates():
    module = load_module()
    parent, clean, provenance = fixtures()
    result, stats = module.apply_clean_open_lineage(
        parent,
        clean,
        provenance,
        expected_candidate_rows=2,
        expected_admitted_rows=1,
        expected_fail_closed_rows=1,
    )
    assert result.loc[1, "accepted_open"] == 22.0
    assert bool(result.loc[1, "open_admitted"])
    assert np.isnan(result.loc[2, "accepted_open"])
    assert not bool(result.loc[2, "open_admitted"])
    # Clean Close/HLC lineage is still used independently of Open lineage.
    assert result.loc[1, "close"] == 21.5
    assert result.loc[2, "close"] == 31.5
    assert stats["candidate_rows"] == 2
    assert stats["admitted_rows"] == 1
    assert stats["fail_closed_rows"] == 1


def test_rejects_candidate_population_drift():
    module = load_module()
    parent, clean, provenance = fixtures()
    with pytest.raises(RuntimeError, match="POPULATION_CHANGED"):
        module.apply_clean_open_lineage(
            parent,
            clean,
            provenance,
            expected_candidate_rows=3,
            expected_admitted_rows=1,
            expected_fail_closed_rows=1,
        )


def test_rejects_candidate_vs_hlc_identity_drift():
    module = load_module()
    parent, clean, provenance = fixtures()
    provenance.loc[0, "hlc_repaired"] = True
    with pytest.raises(RuntimeError, match="CANDIDATE_HLC_IDENTITY_DRIFT"):
        module.apply_clean_open_lineage(
            parent,
            clean,
            provenance,
            expected_candidate_rows=2,
            expected_admitted_rows=1,
            expected_fail_closed_rows=1,
        )


def test_wrapper_has_no_outcome_or_model_execution_paths():
    source = RUNNER.read_text(encoding="utf-8")
    forbidden = (
        "materialize_v4_target_ledger",
        "fit_v4_head(",
        "evaluate_model",
        "historical_performance(",
        "target_rank",
        "raw_return",
    )
    for token in forbidden:
        assert token not in source
