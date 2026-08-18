from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_v4_ca_material_six_remediation_v3 as v3


def _smar_row(**overrides):
    row = {
        "ticker": "SMAR",
        "row_index": 1,
        "event_family_source": "Voluntary Conversion",
        "cum_date": "",
        "record_date": "",
        "distribution_date": "2026-06-11",
        "status": "Active",
        "ratio_raw": "(1 SMAR : 5265 IDR )",
        "ratio_left_value": "1",
        "ratio_left_security": "SMAR",
        "ratio_right_value": "5265",
        "ratio_right_security": "IDR",
        "source_url": "https://web.ksei.co.id/services/registered-securities/shares/lc/SMAR?setLocale=en-US",
        "source_sha256": "abc123",
    }
    row.update(overrides)
    return row


def test_smar_exact_static_security_to_idr_is_nonblocking() -> None:
    classifier = v3.material_six_classifier_v3("fren123")
    event = classifier(
        _smar_row(),
        official_sessions=pd.date_range("2026-06-01", "2026-06-30", freq="B"),
    )
    assert event.ticker == "SMAR"
    assert event.semantic_class == "NON_BLOCKING"
    assert event.transition_date is None
    assert event.family == "VOLUNTARY_CASH_STATIC_SECURITY_TO_CURRENCY"
    assert "SECURITY_TO_IDR" in event.reason


def test_smar_near_miss_ratio_stays_fail_closed() -> None:
    classifier = v3.material_six_classifier_v3("fren123")
    event = classifier(
        _smar_row(ratio_right_value="5264"),
        official_sessions=pd.date_range("2026-06-01", "2026-06-30", freq="B"),
    )
    assert event.semantic_class == "SCHEDULE_REQUIRED"


def test_direct_fallback_scope_is_narrow() -> None:
    assert v3._DIRECT_FALLBACK_TICKERS == {"AVIA", "SMAR", "SCMA", "ADRO"}
    assert "FREN" not in v3._DIRECT_FALLBACK_TICKERS
    assert "MEGA" not in v3._DIRECT_FALLBACK_TICKERS


def test_mega_is_removed_only_from_provider_retry_scope() -> None:
    original = ("AVIA", "SMAR", "MEGA", "SCMA", "FREN", "ADRO")
    result = v3.retry_scope_without_zero_support_mega(original)
    assert result == ("AVIA", "SMAR", "SCMA", "FREN", "ADRO")
    assert set(result) == set(original) - {"MEGA"}


def test_retry_scope_requires_mega_identity() -> None:
    try:
        v3.retry_scope_without_zero_support_mega(("AVIA", "SMAR"))
    except RuntimeError as exc:
        assert "MEGA_EXPECTED_IN_ORIGINAL_RETRY_SCOPE" in str(exc)
    else:
        raise AssertionError("missing MEGA in original retry scope must fail closed")