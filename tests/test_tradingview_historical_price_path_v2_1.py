from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from idx_trade.tradingview_price_path_v2_1 import (
    STATUS_AMBIGUOUS,
    STATUS_MAPPED,
    STATUS_OUTSIDE,
    atomic_write_bytes,
    active_only_model_safe_rows,
    build_expected_state_reconciliation,
    control_request_fixture,
    corporate_action_flags,
    depth_completion_status,
    freeze_immutable_json,
    official_stock_summary_hlcv_oracle,
    load_identity_intervals,
    map_identity_frame,
    official_session_neighborhood,
    pagination_step,
    raw_request_matches,
    serialize_v2_1_request,
    validate_structural_rows,
    yearly_fidelity_support,
    write_network_start_marker,
    write_streaming_artifact,
)


def _intervals() -> pd.DataFrame:
    return pd.DataFrame([
        {"security_id": "IDX:AAA:20200101", "ticker": "AAA", "listed_from": pd.Timestamp("2020-01-01"), "listed_to": pd.NaT},
        {"security_id": "IDX:OVERLAP:20200101", "ticker": "OVERLAP", "listed_from": pd.Timestamp("2020-01-01"), "listed_to": pd.Timestamp("2020-01-10")},
        {"security_id": "IDX:OVERLAP:20200105", "ticker": "OVERLAP", "listed_from": pd.Timestamp("2020-01-05"), "listed_to": pd.Timestamp("2020-01-20")},
    ])


def test_identity_mapping_is_exact_and_fail_closed() -> None:
    rows = pd.DataFrame([
        {"ticker": "AAA", "session_date": "2020-01-02", "security_id": "IDX:AAA:20200101"},
        {"ticker": "AAA", "session_date": "2019-12-31", "security_id": "IDX:AAA:20200101"},
        {"ticker": "OVERLAP", "session_date": "2020-01-06", "security_id": "IDX:OVERLAP:20200101"},
    ])
    mapped = map_identity_frame(rows, _intervals())
    assert mapped.iloc[0]["identity_status"] == STATUS_MAPPED
    assert mapped.iloc[1]["identity_status"] == STATUS_OUTSIDE
    assert mapped.iloc[2]["identity_status"] == STATUS_AMBIGUOUS


def test_provider_identity_must_match_pit_security_id() -> None:
    rows = pd.DataFrame([{"ticker": "AAA", "session_date": "2020-01-02", "security_id": "IDX:WRONG:20000101"}])
    mapped = map_identity_frame(rows, _intervals())
    assert mapped.iloc[0]["identity_status"] == STATUS_MAPPED
    assert mapped.iloc[0]["mapped_security_id"] != mapped.iloc[0]["security_id"]


def test_session_index_quarantine_uses_previous_and_next_official_sessions() -> None:
    sessions = pd.DataFrame({"date": pd.to_datetime(["2020-01-02", "2020-01-06", "2020-01-07"])})
    events = pd.DataFrame([{"ticker": "AAA", "effective_date": "2020-01-06"}])
    keys, detail = official_session_neighborhood(sessions, events)
    assert detail["unmapped_event_count"] == 0
    assert {("AAA", "2020-01-02"), ("AAA", "2020-01-06"), ("AAA", "2020-01-07")} <= keys
    rows = pd.DataFrame({"ticker": ["AAA", "AAA"], "session_date": ["2020-01-02", "2020-01-03"]})
    flags = corporate_action_flags(rows, events, sessions)
    assert flags.tolist() == [True, False]


def test_expected_state_preserves_no_trade_contradiction_and_unknown() -> None:
    expected = pd.DataFrame([
        {"ticker": "AAA", "session_date": "2020-01-02", "security_id": "IDX:AAA:20200101"},
        {"ticker": "AAA", "session_date": "2020-01-03", "security_id": "IDX:AAA:20200101"},
        {"ticker": "AAA", "session_date": "2020-01-06", "security_id": "IDX:AAA:20200101"},
    ])
    activity = pd.DataFrame([
        {"ticker": "AAA", "session_date": "2020-01-02", "activity_state": "ACTIVE"},
        {"ticker": "AAA", "session_date": "2020-01-03", "activity_state": "NO_TRADE"},
        {"ticker": "AAA", "session_date": "2020-01-06", "activity_state": "UNKNOWN"},
    ])
    bars = pd.DataFrame([{
        "ticker": "AAA", "session_date": "2020-01-02", "security_id": "IDX:AAA:20200101", "mapped_security_id": "IDX:AAA:20200101", "identity_status": STATUS_MAPPED, "session_admissible": True,
    }, {
        "ticker": "AAA", "session_date": "2020-01-03", "security_id": "IDX:AAA:20200101", "mapped_security_id": "IDX:AAA:20200101", "identity_status": STATUS_MAPPED, "session_admissible": True,
    }])
    result = build_expected_state_reconciliation(expected, activity, bars).set_index("session_date")
    assert result.loc["2020-01-02", "reconciliation_status"] == "COVERED_ACTIVE"
    assert result.loc["2020-01-03", "reconciliation_status"] == "NO_TRADE_WITH_PROVIDER_BARS_REQUIRES_REVIEW"
    assert result.loc["2020-01-06", "reconciliation_status"] == "UNKNOWN_FAIL_CLOSED"


def test_request_schema_rejects_numeric_timeframe_and_accepts_frozen_controls() -> None:
    valid = {"ticker": "BBCA", "symbol": "IDX:BBCA", "server": "prodata", "timeframe": "60", "session": "regular", "adjustment": "none", "initial_range": 10000, "fetch_more_steps": 0, "fetch_more_batch": 5, "timeout_ms": 25000, "to": 1785517199}
    assert serialize_v2_1_request(valid)["timeframe"] == "60"
    invalid = {**valid, "timeframe": 60}
    with pytest.raises(TypeError):
        serialize_v2_1_request(invalid)
    controls = control_request_fixture({"window": {"start": "2021-04-01", "end": "2026-07-31"}, "acquisition": {"initial_range": 500, "fetch_more_batch": 5000, "fetch_more_steps": 3, "timeout_ms": 25000}})
    assert [row["ticker"] for row in controls] == ["BBCA", "BBRI", "BMRI", "TLKM", "ASII"]
    assert all(row["initial_range"] == 500 and row["fetch_more_steps"] == 3 and row["fetch_more_batch"] == 5000 for row in controls)


def test_atomic_stream_artifact_hash_and_no_partial_on_failure(tmp_path: Path) -> None:
    path = tmp_path / "raw" / "payload.bin"
    result = write_streaming_artifact(path, [b"abc", b"123"])
    assert result["status"] == "COMPLETE"
    assert result["bytes"] == 6
    assert path.read_bytes() == b"abc123"
    assert not list(path.parent.glob("*.partial"))
    with pytest.raises(FileExistsError):
        atomic_write_bytes(path, b"new")
    broken = tmp_path / "raw" / "broken.bin"
    def chunks():
        yield b"prefix"
        raise RuntimeError("simulated interruption")
    with pytest.raises(RuntimeError):
        write_streaming_artifact(broken, chunks())
    assert not broken.exists()
    assert not list(broken.parent.glob("*.partial"))


def test_curated_identity_is_loaded_as_common_interval(tmp_path: Path) -> None:
    master = tmp_path / "master.csv"
    curated = tmp_path / "curated.csv"
    exclusions = tmp_path / "exclude.csv"
    pd.DataFrame([{"security_id": "IDX:AAA:20200101", "ticker": "AAA", "company_name": "A", "listed_from": "2020-01-01", "listed_to": "", "source": "IDX"}]).to_csv(master, index=False)
    pd.DataFrame([{"ticker": "FREN", "company_name": "F", "security_type": "Saham Biasa", "listed_from": "2006-11-29", "listed_to": "2025-04-16", "source": "curated"}]).to_csv(curated, index=False)
    pd.DataFrame([{"ticker": "CNTX"}]).to_csv(exclusions, index=False)
    result = load_identity_intervals(master, curated, exclusions)
    assert "FREN" in set(result["ticker"])
    assert "CNTX" not in set(result["ticker"])


def test_preregistration_is_immutable_and_runtime_marker_is_separate(tmp_path: Path) -> None:
    prereg = tmp_path / "preregistration.json"
    marker = tmp_path / "network_start_marker.json"
    first = freeze_immutable_json(prereg, {"schema": "v2.1", "gates": {"overall": 0.98}})
    assert freeze_immutable_json(prereg, {"schema": "v2.1", "gates": {"overall": 0.98}}) == first
    with pytest.raises(ValueError):
        freeze_immutable_json(prereg, {"schema": "v2.1", "gates": {"overall": 0.99}})
    written = write_network_start_marker(marker, prereg, 5)
    assert written["preregistration_sha256"] == first
    assert prereg.exists() and marker.exists() and prereg != marker


def test_raw_resume_requires_exact_contract_and_preregistration() -> None:
    expected = {"request_index": 1, "ticker": "BBCA", "symbol": "IDX:BBCA", "server": "prodata", "timeframe": "60", "session": "regular", "adjustment": "none", "to": 1785517199, "initial_range": 500, "fetch_more_batch": 5000, "fetch_more_steps": 3, "timeout_ms": 25000, "required_start": "2021-04-01", "adapter_commit": "abc"}
    raw = {**expected, "preregistration_sha256": "prereg"}
    assert raw_request_matches(raw, expected, "prereg")
    assert not raw_request_matches({**raw, "fetch_more_batch": 5}, expected, "prereg")
    assert not raw_request_matches(raw, expected, "other")


def test_depth_completion_and_pagination_use_boundary_not_fixed_bar_count() -> None:
    assert depth_completion_status(provider_data_status="AVAILABLE", earliest_session="2021-03-31", required_start="2021-04-01", prior_buffer_reached=True) == "REQUIRED_START_REACHED"
    assert depth_completion_status(provider_data_status="AVAILABLE", earliest_session="2022-01-01", required_start="2021-04-01", prior_buffer_reached=False, extension_reason="max_steps") == "INCOMPLETE_MAX_DEPTH"
    assert depth_completion_status(provider_data_status="TIMEOUT", earliest_session="2022-01-01", required_start="2021-04-01", prior_buffer_reached=False) == "INCOMPLETE_TIMEOUT"
    before = [{"time": 200}, {"time": 300}]
    after = [{"time": 100}, {"time": 200}, {"time": 300}]
    assert pagination_step(before, after) == {"before_count": 2, "before_min_epoch": 200, "after_count": 3, "after_min_epoch": 100, "delta_bars": 1, "extended": True}


def test_structural_gate_preserves_invalid_evidence() -> None:
    rows = pd.DataFrame([{"open": 10, "high": 9, "low": 8, "close": 8, "volume": -1}])
    result = validate_structural_rows(rows)
    assert result["invalid_rows"] == 1
    assert result["valid"] is False


def test_yearly_support_floor_and_all_years_are_explicit() -> None:
    covered = pd.DataFrame([{"ticker": "AAA", "session_date": "2021-01-01"}, {"ticker": "AAA", "session_date": "2022-01-01"}])
    comparable = covered.iloc[[0]].copy()
    result = yearly_fidelity_support(covered, comparable, [2021, 2022, 2023], minimum_year_matched_rows=2)
    assert set(result) == {"2021", "2022", "2023"}
    assert result["2021"]["minimum_support_pass"] is False
    assert result["2023"]["fidelity_support_ratio"] == 0.0


def test_active_only_model_safe_path_excludes_no_trade_unknown_and_ca() -> None:
    bars = pd.DataFrame([
        {"ticker": "AAA", "session_date": "2021-01-01", "security_id": "S1", "mapped_security_id": "S1", "identity_status": STATUS_MAPPED, "session_admissible": True},
        {"ticker": "AAA", "session_date": "2021-01-02", "security_id": "S1", "mapped_security_id": "S1", "identity_status": STATUS_MAPPED, "session_admissible": True},
        {"ticker": "AAA", "session_date": "2021-01-03", "security_id": "S1", "mapped_security_id": "S1", "identity_status": STATUS_MAPPED, "session_admissible": True},
    ])
    reconciliation = pd.DataFrame([
        {"ticker": "AAA", "session_date": "2021-01-01", "activity_state": "ACTIVE", "reconciliation_status": "COVERED_ACTIVE"},
        {"ticker": "AAA", "session_date": "2021-01-02", "activity_state": "NO_TRADE", "reconciliation_status": "NO_TRADE_WITH_PROVIDER_BARS_REQUIRES_REVIEW"},
        {"ticker": "AAA", "session_date": "2021-01-03", "activity_state": "UNKNOWN", "reconciliation_status": "UNKNOWN_FAIL_CLOSED"},
    ])
    result = active_only_model_safe_rows(bars, reconciliation, {"AAA": "REQUIRED_START_REACHED"}, {("AAA", "2021-01-01")})
    assert result.empty
    result = active_only_model_safe_rows(bars, reconciliation, {"AAA": "REQUIRED_START_REACHED"}, set())
    assert result["session_date"].tolist() == ["2021-01-01"]


def test_official_stock_summary_oracle_compares_hlcv_without_panel_write(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    session = archive / "sessions" / "2021-01-01"
    session.mkdir(parents=True)
    (session / "stock_summary.raw.json").write_text('{"data":[{"StockCode":"AAA","High":12,"Low":9,"Close":11,"Volume":100}]}', encoding="utf-8")
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    pd.DataFrame({"date": [pd.Timestamp("2021-01-01")], "ticker": ["AAA"], "raw_high": [12.0], "raw_low": [9.0], "raw_close": [11.0], "raw_volume": [100.0]}).to_parquet(canonical / "AAA.parquet", index=False)
    rows, summary = official_stock_summary_hlcv_oracle(archive, canonical)
    assert len(rows) == 1
    assert summary["hlc_exact"] == 1.0
    assert summary["volume_within_5"] == 1.0
