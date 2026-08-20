from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.v4_x_clean_data_consolidation import (
    FAIL_CLOSED_SOURCE,
    HLC_SOURCE,
    consolidate_stage_a,
)


def _parent() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "CCC"],
            "date": pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-02", "2026-01-02"]),
            "open": [100.0, 110.0, 200.0, 300.0],
            "high": [105.0, 115.0, 205.0, 305.0],
            "low": [95.0, 105.0, 195.0, 295.0],
            "close": [102.0, 112.0, 202.0, 302.0],
            "volume": [1000.0, 1100.0, 2000.0, 3000.0],
            "regular_market_value": [102000.0, 123200.0, 404000.0, 906000.0],
            "price_provenance": ["YAHOO_RAW", "YAHOO_RAW", "IDX", "IDX"],
            "other": [1, 2, 3, 4],
        }
    )


def _hlc() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": ["2026-01-02", "2026-01-02"],
            "remediated_high": [52.5, 102.5],
            "remediated_low": [47.5, 97.5],
            "remediated_close": [51.0, 101.0],
            "remediation_policy": [
                "STABLE_SCALE_YAHOO_RAW_KSEI_FACTOR_PRE_RECORD_V1",
                "STABLE_SCALE_YAHOO_RAW_KSEI_FACTOR_PRE_RECORD_V1",
            ],
        }
    )


def _open() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": ["2026-01-02"],
            "remediated_open": [50.0],
            "open_remediation_source": ["IDX_OFFICIAL_OPENPRICE"],
            "open_remediation_policy": ["IDX_OPENPRICE_PRIMARY_CA_FACTOR_FALLBACK_FAIL_CLOSED_V1"],
        }
    )


def _fail() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBB"],
            "date": ["2026-01-02"],
            "open_remediation_source": [FAIL_CLOSED_SOURCE],
            "open_remediation_policy": ["IDX_OPENPRICE_PRIMARY_CA_FACTOR_FALLBACK_FAIL_CLOSED_V1"],
        }
    )


def test_stage_a_applies_only_accepted_fields_and_fail_closes_open() -> None:
    parent = _parent()
    original = parent.copy(deep=True)
    result = consolidate_stage_a(parent, _hlc(), _open(), _fail())

    # Caller-owned parent is immutable.
    pd.testing.assert_frame_equal(parent, original)

    clean = result.panel
    aaa = clean[(clean.ticker == "AAA") & (clean.date == pd.Timestamp("2026-01-02"))].iloc[0]
    bbb = clean[(clean.ticker == "BBB") & (clean.date == pd.Timestamp("2026-01-02"))].iloc[0]
    untouched = clean[(clean.ticker == "AAA") & (clean.date == pd.Timestamp("2026-01-05"))].iloc[0]

    assert (aaa.high, aaa.low, aaa.close, aaa.open) == (52.5, 47.5, 51.0, 50.0)
    assert (bbb.high, bbb.low, bbb.close) == (102.5, 97.5, 101.0)
    assert np.isnan(bbb.open)
    assert (untouched.high, untouched.low, untouched.close, untouched.open) == (115.0, 105.0, 112.0, 110.0)

    pd.testing.assert_series_equal(clean["volume"], original["volume"])
    pd.testing.assert_series_equal(clean["regular_market_value"], original["regular_market_value"])
    pd.testing.assert_series_equal(clean["other"], original["other"])
    assert result.summary["universe_repair_performed"] is False


def test_provenance_and_small_correction_ledger_are_explicit() -> None:
    result = consolidate_stage_a(_parent(), _hlc(), _open(), _fail())
    prov = result.provenance
    assert len(prov) == 4

    aaa = prov[(prov.ticker == "AAA") & (prov.date == pd.Timestamp("2026-01-02"))].iloc[0]
    bbb = prov[(prov.ticker == "BBB") & (prov.date == pd.Timestamp("2026-01-02"))].iloc[0]
    ccc = prov[prov.ticker == "CCC"].iloc[0]

    assert aaa.high_source == HLC_SOURCE
    assert aaa.open_source == "IDX_OFFICIAL_OPENPRICE"
    assert bool(aaa.hlc_repaired) and bool(aaa.open_repaired)
    assert bbb.open_source == FAIL_CLOSED_SOURCE
    assert bool(bbb.open_fail_closed_candidate)
    assert ccc.high_source == "PARENT:IDX"
    assert ccc.open_source == "PARENT_UNCHANGED_OPEN_PROVENANCE_UNSPECIFIED"

    ledger = result.correction_ledger
    assert len(ledger) == 2
    assert set(ledger["ticker"]) == {"AAA", "BBB"}
    assert int(ledger["open_fail_closed"].sum()) == 1


def test_open_candidate_partition_must_match_hlc_candidate_identity() -> None:
    bad_fail = _fail().copy()
    bad_fail.loc[0, "ticker"] = "CCC"
    with pytest.raises(ValueError, match="candidate identities disagree"):
        consolidate_stage_a(_parent(), _hlc(), _open(), bad_fail)


def test_duplicate_or_unknown_overlay_identity_fails_closed() -> None:
    duplicate = pd.concat([_hlc(), _hlc().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        consolidate_stage_a(_parent(), duplicate, _open(), _fail())

    unknown = _hlc().copy()
    unknown.loc[0, "ticker"] = "ZZZ"
    with pytest.raises(ValueError, match="absent from frozen parent"):
        consolidate_stage_a(_parent(), unknown, _open(), _fail())


def test_open_outside_post_hlc_envelope_is_rejected() -> None:
    bad = _open().copy()
    bad.loc[0, "remediated_open"] = 999.0
    with pytest.raises(ValueError, match="outside post-HLC envelope"):
        consolidate_stage_a(_parent(), _hlc(), bad, _fail())


def test_invalid_hlc_envelope_is_rejected() -> None:
    bad = _hlc().copy()
    bad.loc[0, "remediated_low"] = 60.0
    with pytest.raises(ValueError, match="low <= close <= high"):
        consolidate_stage_a(_parent(), bad, _open(), _fail())


def test_unexpected_open_source_and_fail_closed_source_are_rejected() -> None:
    bad_open = _open().copy()
    bad_open.loc[0, "open_remediation_source"] = "SYNTHETIC"
    with pytest.raises(ValueError, match="unexpected admitted Open sources"):
        consolidate_stage_a(_parent(), _hlc(), bad_open, _fail())

    bad_fail = _fail().copy()
    bad_fail.loc[0, "open_remediation_source"] = "PARENT"
    with pytest.raises(ValueError, match="fail-closed Open source changed"):
        consolidate_stage_a(_parent(), _hlc(), _open(), bad_fail)


def test_expected_population_contract_is_enforced() -> None:
    expected = {
        "parent_rows": 4,
        "parent_tickers": 3,
        "hlc_overlay_rows": 2,
        "hlc_overlay_tickers": 2,
        "open_overlay_rows": 1,
        "open_fail_closed_rows": 1,
        "open_official_primary_rows": 1,
        "open_factor_fallback_rows": 0,
    }
    result = consolidate_stage_a(_parent(), _hlc(), _open(), _fail(), expected=expected)
    assert result.summary["parent_rows"] == 4

    expected["open_overlay_rows"] = 2
    with pytest.raises(ValueError, match="expected population changed"):
        consolidate_stage_a(_parent(), _hlc(), _open(), _fail(), expected=expected)
