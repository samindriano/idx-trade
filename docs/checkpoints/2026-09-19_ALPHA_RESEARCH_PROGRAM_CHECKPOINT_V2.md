# IDX-Trade Long-Horizon Alpha Research Program — Checkpoint V2

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`  
Scope: isolated, outcome-blind, no canonical/incumbent mutation

## Executive summary

Riset masih bisa dilanjutkan. Yang belum boleh dibuka adalah protected
historical target/forward-return comparison dan klaim superiority. Di lane ini
yang sudah selesai dan dapat dipertanggungjawabkan adalah archaeology alpha,
source/admission inventory, frozen structural construction, audit PIT/mask,
candidate coverage, internal overlap, temporal structural robustness, turnover,
liquidity/concentration proxy, friction diagnostics, horizon/normalization/
missingness/universe robustness diagnostics, serta independent
hash/schema/provenance checks.

Milestone terbaru juga sudah menutup tiga audit pendukung yang sebelumnya masih
terbuka: adversarial robustness H-LIQ-01, contract map untuk capability C3, dan
identity-continuity audit berbasis reconciled security master. Ketiganya lulus
secara struktural, tetapi tidak mengubah boundary admission atau status
kandidat.

Kesimpulan saat ini bukan “tidak ada alpha”, melainkan:

`NO CURRENT ALPHA SURVIVOR CAN BE PROVEN WITHOUT TARGET ADMISSION`

Empat kandidat fixed masih berada pada status struktural berikut: C1, C2, dan
C4 `FUTURE_RESEARCH`; C3 `BLOCKED` karena support financial/PIT parsial dan
sparse. Tidak ada kandidat yang boleh diberi IC, ICIR, OOS, net return,
incremental information, `RESEARCH_SURVIVOR`, atau promotion status.

## Current scientific boundary

Authoritative `origin/main:coordination/TEAM_STATUS.md` masih menyatakan Data QA
Gate V1 `BLOCKED`: population completeness dan historical-as-of authority belum
ditetapkan. Karena itu lane ini menerapkan fail-closed boundary:

- H5/H10 target, forward returns, target-derived incumbent predictions, IC,
  ICIR, OOS, candidate-vs-incumbent comparison, dan future-outcome tuning tidak
  dibuka.
- Tidak ada proxy reconstruction untuk menggantikan target.
- Tidak ada fallback provider, scraping baru, network probe, sparse-period
  rescue, search-until-win, atau perubahan candidate budget.
- Protected outcome vault/counter, capture/cloud/R2, scheduler, canonical data,
  incumbent V4-X1, dan Decision V2 tidak disentuh.
- Semua angka di checkpoint ini adalah capability/structural diagnostics,
  bukan evidence of predictive alpha.

Frozen protocol tetap: enam chronological 100-session folds pada 600 session
terakhir, purge 10 session, H5 dan H10 wajib, exactly four fixed candidates,
tanpa sign/weight/window/model sweep. Historical comparison baru boleh dilakukan
setelah admission artifact yang authoritative dan direview terpisah tersedia.

## All datasets discovered and disposition

| Dataset / source | Evidence | Disposition in this lane |
|---|---|---|
| Clean OHLCV panel `model_safe_signal_research_panel_1260_final_clean.parquet` | 981,940 rows; 945 tickers; 2021-04-29–2026-07-31; unique keys; no outcome-like columns; SHA-256 `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e` | `PARTIAL — FROZEN_ONLY`; structural/capability diagnostics |
| Frozen V4-X1 input `model_safe_signal_research_panel_1260.parquet` | 981,940 rows; 945 tickers; 1,260 dates; recorded SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` | Existing baseline lineage only; does not widen authorization |
| Financial PIT bundle `bundle_rows.parquet` | 277,244 rows; 729 tickers; 2021-06-02–2026-07-17; unique keys; SHA-256 `c6004832e651b380161ec216efb2020dddbe86419d89c4521f77aeb09335876b` | `PARTIAL_PARKED_CAPABILITY_ONLY`; C3 audit only |
| Official exchange sessions | 1,260 dates; SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` | `FROZEN_ONLY`; session/calendar mask |
| Tradability anchors | 1,104,064 anchors; 1,260 dates; SHA-256 `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e` | `FROZEN_ONLY`; same-session structural mask |
| Official IDX current/monthly snapshots | local/staged snapshot evidence | `PARTIAL`; capability/schema assessment only |
| Zapi IDX/TradingView/Investing/Stockbit probes | staged probe/history evidence | `PARTIAL`, `BLOCKED`, or `UNKNOWN`; not substituted into panel |
| Foreign-flow archive / expected representation path | expected path not admitted/found | `BLOCKED/UNKNOWN`; no scientific claim |
| Historical target ledger / challenger scores | controlled/protected | closed until admission/protocol condition; not opened |
| Protected prospective outcome vault/counter | protected operational state | `BLOCKED`; no access/reset/archive/mutation |

## Data admissibility matrix

Full scoped inventory: `2026-09-19_ALPHA_DATA_INVENTORY_RESULT_V1.md`.

| Data property | Current evidence | Status |
|---|---|---|
| Unique ticker/date identity | OHLCV and financial bundle audits | `PASS` for inspected artifacts |
| Official session ordering | frozen 1,260-session file | `PASS` for structural use |
| Same-session tradability mask | frozen anchors | `PASS` for structural use |
| Population completeness | not certified by authoritative Data QA | `UNKNOWN/BLOCKED` |
| Historical-as-of/PIT authority for all names/dates | not certified population-wide | `UNKNOWN/BLOCKED` |
| Corporate-action basis and transition coverage | not admitted for this comparison | `UNKNOWN/BLOCKED` |
| Revision/vintage completeness | not admitted population-wide | `UNKNOWN/BLOCKED` |
| H5/H10 target authority | protected/not admitted | `BLOCKED` |
| Incumbent same-window comparison | no authorized common-support artifact | `UNKNOWN/BLOCKED` |
| Prospective evidence | separate protected process | `BLOCKED` |

## Previous alpha families and lessons

Complete archaeology is recorded in
`2026-09-19_ALPHA_ARCHAEOLOGY_RESULT_V1.md`; the table below is its compact
current interpretation.

| Family | Current interpretation |
|---|---|
| Foreign Flow V2 Core | Exact additive H10 challenger failed its exact gate; this does not close every foreign-flow mechanism. |
| Financial Alpha V1 | Exact event/ratio formulations failed or were flat/narrow; this does not close all financial representations. |
| Breakout event | Fixed event candidate underperformed incumbent; exact specification closed. |
| Effort-vs-result | Causal Stage A passed, but range/effort overlapped heavily with relative volume; Stage B not admitted. |
| Price/trend | Structural/sidecar evidence only; no universal-alpha conclusion. |
| Margin/source semantics | Source meaning did not support the intended interpretation; not an alpha false-negative. |
| Ownership/free-float/HSC | Deep source work, but no final comprehensive alpha experiment; untested, not failed. |
| Suspension/resumption | State engineering exists; no broad standalone alpha conclusion. |
| Foreign-flow mechanism discovery | Outcome-blind shortlist only; no candidate promotion or frozen-budget expansion. |

Important lineage correction: V3-B Structure-Lite initially passed/promoted on
the early F1–F4 review, but a later clean PIT-safe adjudication identified KOCI
pre-listing contamination and a failed late paired gate. The latest trusted
interpretation is `PIT_FAIL/OOS_FAIL` for that historical representation and
clean V2 as the survivor. This is why the program does not inherit old V3-B
headline metrics as current alpha evidence.

## Failure taxonomy

- `FAIL_ENGINEERING_CONFORMANCE`: an early Stage A implementation had reversed
  beta denominator, mask/rank ordering, incomplete official-session grid, and
  insufficient Financial knowledge-time guards; it is retained only for lineage.
- `BLOCKED_SOURCE_ADMISSION`: population completeness, historical-as-of,
  identity/calendar, corporate-action, revision/vintage, or target authority is
  not certified.
- `BLOCKED_PARTIAL_CAPABILITY`: source has finite rows but incomplete support,
  missingness, or unresolved period/provenance fields, as with C3.
- `STRUCTURAL_OVERLAP_CAUTION`: a feature is available but may duplicate an
  existing mechanism; this is not predictive failure.
- `ECONOMIC_CAUTION`: turnover, concentration, or coarse capacity proxy is
  unfavorable; this is not alpha rejection.
- `SEMANTIC_SOURCE_INVALID`: source semantics do not represent the proposed
  economic variable; do not reinterpret it as a negative alpha test.
- `UNTESTED_FAMILY`: source or final experiment was not admitted; do not label
  it failed or surviving.

## Current candidates

The corrected decision universe is 310,761 eligible rows across 711 tickers.

| ID | Fixed formula | Coverage | Structural economics | Status |
|---|---|---:|---|---|
| C1 | `residual_reversal_5_v1` | 295,243 finite rows / 95.0065% | Top-30 turnover 42.15%; base burden 25.29 bps/NAV; Q10 1% capacity proxy 7,630,887 IDR | `FUTURE_RESEARCH` |
| C2 | `participation_confirmation_5_v1` | 310,761 / 100.0000% | Top-30 turnover 32.91%; base burden 19.75 bps/NAV; Q10 capacity 6,403,241 IDR | `FUTURE_RESEARCH` |
| C3 | `financial_quality_growth_v1` | 30,994 / 9.9736% | 278 usable Top-30 dates; turnover 10.93%; Top-10 slot share 25.77%; C3 audit shows only 34,412 all-five finite rows before mask | `BLOCKED` |
| C4 | `path_efficiency_reversal_20_v1` | 310,323 / 99.8591% | Top-30 turnover 23.70%; base burden 14.22 bps/NAV; Q10 capacity 5,022,700 IDR | `FUTURE_RESEARCH` |

The Top-30 turnover and 60-bps base friction burden are structural diagnostics:
buy fee 15 bps + sell fee 25 bps + 10 bps slippage per side. They are not
realized net returns.

## New candidates discovered

None. The program deliberately held the candidate budget at exactly C1–C4.
Outcome-blind mechanism work produced future questions and representations,
not a new candidate eligible for comparison. No arbitrary expansion is allowed
before source admission and a new protocol decision.

## Structurally rejected or closed candidates

- The first Stage A implementation is rejected as engineering evidence, not as
  an alpha result.
- The exact breakout-event specification is closed due to its prior incumbent
  underperformance record.
- Exact Foreign Flow V2 additive H10 is closed for that exact formulation after
  its failed gate; the broader family remains unclosed.
- Invalid margin interpretation is rejected semantically, not predictively.
- No C1–C4 candidate is structurally rejected solely from turnover, overlap, or
  coverage; those diagnostics remain review gates.

## Structural orthogonality map

Internal feature-rank Spearman diagnostics, computed without incumbent or target,
are:

| Pair | Spearman |
|---|---:|
| C1 / C2 | -0.23035511 |
| C1 / C3 | -0.02365537 |
| C1 / C4 | 0.41126169 |
| C2 / C3 | -0.04554962 |
| C2 / C4 | -0.11908659 |
| C3 / C4 | -0.03261201 |

Interpretation is limited to internal score dependence. Incumbent overlap,
conditional incremental information, and target-ranked overlap remain
`UNKNOWN/BLOCKED` because the same-window incumbent/target evidence was not
opened. C1/C4 deserve extra duplicate-mechanism review; C3 is structurally
distinct in this diagnostic but is currently too sparse for admission.

The extended structural lab adds Top-10/20/30/50 mechanics, persistence, rank
churn, liquidity exposure, six 100-session blocks, market-state conditioning,
and daily/rolling pairwise overlap. At Top-30, C1/C4 have daily Spearman
`0.4624` and same-day overlap `34.89%`; C1/C2 are `-0.2454` and `12.21%`; C2/C4
are `-0.1494` and `11.00%`. C4 has `34.5%` of Top-30 slots in the bottom
liquidity quartile, while C3 has `16.5%` but remains sparse/late. These are
structural dependence and implementation diagnostics only.

## Turnover, liquidity, and concentration findings

- C1/C2/C4 have Top-30 availability across all 600 frozen sessions and broadly
  similar first/last-half turnover: C1 40.56%/43.72%, C2 32.47%/33.32%, and
  C4 22.27%/25.16%.
- C3 has no usable Top-30 date in the first 300 sessions and only 278 usable
  Top-30 dates overall; this is a coverage/timing issue, not evidence of slow
  alpha.
- C3's low modeled burden and high coarse capacity proxy are offset by sparse
  coverage and 25.77% Top-10 ticker slot share.
- C1/C2/C4 Top-10 shares are 5.88%, 7.12%, and 7.39%; largest-name shares are
  0.70%, 0.77%, and 1.12% respectively.
- The capacity proxy is `1% * regular_market_value` at the selected name and
  ignores spread, queue, fill probability, and order size. It is not a capacity
  guarantee.

## C3 financial capability result

The dedicated audit is in
`2026-09-19_C3_FINANCIAL_CAPABILITY_RESULT_V1.md`. Its central result is:

- 277,244 financial rows / 729 tickers;
- 70,520 rows with core-three finite values;
- 34,412 rows with all five finite fields and complete gates;
- 30,994 rows after frozen validity/eligibility, 291 dates, 265 tickers;
- 206,313 rows lack financial bundle state/provenance fields;
- no same-bundle or selected-knowledge-time violation in the finite admitted
  subset.

This is a usable capability island, not a population-wide scientific panel.

## PIT and provenance risks

- The financial bundle's missing knowledge timestamps, reporting versions,
  period dates, and attachment hashes prevent population-wide vintage proof.
- `UNRESOLVED_PERIOD_BOUNDARY`, `UNIT_MISMATCH`, and
  `AMBIGUOUS_SAME_TIME` records must remain visible and cannot be normalized
  silently.
- Clean OHLCV identity and official session correctness do not certify
  historical population completeness or corporate-action transition authority.
- A complete row count is not equivalent to admissibility; frozen-only source
  classification remains controlling.

## Reusable tooling and audits created

| Tool / artifact | Result |
|---|---|
| Corrected Stage A builder and verifier | exact schema/mask/session/hash checks `PASS` |
| Stage A robustness audit | `PASS_STRUCTURAL_ONLY` |
| Economics builder and independent verifier | `PASS`; fixed 600-session/Top-30 and first/last-half diagnostics |
| `research/alpha_structural_lab_v1.py` + independent verifier | `PASS`; Top-K churn/persistence, liquidity, state, and orthogonality lab |
| `research/alpha_structural_robustness_v1.py` | `PASS_STRUCTURAL_ONLY`; fixed-formula replay, horizon, monotone-normalization, missingness, universe, and rolling stability battery |
| `2026-09-19_ALPHA_ARCHAEOLOGY_RESULT_V1.md` | committed-source archaeology across V2/V3/V4/O2/auxiliary families |
| `2026-09-19_ALPHA_DATA_INVENTORY_RESULT_V1.md` | scoped field/source inventory with protected-target exclusion |
| `2026-09-19_ALPHA_STRUCTURAL_ROBUSTNESS_RESULT_V1.md` | durable disposition for target-free robustness results |
| `2026-09-19_ALPHA_HYPOTHESIS_CARD_PACK_V1.md` | bounded literature/mechanism cards and novelty-gate decisions; no new candidate ID |
| `2026-09-19_ALPHA_HLIQ01_STRUCTURAL_RESULT_V1.md` | one fixed temporal-liquidity prototype; structurally distinct but not admitted as C5 |
| `2026-09-19_ALPHA_HLIQ01_ROBUSTNESS_RESULT_V1.md` | adversarial H-LIQ horizon, conditional-overlap, missingness, and listing-age audit |
| `2026-09-19_ALPHA_FUTURE_EVALUATION_PACKET_V1.md` | one-shot protected evaluation specification; not executable before independent admission |
| `2026-09-19_C3_FINANCIAL_CONTRACT_MAP_RESULT_V1.md` | mechanism-defined C3 subset capability map; quality core broader, YoY remains binding |
| `2026-09-19_ALPHA_IDENTITY_CONTINUITY_RESULT_V1.md` | read-only security-master interval audit; eligible identity mapping passes, corporate-action basis remains unknown |
| `research/alpha_research_target_firewall_v1.py` | static code/schema/metadata firewall `PASS`; no forbidden target/provider access detected |
| `research/c3_financial_capability_audit_v1.py` | C3 capability/governance funnel `PASS_STRUCTURAL_ONLY` |
| External guarded staging | all derived parquet/JSON outputs isolated outside repository/canonical data |

Target firewall artifact:
`alpha_research_target_firewall_audit.json`, SHA-256
`211d78f5a1ece63a4b1a5ac7d76ac54e70b550961253aa74dccf700240b59d91`.
The firewall code SHA-256 is
`ef27e6ec657027b222a85f7515a3f432e7d2503b1cd0680692052ad4d02c0762`.

## Future research items

The major target-free structural battery, H-LIQ-01 red-team, C3 contract map,
and identity-continuity audit are complete for this milestone. Remaining
authorized work is limited to:

1. Resolve or separately attest corporate-action price basis, issuer/ISIN
   history, and population-wide identity continuity; the current security
   master audit is not that attestation.
2. If useful, perform a bounded capacity/friction review for H-LIQ-01 using
   already admitted structural fields; do not turn it into a candidate or
   run outcome comparisons.
3. Keep the future evaluation packet, ledger, failure taxonomy, candidate
   registry, re-entry queue, data capability matrix, structural orthogonality
   map, future data capability map, and risk register synchronized.
4. Wait for an authoritative Data QA admission artifact before any H5/H10,
   incumbent, IC/ICIR, OOS, or prospective comparison. No provider expansion,
   scraping, or candidate-budget expansion is authorized by this checkpoint.

## Ready-for-reentry candidates

No candidate is ready for scientific comparison today. Conditional queue:

- C1, C2, C4: re-entry-ready in formula/engineering terms, pending authoritative
  data admission and common-support target availability.
- C3: not re-entry-ready until financial population coverage, knowledge-time,
  period-boundary, revision/vintage, and missingness policy are separately
  certified; current status remains `BLOCKED`.

## Future data capability map

| Needed capability | Why it matters | Current state | Required evidence |
|---|---|---|---|
| Population-wide historical OHLCV identity | common universe and no silent exclusions | partial/frozen | completeness certificate and identity reconciliation |
| Historical-as-of financial vintages | PIT-safe C3 | partial/parked | knowledge timestamp, revision/vintage, attachment lineage |
| Corporate-action transition history | comparable price/return basis | not admitted | event-level authority and transition coverage |
| H5/H10 realized targets | scientific comparison | protected/blocked | separate target admission decision |
| Historical incumbent predictions | incremental comparison | unavailable for same window | immutable same-window score artifact |
| Tradability/liquidity history | cost/capacity realism | structural proxy only | population-wide historical liquidity with PIT authority |
| Foreign-flow/ownership history | future family research | partial/blocked | authoritative historical source contract |

## Protected evaluation packet status

The packet is `2026-09-19_ALPHA_FUTURE_EVALUATION_PACKET_V1.md`; it is
specification-only and not populated with outcomes. The frozen
contract defines the target, six chronological folds, purge, common-support
rules, candidate budget, and re-entry gates. No target, forward label,
incumbent score, or prospective outcome was opened in this lane.

## Exact next step when Data QA arrives

1. Read fresh `origin/main:coordination/TEAM_STATUS.md` and the new admission
   artifact; do not rely on this checkpoint alone.
2. Verify population completeness, PIT/as-of, identity/calendar,
   corporate-action basis, revision/vintage, and H5/H10 target authority.
3. If any gate is missing, keep all statuses unchanged and stop.
4. If all gates pass, run the frozen historical comparison once per C1–C4 on
   common support, with no rescue/refit/variant sweep.
5. Separately compare against the immutable incumbent and report IC/ICIR,
   sign consistency, fold stability, friction sensitivity, and prospective
   readiness. Do not promote based on this checkpoint alone.

## DO_NOT_RETRY_WITHOUT_NEW_EVIDENCE

- Do not reopen protected targets/forward returns or incumbent scores.
- Do not scrape Zapi/IDX/TradingView/Investing/Stockbit merely to improve a
  result or fill missingness.
- Do not retry the rejected Stage A implementation or revive the exact failed
  Foreign Flow V2/breakout formulations.
- Do not treat C3's finite subset as a complete historical financial panel.
- Do not infer OOS, IC/ICIR, superiority, `RESEARCH_SURVIVOR`, or production
  readiness from structural diagnostics.
- Do not reset/archive/mutate telemetry, capture, cloud/R2, scheduler,
  counters, canonical data, incumbent, or protected outcome state.

## Repository, branch, artifacts, and verification

- Repository: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`
- Branch: `codex/alpha-available-data-20260919`
- Documentation commits: `ad967925` (checkpoint content), `65025ccd` (metadata correction), `d9bfb868` (current structural red-team/capability milestone); verify current HEAD before re-entry.
- Main/canonical branch: not modified.
- External staging root:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`
- Corrected feature SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Economics JSON SHA-256:
  `089e0d1804fa02c41a5cba75265f4d543de34b1a22ea8a0fe474c3f8fceb5738`
- Economics independent audit SHA-256:
  `18b88ed83c555849a0944bee294cce8c0010274ec8a7078b8de442bb2b1f118c`
- C3 capability JSON SHA-256:
  `4dfe048905acfeef7073a445d926e0c810ca8ebe47a6d1765e00264c67965c31`
- Structural verifiers and Python compilation: `PASS` for the recorded runs.
- Outcome/target/provider access flags: `false`.

## Unresolved risks

The main unresolved risk is not compute; it is scientific admission. A future
session must revalidate the external source status and canonical coordination
before any outcome access. Until then, the correct state is blocked historical
evaluation with productive pre-admission research still available.
