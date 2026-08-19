from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.price_basis_post_remediation_guard import open_hlc_audit


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_price_basis_open_hlc_recertification_v1.py"


def test_open_hlc_audit_flags_range_violation_without_repair() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "AAA"],
            "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "low": [90.0, 90.0, 90.0],
            "high": [110.0, 110.0, 110.0],
            "accepted_open": [100.0, 111.0, np.nan],
        }
    )

    audited, summary = open_hlc_audit(frame, open_column="accepted_open")

    assert summary == {
        "rows": 3,
        "valid_hlc_rows": 3,
        "open_available_rows": 2,
        "open_within_rows": 1,
        "open_range_violation_rows": 1,
        "invalid_hlc_rows": 0,
    }
    assert audited.loc[0, "open_within_corrected_hlc"] == True  # noqa: E712
    assert audited.loc[1, "open_within_corrected_hlc"] == False  # noqa: E712
    assert pd.isna(audited.loc[2, "open_within_corrected_hlc"])


def test_open_hlc_audit_fails_closed_on_invalid_corrected_range() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": ["2026-01-01"],
            "low": [110.0],
            "high": [90.0],
            "open": [100.0],
        }
    )

    _, summary = open_hlc_audit(frame, open_column="open")

    assert summary["invalid_hlc_rows"] == 1
    assert summary["open_range_violation_rows"] == 1


def test_standalone_runner_is_open_only_and_reconstructs_v4x_open_lineage() -> None:
    source = RUNNER.read_text(encoding="utf-8")

    assert "REMEDIATION_MANIFEST_SHA256" in source
    assert "EXPECTED_REPAIR_ROWS = 1657" in source
    assert "EXPECTED_REPAIR_TICKERS = 12" in source
    assert "run_training_price_basis_impact_audit_v1.py" in source
    assert "build_price_evidence" in source
    assert "accepted_open" in source
    assert "open_admitted" in source
    assert "panel_open_vs_corrected_hlc_repaired_rows.csv" in source
    assert '"model_fit": False' in source
    assert '"model_scoring": False' in source
    assert '"target_values_accessed": False' in source
    assert '"protected_forward_accessed": False' in source
    assert '"provider_calls": False' in source
    assert '"volume_or_value_audited": False' in source
    assert '"volume_or_value_repaired": False' in source

    # This gate must remain independent from the separate liquidity audit lane.
    assert "VOLUME_VALUE_MANIFEST_SHA256" not in source
    assert "run_price_basis_volume_value_audit_v1.py" not in source
    assert "regular_market_value" not in source
