# TradingView V2.1 Step 2 — Frozen Training Price-Basis Impact Audit Prep

Date: 2026-08-20 (Asia/Jakarta)  
Branch: `audit/tradingview-v2-1-training-basis-impact-v1`  
Scientific base: `research/idx-ranking-v4-x1-prospective-eval-v1`  
Status: `PREPARED_OFFLINE_RUNTIME_REQUIRED`

## Question

The prior TradingView fidelity forensic exposed evidence that the legacy raw
canonical comparator can carry a different historical price basis from both
TradingView and official IDX Stock Summary. This audit answers the narrower
model-lineage question before any retraining is considered:

> Does a stable official-IDX-vs-frozen-panel H/L/C scale-basis conflict alter
> the actual clean V2 historical training representation or the frozen V4-X1
> final-training-date model representation?

The frozen V2 and V4-X lineages both ultimately depend on the same research
panel SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

This audit does **not** assume that a legacy raw-canonical discrepancy is also
present in the model-safe research panel. It tests that proposition directly.

## Non-negotiable boundaries

This lane is offline and diagnostic only.

- no provider/network calls;
- no model fitting;
- no model scoring/predictions;
- no V4 historical target materialization;
- no protected/fresh-forward outcome access;
- no in-place mutation of the frozen panel;
- no model replacement, promotion, rescue, or retraining authorization;
- no change to prospective V4-X/O2 counters or artifacts.

A positive impact finding is a review trigger, not permission to retrain.

## Frozen inputs

### Shared model-safe panel

Expected SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Default path:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

### Official exchange calendar

Expected SHA-256:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

### Official IDX Stock Summary witness

Default archive root:

`D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1`

The runner reads existing `sessions/YYYY-MM-DD/stock_summary.raw.json` files
only. It makes no provider call.

### Current clean V2 historical replay

Runtime root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_historical_replay_v1_20260813_001`

Immutable prepared-table SHA-256:

`79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826`

Expected population: 292,631 rows / 737 tickers. The frozen winner was again
`HGB_XS_MARKET`. This is the PIT-safe historical replay lineage; the older
pre-listing-contaminated V2 result is not used as the parity oracle here.

V2 security-master SHA-256:

`9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`

### Frozen V4-X1 lineage

The audit branch is based directly on the frozen V4-X1 scientific branch so
that the exact V4 feature/model-frame code is reused without modification.

Parent combined-replay manifest SHA-256:

`12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43`

The final-refit root is discovered only if its manifest schema is
`ranking_v4_x1_final_refit_manifest_v1` and its status is exactly:

`V4_X1_FINAL_REFIT_FROZEN_READY_FOR_FRESH_PROSPECTIVE_SCORING`

The final-refit manifest must also record `provider_calls=false` and
`protected_forward_accessed=false`, and its training-date artifact hash must
match the manifest.

## Basis-conflict rule

For each panel/official-IDX ticker-date overlap:

1. compare H, L and C;
2. a row receives a multiplicative scale factor only when all three positive
   IDX/panel ratios agree under the frozen helper tolerance and the factor is
   materially different from one;
3. a scale regime is decision-bearing only when the same factor persists for
   at least **three consecutive official exchange sessions** for that ticker;
4. all other mismatches remain unresolved conflicts and are not repaired.

The counterfactual panel replaces **H/L/C only** on decision-bearing stable
scale-regime rows. Volume, regular market value, provenance and every other
column remain untouched. The original panel is never overwritten.

## V2 audit

The runner:

1. applies the generic PIT listing-domain gate using the frozen V2 security
   master;
2. reconstructs the Clean-V2 `HGB_XS_MARKET` feature representation from the
   original panel;
3. proves reconstruction parity against the immutable 292,631-row PIT-safe V2
   replay table;
4. only if parity is exact under the frozen numerical tolerance, repeats the
   feature build on the H/L/C counterfactual panel;
5. compares all frozen V2 training identities and all 25 `HGB_XS_MARKET`
   features.

Possible V2 verdicts:

- `V2_NO_TRAINING_SCALE_BASIS_IMPACT`
- `V2_TRAINING_SCALE_BASIS_IMPACT_FOUND`
- `V2_TRAINING_IMPACT_UNRESOLVED_CACHE_OR_PARITY`

No V2 model is fit.

## V4-X1 audit

The runner imports the exact frozen
`scripts/run_v4_3r_historical_one_shot.py` and invokes only the pre-target
functions needed to build:

- PIT-safe V4 control features;
- frozen open/price evidence;
- the V4 model frame including session geometry.

It explicitly does **not** call `materialize_v4_target_ledger`, model fitting,
or scoring.

Original versus H/L/C-counterfactual representations are compared on every
V4 model-frame row whose date belongs to the frozen final H5/H10 training-date
set. This is an **outcome-free superset** of the exact fit-row population.
Therefore:

- zero changed rows is sufficient to establish no scale-basis feature impact
  on the exact final fit rows;
- non-zero changed rows are reported conservatively as *potential* training
  impact because the audit does not open target-backed exact fit-row identity.

Compared columns are all 25 V4 control features plus all three frozen session
geometry features.

Possible V4-X1 verdicts:

- `V4_X1_NO_TRAINING_SCALE_BASIS_IMPACT`
- `V4_X1_POTENTIAL_TRAINING_SCALE_BASIS_IMPACT_FOUND`

No V4-X model or target is materialized.

## Combined adjudication

- both clean: `FROZEN_TRAINING_PANEL_BASIS_IMPACT_NOT_FOUND`
- V2 actual impact or V4-X1 potential impact:
  `FROZEN_TRAINING_PANEL_BASIS_IMPACT_FOUND`
- V2 parity cannot be established:
  `FROZEN_TRAINING_PANEL_BASIS_IMPACT_UNRESOLVED`

This adjudication concerns the **frozen model-safe panel lineage only**. It
must not be used to erase the separate finding that the legacy raw canonical
comparator can have price-basis conflicts.

## Prepared implementation

- `src/idx_trade/training_price_basis_impact_audit.py`
- `scripts/run_training_price_basis_impact_audit_v1.py`
- `tests/test_training_price_basis_impact_audit.py`
- this checkpoint

Default output root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_v2_1_training_basis_impact_v1_20260820`

Expected outputs:

- `panel_vs_idx_basis_rows.csv`
- `stable_scale_runs.csv`
- `counterfactual_hlc_rows.csv`
- `v2_reconstruction_parity_rows.csv`
- `v2_training_feature_impact_rows.csv`
- `v4_x1_candidate_training_feature_impact_rows.csv`
- `training_basis_impact_summary.json`
- `artifact_manifest.json`

The runner refuses to overwrite a non-empty output directory.

## Runtime stop

Run the focused tests and the offline runner locally. Stop after the printed
JSON sections `panel_idx_basis`, `stable_scale_runs`, `v2_clean_replay`,
`v4_x1`, and `adjudication`. Do not run TradingView acquisition and do not
retrain any model from this lane.
