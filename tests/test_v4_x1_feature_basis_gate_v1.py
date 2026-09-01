from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from idx_trade import v4_x1_population_admission_v1 as gate
from idx_trade.provenance import sha256_file
from idx_trade.forward_ohlcv import SESSION_OHLCV_COLUMNS
from idx_trade.ranking_v4_3_features import V4_CONTROL_FEATURE_COLUMNS
from idx_trade.storage import write_parquet_atomic
from idx_trade.ranking_v4_3_preregistration import SESSION_GEOMETRY_FEATURE_COLUMNS


SESSION = "2026-08-28"
OBSERVED_AT = "2026-08-28T18:35:00+07:00"


def test_window_contract_matches_actual_frozen_final_feature_order() -> None:
    assert tuple(feature for feature, _ in gate.FEATURE_BASIS_WINDOW_CONTRACT) == (
        *V4_CONTROL_FEATURE_COLUMNS,
        *SESSION_GEOMETRY_FEATURE_COLUMNS,
    )


def _fixture(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    model_path = tmp_path / "model_input.parquet"
    panel_path = tmp_path / "clean_panel.parquet"
    write_parquet_atomic(
        pd.DataFrame(
            {
                "ticker": ["AAAA"],
                "date": [SESSION],
                "close": [10.0],
            }
        ),
        model_path,
    )
    dates = pd.date_range("2026-06-29", periods=62, freq="D")
    write_parquet_atomic(
        pd.DataFrame(
            {"ticker": ["AAAA"] * len(dates), "date": dates, "close": [10.0] * len(dates)}
        ),
        panel_path,
    )
    candidate_path = tmp_path / "session_ohlcv.parquet"
    write_parquet_atomic(
        pd.DataFrame(
            {
                "ticker": ["AAAA"],
                "session_date": [SESSION],
                "open": [10.0],
                "high": [11.0],
                "low": [9.0],
                "close": [10.0],
                "volume": [100.0],
                "source": ["TEST"],
                "source_ref": ["test://ohlcv"],
                "source_sha256": ["a" * 64],
                "observed_retrieved_at_utc": ["2026-08-28T11:00:00+00:00"],
            }
        ).loc[:, SESSION_OHLCV_COLUMNS],
        candidate_path,
    )
    evidence_path = tmp_path / gate.FEATURE_BASIS_EVIDENCE_FILENAME
    manifest_path = tmp_path / gate.FEATURE_BASIS_MANIFEST_FILENAME
    child_root = tmp_path / "basis_children"
    child_root.mkdir()

    def child(name: str, kind: str, source_ref: str, content: str) -> dict[str, str]:
        path = child_root / f"{name}.json"
        path.write_text(content, encoding="utf-8")
        return {
            "evidence_id": name,
            "kind": kind,
            "path": str(path.relative_to(tmp_path)),
            "sha256": sha256_file(path),
            "source_ref": source_ref,
        }

    producer_child = child("producer", "producer_implementation", "git://producer", "producer-v1\n")
    field_children = {
        field: child(
            f"field-{field}",
            "field_source",
            f"test://basis/{field}",
            f"{field}-basis\n",
        )
        for field in gate.FEATURE_BASIS_FIELDS
    }
    authority_child = child("authority", "authority", "test://authority", "authority-v1\n")
    attestation_children = {
        name: child(name, "attestation", f"test://{name}", f"{name}-v1\n")
        for name in ("identity_attestation", "calendar_attestation", "revision_attestation", "pit_attestation")
    }
    open_child = child("open-source", "open_source", "test://open", "open-v1\n")
    children = [
        producer_child,
        *field_children.values(),
        authority_child,
        *attestation_children.values(),
        open_child,
        {
            "evidence_id": "session-ohlcv",
            "kind": "session_ohlcv",
            "path": str(candidate_path.relative_to(tmp_path)),
            "sha256": sha256_file(candidate_path),
            "source_ref": "test://ohlcv",
        },
    ]
    record = {
        "ticker": "AAAA",
        "state": "CERTIFIED_SAME_BASIS",
        "field_states": {
            "high": "CERTIFIED_SAME_BASIS",
            "low": "CERTIFIED_SAME_BASIS",
            "close": "CERTIFIED_SAME_BASIS",
            "volume": "CERTIFIED_SAME_BASIS",
            "regular_market_value": "CERTIFIED_SAME_BASIS",
        },
        "transition_dates": [],
        "authority": {
            "name": "IDX_TEST_AUTHORITY",
            "ref": "test://authority",
            "sha256": authority_child["sha256"],
            "evidence_id": "authority",
        },
        "source_refs": [child["source_ref"] for child in field_children.values()],
        "source_evidence_ids": {
            field: field_children[field]["evidence_id"] for field in gate.FEATURE_BASIS_FIELDS
        },
        "source_hashes": {
            field: field_children[field]["sha256"] for field in gate.FEATURE_BASIS_FIELDS
        },
    }
    attestations = {
        name: {
            "status": "VERIFIED",
            "ref": attestation_children[name]["source_ref"],
            "sha256": attestation_children[name]["sha256"],
            "evidence_id": name,
        }
        for name in attestation_children
    }
    attestations["pit_attestation"]["knowledge_at"] = OBSERVED_AT
    evidence = {
        "schema_version": gate.FEATURE_BASIS_SCHEMA_VERSION,
        "policy_id": gate.FEATURE_BASIS_POLICY_ID,
        "session_date": SESSION,
        "knowledge_at": OBSERVED_AT,
        "root_manifest_path": str(manifest_path.resolve()),
        "model_input_path": str(model_path.resolve()),
        "model_input_sha256": sha256_file(model_path),
        "model_input_set_sha256": gate._set_hash(["AAAA"]),
        "clean_panel_path": str(panel_path.resolve()),
        "clean_panel_sha256": sha256_file(panel_path),
        "scorer_boundary": {
            "source": "MAX_DATE_FROM_CLEAN_PANEL",
            "historical_end": "2026-08-29",
            "clean_panel_sha256": sha256_file(panel_path),
        },
        **attestations,
        "geometry_open": {
            "status": "CERTIFIED_SAME_BASIS",
            "session_ohlcv_path": str(candidate_path.resolve()),
            "session_ohlcv_sha256": sha256_file(candidate_path),
            "session_ohlcv_evidence_id": "session-ohlcv",
            "session_date": SESSION,
            "knowledge_at": OBSERVED_AT,
            "ticker_set_sha256": gate._set_hash(["AAAA"]),
            "open_source_identity": {
                "source": "TEST_OPEN",
                "source_ref": open_child["source_ref"],
                "evidence_id": "open-source",
            },
            "open_evidence_sha256": open_child["sha256"],
        },
        "window_contract": [
            {"feature": feature, "potential_mixed_basis_span": span}
            for feature, span in gate.FEATURE_BASIS_WINDOW_CONTRACT
        ],
        "window_contract_sha256": gate._feature_basis_window_contract_sha256(),
        "records": [record],
    }
    manifest = {
        "schema_version": gate.FEATURE_BASIS_MANIFEST_SCHEMA_VERSION,
        "policy_id": gate.FEATURE_BASIS_POLICY_ID,
        "evidence_path": str(evidence_path.relative_to(tmp_path)),
        "evidence_sha256": "0" * 64,
        "producer": {
            "producer_id": gate.FEATURE_BASIS_PRODUCER_ID,
            "implementation_ref": "git://test-producer",
            "implementation_commit": "1" * 40,
            "implementation_sha256": producer_child["sha256"],
            "implementation_evidence_id": "producer",
        },
        "children": children,
    }
    manifest["manifest_id"] = gate._feature_basis_manifest_identity(manifest)
    evidence["root_manifest_id"] = manifest["manifest_id"]
    evidence_path.write_text(json.dumps(evidence, sort_keys=True) + "\n", encoding="utf-8")
    manifest["evidence_sha256"] = sha256_file(evidence_path)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    context = {
        "session_date": SESSION,
        "model_input_tickers": ["AAAA"],
        "model_input_path": model_path,
        "model_input_sha256": sha256_file(model_path),
        "clean_panel_path": panel_path,
        "clean_panel_sha256": sha256_file(panel_path),
        "official_session_dates": dates,
        "evidence": evidence,
        "observed_at": OBSERVED_AT,
        "evidence_path": evidence_path,
        "evidence_sha256": sha256_file(evidence_path),
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
        "candidate_ohlcv_path": candidate_path,
        "candidate_ohlcv_sha256": sha256_file(candidate_path),
    }
    return context, record


def test_explicit_same_basis_whole_population_is_safe(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_SAFE
    assert result["reason_codes"] == []


def test_missing_certificate_is_source_capture_unresolved(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["evidence"] = None
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert result["reason_codes"] == ["FEATURE_BASIS_EVIDENCE_MISSING"]


def test_no_known_transition_is_not_a_certified_no_event(tmp_path: Path) -> None:
    context, record = _fixture(tmp_path)
    record["state"] = "NO_KNOWN_TRANSITION"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_NOT_CERTIFIED:AAAA:NO_KNOWN_TRANSITION" in result[
        "reason_codes"
    ]


def test_transition_inside_longest_feature_window_blocks_whole_session(
    tmp_path: Path,
) -> None:
    context, record = _fixture(tmp_path)
    record["state"] = "CERTIFIED_TRANSITION"
    record["transition_dates"] = ["2026-08-27"]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_TRANSITION_OVERLAP
    assert any(
        reason.startswith("BASIS_TRANSITION_OVERLAP:AAAA:2026-08-27:")
        for reason in result["reason_codes"]
    )


def test_transition_outside_exact_window_can_be_admitted(tmp_path: Path) -> None:
    context, record = _fixture(tmp_path)
    record["state"] = "CERTIFIED_TRANSITION"
    record["transition_dates"] = ["2026-06-29"]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_SAFE


def test_field_basis_mismatch_is_not_hidden_by_top_level_certificate(
    tmp_path: Path,
) -> None:
    context, record = _fixture(tmp_path)
    record["field_states"]["volume"] = "CERTIFIED_TRANSITION"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_FIELD_BASIS_NOT_SAFE:AAAA" in result["reason_codes"]


def test_evidence_hash_and_path_binding_fail_closed(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["evidence"]["clean_panel_sha256"] = "0" * 64
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_CLEAN_PANEL_HASH_MISMATCH" in result["reason_codes"]


def test_partial_attestation_is_not_population_safe(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    del context["evidence"]["pit_attestation"]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_PIT_ATTESTATION_INVALID" in result["reason_codes"]


def test_extra_certificate_record_cannot_be_used_to_filter_the_population(
    tmp_path: Path,
) -> None:
    context, record = _fixture(tmp_path)
    extra = dict(record)
    extra["ticker"] = "BBBB"
    context["evidence"]["records"].append(extra)
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_RECORD_EXTRA:BBBB" in result["reason_codes"]


def test_future_transition_is_not_admitted_or_inferred(tmp_path: Path) -> None:
    context, record = _fixture(tmp_path)
    record["state"] = "CERTIFIED_TRANSITION"
    record["transition_dates"] = ["2026-08-29"]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_TRANSITION_AFTER_SESSION:AAAA:2026-08-29" in result[
        "reason_codes"
    ]


def test_open_is_a_required_fresh_candidate_certificate(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    del context["evidence"]["geometry_open"]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_OPEN_EVIDENCE_MISSING" in result["reason_codes"]


def test_open_source_child_hash_is_recomputed_not_declarative(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    manifest = json.loads(Path(context["manifest_path"]).read_text(encoding="utf-8"))
    child = next(item for item in manifest["children"] if item["kind"] == "open_source")
    (Path(context["manifest_path"]).parent / child["path"]).write_text(
        "tampered-open\n", encoding="utf-8"
    )
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert any(reason.startswith("FEATURE_BASIS_MANIFEST_CHILD_HASH_MISMATCH:open-source") for reason in result["reason_codes"])


def test_open_candidate_must_match_session_and_model_population(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["evidence"]["geometry_open"]["session_date"] = "2026-08-27"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_OPEN_SESSION_MISMATCH" in result["reason_codes"]

    context, _ = _fixture(tmp_path / "ticker-mismatch")
    context["evidence"]["geometry_open"]["ticker_set_sha256"] = gate._set_hash(["BBBB"])
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_OPEN_TICKER_SET_MISMATCH" in result["reason_codes"]


def test_future_open_knowledge_is_not_admitted(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["evidence"]["geometry_open"]["knowledge_at"] = "2026-08-29T00:00:00+07:00"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_OPEN_KNOWLEDGE_AT_AFTER_OBSERVATION" in result["reason_codes"]


def test_root_manifest_binds_evidence_bytes_and_ids(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["evidence_sha256"] = "0" * 64
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_EVIDENCE_HASH_MISMATCH" in result["reason_codes"]

    context, _ = _fixture(tmp_path / "evidence-bytes")
    evidence_path = Path(context["evidence_path"])
    evidence_path.write_text(evidence_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    context["evidence_sha256"] = sha256_file(evidence_path)
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_MANIFEST_EVIDENCE_HASH_MISMATCH" in result["reason_codes"]

    context, _ = _fixture(tmp_path / "undeclared")
    context["evidence"]["records"][0]["source_evidence_ids"]["high"] = "not-declared"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_SOURCE:AAAA:high_EVIDENCE_UNDECLARED" in result["reason_codes"]


def test_manifest_rejects_duplicate_ids_and_unapproved_producer(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    manifest_path = Path(context["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["children"][1]["evidence_id"] = manifest["children"][0]["evidence_id"]
    manifest["manifest_id"] = gate._feature_basis_manifest_identity(manifest)
    context["evidence"]["root_manifest_id"] = manifest["manifest_id"]
    evidence_path = Path(context["evidence_path"])
    evidence_path.write_text(json.dumps(context["evidence"], sort_keys=True) + "\n", encoding="utf-8")
    context["evidence_sha256"] = sha256_file(evidence_path)
    manifest["evidence_sha256"] = sha256_file(evidence_path)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_MANIFEST_DUPLICATE_EVIDENCE_ID" in result["reason_codes"]

    context, _ = _fixture(tmp_path / "producer")
    manifest_path = Path(context["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["producer"]["producer_id"] = "unapproved-producer"
    manifest["manifest_id"] = gate._feature_basis_manifest_identity(manifest)
    context["evidence"]["root_manifest_id"] = manifest["manifest_id"]
    evidence_path = Path(context["evidence_path"])
    evidence_path.write_text(json.dumps(context["evidence"], sort_keys=True) + "\n", encoding="utf-8")
    context["evidence_sha256"] = sha256_file(evidence_path)
    manifest["evidence_sha256"] = sha256_file(evidence_path)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_PRODUCER_ID_INVALID" in result["reason_codes"]


def test_open_safe_does_not_hide_unsafe_historical_fields(tmp_path: Path) -> None:
    context, record = _fixture(tmp_path)
    record["field_states"]["volume"] = "CERTIFIED_TRANSITION"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_FIELD_BASIS_NOT_SAFE:AAAA" in result["reason_codes"]
