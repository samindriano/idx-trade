# IDX Trade — Current Status

Date: 2026-08-11 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use the
project ledgers and newest dated checkpoints. If older text conflicts, this
file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- alpha architecture search: **CLOSED**;
- cumulative viewed historical alpha candidates: `17`;
- final historical-development ranker:
  `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- final V3-B refit: **FROZEN SUCCESSFULLY**;
- final model SHA-256:
  `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`;
- exact 33-feature order SHA-256:
  `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- Path Risk V1 / PR-001: **CLOSED — `PATH_RISK_A_DISCOVERY_FAIL_CLOSE`**;
- Path Risk V2 / PR-002 + PR-003: **CLOSED — `PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`**;
- Path Risk V2 winner: **none**;
- Path Risk F5/F6: **SEALED / NOT NEEDED AFTER V2 FAIL_CLOSE**;
- post-2026-07-31 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- calibration / alpha+risk integration / execution-PnL / Kelly / paper/live:
  not authorized automatically.

## Final alpha ranker

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

V3-B is exact V2 `HGB_XS_MARKET` information plus eight frozen causal
Structure-Lite geometry features. It was the only V3 survivor and later passed
its one-shot V2F5/V2F6 late-development confirmation. V4-A Participation,
V4-B Price Path and V4-C Cross-Sectional Context produced no survivor.

Final refit facts:

- rows/tickers/sessions: `292,633 / 737 / 20..1250`;
- training table SHA-256:
  `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe`;
- model SHA-256:
  `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`;
- manifest SHA-256:
  `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9`;
- sessions `1225..1250` were training-only;
- no new historical performance metric was computed in final refit;
- fresh-forward outcomes were not accessed.

Controlling checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REFIT_RUNTIME_RESULT.md`

## Path Risk V1 — closed

PR-001 tested q75 pre-resolution adverse-excursion regression using the exact
33 causal features. It showed useful ordering diagnostics but failed the
frozen proper-scoring gate:

- F1/F2/F3 relative pinball improvement:
  `+0.004267 / +0.011273 / +0.014061`;
- F4: `-0.033463`;
- median improvement: about `+0.00777`, below the `+0.02` gate;
- q25 and worst-fold gates failed;
- Spearman and Q5-Q1 adverse-excursion ordering gates passed.

Frozen verdict:

`PATH_RISK_A_DISCOVERY_FAIL_CLOSE`

PR-001 remains permanently viewed and cannot be rescued/reinterpreted as a
winner.

Controlling files:

- `docs/PATH_RISK_V1_LEDGER.md`;
- `docs/checkpoints/2026-08-10_PATH_RISK_V1_DISCOVERY_RESULT_FAIL_CLOSE.md`.

## Path Risk V2 — closed

Frozen specification:

`docs/PATH_RISK_V2_SPEC.md`

Spec Git blob:

`6d171d3f492b9cd15e0a176428eb9d6e4f6c20c5`

V2 tested exactly two preregistered candidates on Path Risk development folds
F1-F4:

1. PR-002 `PATH-RISK-V2-STOP-H10-HGB-002`
   - exact 33 features;
   - direct HGB `P(stop touch within H10)`.
2. PR-003 `PATH-RISK-V2-DISCRETE-CR-HGB-003`
   - exact 33 features + deterministic horizon step H1..H10;
   - multiclass CONTINUE/STOP/TP discrete hazard model;
   - comparable output = H10 stop cumulative incidence.

The one authorized F1-F4 discovery run completed on code HEAD
`9378943bde44b33e311bec1e1daf38ca5cd9b5d3` after a clean preflight of
`471 passed, 0 failed, 3 warnings`.

Frozen result:

`PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`

Winner: none.

Both PR-002 and PR-003 showed positive risk ordering/discrimination:

- ROC-AUC > 0.5 on all folds;
- Q5-Q1 stop-touch spread positive on all folds;
- both improved log loss versus the fold-specific V3-B alpha-only stop-risk
  mapping on all folds.

But both failed the decision-critical proper-scoring comparison against the
training stop-touch base-rate comparator:

- PR-002 nonnegative log-loss improvement vs base: `0/4`;
- PR-003 nonnegative log-loss improvement vs base: `0/4`;
- PR-002 nonnegative Brier improvement vs base: `1/4`;
- PR-003 nonnegative Brier improvement vs base: `0/4`.

Therefore neither candidate is eligible for promotion. Their useful ordering
signal may not be reinterpreted post hoc as a validated V2 probability/risk
layer.

Artifact hashes:

- candidate metrics:
  `c9e5ea87f66252461bebff2bcbfe91d044618166142b6e9e5de48290ffc22f3c`;
- comparator metrics:
  `c99c89e65710c9aaa2fb95eab57d134885b8054d68f13445b1cae44f4bf06da6`;
- predictions:
  `2fa1204698c207920b6c439eebc5e6123d3b24497c6432e2ba3a23db1b16a7b3`;
- summary:
  `67689476b1cad17b0f39144bcce82e01a00c3f62e30a991ce2c381c5f7b0f332`.

Controlling files:

- `docs/PATH_RISK_V2_LEDGER.md`;
- `docs/checkpoints/2026-08-11_PATH_RISK_V2_DISCOVERY_RESULT_FAIL_CLOSE.md`.

Consequences:

- PR-002 and PR-003 are permanently viewed / closed;
- no Path Risk F5/F6 access is needed or authorized;
- no PR-004 rescue is pre-authorized;
- any future Path Risk V3 must be a genuinely new preregistered hypothesis
  family, not a retune/recalibration/relabeling of V1/V2;
- no risk-veto, alpha reranking, sizing, or alpha+risk integration exists.

## Fresh-forward independent alpha verdict

The final V3-B ranker is independently evaluated only on the first exact
**100 consecutive H10-mature official signal sessions strictly after
2026-07-31**.

Daily outcome-blind operation may record data provenance, exact V3-B features,
scores/ranks, model/artifact fingerprints and maturity state. It must not
expose realized TP/SL, PR-AUC, ROC-AUC, Q5-Q1 performance, realized return or
PnL before the one-shot outcome-access boundary.

Before future outcome access, the exact block and source snapshots must be
hash-pinned, then `FORWARD_OUTCOME_ACCESS_STARTED` must be written atomically
before outcomes are loaded.

## Orchestration execution policy — refreshed 2026-08-11

The project uses **parallel-first LIGHT orchestration for meaningful work** to
reduce wall-clock time with Luna xhigh while preserving frozen research
boundaries.

- MAIN identifies the ready execution frontier before substantial work;
- independent ready scopes should be spawned before MAIN duplicates them;
- `LIGHT` = default for roughly 2–3 useful independent workstreams;
- `HEAVY` = 3–6 independent critical-path scopes or decision-changing review;
- `DIRECT` = small/inherently sequential work;
- dependent scientific experiments remain sequential even when supporting
  implementation/tests/audit work can run concurrently;
- `Luna xhigh` remains MAIN/worker default; `Sol High` remains a bounded
  decision-changing escalation.

The Path Risk V2 hardening milestone demonstrated this with five parallel Luna
workers before the serialized evidence-producing discovery run.

## Immediate next action

Path Risk V2 is closed. Do not automatically open F5/F6 or create PR-004.

Current research-safe priorities are:

1. preserve the final V3-B ranker and continue outcome-blind fresh-forward
   operation/accumulation under the existing 100-session contract;
2. keep Path Risk inactive unless a separately researched and preregistered V3
   hypothesis family is explicitly authorized;
3. keep probability calibration, alpha+risk integration, execution-PnL, Kelly,
   paper/live and forward realized-outcome access blocked unless separately
   authorized.

## Hard boundary

Do not:

- reopen or modify the final V3-B alpha architecture;
- rescue/rewrite PR-001, PR-002, or PR-003;
- add PR-004 as an immediate post-result rescue;
- access Path Risk F5/F6 after the V2 fail-close;
- reinterpret ranking diagnostics as a probability-model PASS;
- access or summarize post-2026-07-31 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED` now;
- create risk-veto, reranking, position-sizing or alpha+risk integration rules;
- start execution/PnL/Kelly/paper/live automatically.
