# Ranking V3-A Recency — Independent Result Review

Date: 2026-08-10 (Asia/Jakarta)
Status: **RANKING_V3_A_RECENCY_REVIEW_PASS — HYPOTHESIS CLOSED, V2 CONTROL RETAINED**

## Reviewed result

Reviewed source result:

- branch: `research/idx-ranking-v2-spec-v1`;
- final result documentation commit: `93e2e72fe3fa405376c16682f522776f8f071cd4`;
- implementation code commit: `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f`;
- result checkpoint: `docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_F1_F4_RESULT.md`;
- deterministic outcome: `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`.

The run is accepted as valid historical-development evidence.

## Reproducibility and safety review

Accepted facts:

- full repo pytest: `240 passed, 3 warnings`;
- exact prepared cache and manifest hashes matched the frozen contract;
- exact V2 `HGB_XS_MARKET` historical reference artifacts were hash verified;
- control-equivalence: PASS on `84,732` V2F1-V2F4 rows;
- row-level control score max absolute difference: `0.0`;
- required control metric max absolute difference: `0.0`;
- V2F5/V2F6 were not scored, loaded or summarized for V3-A;
- reserved post-2026-07-31 V2 forward outcomes were not accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written.

The Windows `core.autocrlf` working-tree Git-blob mismatch was handled by reconstructing a runtime-only copy from the exact committed blob. This did not change research semantics or source code and is accepted as an engineering/provenance handling detail, not a model-result issue.

## Candidate review

### H=252

- absolute discovery sanity: PASS;
- paired promotion: FAIL;
- verdict: `KEEP_DIAGNOSTIC`;
- paired median PR-delta improvement: `-0.00015115912021376743`;
- q25 paired PR improvement: `-0.006956944711256102`;
- worst paired PR improvement: `-0.009192921024824163`;
- PR not below control: `2/4` folds;
- median ROC change: `-0.0038333101945575154`;
- median Q5-Q1 change: `+0.0036039448019138665`.

Interpretation: H252 improves PR separation in V2F1/V2F2 but reverses in V2F3/V2F4. The small aggregate/median picture is not robust enough to justify promotion.

### H=504

- absolute discovery sanity: PASS;
- paired promotion: FAIL;
- verdict: `KEEP_DIAGNOSTIC`;
- paired median PR-delta improvement: `+0.000056855210580852855`;
- q25 paired PR improvement: `-0.009973481859093858`;
- worst paired PR improvement: `-0.03453010158520309`;
- PR not below control: `2/4` folds;
- median ROC change: `-0.0016855094410250238`;
- median Q5-Q1 change: `+0.005210425088733955`.

The V2F4 deterioration is especially material: PR-delta falls from control `0.0382948851` to `0.0037647835`, while ROC falls from `0.5128270` to `0.4787723`. A slightly positive median paired PR improvement therefore cannot support promotion.

## Research conclusion

The bounded hypothesis tested was:

> Can deterministic exponential recency weighting alone improve robustness while holding the V2 target, universe, 25 features, HGB architecture, hyperparameters and ranking semantics fixed?

Within the preregistered H=252/H=504 experiment, the answer is **no**.

Do not rescue this result by trying additional half-lives, rolling windows, clipping, class weights or alternative decay forms under `V3-A-RECENCY-V1`. Such changes require a materially new future hypothesis and are not justified by the current evidence.

The exact uniform V2 `HGB_XS_MARKET` remains the V3 research control/reference.

This does not imply temporal drift is absent. It only rejects the tested solution that simple deterministic recency weighting is a robust improvement.

## Implication for the V3 roadmap

Close V3-A and proceed to the next independently specified hypothesis:

**V3-B — STRUCTURE-LITE**.

The reason to proceed with Structure-Lite rather than rescue recency is that it tests a new information representation rather than another weighting knob. The legacy support/resistance archive provides useful geometry inspiration, but only causal numeric geometry may be reused; its outcome-conditioned scoring layer remains prohibited.

V2F5/V2F6 stay sealed for the eventual final-V3 late-development confirmation. They must not be opened for Structure-Lite discovery.

## Authorization boundary

AUTHORIZED NEXT:

- draft/freeze the V3-B Structure-Lite research specification only;
- inspect existing causal feature/legacy support-resistance code for definition design;
- define a compact fixed structure bundle and exact computation/provenance/equivalence contracts before outcomes;
- use V2F1-V2F4 as the eventual discovery fold set only after a separate run authorization.

NOT AUTHORIZED:

- V3-B fitting/scoring before its spec is frozen and reviewed;
- any V2F5/V2F6 scoring;
- any reserved V2 fresh-forward outcome access;
- changing V3-A and rerunning recency variants;
- V3-C or later outcome work;
- probability calibration, Stage 6, IDX-VAL-002, execution-PnL, Kelly, paper/live trading, or main merge.
