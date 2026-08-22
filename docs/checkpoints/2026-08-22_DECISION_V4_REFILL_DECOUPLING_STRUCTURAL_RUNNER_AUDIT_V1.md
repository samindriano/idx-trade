# Decision V4 Refill Decoupling V1 — Structural Runner Audit

Date: 2026-08-22 Asia/Jakarta

Verdict: `RUNNER_AUDIT_ACCEPTED_SINGLE_STRUCTURAL_REPLAY_AUTHORIZED`

## Reviewed runner

Runner branch:

`research/idx-decision-v4-refill-decoupling-structural-runner-v1`

Reviewed exact runner HEAD:

`6cc21a70ef4cc8096c296393e3b6404cf9efd9f0`

Accepted implementation-audit parent:

`73939c7dbe6db23554323fd0bd4c21ddfd4b964a`

Controlling frozen preregistration:

`docs/specs/decision_v4_refill_decoupling_v1.json`

Rule:

`V4_X1_DECISION_V4_REFILL_DECOUPLING_V1`

## Independent GitHub audit

The exact runner diff from the accepted implementation-audit parent is strictly additive: seven new files and zero modifications to any existing V3/model/runtime/source file.

The runner:

- uses the accepted V4 planner and frozen V4-X1 profile;
- reuses the already hardened V3 pinned structural source loader, verified-score projection, general structural ledgers, holding-spell logic, standard structural metrics/gates, and independent post-replay integrity validator;
- reads only the pinned historical rank-source path already frozen for the Decision development replay;
- does not read H5/H10 outcomes, returns, PnL, protected/fresh forward outcomes, or provider/network data;
- does not refit or rescore any model;
- uses the unchanged V3 structural numeric gates exactly as preregistered for V4;
- independently reconstructs incumbent states and severity-conditioned vacancy permissions from rank ledgers rather than trusting V4 plan labels alone;
- fails closed if a severe session admits B/C vacancy refill or if the severe-session classification differs from the independent reconstruction;
- keeps all newly required V4 descriptive diagnostics non-gating;
- requires exact frozen preregistration canonical SHA and source hashes/session/row counts;
- rejects an invalid authorization token before preregistration or historical source inspection;
- writes to a new output directory only and rejects an already-existing destination/staging directory.

## Frozen structural gates

The reused evaluator constants match the frozen V4 preregistration:

- mean replacements <= 2.25;
- turnover vs naive <= 0.50;
- share transitions with >=3 replacements <= 0.35;
- median completed holding >= 3 sessions;
- one-session holding share <= 0.35;
- mean full-target Top10 overlap >= 6;
- mean target rank <= 12;
- mean target size >= 9;
- share target size 10 >= 0.70;
- share target size <=8 <= 0.10;
- target rank >50 after processing count = 0;
- second-consecutive rank 21..50 retained count = 0;
- post-bootstrap previous-absent entrant count = 0.

V4 adds only fail-closed implementation-integrity conditions for the preregistered mechanism. These are correctness checks, not new performance thresholds.

## Local runner validation reviewed

User-provided local validation on exact runner HEAD reports:

- exact HEAD match: PASS;
- diff check and exact seven-file surface: PASS;
- static compile/import: PASS;
- wrong-token fail-closed smoke: PASS;
- prereg/source accessed before wrong-token rejection: NO;
- replay output created during smoke: NO;
- focused runner/implementation tests: 51 passed, 0 failed, 0 skipped;
- broader Decision regression: 192 passed, 0 failed, 0 skipped;
- full pytest: 553 passed, 0 failed, 0 skipped, with only three existing pandas FutureWarnings;
- tracked worktree mutation: NONE;
- correct authorization token was not used;
- historical 600-session replay was not run.

## Authorization

Exactly one outcome-blind structural replay of the frozen 600-session Decision development rank path is now authorized using the exact reviewed runner HEAD above.

Authorized process interlock token:

`DECISION_V4_REFILL_DECOUPLING_STRUCTURAL_REPLAY_RUNNER_AUDIT_ACCEPTED_V1`

The authorized replay must:

1. run from exact runner HEAD `6cc21a70ef4cc8096c296393e3b6404cf9efd9f0`;
2. use the pinned source accepted by the runner source guard;
3. use a new, non-existing output directory;
4. execute the CLI exactly once;
5. not retry automatically after any failure;
6. not alter code, thresholds, source data, or output after observing the result;
7. not access realized Decision outcomes, returns/PnL, or protected/fresh forward data;
8. not run any V4.1/V4.2/rescue variant.

This audit checkpoint is the separate post-preregistration authorization required by the preregistration audit. The frozen preregistration JSON remains unchanged with its historical `replay_authorized=false` field; that field records the preregistration-time boundary and is not mutated post hoc.

## Post-replay decision rule

If the frozen structural verdict is:

`DECISION_V4_REFILL_DECOUPLING_V1_STRUCTURAL_REJECT`

then Decision V4 is rejected, Decision V2 remains the incumbent, and Decision-rule research closes. No rescue variant is authorized.

If the frozen structural verdict is:

`DECISION_V4_REFILL_DECOUPLING_V1_STRUCTURAL_ACCEPT`

then exactly one final V4-vs-V2 economic comparison may be separately prepared under the already frozen Decision economic protocol. Structural acceptance itself does not authorize economic outcome access in this replay.

## Scientific boundary for the authorized replay

- `OUTCOME_BLIND_STRUCTURAL_REPLAY_ONLY = true`
- `REALIZED_H5_H10_OUTCOMES_ACCESS = false`
- `RETURNS_OR_PNL_ACCESS = false`
- `PROTECTED_FORWARD_ACCESS = false`
- `MODEL_REFIT_OR_RESCORE = false`
- `PROVIDER_OR_NETWORK_CALL = false`
- `THRESHOLD_OR_VARIANT_CHANGE = false`
- `AUTOMATIC_RETRY = false`
- `NUMBER_OF_AUTHORIZED_STRUCTURAL_REPLAY_EXECUTIONS = 1`
