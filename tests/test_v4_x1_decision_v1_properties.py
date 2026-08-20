from decision_v1_helpers import *

def test_randomized_invariants_10000_cases(tmp_path, monkeypatch):
    rng = random.Random(20260821)
    for _ in range(10_000):
        n = rng.randint(20, 80)
        frame = _scores(n=n)
        count = rng.randint(0, TARGET_POSITIONS)
        positions = tuple(f"T{i:02d}" for i in rng.sample(range(1, n + 1), count))
        state = ShadowPortfolioState(None, positions)
        plan = plan_decision_v1(_verified_direct(frame), state)
        ranks = dict(zip(frame.ticker, frame.rank_consensus))
        assert len(plan.target_positions) == TARGET_POSITIONS
        assert len(set(plan.target_positions)) == TARGET_POSITIONS
        assert all(ranks[t] <= 20 for t in plan.target_positions)
        assert all((x.rank_consensus or 999) <= 10 for x in plan.buy_intents)
        assert not ({x.ticker for x in plan.buy_intents} & {x.ticker for x in plan.sell_intents})
        unheld = [(t, int(r)) for t, r in ranks.items() if r <= 10 and t not in plan.target_positions]
        buffer = [(t, int(ranks[t])) for t in plan.target_positions if ranks[t] > 10]
        if unheld and buffer:
            assert max(r for _, r in buffer) - min(r for _, r in unheld) < 5


def test_mandatory_exit_replacement_is_symmetric(tmp_path, monkeypatch):
    plan = plan_decision_v1(_verified_direct(), _state([1,2,3,4,5,6,7,8,9,21]))
    buy = next(x for x in plan.buy_intents if x.ticker == "T10")
    sell = next(x for x in plan.sell_intents if x.ticker == "T21")
    assert buy.reason == "MANDATORY_EXIT_REPLACEMENT"
    assert buy.replacement_peer == "T21"
    assert sell.replacement_peer == "T10"


def test_true_cash_vacancy_buy_is_unconditional(tmp_path, monkeypatch):
    state = ShadowPortfolioState("2026-08-20", tuple(f"T{i:02d}" for i in range(1,10)))
    plan = plan_decision_v1(_verified_direct(), state)
    buy = next(x for x in plan.buy_intents if x.ticker == "T10")
    assert buy.reason == "FILL_VACANCY_TOP10"
    assert buy.replacement_peer is None

@pytest.mark.parametrize("mutation,error", [
    (lambda m: m.__setitem__("schema_version", "v3"), "UPSTREAM_SCHEMA_CHANGED"),
    (lambda m: m["model_bundle"].__setitem__("manifest_sha256", "bad"), "MODEL_BUNDLE_CHANGED"),
    (lambda m: m["freshness"].__setitem__("model_freeze_observed_by", "2026-08-21T00:00:00+00:00"), "FREEZE_BOUNDARY_CHANGED"),
    (lambda m: m["science"]["frozen_scientific_git_blobs"].__setitem__("src/idx_trade/ranking_v4_3_features.py", "bad"), "SCIENTIFIC_BLOB_CHANGED"),
    (lambda m: m.__setitem__("rows", 29), "ROW_COUNT_INVALID"),
])
def test_additional_manifest_tampering_fails_closed(tmp_path, monkeypatch, mutation, error):
    manifest, _ = _write_artifact(tmp_path, monkeypatch, manifest_mutator=mutation)
    with pytest.raises(DecisionV1Error, match=error):
        verify_v4_x1_score_artifact(manifest)


def test_forged_verified_score_session_without_private_token_is_rejected():
    frame = _scores()
    forged = VerifiedScoreSession(
        session_date="2026-08-21",
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=Path("x"),
        artifact_sha256="x",
        manifest_path=Path("y"),
        manifest_sha256="y",
        scores=frame,
        alpha_tie_rows=0,
        _verification_token=object(),
    )
    with pytest.raises(DecisionV1Error, match="VERIFIED_SCORE_SESSION_REQUIRED"):
        plan_decision_v1(forged, ShadowPortfolioState.empty())


def test_shadow_state_input_is_not_mutated():
    state = ShadowPortfolioState("2026-08-20", ("T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09", "T21"))
    before = state.positions
    plan_decision_v1(_verified_direct(), state)
    assert state.positions == before


def test_alpha_tie_diagnostic_and_ticker_tiebreak(tmp_path, monkeypatch):
    frame = _scores()
    frame.loc[1, ["alpha_h5", "alpha_h10", "alpha_consensus"]] = frame.loc[0, ["alpha_h5", "alpha_h10", "alpha_consensus"]].to_numpy()
    manifest, _ = _write_artifact(tmp_path, monkeypatch, frame)
    verified = verify_v4_x1_score_artifact(manifest)
    assert verified.alpha_tie_rows == 2
    assert verified.scores.iloc[:2]["ticker"].tolist() == ["T01", "T02"]
