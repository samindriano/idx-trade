import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from idx_trade.ohlcv_o1_research import V3_B_FEATURE_COLUMNS
from idx_trade.ohlcv_o2_forward import (
    FORWARD_GATE_SESSION_COUNT,
    ForwardContractError,
    O2_CANDIDATE_ID,
    O2_FEATURE_ORDER_SHA256,
    OfficialO2Counter,
    OutcomeAccessGuard,
    PreFreezeSessionError,
    ProtectedOutcomeAccessError,
    SessionGapError,
    _snapshot_provenance_hash,
    persist_counter_state,
    persist_session_score_artifact,
    load_counter_state,
    resolve_first_post_freeze_session,
    score_forward_session,
)
from idx_trade.ohlcv_o2_geometry_research import o2_hgb_pipeline


def _calendar() -> pd.DataFrame:
    starts = pd.date_range("2026-08-10", periods=105, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "session_index": np.arange(1, len(starts) + 1),
            "session_date": starts.date.astype(str),
            "session_start": starts,
        }
    )


def _snapshot(session_date: str, session_index: int) -> pd.DataFrame:
    row = {column: 0.1 for column in V3_B_FEATURE_COLUMNS}
    row.update(
        {
            "ticker": "AAA",
            "signal_date": session_date,
            "signal_session_index": session_index,
            "v3b_eligible": True,
            "input_provenance_sha256": hashlib.sha256(b"aaa").hexdigest(),
            "open": 10.0,
            "high": 11.0,
            "low": 9.0,
            "open_position": 0.5,
            "open_to_high": 0.1,
            "open_to_low": -0.1,
        }
    )
    second = dict(row)
    second["ticker"] = "BBB"
    second["v3b_eligible"] = False
    second["v3b_exclusion_reason"] = "V3B_INELIGIBLE_FIXTURE"
    second["input_provenance_sha256"] = hashlib.sha256(b"bbb").hexdigest()
    return pd.DataFrame([row, second])


def _models():
    rng = np.random.default_rng(42)
    features = pd.DataFrame(rng.normal(size=(8, len(V3_B_FEATURE_COLUMNS) + 3)), columns=[*V3_B_FEATURE_COLUMNS, "open_position", "open_to_high", "open_to_low"])
    target = np.array([0, 1] * 4)
    o2 = o2_hgb_pipeline(tuple(features.columns))
    baseline = o2_hgb_pipeline(tuple(V3_B_FEATURE_COLUMNS))
    o2.fit(features, target)
    baseline.fit(features[list(V3_B_FEATURE_COLUMNS)], target)
    from idx_trade.ohlcv_o2_forward import FrozenModelBundle, FrozenModelIdentity

    o2_id = FrozenModelIdentity("O2", O2_CANDIDATE_ID, None, None, "0" * 64, "0" * 64, O2_FEATURE_ORDER_SHA256, tuple(features.columns))
    v3b_id = FrozenModelIdentity("V3B", "V3-B-STRUCTURE-LITE-V1-CANDIDATE-005", None, None, "1" * 64, "1" * 64, "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e", tuple(V3_B_FEATURE_COLUMNS))
    return FrozenModelBundle(o2, baseline, o2_id, v3b_id)


def test_first_post_freeze_session_is_resolved_from_calendar() -> None:
    calendar = _calendar()
    first = resolve_first_post_freeze_session(calendar, "2026-08-10T12:00:00Z")
    assert first["session_index"] == 2
    assert first["session_date"] == "2026-08-11"


def test_score_only_exact_eligible_rows_and_preserve_exclusion_reason() -> None:
    calendar = _calendar()
    snapshot = _snapshot("2026-08-11", 2)
    result = score_forward_session(
        snapshot=snapshot,
        calendar=calendar,
        session_index=2,
        freeze_timestamp="2026-08-10T12:00:00Z",
        model_bundle=_models(),
        snapshot_sha256=hashlib.sha256(b"snapshot").hexdigest(),
    )
    assert result.outcomes_accessed is False
    assert result.rows["o2_eligible"].tolist() == [True, False]
    assert result.rows.loc[1, "eligibility_reason"] == "V3B_INELIGIBLE_FIXTURE"
    assert result.rows.loc[0, "o2_raw_score"] == pytest.approx(result.rows.loc[0, "o2_raw_score"])
    assert result.snapshot_provenance_sha256 == _snapshot_provenance_hash(snapshot)


def test_session_artifact_is_immutable_and_counter_rejects_backdating_and_gaps(tmp_path) -> None:
    calendar = _calendar()
    result = score_forward_session(
        snapshot=_snapshot("2026-08-11", 2),
        calendar=calendar,
        session_index=2,
        freeze_timestamp="2026-08-10T12:00:00Z",
        model_bundle=_models(),
        snapshot_sha256=hashlib.sha256(b"snapshot").hexdigest(),
    )
    manifest = persist_session_score_artifact(result, tmp_path)
    assert manifest["outcomes_accessed"] is False
    persisted_manifest = json.loads((tmp_path / "session_0002_2026-08-11.json").read_text(encoding="utf-8"))
    assert persisted_manifest["manifest_sha256"] == manifest["manifest_sha256"]
    counter = OfficialO2Counter(first_post_freeze_session_index=2)
    resumed_counter = OfficialO2Counter(first_post_freeze_session_index=2)
    reloaded_manifest = persist_session_score_artifact(result, tmp_path)
    assert reloaded_manifest["manifest_sha256"] == persisted_manifest["manifest_sha256"]
    assert resumed_counter.register(reloaded_manifest) == 1
    counter = resumed_counter
    assert counter.session_count == 1
    with pytest.raises(PreFreezeSessionError):
        OfficialO2Counter(2).register({**manifest, "session_index": 1})
    with pytest.raises(SessionGapError):
        counter.register({**manifest, "session_index": 4})
    assert counter.evaluation_ready(111) is False
    assert FORWARD_GATE_SESSION_COUNT == 100
    state_path = tmp_path / "counter.json"
    persisted = persist_counter_state(counter, state_path)
    assert persisted["session_count"] == 1
    reloaded_counter = load_counter_state(state_path)
    assert reloaded_counter.first_post_freeze_session_index == 2
    assert reloaded_counter.session_count == 1
    with pytest.raises(ForwardContractError):
        persist_counter_state(OfficialO2Counter(2), state_path)
    with pytest.raises(ForwardContractError):
        persist_counter_state(OfficialO2Counter(3, session_count=1, last_session_index=3), state_path)


def test_outcome_access_and_outcome_columns_fail_closed() -> None:
    with pytest.raises(ProtectedOutcomeAccessError):
        OutcomeAccessGuard().open()
    with pytest.raises(ProtectedOutcomeAccessError):
        score_forward_session(
            snapshot=_snapshot("2026-08-11", 2).assign(binary_target=1),
            calendar=_calendar(),
            session_index=2,
            freeze_timestamp="2026-08-10T12:00:00Z",
            model_bundle=_models(),
            snapshot_sha256=hashlib.sha256(b"snapshot").hexdigest(),
        )
