from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

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
    all_dates = pd.bdate_range("2026-04-01", "2026-08-31")
    dates = [date for date in all_dates if date != pd.Timestamp("2026-05-01")]
    historical_dates = [date for date in dates if date <= pd.Timestamp("2026-07-31")]
    forward_dates = [date for date in dates if date > pd.Timestamp("2026-07-31")]
    write_parquet_atomic(
        pd.DataFrame(
            {
                "ticker": ["AAAA"] * len(historical_dates),
                "date": historical_dates,
                "close": [10.0] * len(historical_dates),
            }
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
                "source": ["TEST_OPEN"],
                "source_ref": ["test://open"],
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
    open_child.update({"source": "TEST_OPEN", "source_sha256": "a" * 64})
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
            "historical_end": "2026-07-31",
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
                "source_sha256": "a" * 64,
                "observed_retrieved_at_utc": "2026-08-28T11:00:00+00:00",
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
            "implementation_repository": "samindriano/idx-trade",
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
    trusted_contract = {
        "producer_id": gate.FEATURE_BASIS_PRODUCER_ID,
        "implementation_repository": "samindriano/idx-trade",
        "implementation_ref": "git://test-producer",
        "implementation_commit": "1" * 40,
        "implementation_sha256": producer_child["sha256"],
        "policy_id": gate.FEATURE_BASIS_POLICY_ID,
        "schema_version": gate.FEATURE_BASIS_SCHEMA_VERSION,
    }
    trusted_contract["trust_contract_sha256"] = hashlib.sha256(
        gate._canonical_json(trusted_contract)
    ).hexdigest()
    context = {
        "session_date": SESSION,
        "model_input_tickers": ["AAAA"],
        "model_input_path": model_path,
        "model_input_sha256": sha256_file(model_path),
        "clean_panel_path": panel_path,
        "clean_panel_sha256": sha256_file(panel_path),
        "historical_panel_end": "2026-07-31",
        "official_session_dates": historical_dates + forward_dates,
        "calendar_sources": {
            "historical": historical_dates,
            "forward": forward_dates,
        },
        "evidence": evidence,
        "observed_at": OBSERVED_AT,
        "evidence_path": evidence_path,
        "evidence_sha256": sha256_file(evidence_path),
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
        "candidate_ohlcv_path": candidate_path,
        "candidate_ohlcv_sha256": sha256_file(candidate_path),
        "trusted_producer_contract": trusted_contract,
    }
    return context, record


def _resign_bundle(context: dict[str, object], mutate: callable) -> None:
    manifest_path = Path(context["manifest_path"])
    evidence_path = Path(context["evidence_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    manifest["manifest_id"] = gate._feature_basis_manifest_identity(manifest)
    evidence = dict(context["evidence"])
    evidence["root_manifest_id"] = manifest["manifest_id"]
    evidence_path.write_text(json.dumps(evidence, sort_keys=True) + "\n", encoding="utf-8")
    manifest["evidence_sha256"] = sha256_file(evidence_path)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    context["evidence"] = evidence
    context["evidence_sha256"] = sha256_file(evidence_path)
    context["manifest_sha256"] = sha256_file(manifest_path)


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


def test_missing_external_producer_anchor_fails_closed(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context.pop("trusted_producer_contract")
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "PRODUCER_TRUST_ANCHOR_MISSING" in result["reason_codes"]


def test_complete_self_signed_bundle_is_rejected_by_external_anchor(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    manifest_path = Path(context["manifest_path"])

    def mutate(manifest: dict[str, object]) -> None:
        producer = manifest["producer"]
        child = next(item for item in manifest["children"] if item["evidence_id"] == "producer")
        child_path = manifest_path.parent / child["path"]
        child_path.write_text("self-signed-producer\n", encoding="utf-8")
        child["sha256"] = sha256_file(child_path)
        producer["implementation_commit"] = "2" * 40
        producer["implementation_sha256"] = child["sha256"]

    _resign_bundle(context, mutate)
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "PRODUCER_COMMIT_MISMATCH" in result["reason_codes"]


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("producer_id", "other-producer", "PRODUCER_ID_MISMATCH"),
        ("implementation_repository", "other/repo", "PRODUCER_REPOSITORY_MISMATCH"),
        ("implementation_ref", "git://other", "PRODUCER_REF_MISMATCH"),
        ("implementation_commit", "2" * 40, "PRODUCER_COMMIT_MISMATCH"),
        ("implementation_sha256", "b" * 64, "PRODUCER_ARTIFACT_SHA_MISMATCH"),
    ],
)
def test_external_producer_anchor_mismatch_is_not_admitted(
    tmp_path: Path, field: str, value: str, reason: str
) -> None:
    context, _ = _fixture(tmp_path / field)
    context["trusted_producer_contract"][field] = value
    contract = context["trusted_producer_contract"]
    contract["trust_contract_sha256"] = hashlib.sha256(
        gate._canonical_json(
            {
                key: item
                for key, item in contract.items()
                if key != "trust_contract_sha256"
            }
        )
    ).hexdigest()
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert reason in result["reason_codes"]


def test_external_trust_contract_sha_must_be_valid(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["trusted_producer_contract"]["trust_contract_sha256"] = "invalid"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "PRODUCER_TRUST_CONTRACT_SHA_INVALID" in result["reason_codes"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("producer_id", "tampered-producer"),
        ("implementation_repository", "other/repository"),
        ("implementation_ref", "git://tampered"),
        ("implementation_commit", "2" * 40),
        ("implementation_sha256", "b" * 64),
        ("policy_id", "TAMPERED_POLICY"),
        ("schema_version", "tampered-schema"),
    ],
)
def test_trust_contract_digest_binds_every_trusted_field(
    tmp_path: Path, field: str, value: str
) -> None:
    context, _ = _fixture(tmp_path / field)
    contract = context["trusted_producer_contract"]
    original_digest = contract["trust_contract_sha256"]
    contract[field] = value
    assert contract["trust_contract_sha256"] == original_digest
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "PRODUCER_TRUST_CONTRACT_SHA_MISMATCH" in result["reason_codes"]


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
    official = sorted(pd.Timestamp(value) for value in context["official_session_dates"])
    target_index = official.index(pd.Timestamp(SESSION))
    record["transition_dates"] = [
        official[target_index - 60].date().isoformat()
    ]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_SAFE


def test_transition_at_exact_longest_official_session_boundary_blocks(
    tmp_path: Path,
) -> None:
    context, record = _fixture(tmp_path)
    record["state"] = "CERTIFIED_TRANSITION"
    official = sorted(pd.Timestamp(value) for value in context["official_session_dates"])
    target_index = official.index(pd.Timestamp(SESSION))
    record["transition_dates"] = [
        official[target_index - 59].date().isoformat()
    ]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_TRANSITION_OVERLAP
    assert any(
        reason.startswith("BASIS_TRANSITION_OVERLAP:AAAA:")
        for reason in result["reason_codes"]
    )


def test_forward_calendar_is_separate_from_clean_panel_and_preserves_session_gaps(
    tmp_path: Path,
) -> None:
    context, _ = _fixture(tmp_path)
    official = {pd.Timestamp(value).date().isoformat() for value in context["official_session_dates"]}
    assert max(pd.Timestamp(value) for value in pd.read_parquet(context["clean_panel_path"])["date"]) == pd.Timestamp("2026-07-31")
    assert pd.Timestamp(SESSION) in context["calendar_sources"]["forward"]
    assert "2026-08-29" not in official
    assert "2026-05-01" not in official
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_SAFE


def test_non_official_or_missing_forward_calendar_fails_closed(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["official_session_dates"] = [
        value for value in context["official_session_dates"] if pd.Timestamp(value).date().isoformat() != SESSION
    ]
    context["calendar_sources"] = {
        "historical": context["calendar_sources"]["historical"],
        "forward": [
            value for value in context["calendar_sources"]["forward"] if pd.Timestamp(value).date().isoformat() != SESSION
        ],
    }
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_SESSION_NOT_OFFICIAL" in result["reason_codes"]

    context, _ = _fixture(tmp_path / "missing-forward")
    context["calendar_sources"] = {
        "historical": context["calendar_sources"]["historical"],
        "forward": [],
    }
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_CALENDAR_SOURCE_CONFLICT" in result["reason_codes"]


def test_calendar_conflict_duplicate_and_future_rows_are_explicit(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["calendar_sources"]["historical"].append(pd.Timestamp("2026-08-27"))
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_CALENDAR_SOURCE_CONFLICT" in result["reason_codes"]

    context, _ = _fixture(tmp_path / "duplicate")
    context["official_session_dates"].append(SESSION)
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_OFFICIAL_CALENDAR_DUPLICATE" in result["reason_codes"]

    context, _ = _fixture(tmp_path / "future")
    context["official_session_dates"].append(pd.Timestamp("2026-09-01"))
    context["calendar_sources"]["forward"].append(pd.Timestamp("2026-09-01"))
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
    record["transition_dates"] = ["2026-08-31"]
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.BASIS_UNRESOLVED
    assert "FEATURE_BASIS_TRANSITION_AFTER_SESSION:AAAA:2026-08-31" in result[
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


def test_open_binding_must_match_candidate_source_reference_and_hash(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    context["evidence"]["geometry_open"]["open_source_identity"]["source_ref"] = "test://unrelated"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_OPEN_SOURCE_ROW_MISMATCH:AAAA" in result["reason_codes"]

    context, _ = _fixture(tmp_path / "source-hash")
    context["evidence"]["geometry_open"]["open_source_identity"]["source_sha256"] = "b" * 64
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_OPEN_SOURCE_ROW_MISMATCH:AAAA" in result["reason_codes"]

    context, _ = _fixture(tmp_path / "unrelated-child")
    context["evidence"]["geometry_open"]["open_source_identity"]["evidence_id"] = "field-high"
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_OPEN_SOURCE_UNBOUND:AAAA" in result["reason_codes"]


def test_candidate_open_source_metadata_is_required(tmp_path: Path) -> None:
    context, _ = _fixture(tmp_path)
    candidate_path = Path(context["candidate_ohlcv_path"])
    candidate = pd.read_parquet(candidate_path)
    candidate.loc[0, "source_ref"] = ""
    write_parquet_atomic(candidate, candidate_path)
    context["candidate_ohlcv_sha256"] = sha256_file(candidate_path)
    _resign_bundle(
        context,
        lambda manifest: next(
            item
            for item in manifest["children"]
            if item["evidence_id"] == "session-ohlcv"
        ).__setitem__("sha256", sha256_file(candidate_path)),
    )
    result = gate.evaluate_feature_basis_admission(**context)
    assert result["status"] == gate.SOURCE_CAPTURE_UNRESOLVED
    assert "FEATURE_BASIS_CANDIDATE_SOURCE_METADATA_MISSING" in result["reason_codes"]


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
