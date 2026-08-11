import numpy as np
import pandas as pd
import pytest

from idx_trade.open_research_coverage import _feature_readiness, apply_smb_overlay


def _panel():
    return pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "SMBR"],
            "date": pd.to_datetime(["2023-03-13", "2023-03-14", "2023-03-14"]),
            "high": [110.0, 120.0, 388.0],
            "low": [90.0, 100.0, 372.0],
            "close": [100.0, 110.0, 372.0],
            "open": [100.0, np.nan, np.nan],
            "open_available": [True, False, False],
            "open_evidence_status": ["EXISTING", "OPEN_UNAVAILABLE", "OPEN_UNAVAILABLE"],
        }
    )


def _provenance():
    return pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "SMBR"],
            "date": pd.to_datetime(["2023-03-13", "2023-03-14", "2023-03-14"]),
            "open_source": ["IMMUTABLE_PANEL", None, None],
            "open_evidence_class": ["EXISTING_IMMUTABLE", None, None],
            "validation_status": ["PRESERVED", "UNRESOLVED", "UNRESOLVED"],
            "tradingview_open": [np.nan, np.nan, np.nan],
            "tradingview_high": [np.nan, np.nan, np.nan],
            "tradingview_low": [np.nan, np.nan, np.nan],
            "tradingview_close": [np.nan, np.nan, np.nan],
        }
    )


def _candidate():
    return pd.DataFrame(
        {
            "ticker": ["SMBR"],
            "date": ["2023-03-14"],
            "raw_open": [388.0],
            "raw_high": [388.0],
            "raw_low": [372.0],
            "raw_close": [372.0],
            "hlc_exact": [True],
            "admission_status": ["ADMISSIBLE_OPEN_EVIDENCE"],
        }
    )


def test_overlay_changes_only_authorized_row_and_preserves_existing_open():
    overlay, provenance, change = apply_smb_overlay(_panel(), _provenance(), _candidate())
    assert overlay.loc[(overlay.ticker == "SMBR"), "open"].iloc[0] == 388.0
    assert overlay.loc[(overlay.ticker == "AAA") & overlay.date.eq(pd.Timestamp("2023-03-13")), "open"].iloc[0] == 100.0
    assert provenance.loc[provenance.ticker.eq("SMBR"), "open_source"].iloc[0] == "ZAPI_TRADINGVIEW_REMEDIATION"
    assert change["existing_open_overwritten"] is False


def test_overlay_rejects_hlc_mismatch():
    candidate = _candidate()
    candidate.loc[0, "raw_high"] = 389.0
    with pytest.raises(ValueError, match="H/L/C"):
        apply_smb_overlay(_panel(), _provenance(), candidate)


def test_feature_readiness_keeps_flat_range_open_position_unknown():
    overlay, _, _ = apply_smb_overlay(_panel(), _provenance(), _candidate())
    feature_panel = _panel()
    target = feature_panel.ticker.eq("AAA") & feature_panel.date.eq(pd.Timestamp("2023-03-14"))
    feature_panel.loc[target, ["high", "low", "close"]] = [110.0, 110.0, 110.0]
    overlay.loc[overlay.ticker.eq("AAA") & overlay.date.eq(pd.Timestamp("2023-03-14")), "open"] = 110.0
    eligible = pd.DataFrame({"ticker": ["AAA"], "date": pd.to_datetime(["2023-03-14"]), "signal_session_index": [2]})
    rows, summary = _feature_readiness(eligible, feature_panel, overlay)
    assert int(rows["open_feature_ready"].sum()) == 0
    assert int(summary.loc[summary.feature.eq("all_open_features_after_lag_and_range"), "usable_rows"].iloc[0]) == 0
