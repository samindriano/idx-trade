import importlib.util
from pathlib import Path
import sys

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_training_price_basis_impact_audit_v1_2.py"
spec = importlib.util.spec_from_file_location("basis_v12", SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_changed_scope_separates_direct_and_spillover():
    frame = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "date": ["2026-01-01"] * 3,
            "changed_feature_count": [1, 1, 0],
            "changed__xs_rank_close_return_5": [True, True, False],
        }
    )
    out = mod.changed_scope_summary(frame, {"AAA"})
    assert out["changed_rows"] == 2
    assert out["direct_changed_rows"] == 1
    assert out["spillover_changed_rows"] == 1


def test_seam_boundary_recovers_scale_ratio():
    basis = pd.DataFrame(
        {
            "ticker": ["AAA"] * 5,
            "date": pd.date_range("2026-01-01", periods=5, freq="D"),
            "panel_close": [100.0, 51.0, 52.0, 53.0, 108.0],
            "idx_close": [100.0, 102.0, 104.0, 106.0, 108.0],
            "price_provenance": ["IDX", "YAHOO_RAW", "YAHOO_RAW", "YAHOO_RAW", "IDX"],
        }
    )
    runs = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "run_id": [1],
            "factor": [2.0],
            "start_date": ["2026-01-02"],
            "end_date": ["2026-01-04"],
        }
    )
    out = mod.seam_boundaries(basis, runs)
    assert len(out) == 2
    assert out["scale_explained"].all()
    assert set(out["boundary"]) == {"ENTRY", "EXIT"}


def test_strict_bool_parses_text():
    out = mod.strict_bool(pd.Series(["true", "false", "TRUE"]), label="x")
    assert out.tolist() == [True, False, True]
