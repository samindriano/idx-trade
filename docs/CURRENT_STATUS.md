# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`, `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`, `docs/PATH_RISK_V1_LEDGER.md`, and the newest dated checkpoint/handoff. If older text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1 historical benchmark failed and its consumed holdout is never rerun;
- Ranking V2 historical champion/control: exact `HGB_XS_MARKET`;
- Ranking V3 architecture search: **CLOSED**;
- final historical-development ranker: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- V3-B one-shot V2F5/V2F6 late-development confirmation: **PASS**;
- V3-A Recency: killed;
- V3-C Regime-Specialization: killed;
- V3-D Sector-Relative: parked `BLOCKED_PIT_SECTOR_HISTORY`, outcomes unconsumed;
- V3-E True Ranking: killed;
- V4 final alpha-generation program: **CLOSED — NO SURVIVOR**;
- cumulative historical evaluated alpha-candidate count: `17`;
- final V3-B refit/runtime: **FROZEN SUCCESSFULLY, NO PERFORMANCE METRICS COMPUTED**;
- Path Risk V1: **CLOSED — `PATH_RISK_A_DISCOVERY_FAIL_CLOSE`**;
- Path Risk PR-001 is permanently viewed; F5/F6 remain sealed and are not authorized;
- post-2026-07-31 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

## Final historical ranker

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

It is exact V2 `HGB_XS_MARKET` information plus eight frozen causal Structure-Lite geometry features. Across V3-B F1-F4, median paired PR improvement versus V2 was `+0.0039258450`; the one-shot F5/F6 late-development confirmation passed with median paired PR improvement `+0.0075911303`.

This is historical-development ranking evidence only. It is not calibrated probability, execution/PnL evidence, live readiness, or independent future validation.

Frozen signal-research identities:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Frozen V2 resolved-primary-H10 prepared cache for the final fit:

- cache SHA-256 `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- manifest SHA-256 `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- rows/tickers/sessions `292,633 / 737 / 20..1250`.

Final V3-B refit result:

- status `RANKING_V3_B_FINAL_REFIT_FROZEN`;
- training table SHA-256 `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe`;
- model SHA-256 `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`;
- model manifest SHA-256 `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9`;
- summary SHA-256 `e8e42dec10c73257fe4776f682f55d146ed8ca49b4aed7ce63ddb7488419e6a0`;
- rows/tickers/sessions `292,633 / 737 / 20..1250`;
- sessions `1225..1250` were training-only;
- historical performance metrics were not computed;
- model/manifest verification: `valid=true`;
- fresh-forward outcomes were not accessed.

Controlling checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REFIT_RUNTIME_RESULT.md`

## Path Risk V1 — CLOSED

Frozen hypothesis:

`PATH-RISK-A-ADVERSE-EXCURSION-Q75-V1`

Frozen candidate:

`PATH-RISK-A-Q75-HGB-001`

The outcome-blind 33-feature discovery cache passed pre-outcome review, then PR-001 was executed exactly once on F1-F4 with the corrected current-checkout import path.

Execution facts:

- code HEAD used: `878898b70e930269e11cf00e18e263735fd3928c`;
- pytest: `381 passed, 0 failed, 3 warnings`;
- target rows: `660,721`;
- feature rows: `254,383`;
- joined model rows: `252,198`;
- feature-to-target join coverage: `99.1411%`;
- prediction finite rate: `100%` on all four folds.

Relative pinball improvement by fold:

- V2F1: `+0.004267`;
- V2F2: `+0.011273`;
- V2F3: `+0.014061`;
- V2F4: `-0.033463`.

Frozen gate summary:

- nonnegative pinball improvement on >=3/4: **PASS**, `3/4`;
- median pinball improvement >= `+0.02`: **FAIL**, approximately `+0.00777`;
- q25 pinball improvement >= `0`: **FAIL**, approximately `-0.00517`;
- worst pinball improvement >= `-0.01`: **FAIL**, `-0.033463`;
- positive Spearman on >=3/4: **PASS**, `4/4`;
- median Spearman >= `+0.10`: **PASS**;
- positive Q5-Q1 realized adverse-excursion spread on >=3/4: **PASS**, `4/4`;
- median Q5-Q1 spread >= `+0.10 R`: **PASS**.

Final verdict:

`PATH_RISK_A_DISCOVERY_FAIL_CLOSE`

Interpretation: the frozen representation contains some cross-sectional risk-ordering information, but the q75 model does not robustly beat the unconditional training-q75 comparator on the proper scoring objective. F4 materially degrades pinball loss and shows strong q75 undercoverage. The experiment may not be rescued after the fact as a pure ordering model.

Therefore:

- PR-001 is permanently viewed;
- Path Risk V1 is closed;
- no Path Risk F5/F6 confirmation;
- no alternate quantile/model/feature/target rescue;
- no risk-veto or alpha+risk integration rule;
- final V3-B ranker remains unchanged.

Controlling files:

- `docs/PATH_RISK_V1_LEDGER.md`;
- `docs/checkpoints/2026-08-10_PATH_RISK_V1_DISCOVERY_RESULT_FAIL_CLOSE.md`.

## V4 final alpha review — CLOSED

V4-A:

- `012` exact control: equivalence PASS;
- `013` Impact/Absorption: FAIL;
- `014` Persistent Directional Participation: FAIL.

V4-B:

- `015` exact control: equivalence PASS;
- `016` Path Coherence / Jump Concentration: FAIL;
- `017` Range Acceptance / Rejection: FAIL.

V4-C:

- `018` exact control: equivalence PASS;
- `019` Cross-Sectional Dispersion: FAIL.

No V4 survivor, integration, rescue, threshold relaxation, or additional post-result market-derived alpha family is authorized.

Controlling review:

`docs/checkpoints/2026-08-10_RANKING_V4_FINAL_ALPHA_REVIEW_CLOSED.md`

## V3-D PIT sector history

Status remains `BLOCKED_PIT_SECTOR_HISTORY`.

No complete immutable ticker-by-date IDX-IC source chain with defensible `effective_from`, `effective_to_exclusive`, and `available_at` was established. Ordinals `008/009` remain unviewed.

## Fresh-forward independent verdict

The first independent final-ranker verdict is frozen to the first exact **100 consecutive H10-mature official signal sessions strictly after 2026-07-31**.

The PASS/MIXED/FAIL semantics reuse the already-frozen forward rule unchanged. No shorter interim verdict, rolling performance peek, alternate block, V2 fallback selection, or post-result rescue is allowed.

Daily outcome-blind operation may record:

- official-session data capture and provenance;
- exact final V3-B features;
- final V3-B score/rank artifacts;
- model/feature/artifact fingerprints;
- feature completeness and runtime health;
- count of verified scored sessions toward the future 100-session block;
- calendar/data maturity state without loading realized TP/SL outcomes.

Daily operation must not display or summarize realized TP/SL, PR-AUC, ROC-AUC, Q5-Q1 performance, realized return, PnL, hit rate, or any other reserved forward outcome before the one-shot access boundary.

Before future outcome access, the exact 100-session block and immutable source snapshots must be hash-pinned in a pre-outcome manifest. Then the global `FORWARD_OUTCOME_ACCESS_STARTED` marker must be atomically written before labels/outcomes are loaded. A crash after the marker consumes the block.

## Immediate next action

Primary attention moves to **outcome-blind forward operations for the frozen V3-B ranker**:

1. capture each closed official IDX session with provenance/hash checks;
2. build exact frozen 33-feature V3-B scoring rows;
3. score/rank with exact final model SHA `1a702031...`;
4. persist immutable same-day score/rank artifacts and fingerprints;
5. monitor data/runtime health and verified-session accumulation;
6. keep the forward outcome vault sealed.

Path Risk V1 requires no further execution.

## Hard boundary

Do not:

- reopen V3/V4 architecture selection;
- rescue V4-A/B/C or create a fourth post-result alpha family;
- rerun or rescue Path Risk PR-001;
- access Path Risk F5/F6 outcomes;
- reinterpret PR-001 as a post-hoc pure ordering model;
- create a risk-veto or alpha+risk integration rule;
- bypass the V3-D PIT sector-history block;
- inspect sessions `1225..1250` as a validation slice;
- inspect or summarize post-2026-07-31 fresh-forward labels/outcomes;
- write the real `FORWARD_OUTCOME_ACCESS_STARTED` marker now;
- change the 33-feature ranker, model parameters, labels, universe, or fresh-forward verdict rule;
- start calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge automatically.
