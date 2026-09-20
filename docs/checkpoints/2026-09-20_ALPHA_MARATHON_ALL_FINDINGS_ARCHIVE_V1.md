# IDX-Trade Alpha Research — Full Marathon and Historical Findings Archive

Date of archive: 2026-09-20 (Asia/Jakarta)
Purpose: collect the complete known record for GPT/ChatGPT, including the current
19–20 September marathon and earlier historical marathons. This is an archive
and navigation dossier, not a replacement for the machine-readable registries
or the individual evidence files.

The labels in this document are intentional:

- CURRENT MARATHON = work performed in the isolated alpha-available-data lane on
  2026-09-19 and 2026-09-20.
- HISTORICAL / PRIOR = earlier work, earlier branches, or earlier experiments.
  Those results are retained as historical evidence and must not be confused
  with current-lane results.
- STRUCTURAL ONLY = no protected outcome or forward target was used.
- PRIOR OUTCOME RESULT = an older development/validation result that may have
  opened an older historical target; it was not reopened by the current marathon.

## A. Master conclusion

Current final state:

NO-GO / PRE-ADMISSION / OUTCOME-BLIND / PREDICTIVE STAGE BLOCKED

The work learned a great deal about the alpha surface, data boundaries,
implementation defects, historical failure modes, and admission controls. It
did not establish a better model, a predictive winner, or a candidate ready for
re-entry.

The safe handoff sentence is:

No authorized, PIT-safe, population-complete, corporate-action-safe,
economically executable, or predictively superior model was established.
C1/C2/C4 are structurally reproducible future-research candidates; C3 remains
blocked by sparse/late financial support. Predictive evaluation stays closed
until policy authority, PIT population/identity, corporate-action basis,
publication/revision provenance, and capacity evidence are resolved.

The goal was marked complete by natural stopping point. The local outcome-blind
surface is substantially exhausted; repeating the same local searches,
mutations, or representations would be redundant.

## B. Lane, provenance, and safety

Current isolated lane:

- worktree: C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919
- branch: codex/alpha-available-data-20260919
- baseline: 58f094b8
- current HEAD: f9a7f9c7
- external staging:
  D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded

The lane never changed the incumbent/model-alpha, canonical or production
data, cloud/provider/Zapi live state, capture, telemetry, scheduler, forward
monitoring, counters, protected targets/outcomes, deployment, or global
configuration. It did not reset, clean, archive, merge, push, or overwrite
other lanes.

Current marathon did not:

- open H5/H10 or any protected forward target;
- inspect forward returns, IC, Rank-IC, ICIR, OOS, PnL, prospective results, or
  incumbent predictive results;
- fit, refit, sweep, optimize, or rescue a new model;
- create C5 or expand the fixed C1–C4 budget;
- silently repair/rescale price data;
- call a provider, scrape live data, use credentials, or substitute a source
  into the canonical panel.

All current numeric diagnostics are structural, rank/overlap/support/turnover
or explicitly proxy economics. They are not claims of return or alpha.

## C. Chronology of the whole record

### C1. HISTORICAL / PRIOR: repository scientific-integrity audit — 2026-08-13

Checkpoint:
docs/checkpoints/2026-08-13_REPOSITORY_SCIENTIFIC_INTEGRITY_AUDIT_INDEPENDENT_ACCEPTANCE.md

Verdict:
REPOSITORY_SCIENTIFIC_INTEGRITY_AUDIT_ACCEPTED_NO_GO_FOR_REPRODUCIBLE_RESEARCH_RELEASE

The independent audit upheld a repository-wide reproducibility/PIT/data-integrity
NO-GO. It did not reverse accepted historical model verdicts. Confirmed
fail-open defects were:

1. coverage-window textual is_complete values could be truthy when "False";
2. malformed non-null listed_to dates could become NaT/open-ended;
3. duplicate OHLCV dates could be silently resolved with keep-last, including
   conflicting bars;
4. missing source files could be fingerprinted as None and manifests could be
   replaced rather than enforced write-once.

Additional accepted risks covered provider/source authority, PIT/session
domain, mutable artifact publication, and absent scheduled O2.1/Reliability
modules. Targeted validation was 39 passed, 1 failed; the remaining failure
was a storage-test expectation mismatch. Ownership was left with the active
engineering/data lanes; this audit lane did not patch them.

Interpretation: this was an infrastructure and scientific-integrity NO-GO, not
proof that every historical model result was false.

### C2. HISTORICAL / PRIOR: Stockbit and Zapi capture reliability — 2026-08-21 to 2026-08-25

These were acquisition/infrastructure lanes, not alpha discovery and not
current-marathon evidence. They intentionally did not change model, outcome,
counter, Decision, sizing, execution, or protected target state.

#### 2026-08-21 routine archive V2

Checkpoint:
docs/checkpoints/2026-08-21_STOCKBIT_STREAM_PROSPECTIVE_ARCHIVE_V2_REMEDIATION.md

The first cloud bootstrap had used all 963 current identities. V2 changed the
routine capture design to the top 200 active current identities ranked by the
prior completed IDX session regular market traded value:
regular_value = Value - NonRegularValue

Selection was deterministic with ticker tie-break. Same-run sentiment, return,
model, target, O2, and protected outcome were not used.

Schedule was 08:47 pre-open, 12:07 midday, and 16:47 after-close, every
calendar day. Weekend/holiday runs reused the latest valid completed IDX
session only for universe ranking while preserving capture date in run_id.
Expected monthly budget was 18,000–18,600 Stream calls, below the 25,000-call
Zapi Pro budget with retry headroom.

Storage changed to immutable run-namespaced raw response, normalized observation,
manifest, and exact IDX stock-summary source response. Conditional immutable
PUT and SHA metadata were used; per-post canonical objects were removed from
the hot path. Zapi envelope handling was fixed to preserve the exact outer
response and validate the nested finance payload. Partial runs remained
PARTIAL_FAILURE and could not become DATA_READY. Quota-after telemetry was
best effort; pre-capture quota remained hard-gated.

Bounded cloud smoke: workflow 32450648278, job 96678410979, source session
2026-08-20, top-5 validation only, 5/5 calls, 150 normalized observations,
run_id 2026-08-21_observable_validation_c12c95b65481cfa9,
universe SHA c12c95b65481cfa95f23d06dd5fb7bde89eb82eade3dbc0c54817dd4ee1d995a,
manifest SHA 0d9e4ccc3ea224aeae5e396f86d627f64fe6708e06d35c7907df1157c2118bbe.
No model/outcome/counter access or mutation.

#### 2026-08-23 transient retry and full E2E

Checkpoints:
docs/checkpoints/2026-08-23_STOCKBIT_STREAM_TRANSIENT_RETRY_REMEDIATION.md
docs/checkpoints/2026-08-23_STOCKBIT_STREAM_FULL_E2E_RESULT.md

First top-200 run 32615513888 reached 200/200 but had 198 OK, one HTTP_503,
one HTTP_520, and correctly ended PARTIAL_FAILURE. The fix allowed at most one
retry for an explicit allowlist of transient 5xx statuses, retained all
attempt evidence, reserved worst-case quota, and required final OK for every
planned ticker.

Next full E2E run 32616176893: after_close, capture 2026-08-23, source session
2026-08-21, 200/200 calls, OK=200, 5,919 normalized rows, DATA_READY,
run_id 2026-08-23_after_close_e3315af53dda3073_b60cfd3e81a78317,
universe SHA e3315af53dda307339af2a312c84337e21b5b4c5a34c80267d4a54de23c96c4c,
manifest SHA 5690d7439c357d0d1b8cdbcb8e8da8a17e1a0ea8ff42d4ca29bca9474dc9ff08.
It proved the R2 write path accepted the complete manifest and embedded
digests, but was not an independent byte-level GET readback audit.

Validation: 14 focused capture/archive tests, py_compile, diff check; one
unrelated storage baseline failure remained. No model/outcome/counter access.

#### 2026-08-23 retention policy

Checkpoint:
docs/checkpoints/2026-08-23_STOCKBIT_STREAM_R2_RETENTION_V1.md

The two project-owned 180-day delete rules for raw and normalized Stockbit
research objects were removed. Raw, normalized, manifests, and universe_inputs
are retained indefinitely. Workflow 32626013468 applied and verified the
merged lifecycle payload, SHA 1ec643ae14dc9dfcd6b76afb410d1c6caea3caa9668717c77a05f3f0e9653d80.
No R2 object was listed, read, deleted, or overwritten; the unrelated multipart
abort rule was preserved.

#### 2026-08-24 schema diagnostics and bounded schema retry

Checkpoints:
docs/checkpoints/2026-08-24_STOCKBIT_STREAM_SCHEMA_DIAGNOSTIC_REMEDIATION.md
docs/checkpoints/2026-08-24_STOCKBIT_STREAM_SCHEMA_RETRY_REMEDIATION_V2.md

Run 32716493115 had 199 OK plus one ITEM_SCHEMA_ERROR, 200/200 calls,
PARTIAL_FAILURE, counter/model/outcome all false. Safe diagnostic identified
PADI item 9 missing_content without persisting post content or author identity.

A later direct probe returned a valid PADI item. The bounded policy retained the
bad response, made at most one additional request only for ITEM_SCHEMA_ERROR,
accepted only a fully valid final response, and retained PARTIAL_FAILURE if the
second response was invalid. Run 32722871440 recovered: 200/200, OK=200,
5,931 normalized rows, DATA_READY, validation_diagnostics empty,
manifest SHA 3e160e6024c1fddb40109184205baf54ebc7c0d89f9ca1ab5fadaf7ec7343e1b.
No model/outcome/counter access.

#### 2026-08-25 reliability remediation

Checkpoint:
docs/checkpoints/2026-08-25_FORWARD_RELIABILITY_STOCKBIT_REMEDIATION_V1.md

Two narrow defects were fixed: resumed OK records incorrectly consumed call
budget, and stale attempt-1 response state could leak into a terminal
request-exception record. All attempts remain immutable and auditable.

Read-only 2026-08-24 shadow evidence: 962 planned rows, 833 activity-eligible
successes, 129 no-activity HTTP-404 skips, 120,251 normalized points, 0 HTTP
429, 0 retries, 962 attempts, synthetic fill false, shadow certification
eligible true, manifest SHA
0d4a878e92681dde6c82b0ddf7927502338082188ab301eeebba76e24ab8ac8e.
Validation: 27 focused and 78 full tests passed, no provider call during the
remediation. A genuine future run was still required for live proof of the new
branch.

### C3. HISTORICAL / PRIOR: V4-X1 prospective gate and operational reliability — 2026-08-24 to 2026-08-26

Primary checkpoints:
docs/checkpoints/2026-08-24_V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1.md
docs/checkpoints/2026-08-24_V4_X1_PROSPECTIVE_EVALUATOR_V1_IMPLEMENTATION.md
docs/checkpoints/2026-08-24_V4_X1_PROSPECTIVE_PROTECTED_ACCESS_GATE_V1.md
docs/checkpoints/2026-08-25_V4_X1_PROSPECTIVE_EVALUATION_GATE_AUDIT_V1.md
docs/checkpoints/2026-08-25_V4_X1_CANONICAL_TARGET_IDENTITY_RESOLUTION_V1.md
docs/checkpoints/2026-08-25_V4_X1_FORWARD_RELIABILITY_HARDENING_V1.md
docs/checkpoints/2026-08-25_V4_X1_PROSPECTIVE_PREACCESS_READINESS_V1_BASE.md
docs/checkpoints/2026-08-26_V4_X1_PROSPECTIVE_PREACCESS_ADAPTER_FINAL_HARDENING_V1.md

This prior gate froze model V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1,
fingerprint 30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf,
100 official sessions, Decision V2 Minimal, Sizing V1, Execution V1, deterministic
tie-breaks, and a strict outcome-blind pre-access contract. The historical
context IC was approximately 0.098054 but was not a forward acceptance cutoff.

The protocol required all of these before protected access: exactly 100/100
counter, all score/session artifacts valid, target mature, PaperState continuity,
protocol/evaluator hashes pinned, and no known unauthorized access. It separated
alpha, Decision, execution, portfolio, and operational validity rather than
letting one metric rescue another. It specified mean daily cross-sectional
Spearman IC as primary alpha statistic, ICIR, fixed rank buckets, top-k
diagnostics, net return, volatility, Sharpe with zero daily risk-free rate,
drawdown, Sortino, CAGR-equivalent, benchmark rules, turnover, pending Open,
capacity, fees, slippage, stamp duty, dividends, moving-block bootstrap, and
fixed first/last-half diagnostics. Those metrics were a preregistered future
evaluation protocol, not results of this current marathon.

Historical target-identity work distinguished:
0.097554036 clean common-support Spearman over 600 dates;
0.09805414600339561 frozen evaluator headline fold-mean;
0.099248615 mean frozen-formula IC over a 600-date slice; and
0.0980538834688018 unresolved retained prospective context.
The last value was not substituted and not used for target selection.

Reliability work separated Stockbit, Official Open, evidence health, and
scheduler defects. Official Open authority remained IDX TradingSummary/GetStockSummary,
field OpenPrice, transport DIRECT_IDX_THEN_ZAPI_RAW_V1. A scheduler defect had
been found where a headless runner invoked runtime v1 while remediation was v2;
the runner was corrected in PR #85 but the deployed separate checkout was not
mutated by that task. The 2026-08-24 live Official Open run failed with
DIRECT_IDX_REQUEST_ERROR then ZAPI_RAW_REQUEST_ERROR; no certified Open artifact
existed. Evidence health classified score/EOD complete, Open/Decision/prepared/
execution/PaperState/CA-dividend pending expected, protected outcomes
PROTECTED_NOT_READ, accessed false, values_loaded false, report SHA
922163578e424c509981d39ce99e963b992e29be2a52ba4660884ee54f1a2560.

Historical verdicts:
PROSPECTIVE_EVAL_GATE_V1_AUDITED_TARGET_IDENTITY_RESOLVED_REAL_ACCESS_BLOCKED
and
FORWARD_RELIABILITY_REMEDIATED_NEXT_GENUINE_SESSION_PROOF_PENDING.

No PR was merged by that audit and no protected prospective access occurred.

### C4. HISTORICAL / PRIOR: Alpha Frontier and closed-family re-evaluation — 2026-08-26

Checkpoints:
docs/checkpoints/2026-08-26_ALPHA_FRONTIER_RESEARCH_V1_BOOTSTRAP.md
docs/checkpoints/2026-08-26_CLOSED_ALPHA_FAMILY_REEVALUATION.md

The frontier lane explicitly froze incumbent V4-X1, Decision V2, Sizing V1,
and Execution V1. Phase A was descriptive/outcome-blind. It was not a rescue
of closed Foreign Flow V2 or Financial V1. The intent was mechanism discovery:
source semantics, missingness, distribution, extremes, persistence, long-memory,
state dependence, and conditional hypotheses before new predictive work.

Foreign Flow V2 exact historical experiment (PRIOR OUTCOME RESULT, not current):
Clean V2 25-feature HGB plus eight Foreign Flow V2 features, binary H10
TP_FIRST versus SL_FIRST, paired expanding folds. Median paired PR-AUC delta
was approximately -0.004294, q25 negative, only 1/6 folds positive. The exact
additive H10 challenger failed:
FOREIGN_FLOW_V2_CORE_NO_SURVIVOR.
It did not prove that the entire Foreign Flow family has no edge. Untested
mechanisms included event/tail, conditional interactions, reversal/
continuation asymmetry, other horizons, cross-sectional IC, filtering/
confirmation roles, supply-adjusted pressure, and market-wide regimes.

Financial Alpha V1 exact historical experiment (PRIOR OUTCOME RESULT, not
current): 13 accounting features across Q1/H1/9M/FY (52 slots), Clean V2 plus
Financial versus control, binary H10 path target, only V2F4/V2F5/V2F6,
common support 70,520 rows / 321 tickers. Median PR-AUC delta was slightly
positive, but q25 negative and ROC/Q5-Q1 guardrails worsened. Exact verdict:
FINANCIAL_PIT_ALPHA_V1_NO_SURVIVOR.
It did not prove Financial data has no edge. Untested mechanisms included
filing-event surprise, changes/accelerations, sector/size-relative ranks,
valuation interactions, earnings quality/accruals, revision/restatement,
post-filing drift, longer horizons, and context/risk roles.

Other historical family meanings:

- Margin work mainly rejected source semantics as actual margin usage/flow; it
  was not an alpha false negative.
- Ownership/free-float/HSC work had deep source work but no final comprehensive
  alpha experiment; do not call the family alpha-rejected.
- Suspension/resumption had data-state engineering, not a broad standalone alpha conclusion.
- Price/trend state remained descriptive/sidecar, not a universal rejection.

Process rule adopted: certify source/PIT, run outcome-blind EDA and mechanism
diagnostics, freeze hypotheses, run univariate/event/quantile/decay/conditional
checks, then compare incremental value on common support, and reserve unseen
evidence for confirmation. Do not mine consumed folds for rescue tuning.

## D. CURRENT MARATHON: 2026-09-19 to 2026-09-20

### D1. Goal and frozen inputs

The current goal was to learn as much as possible from available data, code,
artifacts, and history without forcing a new candidate or opening protected
outcomes. Current frozen inputs:

- features: 981,940 rows, SHA
  aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4
- structural panel SHA
  25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e
- official sessions: 1,260, SHA
  661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a

### D2. Stage-A correction and independent replay

Initial v1 failed due reversed beta denominator, mask/rank order, incomplete
official-session rolling, and insufficient financial knowledge-time guards.
Corrected construction and independent replay matched 981,940 panel keys,
eligibility masks, scores, and average-tie ranks with zero mismatch.

Interpretation remains scoped implementation reproducibility only. It is not PIT,
population, corporate-action, capacity, or predictive evidence.

### D3. Candidate results

C1 residual reversal:
295,243 finite rows, 95.0065% support, Top-30 turnover about 42.15%,
proxy burden about 25.29 bps/NAV, most sensitive to unresolved price basis.

C2 participation confirmation:
310,761 finite rows, 100% current support, Top-30 turnover about 32.91%,
proxy burden about 19.75 bps/NAV, interaction/tail caution.

C3 financial quality/growth:
30,994 finite rows, 9.9736% support, zero finite support through 2024,
278 usable Top-30 dates, begins 2025-04-25 and is partial through 2026-07-17,
blocked by financial PIT/publication/support.

C4 path-efficiency reversal:
310,323 finite rows, 99.8591% support, Top-30 turnover about 23.70%,
proxy burden about 14.22 bps/NAV, normalizer/overlap caution.

Four-way finite intersection:
30,861 rows, 9.9308% of current eligible rows, dominated by C3.

### D4. Eligibility policy and population

Protocol prose says trailing 60 official sessions with minimum 20 finite
observations; implementation inherited min_periods=60. No authority binds either.

Policy delta is 38,004 rows and 619 tickers and occurs every calendar year:
2021 11,623; 2022 4,257; 2023 4,577; 2024 4,669; 2025 7,741; 2026 5,137.

Cross-policy Top-30 overlap:
C1 96.52% universe / 32.52% exact daily;
C2 100% / 100%;
C3 94.05% / 22.30%;
C4 91.71% / 12.74%, average symmetric difference 4.98 names.

C2 invariance follows its separate 60-session feature warm-up. Status:
POLICY_AUTHORITY_MISSING / BLOCKED_POLICY_CONFLICT.

All finite scores sit inside the 310,761-row eligibility mask. Missingness
within eligible rows: C1 15,518; C2 0; C3 279,767; C4 438.

Tradability anchor has 1,104,064 rows / 980 tickers:
ACTIVE 982,398 rows / 946 tickers; NO_TRADE 121,666 / 617 tickers.
Panel has 981,940 rows / 945 tickers, overlaps all ACTIVE keys and zero
NO_TRADE. CNTX is the only ACTIVE ticker absent from panel: 458 rows,
2021-04-29 through 2024-08-01.

583/980 tickers switch ACTIVE/NO_TRADE status; median changed-ticker
transitions 10, q95 212.9, maximum 374. These labels do not prove lifecycle,
suspension, delisting, relisting, ticker reuse, or issuer continuity.

### D5. C1/C4 overlap, normalizer, and horizon

Monotone rank/z/robust-z transformations are redundant.

C1/C4 numerator-only Top-30 overlap: 63.75% / 62.22%.
Stored cross-candidate overlap: 35.80%; numerator-only: 36.82%.

Raw -ret_5 versus raw -ret_20: 37.96% Top-30 overlap, mean daily Spearman
0.4327.
C1 raw versus residual: 84.55%, Spearman 0.9338.
Stored C1 versus residual numerator: 63.75%, Spearman 0.9548.
Stored C4 versus raw -ret_20: 62.22%, Spearman 0.9370.

Normalizer denominator percentile medians:
C1 score-only 18.74% versus numerator-only 87.95%;
C4 score-only 17.86% versus numerator-only 83.38%.
The normalizers materially shape final membership; shared overlap remains a
structural caution, not predictive redundancy or orthogonality evidence.

### D6. C2 interaction and market state

C2 formula is ret_5 multiplied by log abnormal turnover.
Pooled Top-30 mix is 68.68% positive-return/high-activity and 31.32%
negative-return/low-activity. 2025 is 78.80/21.20; 2026 partial is 59.90/40.10.
Cross-sign zero is largely mechanically implied by the product sign.

Across 1,141 dates, mean C1/C2 overlap is 8.90% in HIGH_HIGH versus 19.64%
in LOW_LOW. C1/C4 mean overlap is 39.06% in RET_LOW_ACT_HIGH. C2/C4 is
lowest in HIGH_HIGH at 8.29%. This is structural state dependence only.

### D7. Breadth, turnover, and score geometry

Average finite support C1/C2/C4 is 99.54% / 100.00% / 99.85%.
Count-versus-turnover Spearman is 0.133 / 0.061 / 0.175.
C3 average finite support is 35.96%, rho -0.372 overall and -0.711 in 2026
partial. C3 remains support-sensitive, not causally explained.

C2 has the widest normalized rank-30/rank-31 gap; C1/C4 thinner gaps; C3 has
10.18% exact boundary-tie fraction. Gap-to-turnover associations are modest.
These are representation-dependent mechanics, not predictive quality.

Equal-weight C1+C4 has lowest structural turnover about 34.85%. No weight sweep,
no optimization, and no C5.

### D8. Red-team hypotheses

H-LIQ-01:
155,679 finite rows, mean Top-30 turnover 10.31%, bottom-value Q1 share
39.67%. Size-neutral reduced Q1 exposure but raised turnover. Distinct
structural surface, unstable economics/source semantics, no same-surface retry.

H-VOL-01:
308,514 finite rows, mean Top-30 turnover 29.2778%, bottom-value Q1 share
42.72%. CA stress changed 547 scores and 8,876 ranks. Risk signal only.

H-EXC-01:
raw excursion tails around -16.2/5.0 and turnover 40.9694%; representation
failed numerically as written; no post-hoc rescue.

H-EXC-02:
308,067 finite rows, bounded [-1,1], turnover 40.7750%; numerically stable
but high-churn and horizon-sensitive; future only.

### D9. Corporate actions and price basis

HLC overlay: 1,657 rows.
Unresolved non-stable-scale residual: 188 disjoint rows.
Registered stress changed 547 scores and 8,876 ranks.
Minimum Top-30 overlap under stress: 86.6667%.
No price was silently rescaled or repaired.

No event was inferred from share counts, listing/record/distribution dates, or
price jumps alone. Future admission needs event-to-window linkage, effective
and knowledge time, adjusted/unadjusted semantics, identity continuity, and
window-level PASS.

### D10. Source and data inventory

Frozen panel: 981,940 rows, 945 tickers, 2021-04-29–2026-07-31.
Official sessions: 1,260.
Financial bundle: 277,244 rows, 729 tickers, 2021-06-02–2026-07-17.
Tradability anchors: 1,104,064.

Persisted acquisition census:
panel-depth 12 tickers / 18,835 rows;
historical IDX BBCA 1,616 rows, exact duplicate of panel-depth BBCA;
TradingView BBCA max 6,356 rows, 2000-05-31–2026-09-18;
Investing BBCA max 2,065 rows, 2018-08-08–2026-09-18;
official IDX summary 671 rows on 2020-01-02 and 963 on 2026-09-18;
current foreign flow 20 rows;
current stock summary 20 rows;
active listings 962 rows;
Stockbit chart 60 current BBCA items;
Stockbit stream 5 redacted metadata items.

Additional local sources:
historical official foreign flow 1,288 sessions / 1,129,024 rows / 983 tickers,
2021-04-01–2026-08-13, publication time unknown;
Dataset-Saham-IDX 1,014 CSVs / 1,146,324 rows, 4 unmapped tickers and
11 non-identical duplicate groups;
listing/delisting 440 monthly files, 962 current rows, 163 records / 159 tickers,
6 conflicts and 2,280 ambiguous issue rows;
LBRE free-float 58,671 manifest files, 25,262 canonical, 868 unresolved lineage;
statutory free float 923/956 exact shares at 2025-12-31 and percentage-only
2026-03-31;
HSC ownership 59 events / 55 effective tickers;
broker/margin 326 eligible, 220 margin, 965 stock, 106 eligible absent;
Open positive finite on 201,415/310,761 eligible rows = 64.8135%, all 1,201
eligible dates with at least 30 Open rows, but 20,995 source transitions and
unresolved PIT/CA/execution semantics.

Market context sampled copies match on three rich dates; arithmetic exact on
2024-06-21 and 2026-07-31, with a localized composite/component discrepancy
on 2021-01-04. Only three sampled digital monthly blocks exist, so no
continuous PIT source was admitted.

No local surface satisfied all population/PIT/identity/CA/revision/capacity
requirements.

### D11. Local Zapi archive result

Checkpoint:
docs/checkpoints/2026-09-19_ALPHA_ZAPI_LOCAL_PROBE_ADMISSION_AUDIT_V1.md

Result:
BLOCKED / NOT_ADMITTED / NO_NEW_ALPHA_SURFACE

Only persisted local probes were inspected; no network/provider/scraper call
was made. Four Zapi probe directories contained one BBCA profile snapshot,
one 2026 dividend row, and two empty monthly dividend payloads. Schema exposed
year/month/page/length/search but no row-level publication/knowledge time,
revision/vintage, source selection, or available-at field. Official parity event
was not found. Empty responses do not prove the underlying source has no data.

No dividend feature, corporate-action repair, panel fill, or provider reopen
is authorized from those probes.

### D13. CURRENT MARATHON: public EOD/IPO source coverage

Checkpoint:
docs/checkpoints/2026-09-20_ALPHA_PUBLIC_EOD_SOURCE_COVERAGE_RESULT_V1.md

Result: CAPABILITY FOUND / ADMISSION BLOCKED

This newly added current-marathon experiment pinned and inspected two public
EOD ticker-file snapshots plus an IPO-only JSON snapshot. It did not touch
canonical data, protected outcomes, provider credentials, cloud, capture,
telemetry, scheduler, or incumbent state.

Pinned sources:

- Pholenk/IDX-Dataset commit 9bb3b26bd28ab46bc2f3e74a7c03805ce053301b,
  983 ticker CSVs, 1,289,820 rows, 2020-01-02 through 2026-05-29;
- wildangunawan/Dataset-Saham-IDX commit bc0ac7712ce5e46f1067349e13ab9f338883c6c4,
  explicit Semua folder, 958 files, 1,078,040 rows, 2019-07-29 through
  2025-02-21;
- ricotandrio/web-indonesia-ipo-data commit 5f1ca215b29e0bb962b4a09217414a2619c20fd8,
  251 IPO ticker files, information updated 28 June 2026;
- NeaByteLab/IDX-API commit 910b8db70893b93920a1bba331d00a1a245907c6, used
  only for source-route discovery; ordinary curl reached the official host but
  received a Cloudflare 403 challenge, with no bypass or authenticated call.

Both independent EOD snapshots contain CNTX. The newer snapshot has 1,537 CNTX
rows from 2020-01-02 through 2026-05-29, including 824 zero-volume rows. This
changes the narrow wording from panel-absent to panel-absent but discoverable
in independent public EOD snapshots; it does not prove population completeness
or survivorship safety.

Through the newer 2026-05-29 cutoff:

- anchor exact keys: 1,060,071 / 1,062,767 = 99.7463%;
- panel exact keys: 943,283 / 945,693 = 99.7452%.

The six missing ticker files are BACH, EMMI, JECX, JELI, PRDL, and RANS. They
exactly equal the IPO dataset declared new-stock list. This is bounded,
independently supported snapshot-timing/new-issue evidence, not an authority
for historical membership.

Source characteristics include 156,317 zero-volume rows, 1,045,981 rows with
at least one zero OHLC field, 427 files with changing listed-share values, and
78 files with multiple names. These are raw source characteristics; they are
not corporate-action or identity conclusions.

Final admission remains blocked for historical population completeness,
survivorship, row-level publication/available-at/revision time, issuer/ISIN
continuity, ticker reuse, delisted/relisted lifecycle, and corporate-action
effective basis. Exact result artifact SHA:
44522e840f0e639c6616f13f54626a69408c5df625cc61ee7f283a8826dfe94b.

### D12. Current tooling and control findings

Latest verification:

- knowledge verifier PASS: 54 experiment records, 47 findings, 17 no-retry,
  18 source capability;
- data-authority packet verifier PASS;
- protected-field scan PASS;
- protected payloads persisted: false;
- previous focused structural suite: 22 tests passed;
- public EOD source-coverage tests: 4/4 passed;
- git diff check passed for this archive;
- f9a7f9c7 was clean before the newly observed public-EOD artifacts; those
  unrelated/uncommitted artifacts remain untouched and are not staged here.

Tooling findings:

- five declared formula/mask mutations are detected by the independent
  constructor challenger;
- expected corrupt-hash, missing-reference, network-import, protected-token,
  candidate-injection, policy-selection, and re-entry-opening failures are
  detected;
- six stale current-tree refs were repaired and eight unavailable historical
  refs classified;
- nested strict-allowlist draft catches five unknown/missing nested packet
  cases accepted by current verifier;
- freshness draft catches stale/missing verifier hashes and packet/result schema
  binding issues.

Remaining limitations:

- denylist/token checks are not a semantic allowlist;
- disguised fields or schema columns can false-green shallow scans;
- packet verifier does not recompute every producer formula;
- process checks cannot prove runtime access absence;
- PASS is limited to checked hash/path/schema/process assertions.

## E. Complete current experiment record

Authoritative machine record:
research_knowledge/experiment_registry.jsonl

The latest registry has 54 records, 47 findings, 17 no-retry records, and 18
source-capability records. The complete IDs and final dispositions are:

ARCH-PRIOR-ALPHA-001 — SUPPORTED: archaeology/failure taxonomy.
STAGEA-CONFORMANCE-001 — IMPLEMENTATION_FAIL: first implementation defects.
STAGEA-CORRECTED-002 — PROVEN_SCOPED: corrected structural construction.
C1-STRUCT-001 — SUPPORTED_STRUCTURAL_ONLY.
C2-STRUCT-002 — SUPPORTED_STRUCTURAL_ONLY.
C3-CAPABILITY-003 — BLOCKED_BY_PIT.
C4-STRUCT-004 — SUPPORTED_STRUCTURAL_ONLY.
ORTHO-ROBUST-005 — SUPPORTED_STRUCTURAL_ONLY.
COMBO-ECON-009 — PROMISING_STRUCTURAL_ONLY.
HLIQ01-STRUCT-010 — PROMISING_STRUCTURAL_ONLY.
HLIQ01-REDTEAM-011 — INCONCLUSIVE_ECONOMIC_CAUTION.
HVOL01-STRUCT-012 — PROMISING_STRUCTURAL_ONLY.
HVOL01-CA-013 — SUPPORTED_RISK_SIGNAL.
HEXC01-RAW-014 — REPRESENTATION_FAIL.
HEXC02-BOUNDED-015 — PROMISING_STRUCTURAL_ONLY.
CAPACITY-PROXY-017 — SUPPORTED_RISK_SIGNAL.
CA-BASIS-018 — BLOCKED_BY_DATA.
IDENTITY-CONT-019 — BLOCKED_BY_PIT.
SOURCE-CENSUS-020 — SUPPORTED_CAPABILITY_MAP.
FOREIGN-FLOW-021 — BLOCKED_BY_PIT.
DATASET-IDX-025 — UNAUTHORITATIVE.
OPEN-CAPABILITY-024 — PARTIAL_CAPABILITY.
CONSTRUCTOR-REPLAY-026 — PROVEN_SCOPED.
ELIGIBILITY-CONFLICT-027 — BLOCKED_BY_POLICY.
PACKET-CONTROLS-028 — PROVEN_SCOPED.
LANE-INTEGRITY-029 — PROVEN_SCOPED.
LOCAL-SURFACE-CLOSURE-030 — SUPPORTED_EXHAUSTION.
KNOWLEDGE-VERIFIER-031 — SUPPORTED_TOOLING.
VERIFIER-SEMANTIC-032 — SUPPORTED_LIMITATION.
COMMON-SUPPORT-033 — PROVEN_SCOPED.
ELIGIBILITY-SCENARIO-034 — SUPPORTED_CLARIFICATION.
TOOLING-MUTATION-035 — SUPPORTED_TOOLING_WITH_KNOWN_GAPS.
LANE-ALLOWLIST-036 — SUPPORTED_CORRECTION.
ARCHAEOLOGY-037 — SUPPORTED_EXHAUSTION.
TOOLING-038 — SUPPORTED_LIMITATION.
ELIGIBILITY-PROVENANCE-039 — SUPPORTED_PROVENANCE_NARROWED.
TOOLING-040 — SUPPORTED_SCOPED.
TOOLING-041 — SUPPORTED_SCOPED.
TOOLING-042 — SUPPORTED_SCOPED.
CANDIDATE-ERA-AUTHORITY-043 — SUPPORTED_CANDIDATE_SPECIFIC_STRUCTURAL_MAP.
ELIGIBILITY-ERA-DELTA-044 — SUPPORTED_PERSISTENT_POLICY_DELTA.
CANDIDATE-ERA-MECHANICS-045 — SUPPORTED_STRUCTURAL_ERA_MECHANICS.
CANDIDATE-SCORE-SEPARATION-046 — SUPPORTED_STRUCTURAL_SCORE_GEOMETRY.
CANDIDATE-COMPONENT-047 — SUPPORTED_STRUCTURAL_COMPONENT_ANATOMY.
C2-INTERACTION-QUADRANTS-048 — SUPPORTED_STRUCTURAL_C2_MIXTURE.
C1-C4-NUMERATOR-OVERLAP-049 — SUPPORTED_STRUCTURAL_NUMERATOR_OVERLAP.
UNIVERSE-BREADTH-TURNOVER-050 — SUPPORTED_CANDIDATE_SPECIFIC_BREADTH_MECHANICS.
REDTEAM-ADJUDICATION-051 — SUPPORTED_ADJUDICATION.
ELIGIBILITY-WARMUP-052 — SUPPORTED_ELIGIBILITY_FEATURE_SEPARATION.
POPULATION-STATE-CENSUS-053 — SUPPORTED_UNIVERSE_STATE_BOUNDARY.
ANCHOR-STATE-TRANSITIONS-054 — SUPPORTED_STATE_SEMANTICS_BOUNDARY.
ELIGIBILITY-SELECTION-OVERLAP-055 — SUPPORTED_POLICY_SELECTION_SENSITIVITY.
C1-C4-HORIZON-BRIDGE-056 — SUPPORTED_STRUCTURAL_HORIZON_BRIDGE.
PUBLIC-EOD-SOURCE-COVERAGE-057 — SUPPORTED_PUBLIC_CAPABILITY_BOUNDARY.

For exact question, method, input refs, code refs, limitations, reopen trigger,
and related experiments, use the JSONL record rather than this condensed list.

## F. Current no-retry and no-admission rules

Do not retry the same Stage-A implementation, monotone transforms, raw H-EXC-01,
same-surface H-LIQ residualization, exact foreign-flow formulation, unsupported
margin interpretation, current C3 YoY bundle, broad provider search, CA repair,
eligibility choice by convenience, protected predictive comparison, or C5.

Do not turn historical source capability into admissible data merely because it
has more rows. Do not turn an empty probe into negative authority. Do not infer
issuer lifecycle from ACTIVE/NO_TRADE. Do not call a structural overlap a
predictive orthogonality result.

## G. Missing authority and future re-entry criteria

Open questions:

- Q-001 policy authority;
- Q-003 PIT population/universe completeness;
- Q-004 corporate-action basis;
- Q-005 publication/revision/vintage;
- Q-006 execution capacity;
- Q-007 common support after admission;
- Q-009 freshness contract adoption;
- Q-014 nested schema/version adoption;
- Q-023 horizon bridge is mapped structurally but not predictively.

A future re-entry requires:

1. hash-bound eligibility authority and isolated regeneration;
2. PIT-complete population and issuer/security identity;
3. event-complete CA basis with effective and knowledge time;
4. publication/revision/vintage authority;
5. executable liquidity/capacity contract;
6. pre-registered mechanism and candidate budget;
7. only then protected common-support H5/H10 evaluation.

## H. Evidence-of-record map

Primary machine records:

- research_knowledge/manifest.json
- research_knowledge/experiment_registry.jsonl
- research_knowledge/findings_index.jsonl
- research_knowledge/no_retry_registry.jsonl
- research_knowledge/source_capability_matrix.json
- research_knowledge/knowledge_synthesis.md
- research_knowledge/research_frontier.md
- research_knowledge/open_questions.md
- research_knowledge/reproducibility.md
- research_knowledge/data_authority_packet_v1.md
- research_knowledge/data_authority_packet_v1.json

Current navigation:

- docs/checkpoints/2026-09-20_ALPHA_MARATHON_AUDIT_HANDOFF_V6.md
- docs/checkpoints/2026-09-20_ALPHA_FULL_MARATHON_HANDOFF_TO_CHATGPT_V2.md
- docs/checkpoints/2026-09-20_ALPHA_MARATHON_GPT_COMPACT_SUMMARY.md
- docs/checkpoints/2026-09-20_ALPHA_PROGRAM_COMPLETION_AUDIT_V2.md
- docs/checkpoints/2026-09-20_ALPHA_LONG_RUN_HANDOFF_TO_CHATGPT_V4.md
- docs/checkpoints/2026-09-20_ALPHA_C1234_REDTEAM_ADJUDICATION_V1.md
- docs/checkpoints/2026-09-20_ALPHA_ELIGIBILITY_POLICY_RESOLUTION_PACKET_V1.md
- docs/checkpoints/2026-09-20_ALPHA_DATA_SURFACE_CENSUS_V1.md
- docs/checkpoints/2026-09-20_ALPHA_LOCAL_DATA_SURFACE_CENSUS_CONTINUATION_V1.md
- docs/checkpoints/2026-09-19_ALPHA_DATA_INVENTORY_RESULT_V1.md
- docs/checkpoints/2026-09-19_ALPHA_ZAPI_LOCAL_PROBE_ADMISSION_AUDIT_V1.md
- this archive

Historical navigation:

- docs/checkpoints/2026-08-13_REPOSITORY_SCIENTIFIC_INTEGRITY_AUDIT_INDEPENDENT_ACCEPTANCE.md
- docs/checkpoints/2026-08-21_STOCKBIT_STREAM_PROSPECTIVE_ARCHIVE_V2_REMEDIATION.md
- docs/checkpoints/2026-08-23_STOCKBIT_STREAM_FULL_E2E_RESULT.md
- docs/checkpoints/2026-08-23_STOCKBIT_STREAM_R2_RETENTION_V1.md
- docs/checkpoints/2026-08-23_STOCKBIT_STREAM_TRANSIENT_RETRY_REMEDIATION.md
- docs/checkpoints/2026-08-24_V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1.md
- docs/checkpoints/2026-08-25_V4_X1_PROSPECTIVE_EVALUATION_GATE_AUDIT_V1.md
- docs/checkpoints/2026-08-25_V4_X1_FORWARD_RELIABILITY_HARDENING_V1.md
- docs/checkpoints/2026-08-26_ALPHA_FRONTIER_RESEARCH_V1_BOOTSTRAP.md
- docs/checkpoints/2026-08-26_CLOSED_ALPHA_FAMILY_REEVALUATION.md
- all 2026-09-19 Alpha checkpoint files
- all 2026-09-20 Alpha checkpoint files

For detailed small results, read the dated checkpoint whose filename begins with
the experiment family, then verify its registry input_refs and machine result.

## I. Final archive interpretation

The historical prior outcomes and current structural results must remain
separate. The old Foreign Flow and Financial V1 verdicts reject exact older
representations/targets, not entire information families. The old V4-X1
protocol defines a sealed future test, not a current result. Stockbit/Zapi/R2
work proves bounded capture/reliability behavior, not alpha. The current
marathon proves structural reproducibility and maps blockers, not predictive
superiority.

This archive is complete as a durable handoff when combined with the registry
and dated evidence files. It is not permission to open protected data or to
touch the incumbent lane.

Final current state:
NO-GO — resolve authority and admission gates before any protected predictive
evaluation.

## J. Post-archive continuation — 2026-09-20

This section was added after the original archive commit and is intentionally
marked as a later continuation, not backdated into the prior marathon.

### J.1 Runtime-lineage audit

An isolated read-only audit compared the current `origin/main` source tree
with the runtime actually pinned by the E2E cloud workflow. `origin/main` does
not contain the Decision V2 adapter symbols in its ordinary `src/idx_trade`
tree, but the exact runtime commit
`045e25a19d9f71170d2c863e768102937e59ad73` does contain:

- `decision_v2_minimal.py` and `v4_x1_decision_v2_minimal.py`;
- `v4_x1_sizing_v1_decision_v2_adapter.py`;
- `v4_x1_execution_v1_decision_v2_adapter.py`;
- the E2E orchestration imports and calls for those adapters.

Therefore this observation is not evidence of a production Decision V2 gap:
the workflow checks out the exact pinned runtime. It is a lineage warning for
future audits: inspect the deployed/pinned commit, not only the default branch.
No production, cloud, capture, or model state was changed.

### J.2 Independent worker audit additions

Four read-only audits were run in parallel. Their durable conclusions are:

- No new alpha/portfolio experiment is justified merely by system-completion
  inconvenience. Historical evidence says churn is mainly entry/exit-state
  behavior; strict persistence can cause capacity failure; refill decoupling
  did not solve the mechanism; and fee-aware allocation must be joint rather
  than independent per-name budgeting.
- A bounded Rank-to-Open state-transition audit was genuinely non-redundant;
  it was preregistered and run below.
- The public/official source authority package remains structurally coherent,
  but admission is still blocked. The latest package counts were 55
  experiments, 48 findings, 18 no-retry records, 19 source-capability entries,
  6 synthesis documents; verifier PASS, with 209 distinct registry references,
  521 resolved uses, 8 classified unavailable historical uses, and 6 repaired
  references. Current-head/hash freshness gaps remain explicitly open.
- A deeper frozen-runtime audit found two fail-closed unknowns: immediate
  official-session adjacency is not enforced by the Decision V2 resolver, and
  invalid/nonfinite regular-market-value denominators can become zero capacity
  rather than UNKNOWN. Additional unknowns include caller-trusted sizing-price
  provenance, missing runtime config-hash admission, malformed pending
  buy/sell overlap handling, and an underfill/profile inconsistency. These are
  operational science-control findings, not permission to reopen Decision V2.

### J.3 Rank-to-Open state-transition audit — new result

The isolated audit in
`docs/checkpoints/2026-09-20_ALPHA_RANK_OPEN_STATE_TRANSITION_RESULT_V1.md`
joined the frozen C1-C4 rank surface to the existing frozen Open field only.
It passed the structural/privacy gates and remained
`BLOCKED_SOURCE_ADMISSION`:

| Candidate | Complete dates | Selected | Ready Open | Pending Open | Pending rate |
|---|---:|---:|---:|---:|---:|
| C1 | 600 | 18,000 | 12,696 | 5,304 | 29.4667% |
| C2 | 600 | 18,000 | 11,991 | 6,009 | 33.3833% |
| C3 | 278 | 8,340 | 8,305 | 35 | 0.4197% |
| C4 | 600 | 18,000 | 12,443 | 5,557 | 30.8722% |

The result shows that aggregate Open coverage is not the same as
rank-conditioned readiness. It does not establish predictive value, PIT
knowledge time, source authority, CA correctness, survivorship, or fills. The
machine result remains in the isolated staging subfolder
`20260920T-rank-open-state-transition` and was not copied into canonical or
protected data.

The global interpretation is unchanged: NO-GO for protected predictive
evaluation and no admission change. The new audit is a structural shadow only.

## K. Post-archive continuation — runtime contract forensics

The later read-only audit is recorded in
`docs/checkpoints/2026-09-20_ALPHA_RUNTIME_CONTRACT_FORENSICS_RESULT_V1.md`.
It refined, rather than amplified, two worker concerns:

- The Decision V2 function itself accepts any strictly increasing previous
  date, but the active pinned controller derives the immediate predecessor
  from the official session calendar and requires that exact score artifact.
  This is a low-level API hardening gap, not a confirmed production adjacency
  failure.
- The frozen 600-session panel contains no zero, nonfinite, or negative
  `regular_market_value`: 503,797 joined rows, 155,679 eligible rows, and all
  Top-30 C1-C4 rows are positive finite. The execution verifier's missing-to-
  zero normalization and allocator zero-capacity behavior therefore remain a
  latent contract risk, not an observed historical incidence.

The same audit found that the pinned runtime's adapter-config verifier is
defined and test-covered, but no production call site was found outside the
definition/tests, and the E2E execution payload does not serialize the
adapter-config hash. This is retained as configuration-lineage hardening
work, with no current runtime mismatch proven and no code change authorized in
this lane.

The exact pinned-runtime call-site census further found that
`verify_sizing_v1_config`, `verify_execution_v1_config`, and
`verify_execution_v1_decision_v2_adapter_config` have definitions and tests but
no non-test production call site. The runtime therefore relies mainly on
checkout pinning, constants, provenance, and tests rather than invoking every
JSON config verifier at runtime. This is a latent configuration-enforcement
gap, not evidence of live drift.
