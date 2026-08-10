# Handoff — IDX Ranking V3-B Structure-Lite Local Prepare + F1-F4 Run

Date: 2026-08-10 (Asia/Jakarta)

Status: **AUTHORIZED — RUN FROZEN V3-B LOCALLY; NO REDESIGN**

## Objective

Execute the already-reviewed and already-implemented V3-B Structure-Lite experiment locally against the exact frozen research artifacts.

This task is execution/documentation only. Do not redesign Structure-Lite, add variants, or alter any frozen definition after seeing data/metrics.

## Required reads before any command

Fetch/pull the latest `research/idx-ranking-v2-spec-v1` and explicitly acknowledge reading:

1. `docs/CURRENT_STATUS.md`
2. `docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_REVIEW_PASS.md`
3. `docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_F1_F4_RESULT.md`
4. `docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`
5. `docs/RANKING_V3_STRUCTURE_LITE_SPEC_REVIEW_ADDENDUM_V1.md`
6. `docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_IMPLEMENTED_RUN_AUTHORIZED.md`
7. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
8. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`
9. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`
10. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
11. `src/idx_trade/research_v3_structure_lite.py`
12. `src/idx_trade/ranking_v3_structure_lite.py`

The review addendum controls wherever it clarifies the original Structure-Lite spec.

## Frozen candidate set

Exactly two candidate slots exist:

- ordinal `004`: exact V2 `HGB_XS_MARKET` control;
- ordinal `005`: one fixed eight-feature Structure-Lite candidate.

No second Structure-Lite variant exists.

Do not change:

- any of the eight feature definitions/order;
- P/L/R/S/B/V constants;
- ATR/cluster/touch/volume thresholds;
- V2 25-feature prefix;
- HGB parameters or seed;
- H10 target/universe;
- metrics/gates;
- F1-F4 fold boundaries;
- candidate IDs;
- score transform.

## Frozen source identities

The local task must locate and SHA-verify exact artifacts, failing closed if missing or ambiguous:

- signal-research panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- official calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- security master SHA-256:
  `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`
- V2 prepared table SHA-256:
  `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`
- V2 prepared manifest SHA-256:
  `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`
- frozen V2 HGB summary SHA-256:
  `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`
- frozen V2 HGB predictions SHA-256:
  `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`

Known research store root is under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\...`

Do not assume a path if the hash points somewhere else; the hash is authoritative.

## Step 1 — repository preflight

1. `git fetch` and `git pull --ff-only` the branch.
2. Verify branch is exactly `research/idx-ranking-v2-spec-v1`.
3. Verify clean working tree.
4. Record current HEAD.
5. Run full repository pytest from the correct repo root.

If any test fails, STOP. Do not prepare cache and do not score.

Report exact passed/failed/warnings and duration.

## Step 2 — build the outcome-independent V3-B discovery cache

Use the already-implemented module:

`python -m idx_trade.ranking_v3_structure_lite prepare`

Provide exact paths for:

- `--panel`
- `--calendar`
- `--security-master`
- `--v2-prepared`
- `--v2-manifest`
- `--spec docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`
- `--addendum docs/RANKING_V3_STRUCTURE_LITE_SPEC_REVIEW_ADDENDUM_V1.md`
- `--output-dir <NEW_EMPTY_V3_B_PREPARE_DIR>`
- `--code-commit <CURRENT_IMPLEMENTATION_HEAD_OR_EXPLICIT_CODE_HEAD>`

The output directory must be new/empty.

This prepare stage is outcome-independent. It must:

- physically materialize only V2 eligible rows through session `984`;
- never copy/load V2F5/F6 candidate rows into the discovery cache;
- build Structure-Lite only through official session 984;
- preserve exact V2 row identity/order and all original V2 columns;
- write an immutable V3-B cache and manifest with hashes/coverage.

After prepare, inspect only provenance, row identity, coverage/missingness and feature sanity. Do **not** calculate target-performance diagnostics manually before the frozen runner.

Required prepare checks before scoring:

- manifest status is `RANKING_V3_B_STRUCTURE_LITE_DISCOVERY_CACHE_FROZEN`;
- last signal session exactly `<=984`;
- `v2f5_v2f6_materialized=false`;
- `outcome_metrics_computed=false`;
- all source hashes match;
- no duplicate/orphan join rows;
- exact V2 prefix preserved;
- no infinite structure feature values;
- event state only `{-2,-1,0,1,2}`;
- volume confirmation only `{0,1}` when observed;
- record all feature coverage/missingness.

If preparation/data/provenance fails, STOP and document the blocker. That is not a hypothesis result.

Once the discovery cache hashes are recorded, **do not edit implementation/spec/gates before the run**.

## Step 3 — run F1-F4 only

Use:

`python -m idx_trade.ranking_v3_structure_lite run`

Provide:

- `--cache <FROZEN_V3_B_DISCOVERY_CACHE>`
- `--cache-manifest <FROZEN_V3_B_DISCOVERY_MANIFEST>`
- `--reference-v2-dir <EXACT_HGB_XS_MARKET_REFERENCE_DIR>`
- `--spec docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`
- `--addendum docs/RANKING_V3_STRUCTURE_LITE_SPEC_REVIEW_ADDENDUM_V1.md`
- `--output-dir <NEW_EMPTY_V3_B_RUN_DIR>`
- `--code-commit <IMPLEMENTATION_HEAD>`

The runner must execute sequentially:

1. exact V2 control on V2F1-F4;
2. mandatory control equivalence against immutable V2 HGB artifacts;
3. if and only if equivalence PASS, exact one Structure-Lite candidate;
4. frozen absolute-sanity and paired-promotion gates;
5. deterministic verdict.

If control equivalence fails, STOP immediately. Do not interpret Structure-Lite metrics and do not weaken tolerance.

## Required result reporting

Return exact per-fold F1-F4 metrics for control and Structure-Lite:

- prevalence;
- PR-AUC;
- PR-AUC minus prevalence;
- ROC-AUC;
- Q1 TP rate;
- Q5 TP rate;
- Q5-Q1 TP-rate spread;
- top-decile TP rate/lift.

Also report paired per-fold changes and aggregate:

- median/q25/worst paired PR-delta improvement;
- PR not below control fold count;
- median ROC change;
- median Q5-Q1 change;
- Q5-Q1 not below control fold count;
- V2F4 behavior;
- coverage/missingness;
- runtime profile.

The expected frozen global verdict is one of:

- `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`; or
- `V3_B_STRUCTURE_LITE_KILL_KEEP_V2_CONTROL`.

Do not invent a third rescue path.

## Step 4 — permanent ledger / repo documentation

After the frozen run, update:

- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
  - ordinal 004 becomes executed control;
  - ordinal 005 becomes executed Structure-Lite candidate;
  - cumulative evaluated count becomes `5`;
- dated V3-B result checkpoint;
- result handoff for ChatGPT review;
- `docs/CURRENT_STATUS.md`.

Record:

- branch/source/final HEAD;
- implementation commit;
- pytest result;
- all input/cache/output SHA-256;
- cache rows/tickers/session range;
- coverage diagnostics;
- control-equivalence status;
- candidate gates/verdict;
- artifact inventory;
- runtime/environment;
- explicit safety confirmations.

Commit and push. Verify clean/synced branch. Then STOP for ChatGPT review.

## Hard prohibitions

Do not:

- change any V3-B feature, parameter or gate after score;
- create a second V3-B variant or rescue candidate;
- reopen V3-A Recency;
- materialize/score/summarize V2F5/V2F6;
- inspect reserved post-2026-07-31 V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start V3-C Regime, V3-D Sector, V3-E True Ranking or V3 integration;
- start calibration, Stage 6, IDX-VAL-002, execution-PnL, Kelly, paper/live or main merge.

## Stop rule

After the F1-F4 V3-B result is documented, committed and pushed, STOP and return the exact result to ChatGPT. Do not proceed automatically to V3-C.
