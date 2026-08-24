from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.prospective_evaluation_gate_v1 import (
    ProspectiveAccessGateBlocked,
    _normalize_dates,
    _canonical_hash,
    _validate_target_against_contract,
    _validate_code_pin_manifest,
    git_blob_sha1_file,
    validate_machine_readable_contract,
)
from idx_trade.provenance import sha256_file


CONTRACT = Path("config/v4_x1_prospective_evaluation_contract_v1.json").resolve()
CODE_PIN = Path("config/v4_x1_prospective_evaluation_code_pin_v1.json").resolve()
CLI = Path("tools/evaluate_prospective_v4_x1.py").resolve()
PROTOCOL = Path("docs/checkpoints/2026-08-24_V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1.md").resolve()
EVALUATOR = Path("src/idx_trade/prospective_evaluation_v1.py").resolve()
GATE = Path("src/idx_trade/prospective_evaluation_gate_v1.py").resolve()


def test_machine_contract_explicitly_blocks_unresolved_canonical_target() -> None:
    contract_sha = sha256_file(CONTRACT)
    with pytest.raises(ProspectiveAccessGateBlocked, match="CANONICAL_TARGET_IDENTITY_UNRESOLVED"):
        validate_machine_readable_contract(CONTRACT, contract_sha, require_resolved_target=True)


def test_preflight_cli_is_read_only_and_reports_target_blocker() -> None:
    contract_sha = sha256_file(CONTRACT)
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--preflight-only",
            "--contract",
            str(CONTRACT),
            "--contract-sha256",
            contract_sha,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["status"] == "PRE_FLIGHT_BLOCKED"
    assert payload["blocker_codes"] == ["CANONICAL_TARGET_IDENTITY_UNRESOLVED"]
    assert payload["protected_outcomes_accessed"] is False
    assert payload["real_protected_loader_called"] is False
    assert payload["real_outcome_access_marker_written"] is False
    assert payload["forward_counter_changed"] is False
    assert payload["paper_state_changed"] is False


def test_session_date_timezone_does_not_shift_civil_date() -> None:
    normalized = _normalize_dates(
        pd.Series(["2026-08-25T00:00:00+07:00"]), label="synthetic session"
    )
    assert normalized.iloc[0] == pd.Timestamp("2026-08-25")


def test_code_pin_manifest_binds_to_executing_gate_and_evaluator(tmp_path: Path) -> None:
    payload = {
        "schema_version": "v4_x1_prospective_evaluation_code_pin_v1",
        "model": {
            "model_id": "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1",
            "generation": "V4-X1-CLEAN",
            "fingerprint": "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf",
        },
        "protocol": {
            "path": str(PROTOCOL),
            "source_commit": "a" * 40,
            "git_blob_sha1": git_blob_sha1_file(PROTOCOL),
        },
        "evaluator": {
            "path": str(EVALUATOR),
            "source_commit": "b" * 40,
            "git_blob_sha1": git_blob_sha1_file(EVALUATOR),
        },
        "gate": {
            "path": str(GATE),
            "source_commit": "c" * 40,
            "git_blob_sha1": git_blob_sha1_file(GATE),
        },
        "contract": {"path": str(CONTRACT), "sha256": sha256_file(CONTRACT)},
    }
    manifest = tmp_path / "code-pins.json"
    manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    manifest_sha = sha256_file(manifest)
    _validate_code_pin_manifest(
        manifest,
        manifest_sha,
        protocol_path=PROTOCOL,
        evaluator_path=EVALUATOR,
        gate_path=GATE,
        contract_path=CONTRACT,
        fixture_root=None,
    )

    copied_evaluator = tmp_path / "copied_evaluator.py"
    shutil.copyfile(EVALUATOR, copied_evaluator)
    with pytest.raises(ProspectiveAccessGateBlocked, match="not the executing module"):
        _validate_code_pin_manifest(
            manifest,
            manifest_sha,
            protocol_path=PROTOCOL,
            evaluator_path=copied_evaluator,
            gate_path=GATE,
            contract_path=CONTRACT,
            fixture_root=None,
        )


def test_committed_code_pin_manifest_is_self_consistent() -> None:
    _validate_code_pin_manifest(
        CODE_PIN,
        sha256_file(CODE_PIN),
        protocol_path=PROTOCOL,
        evaluator_path=EVALUATOR,
        gate_path=GATE,
        contract_path=CONTRACT,
        fixture_root=None,
    )


def test_resolved_target_must_match_contract_and_source_manifest(tmp_path: Path) -> None:
    identity = {
        "status": "RESOLVED",
        "target_id": "TARGET_V1",
        "horizon": "T+5",
        "definition": "close_t5 / open_t1 - 1",
        "transform": "gross_raw_price_return",
        "provenance": {"builder": "builder.py"},
        "hashes": {"builder_sha256": "a" * 64},
    }
    source = tmp_path / "target-source.json"
    source.write_text(
        json.dumps(
            {
                "canonical_target_id": "TARGET_V1",
                "target_identity_sha256": _canonical_hash(identity),
                "target_identity": identity,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    target = {
        "canonical_target_id": "TARGET_V1",
        "target_identity_sha256": _canonical_hash(identity),
        "horizon": identity["horizon"],
        "definition": identity["definition"],
        "transform": identity["transform"],
        "provenance": identity["provenance"],
        "target_hashes": identity["hashes"],
        "source_manifest_path": str(source),
    }
    _validate_target_against_contract(target, {"target_identity": identity})
    bad = dict(target, canonical_target_id="OTHER_TARGET")
    with pytest.raises(ProspectiveAccessGateBlocked, match="does not match frozen contract identity"):
        _validate_target_against_contract(bad, {"target_identity": identity})
