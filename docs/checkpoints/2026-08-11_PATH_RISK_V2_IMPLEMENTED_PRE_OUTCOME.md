# Path Risk V2 — Implemented Pre-Outcome

Date: 2026-08-11 (Asia/Jakarta)

Status: **IMPLEMENTED / FROZEN PRE-OUTCOME — REAL PR-002/PR-003 RUN NOT YET EXECUTED**

## Scope

Path Risk V2 has been frozen and implemented after V1 closed as
`PATH_RISK_A_DISCOVERY_FAIL_CLOSE`.

V2 is not a rescue of PR-001.  It contains exactly two new candidates:

- PR-002 `PATH-RISK-V2-STOP-H10-HGB-002` — direct H10 stop-touch probability;
- PR-003 `PATH-RISK-V2-DISCRETE-CR-HGB-003` — discrete H1..H10
  CONTINUE/STOP/TP competing-risk model whose comparable output is H10 stop CIF.

Frozen spec:

`docs/PATH_RISK_V2_SPEC.md`

Spec Git blob:

`6d171d3f492b9cd15e0a176428eb9d6e4f6c20c5`

## Implementation

Created:

- `src/idx_trade/path_risk_v2.py`;
- `src/idx_trade/path_risk_v2_discovery_run.py`;
- `tests/test_path_risk_v2.py`;
- `tests/test_path_risk_v2_discovery_run.py`;
- `docs/PATH_RISK_V2_LEDGER.md`.

The discovery runner is physically bounded by its only outcome-bearing input:

`path_risk_v1_discovery_model_table.parquet`

SHA-256:

`b66fc7e40f18940ae9db418331a421e0f36d23b86597500b1d3ba73a8e3777fe`

That artifact contains only the already-viewed F1-F4 Path Risk development
population and has maximum signal session `984`.  The V2 runner does not load
raw H10 labels or the source price panel and therefore cannot materialize F5/F6
through those inputs.

Official calendar SHA-256:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`.

Exact 33-feature order SHA-256 remains:

`100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`.

## Runtime engineering review

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` was read before V2
implementation as required.

Relevant recommendations applied:

1. **Reuse immutable transformations** — V2 reuses the frozen V1 joined model
   table instead of rebuilding adverse-excursion targets/path evidence.
2. **Column-projected Parquet read** — the runner reads only identity/outcome
   diagnostics plus the exact 33 features.
3. **Vectorized expansion** — PR-003 person-period rows are created with NumPy
   repeat/cumulative-index operations rather than per-row DataFrame appends.
4. **Profile before parallelizing** — V2 discovery is intentionally sequential
   and records comparator, PR-002, PR-003 and fold wall times.  No unrestricted
   process/fold parallelism is introduced before measuring the new bottleneck.

This is expected to remove the ~10-minute V1 target-construction bottleneck;
PR-003 multiclass expansion/fit is the likely new cost center and must be
measured rather than assumed.

## Candidate/comparator boundary

PR-002 and PR-003 use the exact 33 causal V3-B market/setup features.  PR-003
adds only deterministic `path_horizon_step`.

The final V3-B alpha score is not a candidate feature.  Instead the runner
builds a fold-specific alpha-only comparator using the exact V3-B architecture
fit only on each outer training fold's TP_FIRST/SL_FIRST rows, then maps its raw
score to stop-touch probability with a one-dimensional training-only logistic
mapping.

This makes incremental information beyond alpha part of the frozen V2 gate.

## Outcome state

At this checkpoint:

- PR-002 result viewed: `false`;
- PR-003 result viewed: `false`;
- V2 candidate models fitted on real data: `false`;
- V2 real performance metrics computed: `false`;
- Path Risk F5/F6 accessed: `false`;
- post-2026-07-31 fresh-forward outcomes accessed: `false`;
- `FORWARD_OUTCOME_ACCESS_STARTED` written: `false`;
- final V3-B ranker modified: `false`;
- risk-veto / alpha+risk integration created: `false`.

## Next boundary

Before a real V2 F1-F4 development run:

1. pull the exact latest branch;
2. verify current-checkout `src` import resolution;
3. run the full pytest suite with zero failures;
4. verify the V1 model-table/calendar/spec hashes;
5. execute the V2 discovery runner exactly once in a new output directory;
6. stop and return the result for ChatGPT review/documentation.

F5/F6 remain prohibited even if a V2 winner is selected.  A separate
preregistered confirmation step will be required.
