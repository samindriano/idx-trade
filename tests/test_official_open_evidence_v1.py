import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.official_open_evidence_v1 import (
    AUTHORITY,
    FALLBACK_POLICY,
    FIELD_SEMANTICS,
    SCHEMA_VERSION,
    TRANSPORT,
    UPSTREAM_PATH,
    OfficialOpenEvidenceError,
    certify_official_open_raw_response,
    fetch_direct_idx_stock_summary,
    normalize_idx_stock_summary_payload,
)


def _payload(rows):
    return json.dumps(
        {
            "data": rows,
            "recordsTotal": len(rows),
            "recordsFiltered": len(rows),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _rows():
    return [
        {
            "StockCode": "AADI",
            "Date": "2026-06-12T00:00:00",
            "OpenPrice": 8100,
            "FirstTrade": 8075,
        },
        {
            "StockCode": "BBCA",
            "Date": "2026-06-12T00:00:00",
            "OpenPrice": 6000,
            "FirstTrade": 5975,
        },
        {
            "StockCode": "ZERO",
            "Date": "2026-06-12T00:00:00",
            "OpenPrice": 0,
            "FirstTrade": 1000,
        },
    ]


def test_normalization_preserves_openprice_and_firsttrade_as_distinct_fields():
    frame, counts = normalize_idx_stock_summary_payload(
        _payload(_rows()), expected_session_date="2026-06-12"
    )
    aadi = frame.set_index("ticker").loc["AADI"]
    zero = frame.set_index("ticker").loc["ZERO"]
    assert aadi.open_price == 8100
    assert aadi.first_trade == 8075
    assert zero.open_price == 0
    assert zero.first_trade == 1000
    assert counts == {
        "records_total": 3,
        "records_filtered": 3,
        "row_count": 3,
        "unique_ticker_count": 3,
    }


def test_normalization_requires_complete_unfiltered_session():
    raw = json.dumps(
        {
            "data": _rows()[:2],
            "recordsTotal": 3,
            "recordsFiltered": 2,
        }
    ).encode()
    with pytest.raises(OfficialOpenEvidenceError, match="FULL_SESSION_COUNT_MISMATCH"):
        normalize_idx_stock_summary_payload(raw, expected_session_date="2026-06-12")


def test_certification_writes_manifest_last_with_hash_bound_source(tmp_path):
    raw = _payload(_rows())
    manifest_path = certify_official_open_raw_response(
        raw,
        session_date="2026-06-12",
        output_dir=tmp_path / "official_open" / "2026-06-12",
        transport_metadata={"http_status": 200},
    )
    payload = json.loads(manifest_path.read_text())
    raw_path = manifest_path.parent / payload["raw_artifact_path"]
    normalized_path = manifest_path.parent / payload["normalized_artifact_path"]

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["authority"] == AUTHORITY
    assert payload["upstream_path"] == UPSTREAM_PATH
    assert payload["transport"] == TRANSPORT
    assert payload["field_semantics"] == FIELD_SEMANTICS
    assert payload["fallback_policy"] == FALLBACK_POLICY
    assert payload["execution_grade"] is True
    assert payload["positive_openprice_count"] == 2
    assert payload["unavailable_openprice_count"] == 1
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == payload["raw_artifact_sha256"]
    assert hashlib.sha256(normalized_path.read_bytes()).hexdigest() == payload["normalized_artifact_sha256"]

    frame = pd.read_parquet(normalized_path).set_index("ticker")
    assert frame.loc["ZERO", "open_price"] == 0
    assert frame.loc["ZERO", "first_trade"] == 1000


def test_certification_refuses_overwrite(tmp_path):
    raw = _payload(_rows())
    output = tmp_path / "session"
    certify_official_open_raw_response(raw, session_date="2026-06-12", output_dir=output)
    with pytest.raises(OfficialOpenEvidenceError, match="ALREADY_EXISTS"):
        certify_official_open_raw_response(raw, session_date="2026-06-12", output_dir=output)


class _Response:
    status_code = 200
    content = _payload(_rows())


def test_direct_fetch_uses_full_session_request_without_ticker_filter():
    observed = {}

    def fake_get(url, *, params, headers, timeout):
        observed.update(url=url, params=params, headers=headers, timeout=timeout)
        return _Response()

    raw, meta = fetch_direct_idx_stock_summary(
        "2026-06-12", get=fake_get, timeout_seconds=7
    )
    assert raw == _Response.content
    assert observed["params"] == {"date": "20260612", "start": 0, "length": 9999}
    assert "code" not in observed["params"]
    assert meta["upstream_path"] == UPSTREAM_PATH
    assert meta["http_status"] == 200
