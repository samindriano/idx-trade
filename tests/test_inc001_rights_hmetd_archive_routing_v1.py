from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_inc001_rights_hmetd_archive_routing_v1.py"
SPEC = importlib.util.spec_from_file_location("rights_archive_routing", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_archive_semantics_requires_publication_month_evidence(tmp_path: Path) -> None:
    root = tmp_path / "retained"
    root.mkdir()
    (root / "event_candidate_documents.csv").write_text(
        "event_id,ticker,source_type,family,source_dates,query_slug,query_year,query_month,reference,subject,document_date,document_url\n"
        "E1,TEST,Right Distribution,RIGHT_DISTRIBUTION,2021-03-01,rights-distribution,2021,01,REF1,HMETD TEST,2021-01-05,https://example.invalid/1.pdf\n"
        "E2,TEST2,Right Distribution,RIGHT_DISTRIBUTION,2025-12-10,rights-distribution,2025,12,REF2,HMETD TEST2,2025-12-01,https://example.invalid/2.pdf\n",
        encoding="utf-8",
    )
    result = audit.archive_temporal_semantics(root)
    assert result["conclusion"] == "ARCHIVE_KEYS_PUBLICATION_MONTH"
    assert result["retained_document_rows"] == 2
    assert result["archive_month_equals_publication_month_rows"] == 2
    assert result["publication_to_first_event_calendar_months"]["maximum"] == 2


def test_archive_plan_is_exact_three_month_window_and_deduplicated(tmp_path: Path) -> None:
    v13 = tmp_path / "v13"
    retained = tmp_path / "retained"
    followup = tmp_path / "followup"
    for root in (v13, retained, followup):
        root.mkdir()
    source_header = "source_event_id,source_kind,ticker,event_family,source_native_label,candidate_date,cum_date,record_date,distribution_date,ratio_raw,source_ref,evidence_sha256,source_contract_id\n"
    source_rows = []
    for ticker, source_id, candidate in (
        ("SAME", audit.TARGET_SOURCE_IDS["SAME"], "2021-03-01"),
        ("SGER", audit.TARGET_SOURCE_IDS["SGER"], "2024-05-29"),
        ("PACK", audit.TARGET_SOURCE_IDS["PACK"], "2026-01-13"),
    ):
        source_rows.append(
            f"{source_id},{audit.KSEI_KIND},{ticker},RIGHTS_HMETD,Right Distribution,{candidate},,{candidate},{candidate},(1 {ticker} : 1 {ticker}-R),https://example.invalid/{ticker},{'a' * 64},CONTRACT\n"
        )
    (v13 / "source_evidence_ledger.csv").write_text(source_header + "".join(source_rows), encoding="utf-8")
    (retained / "event_candidate_documents.csv").write_text(
        "event_id,ticker,source_type,family,source_dates,query_slug,query_year,query_month,reference,subject,document_date,document_url\n"
        "E1,OTHER,Right Distribution,RIGHT_DISTRIBUTION,2021-03-01,rights-distribution,2021,01,REF1,HMETD OTHER,2021-01-05,https://example.invalid/1.pdf\n",
        encoding="utf-8",
    )
    (retained / "request_records.jsonl").write_text("[]", encoding="utf-8")
    (followup / "bounded_followup_results.json").write_text(json.dumps({"index_results": []}), encoding="utf-8")
    targets, plan = audit.target_scope_and_plan(v13, retained, followup)
    assert [row["ticker"] for row in targets] == ["SAME", "SGER", "PACK"]
    assert plan["scope_tickers"] == ["SAME", "SGER", "PACK"]
    assert plan["new_request_count"] == 9
    assert len(plan["new_request_months"]) == 9
    assert len(plan["new_request_months"]) == len(set(plan["new_request_months"]))
    assert plan["planned_months_by_ticker"]["SAME"] == ["2021-01", "2021-02", "2021-03"]
    assert plan["planned_months_by_ticker"]["SGER"] == ["2024-03", "2024-04", "2024-05"]
    assert plan["planned_months_by_ticker"]["PACK"] == ["2025-11", "2025-12", "2026-01"]


def test_candidate_month_no_match_with_no_provider_failure_is_not_false_negative() -> None:
    target = {
        "economic_event_id": "E1",
        "ticker": "SAME",
        "candidate_date": "2021-03-01",
    }
    result = audit.classify_target(
        target,
        [
            {"item": {"ticker": "SAME", "month_key": "2021-03"}, "matching_target_rows": 0, "request": {"status_code": 200}},
            {"item": {"ticker": "SAME", "month_key": "2021-02"}, "matching_target_rows": 0, "request": {"status_code": 200}},
        ],
        [],
    )
    assert result["routing_root_cause"] == "ARCHIVE_ROW_STILL_NOT_DISCOVERED"
    assert result["result_classification"] == "ARCHIVE_ROW_STILL_NOT_DISCOVERED"
    assert result["non_candidate_month_matching_rows"] == 0


def test_non_candidate_exact_row_is_recorded_as_routing_false_negative() -> None:
    target = {"economic_event_id": "E1", "ticker": "SAME", "candidate_date": "2021-03-01"}
    result = audit.classify_target(
        target,
        [
            {"item": {"ticker": "SAME", "month_key": "2021-03"}, "matching_target_rows": 0, "request": {"status_code": 200}},
            {"item": {"ticker": "SAME", "month_key": "2021-02"}, "matching_target_rows": 1, "request": {"status_code": 200}},
        ],
        [],
    )
    assert result["routing_root_cause"] == "CANDIDATE_MONTH_ROUTING_FALSE_NEGATIVE"
    assert result["result_classification"] == "DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT"


def test_transition_date_linkage_requires_record_and_distribution_match() -> None:
    target = {"record_date": "2025-01-14", "distribution_date": "2025-01-20"}
    assert audit.target_dates_match(target, {"record_date": "2025-01-14", "distribution_date": "2025-01-20"})
    assert not audit.target_dates_match(target, {"record_date": "2025-01-14", "distribution_date": "2025-01-21"})


def test_exact_document_capture_creates_its_immutable_parent(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_request(url: str, raw_path: Path) -> dict[str, object]:
        calls.append(url)
        raw_path.write_bytes(b"official pdf bytes")
        return {"status_code": 200, "raw_path": str(raw_path), "sha256": audit.sha256_file(raw_path), "bytes": raw_path.stat().st_size}

    def fake_extract(pdf_path: Path, text_path: Path) -> tuple[str, str]:
        text_path.write_text(
            "Tanggal Ex di Pasar Regular dan Pasar Negosiasi: 13 Januari 2025\n"
            "Tanggal Pencatatan (Recording Date): 14 Januari 2025\n"
            "Tanggal Distribusi: 20 Januari 2025\n",
            encoding="utf-8",
        )
        return "OK", audit.sha256_file(text_path)

    monkeypatch.setattr(audit, "perform_request", fake_request)
    monkeypatch.setattr(audit, "extract_pdf_text", fake_extract)
    target = {"record_date": "2025-01-14", "distribution_date": "2025-01-20"}
    result = audit.fetch_and_parse_exact_document(
        {"source_ref": "https://example.invalid/exact.pdf", "document_reference": "KSEI-1/JKU/0125", "title": "HMETD TEST"},
        "TEST",
        target,
        tmp_path / "audit",
        1,
    )
    assert calls == ["https://example.invalid/exact.pdf"]
    assert result["document_result"] == "RESOLVED_EXACT"
    assert Path(result["request"]["raw_path"]).is_file()
