from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from idx_trade.providers.idx_ownership import (
    _parse_optional_bool,
    _parse_percentage,
    _parse_shares,
    parse_gt1_ownership_csv,
    parse_idx_company_ownership_payload,
)


def test_company_profile_named_holders_no_float_inference() -> None:
    payload = {
        "Profiles": [{"KodeEmiten": "DCII"}],
        "PemegangSaham": [
            {
                "Nama": "PT A",
                "Jumlah": "3.200.142.830",
                "Persentase": "41,10",
                "Pengendali": True,
                "Kategori": "Pengendali",
            },
            {
                "Nama": "BUDI",
                "Jumlah": 1_000_000,
                "Persentase": 1.25,
                "Pengendali": False,
                "Kategori": "Lainnya",
            },
        ],
    }
    raw = json.dumps(payload).encode()
    frame, meta = parse_idx_company_ownership_payload(
        payload,
        ticker="DCII",
        source_ref="https://idx",
        raw_bytes=raw,
        observed_available_at_utc="2026-08-15T00:00:00+00:00",
    )

    assert len(frame) == 2
    assert frame.iloc[0]["holding_shares"] == 3_200_142_830
    assert frame.iloc[0]["holding_pct"] == 41.10
    assert bool(frame.iloc[0]["is_controller"]) is True
    assert meta.reported_free_float_pct is None
    assert meta.raw_sha256 == hashlib.sha256(raw).hexdigest()
    assert "effective_free_float" not in frame.columns


def test_company_profile_missing_holders_fails_but_empty_is_explicitly_valid() -> None:
    with pytest.raises(ValueError, match="missing PemegangSaham"):
        parse_idx_company_ownership_payload({}, ticker="BBCA", source_ref="x")

    frame, meta = parse_idx_company_ownership_payload(
        {"PemegangSaham": []}, ticker="BBCA", source_ref="x"
    )
    assert frame.empty
    assert meta.rows == 0


def _gt1_csv(classification_column: str = "INVESTOR_TYPE") -> bytes:
    return (
        f"DATE,SHARE_CODE,ISSUER_NAME,INVESTOR_NAME,{classification_column},LOCAL_FOREIGN,"
        "NATIONALITY,DOMICILE,HOLDINGS_SCRIPLESS,HOLDINGS_SCRIP,"
        "TOTAL_HOLDING_SHARES,PERCENTAGE\n"
        "27-Feb-2026,AADI,AADI Tbk,ADARO STRATEGIC INVESTMENTS,CP,L,,INDONESIA,"
        "3.200.142.830,0,3.200.142.830,\"41,10\"\n"
    ).encode()


def test_gt1_snapshot_uses_embedded_date_and_indonesian_numbers() -> None:
    frame, meta = parse_gt1_ownership_csv(
        _gt1_csv(),
        source_ref="mirror://1%ownership-2025-03-04.csv",
    )

    assert meta.snapshot_date == "2026-02-27"
    assert frame.iloc[0]["snapshot_date"] == pd.Timestamp("2026-02-27")
    assert frame.iloc[0]["holding_shares"] == 3_200_142_830
    assert frame.iloc[0]["holding_pct"] == 41.10
    assert frame.iloc[0]["holdings_scripless"] == 3_200_142_830
    assert frame.iloc[0]["investor_type"] == "CP"
    assert meta.reported_free_float_pct is None


def test_gt1_snapshot_accepts_official_investor_classification_alias() -> None:
    frame, meta = parse_gt1_ownership_csv(
        _gt1_csv("INVESTOR_CLASSIFICATION"),
        source_ref="idx-announcement://ownership-gt1",
    )
    assert len(frame) == 1
    assert frame.iloc[0]["investor_type"] == "CP"
    assert meta.snapshot_date == "2026-02-27"


def test_gt1_snapshot_reconciles_scrip_and_rejects_mixed_dates() -> None:
    header = (
        "DATE,SHARE_CODE,ISSUER_NAME,INVESTOR_NAME,INVESTOR_TYPE,LOCAL_FOREIGN,"
        "NATIONALITY,DOMICILE,HOLDINGS_SCRIPLESS,HOLDINGS_SCRIP,"
        "TOTAL_HOLDING_SHARES,PERCENTAGE\n"
    )
    bad = (
        header
        + "27-Feb-2026,AADI,A,Holder,CP,L,,ID,900,100,999,\"1,10\"\n"
    ).encode()
    with pytest.raises(ValueError, match="reconciliation failed"):
        parse_gt1_ownership_csv(bad, source_ref="x")

    mixed = (
        header
        + "27-Feb-2026,AADI,A,H1,CP,L,,ID,900,100,1000,\"1,10\"\n"
        + "28-Feb-2026,AADI,A,H2,CP,L,,ID,800,200,1000,\"1,10\"\n"
    ).encode()
    with pytest.raises(ValueError, match="exactly one snapshot DATE"):
        parse_gt1_ownership_csv(mixed, source_ref="x")


def test_invalid_percent_and_fractional_shares_fail_closed() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        _parse_percentage("101,0", field="pct")
    with pytest.raises(ValueError, match="fractional"):
        _parse_shares(1.5, field="shares")


def test_optional_controller_is_strict() -> None:
    assert _parse_optional_bool("ya", field="x") is True
    assert _parse_optional_bool("tidak", field="x") is False
    with pytest.raises(ValueError, match="unrecognized"):
        _parse_optional_bool("mungkin", field="x")
