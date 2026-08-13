# Checkpoint — Ranking V3 Recency Specification Review Pass

Date: 2026-08-10 (Asia/Jakarta)

Status: **RANKING_V3_RECENCY_SPEC_REVIEW_PASS_WITH_CORRECTIONS**

## Reviewed inputs

- branch: `research/idx-ranking-v2-spec-v1`;
- submitted review HEAD: `d022ad25430a79661e796e929f3dfd7d81fb3ec5`;
- frozen spec: `docs/RANKING_V3_RECENCY_SPEC_V1.md`;
- reported spec SHA-256: `53c5bc3e90af12fea62a73815e1e85352e836d69938ce0e9287437a52c1d58fa`;
- spec Git blob: `b6e055ad4fe5e964e29892ef2bd0d9b8a4921c83`;
- ledger: `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`;
- roadmap: `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`;
- legacy lessons: `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`;
- runtime note: `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
- frozen V2 champion/forward contract and existing V2 candidate semantics.

No V3 recency outcome, V2F5/V2F6 recency score, or reserved post-2026-07-31 V2 forward outcome was used in this review.

## Review decision

The V3-A recency hypothesis is accepted for a bounded first outcome-bearing development run after applying the independent review addendum:

`docs/RANKING_V3_RECENCY_SPEC_REVIEW_ADDENDUM_V1.md`

Accepted core choices:

- exact `HGB_XS_MARKET` V2 control;
- exact 25 V2 features and H10 semantics;
- two and only two recency variants, H=252 and H=504 official sessions;
- deterministic exponential weights;
- fold-local mean-one normalization;
- V2F1-V2F4 discovery only;
- original discovery robustness/pairwise gates and deterministic tie rule;
- permanent candidate ledger;
- reserved post-2026-07-31 V2 forward outcomes remain off-limits.

## Controlling pre-outcome corrections

1. **Do not use V2F5/V2F6 for V3-A.** They remain sealed for the future final V3 architecture after the bounded hypothesis ladder and at most one preregistered integration experiment.
2. **Remove the V3-A late-confirmation gate.** Recency promotion/kill is based only on the frozen V2F1-V2F4 discovery rules.
3. **Add a mandatory exact-control equivalence gate.** The new uniform-control path must reproduce the existing frozen V2 HGB_XS_MARKET F1-F4 score/metric artifacts before recency results are accepted.
4. Future absolute ROC gates must use `ROC-AUC > 0.50`; merely positive ROC is meaningless.
5. The phrase `V4 discovery fold behavior` in the submitted spec means `V3D4 = V2F4`.
6. Mean-one weight verification uses strict float64 tolerance, not bitwise decimal equality.

The original spec remains immutable pre-review evidence; the addendum controls conflicts. The first V3-A run manifest must pin both.

## Authorization now

Authorized after local pull/fetch:

- implement the exact recency-weighting path and tests;
- verify all frozen input/spec/addendum hashes;
- run the uniform V2 control on V2F1-V2F4;
- prove control equivalence to immutable existing V2 artifacts;
- only if equivalence passes, run H=252 and H=504 on V2F1-V2F4;
- compute the frozen discovery metrics and deterministic verdict;
- update ledger ordinals 001-003 and cumulative evaluated count;
- record immutable artifacts/hashes, runtime profile, implementation checkpoint, result handoff, and continuity state;
- stop for ChatGPT review.

Prefer a simple deterministic sequential/reference runner for this 3-candidate x 4-fold workload unless profiling proves bounded concurrency materially useful. Do not add optimization complexity merely because it is available.

## Not authorized

- V2F5/V2F6 recency scoring;
- any post-2026-07-31 V2 forward outcome access;
- writing `FORWARD_OUTCOME_ACCESS_STARTED`;
- modifying V2 or recency candidate definitions/gates after outcomes;
- Structure-Lite, Regime, Sector-Relative, True-Ranking, or integration outcome runs;
- Stage 6, probability calibration, `IDX-VAL-002`, execution-PnL, Kelly sizing, paper/live trading, or merge to `main`.

## Stop rule

Once the V3-A F1-F4 control + H252 + H504 run and deterministic ledger/verdict are complete, stop. Do not proceed automatically to V3-B or consume V2F5/V2F6.
