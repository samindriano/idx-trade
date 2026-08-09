import pandas as pd

from idx_trade.providers import yahoo
from idx_trade.tier2_open_audit import (
    audit_provider_rows,
    build_audit_candidates,
    redact_secrets,
    run_zapi_audit,
    run_yahoo_audit,
    select_audit_sample,
    sample_manifest_sha256,
)


def _fixture_candidates():
    rows = []
    for index in range(20):
        rows.append(
            {
                "ticker": "BBCA",
                "date": pd.Timestamp("2025-01-02") + pd.Timedelta(days=index),
                "open": 100.0,
                "high": 110.0,
                "low": 90.0,
                "close": 105.0,
            }
        )
    for index in range(20):
        rows.append(
            {
                "ticker": "MASA",
                "date": pd.Timestamp("2025-02-03") + pd.Timedelta(days=index),
                "open": None,
                "high": 110.0,
                "low": 90.0,
                "close": 105.0,
            }
        )
    for index in range(5):
        rows.append(
            {
                "ticker": "FREN",
                "date": pd.Timestamp("2025-03-03") + pd.Timedelta(days=index),
                "open": None,
                "high": 11.0,
                "low": 9.0,
                "close": 10.0,
            }
        )
    return pd.DataFrame(rows)


def _fixture_diagnostics(panel):
    missing = panel[panel["open"].isna()].copy()
    return pd.DataFrame(
        {
            "ticker": missing["ticker"],
            "date": missing["date"],
            "diagnostic": [
                "SECONDARY_OHLC_INVALID" if ticker == "MASA" else "SECONDARY_ROW_UNAVAILABLE"
                for ticker in missing["ticker"]
            ],
        }
    )


def test_sample_is_deterministic_and_preserves_strata():
    panel = _fixture_candidates()
    candidates = build_audit_candidates(panel, _fixture_diagnostics(panel))
    first = select_audit_sample(candidates, target_size=45)
    second = select_audit_sample(candidates, target_size=45)
    pd.testing.assert_frame_equal(first, second)
    assert sample_manifest_sha256(first) == sample_manifest_sha256(second)
    counts = first["sample_role"].value_counts().to_dict()
    assert counts["KNOWN_EXISTING_OPEN"] >= 20
    assert counts["MISSING_OPEN_WILDAN_ROW"] >= 20
    assert counts["MISSING_OPEN_WILDAN_NO_ROW"] >= 5


def _single_sample(role="MISSING_OPEN_WILDAN_ROW"):
    return pd.DataFrame(
        [
            {
                "sample_id": "T2-001",
                "sample_role": role,
                "ticker": "MASA",
                "date": pd.Timestamp("2025-01-02"),
                "panel_open": None if role != "KNOWN_EXISTING_OPEN" else 100.0,
                "panel_high": 110.0,
                "panel_low": 90.0,
                "panel_close": 105.0,
                "wildan_diagnostic": "SECONDARY_OHLC_INVALID",
                "edge_case_tags": "",
            }
        ]
    )


def _provider(**overrides):
    row = {
        "ticker": "MASA",
        "date": pd.Timestamp("2025-01-02"),
        "raw_open": 100.0,
        "raw_high": 110.0,
        "raw_low": 90.0,
        "raw_close": 105.0,
        "raw_volume": 1000.0,
        "source_ref": "provider://sample",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_existing_open_is_preserved_and_not_admitted_for_overwrite():
    sample = _single_sample("KNOWN_EXISTING_OPEN")
    audit, summary = audit_provider_rows(sample, _provider(), "TEST")
    assert audit.loc[0, "admission_status"] == "PRESERVED_EXISTING_OPEN"
    assert audit.loc[0, "diagnostic"] == "EXISTING_OPEN_PRESERVED"
    assert summary["admissible_missing_open_rows"] == 0


def test_hlc_exact_gate_rejects_mismatch():
    audit, _ = audit_provider_rows(_single_sample(), _provider(raw_high=111.0), "TEST")
    assert audit.loc[0, "diagnostic"] == "HLC_MISMATCH_HIGH"


def test_open_must_be_positive_and_in_range():
    negative, _ = audit_provider_rows(_single_sample(), _provider(raw_open=0), "TEST")
    outside, _ = audit_provider_rows(_single_sample(), _provider(raw_open=120), "TEST")
    assert negative.loc[0, "diagnostic"] == "CANDIDATE_OPEN_INVALID"
    assert outside.loc[0, "diagnostic"] == "CANDIDATE_OPEN_OUTSIDE_CERTIFIED_RANGE"


def test_zapi_missing_credential_is_blocked_not_data_failure():
    audit = run_zapi_audit(_single_sample(), api_key=None)
    assert audit["summary"]["access_status"] == "ZAPI_BLOCKED_CREDENTIAL_ABSENT"
    assert audit["summary"]["requests_made"] == 0
    assert audit["summary"]["rejection_breakdown"]["NO_PROVIDER_ROW"] == 1


def test_zapi_plan_failure_is_distinct_from_source_data_rejection():
    class Response:
        status_code = 403
        text = "upgrade required: minPlan=pro"

        def json(self):
            return {}

    class Session:
        def get(self, *args, **kwargs):
            assert kwargs["headers"]["x-api-key"] == "zpi_test_secret"
            return Response()

    result = run_zapi_audit(_single_sample(), api_key="zpi_test_secret", session=Session())
    assert result["summary"]["access_status"] == "PLAN_GATED"
    assert result["summary"]["plan_status"] == "PLAN_GATED"
    assert result["summary"]["rejection_breakdown"]["NO_PROVIDER_ROW"] == 1
    assert "zpi_test_secret" not in str(result["summary"])


def test_yahoo_raw_and_adjusted_fields_stay_separate(monkeypatch):
    calls = {}

    def fake_download(*args, **kwargs):
        calls.update(kwargs)
        index = pd.DatetimeIndex(["2025-01-02"])
        return pd.DataFrame(
            {
                "Open": [100.0],
                "High": [110.0],
                "Low": [90.0],
                "Close": [105.0],
                "Adj Close": [95.0],
                "Volume": [1000],
                "Dividends": [0.0],
                "Stock Splits": [0.0],
            },
            index=index,
        )

    monkeypatch.setattr(yahoo.yf, "download", fake_download)
    result = yahoo.download_daily(["MASA"], "2025-01-02", "2025-01-03", threads=False)["MASA"]
    assert calls["auto_adjust"] is False
    assert result.loc[0, "raw_open"] == 100.0
    assert result.loc[0, "vendor_adj_close"] == 95.0
    assert result.loc[0, "raw_open"] != result.loc[0, "vendor_adj_close"]


def test_yahoo_provider_log_is_reported_as_request_error(monkeypatch, capsys):
    def fake_download(tickers, start, end, threads):
        print("1 Failed download: ['MASA.JK']: YFTzMissingError")
        return {"MASA": pd.DataFrame()}

    monkeypatch.setattr("idx_trade.tier2_open_audit.download_daily", fake_download)
    result = run_yahoo_audit(_single_sample())
    assert result["summary"]["requests_made"] == 1
    assert "MASA:" in result["summary"]["request_errors"][0]
    assert "YFTzMissingError" in result["summary"]["request_errors"][0]
    assert capsys.readouterr().out == ""


def test_secret_redaction_is_recursive():
    value = {"error": "x-api-key: zpi_test_secret", "nested": ["Bearer zpi_test_secret"]}
    cleaned = redact_secrets(value, ("zpi_test_secret",))
    assert "zpi_test_secret" not in str(cleaned)
    assert "[REDACTED]" in str(cleaned)
