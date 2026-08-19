import pandas as pd

from idx_trade.price_basis_remediation import (
    apply_hlc_overlay,
    build_hlc_overlay,
    non_hlc_parity,
    select_certified_repairs,
)


def _cert():
    return pd.DataFrame([
        {
            "ticker": "TEST",
            "expected_factor": 2.0,
            "ca_type": "MANDATORY_CONVERSION",
            "ca_ratio": "1:2",
            "record_date": "2026-01-10",
            "distribution_date": "2026-01-11",
            "source": "KSEI",
            "source_url": "https://web.ksei.co.id/services/registered-securities/shares/lc/TEST",
            "certification_status": "CERTIFIED_PRIMARY",
        }
    ])


def _basis():
    return pd.DataFrame([
        {
            "ticker": "TEST",
            "date": "2026-01-05",
            "price_provenance": "YAHOO_RAW",
            "panel_idx_stable_run_member": True,
            "panel_idx_scale_factor": 2.0,
            "panel_high": 50.0,
            "panel_low": 45.0,
            "panel_close": 48.0,
            "idx_high": 100.0,
            "idx_low": 90.0,
            "idx_close": 96.0,
        }
    ])


def test_certified_repair_selection_and_overlay():
    selected, stats = select_certified_repairs(_basis(), _cert())
    assert stats["certified_rows"] == 1
    assert stats["factor_fail_rows"] == 0
    overlay = build_hlc_overlay(selected)
    assert overlay.loc[0, "remediated_close"] == 96.0
    assert overlay.loc[0, "parent_price_provenance"] == "YAHOO_RAW"


def test_post_record_row_is_not_certified():
    basis = _basis()
    basis.loc[0, "date"] = "2026-01-10"
    _, stats = select_certified_repairs(basis, _cert())
    assert stats["certified_rows"] == 0
    assert stats["post_or_on_record_date_rows"] == 1


def test_factor_mismatch_is_not_certified():
    basis = _basis()
    basis.loc[0, "panel_idx_scale_factor"] = 5.0
    _, stats = select_certified_repairs(basis, _cert())
    assert stats["certified_rows"] == 0
    assert stats["factor_fail_rows"] == 1


def test_overlay_changes_only_hlc():
    panel = pd.DataFrame([
        {
            "ticker": "TEST",
            "date": "2026-01-05",
            "high": 50.0,
            "low": 45.0,
            "close": 48.0,
            "volume": 123.0,
            "regular_market_value": 456.0,
            "price_provenance": "YAHOO_RAW",
        }
    ])
    selected, _ = select_certified_repairs(_basis(), _cert())
    corrected = apply_hlc_overlay(panel, build_hlc_overlay(selected))
    assert corrected.loc[0, "high"] == 100.0
    assert corrected.loc[0, "low"] == 90.0
    assert corrected.loc[0, "close"] == 96.0
    assert corrected.loc[0, "volume"] == 123.0
    assert corrected.loc[0, "regular_market_value"] == 456.0
    assert corrected.loc[0, "price_provenance"] == "YAHOO_RAW"
    assert non_hlc_parity(panel.assign(date=pd.to_datetime(panel["date"])), corrected)["non_hlc_equal"] is True
