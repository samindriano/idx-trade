# Price-Basis Remediation V1 — Runtime Result

Date: 2026-08-20 Asia/Jakarta  
Branch: `data/price-basis-remediation-v1`

## Decision

Local materialization completed successfully with verdict:

`PRICE_BASIS_HLC_REMEDIATION_MATERIALIZED_REFIT_NOT_AUTHORIZED`

The runtime was offline and outcome-free. No model fit, model scoring, provider call,
protected-forward access, target-value access, parent-panel overwrite, or volume/value
repair occurred.

## Frozen inputs

- parent panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- Step-2 audit V1.1 manifest SHA-256: `62562fa3f1d949c3e4f9e225aae13b116a5e2c00dffcceab6240ebb07ea422d6`
- Step-2 audit V1.2 manifest SHA-256: `620fbd1f98924365e623919d3339f005abd7960f66631213631b845dcd7061f5`

## Materialization evidence

All frozen repair gates passed:

- parent stable rows: 1,657 / 12 tickers;
- certified rows: 1,657 / 12 tickers;
- missing certification rows: 0;
- factor failures: 0;
- provenance failures: 0;
- post/on-record-date failures: 0;
- counterfactual parity rows: 1,657;
- non-HLC identity parity: PASS;
- non-HLC value parity: PASS across all 10 non-HLC columns.

Repair tickers:
`BUAH, CLEO, CUAN, CYBR, DSSA, MEGA, MLPT, MMIX, RAJA, RISE, RMKE, WGSH`.

Official-IDX H/L/C exact agreement on the 981,940-row comparison population improved
from 978,497 rows (`99.6493675785%`) to 980,154 rows (`99.8181151598%`) after the
certified overlay.

The 188 remaining scale-consistent but non-stable rows are retained as unresolved
diagnostics and are not silently repaired.

## Runtime artifact

External root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\price_basis_remediation_v1_20260820`

Runtime manifest SHA-256:
`2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278`

## Scientific interpretation

This closes the narrow H/L/C materialization step. It does not make the panel a
fully-clean model-training input yet because `volume` and `regular_market_value`
were intentionally preserved unchanged. The parent Step-2 evidence already proved
that H/L/C basis correction changes 52,554 V2 prepared rows and 56,602 V4-X1 exact
H5/H10 union rows; no refit is authorized until volume/value basis is audited.

## Next boundary

Run a bounded, preregistered volume/value-basis audit on exactly the frozen 1,657
H/L/C repair identities. The audit must compare the unchanged panel `volume` and
`regular_market_value` with official IDX Stock Summary witnesses where those fields
are available, diagnose whether any corporate-action multiplicative factor survives
in those fields, and stop before any repair or model refit.
