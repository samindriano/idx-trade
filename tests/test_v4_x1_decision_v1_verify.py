from decision_v1_helpers import *

def test_frozen_config_hash_matches_patch():
    path = Path(__file__).parents[1] / "config" / "v4_x1_decision_v1.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_CONFIG_SHA256
    payload = verify_frozen_config(path)
    assert payload["replacement_rank_gap_min"] == 5
    assert payload["investment_policy"] == "NO_DISCRETIONARY_CASH_OR_MARKET_TIMING"
    assert payload["full_nav_investment_required"] is False
    assert payload["residual_cash_allowed"] is True


def test_config_mutation_fails(tmp_path):
    source = Path(__file__).parents[1] / "config" / "v4_x1_decision_v1.json"
    payload = json.loads(source.read_text())
    payload["replacement_rank_gap_min"] = 4
    changed = tmp_path / "config.json"
    changed.write_text(json.dumps(payload))
    with pytest.raises(DecisionV1Error, match="CONFIG_SHA_MISMATCH"):
        verify_frozen_config(changed)


def test_score_artifact_verification_happy_path(tmp_path, monkeypatch):
    manifest, _ = _write_artifact(tmp_path, monkeypatch)
    verified = verify_v4_x1_score_artifact(manifest)
    assert verified.session_date == "2026-08-21"
    assert verified.scores["rank_consensus"].tolist() == list(range(1, 31))


@pytest.mark.parametrize("field,value,error", [
    ("status", "FAILED", "UPSTREAM_NOT_DONE"),
    ("model_id", "WRONG", "MODEL_ID_MISMATCH"),
    ("generation", "V4-X1", "GENERATION_MISMATCH"),
    ("model_fingerprint", "bad", "FINGERPRINT_MISMATCH"),
])
def test_score_manifest_lineage_guards(tmp_path, monkeypatch, field, value, error):
    def mutate(m): m[field] = value
    manifest, _ = _write_artifact(tmp_path, monkeypatch, manifest_mutator=mutate)
    with pytest.raises(DecisionV1Error, match=error):
        verify_v4_x1_score_artifact(manifest)


def test_score_manifest_science_guard(tmp_path, monkeypatch):
    def mutate(m): m["science"]["consensus_formula"] = "changed"
    manifest, _ = _write_artifact(tmp_path, monkeypatch, manifest_mutator=mutate)
    with pytest.raises(DecisionV1Error, match="CONSENSUS_FORMULA_CHANGED"):
        verify_v4_x1_score_artifact(manifest)


def test_score_manifest_outcome_guard(tmp_path, monkeypatch):
    def mutate(m): m["guards"]["protected_outcome_accessed"] = True
    manifest, _ = _write_artifact(tmp_path, monkeypatch, manifest_mutator=mutate)
    with pytest.raises(DecisionV1Error, match="UPSTREAM_GUARD_CHANGED"):
        verify_v4_x1_score_artifact(manifest)


def test_artifact_tamper_fails_sha(tmp_path, monkeypatch):
    manifest, artifact = _write_artifact(tmp_path, monkeypatch)
    artifact.write_bytes(b"tampered")
    with pytest.raises(DecisionV1Error, match="ARTIFACT_SHA_MISMATCH"):
        verify_v4_x1_score_artifact(manifest)


def test_duplicate_ticker_rejected_even_with_matching_manifest(tmp_path, monkeypatch):
    frame = _scores()
    frame.loc[1, "ticker"] = frame.loc[0, "ticker"]
    manifest, _ = _write_artifact(tmp_path, monkeypatch, frame)
    with pytest.raises(DecisionV1Error, match="DUPLICATE_TICKER"):
        verify_v4_x1_score_artifact(manifest)


def test_noncontiguous_rank_rejected(tmp_path, monkeypatch):
    frame = _scores()
    frame.loc[10, "rank_consensus"] = 99
    manifest, _ = _write_artifact(tmp_path, monkeypatch, frame)
    with pytest.raises(DecisionV1Error, match="RANK_NOT_CONTIGUOUS"):
        verify_v4_x1_score_artifact(manifest)


def test_consensus_mismatch_rejected(tmp_path, monkeypatch):
    frame = _scores()
    frame.loc[0, "alpha_consensus"] -= 0.1
    manifest, _ = _write_artifact(tmp_path, monkeypatch, frame)
    with pytest.raises(DecisionV1Error, match="CONSENSUS_MISMATCH"):
        verify_v4_x1_score_artifact(manifest)


def test_rank_order_mismatch_rejected(tmp_path, monkeypatch):
    frame = _scores()
    frame.loc[0, "rank_consensus"], frame.loc[1, "rank_consensus"] = 2, 1
    manifest, _ = _write_artifact(tmp_path, monkeypatch, frame)
    with pytest.raises(DecisionV1Error, match="RANK_ORDER_MISMATCH"):
        verify_v4_x1_score_artifact(manifest)
