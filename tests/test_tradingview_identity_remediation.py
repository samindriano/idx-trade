import json

import pandas as pd

from idx_trade.tradingview_identity_remediation import (
    EXPECTED_CONTRACT,
    _classify_remediation,
    _raw_response_shape,
    _request_once,
)


class FakeResponse:
    def __init__(self, payload=None, status_code=200, headers=None, text=""):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers, timeout))
        return self.responses.pop(0)


def test_smb_retry_keeps_frozen_contract_and_has_no_internal_retry():
    session = FakeSession([FakeResponse({"content": {"symbol": "IDX:SMBR", "exchange": "IDX", "market": "indonesia", "candles": []}})])
    payload, meta = _request_once(session, "SMBR", "secret")
    assert payload["content"]["symbol"] == "IDX:SMBR"
    assert session.calls[0][1] == {"symbol": "IDX:SMBR", "market": "indonesia", "resolution": "1D", "count": 1000}
    assert meta["attempts"] == 1
    assert meta["retries"] == 0
    assert EXPECTED_CONTRACT["count"] == 1000


def test_http_520_is_one_request_error_not_a_symbol_guess():
    session = FakeSession([FakeResponse(status_code=520, headers={"Retry-After": "60"})])
    payload, meta = _request_once(session, "SMBR", "secret")
    assert payload is None
    assert meta["errors"] == ["HTTP_520"]
    assert len(session.calls) == 1


def test_raw_shape_reports_chart_identity_and_candle_count():
    shape = _raw_response_shape({"data": {"symbol": "IDX:SMBR", "exchange": "IDX", "market": "indonesia", "candles": [{"date": "2023-03-14"}]}, "project": "finance:tradingview:chart", "timestamp": "x"})
    assert shape["top_level_keys"] == ["data", "project", "timestamp"]
    assert shape["content_keys"] == ["candles", "exchange", "market", "symbol"]
    assert shape["candle_count"] == 1


def test_classification_requires_exact_hlc_and_valid_open():
    audit = pd.DataFrame(
        [
            {"sample_id": "x", "ticker": "SMBR", "date": pd.Timestamp("2023-03-14"), "admission_status": "ADMISSIBLE_OPEN_EVIDENCE", "diagnostic": "FROZEN_CONTRACT_PASS", "hlc_exact": True},
            {"sample_id": "y", "ticker": "SMBR", "date": pd.Timestamp("2023-03-15"), "admission_status": "REJECTED", "diagnostic": "HLC_MISMATCH_HIGH", "hlc_exact": False},
        ]
    )
    status = pd.DataFrame([{"ticker": "SMBR", "status": "SUCCESS", "min_date": "2023-01-01", "max_date": "2023-12-31"}])
    classified = _classify_remediation(audit, status)
    assert classified["remediation_class"].tolist() == ["TV_RECOVERY_CANDIDATE", "TV_HLC_DISAGREEMENT"]


def test_secret_is_not_in_raw_record_serialization():
    from idx_trade.tradingview_identity_remediation import redact_secrets

    secret = "zpi_secret_value"
    value = redact_secrets({"api_key": secret, "nested": [secret]}, (secret,))
    assert secret not in json.dumps(value)
