from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.v4_ksei_coverage_gap import (
    classify_attempt,
    merge_coverage,
    merge_history,
    parent_failure_summary,
    ticker_identity_sha256,
)


EXPECTED_GAP_SHA = "1cd050985841519d24f58a38d10014693ff4a843cbd438586237ad4419ffe812"
EXPECTED_GAPS = {
    "ACRO", "AMAN", "AVIA", "AYAM", "BCIP", "BDKR", "BJTM", "CBRE",
    "DFAM", "DGIK", "HELI", "IBOS", "ICBP", "ISAP", "ISAT", "JPFA",
    "KEJU", "KRAS", "MAPA", "MAPI", "MIDI", "MIKA", "MINA", "MSJA",
    "NASI", "OLIV", "PMMP", "PMUI", "PRIM", "PSAB", "SDMU", "SKRN",
    "SLIS", "SMAR", "SNLK", "SOCI", "SOFA", "STAA", "STRK", "TCPI",
    "TEBE", "TOSK", "VISI",
}


def test_frozen_config_exact_43_identity():
    config = json.loads(Path("config/v4_ksei_coverage_gap_remediation_v1.json").read_text(encoding="utf-8"))
    tickers = config["gap_tickers"]
    assert len(tickers) == 43
    assert len(set(tickers)) == 43
    assert set(tickers) == EXPECTED_GAPS
    assert ticker_identity_sha256(tickers) == EXPECTED_GAP_SHA
    assert config["gap_ticker_identity_sha256"] == EXPECTED_GAP_SHA
    assert config["provider"]["source_substitution"] is False
    assert config["provider"]["parser_relaxation"] is False
    assert config["hard_boundaries"]["full_610_recrawl"] is False
    assert config["hard_boundaries"]["target_or_rank_materialization"] is False
    assert config["hard_boundaries"]["model_fit"] is False


def test_attempt_failure_classes_are_fail_closed():
    assert classify_attempt({"status_code": 0, "bytes": 0, "error": "Timeout: boom"}) == "NETWORK_OR_TRANSPORT"
    assert classify_attempt({"status_code": 503, "bytes": 123, "error": "RuntimeError:HTTP_OR_EMPTY:503:123"}) == "HTTP_NON_200_OR_EMPTY"
    assert classify_attempt({"status_code": 200, "bytes": 500, "error": "KseiHistoryParseError:KSEI short-code identity mismatch: expected AMAN, got None"}) == "PARSE_IDENTITY_MISMATCH"
    assert classify_attempt({"status_code": 200, "bytes": 500, "error": "KseiHistoryParseError:expected exactly one Corporate Action table, found 0"}) == "PARSE_TABLE_STRUCTURE"


def test_parent_failure_summary_requires_every_gap_ticker():
    records = [
        {"ticker": "ACRO", "attempt": 1, "status_code": 0, "bytes": 0, "error": "Timeout:x"},
        {"ticker": "ACRO", "attempt": 2, "status_code": 0, "bytes": 0, "error": "Timeout:y"},
    ]
    summary = parent_failure_summary(records, gap_tickers=["ACRO"])
    assert summary.iloc[0]["parent_dominant_failure_class"] == "NETWORK_OR_TRANSPORT"
    with pytest.raises(RuntimeError, match="PARENT_REQUEST_RECORDS_MISSING_GAP_TICKER"):
        parent_failure_summary(records, gap_tickers=["ACRO", "AMAN"])


def _coverage_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "AAAA", "coverage_status": "COVERAGE_CERTIFIED", "coverage_certified": True, "attempt_count": 1, "final_http_status": 200, "source_url": "u1", "source_sha256": "h1", "ca_rows": 2, "active_ca_rows": 2, "active_mechanical_rows": 0, "active_unknown_rows": 0, "earliest_ca_date": "2020-01-01", "latest_ca_date": "2021-01-01", "failure_reason": ""},
            {"ticker": "ACRO", "coverage_status": "COVERAGE_UNRESOLVED", "coverage_certified": False, "attempt_count": 3, "final_http_status": 0, "source_url": "old", "source_sha256": None, "ca_rows": 0, "active_ca_rows": 0, "active_mechanical_rows": 0, "active_unknown_rows": 0, "earliest_ca_date": None, "latest_ca_date": None, "failure_reason": "ALL_THREE_ATTEMPTS_FAILED_OR_UNPARSABLE"},
        ]
    )


def test_merge_coverage_only_replaces_successful_gap_row_and_preserves_non_gap():
    parent = _coverage_frame()
    remediation = parent[parent["ticker"].eq("ACRO")].copy()
    remediation.loc[:, "coverage_status"] = "COVERAGE_CERTIFIED"
    remediation.loc[:, "coverage_certified"] = True
    remediation.loc[:, "attempt_count"] = 1
    remediation.loc[:, "final_http_status"] = 200
    remediation.loc[:, "source_url"] = "new"
    remediation.loc[:, "source_sha256"] = "newhash"
    remediation.loc[:, "ca_rows"] = 4
    remediation.loc[:, "failure_reason"] = ""
    merged = merge_coverage(parent, remediation, gap_tickers=["ACRO"])
    assert merged.loc[merged["ticker"].eq("AAAA")].iloc[0].to_dict() == parent.loc[parent["ticker"].eq("AAAA")].iloc[0].to_dict()
    acro = merged.loc[merged["ticker"].eq("ACRO")].iloc[0]
    assert bool(acro["coverage_certified"]) is True
    assert acro["source_sha256"] == "newhash"


def test_failed_recovery_cannot_mutate_parent_gap_row():
    parent = _coverage_frame()
    remediation = parent[parent["ticker"].eq("ACRO")].copy()
    remediation.loc[:, "attempt_count"] = 99
    remediation.loc[:, "failure_reason"] = "NEW_FAILURE"
    merged = merge_coverage(parent, remediation, gap_tickers=["ACRO"])
    assert merged.loc[merged["ticker"].eq("ACRO")].iloc[0].to_dict() == parent.loc[parent["ticker"].eq("ACRO")].iloc[0].to_dict()


def test_merge_history_is_append_only_and_scope_locked():
    parent = [{"ticker": "AAAA", "row_index": 1, "event_family_source": "Cash Dividend"}]
    recovered = [{"ticker": "ACRO", "row_index": 1, "event_family_source": "Proxy Voting"}]
    merged = merge_history(parent, recovered, gap_tickers=["ACRO"])
    assert merged == [*parent, *recovered]
    with pytest.raises(RuntimeError, match="RECOVERED_HISTORY_OUT_OF_SCOPE"):
        merge_history(parent, [{"ticker": "BBBB"}], gap_tickers=["ACRO"])


def test_parent_gap_history_must_be_empty_before_append():
    with pytest.raises(RuntimeError, match="PARENT_HISTORY_UNEXPECTED_ROWS_FOR_GAP_TICKERS"):
        merge_history([{"ticker": "ACRO", "row_index": 1}], [], gap_tickers=["ACRO"])
