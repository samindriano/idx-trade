# Price-Basis Open Remediation V1 — Runtime Result

Date: 2026-08-20 (Asia/Jakarta)
Branch: `data/price-basis-open-remediation-v1`
Frozen implementation head before runtime: `4403c7a00e42a5bdd3c151536f396251080a66b1`

## Decision

`OPEN_PRICE_BASIS_REMEDIATION_MATERIALIZED_CROSS_LANE_CONSOLIDATION_REQUIRED_BEFORE_REFIT`

The preregistered Open price-basis remediation completed successfully on the exact 1,657-row / 12-ticker HLC-remediation population. The result is an immutable corrected Open candidate only. It does not authorize any V2/V4-X replay, model fit, model scoring, model tuning, protected-forward access, or parent-panel overwrite.

## Runtime evidence

- Output manifest: `D:\Documents\Project\idx-trade-data-gate-20260808v\price_basis_open_remediation_v1_20260820\MANIFEST.json`
- Manifest SHA-256: `753d5470bd240bbf6158142bc5a2b339cea96f83cfb7451c5e18fc10cf5f060f`
- Parent residual adjudication manifest SHA-256: `29b44a549a438189f3efbc2d24a1d7dac9ac4512e4458c70938a8cad193e0949`
- Parent HLC remediation manifest SHA-256: `2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278`
- Policy: `IDX_OPENPRICE_PRIMARY_CA_FACTOR_FALLBACK_FAIL_CLOSED_V1`

## Result counts

| Item | Rows |
|---|---:|
| Frozen repair population | 1,657 |
| Official IDX OpenPrice primary | 1,216 |
| Certified CA-factor fallback | 439 |
| Total admitted Open overlay | 1,655 |
| Admitted and within corrected H/L | 1,655 |
| Official-vs-factor disagreement, resolved by official-primary rule | 2 |
| Unsupported / fail-closed | 2 |

Candidate Open coverage on the repaired population is `0.9987929993964997` (1,655 / 1,657).

## Guardrails verified by runtime

- `model_fit=false`
- `model_scoring=false`
- `model_tuning=false`
- `protected_forward_accessed=false`
- `provider_calls=false`
- `target_values_accessed=false`
- `parent_panel_overwritten=false`
- `unsupported_open_synthesized=false`

The two unsupported rows remain fail-closed. No clamping, inferred factor, synthetic Open, forward fill, or rescue rule is permitted.

## Scientific disposition

Price-basis remediation is now materially complete for the accepted candidate lineage:

1. H/L/C remediation materialized on 1,657 certified rows.
2. Broad Volume and Regular-Market-Value basis audit passed across all 981,940 panel rows with zero mismatch and zero liquidity-feature delta.
3. Open basis forensic and residual adjudication classified the stale Open mechanism.
4. Open remediation materialized 1,655 defensible rows and left 2 rows fail-closed.

No model replay/refit should start yet. The next authorized action is cross-lane data consolidation after the parallel data-audit lanes finish, followed by one frozen consolidated input manifest. Only then should deterministic V2/V4-X replay/refit be considered.

Status: **`WAITING_FOR_CROSS_LANE_DATA_CONSOLIDATION`**.
