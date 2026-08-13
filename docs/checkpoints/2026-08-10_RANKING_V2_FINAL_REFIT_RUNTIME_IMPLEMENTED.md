# Ranking V2 Final Refit Runtime Implemented

Date: 2026-08-10 (Asia/Jakarta)

## Decision

The authorized `IDX-RANKING-V2-FINAL-REFIT-FORWARD-RUNTIME-IMPLEMENT` phase is
complete. The only fitted model is the frozen `HGB_XS_MARKET` final-development
refit. The forward runtime is implemented outcome-blind and frozen for later
one-shot use.

## Validation and artifacts

- runtime commit: `565cffa86b05f2bd877d06b6961e3b792253cb77`;
- pytest: **228 passed, 3 existing warnings**;
- training rows: `292633`;
- training tickers: `737`;
- signal-session boundary: `20..1250`;
- model: `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_final_refit_20260810\ranking_v2_hgb_xs_market_final.joblib`;
- model SHA-256: `5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace`;
- JSON manifest: `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_final_refit_20260810\ranking_v2_hgb_xs_market_final_manifest.json`;
- manifest SHA-256: `f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9`;
- artifact pair verification: `valid=true`;
- profiled cache read/normalize: `0.2982 s`;
- profiled final model fit: `6.3775 s`;
- profiled serialization: `0.0392 s`.

The prepared cache and manifest hashes were verified against the frozen
values. Runtime environment and source fingerprints are recorded in the model
manifest.

## Outcome-access boundary

- fresh-forward labels/outcomes after 2026-07-31: **not read or inspected**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **not written**;
- marker behavior was tested only against a temporary synthetic directory;
- no fresh-forward PASS/MIXED/FAIL verdict was produced;
- no Stage 6, `IDX-VAL-002`, trading, or main merge was started.

The next action requires separate MAIN / ChatGPT authorization after a complete
immutable 100-session H10-mature forward block and its provenance are ready.
