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
- Path Risk V2: **FROZEN + IMPLEMENTED PRE-OUTCOME**;
- Path Risk V2 PR-002/PR-003: **RESERVED / UNVIEWED**;
- Path Risk F5/F6: **SEALED**;
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

## Path Risk V2 — implemented, not yet run

Frozen specification:

`docs/PATH_RISK_V2_SPEC.md`

Spec Git blob:

`6d171d3f492b9cd15e0a176428eb9d6e4f6c20c5`

Exactly two V2 candidates exist:

1. PR-002 `PATH-RISK-V2-STOP-H10-HGB-002`
   - exact 33 features;
   - direct HGB `P(stop touch within H10)`.
2. PR-003 `PATH-RISK-V2-DISCRETE-CR-HGB-003`
   - exact 33 features + deterministic horizon step H1..H10;
   - multiclass CONTINUE/STOP/TP discrete hazard model;
   - comparable output = H10 stop cumulative incidence.

Binary risk endpoint:

- positive: `SL_FIRST`, `AMBIGUOUS_SAME_BAR`;
- negative: `TP_FIRST`, `NO_BARRIER_HIT`.

F1-F4 are already-consumed Path Risk development knowledge and are the only
folds allowed in V2 discovery. V2 reuses the immutable V1 joined model table:

- SHA-256:
  `b66fc7e40f18940ae9db418331a421e0f36d23b86597500b1d3ba73a8e3777fe`;
- rows: `252,198`;
- max signal session: `984`.

The V2 runner additionally compares both candidates against:

- training stop-touch base rate;
- a fold-specific V3-B alpha-only -> stop-risk logistic mapping.

This checks whether a separate risk layer adds information beyond alpha itself.
No final all-history alpha model is used as a historical comparator.

Implementation:

- `src/idx_trade/path_risk_v2.py`;
- `src/idx_trade/path_risk_v2_discovery_run.py`;
- `tests/test_path_risk_v2.py`;
- `tests/test_path_risk_v2_discovery_run.py`.

Ledger/checkpoint:

- `docs/PATH_RISK_V2_LEDGER.md`;
- `docs/checkpoints/2026-08-11_PATH_RISK_V2_IMPLEMENTED_PRE_OUTCOME.md`.

At this point:

- PR-002 result viewed: `false`;
- PR-003 result viewed: `false`;
- real V2 model fit/metrics: not run;
- F5/F6: sealed;
- no calibration/risk-veto/alpha+risk integration exists.

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

The project now uses **parallel-first LIGHT orchestration for meaningful work**
to reduce wall-clock time with Luna xhigh while preserving all frozen research
boundaries.

- MAIN must build the execution frontier before substantial implementation;
- independent ready scopes should be spawned before MAIN duplicates them;
- `LIGHT` = default for roughly 2–3 useful independent workstreams;
- `HEAVY` = 3–6 independent critical-path scopes or decision-changing review;
- `DIRECT` = small/inherently sequential work; substantial DIRECT requires a
  reason that workers would not materially shorten the critical path;
- dependent scientific experiments remain sequential even when supporting
  implementation/tests/audit work can run concurrently;
- `Luna xhigh` remains the MAIN/worker default; `Sol High` remains a bounded
  decision-changing escalation, not a persistent default.

For the immediate Path Risk V2 milestone, import/full-suite verification and
independent frozen-spec/seal audit may run in parallel when isolated. The one
evidence-producing PR-002/PR-003 F1-F4 discovery execution remains serialized
after preflight because its result controls the next scientific decision.

Controlling orchestration documents:

- `AGENTS.md`;
- `docs/ORCHESTRATION.md`;
- `coordination/TEAM_STATUS.md`;
- `coordination/TASK_REGISTRY.md`.

## Immediate next action

Run the full repository test suite locally after pulling the latest branch. If
it passes and current-checkout import resolution is correct, execute exactly one
Path Risk V2 PR-002/PR-003 F1-F4 development run using:

`coordination/handoffs/IDX-PATH-RISK-V2-DISCOVERY-F1-F4-RUN.md`

Return the result to ChatGPT. Do not touch F5/F6 after the run even if a winner
is selected; a separate one-shot confirmation specification is required.

## Hard boundary

Do not:

- reopen or modify the final V3-B alpha architecture;
- rescue/rewrite PR-001;
- add PR-004 after seeing PR-002/PR-003;
- access Path Risk F5/F6 during V2 discovery;
- use F5/F6 to choose between PR-002 and PR-003;
- access or summarize post-2026-07-31 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED` now;
- create risk-veto, reranking, position-sizing or alpha+risk integration rules;
- start execution/PnL/Kelly/paper/live automatically.
