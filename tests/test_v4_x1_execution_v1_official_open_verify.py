import hashlib
import json

import pandas as pd
import pytest

from idx_trade.official_open_evidence_v1 import (
    DIRECT_TRANSPORT,
    TRANSPORT_POLICY,
    UPSTREAM_PATH,
    ZAPI_RAW_TRANSPORT,
    certify_official_open_raw_response,
)
from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_execution_v1_verify import verify_open_execution_inputs


def _raw(*, zero_open=False, zapi=False):
    rows = [
        {
            "StockCode": "AADI",
            "Date": "2026-06-12T00:00:00",
            "OpenPrice": 8100,
            "FirstTrade": 8075,
        },
        {
            "StockCode": "BBCA",
            "Date": "2026-06-12T00:00:00",
            "OpenPrice": 0 if zero_open else 6000,
            "FirstTrade": 5975,
        },
        {
            "StockCode": "BBRI",
            "Date": "2026-06-12T00:00:00",
            "OpenPrice": 2880,
            "FirstTrade": 2890,
        },
    ]
    payload = {
        "data": rows,
        "recordsTotal": len(rows),
        "recordsFiltered": len(rows),
    }
    if zapi:
        payload.update(provider="idx", path=UPSTREAM_PATH)
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _manifest(tmp_path, *, zero_open=False, transport=DIRECT_TRANSPORT):
    return certify_official_open_raw_response(
        _raw(zero_open=zero_open, zapi=transport == ZAPI_RAW_TRANSPORT),
        session_date="2026-06-12",
        output_dir=tmp_path / "official_open" / "2026-06-12",
        transport=transport,
        transport_metadata={"http_status": 200},
    )


def test_certified_idx_openprice_is_admitted_with_full_lineage(tmp_path):
    manifest = _manifest(tmp_path)
    verified = verify_open_execution_inputs(
        manifest_path=manifest,
        execution_session_date="2026-06-12",
    )
    assert verified.raw_open_prices == {"AADI": 8100.0, "BBCA": 6000.0, "BBRI": 2880.0}
    assert verified.authority == "IDX"
    assert verified.upstream_path == UPSTREAM_PATH
    assert verified.field_semantics == "IDX_OFFICIAL_OPENPRICE"
    assert verified.fallback_policy == "NONE"
    assert verified.transport == DIRECT_TRANSPORT
    assert verified.transport_policy == TRANSPORT_POLICY
    assert verified.raw_source_sha256 == hashlib.sha256(verified.raw_source_path.read_bytes()).hexdigest()
    assert verified.manifest_sha256 == hashlib.sha256(manifest.read_bytes()).hexdigest()


def test_certified_zapi_raw_idx_passthrough_is_admitted_with_exact_transport_lineage(tmp_path):
    manifest = _manifest(tmp_path, transport=ZAPI_RAW_TRANSPORT)
    verified = verify_open_execution_inputs(
        manifest_path=manifest,
        execution_session_date="2026-06-12",
    )
    assert verified.raw_open_prices == {"AADI": 8100.0, "BBCA": 6000.0, "BBRI": 2880.0}
    assert verified.authority == "IDX"
    assert verified.upstream_path == UPSTREAM_PATH
    assert verified.transport == ZAPI_RAW_TRANSPORT
    assert verified.transport_policy == TRANSPORT_POLICY


def test_zero_openprice_with_positive_firsttrade_remains_unavailable(tmp_path):
    manifest = _manifest(tmp_path, zero_open=True)
    verified = verify_open_execution_inputs(
        manifest_path=manifest,
        execution_session_date="2026-06-12",
    )
    assert "BBCA" not in verified.raw_open_prices
    assert "BBCA" not in verified.available_tickers
    assert verified.raw_open_prices["AADI"] == 8100.0


def test_wrong_execution_date_is_rejected(tmp_path):
    manifest = _manifest(tmp_path)
    with pytest.raises(DecisionV1Error, match="OPEN_MANIFEST_DATE_MISMATCH"):
        verify_open_execution_inputs(
            manifest_path=manifest,
            execution_session_date="2026-06-15",
        )


def test_raw_bytes_tamper_is_rejected(tmp_path):
    manifest = _manifest(tmp_path)
    payload = json.loads(manifest.read_text())
    raw_path = manifest.parent / payload["raw_artifact_path"]
    raw_path.write_bytes(raw_path.read_bytes() + b"\n")
    with pytest.raises(DecisionV1Error, match="OPEN_RAW_SHA_MISMATCH"):
        verify_open_execution_inputs(
            manifest_path=manifest,
            execution_session_date="2026-06-12",
        )


def test_normalized_bytes_tamper_is_rejected(tmp_path):
    manifest = _manifest(tmp_path)
    payload = json.loads(manifest.read_text())
    normalized = manifest.parent / payload["normalized_artifact_path"]
    frame = pd.read_parquet(normalized)
    frame.loc[frame["ticker"] == "AADI", "open_price"] = 9999
    frame.to_parquet(normalized, index=False)
    with pytest.raises(DecisionV1Error, match="OPEN_NORMALIZED_SHA_MISMATCH"):
        verify_open_execution_inputs(
            manifest_path=manifest,
            execution_session_date="2026-06-12",
        )


def test_manifest_authority_tamper_is_rejected(tmp_path):
    manifest = _manifest(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["authority"] = "STOCKBIT"
    manifest.write_text(json.dumps(payload, sort_keys=True))
    with pytest.raises(DecisionV1Error, match="MANIFEST_CONTRACT_CHANGED:authority"):
        verify_open_execution_inputs(
            manifest_path=manifest,
            execution_session_date="2026-06-12",
        )


def test_manifest_transport_outside_admitted_chain_is_rejected(tmp_path):
    manifest = _manifest(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["transport"] = "UNVERIFIED_PROXY"
    manifest.write_text(json.dumps(payload, sort_keys=True))
    with pytest.raises(DecisionV1Error, match="MANIFEST_CONTRACT_CHANGED:transport"):
        verify_open_execution_inputs(
            manifest_path=manifest,
            execution_session_date="2026-06-12",
        )


def test_zapi_transport_requires_raw_provider_and_path_witness(tmp_path):
    manifest = _manifest(tmp_path, transport=ZAPI_RAW_TRANSPORT)
    payload = json.loads(manifest.read_text())
    raw_path = manifest.parent / payload["raw_artifact_path"]
    raw = json.loads(raw_path.read_text())
    raw["provider"] = "other"
    raw_path.write_text(json.dumps(raw, sort_keys=True))
    payload["raw_artifact_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(payload, sort_keys=True))
    with pytest.raises(DecisionV1Error, match="ZAPI_RAW_PROVIDER_MISMATCH"):
        verify_open_execution_inputs(
            manifest_path=manifest,
            execution_session_date="2026-06-12",
        )


def test_firsttrade_substitution_is_rejected_even_if_forged_parquet_sha_is_updated(tmp_path):
    manifest = _manifest(tmp_path, zero_open=True)
    payload = json.loads(manifest.read_text())
    normalized = manifest.parent / payload["normalized_artifact_path"]
    frame = pd.read_parquet(normalized)
    row = frame["ticker"] == "BBCA"
    assert frame.loc[row, "open_price"].iloc[0] == 0
    assert frame.loc[row, "first_trade"].iloc[0] == 5975
    frame.loc[row, "open_price"] = frame.loc[row, "first_trade"]
    frame.to_parquet(normalized, index=False)
    payload["normalized_artifact_sha256"] = hashlib.sha256(normalized.read_bytes()).hexdigest()
    payload["positive_openprice_count"] = 3
    payload["unavailable_openprice_count"] = 0
    manifest.write_text(json.dumps(payload, sort_keys=True))

    with pytest.raises(DecisionV1Error, match="NORMALIZED_OPENPRICE_MISMATCH"):
        verify_open_execution_inputs(
            manifest_path=manifest,
            execution_session_date="2026-06-12",
        )


def test_duplicate_raw_key_cannot_be_certified(tmp_path):
    rows = json.loads(_raw().decode())["data"]
    rows.append(dict(rows[0]))
    raw = json.dumps(
        {"data": rows, "recordsTotal": len(rows), "recordsFiltered": len(rows)}
    ).encode()
    from idx_trade.official_open_evidence_v1 import OfficialOpenEvidenceError

    with pytest.raises(OfficialOpenEvidenceError, match="DUPLICATE_KEY"):
        certify_official_open_raw_response(
            raw,
            session_date="2026-06-12",
            output_dir=tmp_path / "duplicate",
        )
