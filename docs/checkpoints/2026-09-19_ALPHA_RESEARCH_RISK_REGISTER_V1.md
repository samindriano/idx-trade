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
| R-15 | H-EXC-02 high churn, horizon dependence, and residual basis exposure | New absolute-distance balance has exact score domain `[-1,1]`, `308,067` finite eligible rows, mean 5-session Top-30 turnover `40.7750%`, and maximum `86.6667%`; 20/60 reduce turnover but have only `34.7905% / 24.3750% / 42.3333%` pairwise overlap, while the 188-row CA stress leaves `99.9722%` mean and `93.3333%` minimum Top-30 overlap but changes `3,977` ranks. | Numerical stability and lower long-horizon turnover do not establish one robust representation, capacity, predictive value, or global PIT/CA basis safety. | `OPEN / CAUTION` | Keep all horizons as future research only; require novelty, price-basis, capacity, and Data QA admission before any candidate decision. |
| R-16 | H-MICRO-02 Open capability and source semantics | Positive finite Open exists on `201,415/310,761` eligible rows (`64.8135%`); all `1,201` eligible dates have at least 30 Open rows, but provenance is split IDX/Yahoo with `20,995` source transitions and no admitted available-at/execution contract. | Structural Open coverage is broad enough for inspection but cannot support PIT-safe overnight/intraday evaluation or source selection. | `OPEN / BLOCKED` | Preserve as partial capability only; require independent source, knowledge-time, CA-basis, identity, and execution admission. |
| R-09 | Dataset-Saham-IDX source admission | `1,014` CSVs and useful OHLCV/foreign/bid-offer fields exist, but no row-level knowledge-time/vintage contract and 11 non-identical duplicate ticker copies. | Data availability cannot be converted into PIT scientific evidence. | `OPEN / BLOCKED` | Preserve as blocked unless an independent source-selection/PIT/identity audit can pass. |
| R-10 | Incumbent/common-support identity | Internal C1-C4 correlations are structural only; same-window immutable incumbent identity is not admitted for predictive comparison. | Low/high structural overlap cannot establish incremental alpha. | `OPEN / BLOCKED` | Verify immutable incumbent/common support only after Data QA admission. |
| R-11 | Protected target and prospective state | H5/H10, forward returns, labels, target-derived incumbent scores, counters, and prospective vault remain protected. | Predictive/OOS/IC/ICIR claims are prohibited. | `OPEN / BLOCKED` | Keep target firewall absolute; execute packet only after independent admission. |
| R-12 | Process-level access attestation | Phase-Q access flags are self-attested; they are not independent proof of absence. | A false-green access claim could invalidate downstream evidence. | `OPEN / UNKNOWN` | Maintain explicit access flags and commission independent red-team review before re-entry. |
| R-13 | Candidate-budget expansion | H-LIQ, H-VOL, and H-EXC are not in the protected four-ID packet; exact H-EXC is rejected. | Discovery could silently become post-hoc multiple testing. | `CONTROLLED` | Keep packet exactly C1-C4; require a new frozen decision for any expansion. |
| R-14 | Lane isolation and production contamination | Current branch is `codex/alpha-available-data-20260919`; derived outputs are staged externally; main/canonical/capture/cloud/telemetry were not modified in this lane. | Boundary failure would contaminate active model/data work. | `CONTROLLED` | Recheck branch, worktree, output root, and protected flags at every milestone. |
| R-17 | Robustness lookback alignment | The historical V1 lookback replay attached variants positionally after a reset-index merge; its low overlap values are not reliable. Key-aligned V2 replay corrected the implementation and preserved V1 for lineage. | Stale low-overlap values could overstate horizon instability. | `CLOSED / TOOLING` | Use only the V2 key-aligned artifact; do not cite V1 lookback metrics as current evidence. |
| R-18 | Combination liquidity percentile denominator | Historical V1 ranked value/volume over the full panel while selection used eligible rows. V2 now ranks within eligible rows by date; V1 exposure percentages are superseded. | Liquidity concentration was materially understated in the old combination report. | `CLOSED / TOOLING` | Use V2 eligible-only exposure; retain real capacity as `OPEN / CAUTION`. |
| R-19 | Research artifact hash declaration shape | Active target-free artifacts use several compatible hash locations (`source_hashes`, `inputs`, manifest `files`, or direct fields), which previously required caller-specific interpretation. | A future artifact could be read without verifying the intended code/input identity. | `CLOSED / TOOLING` | Use `research/verify_alpha_research_artifact_contract_v1.py`; pass every required input explicitly and use `--require-manifest` when the experiment contract requires a manifest. |

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

## Continuation risk additions — 2026-09-19

| Risk | Evidence | Status | Control |
|---|---|---|---|
| Reporting-age public availability | `70,931` age rows are internally coherent, but coverage begins in 2024 and knowledge time is not independently public-availability authority | `OPEN / UNKNOWN` | No pre-2024 fill; retain FILINGAGE-01 as source capability only |
| Execution-state semantics | `1,104,064` official rows reconcile exactly, but `NO_TRADE` semantics, completeness, PIT timing, vintage, and identity remain unresolved | `OPEN / UNKNOWN` | Do not reinterpret as suspension, illiquidity, or executable capacity |
| Suspension interval coverage | `471` duplicate expanded key groups; `120,498/121,666` unique no-trade keys outside available regular intervals | `OPEN / BLOCKED` | No silent deduplication or interval-based imputation |
| Sector membership/PIT | Structured 2022/2023 snapshots only; PDF-only gaps, `GWSA/KOTA` cross-sheet duplicates, no daily membership/identity/vintage | `OPEN / UNKNOWN` | No daily expansion or sector feature admission |
| CA residual population | `0/188` unresolved scale rows overlap retained HLC overlay; listing interval is narrow evidence only | `OPEN / UNKNOWN` | Require event-level issuer/ISIN/basis authority |
| C1/C2/C4 verifier scope | v2 independently checks stored artifact/structural invariants but does not rebuild the feature constructor or eligibility masks from raw inputs | `OPEN / UNKNOWN` | Do not describe it as full source-recomputing certification; preserve scope limitation |
| Re-entry packet freshness | Current V2 packet/contract remain frozen to an earlier manifest/commit; the contract manifest head differs from the current lane head | `OPEN / UNKNOWN` | Treat V2 as specification-only; do not execute or silently rewrite hashes; re-verify freshness only after an explicit packet update |
| H-LIQ temporal persistence | Six 100-session blocks show Q4 H-LIQ/C2 dependence `0.0762–0.3053` and bottom-value Q1 share `29.47%–51.30%` | `OPEN / UNKNOWN` | Keep H-LIQ no-C5; do not claim stable novelty or economic meaning |
| CA/issuer-basis red-team | HLC overlay covers only `1,657/981,940` rows; residual `188` keys are disjoint; security master lacks issuer/ISIN transition authority; C1 minimum Top-30 overlap under basis stress is `36.667%` | `OPEN / BLOCKED` | No global same-basis certification, price repair, or issuer-continuity inference without event-level authority |
| Capacity/friction tails | Six-surface artifact adds q95/q99/max turnover, concentration, and three quartile families; H-EXC-02 fixed-window max turnover `86.6667%`, H-LIQ Q1 value share `39.6722%`, H-VOL Q1 value share `40.6889%` | `OPEN / BLOCKED` | Use as structural caution only; require ADV/spread/queue/fill/executable-capacity authority |
| New mechanism surface | Bounded review found no unrepresented PIT-defensible OHLCV/value mechanism; effort-vs-result and breakout/dispersion directions are covered, redundant, or closed | `CLOSED / NO NEW CANDIDATE` | Do not run near-duplicate formula sweeps; reopen only with a new information source or contract |
| C3 capability denominator | Existing contract map mixes full eligible-panel denominator `310,761` with matched eligible financial-source denominator `249,333`; quality-core remains capability-only | `OPEN / DOCUMENTATION` | Report both denominators explicitly; do not treat quality-core as a frozen candidate or coverage rescue |
| Packet producer/attestation split | Producer pin `10939862...` is valid and byte-consistent, but packet/contract arrived later and prior freshness memo is stale | `OPEN / UNKNOWN` | Preserve producer pin; bind future packet updates to producer `P` and attest packet commit `Q` separately |
| Dataset-Saham-IDX provenance | Independent red-team confirms `337` missing admitted sessions, `11` non-identical duplicate folder groups, and no row-level vintage/PIT field | `OPEN / BLOCKED` | Keep source not admitted; no feature construction or fallback-source promotion |
| BBCA deep-history basis divergence | TradingView/IDX price basis is exactly 5x through 2021-10-12 and 1x thereafter; Investing has `0/1,568` exact OHLCV matches and variable scale | `OPEN / BLOCKED` | Do not rescale, merge, or admit either surface without authoritative basis/PIT/issuer/CA evidence |
| C1/C2/C4 readiness red-team | Independent challenge leaves full constructor/PIT/population proof unknown; CA basis and executable capacity fail readiness; C1/C4 are not additive-independent | `OPEN / BLOCKED` | Keep C1-C4 conditional and combinations outside packet; require new authority before re-entry |
| BBCA event-level CA linkage | 61-row BBCA trace is exact against IDX, but retained 26-row event census and 162-row transition ledger contain `0` BBCA rows | `OPEN / BLOCKED` | Treat the trace as forensic context only; do not infer event/effective date/ratio/issuer/ISIN or rescale history |
| Panel-depth field semantics | 19 fields are structurally populated, but price/value units, frequency meaning, aggregation, publication timing, and field-level provenance are incomplete | `OPEN / BLOCKED` | Keep the field contract structural-only; no feature or candidate admission |
| Quote-state timing and executability | Bid/offer is populated and ordered on both-positive rows, but timestamp/age/depth/queue/fill semantics are absent | `OPEN / BLOCKED` | Treat bid/offer as a future raw-input surface only; do not claim executable capacity or run C5 |
| Foreign-flow interpretation | Share and value net arithmetic is exact, but actor scope, currency/unit, aggregation, PIT, and revision/vintage are unknown | `OPEN / BLOCKED` | Keep foreign-flow in the existing H-FLOW family; no new mechanism card or predictive use |
| Listed-share transitions | 23 adjacent transitions appear across 6 symbols without event-level linkage | `OPEN / BLOCKED` | Do not map transitions to corporate actions, effective dates, issuer/ISIN, or price-basis repair |

These additions are source and provenance risks only; they do not authorize
protected evaluation or candidate-budget expansion.

| Candidate CA-exposure completeness | Existing replay covers only a 188-key forensic residual and has no complete event-to-window issuer/ISIN/PIT linkage | `OPEN / BLOCKED` | Treat C1/C2/C4/H-LIQ results as bounded sensitivity only; require independently admitted population-wide transition authority |
| Re-entry packet current-head freshness | Packet-bound Git files are unchanged from Q to R and current source hashes match, but external bytes were not attested at Q | `OPEN / UNKNOWN` | Record packet byte freshness separately; do not call the packet fully fresh or execute it |

- Current branch: `codex/alpha-available-data-20260919`
- Current checkpoint family: `2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`,
  `2026-09-19_ALPHA_RESEARCH_PHASE_MATRIX_V1.md`, and
  `2026-09-19_ALPHA_RESEARCH_CHATGPT_HANDOFF_V3.md`
- H-EXC evidence: `2026-09-19_ALPHA_HEXC01_EXCURSION_ASYMMETRY_RESULT_V1.md`
- H-VOL evidence: `2026-09-19_ALPHA_HVOL01_HORIZON_STABILITY_RESULT_V1.md` and
  `2026-09-19_ALPHA_HVOL01_CA_SENSITIVITY_RESULT_V1.md`
- No protected outcome or production artifact was accessed or modified.
