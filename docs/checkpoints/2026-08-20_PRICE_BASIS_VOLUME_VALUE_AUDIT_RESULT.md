# Price-Basis Volume/Value Audit V1 — Runtime Result

Date: 2026-08-20 Asia/Jakarta  
Branch: `data/price-basis-remediation-v1`

## Verdict

`NO_REPEATED_VOLUME_VALUE_BASIS_SCALE_EVIDENCE_REFIT_REVIEW_READY`

The bounded audit completed on exactly the 1,657 H/L/C-remediated rows across 12 tickers. No provider calls, model fitting/scoring, target-value access, protected-forward access, or additional repair occurred.

## Frozen runtime evidence

- population: 1,657 rows / 12 tickers;
- official Stock Summary archive: 1,288 parsed files, 1,129,024 rows, all 1,288 files carrying both Volume and Value;
- Volume: 1,657/1,657 `SAME_BASIS`, zero CA-factor rows, zero other-ratio rows, zero invalid/missing rows, zero repeated non-unit ratio groups;
- Value: 1,657/1,657 `SAME_BASIS`, zero CA-factor rows, zero other-ratio rows, zero invalid/missing rows, zero repeated non-unit ratio groups;
- `refit_review_ready=true`;
- runtime manifest SHA-256: `317c5cad8170b34b69c87eb43763b9afe4a368cbd9a3afaf94c5297aebeeb38f`.

## Interpretation

The previously confirmed Yahoo historical corporate-action basis problem is an H/L/C basis problem for the certified 1,657-row population. The bounded evidence does not support any Volume or regular-market-Value basis remediation on those rows. Accordingly, the materialized H/L/C-only panel remains the correct remediation candidate; volume and value must remain unchanged.

This result does not authorize tuning, feature changes, target changes, historical performance recomputation, protected-forward access, or overwriting any legacy V2/V4-X model. The next permissible step is a separately frozen deterministic clean-refit protocol using exactly the remediated panel and the already-consumed historical training contracts.