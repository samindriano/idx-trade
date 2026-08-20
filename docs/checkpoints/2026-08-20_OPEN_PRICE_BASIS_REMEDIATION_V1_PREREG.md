# Open Price-Basis Remediation V1 — Preregistered Materialization

Date: 2026-08-20 Asia/Jakarta  
Branch: `data/price-basis-open-remediation-v1`

## Trigger

The post-HLC guard proved that all 1,657 HLC-remediated rows had stale existing Open outside corrected raw H/L. The subsequent outcome-blind Open forensic and residual adjudication are immutable parents:

- HLC remediation manifest SHA-256: `2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278`;
- Open forensic manifest SHA-256: `4538f4d35d042e7e3257b746a56065702463cf8393b1ae922db473a8b355724e`;
- residual adjudication manifest SHA-256: `29b44a549a438189f3efbc2d24a1d7dac9ac4512e4458c70938a8cad193e0949`.

The adjudication classified exactly 1,657 rows / 12 tickers:

- 1,214 `OFFICIAL_IDX_OPEN_PRIMARY_CANDIDATE`;
- 2 `OFFICIAL_PRIMARY_FACTOR_DISAGREEMENT`;
- 439 `CA_FACTOR_FALLBACK_CANDIDATE`;
- 2 `UNRESOLVED_NO_OFFICIAL_FACTOR_OUT_OF_RANGE`.

Thus 1,216 rows have usable official IDX `OpenPrice`, 439 additional rows have only a certified CA-factor reconstruction inside corrected H/L, and 2 rows have neither admissible mechanism.

## Frozen remediation policy

`IDX_OPENPRICE_PRIMARY_CA_FACTOR_FALLBACK_FAIL_CLOSED_V1`

For the exact frozen 1,657-row population:

1. If official IDX `OpenPrice` is positive and within corrected raw H/L, use official `OpenPrice` as the remediated Open. This includes the two rows where the CA-factor reconstruction disagrees with official Open; official IDX is the primary raw-price oracle.
2. Only when official `OpenPrice` is unavailable/non-positive, admit `accepted_open * independently certified CA factor` if the transformed value is inside corrected raw H/L.
3. Otherwise Open is fail-closed/unavailable. Do not infer another factor, clamp to H/L, synthesize, forward-fill, or retain an out-of-basis Open.
4. The result is a separate immutable overlay/candidate. The parent research panel and existing derivative/Open overlays are not overwritten.

Expected materialization counts are frozen before execution:

- official-primary rows: 1,216;
- CA-factor fallback rows: 439;
- admitted remediated Open rows: 1,655;
- fail-closed rows: 2;
- official-vs-factor disagreement rows: 2, resolved in favor of official IDX;
- all 1,655 admitted remediated Open values must be inside corrected H/L.

Any count or parent-hash drift fails closed.

## Explicit non-scope

- no V2/V4-X replay, fit, refit, scoring, or tuning;
- no historical target-value access;
- no protected/fresh-forward outcome access;
- no provider/network calls;
- no parent-panel overwrite;
- no mutation of H/L/C, Volume, Regular-Market Value, universe eligibility, or CA target continuity;
- no attempt to rescue the two unsupported Open rows;
- no model promotion or prospective-counter transition.

## Cross-lane boundary

Even after successful Open-overlay materialization, deterministic V2/V4-X replay/refit remains **not authorized**. Other data-integrity lanes are running in parallel. The Open result must be frozen as an immutable candidate and wait for a cross-lane data-consolidation checkpoint that pins the final accepted input set exactly once.

Expected successful runtime status:

`OPEN_PRICE_BASIS_REMEDIATION_MATERIALIZED_CROSS_LANE_CONSOLIDATION_REQUIRED_BEFORE_REFIT`
