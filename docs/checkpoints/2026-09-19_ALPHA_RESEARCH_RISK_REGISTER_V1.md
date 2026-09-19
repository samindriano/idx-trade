# IDX-Trade Alpha Research — Risk Register V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Purpose: durable pre-admission risk register; no entry is a predictive claim.

## Status vocabulary

- `OPEN / BLOCKED`: an external admission or protected artifact is required.
- `OPEN / UNKNOWN`: evidence is incomplete and cannot be safely inferred.
- `OPEN / CAUTION`: structural evidence exists but material implementation risk
  remains.
- `CLOSED / REPRESENTATION`: the exact representation is rejected; the broader
  mechanism is not necessarily rejected.
- `CONTROLLED`: the lane boundary or mitigation is verified for this work.

## Active risks

| ID | Risk | Scope / evidence | Impact | Status | Required next action |
|---|---|---|---|---|---|
| R-01 | Population completeness and historical as-of authority | Clean panel and anchors are frozen structural inputs only; no independent Data QA admission proves population-wide PIT availability. | Any historical predictive comparison could be contaminated or incomplete. | `OPEN / BLOCKED` | Require independent Data QA artifact before any protected read. |
| R-02 | Corporate-action and price-basis incompleteness | Known HLC overlay is represented, but 188 non-stable scale rows and open-price residuals remain unresolved. C1 is most sensitive; H-VOL stress has `86.6667%` minimum Top-30 overlap. | Candidate rankings may depend on mixed or uncertified basis. | `OPEN / UNKNOWN` | Resolve through an independently admitted transition/basis package; do not treat `idx_close` forensic values as truth. |
| R-03 | Issuer/ISIN/security continuity | Frozen interval mapping is one-to-one for audited keys but does not certify all issuer/security transitions or survivorship. | Long windows may join incompatible securities or omit delisted names. | `OPEN / UNKNOWN` | Obtain authoritative identity/transition evidence and rerun the admission gate. |
| R-04 | Historical capacity, ADV, spread, and fills | Current economics use regular-market-value/value-traded proxies; real ADV, spread, queue, and fill history are not admitted. | Low turnover or low overlap may not be executable after friction. | `OPEN / CAUTION` | Continue bounded proxy stress only; require historical liquidity authority for executable claims. |
| R-05 | C3 financial PIT capability | C3 has `30,994` eligible rows and `278` usable Top-30 dates; YoY/provenance contracts remain sparse. | Financial candidate cannot support a stable common-support evaluation. | `OPEN / BLOCKED` | Resolve population-wide publication lag, vintage, period, and identity contracts; no fill or rescue subset. |
| R-06 | H-LIQ-01 novelty and composition | Structurally distinct, but conditional C2 dependence, bottom-value exposure, horizon sensitivity, and missing sector history remain. | H-LIQ may be a liquidity/participation transformation or economically concentrated. | `OPEN / CAUTION` | Keep future research only; no C5 until novelty, basis, and capacity gates change. |
| R-07 | H-VOL-01 horizon dependence and basis | Fixed `5/20`, `5/60`, `20/120` forms differ materially in support/turnover/Top-30 membership; 188-row CA stress changes `547` scores and `8,876` ranks. | The compression family has no single robust frozen horizon yet. | `OPEN / CAUTION` | Preserve `5/60` as diagnostic baseline only; no horizon selection or packet expansion. |
| R-08 | H-EXC-01 numerical instability | Raw previous-close excursion asymmetry has score min/max `-16.2 / 5.0`, mean Top-30 turnover `40.9694%`, max `93.3333%`. | The exact representation can create false extremeness and high churn. | `CLOSED / REPRESENTATION` | Do not retry exact formula with post-result clipping/floors; a bounded alternative needs a new contract. |
| R-15 | H-EXC-02 high churn despite bounded representation | New absolute-distance balance has exact score domain `[-1,1]`, `308,067` finite eligible rows, mean Top-30 turnover `40.7750%`, and maximum `86.6667%`. | Numerical stability does not establish capacity, predictive value, or robustness to PIT/CA basis. | `OPEN / CAUTION` | Keep as future research only; require novelty, price-basis, capacity, and Data QA admission before any candidate decision. |
| R-09 | Dataset-Saham-IDX source admission | `1,014` CSVs and useful OHLCV/foreign/bid-offer fields exist, but no row-level knowledge-time/vintage contract and 11 non-identical duplicate ticker copies. | Data availability cannot be converted into PIT scientific evidence. | `OPEN / BLOCKED` | Preserve as blocked unless an independent source-selection/PIT/identity audit can pass. |
| R-10 | Incumbent/common-support identity | Internal C1-C4 correlations are structural only; same-window immutable incumbent identity is not admitted for predictive comparison. | Low/high structural overlap cannot establish incremental alpha. | `OPEN / BLOCKED` | Verify immutable incumbent/common support only after Data QA admission. |
| R-11 | Protected target and prospective state | H5/H10, forward returns, labels, target-derived incumbent scores, counters, and prospective vault remain protected. | Predictive/OOS/IC/ICIR claims are prohibited. | `OPEN / BLOCKED` | Keep target firewall absolute; execute packet only after independent admission. |
| R-12 | Process-level access attestation | Phase-Q access flags are self-attested; they are not independent proof of absence. | A false-green access claim could invalidate downstream evidence. | `OPEN / UNKNOWN` | Maintain explicit access flags and commission independent red-team review before re-entry. |
| R-13 | Candidate-budget expansion | H-LIQ, H-VOL, and H-EXC are not in the protected four-ID packet; exact H-EXC is rejected. | Discovery could silently become post-hoc multiple testing. | `CONTROLLED` | Keep packet exactly C1-C4; require a new frozen decision for any expansion. |
| R-14 | Lane isolation and production contamination | Current branch is `codex/alpha-available-data-20260919`; derived outputs are staged externally; main/canonical/capture/cloud/telemetry were not modified in this lane. | Boundary failure would contaminate active model/data work. | `CONTROLLED` | Recheck branch, worktree, output root, and protected flags at every milestone. |

## Highest-priority unresolved risks

1. `R-01/R-02/R-03/R-10/R-11`: independent Data QA and common-support
   admission remain the gating cluster for any predictive evaluation.
2. `R-04`: executable capacity remains a proxy-only question.
3. `R-06/R-07`: H-LIQ and H-VOL remain future hypotheses with unresolved
   novelty/economic/basis decisions.
4. `R-09`: Dataset-Saham-IDX is not a fallback source and must not be promoted
   by row count alone.

## Do-not-retry implications

- Do not open targets, forward returns, incumbent prediction artifacts, or
  protected counters to resolve any risk above.
- Do not use `idx_close` forensic substitutions as corrections.
- Do not retry raw H-EXC-01 with ad hoc clipping or denominator floors.
- Do not turn metadata-only snapshots or Dataset-Saham-IDX rows into historical
  PIT evidence without an independent contract.
- Do not expand the protected candidate budget or optimize combination weights.

## Re-entry condition

The risk register does not authorize target access. Before the frozen C1-C4
packet can run, an independent Data QA artifact must clear population
completeness, historical-as-of/PIT, identity/calendar, corporate-action basis,
revision/vintage, H5/H10 authority, immutable incumbent/common support, and
protected-state integrity. Any `UNKNOWN` remains blocking.

## Provenance

- Current branch: `codex/alpha-available-data-20260919`
- Current checkpoint family: `2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`,
  `2026-09-19_ALPHA_RESEARCH_PHASE_MATRIX_V1.md`, and
  `2026-09-19_ALPHA_RESEARCH_CHATGPT_HANDOFF_V3.md`
- H-EXC evidence: `2026-09-19_ALPHA_HEXC01_EXCURSION_ASYMMETRY_RESULT_V1.md`
- H-VOL evidence: `2026-09-19_ALPHA_HVOL01_HORIZON_STABILITY_RESULT_V1.md` and
  `2026-09-19_ALPHA_HVOL01_CA_SENSITIVITY_RESULT_V1.md`
- No protected outcome or production artifact was accessed or modified.
