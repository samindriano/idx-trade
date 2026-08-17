# Ranking V4-3 — target / feature / model / evaluator pre-outcome freeze

Date: 2026-08-17 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-3-target-execution-freeze-v1`
Status: `V4_3_EXECUTION_PATH_FROZEN_PENDING_LOCAL_SYNTHETIC_VALIDATION_PIT_REFRESH_AND_CA_CONTINUITY`

## Boundary

This checkpoint freezes the historical V4 execution path **before any V4 historical R5/R10 target, target rank, model fit, prediction, IC, Top30, raw-return diagnostic, bootstrap result, provider call, or protected/fresh-forward outcome is accessed**.

The branch is still not authorized to run historical targets/models. It is a pre-outcome engineering freeze only.

## Parents already accepted

- V4-0 product/decision contract: `02716c29e6c41fe1f5244708f9cccac77d978eb9`.
- V4-1 target contract: `199d770520edcd4a7b4537c75d5edaba2b0aa349`.
- V4-2 evaluator contract: `cdb061d32b1d9f63b1b5f719939678a1f15bb082`.
- V4-3 scientific preregistration base: `8dbde070b18edf432348062e5a9218f6ef2665f9`.
- V4-3 primary-liquid support acceptance: `48dbca3799a71306a62a9ad156a106e1a978b006`.
- V4-3 pre-fit runtime manifest SHA-256: `cf6f1b0c859dd21b1c0f377f45d62ecdc98165ff6e0975b852a85b11cfbcaac6`.
- canonical V4-3 preregistration bytes SHA-256: `3a54dcf0266f8a2808b8c1d73dda41a32baea368e6b48aac21e9fa073f6824ed`.

## Frozen target / execution semantics

Machine-readable contract:

`config/ranking_v4_3_target_execution_protocol.json`

Target semantics are exactly:

- entry: official `Open_(t+1)`;
- H5: `Close_(t+5) / Open_(t+1) - 1`;
- H10: `Close_(t+10) / Open_(t+1) - 1`;
- no `Close_t` fallback;
- no synthetic Open;
- no forward fill;
- raw price return, not total-shareholder return;
- cash dividends are not mechanically adjusted into the target.

The target ledger preserves every decision row and assigns explicit fail-closed states rather than dropping future-unobservable rows.

Only `RESOLVED_NO_MECHANICAL_DISCONTINUITY` is a passing corporate-action continuity state for V4 generation 1. Any split, reverse split, stock dividend, bonus share, rights issue, or other mechanical share/price-basis event that may cross after `Open_(t+1)` through and including `Close_(t+h)` remains `PRICE_CONTINUITY_UNRESOLVED`.

Generation 1 has no adjusted endpoint-price layer. Therefore a generic “same-basis resolved” shortcut is deliberately not admitted; adding one later would require a new preregistered generation.

## Frozen target implementation

`src/idx_trade/ranking_v4_3_target_execution.py`

The module implements:

- exact official-session t+1 / t+5 / t+10 identity handling;
- strict market-state and Open/Close admission checks;
- explicit continuity evidence keyed by `(ticker, signal_date, horizon)` with non-empty provenance and evidence SHA;
- fail-closed missing continuity records;
- explicit `NO_FUTURE_SESSION`, `MARKET_ENTRY_UNAVAILABLE`, `TARGET_DATA_UNOBSERVABLE`, `PRICE_CONTINUITY_UNRESOLVED`, and `TRADING_MECHANISM_REFERENCE_UNRESOLVED` states;
- valid zero and negative returns retained as targets;
- within-date average-tie normalized target ranks;
- 50/50 realized H5/H10 consensus only when both heads are available;
- Geometry3 Open-dependent features built only from admitted exact-session Open values.

Synthetic tests cover no-entry, mechanism ambiguity, missing Open, missing price rows, missing/failed continuity, ties, negative/zero returns, no-future-session retention, and continuity provenance.

## PIT/listing-domain remediation before features

A separate frozen-lineage audit proved that a KOCI pre-listing panel row entered historical V2/V3-B/O2 rolling/liquidity/context construction. V4 does not inherit that bug.

Machine-readable remediation contract:

`config/ranking_v4_3_pit_feature_protocol.json`

Implementation:

`src/idx_trade/ranking_v4_3_features.py`

The exact 25 V4 Control information columns are unchanged. The correction is causal ordering:

1. normalize row identity;
2. join the separately pinned authoritative security listing interval;
3. remove missing-master, pre-listing, and post-listing rows;
4. only then compute ATR / rolling price-volume features;
5. compute the causal 60-official-session primary-liquidity state;
6. compute within-date cross-sectional ranks on PIT-valid primary-liquid rows only;
7. compute market breadth/medians and stock-minus-market context.

Any `listed_from` / `listed_to` already carried by the source panel is explicitly discarded before the authoritative security-master join.

Pinned security-master source SHA-256:

`c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240`.

## Frozen learner and evaluator implementation

`src/idx_trade/ranking_v4_3_model_eval.py`

The model path now fixes:

- Control = frozen 25 contextual information columns;
- Challenger = Control + frozen Geometry3;
- the exact preregistered `HistGradientBoostingRegressor` and imputation policies;
- equal total sample weight per training date;
- within-date prediction percentile ranks;
- 50/50 H5/H10 alpha consensus;
- Top30/Bottom30 selected before future target observability;
- no Top30 refill;
- >=90% target-coverage date gate;
- >=27/30 observable Top30 and Bottom30 requirement;
- >=90 admitted metric dates per 100-date fold **separately for IC, Top30, and spread**;
- six frozen 100-date folds;
- 10-date moving-block bootstrap, 2,000 replications, seed 42;
- exact common-support paired challenger-control deltas;
- direct mapping to all frozen absolute and incremental promotion thresholds.

### Frozen score-tie behavior

Large score ties are resolved without target information:

- Top30: alpha descending, ticker ascending;
- Bottom30: alpha ascending, ticker descending.

These are exact reverse deterministic orders, so the two 30-name sets remain disjoint whenever the scored date has at least 60 names. A runtime overlap raises an error.

## PIT-remediated support refresh

Outcome-blind runner:

`scripts/run_v4_3_pit_support_refresh.py`

It does **not** compute returns or target ranks. It recomputes only basic target-support identities after the listing-domain correction using the already accepted Open lineage and tradability states.

The already-frozen 600 validation dates are retained only if:

1. every frozen date remains >=90% basic both-target support on the corrected primary-liquid universe; and
2. the corrected basic-consensus eligible tail-600 identity is byte-for-byte the same `(session_index,date)` sequence as the frozen validation identity.

If either check fails, execution stops for pre-outcome review. The runner explicitly records `corporate_action_continuity_certified=false`.

Frozen validation identity SHA-256:

`91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915`.

The validation CSV is verified against canonical Git HEAD bytes, while Windows working-tree bytes are recorded separately.

## Execution-code identity freeze

Machine-readable protocol:

`config/ranking_v4_3_execution_code_protocol.json`

Capture tool:

`scripts/capture_v4_3_execution_code_manifest.py`

Before first historical target access the capture must:

- require a clean worktree;
- verify the accepted exact Python/package runtime;
- verify canonical preregistration bytes;
- SHA-256 every target/feature/model/evaluator/protocol/test source from canonical Git HEAD;
- separately record working-tree hashes;
- create only a small execution-code manifest;
- never read the historical panel, R5/R10, target ranks, predictions, or performance.

After historical target/performance access, material execution-code/runtime changes are not V4 rescue fixes; they require a separately preregistered generation.

## Corporate-action evidence blocker

Existing accepted Corporate Action work does **not** currently establish the market-wide forward price-continuity ledger required here.

Existing evidence is useful but bounded:

- KSEI historical detail / transaction-history access is real, but retrospective availability does not prove event effective date;
- IDX `GetIssuedHistory` exposes multiple action types, but `TanggalPencatatan` has explicitly not been admitted as a generic market-effective/ex-date;
- bounded deterministic KSEI↔IDX linkage resolves only a small subset of sampled events;
- publication-date hardening improves PIT availability, not price-basis effective timing;
- the signal-panel `corporate_action_integrity_verified` boolean is not equivalent to full forward V4 continuity for rights/bonus/stock-dividend/other mechanical events.

Therefore historical V4 target access remains blocked even if the PIT support refresh and execution-code capture pass.

## Required next local validation

Only the following outcome-blind local work is authorized next:

1. run the focused synthetic V4 test suite plus compile/diff checks;
2. run the PIT-remediated support refresh against the exact pinned local artifacts;
3. if and only if the PIT refresh preserves the frozen 6x100 identities, capture the execution-code manifest;
4. promote only small manifests/checkpoint/handoff metadata and stop.

No historical R5/R10, target ranks, model fits, predictions, performance metrics, provider calls, or Corporate Action acquisition are authorized by this checkpoint.

Verdict:

`V4_3_EXECUTION_PATH_FROZEN_PENDING_LOCAL_SYNTHETIC_VALIDATION_PIT_REFRESH_AND_CA_CONTINUITY`
