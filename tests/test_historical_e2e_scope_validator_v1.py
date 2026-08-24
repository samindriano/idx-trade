from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path

import pytest

from idx_trade.historical_e2e_scope_validator_v1 import (
    EXPECTED_CANDIDATE_SESSION_COUNT,
    HistoricalE2EScopeValidationError,
    MIN_STRICT_SESSION_COUNT,
    canonical_scope_payload_hash,
    load_replay_scope,
    validate_scope_payload,
)


def _synthetic_scope(
    *,
    status: str = "STRICT_SCOPE_FROZEN",
    strict_start: int = 0,
    strict_count: int = EXPECTED_CANDIDATE_SESSION_COUNT,
) -> dict[str, object]:
    sessions = []
    first_decision_date = date(2020, 1, 2)
    for index in range(EXPECTED_CANDIDATE_SESSION_COUNT):
        decision_date = first_decision_date + timedelta(days=index)
        execution_date = decision_date + timedelta(days=1)
        sessions.append(
            {
                "session_index": index,
                "decision_session_date": decision_date.isoformat(),
                "execution_session_date": execution_date.isoformat(),
            }
        )

    payload: dict[str, object] = {
        "schema_version": "idx_trade_historical_e2e_scope_v1",
        "status": status,
        "outcome_access": False,
        "model_fit": False,
        "protected_outcome_access": False,
        "source_pins": {
            "structural_manifest_sha256": "a" * 64,
            "calendar_sha256": "b" * 64,
        },
        "candidate_session_count": EXPECTED_CANDIDATE_SESSION_COUNT,
        "strict_session_indices": (
            list(range(strict_start, strict_start + strict_count))
            if status == "STRICT_SCOPE_FROZEN"
            else []
        ),
        "blockers": [] if status == "STRICT_SCOPE_FROZEN" else ["BLOCKED"],
        "open": {"per_session": sessions},
    }
    if status == "STRICT_SCOPE_FROZEN":
        payload.update(
            {
                "start_session": sessions[strict_start]["decision_session_date"],
                "end_session": sessions[strict_start + strict_count - 1][
                    "decision_session_date"
                ],
                "session_count": strict_count,
            }
        )
    payload["scope_payload_sha256"] = canonical_scope_payload_hash(payload)
    return payload


def _assert_invalid(payload: dict[str, object], expected: str) -> None:
    with pytest.raises(HistoricalE2EScopeValidationError, match=expected):
        validate_scope_payload(payload)


def test_valid_synthetic_strict_scope_is_accepted_and_hash_is_deterministic() -> None:
    payload = _synthetic_scope()
    result = validate_scope_payload(payload)
    assert result == payload

    reordered = dict(reversed(list(payload.items())))
    assert canonical_scope_payload_hash(
        {key: value for key, value in reordered.items() if key != "scope_payload_sha256"}
    ) == payload["scope_payload_sha256"]


@pytest.mark.parametrize(
    "strict_count", [20, 60, 120, 252, EXPECTED_CANDIDATE_SESSION_COUNT]
)
def test_meaningful_contiguous_strict_ranges_are_accepted(strict_count: int) -> None:
    payload = _synthetic_scope(strict_start=0, strict_count=strict_count)
    assert validate_scope_payload(payload)["session_count"] == strict_count


def test_strict_scope_minimum_is_twenty_sessions() -> None:
    payload = _synthetic_scope(strict_count=MIN_STRICT_SESSION_COUNT - 1)
    _assert_invalid(payload, "REPLAY_SCOPE_SESSION_COUNT_INVALID")


def test_nonzero_scope_start_fails_without_predecessor_state_anchor() -> None:
    payload = _synthetic_scope(strict_start=17, strict_count=20)
    _assert_invalid(payload, "REPLAY_SCOPE_NONZERO_START_STATE_UNSUPPORTED")


def test_empty_scope_is_valid_only_as_blocked_status() -> None:
    payload = _synthetic_scope(status="STRICT_SCOPE_EMPTY_BLOCKED")
    assert validate_scope_payload(payload)["strict_session_indices"] == []

    without_optional_hash = dict(payload)
    without_optional_hash.pop("scope_payload_sha256")
    with pytest.raises(HistoricalE2EScopeValidationError, match="PAYLOAD_HASH_MISSING"):
        validate_scope_payload(without_optional_hash)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("structural_manifest_sha256", "a" * 63),
        ("calendar_sha256", "g" * 64),
        ("scope_payload_sha256", "f" * 63),
    ],
)
def test_malformed_hashes_fail_closed(field: str, value: str) -> None:
    payload = _synthetic_scope()
    if field == "scope_payload_sha256":
        payload[field] = value
    else:
        pins = deepcopy(payload["source_pins"])
        assert isinstance(pins, dict)
        pins[field] = value
        payload["source_pins"] = pins
    _assert_invalid(payload, "REPLAY_SCOPE_(SOURCE_PIN|PAYLOAD_HASH)_INVALID")


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (
            lambda payload: payload["strict_session_indices"].__setitem__(100, 101),
            "REPLAY_SCOPE_STRICT_SESSION_INDEX_DUPLICATE",
        ),
        (
            lambda payload: payload["strict_session_indices"].__setitem__(100, 102),
            "REPLAY_SCOPE_STRICT_SESSION_INDICES_NOT_ORDERED",
        ),
        (
            lambda payload: payload.__setitem__("strict_session_indices", list(range(500))),
            "REPLAY_SCOPE_STRICT_SESSION_COUNT_INVALID",
        ),
    ],
)
def test_non_contiguous_duplicate_and_incorrect_strict_indices_fail_closed(
    mutator, expected: str
) -> None:
    payload = _synthetic_scope()
    mutator(payload)
    payload.pop("scope_payload_sha256", None)
    _assert_invalid(payload, expected)


@pytest.mark.parametrize("field", ["outcome_access", "model_fit", "protected_outcome_access"])
def test_any_outcome_or_fit_flag_true_fails_closed(field: str) -> None:
    payload = _synthetic_scope()
    payload[field] = True
    payload.pop("scope_payload_sha256", None)
    _assert_invalid(payload, f"REPLAY_SCOPE_{field.upper()}_FLAG_INVALID")


def test_duplicate_session_identity_fails_even_with_unique_indices() -> None:
    payload = _synthetic_scope()
    sessions = deepcopy(payload["open"]["per_session"])
    assert isinstance(sessions, list)
    sessions[1]["decision_session_date"] = sessions[0]["decision_session_date"]
    sessions[1]["execution_session_date"] = sessions[0]["execution_session_date"]
    payload["open"]["per_session"] = sessions
    payload.pop("scope_payload_sha256", None)
    _assert_invalid(payload, "REPLAY_SCOPE_SESSION_IDENTITY_DUPLICATE")


def test_strict_scope_gap_fails_closed() -> None:
    payload = _synthetic_scope(strict_count=20)
    payload["strict_session_indices"] = list(range(9)) + list(range(10, 21))
    payload.pop("scope_payload_sha256", None)
    _assert_invalid(payload, "REPLAY_SCOPE_STRICT_SESSION_INDICES_NOT_CONTIGUOUS")


@pytest.mark.parametrize("field", ["start_session", "end_session", "session_count"])
def test_explicit_strict_range_boundaries_are_required_and_bound(field: str) -> None:
    payload = _synthetic_scope(strict_start=0, strict_count=20)
    if field == "start_session":
        payload[field] = "2020-01-03"
    elif field == "end_session":
        payload[field] = "2020-01-03"
    else:
        payload[field] = 21
    payload.pop("scope_payload_sha256", None)
    _assert_invalid(payload, "REPLAY_SCOPE_(RANGE_BOUND|.*SESSION_COUNT)_")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "wrong_schema"),
        ("status", "DRAFT"),
    ],
)
def test_schema_and_status_fail_closed(field: str, value: str) -> None:
    payload = _synthetic_scope()
    payload[field] = value
    payload.pop("scope_payload_sha256", None)
    _assert_invalid(payload, f"REPLAY_SCOPE_{'SCHEMA_VERSION' if field == 'schema_version' else 'STATUS'}_INVALID")


def test_hash_mismatch_and_invalid_json_file_fail_closed(tmp_path: Path) -> None:
    payload = _synthetic_scope()
    payload["blockers"] = ["UNEXPECTED_MUTATION"]
    _assert_invalid(payload, "REPLAY_SCOPE_PAYLOAD_HASH_MISMATCH")

    path = tmp_path / "REPLAY_SCOPE.json"
    path.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(HistoricalE2EScopeValidationError, match="REPLAY_SCOPE_JSON_INVALID"):
        load_replay_scope(path)


def test_loader_validates_synthetic_scope_file(tmp_path: Path) -> None:
    payload = _synthetic_scope()
    path = tmp_path / "REPLAY_SCOPE.json"
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    assert load_replay_scope(path) == payload
