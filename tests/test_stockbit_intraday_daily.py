from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

import idx_trade.stockbit_intraday_daily as daily


SESSION = date(2026, 8, 12)


def _universe() -> pd.DataFrame:
    return pd.DataFrame({"ticker": ["BBCA", "BBRI", "ZERO"], "listed_from": ["2000-01-01"] * 3})


def _summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBCA", "ZERO"],
            "session_date": [SESSION.isoformat(), SESSION.isoformat()],
            "volume": [100.0, 0.0],
            "value": [1000.0, 0.0],
            "frequency": [5.0, 0.0],
            "raw_close": [9000.0, 100.0],
            "raw_high": [9100.0, 100.0],
            "raw_low": [8900.0, 100.0],
        }
    )


def _payload() -> dict:
    rows = []
    for ticker, volume, value, frequency in (("BBCA", 100, 1000, 5), ("ZERO", 0, 0, 0)):
        rows.append(
            {
                "StockCode": ticker,
                "Date": SESSION.isoformat(),
                "Volume": volume,
                "Value": value,
                "Frequency": frequency,
                "Close": 100,
                "High": 100,
                "Low": 100,
            }
        )
    return {"data": {"data": rows, "recordsTotal": len(rows)}}


def _metrics(fn: int = 0, *, eligible: bool = True) -> daily.ShadowMetrics:
    return daily.ShadowMetrics(
        false_negative=fn,
        false_positive=0,
        actual_success=2,
        actual_non_success=1,
        unexpected_statuses=(),
        non_404_request_errors=(),
        certification_eligible=eligible,
    )


def test_gate_missing_summary_is_conservative_fetch():
    decisions = daily._build_gate_decisions(_universe(), _summary())
    by_ticker = decisions.set_index("ticker")
    assert by_ticker.loc["BBCA", "gate_decision"] == "FETCH_TRADED"
    assert by_ticker.loc["ZERO", "gate_decision"] == "SKIP_NO_ACTIVITY"
    assert by_ticker.loc["BBRI", "gate_decision"] == "FETCH_MISSING_SUMMARY"
    assert bool(by_ticker.loc["BBRI", "would_fetch_stockbit"])


def test_three_zero_fn_shadow_sessions_promote_to_enforce():
    policy = daily._policy_default()
    for offset in range(3):
        policy = daily.update_policy_after_session(
            policy,
            run_mode="SHADOW",
            expected_date=date(2026, 8, 12 + offset),
            complete=True,
            metrics=_metrics(),
            shadow_sessions_required=3,
            recheck_every=10,
            manifest_sha256=f"m{offset}",
        )
    assert policy["mode"] == "ENFORCE"
    assert policy["consecutive_zero_fn_shadow_sessions"] == 3


def test_false_negative_resets_shadow_and_recheck_reverts():
    policy = daily._policy_default()
    policy["mode"] = "ENFORCE"
    policy["enforced_sessions_since_recheck"] = 10
    assert daily._run_mode(policy, recheck_every=10) == "SHADOW_RECHECK"
    updated = daily.update_policy_after_session(
        policy,
        run_mode="SHADOW_RECHECK",
        expected_date=SESSION,
        complete=True,
        metrics=_metrics(1),
        shadow_sessions_required=3,
        recheck_every=10,
        manifest_sha256="m",
    )
    assert updated["mode"] == "SHADOW"
    assert updated["consecutive_zero_fn_shadow_sessions"] == 0
    assert updated["enforced_sessions_since_recheck"] == 0


def test_enforce_skip_writes_only_confirmed_zero_activity(tmp_path):
    decisions = daily._build_gate_decisions(_universe(), _summary())
    written = daily.apply_gate_skips(tmp_path, decisions, expected_date=SESSION)
    assert written == 1
    assert daily._read_status(daily._status_path(tmp_path, "ZERO"))["status"] == daily.TERMINAL_GATE_SKIP
    assert daily._read_status(daily._status_path(tmp_path, "BBCA")) is None
    assert daily._read_status(daily._status_path(tmp_path, "BBRI")) is None


def test_shadow_metrics_detects_gate_false_negative():
    decisions = daily._build_gate_decisions(_universe(), _summary())
    statuses = pd.DataFrame(
        {
            "ticker": ["BBCA", "BBRI", "ZERO"],
            "status": ["SUCCESS", "REQUEST_ERROR", "SUCCESS"],
            "errors": ["", "HTTP_404", ""],
        }
    )
    metrics = daily.shadow_metrics(decisions, statuses, complete=True)
    assert metrics.false_negative == 1
    assert metrics.certification_eligible


def test_gate_network_evidence_is_persisted_before_parser_failure(tmp_path, monkeypatch):
    calls = {"count": 0}

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        return _payload(), {"remaining_month": "20000"}

    monkeypatch.setattr(daily, "_request_summary", fake_request)
    monkeypatch.setattr(daily, "parse_stock_summary_payload", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("schema")))

    with pytest.raises(ValueError, match="schema"):
        daily.prepare_traded_gate(
            tmp_path,
            _universe(),
            expected_date=SESSION,
            universe_sha="universe-hash",
            api_key="secret",
            session=object(),
        )
    paths = daily._gate_paths(tmp_path)
    assert calls["count"] == 1
    assert paths["raw"].exists()
    assert paths["headers"].exists()


def test_gate_resume_reuses_raw_without_second_network_call(tmp_path, monkeypatch):
    calls = {"count": 0}

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        return _payload(), {"remaining_month": "20000"}

    monkeypatch.setattr(daily, "_request_summary", fake_request)
    first = daily.prepare_traded_gate(
        tmp_path,
        _universe().iloc[[0, 2]].reset_index(drop=True),
        expected_date=SESSION,
        universe_sha="universe-hash",
        api_key="secret",
        session=object(),
    )
    second = daily.prepare_traded_gate(
        tmp_path,
        _universe().iloc[[0, 2]].reset_index(drop=True),
        expected_date=SESSION,
        universe_sha="universe-hash",
        api_key="secret",
        session=object(),
    )
    assert first.summary_call_made
    assert not second.summary_call_made
    assert calls["count"] == 1
    assert len(second.decisions) == 2


def test_ineligible_shadow_session_does_not_advance_counter():
    policy = daily._policy_default()
    updated = daily.update_policy_after_session(
        policy,
        run_mode="SHADOW",
        expected_date=SESSION,
        complete=True,
        metrics=_metrics(0, eligible=False),
        shadow_sessions_required=3,
        recheck_every=10,
        manifest_sha256="m",
    )
    assert updated["mode"] == "SHADOW"
    assert updated["consecutive_zero_fn_shadow_sessions"] == 0
