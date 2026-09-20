from __future__ import annotations

import json
from pathlib import Path

from research.idx_population_identity_lifecycle_crosswalk_v1 import (
    build_identity_graph,
    classify_ksei_detail,
    parse_ksei_detail_html,
    parse_ksei_sources,
    parse_lifecycle_rows,
    parse_public_ipo_surface,
    parse_corporate_action_probe,
    parse_announcement_hits,
)


VALID_HTML = """
<h1>ABC Tbk, PT</h1>
<dl>
<dt>Security name</dt><dd>ABC Tbk</dd>
<dt>Issuer</dt><dd>ABC Tbk, PT</dd>
<dt>ISIN Code</dt><dd>ID1000123456</dd>
<dt>Short Code</dt><dd>ABC</dd>
<dt>Type</dt><dd>Saham Biasa</dd>
<dt>Listing Date</dt><dd>01 January 2020</dd>
<dt>Status</dt><dd>Active</dd>
</dl>
"""


def test_ksei_detail_requires_matching_code_and_isin() -> None:
    parsed = parse_ksei_detail_html(VALID_HTML, "ABC")
    assert parsed["short_code"] == "ABC"
    assert parsed["isin"] == "ID1000123456"
    assert classify_ksei_detail(VALID_HTML, "ABC", 200)["parse_status"] == "DETAIL_VALID"
    assert classify_ksei_detail(VALID_HTML, "ABD", 200)["parse_status"] == "HTTP_200_EMPTY_OR_MISMATCH"
    assert classify_ksei_detail(VALID_HTML, "ABC", 500)["parse_status"] == "HTTP_NON_200"


def test_ksei_population_preserves_empty_and_transport_results(tmp_path: Path) -> None:
    table_path = tmp_path / "table.json"
    detail_root = tmp_path / "details"
    raw_root = detail_root / "raw"
    raw_root.mkdir(parents=True)
    table_path.write_text(json.dumps({"codes": [{"code": "ABC"}, {"code": "ABD"}, {"code": "ABE"}]}), encoding="utf-8")
    (detail_root / "acquisition_metadata.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"code": "ABC", "http_status": 200, "raw_path": str(raw_root / "ABC.html"), "sha256": "abc"}),
                json.dumps({"code": "ABD", "http_status": 200, "raw_path": str(raw_root / "ABD.html"), "sha256": "abd"}),
                json.dumps({"code": "ABE", "http_status": 500, "raw_path": str(raw_root / "ABE.html"), "sha256": "abe"}),
            ]
        ),
        encoding="utf-8",
    )
    (raw_root / "ABC.html").write_text(VALID_HTML, encoding="utf-8")
    (raw_root / "ABD.html").write_text("<html><body>No registered security result</body></html>", encoding="utf-8")
    codes, details, meta = parse_ksei_sources(table_path, detail_root)
    assert codes == {"ABC", "ABD", "ABE"}
    assert details["ABC"]["parse_status"] == "DETAIL_VALID"
    assert details["ABD"]["parse_status"] == "HTTP_200_EMPTY_OR_MISMATCH"
    assert details["ABE"]["parse_status"] == "HTTP_NON_200"
    assert meta["detail_status_counts"]["DETAIL_VALID"] == 1


def test_lifecycle_rows_keep_conflicting_intervals(tmp_path: Path) -> None:
    current = tmp_path / "current.csv"
    delisting = tmp_path / "delisting.csv"
    master = tmp_path / "master.csv"
    header = "ticker,company_name,listed_from,listed_to,source,source_ref\n"
    current.write_text(header + "ABC,ABC Tbk,2020-01-01,,current,CURRENT\n", encoding="utf-8")
    delisting.write_text(header + "ABC,Old ABC,2020-01-01,2022-01-01,delisting,DEL\n", encoding="utf-8")
    master.write_text("security_id,ticker,company_name,listed_from,listed_to,source\n" + "IDX:ABC:1,ABC,ABC Tbk,2020-01-01,,master\n", encoding="utf-8")
    intervals, meta = parse_lifecycle_rows(current, delisting, master)
    assert len(intervals["ABC"]) == 3
    assert meta["conflict_codes"] == ["ABC"]


def test_identity_graph_edges_are_bounded_and_provenanced(tmp_path: Path) -> None:
    raw = tmp_path / "ABC.html"
    raw.write_text(VALID_HTML, encoding="utf-8")
    ksei = {
        "ABC": {
            **classify_ksei_detail(VALID_HTML, "ABC", 200),
            "acquisition": {"raw_path": str(raw), "sha256": "sha", "retrieved_at_utc": "2026-09-20T00:00:00Z"},
        }
    }
    graph = build_identity_graph(
        ["ABC"],
        ksei,
        {},
        {},
        {"ABC": [{"security_id": "IDX:ABC:1", "_source_path": "master.csv", "_source_sha256": "master-sha"}]},
        {},
    )
    assert graph["global_constraints"]["historical_population_completeness"] == "UNKNOWN"
    edge = next(item for item in graph["edges"] if item["relation"] == "IDENTIFIED_BY_ISIN")
    assert edge["status"] == "SUPPORTED_BOUNDED"
    assert edge["provenance"][0]["sha256"] == "sha"


def test_public_ipo_surface_uses_issuer_ticker_not_participant_codes(tmp_path: Path) -> None:
    root = tmp_path / "data"
    stock_root = root / "stock"
    stock_root.mkdir(parents=True)
    (root / "stocks.csv").write_text("ticker_code;participant_admin.code\nABCD;OD\n", encoding="utf-8")
    (stock_root / "EFGH.json").write_text(json.dumps({"ticker_code": "EFGH", "participant_admin": {"code": "SQ"}}), encoding="utf-8")
    (stock_root / "ABCD-C1.json").write_text(json.dumps({"ticker_code": "ABCD-C1", "participant_admin": {"code": "OD"}}), encoding="utf-8")
    codes, nonstandard = parse_public_ipo_surface(root)
    assert codes == {"ABCD", "EFGH"}
    assert nonstandard == {"ABCD-C1"}
    assert "OD" not in codes


def test_corporate_action_probe_preserves_document_semantics(tmp_path: Path) -> None:
    path = tmp_path / "ca.json"
    path.write_text(json.dumps({"source": {"codes": ["ABC"], "raw_sha256": "raw", "sample_records": 1}, "document_evidence": [{"code": "ABC", "publish_date": "2024-01-01", "document_sha256": "doc", "semantics": "plan pending approval", "effective_transition_stated": False}]}), encoding="utf-8")
    codes, evidence = parse_corporate_action_probe(path)
    assert codes == {"ABC"}
    assert evidence["ABC"][1]["effective_transition_stated"] is False


def test_announcement_hits_require_exact_code_and_preserve_bounded_semantics(tmp_path: Path) -> None:
    root = tmp_path / "probes" / "idx-announcements"
    root.mkdir(parents=True)
    (root / "page.raw").write_text(json.dumps({"Items": [
        {"Code": "ABC", "PublishDate": "2026-01-01", "Title": "Perubahan Nama Anak Perusahaan", "AnnouncementNo": "A1"},
        {"Code": "ABCD", "PublishDate": "2026-01-02", "Title": "Perubahan Nama Emiten", "AnnouncementNo": "A2"},
    ]}), encoding="utf-8")
    hits = parse_announcement_hits(tmp_path / "probes", {"ABC"})
    assert list(hits) == ["ABC"]
    assert hits["ABC"][0]["title"] == "Perubahan Nama Anak Perusahaan"


def test_materialized_identity_collision_census_does_not_collapse_security_identity() -> None:
    packet_path = Path(__file__).parents[1] / "research_knowledge" / "identity_lifecycle_population_crosswalk_v1.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    census = packet["identity_collision_census"]
    assert census["status"] == "COUNTEREXAMPLES_PRESERVED_NO_COLLAPSE"
    assert census["current_detail_contract_limits"]["series_continuity_proven"] is False
    assert census["current_detail_contract_limits"]["historical_ticker_reuse_proven"] is False
    assert census["lifecycle_conflict_codes"] == ["BUKK", "INRU", "ITMA", "KIAS", "SKBM", "UNTX"]


def test_materialized_conflict_audit_keeps_heterogeneous_classes_unknown() -> None:
    packet_path = Path(__file__).parents[1] / "research_knowledge" / "identity_lifecycle_population_crosswalk_v1.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    audit = packet["lifecycle_conflict_source_audit"]
    assert audit["BUKK"]["ksei_detail_status"] == "HTTP_NON_200"
    assert audit["ITMA"]["ksei_detail_status"] == "DETAIL_VALID"
    assert audit["UNTX"]["profile_present"] is False
    assert len(audit["SKBM"]["exact_announcement_hits"]) == 2
    assert all("Anak Perusahaan" in hit["title"] for hit in audit["SKBM"]["exact_announcement_hits"])
    assert audit["UNTX"]["announcement_search_interpretation"].startswith("bounded retained-search")


def test_historical_only_announcement_audit_does_not_turn_no_hits_into_absence() -> None:
    packet_path = Path(__file__).parents[1] / "research_knowledge" / "identity_lifecycle_population_crosswalk_v1.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    audit = packet["historical_only_announcement_audit"]
    assert audit["searched_code_count"] == 115
    assert audit["exact_hit_count"] == 0
    assert audit["exact_code_count"] == 0
    assert "not evidence" in audit["interpretation"]
