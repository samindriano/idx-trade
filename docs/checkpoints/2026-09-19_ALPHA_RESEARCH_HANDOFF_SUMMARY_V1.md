# Alpha Research Program — Handoff Summary V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Branch HEAD at V1 handoff: `03ac0c8d0f9a28c835cb740d7627dd9d1876251c`
Latest lane milestone commit: `5d1f97c6` (`research: add capacity proxy stress audit`)
Latest status/documentation commit before this checkpoint: `0a9bbbb9`
Superseded by: `2026-09-19_ALPHA_RESEARCH_PROGRAM_CHECKPOINT_V2.md`
Current self-contained read-in: `2026-09-19_ALPHA_RESEARCH_PROGRAM_FINAL_HANDOFF_V1.md`
Goal status: historical outcome stage `BLOCKED`; pre-admission research continues
Latest concise status read-in: `2026-09-19_ALPHA_RESEARCH_CURRENT_STATUS_V2.md`
Latest consolidated read-in: `2026-09-19_ALPHA_RESEARCH_LATEST_READIN_V1.md`
Latest Phase-Q replay/tooling result: `2026-09-19_ALPHA_PHASE_Q_REPLAY_RESULT_V1.md`
Latest Stage-A lineage result: `2026-09-19_ALPHA_STAGE_A_LINEAGE_RESULT_V1.md`
Latest Stage-A consumer audit: `2026-09-19_ALPHA_STAGE_A_CONSUMER_AUDIT_V1.md`
Latest adversarial audit: `2026-09-19_ALPHA_C1234_ADVERSARIAL_RESULT_V1.md`
Latest CA/price-basis audit: `2026-09-19_ALPHA_CA_PRICE_BASIS_RESULT_V1.md`
Latest H-LIQ novelty diagnostic: `2026-09-19_ALPHA_HLIQ01_NOVELTY_RESULT_V1.md`

## Executive answer

Riset belum “berhenti total”. Bagian yang sudah sah dan selesai adalah:

- rekonstruksi prior alpha/failure;
- inventory dan klasifikasi source;
- frozen protocol dan bounded candidate portfolio;
- causal/PIT-safe structural feature construction;
- missingness, coverage, overlap internal, robustness, turnover, liquidity
  proxy, concentration, horizon sensitivity, normalization invariance,
  synthetic missingness/universe stress, dan friction diagnostics;
- independent hash/mask/schema/provenance audits.

Bagian yang tidak boleh dilanjutkan tanpa perubahan authoritative di luar lane
ini adalah historical scientific comparison: membuka target H5/H10, menghitung
IC/ICIR/OOS, membuktikan incremental information terhadap incumbent, dan
menetapkan `RESEARCH_SURVIVOR`.

## Safety and isolation

Semua pekerjaan dilakukan di branch/worktree terpisah. Tidak ada perubahan pada
incumbent V4-X1, Decision V2, canonical data, capture/runtime, cloud/R2,
scheduler, counter, atau protected outcome vault. Tidak ada target/forward
label/provider/network access selama lane ini.

Derived artifacts berada di:

`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`

## Frozen research contract

Protocol: `2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1`

- Target: `CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1`.
- H5: `Close_(t+5) / Open_(t+1) - 1`.
- H10: `Close_(t+10) / Open_(t+1) - 1`.
- Universe: `V4_PRIMARY_LIQUID_CAUSAL_V1`.
- Historical design: six chronological 100-session folds, last 600 sessions,
  ten-session purge, both H5 and H10 required.
- Candidate budget: exactly four fixed formulas; no sign/weight/window/model
  sweeps, rescue, retry, or search-until-win.
- Promotion requires later untouched prospective evidence; no production action
  follows from this lane.

## Source admission result

Authoritative `origin/main:coordination/TEAM_STATUS.md` still reports:

- Research Integrity / Data QA Gate V1: `BLOCKED`.
- Population completeness and historical-as-of authority: unknown.
- 100-session prospective alpha evaluation: `BLOCKED`.

Current source disposition:

| Source | Status | Allowed use in this lane |
|---|---|---|
| Clean OHLCV panel | `PARTIAL — FROZEN_ONLY` | Structural/capability diagnostics only. |
| Official sessions | `PARTIAL — FROZEN_ONLY` | Session ordering and mask construction only. |
| Tradability anchors | `PARTIAL — FROZEN_ONLY` | Same-session structural mask only. |
| Financial PIT bundle | `PARTIAL` / parked | Capability diagnostics only; no scientific claim. |
| Zapi/IDX/TradingView/Investing/Stockbit probes | `PARTIAL`, `BLOCKED`, or `UNKNOWN` | No reopening solely to obtain a better result. |
| Foreign-flow archive | `BLOCKED` / expected path absent | No scientific claim. |
| Protected prospective outcome vault/counter | `BLOCKED` | Never opened, reset, archived, or mutated. |

The exact re-entry checklist is in
`2026-09-19_ALPHA_RESEARCH_DATA_ADMISSION_REMEDIATION_V1.md`.

## Prior research reconstructed

- Foreign Flow V2 exact additive H10 challenger: failed its exact gate; this
  does not prove the entire foreign-flow family has no edge.
- Financial Alpha V1 exact event/ratio representation: failed/flat and had
  narrow support; this does not close every event/change/relative-value
  financial hypothesis.
- Breakout event: fixed candidate underperformed; exact specification closed.
- Effort-vs-result: causal Stage A passed, but range/effort overlapped heavily
  with relative volume and Stage B was not admitted.
- Price/trend: structural/sidecar evidence only; no universal-alpha claim.
- Margin: source semantics did not support the intended interpretation; not an
  alpha false-negative result.
- Ownership/free-float/HSC: source work was deep, but no final comprehensive
  alpha experiment; untested, not failed.
- Suspension/resumption: state engineering exists; no broad standalone alpha
  conclusion.
- Frontier mechanism discovery: outcome-blind only; future shortlist retained,
  no new candidate added to the frozen budget.

## Candidate results so far

The corrected decision universe contains 310,761 eligible rows across 711
tickers.

| ID | Fixed hypothesis | Structural result | Economics result | Current verdict |
|---|---|---|---|---|
| C1 | `residual_reversal_5_v1` | 295,243 finite rows / 95.0065% coverage | Top-30 turnover 42.15%; base burden 25.29 bps/NAV | `FUTURE_RESEARCH` |
| C2 | `participation_confirmation_5_v1` | 310,761 finite rows / 100.0000% coverage | Top-30 turnover 32.91%; base burden 19.75 bps/NAV | `FUTURE_RESEARCH` |
| C3 | `financial_quality_growth_v1` | 30,994 finite rows / 9.9736% coverage | 278 usable Top-30 dates; top-10 ticker share 25.77% | `BLOCKED` |
| C4 | `path_efficiency_reversal_20_v1` | 310,323 finite rows / 99.8591% coverage | Top-30 turnover 23.70%; base burden 14.22 bps/NAV | `FUTURE_RESEARCH` |

Latest pre-admission additions:

- H-LIQ-01 remains `FUTURE_RESEARCH / NOVELTY_PENDING /
  ECONOMIC_CAUTION`. Its adversarial follow-up retained all 600 structural
  dates under deterministic 5% masking, but found horizon sensitivity,
  conditional C2 dependence in the top-value bucket, selected-vs-eligible
  listing-age concentration, and no admitted sector field. It is not C5.
- The C3 contract map shows quality-only capability is broader (64,406 frozen
  rows / 505 dates with at least 30 names), while every YoY-containing
  contract remains at 30,994 rows / 278 usable Top-30 dates. This is a
  capability diagnosis, not a C3 subset admission.
- The identity-continuity audit maps every frozen eligible key to exactly one
  active security-master interval. It does not certify issuer/ISIN history,
  corporate-action transitions, or price-basis consistency.
- Phase M/L combination readiness is now documented separately: four
  equal-weight C1/C2/C4 combinations were measured under low/base/stress
  friction scenarios. C1+C4 had the lowest tested combination turnover
  (`34.85%`), but no combination is in the protected four-ID packet and no
  weight was optimized.

These are structural/capability results only; none opens target, incumbent,
provider, network, prospective, or protected outcome data.

The latest main-run adversarial audit passed all target-free C1/C2/C4 static,
schema/key, calendar, identity-interval, mask, and numerical checks. A new
source-recomputing replay also passed; the old verifier is now treated as
envelope-only. Three additional read-only Phase-Q red-team reviews and the
tooling replay are complete, but readiness remains `NO-GO` because PIT/as-of,
issuer identity, survivorship, price basis, real capacity, and process-level
access attestation are unresolved.

The CA/price-basis follow-up confirms the known 1,657-row HLC overlay is
already embedded in the current panel and does not change C1/C2/C4 on replay;
188 non-stable scale rows and open-price residuals remain unresolved, so the
admission blocker stays in place. A forensic substitution of the 188 rows
shows materially higher basis sensitivity for C1 than C2/C4; this is a risk
signal, not a correction or predictive result.

The H-LIQ novelty diagnostic finds a distinct temporal-variability structure
versus C2 overall, with higher shared participation dependence in the top
market-value bucket. It remains `NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 ID
was created.

Internal candidate Spearman diagnostics (not incumbent comparison):

- C1/C2: `-0.23035511`
- C1/C3: `-0.02365537`
- C1/C4: `0.41126169`
- C2/C3: `-0.04554962`
- C2/C4: `-0.11908659`
- C3/C4: `-0.03261201`

First/last-half economics remain broadly similar for C1/C2/C4. C3 has only
one finite row in the first 300 sessions and becomes usable only late in the
window, reinforcing the PIT/coverage block.

## Engineering correction and audit result

The first implementation was rejected as invalid engineering evidence because
of a reversed beta denominator, mask/rank ordering, incomplete official-session
rolling grid, and insufficient Financial knowledge-time guards. A corrected
implementation was then built without changing hypotheses or candidate budget.

Final corrected structural verifier: `PASS`, including:

- exact schema;
- zero duplicate keys;
- source-key closure;
- canonical session/anchor hashes;
- no score outside eligibility mask;
- rank bounds;
- exact artifact/code/source hashes;
- exactly 600 frozen sessions;
- no network/provider imports or HTTP calls;
- outcome access flags false.

Final economics verifier: `PASS`, including fixed Top-30/600-session scope,
first/last 300-session slices, bounded turnover/concentration, and friction
formula reconciliation.

## What is still unknown

No evidence exists yet for:

- incumbent IC versus candidate IC;
- IC delta, ICIR, sign consistency, or target-ranked spread;
- historical OOS superiority;
- conditional incremental information against incumbent;
- realized friction-adjusted return or capacity;
- canonical H5/H10 common-support comparison;
- `RESEARCH_SURVIVOR`.

These are unknown because the admission gate blocks target access, not because
the candidates have been proven to fail.

## Re-entry steps for a future ChatGPT session

1. Read this handoff, the frozen protocol, the data-admission audit, and the
   remediation contract.
2. Read fresh `origin/main:coordination/TEAM_STATUS.md`.
3. Do not open target/outcome data merely because it exists locally.
4. Proceed only if a separately reviewed admission artifact establishes
   population completeness, historical-as-of/PIT authority, identity/calendar,
   corporate-action basis, revision/vintage, and both H5/H10 target horizons.
5. Re-run the frozen historical comparison exactly once per candidate on common
   support; do not change the contract or rescue a candidate.
6. Otherwise leave candidates in their current statuses and do not claim that
   any candidate is better.

## Canonical lane documents

- `2026-09-19_ALPHA_RESEARCH_PROGRAM_CHECKPOINT_V2.md` (latest complete
  checkpoint for future ChatGPT read-in)
- `2026-09-19_C3_FINANCIAL_CAPABILITY_RESULT_V1.md`
- `2026-09-19_ALPHA_STRUCTURAL_LAB_RESULT_V1.md`
- `2026-09-19_ALPHA_STRUCTURAL_ROBUSTNESS_RESULT_V1.md`
- `2026-09-19_ALPHA_HYPOTHESIS_CARD_PACK_V1.md`
- `2026-09-19_ALPHA_HLIQ01_STRUCTURAL_RESULT_V1.md`
- `2026-09-19_ALPHA_HLIQ01_ROBUSTNESS_RESULT_V1.md`
- `2026-09-19_ALPHA_FUTURE_EVALUATION_PACKET_V2.md` (current; V1 superseded)
- `2026-09-19_C3_FINANCIAL_CONTRACT_MAP_RESULT_V1.md`
- `2026-09-19_ALPHA_IDENTITY_CONTINUITY_RESULT_V1.md`
- `2026-09-19_ALPHA_COMBINATION_ECONOMICS_RESULT_V1.md`
- `2026-09-19_ALPHA_CAPACITY_STRESS_RESULT_V1.md`
- `2026-09-19_ALPHA_ARCHAEOLOGY_RESULT_V1.md`
- `2026-09-19_ALPHA_DATA_INVENTORY_RESULT_V1.md`
- `2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1.md`
- `2026-09-19_ALPHA_RESEARCH_DATA_ADMISSION_AUDIT_V1.md`
- `2026-09-19_ALPHA_RESEARCH_DATA_ADMISSION_REMEDIATION_V1.md`
- `2026-09-19_ALPHA_RESEARCH_STAGE_A_CORRECTED_RESULT_V2.md`
- `2026-09-19_ALPHA_RESEARCH_ECONOMICS_RESULT_V1.md`
- `2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`
