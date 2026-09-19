# IDX-Trade Long-Horizon Alpha Research — Current Final Handoff V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Latest verified current HEAD before this documentation amendment: `8f98e09d2fa587219b233d581023b0ea73de7e5e`
Latest research milestone: `8f98e09d` — local data-surface closure review
Latest status/documentation: `2026-09-20_ALPHA_PACKET_CONTRACT_FIREWALL_HARDENING_RESULT_V1.md`
Status: `PRE-ADMISSION RESEARCH ACTIVE / HISTORICAL TARGET STAGE BLOCKED`

Latest concise status read-in: `2026-09-19_ALPHA_RESEARCH_CURRENT_STATUS_V2.md`
Latest adversarial result: `2026-09-20_ALPHA_C1234_REDTEAM_ADJUDICATION_V1.md`
Latest CA/price-basis result: `2026-09-20_ALPHA_CA_ISSUER_PRICE_BASIS_ADMISSION_SPEC_V1.md`
Latest H-LIQ novelty result: `2026-09-20_ALPHA_HLIQ01_NOVELTY_NO_RETRY_ADJUDICATION_V1.md`
Latest H-LIQ source decomposition result: `2026-09-19_ALPHA_HLIQ01_SOURCE_DECOMPOSITION_RESULT_V1.md`
Latest H-FRAG-01 source audit: `2026-09-19_ALPHA_HFRAG01_SOURCE_AUDIT_RESULT_V1.md`
Latest H-FRAG-01 independent verifier: `research/verify_alpha_hfrag01_source_audit_v1.py`
Latest FILINGAGE-01 source audit: `2026-09-19_ALPHA_FILINGAGE01_SOURCE_AUDIT_RESULT_V1.md`
Latest EXECSTATE-01 source audit: `2026-09-19_ALPHA_EXECSTATE01_SOURCE_AUDIT_RESULT_V1.md`
Latest SUSPSTATE-01 reconciliation: `2026-09-19_ALPHA_SUSPSTATE01_RECONCILIATION_RESULT_V1.md`
Latest CA residual coverage: `2026-09-19_ALPHA_CA_RESIDUAL_COVERAGE_RESULT_V1.md`
Latest SECTOR-01 source audit: `2026-09-19_ALPHA_SECTOR01_SOURCE_AUDIT_RESULT_V1.md`
Latest literature mechanism card: `2026-09-19_ALPHA_LITERATURE_MECHANISM_CARD_REVERSAL_LIQUIDITY_V1.md`
Latest C1/C2/C4 verifier-scope adjudication: `2026-09-19_ALPHA_C1234_REDTEAM_SCOPE_ADJUDICATION_RESULT_V1.md`
Latest H-LIQ temporal persistence red-team: `2026-09-19_ALPHA_HLIQ01_TEMPORAL_PERSISTENCE_REDTEAM_RESULT_V1.md`
Latest re-entry packet freshness audit: `2026-09-19_ALPHA_REENTRY_PACKET_FRESHNESS_AUDIT_RESULT_V1.md`
Latest H-LIQ independent verifier: `research/verify_alpha_hliq01_source_decomposition_v1.py`
Current future-evaluation packet: `2026-09-19_ALPHA_FUTURE_EVALUATION_PACKET_V2.md`
Latest re-entry contract closure: `2026-09-19_ALPHA_REENTRY_PACKET_CONTRACT_CLOSURE_RESULT_V1.md`
Latest re-entry verifier: `research/verify_alpha_future_evaluation_packet_v2.py`
Latest H-VOL result: `2026-09-19_ALPHA_HVOL01_CA_SENSITIVITY_RESULT_V1.md`
Latest H-VOL horizon audit: `2026-09-19_ALPHA_HVOL01_HORIZON_STABILITY_RESULT_V1.md`
Latest H-EXC result: `2026-09-19_ALPHA_HEXC01_EXCURSION_ASYMMETRY_RESULT_V1.md`
Latest H-EXC-02 result: `2026-09-19_ALPHA_HEXC02_BOUNDED_EXCURSION_RESULT_V1.md`
Latest H-EXC-02 CA sensitivity: `2026-09-19_ALPHA_HEXC02_CA_SENSITIVITY_RESULT_V1.md`
Latest H-EXC-02 horizon stability: `2026-09-19_ALPHA_HEXC02_HORIZON_RESULT_V1.md`
Latest Open capability audit: `2026-09-19_ALPHA_OPEN_CAPABILITY_RESULT_V1.md`
Latest corrected robustness/combination replay: `2026-09-19_ALPHA_PHASE_Q_REDTEAM_CORRECTION_RESULT_V1.md`
Latest current-head packet attestation: `2026-09-20_ALPHA_REENTRY_PACKET_CURRENT_HEAD_ATTESTATION_RESULT_V1.md`
Latest HSC ownership source audit: `2026-09-20_ALPHA_HSC_OWNERSHIP_EVENT_SOURCE_AUDIT_RESULT_V1.md`
Latest broker/margin source audit: `2026-09-20_ALPHA_BROKER_MARGIN_SNAPSHOT_SOURCE_AUDIT_RESULT_V1.md`
Latest handoff/control and local-surface review: `2026-09-20_ALPHA_CONTROL_AND_SURFACE_REDTEAM_RESULT_V1.md`
Latest packet contract/firewall hardening: `2026-09-20_ALPHA_PACKET_CONTRACT_FIREWALL_HARDENING_RESULT_V1.md`
Latest local data-surface closure review: `2026-09-20_ALPHA_LOCAL_DATA_SURFACE_REVIEW_NO_NEW_EVIDENCE_V1.md`
Latest completion audit: `2026-09-20_ALPHA_PROGRAM_COMPLETION_AUDIT_V1.md`

This is the current read-in document for a future ChatGPT session. Detailed
evidence remains in the linked checkpoint documents; this handoff records the
decision state, boundaries, and exact next action in one place.

## Executive summary

The program has completed the bounded pre-admission structural work for the
corrected C1-C4 portfolio, C3 capability decomposition, target-free
orthogonality, structural robustness, H-LIQ-01 novelty review, identity
continuity, and equal-weight combination/economics readiness. No target or
protected outcome was opened. No candidate has predictive evidence or survivor
status.

The latest main-run adversarial audit of C1/C2/C4 also passed all target-free
static, schema/key, calendar, identity-interval, mask, and numerical checks.
This is structural evidence only and does not replace the still-missing
independent Phase-Q red-team or Data QA admission.

The independent Phase-Q red-team subsequently found two historical report
defects. The old robustness lookback replay used positional variant alignment
after a reset-index merge, and the old combination report used a full-panel
liquidity percentile denominator. Corrected V2 replays are now authoritative
for those structural claims; V1 artifacts remain preserved for lineage. The
corrected values strengthen liquidity caution but do not change candidate or
packet status.

The latest CA/price-basis audit found that the known 1,657-row HLC overlay is
already represented in the current panel and replay does not change C1/C2/C4,
but 188 non-stable scale rows and open-price residuals remain unresolved. This
narrows exposure without clearing the admission blocker.

Using the unresolved rows only as a forensic sensitivity test, C1 showed the
largest basis fragility (10.617% rank changes; 36.667% minimum Top-30 overlap),
while C2/C4 were materially more stable. This is not a corrected dataset or a
predictive result; C1 remains blocked on basis resolution.

The H-LIQ novelty diagnostic supports a distinct temporal-variability
mechanism relative to C2 overall, but dependence rises in the top-value bucket
(0.468 versus the turnover-level component). H-LIQ remains a future hypothesis
and no C5 ID is admitted.

The fixed C2 turnover-level source-decomposition replay was independently
recomputed. It reduces H-LIQ's mean daily Spearman against that level
component from `0.1647556` to `0.0157646`, but residual dependence with full C2
remains `0.0843185`; bottom-value Q1 exposure worsens from `39.6722%` to
`50.3889%`. This establishes only
`STRUCTURAL_NONREDUNDANCY_VS_C2_LEVEL_ONLY`, not mechanism-level novelty or
economic readiness. H-LIQ remains `FUTURE_RESEARCH / NOVELTY_PENDING /
ECONOMIC_CAUTION` and no C5 ID is created. The generator, independent
verifier, guarded feature schema, and both JSON outputs also passed the
outcome-blind target firewall; firewall artifact SHA-256 is
`64911263e31b24e200f789491f187719c033aecf76749bb58e38d53f0ade30f7`.

The stale re-entry attestation was replaced by a V2 machine-readable contract.
It binds source/manifest/code hashes, key digests, candidate missingness and
tie rules, robustness/friction evidence, and a fail-closed C3 gate. Independent
contract verification and firewall both pass, but this is only specification
closure: the verdict remains `NO-GO_FOR_REENTRY / BLOCKED_BY_DATA_ADMISSION`.

The isolated H-FRAG-01 source audit found a coherent official stock-summary
cache with `1,104,064` rows and exact `981,940/981,940` panel overlap for the
reconciliation fields. The preregistered ratio validity gate nevertheless
fails on `8,750` non-regular-volume rows and `7` non-regular-frequency rows
outside `[0,1]`. Independent source verification and target/privacy firewalls
pass, but the surface remains `SOURCE_BLOCKED / PARTIAL`; no C5 or packet
expansion is authorized.

Current conclusion:

`NO CURRENT ALPHA SURVIVOR CAN BE PROVEN WITHOUT TARGET ADMISSION`

The next useful work is limited to admission-quality identity/price-basis and
capacity evidence, plus independent H-FRAG field-semantics, available-at,
revision/vintage, and identity review before any candidate is marked ready.
Repeating C1-C4 structural calculations or broad provider searches would be
redundant without new evidence.

## Current scientific boundary

Blocked until an independently reviewed Data QA admission artifact exists:

- H5/H10 targets, forward returns, protected labels, or target-derived
  incumbent predictions;
- IC, ICIR, OOS, candidate/incumbent predictive comparison, target-ranked
  spread, superiority, or `RESEARCH_SURVIVOR` claims;
- proxy reconstruction of protected labels, future-outcome tuning, or model
  promotion.

This lane also does not modify incumbent alpha, V4-X1, Decision V2, canonical
datasets/history, protected vaults/counters, capture/runtime, cloud/R2,
scheduler, production jobs, or production artifacts.

## All datasets discovered and data admissibility matrix

| Dataset/source | Capability | Disposition |
|---|---|---|
| Clean OHLCV panel | 981,940 rows, 945 tickers, 1,260 dates; OHLCV/value/provenance fields | `PARTIAL / FROZEN_ONLY`; structural use only |
| Dataset-Saham-IDX historical raw corpus | 1,014 CSVs / 1,146,324 rows; four unmapped tickers and 11 non-identical duplicate ticker groups | `BLOCKED / NOT_ADMITTED`; no row-level PIT/publication/revision-vintage or authoritative CA contract |
| Official sessions | 1,260 official dates | `PARTIAL / FROZEN_ONLY`; calendar/mask only |
| Tradability anchors | 1,104,064 anchors | `PARTIAL / FROZEN_ONLY`; same-session mask only |
| Financial PIT bundle | 277,244 rows; partial knowledge/provenance coverage | `PARTIAL / PARKED`; C3 capability only |
| Activity metadata | 105/963 populated `activity_median_regular_value_60` snapshot rows; no date history/available-at timestamp | `METADATA_ONLY / NON-ADMISSIBLE` |
| Sector/industry, spread, order book, ADV, disclosure, ownership, foreign flow | leads, snapshots, or partial/blocked archives | no new PIT-admissible source |
| H5/H10/prospective/forward outcome artifacts | protected | `BLOCKED`; never opened |

Detailed inventory: `2026-09-19_ALPHA_DATA_INVENTORY_RESULT_V1.md` and
`2026-09-19_DATA_CAPABILITY_MATRIX_V1.md`.

## Previous alpha families and failure taxonomy

Archaeology covered V2, V3-A–E, V3-B correction, V4-A–C, V4-X1 lineage,
financial, participation, price-path, effort-vs-result, foreign-flow,
ownership/free-float, suspension/resumption, and auxiliary experiments.

Failure classes retained:

- engineering conformance failure;
- `DATA_FAIL`, `PIT_FAIL`, `COVERAGE_FAIL`, `REPRESENTATION_FAIL`,
  `MODEL_FAIL`, `OOS_FAIL`, `ROBUSTNESS_FAIL`, `ECONOMICS_FAIL`,
  `REDUNDANCY_FAIL`, `INFRASTRUCTURE_FAIL`, `INCONCLUSIVE`;
- source-admission, partial-capability, semantic-source-invalid, and
  untested-family distinctions.

Exact family dispositions are in `2026-09-19_ALPHA_ARCHAEOLOGY_RESULT_V1.md`
and `2026-09-19_ALPHA_FAILURE_TAXONOMY_V1.md`.

## Current candidates

| ID | Structural result | Economic/coverage result | Status |
|---|---|---|---|
| C1 residual reversal | 295,243 finite rows / 95.0065% | 42.15% Top-30 turnover; 25.29 bps base burden | `FUTURE_RESEARCH` |
| C2 participation confirmation | 310,761 / 100% | 32.91%; 19.75 bps | `FUTURE_RESEARCH` |
| C3 financial quality/growth | 30,994 / 9.9736%; 278 usable Top-30 dates | sparse/late PIT support; 25.77% top-10 slot share | `BLOCKED` |
| C4 path efficiency reversal | 310,323 / 99.8591% | 23.70%; 14.22 bps | `FUTURE_RESEARCH` |

## New candidates and structural combinations

No new candidate ID was created. H-LIQ-01 remains
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; it is not C5.

H-VOL-01 is a second future hypothesis, not a candidate ID. Its fixed
compression state has broad structural support and low bounded overlap, but
the 188-row CA stress changed 547 scores and 8,876 ranks, with minimum Top-30
overlap of 86.6667%. Keep it at
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; it is not in the
protected four-ID packet.

The fixed horizon audit (`5/20`, `5/60`, `20/120`) shows material horizon
dependence in turnover, support, and Top-30 membership. The baseline reproduces
exactly, but no horizon is selected and H-VOL remains outside the packet.

H-EXC-02 is a separate new contract for the broader excursion mechanism, not
a rescue of H-EXC-01. Its absolute-distance balance is exactly bounded in
`[-1,1]` with `308,067` finite eligible rows, but mean/max Top-30 turnover is
`40.7750% / 86.6667%`. It remains
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 ID or packet
change was made. See `2026-09-19_ALPHA_HEXC02_BOUNDED_EXCURSION_RESULT_V1.md`.

Its dedicated 188-row CA sensitivity leaves support unchanged and preserves
`99.9722% / 93.3333%` mean/minimum Top-30 overlap, but changes `3,977` ranks
through direct and spillover effects. This is forensic narrowing only; global
PIT/CA authority, capacity, and candidate readiness remain unresolved. See
`2026-09-19_ALPHA_HEXC02_CA_SENSITIVITY_RESULT_V1.md`.

The fixed H-EXC-02 horizon audit evaluated `5/20/60`: mean turnover fell to
`40.7750% / 20.4944% / 11.7570%`, but pairwise Top-30 overlap was only
`34.7905% / 24.3750% / 42.3333%`. No horizon was selected; longer windows
remain distinct future representations and do not repair the family or prove
predictive value. See `2026-09-19_ALPHA_HEXC02_HORIZON_RESULT_V1.md`.

The historical Open capability audit found `201,415/310,761` eligible rows
(`64.8135%`) with positive finite Open and at least 30 Open rows on every
eligible date. Provenance is split between IDX and Yahoo with `20,995` source
transitions; available-at, PIT, CA-basis, identity, and execution semantics
remain unadmitted. H-MICRO-02 is now classified
`PARTIAL_CAPABILITY / BLOCKED_SOURCE_ADMISSION`, not C5. See
`2026-09-19_ALPHA_OPEN_CAPABILITY_RESULT_V1.md`.

Four equal-weight structural combination hypotheses were measured separately:
C1+C2, C1+C4, C2+C4, and C1+C2+C4. C1+C4 had the lowest tested combination
turnover at 34.85% and balanced component overlap, but no weights were
optimized and none is in the protected four-ID packet.

## Structurally rejected, blocked, and ready-for-reentry directions

- Rejected/closed: invalid early Stage-A implementation, exact breakout
  formulation, exact additive foreign-flow formulation, semantically invalid
  margin interpretation, and the raw H-EXC-01 excursion representation for
  numerical unboundedness/churn. H-EXC-02 is bounded but high-churn and
  remains future research only; the broader excursion mechanism is not
  predictively tested.
- Blocked: C3 scientific evaluation, all target/incumbent comparisons,
  incomplete PIT/identity/CA/revision authority, and metadata-only activity
  snapshot reuse.
- Ready for re-entry: none today. C1/C2/C4 are conditionally engineering-ready
  only; they require the admission artifact and common-support target. H-LIQ-
  01 and H-VOL-01 remain future research and are not ready.

## Structural orthogonality and economics

Internal Spearman diagnostics: C1/C2 `-0.2304`, C1/C3 `-0.0237`, C1/C4
`0.4113`, C2/C3 `-0.0455`, C2/C4 `-0.1191`, C3/C4 `-0.0326`. Daily map
identifies C1/C4 as the main duplicate-mechanism caution. These are structural
only, not incremental alpha.

Base economics uses 15 bps buy fee, 25 bps sell fee, and 10 bps slippage per
side. Combination scenarios additionally test 40 bps low and 110 bps stress
matched turnover. Real spread, queue position, ADV, and capacity history are
not admitted, so all burdens are structural sensitivities. A separate value
capacity stress at 0.25%/0.5%/1%/2% gives 1% q10 proxies of IDR 7.63m/6.40m/
13.03m/5.02m for C1/C2/C3/C4; this does not change candidate status.

## PIT/provenance risks

Population completeness, historical-as-of authority, issuer/ISIN continuity,
corporate-action transition basis, revision/vintage completeness, sector
history, and authoritative historical liquidity remain unresolved. The
security-master interval audit maps all frozen eligible keys one-to-one, but
does not certify corporate-action or price-basis correctness.

## Reusable tooling and artifacts

- target-access firewall and independent schema/hash checks;
- corrected Stage-A builder/verifier;
- economics and Top-K structural lab;
- temporal/normalization/missingness/universe robustness harness;
- H-LIQ-01 structural and adversarial harness;
- H-LIQ-01 source-decomposition generator, independent recomputation
  verifier, artifact hash contract, and outcome-blind firewall;
- V2 future-evaluation packet contract, source/key/hash verifier, and
  fail-closed C3 execution gate;
- C3 capability and contract-map verifier;
- identity-continuity audit;
- equal-weight combination and friction-scenario harness;
- regular-market-value capacity stress harness;
- future evaluation packet, phase matrix, candidate registry, ledger, risk
  register, re-entry queue, data capability matrix, and future-data map.

Phase coverage matrix: `2026-09-19_ALPHA_RESEARCH_PHASE_MATRIX_V1.md`.
Capacity proxy detail: `2026-09-19_ALPHA_CAPACITY_STRESS_RESULT_V1.md`.
Current status read-in: `2026-09-19_ALPHA_RESEARCH_CURRENT_STATUS_V2.md`.
Adversarial detail: `2026-09-19_ALPHA_C1234_ADVERSARIAL_RESULT_V1.md`.
Historical/stale re-entry packet audit: `2026-09-19_ALPHA_REENTRY_PACKET_AUDIT_RESULT_V2.md`; use the V2 contract closure instead.
Risk register: `2026-09-19_ALPHA_RESEARCH_RISK_REGISTER_V1.md`.

## Do not retry without new evidence

- Do not open protected targets, forward returns, incumbent score artifacts,
  counters, or prospective vaults.
- Do not scrape or add Zapi/IDX/TradingView/Investing/Stockbit providers just
  to fill current structural gaps.
- Do not retry failed exact formulations, monotone duplicates, sparse C3
  variants, metadata-only activity snapshot reuse, or raw H-EXC-01 without a
  new preregistered numerical contract.
- Do not optimize combination weights, refit, rescue, sign-flip, or expand the
  candidate budget before a new frozen protocol decision.
- Do not use the superseded V1 robustness lookback overlaps or V1 combination
  liquidity-exposure percentages; use the key-aligned/eligible-only V2 replay.

## Future data opportunities

Highest-value opportunities are population-wide PIT financial vintages,
sector/industry intervals with available-at timestamps, event-level corporate
action transitions, issuer identity history, historical liquidity/spread/order
book, and PIT foreign-flow/ownership/disclosure data. Each requires source
authority, identity mapping, revision/vintage, licensing, and admission proof.

## Protected evaluation packet status

`2026-09-19_ALPHA_FUTURE_EVALUATION_PACKET_V2.md` is the current
specification-only packet for exactly C1-C4: fixed target, population, six
folds, purge/embargo, metrics, gates, friction assumptions, robustness, and
one-shot stopping rule. V1 is superseded and the current packet is not
executable before independent Data QA admission.

## Exact next step when Data QA admission arrives

1. Read fresh canonical `origin/main:coordination/TEAM_STATUS.md` and the new
   admission artifact.
2. Verify population completeness, PIT/as-of, identity/calendar,
   corporate-action basis, revision/vintage, H5/H10 authority, and immutable
   incumbent common-support identity.
3. If any gate fails or is unknown, do not open outcomes and leave all statuses
   unchanged.
4. If every gate passes, execute the frozen C1-C4 comparison once, with no
   rescue/refit/variant sweep, then report the predeclared metrics and gates.

## Repository, artifacts, hashes, tests, unresolved risks

- Repository/worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`
- Branch: `codex/alpha-available-data-20260919`
- Latest verified current HEAD before this documentation amendment: `58f094b8b59b8933bee6cf2f9996f433a57391a4`
- Canonical `origin/main` was not modified.
- Derived staging root:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`
- Combination builder SHA-256: `a326d8d40933562f2de3a3137adc2a0280529d3db610ed2c6ce5224b73568591`.
- Combination verifier SHA-256: `3e8b7ad0a2cc3d760bd56f0838c1a2e76878bc9e97ba86c257159e33aa0889bc`.
- Combination output SHA-256: `82c76798f5135f345e41f9d536497f68908b3744107d951b583d6a3297de985d`.
- Corrected robustness V2 code/output SHA-256: `d5b07ff38cb61723bc4a3470e2716857cf5a5dbb5227baaf5f3f98e4f7bb63ee` /
  `64d03527b7bb504dee34e854ed9123f03fb55c557a455462eef46a928c823444`.
- Corrected combination V2 code/output SHA-256: `5c1db06448f656f7a11a1217a7e05887c398beeb7900592eed2f8432f1d971ff` /
  `87b195ea6cbd281d861932bd9bdf2935c9538bfb6b5031bee2dbf60675ee6c2f`.
- Reusable artifact hash-contract verifier: `research/verify_alpha_research_artifact_contract_v1.py`, SHA-256
  `c587bba69fbfdd77cf9ea4f5ce0dbda191ec5efd191bff55355f0b32cf9ca138`;
  PASS report SHA-256 `2b8064b51f34b6de084f1facd070cc2288d0270e707c0b6798a3b2e2767615ad`.
- Combination firewall SHA-256: `4d00cace99225d5286c5143698622a85a735564b5ee6955bab98007038d679f4`.
- H-LIQ source-decomposition generator SHA-256:
  `be3880729cd5defc5509c7b7dd8bae06548b475e9305b73e0e9c112506576531`;
  independent verifier SHA-256
  `409a2b66e9bd99080007301d94dd2ab3b08dccf25b06a1fb46bf65ea528fdd66`;
  generated artifact SHA-256
  `352a422086d540318f0464aaec2b80b3eb427a87176caa0326559242dacfc35e`;
  firewall SHA-256
  `64911263e31b24e200f789491f187719c033aecf76749bb58e38d53f0ade30f7`.
- V2 packet SHA-256:
  `44fb9b2202a120076bb5fb40610a30baaf9ff3515d3df9efdb1a58b32862c049`;
  contract SHA-256
  `3f46b1d810928f50c1c85fa76146dff881cdd38bc7f4e4315d2862de7c9dbfd8`;
  verification SHA-256
  `20fe7c5138275c4491c3c20785504e6cb0cf24a07ee80c4dfce733d960ea19bc`;
  firewall SHA-256
  `71ea4f84dee8effbd2b7b8484546c7ce2fdf7f06859449a034b654d6fd2d7fed`.
- Other structural code/output hashes are recorded in their result docs and
  staging JSON manifests; all are isolated and target-free.
- Tests: Python compilation `PASS`; C3 verifier `PASS`; independent H-LIQ
  source recomputation `PASS`; corrected V2
  verifiers `PASS`; V2 re-entry contract verifier `PASS`; outcome-blind target firewall `PASS`; artifact hash
- H-FRAG-01 source audit and independent source inventory verifier `PASS` at
  their respective integrity/firewall layers; scientific disposition remains
  `SOURCE_BLOCKED / PARTIAL` because the preregistered boundedness gate failed.
  contract PASS plus deliberate wrong-code/required-manifest FAIL paths;
  git worktree was clean at baseline.
- Unresolved risks: authoritative admission, corporate-action/price basis,
  real capacity, sector/PIT history, and mechanism-level novelty; the latest
  independent red-team correction replay is complete but remains structural.

### 2026-09-19 continuation addendum

Four additional read-only, outcome-blind source audits are now durable in this
lane. FILINGAGE-01 is a partial reporting-age capability (`70,931` coherent
age rows, coverage from 2024 only) and remains not admitted. EXECSTATE-01 is a
coherent official execution-state source (`1,104,064` rows; `1,260` sessions;
`982,398 ACTIVE` and `121,666 NO_TRADE`) but its exchange semantics, PIT timing,
completeness, vintage, and identity authority remain unknown. SUSPSTATE-01 is
source-blocked because the interval expansion has `471` duplicate key groups
and covers only `1,168` regular interval/no-trade rows while `120,498/121,666`
unique no-trade keys are outside the available regular intervals. The CA
residual check confirms `0/188` overlap with the retained HLC overlay; issuer/
ISIN transition and event semantics remain unknown.

Result documents:

- `2026-09-19_ALPHA_FILINGAGE01_SOURCE_AUDIT_RESULT_V1.md`
- `2026-09-19_ALPHA_EXECSTATE01_SOURCE_AUDIT_RESULT_V1.md`
- `2026-09-19_ALPHA_SUSPSTATE01_RECONCILIATION_RESULT_V1.md`
- `2026-09-19_ALPHA_CA_RESIDUAL_COVERAGE_RESULT_V1.md`

The corresponding generators, independent verifiers, hash contracts, and
target/privacy firewalls all completed their registered integrity checks. No
target, outcome, provider, cloud, incumbent, canonical data, capture,
scheduler, telemetry, or production state was accessed or changed.

The follow-on SECTOR-01 audit is also complete: `22` structured 2022/2023
sector sheets contain `1,607` rows and `837` unique ticker codes, but only
document-level periods, PDF-only year gaps, two cross-sheet duplicates
(`GWSA`/`KOTA`), and no daily/PIT/identity/vintage authority. Status is
`SOURCE_PARTIAL_STRUCTURAL_SIGNAL / NOT_ADMITTED`; no feature or candidate was
created. See `2026-09-19_ALPHA_SECTOR01_SOURCE_AUDIT_RESULT_V1.md`.

A bounded literature scan did not justify another raw reversal or liquidity
candidate: those mechanisms overlap the already audited C1/C2/H-LIQ families.
It preserved one future specification—industry-adjusted reversal—because it is
mechanistically distinct, but the current sector archive is not PIT-safe for
daily implementation. See
`2026-09-19_ALPHA_LITERATURE_MECHANISM_CARD_REVERSAL_LIQUIDITY_V1.md`.

The H-LIQ temporal persistence red-team passed coverage/mask integrity across
six 100-session blocks, but Q4 H-LIQ/C2 dependence ranged `0.0762–0.3053` and
selected bottom-value Q1 share ranged `29.47%–51.30%`. This fails an
unqualified persistence claim; H-LIQ remains no-C5 and
`NOVELTY_PENDING / ECONOMIC_CAUTION`. See
`2026-09-19_ALPHA_HLIQ01_TEMPORAL_PERSISTENCE_REDTEAM_RESULT_V1.md`.

The re-entry packet freshness audit confirms C1/C2/C3/C4 indexing and C3
fail-closed behavior, but the frozen contract manifest head differs from the
current lane head. Packet freshness is therefore `UNKNOWN`; the V2 packet
remains specification-only and must not be executed. Stale V1 index references
were repaired or labeled historical. See
`2026-09-19_ALPHA_REENTRY_PACKET_FRESHNESS_AUDIT_RESULT_V1.md`.

No predictive superiority claim is made.

### Latest continuation — 2026-09-19 CA, capacity, and mechanism closure

The independent CA/issuer-basis red-team keeps global price-basis admission
blocked: the 1,657-row overlay covers only a narrow panel slice, the 188
residual keys are disjoint, and the security master has no issuer/ISIN
transition chain. C1 is materially sensitive under the registered basis
stress; the other surfaces remain unresolved. See
`2026-09-19_ALPHA_CA_ISSUER_BASIS_REDTEAM_RESULT_V1.md`.

The new tail/concentration artifact covers C1/C2/C4/H-LIQ-01/H-VOL-01/
H-EXC-02 over the fixed 600-session window. It quantifies q95/q99/max turnover
burdens, HHI/effective names, and market-value/raw-volume/dollar-turnover
quartiles. It passes independent structural verification but does not admit
capacity, ADV, spread, queue, or fill semantics. See
`2026-09-19_ALPHA_CAPACITY_FRICTION_TAIL_RESULT_V1.md`.

The bounded mechanism-surface review found no new PIT-defensible candidate from
the admitted OHLCV/value surface. The candidate budget remains exactly C1-C4;
H-LIQ/H-VOL/H-EXC-02 remain future research only. See
`2026-09-19_ALPHA_NEW_MECHANISM_SURFACE_ADJUDICATION_V1.md`.

The C3 capability red-team added a denominator erratum: matched-source rates
are `25.8313%` for quality-core and `12.4308%` for all-five, while the
population-relative full-panel rates are `20.7253%` and `9.9736%`. Quality-core
is not a frozen candidate; C3 remains blocked. Packet provenance is classified
separately as producer binding verified, packet attestation stale, and full
freshness unknown. See
`2026-09-19_C3_CAPABILITY_DENOMINATOR_REDTEAM_ERRATUM_V1.md` and
`2026-09-19_ALPHA_REENTRY_PACKET_PRODUCER_BINDING_RECONCILIATION_RESULT_V1.md`.

The local Zapi probe archive was audited read-only. It contains one BBCA
company-profile snapshot and empty March/August dividend payloads; the profile
fails its official parity review and the dividend probes lack usable selected
rows, ticker identity, and historical timing/revision semantics. Zapi remains
`BLOCKED / NOT_ADMITTED` and creates no new alpha surface. See
`2026-09-19_ALPHA_ZAPI_LOCAL_PROBE_ADMISSION_AUDIT_V1.md`.

The persisted KSEI ownership archive was then quality-audited. Eight annual or
monthly snapshots are structurally clean and overlap 100% of panel tickers on
their exact dates, but cover only `8/1,260` panel dates and do not establish
publication/revision, issuer/ISIN, or effective-free-float authority. The
five current profile probes expose no explicit free-float field. H-FLOW-01 is
therefore a future specification only, not C5 or packet material. See
`2026-09-19_ALPHA_OWNERSHIP_KSEI_SOURCE_AUDIT_RESULT_V1.md`.

The local market-index/breadth archive was subsequently audited read-only. Its
direct and Zapi copies match exactly on three sampled rich dates, with exact
market-total reconciliation on the 2024/2026 samples and an explicit localized
arithmetic exception on the 2021 sample. Only three sampled digital monthly
blocks are present; continuous PIT daily coverage and publication/revision
semantics are not established. The result is
`PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`, with no feature, candidate,
C5, packet, or predictive-status change. See
`2026-09-20_ALPHA_MARKET_CONTEXT_SOURCE_AUDIT_RESULT_V1.md`.

An independent H-LIQ-01 novelty red-team then found no basis for repeating the
same C2-level residualization or temporal-persistence experiment. The residual
retains `0.0843185` dependence with full C2, worsens bottom-value exposure to
`50.3889%`, and its block dependence is unstable. H-LIQ remains
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 or packet change.
See `2026-09-20_ALPHA_HLIQ01_NOVELTY_NO_RETRY_ADJUDICATION_V1.md`.

The local panel-depth archive was then audited in the isolated lane. Its 12
symbols and 18,835 rows pass raw-hash, schema, arithmetic, date, and official
parity checks (23/23 available pairs); BBCA is a duplicate of the existing
historical-depth surface. Missing row-level PIT/available-at, revision,
identity/ISIN, issuer-transition, and corporate-action semantics keep the
source at `PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`. No feature,
candidate, packet, or predictive evaluation was performed. See
`2026-09-20_ALPHA_PANEL_DEPTH_SOURCE_AUDIT_RESULT_V1.md`.

An independent Phase-Q red-team then challenged C1/C2/C4 and combinations.
Replay integrity passes only narrowly; CA price basis and executable capacity
fail readiness, full constructor/PIT/population proof remains unknown, and
C1/C4 are not additive-independent. No candidate or combination was promoted.
See `2026-09-20_ALPHA_C1234_REDTEAM_ADJUDICATION_V1.md`.

The local-data census found no admissible new source. TradingView BBCA max and
Investing BBCA max are the only non-redundant deep-history surfaces and remain
partial/basis-blocked; current snapshots, listings, HTML, technicals, and
Stockbit probes are not historical PIT sources. See
`2026-09-20_ALPHA_DATA_SURFACE_CENSUS_V1.md`.

Their local reconciliation records TradingView at 5x versus IDX through
2021-10-12 and 1x thereafter, while Investing has 0/1,568 exact OHLCV matches
and no constant scale. This is source divergence, not CA truth or admission.
See `2026-09-20_ALPHA_BBCA_PRICE_BASIS_RECONCILIATION_RESULT_V1.md`.

The follow-up BBCA CA-event linkage audit found 61 exact panel/IDX HLC trace
rows but zero BBCA rows in the retained event and transition ledgers. It keeps
the 2021-10-13 alignment as forensic context only; no corporate-action event or
issuer/ISIN transition was certified. See
`2026-09-20_ALPHA_BBCA_CA_EVENT_LINKAGE_RESULT_V1.md`.

The panel-depth field-contract audit then covered all 19 fields across 18,835
rows. Foreign-flow arithmetic and basic bid/offer ordering pass structurally,
but no PIT/revision/identity/CA contract, price or monetary units, quote timing,
depth, or executable semantics are available. Bid/offer therefore remains a
future specification only (`FUTURE_QUOTE_FLOW_INTERACTION_V1`), with no
candidate or C5 evaluation. See
`2026-09-20_ALPHA_PANEL_DEPTH_FIELD_CONTRACT_RESULT_V1.md`.

The independent CA/issuer exposure-completeness review confirms that all
candidate price-basis evidence remains bounded forensic sensitivity, not
population-complete safety. C1 is most fragile under the 188-row comparison;
C2/C4/H-LIQ are not cleared, and no event-to-window issuer/ISIN/PIT linkage is
available. The re-entry packet has current packet-byte freshness through the
latest recorded clean rerun `R2=fbaa824c` (the earlier `R0` and `R1` runs are
retained in attestation history), but full external-source freshness remains
unknown. No candidate status changed and the packet remains
NO-GO. See `2026-09-20_ALPHA_CA_CANDIDATE_EXPOSURE_COMPLETENESS_RESULT_V1.md`.

The extended local census then classified six additional raw surfaces—official
foreign flow, listing/delisting lifecycle, monthly and statutory free-float,
HSC ownership events, and broker/margin category state. All remain partial or
blocked and none changes the candidate registry or protected packet. See
`2026-09-20_ALPHA_LOCAL_DATA_SURFACE_CENSUS_CONTINUATION_V1.md`.

The historical official foreign-flow archive was independently audited and
passes structural/hash/calendar integrity across 1,129,024 rows and 1,288
sessions. It remains blocked for PIT admission because publication time is
unknown and T+1 is only declarative; no issuer/ISIN, CA, revision, or panel
completeness authority was established. It strengthens future H-FLOW
capability without creating a candidate. See
`2026-09-20_ALPHA_FOREIGN_FLOW_HISTORICAL_SOURCE_AUDIT_RESULT_V1.md`.

The listing/delisting lifecycle surface was independently checked after the
foreign-flow audit. Raw/normalized integrity is exact across 440 monthly
files, 962 current rows, and 163 delisting rows, but six lifecycle conflicts
remain and no daily PIT membership, issuer/ISIN, publication-time,
revision/vintage, or corporate-action chain exists. The surface is
capability-only (`PARTIAL / IDENTITY_BLOCKED`); no feature, candidate,
protected-packet, or model status changed. See
`2026-09-20_ALPHA_LISTING_DELISTING_LIFECYCLE_SOURCE_AUDIT_RESULT_V1.md`.

The LBRE free-float surface was then audited independently. Manifest
integrity is exact across 58,671 artifacts, while 868 lineage rows remain
unresolved and the data is monthly issuer-report coverage without a complete
daily PIT/population, issuer/ISIN, CA, revision, or public-availability
contract. The surface remains capability-only
(`PARTIAL / SOURCE_REMEDIATION_REQUIRED`); no feature, candidate, packet, or
model status changed. See
`2026-09-20_ALPHA_LBRE_FREE_FLOAT_SOURCE_AUDIT_RESULT_V1.md`.

The statutory free-float snapshot was then audited independently. Manifest
integrity passes for 2,145 new files and seven reused parent bindings, but
the 2025 anchor has 33 missing explicit-share rows and the 2026 anchor is
percentage-only. Embedded LBRE lineage remains incomplete. The surface is
capability-only (`PARTIAL / SOURCE_REMEDIATION_REQUIRED`); no feature,
candidate, packet, or model status changed. See
`2026-09-20_ALPHA_STATUTORY_FREE_FLOAT_SOURCE_AUDIT_RESULT_V1.md`.

The HSC ownership event ledger was then audited independently. Its 137
manifest artifacts, 59 unique events, revision counts, replay checkpoints,
and 55-ticker effective cutoff target all pass structural verification. The
source remains capability-only (`PARTIAL / EVENT_ONLY`) because it is not a
daily population-wide PIT panel and lacks complete issuer/ISIN, CA, revision,
and public-availability authority. No feature, candidate, packet, or model
status changed. See
`2026-09-20_ALPHA_HSC_OWNERSHIP_EVENT_SOURCE_AUDIT_RESULT_V1.md`.

The broker/margin snapshot was then audited independently. Manifest integrity
and official/Zapi raw parity pass across 73 files, 220 margin rows, and 965
stock rows, but the single-date source remains `SNAPSHOT_ONLY / BLOCKED`:
106/326 eligible names are absent from Margin Summary, all-six equality is
0/220, financing-flow semantics are not proven, and publication/knowledge
time is absent. No feature, candidate, packet, or model status changed. See
`2026-09-20_ALPHA_BROKER_MARGIN_SNAPSHOT_SOURCE_AUDIT_RESULT_V1.md`.

The CA/issuer review produced a reusable admission specification rather than
a repair: `CA_ISSUER_PRICE_BASIS_ADMISSION_V1` requires complete
event-to-window linkage, issuer/ISIN continuity, effective and knowledge time,
explicit basis semantics, and a PASS for every finite candidate window. It is
not an admission artifact and does not change candidate or packet status. See
`2026-09-20_ALPHA_CA_ISSUER_PRICE_BASIS_ADMISSION_SPEC_V1.md`.

An independent control and local-surface red-team then corrected stale
attestation/frontier metadata and made `Dataset-Saham-IDX` explicit in the
capability maps as `BLOCKED / NOT_ADMITTED`. No candidate, packet, or admission
status changed. See
`2026-09-20_ALPHA_CONTROL_AND_SURFACE_REDTEAM_RESULT_V1.md`.
