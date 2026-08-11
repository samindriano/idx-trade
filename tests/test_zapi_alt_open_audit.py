import pandas as pd

from idx_trade.zapi_alt_open_audit import (
    _investing_identity_candidates,
    _session_date,
    classify_provider,
    fetch_investing,
    fetch_tradingview,
)
from idx_trade.tier2_open_audit import classify_zapi_access_failure


class FakeResponse:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text
        self.headers = {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers, timeout))
        return self.responses.pop(0)


def test_session_date_uses_asia_jakarta_session_date():
    assert _session_date("2026-06-22T02:00:00.000Z") == pd.Timestamp("2026-06-22")


def test_investing_identity_requires_indonesian_listing():
    payload = {
        "content": {
            "quotes": [
                {"symbol": "BBCA", "pairId": 1, "exchange": "Jakarta", "country": "Indonesia"},
                {"symbol": "BBCA", "pairId": 2, "exchange": "OTC", "country": "USA"},
            ]
        }
    }
    result = _investing_identity_candidates(payload, "BBCA")
    assert [row["pairId"] for row in result] == [1]


def test_tradingview_fetch_parses_idx_daily_candle(monkeypatch):
    monkeypatch.setattr("idx_trade.zapi_alt_open_audit.time.sleep", lambda *_: None)
    session = FakeSession(
        [
            FakeResponse(
                {
                    "content": {
                        "symbol": "IDX:BBCA",
                        "exchange": "IDX",
                        "market": "indonesia",
                        "candles": [
                            {
                                "date": "2026-06-22T02:00:00.000Z",
                                "open": 6400,
                                "high": 6400,
                                "low": 6125,
                                "close": 6225,
                                "volume": 100,
                            }
                        ],
                    }
                }
            )
        ]
    )
    sample = pd.DataFrame({"ticker": ["BBCA"]})
    result = fetch_tradingview(sample, "secret", session=session)
    row = result["rows"].iloc[0]
    assert row["ticker"] == "BBCA"
    assert row["date"] == pd.Timestamp("2026-06-22")
    assert row["raw_open"] == 6400
    assert result["ticker_status"].iloc[0]["status"] == "SUCCESS"


def test_tradingview_symbol_404_is_provider_error_not_access_gate(monkeypatch):
    monkeypatch.setattr("idx_trade.zapi_alt_open_audit.time.sleep", lambda *_: None)
    session = FakeSession(
        [
            FakeResponse(
                {
                    "content": {
                        "symbol": "IDX:BBRI",
                        "exchange": "IDX",
                        "market": "indonesia",
                        "candles": [],
                    }
                }
            ),
            FakeResponse({}, status_code=404),
        ]
    )
    sample = pd.DataFrame({"ticker": ["FREN", "BBRI"]})
    result = fetch_tradingview(sample, "secret", session=session)
    assert classify_zapi_access_failure(404, "not found") == "REQUEST_ERROR"
    assert len(session.calls) == 2
    assert result["ticker_status"].iloc[0]["status"] == "NO_DATA"
    assert result["ticker_status"].iloc[1]["status"] == "REQUEST_ERROR"


def test_investing_fetch_uses_verified_pair_id(monkeypatch):
    monkeypatch.setattr("idx_trade.zapi_alt_open_audit.time.sleep", lambda *_: None)
    session = FakeSession(
        [
            FakeResponse(
                {
                    "content": {
                        "quotes": [
                            {
                                "symbol": "BBCA",
                                "pairId": 123,
                                "exchange": "Jakarta",
                                "country": "Indonesia",
                                "name": "Bank Central Asia",
                            }
                        ]
                    }
                }
            ),
            FakeResponse(
                {
                    "content": {
                        "pairId": 123,
                        "symbol": "BBCA",
                        "candles": [
                            {
                                "date": "2026-06-22T00:00:00.000Z",
                                "open": 6400,
                                "high": 6400,
                                "low": 6125,
                                "close": 6225,
                                "volume": 100,
                            }
                        ],
                    }
                }
            ),
        ]
    )
    sample = pd.DataFrame({"ticker": ["BBCA"]})
    result = fetch_investing(sample, "secret", session=session)
    assert result["identity"].iloc[0]["identity_status"] == "IDENTITY_VERIFIED"
    assert str(result["identity"].iloc[0]["pair_id"]) == "123"
    assert result["rows"].iloc[0]["raw_open"] == 6400
    assert session.calls[1][1]["pairId"] == 123
    assert session.calls[1][1]["pointscount"] == 1500


def test_classification_distinguishes_history_window_unavailable():
    sample = pd.DataFrame(
        {
            "sample_id": ["Z2-001"],
            "residual_problem_class": ["NO_PROVIDER_ROW"],
            "yahoo_raw_high": [None],
            "yahoo_raw_low": [None],
            "yahoo_raw_close": [None],
        }
    )
    audit = pd.DataFrame(
        {
            "sample_id": ["Z2-001"],
            "sample_role": ["RESIDUAL_PROVIDER_GAP"],
            "ticker": ["BBCA"],
            "date": [pd.Timestamp("2021-05-03")],
            "raw_open": [None],
            "raw_high": [None],
            "raw_low": [None],
            "raw_close": [None],
            "hlc_exact": [False],
            "known_open_exact": [None],
            "admission_status": ["REJECTED"],
            "diagnostic": ["NO_PROVIDER_ROW"],
        }
    )
    status = pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "status": ["SUCCESS"],
            "min_date": [pd.Timestamp("2022-08-01")],
            "max_date": [pd.Timestamp("2026-08-10")],
        }
    )
    result = classify_provider(sample, audit, status, "TV")
    assert result.loc[0, "provider_class"] == "TV_HISTORY_WINDOW_UNAVAILABLE"
