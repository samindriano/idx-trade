# IDX Trade V1 Validation Threat Model

Status: STAGE-2 DESIGN; NO MODELLING AUTHORIZED
Date: 2026-08-09 (Asia/Jakarta)

This document lists the failure mechanisms that can make a daily signal result
look predictive while violating the frozen `SIGNAL_RESEARCH_HLCV` contract.
Each threat has a prevention rule and a regression or audit test requirement.

| threat | failure mechanism | prevention | regression/audit test |
|---|---|---|---|
| Look-ahead in pivots/SR | A pivot is timestamped at its historical turning point even though future bars were needed to confirm it. | Store the confirmation/availability date; expose the level only from that date forward. | Shift future confirmation bars and assert the feature at the original pivot date is unchanged or unavailable. |
| Rolling-window off-by-one | A window accidentally includes `t+1` or uses a centered calculation. | Right-align every window and assert source max date <= signal date. | Append or perturb future rows and assert features at earlier dates do not change. |
| Survivorship bias | Current active names or a final-universe list is backfilled into 2021. | Use PIT listing, scope, and tradability at each signal date. | Reconstruct universe from a historical date and compare it with a current-active list; current membership must not control admission. |
| Corporate-action leakage | A later split/reverse event changes earlier features or labels without a frozen action boundary. | Use the verified raw technical panel and action evidence as of the research contract; never use future action knowledge to alter a prior row. | Inject a later action into a fixture and assert earlier raw rows/features do not change. |
| Provider revision leakage | A revised vendor bar is silently substituted for the value available at the research cutoff. | Preserve raw artifact revision protection and provenance; record artifact hash and retrieval lineage. | Change a provider revision and assert the run stops or produces a new explicit snapshot, never a silent overwrite. |
| Random split leakage | Rows from adjacent dates or the same future path are randomly split across train and validation. | Use official-session chronological folds and keep same-date cross-sections grouped. | Assert `max(train_date) < min(validation_date)` after purge and no date is in both sets. |
| Overlapping forward labels | A training label's future path overlaps a validation signal period. | Purge the final 20 training signal sessions before each validation start. | Enumerate every training `[t+1,t+H]` interval and assert no interval intersects validation dates. |
| Same-date cross-sectional contamination | A date-level transformation or target statistic uses validation securities when fitting a training transform. | Fit cross-sectional ranks, imputers, and scalers separately within the training dates; keep date groups intact. | Permute or remove validation names and assert training features/models do not change. |
| Future preprocessing fit | A scaler, imputer, encoder, threshold, or feature selector is fit on all dates. | Fit all preprocessing only on the fold's model-fit prefix; apply frozen transforms to calibration and validation. | Fit with and without future rows and assert training transforms are identical. |
| Feature selection on final holdout | Holdout performance determines which features or families are retained. | Freeze feature family and model choice using development folds; read holdout once afterward. | Run-level manifest records zero holdout reads before final evaluation; reject any holdout-dependent config hash. |
| Calibration on holdout | Holdout outcomes are used to fit Platt/isotonic calibration before reporting holdout quality. | Fit calibration chronologically inside development folds; reuse the frozen method for holdout. | Assert calibration source dates precede validation/holdout and contain no holdout rows. |
| Threshold optimization on holdout | A probability or score threshold is chosen from final holdout outcomes. | Report threshold-free ranking and fixed pre-registered bucket metrics; any threshold must be frozen from development. | Compare run manifest threshold to the pre-holdout config and fail if it differs. |
| Universe/liquidity future information | A name is admitted using future median value, later survival, or current membership. | Use trailing 60-session value and observed-count rule calculated at each `t`. | Recompute eligibility after truncating data at `t`; result must equal the original eligibility at `t`. |
| Ambiguous TP/SL intraday ordering | Daily High and Low both touch barriers, but code guesses which occurred first. | Emit `AMBIGUOUS_SAME_BAR`; exclude from primary binary calibration and report sensitivity bounds separately. | Fixture with both hits on one bar must never yield WIN or LOSS. |
| Nullable Open dependency | A primary feature or target quietly substitutes Open with Close, prior close, zero, or a vendor adjusted value. | Primary features use H/L/C/Volume/value only; Open remains nullable and explicit. | Remove Open from the panel and assert primary feature/label construction remains identical. |
| Provider contamination | Yahoo has a bar on an official NO_TRADE/SUSPENDED/UNKNOWN session and it enters the panel. | Admit only official ACTIVE rows; quarantine non-ACTIVE provider bars. | Fixture with a provider row on SUSPENDED must produce quarantine and zero model-panel admission. |
| Unknown-state collapse | Missing Stock Summary or legal evidence is converted to NO_TRADE or ACTIVE. | Preserve UNKNOWN as a distinct state and exclude it from research denominators. | Delete an exact official point row and assert state becomes UNKNOWN, never NO_TRADE. |
| Horizon-end truncation | The last signal dates are labelled with an incomplete forward window. | Emit `UNRESOLVED_HORIZON_END` and keep the rows in coverage diagnostics. | Truncate a fixture at the panel end and assert no partial label is emitted. |
| Delisting/suspension interruption | A future non-ACTIVE or delisted period is forward-filled as a price path. | Require a complete ACTIVE future path for a resolved first-touch label; record `UNRESOLVED_PATH`. | Insert a suspension between signal and horizon and assert no resolved label is produced. |
| Class/prevalence leakage | Outcome prevalence from validation or holdout is used to set the base-rate baseline or class weights. | Compute rates from training data only; report validation/holdout prevalence only after scoring. | Alter validation outcomes and assert training baseline probabilities remain unchanged. |
| Score semantics collapse | Probability, Opportunity Score, and Estimate Reliability are stored as one confidence field. | Keep separate named outputs and contracts. | Schema test rejects a single confidence field as the only output. |

The minimum acceptable implementation outcome is fail-closed behavior on every
threat above. A passing model metric cannot waive a threat-control failure.
