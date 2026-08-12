# Forward Monitoring Scope V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **UI / OPERATING CONTRACT — OUTCOME-BLIND**

## Purpose

Define what the IDX Trade frontend should monitor now that the historical alpha search is closed and the final ranker is frozen.

The monitored alpha model is exactly:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

Frozen final model SHA-256:

`1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`

The dashboard must distinguish four separate things that were previously mixed together:

1. EOD data capture;
2. final-model signal scoring;
3. forward-validation accumulation;
4. realized outcome/performance access.

Only the first three are visible during the protected forward period. The fourth remains locked.

## 1. Data capture — visible now

For every official closed IDX signal session after the monitoring start boundary, track:

- official session identity;
- snapshot state: available / fetching / ready / failed;
- immutable snapshot path/hash;
- evidence/manifest path/hash;
- eligible/PIT universe construction status;
- provider/data failures;
- capture timestamps.

A captured session is **not** automatically a scored model session.

## 2. Final V3-B signal scoring — visible now

For each data-ready session, the intended forward scorer should eventually persist one immutable V3-B score artifact containing only outcome-blind information, including:

- signal date;
- ticker;
- final V3-B raw ranking score;
- same-date rank / percentile;
- eligible-universe size;
- exact model ID and model SHA;
- exact feature-order identity;
- score-artifact and manifest hashes;
- feature/data completeness diagnostics.

The UI may show rankings, top names, score distributions, rank changes, missing-feature diagnostics, and model/data fingerprint health because these do not reveal future realized labels.

Do not treat the score as calibrated `P(TP before SL)`.

## 3. Forward-validation accumulation — visible now

Track progress toward the frozen first independent verdict:

- number of verified final V3-B score sessions;
- target: exactly 100 consecutive H10-mature official forward signal sessions;
- H10 maturity/data-completeness metadata when implemented;
- first/last candidate signal dates;
- missing or failed sessions that prevent a consecutive block;
- model/source identity consistency across the block.

A session counts toward visible scoring progress only when a verified final V3-B score artifact exists. Data capture alone does not count.

## 4. Outcome vault — hidden until one-shot authorization

The frontend must not expose or derive any of the following before the exact 100-session block is frozen and the separate outcome-access workflow is authorized:

- TP_FIRST / SL_FIRST labels;
- per-stock realized success/failure;
- PR-AUC;
- PR-AUC minus prevalence;
- ROC-AUC;
- Q1/Q5 TP rates;
- Q5-Q1 spread;
- top-decile realized lift;
- realized forward returns;
- PnL / equity curve;
- rolling or interim model-performance summaries.

The UI should show only `OUTCOMES LOCKED` during this phase.

## Model ecosystem shown by the frontend

### Active forward model

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

- 33 causal features;
- exact V2 market/cross-sectional information plus eight Structure-Lite features;
- historical alpha architecture closed;
- final refit complete;
- this is the only alpha model that should count toward the protected forward validation.

### Historical reference only

`HGB_XS_MARKET`

This remains the V2 historical champion/control, but it is no longer the active forward champion and must not accumulate a competing independent block for adaptive V2-vs-V3 selection.

### Separate lane, not integrated

`PATH-RISK-A-Q75-HGB-001`

Path Risk V1 is a separate risk-research experiment. It must not appear as a second-stage trade filter or active forward model unless Path Risk itself passes its frozen research gates and a later integration hypothesis is separately preregistered.

### Not yet available

- calibrated probability;
- expected-payoff/distribution layer;
- reliability/uncertainty layer;
- trade-selection policy;
- portfolio sizing;
- execution/PnL layer.

## UI hierarchy

The Forward Monitoring page should therefore answer, in order:

1. **Did we capture the session correctly?**
2. **Did the exact final V3-B model produce a verified score artifact?**
3. **How many protected forward sessions have accumulated toward 100?**
4. **Are the model/data identities still unchanged?**
5. **Are outcomes still locked?**

It should not answer "Did today's picks win?" yet.

## Implementation boundary

The current frontend branch already contains a data-capture runtime and model-run registry. Updating the UI/model catalog does not by itself implement the final V3-B scorer. The real scorer must be wired later against the frozen local final-model artifact and the latest V3-B causal forward runtime without changing research semantics.
