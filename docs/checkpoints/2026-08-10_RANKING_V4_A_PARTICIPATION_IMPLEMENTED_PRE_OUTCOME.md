# Ranking V4-A Participation Quality — Implemented Pre-Outcome

Date: 2026-08-10 (Asia/Jakarta)
Status: **IMPLEMENTATION PASS / LOCAL OUTCOME-BLIND CACHE AUDIT NEXT / MODEL OUTCOME RUN NOT YET AUTHORIZED**

## Decision state

Family `V4-A-PARTICIPATION-V1` is now specified, independently reviewed and implemented through the pre-outcome tooling stage.

The first-pass candidate set is frozen as:

- ordinal `012`: `V4-A-PARTICIPATION-V1-CONTROL-012` — exact final V3-B 33-feature HGB control;
- ordinal `013`: `V4-A-PARTICIPATION-V1-IMPACT-013` — exact V3-B plus the three-feature A1 Impact/Absorption bundle;
- ordinal `014`: `V4-A-PARTICIPATION-V1-PERSIST-DIRECTION-014` — exact V3-B plus the four-feature A2 Persistent Directional Participation bundle.

No first-pass A1+A2 integration candidate exists. One integration is allowed later only if both 013 and 014 independently pass their frozen gates.

No V4-A candidate outcome has been viewed. The V4 evaluated-candidate count remains `0`; cumulative historical evaluated-candidate count remains `9`.

## Frozen controlling design

Seven-family arena:

`docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`

V4-A experiment map:

`docs/RANKING_V4_A_PARTICIPATION_QUALITY_EXPERIMENT_MAP_V1.md`

Frozen exact V4-A spec:

`docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`

Frozen spec Git blob:

`e32fa69596291f418ae797613da219bd0d3cf69c`

Independent review addendum:

`docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_REVIEW_ADDENDUM_V1.md`

Hypothesis accounting:

`docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`

## Implemented code

### Feature construction

`src/idx_trade/research_v4_participation.py`

A1 exact appended features:

1. `v4a_range_impact_logrel20`;
2. `v4a_close_impact_logrel20`;
3. `v4a_high_range_impact_fraction_5`.

A2 exact appended features:

1. `v4a_value_persistence_fraction_5`;
2. `v4a_value_acceleration_log_5v20`;
3. `v4a_signed_value_5`;
4. `v4a_signed_value_20`.

The implementation uses official-session adjacency, fails closed for exact-five-session paths across a missing official row, treats zero regular-market value as invalid for the affected per-row participation quantity rather than as zero participation evidence, rejects label/outcome columns at the feature-builder boundary, and does not require historical Open.

### Candidate/model contract

`src/idx_trade/ranking_v4_participation.py`

- exact V3-B 33-feature prefix is preserved;
- A1 model has 36 total feature columns;
- A2 model has 37 total feature columns;
- exact frozen V3-B HGB/imputer architecture is reused;
- model-family/hyperparameter/threshold search is absent;
- session `1225+` is hard-blocked from historical V4-A implementation;
- first-pass candidate set/order is hard-coded as control+A1+A2 only.

### Outcome-independent cache preparation

`src/idx_trade/ranking_v4_participation_prepare.py`

The prepare path pins the frozen signal-panel/calendar identities and exact V3-B late-development cache/manifest identities, preserves all original V3-B cache columns, appends the seven V4-A columns, and writes a manifest with:

- `outcome_metrics_computed=false`;
- `fresh_forward_accessed=false`;
- `post_1224_materialized=false`;
- `integration_candidate_materialized=false`.

### Atomic first-pass model runner

`src/idx_trade/ranking_v4_participation_run.py`

The runner is implemented but **not yet authorized for execution**.

When separately authorized after the feature-cache audit, one invocation will:

1. fit/score exact V3-B control across V2F1..V2F6;
2. prove exact control equivalence against frozen V3-B F1-F6 reference artifacts at `1e-12`;
3. fit/score A1 and A2 without mid-run adaptation;
4. apply the frozen per-challenger promotion gates;
5. emit top-decile overlap diagnostics;
6. stop without creating an integration candidate.

### Outcome-blind feature audit

`src/idx_trade/ranking_v4_participation_audit.py`

The audit physically projects only identity, existing V3-B participation-context and V4-A feature columns from the prepared Parquet. It does not load `binary_target` or label/outcome columns.

It reports:

- missing/finite coverage;
- distribution summaries;
- constant/low-coverage features;
- Spearman redundancy within V4-A and versus existing V3-B volume/value context;
- any absolute correlation `>=0.95`;
- explicit fresh-forward/session-boundary flags.

### CLI / local handoff

- `src/idx_trade/ranking_v4_participation_cli.py`;
- `coordination/handoffs/IDX-RANKING-V4-A-PARTICIPATION-CACHE-AUDIT.md`.

The handoff requires SHA-based resolution/verification of frozen local artifacts and authorizes only prepare + outcome-blind audit. It explicitly prohibits the model `run` subcommand.

## Tests / CI

Implementation commit validated by CI:

`62f7f1e730ab2ae23037e085fd59e59d2324242a`

GitHub Actions full repository pytest:

- `337 passed`;
- `0 failed`;
- `2062 warnings` (existing/deprecation-warning volume, not test failures);
- pytest duration `17.13s` on the CI run.

Focused tests cover:

- exact V3-B feature-prefix preservation;
- exact A1/A2 feature counts/order;
- frozen HGB parameters;
- no Open dependency;
- causal centered impact normalization;
- flat and directional participation behavior;
- participation acceleration;
- official-session gap fail-closed behavior;
- outcome-column rejection;
- future-row append invariance;
- session-1225 boundary;
- first-pass candidate-set/integration prohibition;
- frozen promotion gate behavior;
- exact control-equivalence enforcement;
- outcome-blind audit column projection.

## Next permitted action

Run only the Windows-local procedure in:

`coordination/handoffs/IDX-RANKING-V4-A-PARTICIPATION-CACHE-AUDIT.md`

That procedure must stop after returning the outcome-blind cache/audit report.

A separate ChatGPT review/checkpoint is required before any V4-A F1-F6 candidate model is fitted/scored.

## Hard boundary confirmation

At this checkpoint:

- V4-A A1 result: `UNVIEWED`;
- V4-A A2 result: `UNVIEWED`;
- A1+A2 integration: not materialized;
- sessions `1225+`: not materialized/scored by V4-A;
- post-2026-07-31 fresh-forward outcomes: not accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED`: not written;
- V3-B remains immutable;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge remain unauthorized.
