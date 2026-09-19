# IDX-Trade Long-Horizon Alpha Research — Current Final Handoff V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Verified research baseline HEAD before this handoff addendum: `153a9716`
Latest research milestone commit: `153a9716`
Latest status/documentation commit: `153a9716`
Status: `PRE-ADMISSION RESEARCH ACTIVE / HISTORICAL TARGET STAGE BLOCKED`

Latest concise status read-in: `2026-09-19_ALPHA_RESEARCH_CURRENT_STATUS_V2.md`
Latest adversarial result: `2026-09-19_ALPHA_PHASE_Q_REDTEAM_CORRECTION_RESULT_V1.md`
Latest CA/price-basis result: `2026-09-19_ALPHA_CA_PRICE_BASIS_RESULT_V1.md`
Latest H-LIQ novelty result: `2026-09-19_ALPHA_HLIQ01_NOVELTY_RESULT_V1.md`
Latest H-LIQ source decomposition result: `2026-09-19_ALPHA_HLIQ01_SOURCE_DECOMPOSITION_RESULT_V1.md`
Latest H-LIQ independent verifier: `research/verify_alpha_hliq01_source_decomposition_v1.py`
Latest H-VOL result: `2026-09-19_ALPHA_HVOL01_CA_SENSITIVITY_RESULT_V1.md`
Latest H-VOL horizon audit: `2026-09-19_ALPHA_HVOL01_HORIZON_STABILITY_RESULT_V1.md`
Latest H-EXC result: `2026-09-19_ALPHA_HEXC01_EXCURSION_ASYMMETRY_RESULT_V1.md`
Latest H-EXC-02 result: `2026-09-19_ALPHA_HEXC02_BOUNDED_EXCURSION_RESULT_V1.md`
Latest H-EXC-02 CA sensitivity: `2026-09-19_ALPHA_HEXC02_CA_SENSITIVITY_RESULT_V1.md`
Latest H-EXC-02 horizon stability: `2026-09-19_ALPHA_HEXC02_HORIZON_RESULT_V1.md`
Latest Open capability audit: `2026-09-19_ALPHA_OPEN_CAPABILITY_RESULT_V1.md`
Latest corrected robustness/combination replay: `2026-09-19_ALPHA_PHASE_Q_REDTEAM_CORRECTION_RESULT_V1.md`

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
ECONOMIC_CAUTION` and no C5 ID is created.

Current conclusion:

`NO CURRENT ALPHA SURVIVOR CAN BE PROVEN WITHOUT TARGET ADMISSION`

The next useful work is limited to admission-quality identity/price-basis and
capacity evidence, plus dedicated red-team review before any candidate is
marked ready. Repeating C1-C4 structural calculations or broad provider
searches would be redundant without new evidence.

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
Re-entry packet audit: `2026-09-19_ALPHA_REENTRY_PACKET_AUDIT_RESULT_V2.md`.
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

`2026-09-19_ALPHA_FUTURE_EVALUATION_PACKET_V1.md` is complete as a
specification-only packet for exactly C1-C4: fixed target, population, six
folds, purge/embargo, metrics, gates, friction assumptions, robustness, and
one-shot stopping rule. It is not executable before independent Data QA
admission.

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
- Verified baseline HEAD: `8ad60569`
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
- Other structural code/output hashes are recorded in their result docs and
  staging JSON manifests; all are isolated and target-free.
- Tests: Python compilation `PASS`; C3 verifier `PASS`; corrected V2
  verifiers `PASS`; outcome-blind target firewall `PASS`; artifact hash
  contract PASS plus deliberate wrong-code/required-manifest FAIL paths;
  git worktree was clean at baseline.
- Unresolved risks: authoritative admission, corporate-action/price basis,
  real capacity, sector/PIT history, and mechanism-level novelty; the latest
  independent red-team correction replay is complete but remains structural.

No predictive superiority claim is made.
