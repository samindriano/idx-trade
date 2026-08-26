import hashlib

import pandas as pd

from idx_trade.research_integrity_gate_v1 import (
    IntegrityStatus,
    check_allowed_values,
    check_file_hashes,
    check_missingness_policy,
    check_nonnegative,
    check_ohlc_identity,
    check_session_membership,
    check_knowledge_time,
    check_unique_key,
)


def test_nonnegative_rejects_non_numeric_even_when_na_is_allowed():
    frame = pd.DataFrame({"volume": [1.0, None, "oops"]})
    check = check_nonnegative(frame, ["volume"], allow_na=True)
    assert check.status is IntegrityStatus.FAIL
    assert check.evidence["invalid_rows"] == 1


def test_allowed_values_supports_exact_unit_contract():
    frame = pd.DataFrame({"unit": ["SHARES", "SHARES", "VALUE"]})
    check = check_allowed_values(frame, "unit", ["SHARES"])
    assert check.status is IntegrityStatus.FAIL
    assert check.evidence["invalid_rows"] == 1
    assert check.evidence["invalid_examples"] == ["VALUE"]


def test_session_membership_rejects_non_official_date():
    frame = pd.DataFrame({"session_date": ["2026-01-02", "2026-01-03"]})
    official = pd.DatetimeIndex(["2026-01-02", "2026-01-05"])
    check = check_session_membership(frame, official, session_column="session_date")
    assert check.status is IntegrityStatus.FAIL
    assert check.evidence["invalid_rows"] == 1


def test_missingness_policy_is_column_specific():
    frame = pd.DataFrame({"a": [1.0, None, None, 4.0], "b": [1.0, None, 3.0, 4.0]})
    check = check_missingness_policy(frame, {"a": 0.25, "b": 0.25})
    assert check.status is IntegrityStatus.FAIL
    assert "a" in check.evidence["violations"]
    assert "b" not in check.evidence["violations"]


def test_file_hashes_pass_and_fail_closed_when_missing(tmp_path):
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"idx-trade")
    expected = hashlib.sha256(b"idx-trade").hexdigest()

    passed = check_file_hashes({path: expected})
    assert passed.status is IntegrityStatus.PASS

    missing = check_file_hashes({tmp_path / "missing.bin": expected})
    assert missing.status is IntegrityStatus.UNKNOWN


def test_nonnegative_rejects_infinite_values():
    frame = pd.DataFrame({"value": [float("inf"), float("-inf"), 1.0]})
    check = check_nonnegative(frame, ["value"])
    assert check.status is IntegrityStatus.FAIL
    assert check.evidence["invalid_rows"] == 2


def test_empty_data_checks_are_unknown():
    empty = pd.DataFrame({"value": pd.Series(dtype=float), "session_date": pd.Series(dtype=str)})
    assert check_nonnegative(empty, ["value"]).status is IntegrityStatus.UNKNOWN
    assert check_allowed_values(empty, "value", [1]).status is IntegrityStatus.UNKNOWN
    assert check_session_membership(empty, ["2026-01-02"], session_column="session_date").status is IntegrityStatus.UNKNOWN
    assert check_missingness_policy(empty, {"value": 1.0}).status is IntegrityStatus.UNKNOWN


def test_knowledge_time_rejects_naive_timestamps():
    frame = pd.DataFrame(
        {
            "known_at": ["2026-01-02 09:00:00"],
            "decision_at": ["2026-01-02T10:00:00+07:00"],
        }
    )
    check = check_knowledge_time(frame, knowledge_column="known_at", decision_column="decision_at")
    assert check.status is IntegrityStatus.FAIL
    assert check.evidence["naive_timestamp_rows"] == 1


def test_empty_hash_expectation_is_unknown():
    assert check_file_hashes({}).status is IntegrityStatus.UNKNOWN


def test_unique_key_rejects_null_key_values():
    frame = pd.DataFrame({"ticker": [None], "session": ["2026-01-02"]})
    check = check_unique_key(frame, ["ticker", "session"])
    assert check.status is IntegrityStatus.FAIL
    assert check.evidence["null_key_rows"] == 1


def test_ohlc_rejects_nonfinite_or_nonpositive_values():
    frame = pd.DataFrame(
        {
            "open": [100.0, 0.0],
            "high": [float("inf"), 1.0],
            "low": [99.0, 0.0],
            "close": [100.0, 1.0],
        }
    )
    check = check_ohlc_identity(frame)
    assert check.status is IntegrityStatus.FAIL
    assert check.evidence["invalid_rows"] == 2
