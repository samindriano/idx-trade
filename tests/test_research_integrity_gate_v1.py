import json

import pandas as pd
import pytest

from idx_trade.research_integrity_gate_v1 import (
    IntegrityCheck,
    IntegrityStage,
    IntegrityStatus,
    assert_integrity_gate,
    check_additive_identity,
    check_knowledge_time,
    check_ohlc_identity,
    check_required_columns,
    check_unique_key,
    evaluate_integrity_gate,
    load_gate_profile,
    required_checks_for_stage,
)


def test_missing_required_check_materializes_as_unknown_and_blocks():
    report = evaluate_integrity_gate(
        IntegrityStage.DATA_ADMISSION,
        [
            IntegrityCheck(
                check_id="source.semantics",
                category="SOURCE_SEMANTICS",
                status=IntegrityStatus.PASS,
                summary="Source contract frozen.",
            )
        ],
        required_check_ids=("source.semantics", "pit.knowledge_time"),
    )

    assert not report.passed
    assert report.blocking_check_ids == ("pit.knowledge_time",)
    missing = {check.check_id: check for check in report.checks}["pit.knowledge_time"]
    assert missing.status is IntegrityStatus.UNKNOWN
    assert missing.required
    with pytest.raises(RuntimeError, match="DATA_ADMISSION integrity gate failed"):
        assert_integrity_gate(report)


def test_required_profile_check_cannot_be_downgraded_to_optional():
    report = evaluate_integrity_gate(
        "DATA_ADMISSION",
        [
            IntegrityCheck(
                check_id="ca.price_basis",
                category="CORPORATE_ACTION_PRICE_BASIS",
                status=IntegrityStatus.UNKNOWN,
                summary="Not audited yet.",
                required=False,
            )
        ],
        required_check_ids=("ca.price_basis",),
    )

    assert not report.passed
    assert report.blocking_check_ids == ("ca.price_basis",)
    assert report.checks[0].required


def test_optional_unknown_is_visible_but_nonblocking():
    report = evaluate_integrity_gate(
        "RESEARCH_ADMISSION",
        [
            IntegrityCheck(
                check_id="data_admission.pass",
                category="UPSTREAM_GATE",
                status=IntegrityStatus.PASS,
                summary="Upstream gate passed.",
            ),
            IntegrityCheck(
                check_id="diagnostic.extra_visual",
                category="DIAGNOSTIC",
                status=IntegrityStatus.UNKNOWN,
                summary="Optional visual not produced.",
                required=False,
            ),
        ],
        required_check_ids=("data_admission.pass",),
    )

    assert report.passed
    assert report.nonblocking_findings == ("diagnostic.extra_visual",)


def test_schema_unique_key_and_ohlc_primitives_fail_on_bad_rows():
    frame = pd.DataFrame(
        {
            "ticker": ["BBCA", "BBCA"],
            "session": ["2026-01-02", "2026-01-02"],
            "open": [100.0, 100.0],
            "high": [99.0, 101.0],
            "low": [98.0, 99.0],
            "close": [100.0, 100.0],
        }
    )

    assert check_required_columns(frame, ["ticker", "session", "close"]).status is IntegrityStatus.PASS
    assert check_unique_key(frame, ["ticker", "session"]).status is IntegrityStatus.FAIL
    assert check_ohlc_identity(frame).status is IntegrityStatus.FAIL


def test_additive_identity_catches_foreign_flow_mismatch():
    frame = pd.DataFrame(
        {
            "foreign_buy": [100.0, 50.0],
            "foreign_sell": [40.0, 20.0],
            "foreign_net": [60.0, 31.0],
        }
    )

    check = check_additive_identity(
        frame,
        lhs="foreign_net",
        positive="foreign_buy",
        negative="foreign_sell",
    )
    assert check.status is IntegrityStatus.FAIL
    assert check.evidence["invalid_rows"] == 1


def test_knowledge_time_is_fail_closed_for_future_or_unknown_timestamp():
    frame = pd.DataFrame(
        {
            "known_at": ["2026-01-02T09:00:00+07:00", None],
            "decision_at": ["2026-01-02T08:00:00+07:00", "2026-01-03T08:00:00+07:00"],
        }
    )

    check = check_knowledge_time(
        frame,
        knowledge_column="known_at",
        decision_column="decision_at",
    )
    assert check.status is IntegrityStatus.FAIL
    assert check.evidence["invalid_rows"] == 2


def test_default_profile_is_schema_v1_and_has_three_stages(tmp_path):
    payload = {
        "schema_version": 1,
        "stages": {
            "DATA_ADMISSION": {"required_check_ids": ["a"]},
            "RESEARCH_ADMISSION": {"required_check_ids": ["b"]},
            "MODEL_PROMOTION": {"required_check_ids": ["c"]},
        },
    }
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    profile = load_gate_profile(path)
    assert required_checks_for_stage(profile, "DATA_ADMISSION") == ("a",)
    assert required_checks_for_stage(profile, "RESEARCH_ADMISSION") == ("b",)
    assert required_checks_for_stage(profile, "MODEL_PROMOTION") == ("c",)
