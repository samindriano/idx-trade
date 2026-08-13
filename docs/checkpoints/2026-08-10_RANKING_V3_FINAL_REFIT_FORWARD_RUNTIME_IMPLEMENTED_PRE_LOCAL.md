# Ranking V3-B Final Refit / Forward Runtime — Implemented Pre-Local

Date: 2026-08-10 (Asia/Jakarta)
Status: **IMPLEMENTED PRE-OUTCOME / WINDOWS-LOCAL PYTEST + FINAL REFIT NEXT**

## Decision state

The final V4 alpha review is closed with no survivor. Exact V3-B Structure-Lite remains the final historical-development ranker.

The frozen final-refit/fresh-forward specification and independent review are:

- `docs/RANKING_V3_FINAL_FORWARD_SPEC_V1.md`;
- spec Git blob `024f1919de8d5ea4e2e9933a9e4c1a1ef9bbe4f4`;
- `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_FORWARD_SPEC_REVIEW_PASS.md`.

Repo implementation now exists:

- `src/idx_trade/ranking_v3_forward_runtime.py`;
- `tests/test_ranking_v3_forward_runtime.py`.

This checkpoint records implementation only. A full Windows-local repository pytest and the exact final refit have not yet been executed after these files were added.

## Implemented final-refit behavior

The runtime:

- verifies the frozen panel/calendar/security-master hashes;
- verifies the exact V2 prepared-cache and manifest hashes/facts;
- requires the frozen final-forward spec identity;
- rebuilds exact causal Structure-Lite geometry through signal session 1250;
- joins the eight Structure-Lite columns one-to-one onto the exact 292,633 frozen V2 rows;
- rejects orphan/duplicate rows and infinity;
- preserves missing Structure-Lite values for the frozen imputer;
- verifies exact 33-feature order SHA-256 `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- serializes and hashes the exact final training table;
- fits exactly one frozen V3-B HGB model;
- serializes and hashes model + manifest;
- records explicitly that no historical performance metric was computed and sessions 1225..1250 were used for training only.

## Implemented outcome-blind forward behavior

The runtime also provides:

- exact V2 causal forward-feature construction reuse;
- exact Structure-Lite forward geometry join;
- primary-liquid-only scoring rows;
- outcome-column rejection;
- ACTIVE-only signal-panel guard when tradability state is present;
- final model/manifest verification;
- exact frozen model scoring;
- V3-specific pre-outcome manifest generation;
- reuse of the frozen H10 maturity, 100-session selection, PASS/MIXED/FAIL evaluation, and global marker primitives.

No real forward label/outcome loader or automatic one-shot execution was added to the CLI. That is intentional: the current authorized CLI exposes only `final-refit`.

## Focused tests added

The new tests cover:

- exact 33-feature order/hash;
- row-preserving Structure-Lite join and missing-value semantics;
- orphan-key fail-closed behavior;
- outcome-blind post-cutoff primary-liquid forward feature construction;
- outcome-column rejection;
- non-ACTIVE signal-panel rejection;
- future-row causal invariance across all 33 model features.

Existing V2 marker/maturity tests remain the reference for the shared one-shot primitives.

## Next action

Execute only the Windows-local handoff:

`coordination/handoffs/IDX-RANKING-V3-FINAL-REFIT-FORWARD-RUNTIME-LOCAL.md`

Required sequence:

1. pull latest branch;
2. full pytest, zero failures;
3. verify exact frozen local input hashes;
4. run one `ranking_v3_forward_runtime final-refit` into a new empty output directory;
5. verify the resulting model/manifest pair and training-table facts/hashes;
6. document/push the result;
7. STOP.

## Hard boundary

Do not load fresh-forward labels/outcomes, write the real `FORWARD_OUTCOME_ACCESS_STARTED`, compute a 100-session verdict, score sessions 1225..1250 as a validation slice, reopen historical architecture selection, or begin calibration/Stage 6/IDX-VAL-002/execution/PnL/paper/live/main merge.