from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from idx_trade.prospective_evaluation_gate_v1 import (
    ProspectiveAccessGateBlocked,
    _validate_canonical_target_identity,
    validate_machine_readable_contract,
)
from idx_trade.provenance import sha256_file


CONTRACT = Path("config/v4_x1_prospective_evaluation_contract_v1.json").resolve()


def _payload() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_frozen_target_identity_validates_without_metric_access() -> None:
    payload = _payload()
    _validate_canonical_target_identity(payload, contract_path=CONTRACT)
    assert payload["target_identity"]["status"] == "RESOLVED"
    assert payload["evaluation"]["historical_reference_provenance_status"] == "UNRESOLVED_CONTEXT_ONLY"


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(lambda t: t["definition"].update(entry_price="Close_(t)"), id="denominator"),
        pytest.param(lambda t: t["definition"].update(h5="Close_(t+4) / Open_(t+1) - 1"), id="h5-horizon"),
        pytest.param(lambda t: t["definition"].update(h10="Close_(t+9) / Open_(t+1) - 1"), id="h10-horizon"),
        pytest.param(lambda t: t["transform"]["realized_consensus"]["weights"].update(h5=0.4, h10=0.6), id="consensus-weights"),
        pytest.param(lambda t: t["transform"]["raw_target_rank"].update(ascending=False), id="rank-direction"),
        pytest.param(lambda t: t["transform"]["raw_target_rank"].update(method="min"), id="rank-ties"),
        pytest.param(lambda t: t["transform"]["final_target"].update(rank_transform="extra-rank"), id="final-rank"),
        pytest.param(lambda t: t["prediction"].update(field="other_score"), id="prediction"),
        pytest.param(lambda t: t["provenance"]["authoritative_sources"][0].update(path="wrong.md"), id="provenance-path"),
        pytest.param(lambda t: t["provenance"]["authoritative_sources"][0].update(git_blob_sha1="0" * 40), id="provenance-blob"),
        pytest.param(lambda t: t["hashes"].update(construction_code_git_blob_sha1="0" * 40), id="construction-blob"),
        pytest.param(lambda t: t["target_spec_sha256"].__class__ and t.update(target_spec_sha256="0" * 64), id="target-spec-sha"),
        pytest.param(lambda t: t["support"].update(metric_group_key="ticker"), id="support-filter"),
        pytest.param(lambda t: t["target_spec_path"].__class__ and t.update(target_spec_path="missing.json"), id="target-spec-path"),
        pytest.param(lambda t: t["target_id"].__class__ and t.update(target_id="OTHER_TARGET"), id="target-id"),
    ],
)
def test_canonical_target_semantic_mutations_fail_closed(mutation) -> None:
    payload = _payload()
    mutation(payload["target_identity"])
    with pytest.raises(ProspectiveAccessGateBlocked):
        _validate_canonical_target_identity(payload, contract_path=CONTRACT)


def test_model_fingerprint_mutation_is_rejected_by_machine_contract(tmp_path: Path) -> None:
    payload = _payload()
    payload["model"]["fingerprint"] = "0" * 64
    path = tmp_path / CONTRACT.name
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ProspectiveAccessGateBlocked):
        validate_machine_readable_contract(path, sha256_file(path), require_resolved_target=True)


def test_historical_metric_variants_do_not_change_semantic_target_identity(tmp_path: Path) -> None:
    first = _payload()
    second = copy.deepcopy(first)
    first["evaluation"]["historical_point_estimate"] = 0.097554036
    second["evaluation"]["historical_point_estimate"] = 0.099248615
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    first_path.write_text(json.dumps(first, indent=2) + "\n", encoding="utf-8")
    second_path.write_text(json.dumps(second, indent=2) + "\n", encoding="utf-8")
    _validate_canonical_target_identity(first, contract_path=CONTRACT)
    _validate_canonical_target_identity(second, contract_path=CONTRACT)
    assert first["target_identity"] == second["target_identity"]
