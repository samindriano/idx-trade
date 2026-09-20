# IDX-Trade Alpha Research — Long-Run Audit Handoff V4

Date: 2026-09-20 (Asia/Jakarta)
Purpose: standalone summary of the isolated belasan-jam research run for an
older ChatGPT session to audit.
Status: `NO-GO / PRE-ADMISSION / OUTCOME-BLIND / PREDICTIVE STAGE BLOCKED`

This document is a navigation and audit summary, not a replacement for the
machine-readable registries or the individual checkpoint artifacts. If a
number here disagrees with a current artifact, the artifact, its hash, and the
current Git state win; stop and audit the discrepancy.

## 1. Bottom line

The run produced a durable, outcome-blind map of the available IDX-Trade alpha
research surface. It materially improved reproducibility and clarified where
the blockers are, but it did **not** prove a better model.

No protected target, forward return, H5/H10 outcome, IC, Rank-IC, ICIR, OOS,
PnL, incumbent predictive result, prospective result, or `READY_FOR_REENTRY`
claim was read, reconstructed, persisted, or used for selection. No C5 was
created. Candidate status was not promoted.

The current safe conclusion is:

> Structural evidence is sufficiently mapped to identify future research
> candidates, but PIT population, eligibility authority, identity, corporate-
> action price basis, capacity, and (for C3) financial publication/revision
> provenance remain unresolved. Predictive evaluation is blocked.

## 2. Lane and safety boundary

All work was kept in the separate research lane:

- Worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`
- Branch: `codex/alpha-available-data-20260919`
- Baseline: `58f094b8`
- External staging root: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded`

The lane did not mutate, reset, archive, promote, or merge:

- incumbent/model-alpha state;
- canonical or production data/artifacts;
- protected targets or outcomes;
- provider/cloud/R2 state;
- capture, telemetry, scheduler, forward-monitoring, or counters;
- `origin/main` or any shared production branch.

The result is process-scope evidence. The lane verifier cannot prove that a
runtime could never access a protected payload; that limitation is recorded
and is not converted into a stronger privacy claim.

The work window covered 2026-09-19 through 2026-09-20. Any statement that this
was “roughly 23 hours” is only a calendar/work-window estimate from prior
handoff context, not a claim of 23 continuous hours of attention, compute, or
model-token use.

## 3. What was done, in order

### A. Historical alpha archaeology

The retained V2/V3/V4/V4-X1, ranking, price-path, participation, regime,
financial, foreign-flow, ownership, sector, and auxiliary directions were
classified into distinct buckets: engineering/conformance failure, source/PIT
block, sparse capability, redundancy/overlap, economics/capacity caution,
semantic source failure, or replay gap.

This prevents “not admitted”, “not tested”, and “failed as written” from being
collapsed into one conclusion. Family-level archaeology is supported; exact
source-level replayability is partial. V4-E/F/G and protected/auxiliary
families remain replay-gap, source-blocked, tombstone, or lineage-only. No old
predictive comparison was reopened.

Primary evidence: `ARCHAEOLOGY-037`,
`docs/checkpoints/2026-09-20_ALPHA_HISTORICAL_ARCHAEOLOGY_AUDIT_RESULT_V1.md`,
`research_knowledge/historical_archaeology_audit_v1.json`.

### B. Candidate contract and corrected Stage-A replay

Four fixed candidate families were retained: C1, C2, C3, and C4. The future
evaluation packet stayed specification-only; no sweep, rescue, refit, new
candidate, or protected evaluation was authorized.

The initial Stage-A implementation was rejected as engineering evidence due to
construction defects, including beta-denominator direction, mask/rank order,
official-session rolling semantics, and financial knowledge-time guards. The
corrected implementation plus an independent constructor replay matched:

- 981,940 panel keys;
- eligibility masks;
- candidate scores;
- average-tie ranks;
- zero recorded mismatches.

This proves scoped implementation reproducibility only. It does not prove PIT
safety, population completeness, survivorship safety, corporate-action basis,
execution capacity, target correctness, or predictive value.

Evidence: `STAGEA-CONFORMANCE-001`, `STAGEA-CORRECTED-002`,
`CONSTRUCTOR-REPLAY-026`, and
`docs/checkpoints/2026-09-20_ALPHA_CONTINUATION_FRONTIER_AND_CONSTRUCTOR_REPLAY_V1.md`.

### C. Fixed C1–C4 structural audit

| Candidate | Mechanism | Finite support | Structural result | State |
|---|---|---:|---|---|
| C1 `residual_reversal_5_v1` | short-horizon residual reversal | 295,243 / 95.0065% | Top-30 turnover about 42.15%; proxy burden about 25.29 bps/NAV; most price-basis-sensitive | `FUTURE_RESEARCH` |
| C2 `participation_confirmation_5_v1` | price/participation confirmation | 310,761 / 100% | Top-30 turnover about 32.91%; proxy burden about 19.75 bps/NAV; broad support with heavy tails | `FUTURE_RESEARCH` |
| C3 `financial_quality_growth_v1` | financial quality/growth | 30,994 / 9.9736% | 278 usable Top-30 dates; sparse and late financial PIT support | `BLOCKED` |
| C4 `path_efficiency_reversal_20_v1` | path-efficiency reversal | 310,323 / 99.8591% | Top-30 turnover about 23.70%; proxy burden about 14.22 bps/NAV; low-churn overlap caution | `FUTURE_RESEARCH` |

These are structural rankings and friction proxies, not target-derived
performance metrics.

### D. Orthogonality, robustness, and combinations

- Monotone rank/z/robust-z representations reproduced the same selected sets
  and were closed as redundant representations.
- C1/C4 showed structural dependence cautions; low Top-K overlap was not
  upgraded into predictive orthogonality.
- Structural Spearman results are feature/score diagnostics, not target
  correlations.
- A positional-merge robustness result was superseded by a key-aligned replay.
- Equal-weight combinations were measured structurally; no weight sweep and no
  new candidate ID were created.
- An initial common-support daily aggregation bug produced an all-zero output;
  it was detected, corrected, and rerun before acceptance.

### E. Bounded new mechanism hypotheses

| Hypothesis | Evidence | Disposition |
|---|---|---|
| H-LIQ-01 activity variability | 155,679 finite rows; mean Top-30 turnover 10.31%; bottom-value Q1 share 39.67%; size-neutral variant lowered Q1 exposure but increased turnover | Future research; novelty/economics unresolved; same-surface residual retry no-go |
| H-VOL-01 volatility compression | 308,514 finite rows; mean Top-30 turnover 29.2778%; bottom-value Q1 share 42.72%; CA stress changed 547 scores and 8,876 ranks | Future only; horizon-sensitive; not admitted |
| H-EXC-01 raw excursion asymmetry | score tails approximately -16.2/5.0; turnover 40.9694% | Representation failure as written |
| H-EXC-02 bounded excursion balance | 308,067 finite rows; bounded [-1,1]; turnover 40.7750% | Future only; horizon-sensitive; not admitted |

Intraday/overnight, financial-change disagreement, flow-conditioned events,
ownership/free-float, sector history, effort-vs-result, breakout/rejection,
and dispersion directions remain blocked, redundant, untested, or future
specifications according to their evidence. No C5 exists.

### F. Economics and capacity

Fixed Top-K churn, persistence, turnover tails, repeat-name concentration, HHI,
effective names, value/volume quartiles, and friction proxies were measured.
They are risk bounds only. Historical executable ADV, spread, queue, fill
probability, and capacity authority are absent. Snapshot or metadata values
were not promoted into historical liquidity features.

### G. Corporate-action, issuer, and identity forensics

- HLC overlay: 1,657 rows.
- Unresolved non-stable-scale basis-stress residual: 188 rows, disjoint from
  that overlay.
- C1 is most fragile under the registered unresolved price-basis stress.
- No price was silently rescaled or repaired.
- No corporate-action event was inferred from share counts or price movement
  alone.
- Ticker continuity was not treated as issuer/security continuity.
- Row mapping was not treated as population completeness.

Future admission requires event-to-window linkage, issuer/ISIN continuity,
effective date plus knowledge time, explicit adjusted/unadjusted semantics, and
a passing basis contract for every finite candidate window.

### H. Source and data capability census

The central lesson is that locally available data is not automatically PIT or
admission authority:

| Surface | Observed capability | Why not admitted |
|---|---:|---|
| Official sessions | 1,260 sessions | Calendar only; not population/PIT authority |
| Tradability anchors | 1,104,064 rows | Structural mask only |
| Main structural panel | about 981,940 unique ticker/date rows | Population/PIT/CA completeness unresolved |
| Foreign flow | 1,129,024 rows / 1,288 sessions | Publication, revision, identity, CA, completeness unknown |
| Dataset-Saham-IDX | 1,014 CSVs / 1,146,324 rows | 4 unmapped tickers, 11 non-identical duplicate groups, no row-level PIT/vintage |
| Listing/delisting | 440 monthly files; 962 current; 163 delisted | Six conflicts; no daily PIT membership |
| LBRE free float | 58,671 manifest files; 25,262 canonical; 868 unresolved lineage | Monthly lineage, not daily PIT population |
| Statutory free float | 923/956 exact shares at 2025-12-31; 2026-03-31 percentage-only | No continuous historical PIT panel |
| HSC ownership events | 59 events / 55 effective tickers | Event-only, not daily PIT feature |
| Broker/margin | 326 eligible; 220 margin; 965 stock; 106 eligible absent | Snapshot-only; financing semantics unresolved |
| Panel depth | 19 fields / 18,835 rows / 12 symbols | PIT, identity, revision, CA, execution semantics absent |
| Historical Open | 201,415 / 310,761 positive finite; 64.8135% | Source/PIT/CA/basis semantics unresolved |
| TradingView / Investing BBCA | 6,356 / 2,065 rows | Partial and basis-divergent; 0/1,568 exact OHLCV overlap |

Bounded local-surface closure found no new admission-changing source. Repeating
provider searches without row-level publication/knowledge-time, revision,
identity, corporate-action, and completeness contracts is low-value.

### I. Eligibility policy and provenance

Two already-defined branches were compared without selecting either:

- implementation-aligned `min_periods=60`: 310,761 rows, 711 tickers, 1,201
  dates;
- literal minimum-20 branch: 348,765 rows, 740 tickers, 1,241 dates;
- difference: 38,004 rows, 619 tickers, 1,241 dates;
- common-finite rank changes for C1/C3/C4: 73.1086%, 96.6122%, and 99.5192%;
- C2 rank change: 0%, because its feature warm-up still requires 60 rows;
- exact all-four finite current-support intersection: 30,861 rows, 9.9308% of
  current eligible rows; 277 dates with at least 30 names; daily max 175;
  median 0 because C3 is sparse.

Historical provenance was narrowed but not resolved:

- legacy primary-liquidity code at `26aac816` explicitly uses a 60 official-
  session window and at least 20 finite ACTIVE observations;
- the related specification states at least 20 valid ACTIVE observations in a
  trailing 60-session window;
- Stage-A V1 uses complete-window rolling without a later explicit >=20 mask;
- Stage-A V2 adds >=20 after complete-window rolling, making it redundant for
  the implementation's count/median fields;
- `security_master` has a separate 60-session `IPO_WARMUP` concept.

The new calendar-year delta experiment confirms that this ambiguity is not
only an early warm-up artifact:

| Year | New rows admitted by min20 minus min60 |
|---|---:|
| 2021 | 11,623 |
| 2022 | 4,257 |
| 2023 | 4,577 |
| 2024 | 4,669 |
| 2025 | 7,741 |
| 2026 partial | 5,137 |
| **Total** | **38,004** |

No policy was selected, no population was silently regenerated, and no
predictive comparison was run.

### J. Candidate-specific era and mechanics addendum

The final continuation added two non-redundant structural views.

Candidate-specific support map:

- 1,260 official sessions from 2021-04-29 through 2026-07-31;
- C1 coverage: 48.4942% in 2021 and about 99.5% from 2022 onward;
- C2 coverage: 100% in every observed year;
- C3 coverage: 0% through 2024, 22.6348% in 2025, 39.4084% in 2026;
- C3 first finite date: 2025-04-25; latest finite date: 2026-07-17;
- structural panel: 981,940 rows / 945 tickers;
- ACTIVE anchors: 982,398 rows; all panel keys are ACTIVE and no panel key is
  NO_TRADE; 458 ACTIVE-anchor rows are absent from the panel in 2021–2024.

Candidate-specific authority was decomposed:

- C1/C4: eligibility policy, PIT population, issuer/security identity, CA price
  basis, and capacity;
- C2: the C1/C4 gates plus historical volume/liquidity semantics and capacity;
- C3: population/identity plus publication timing, revision/vintage, bundle
  provenance, and the upstream liquidity mask.

Fixed Top-30 calendar-year mechanics then showed:

- 2022 to 2026-partial turnover: C1 41.21% to 43.78%, C2 33.39% to 35.55%,
  C4 23.32% to 25.47%;
- 2025-to-2026 selected-ticker Jaccard: C1 0.6438, C2 0.5748, C4 0.5511;
- C3 has no usable Top-30 date before 2025; in 2025/2026 its turnover is
  10.76%/11.24%, effective names 61.7/51.0, and persistence 8.00/8.37
  sessions.

These are descriptive mechanics. C3's apparent persistence/concentration is
support-driven. No era, policy, candidate status, capacity, orthogonality, or
predictive interpretation was admitted.

The follow-up score-separation diagnostic added a distinct geometry view:

- C2 median normalized rank-30/rank-31 gap: `0.05912`, with mean next-session
  turnover `32.62%`;
- C1: median gap `0.01089`, turnover `41.74%`;
- C4: median gap `0.00936`, turnover `23.26%`;
- C3: median gap `0.01810`, exact boundary-tie fraction `10.18%`, and only 275
  usable dates.

Gap-to-next-turnover Spearman associations are modest (`-0.071`, `-0.174`,
`-0.060`, `-0.115` for C1–C4), so turnover is not explained by one universal
thin-margin mechanism. This is representation-dependent structural evidence,
not predictive quality, causal evidence, or capacity.

## 4. Tooling and audit-control work

The run also audited whether its own research controls could produce false
green states:

- knowledge-base verifier: current `PASS`; current counts 43 experiments, 34
  findings, 15 no-retry entries, 17 source-capability entries, 6 synthesis
  documents;
- authority-packet verifier: current `PASS` after missing evidence-reference
  checks were repaired;
- packet/firewall control: hash-bound output `PASS`, 65/65 checks;
- lane verifier: latest process-scope output `PASS`, 10/10 checks;
- focused authority/eligibility tests: current focused suite 14/14 passing;
- formula mutation challenger: five declared C1/C2/C4 semantic mutations
  detected on a 3-ticker/150-session synthetic fixture;
- nested packet schema challenger: draft strict allowlist rejected five
  declared nested/missing mutations that the current verifier accepted;
- verifier freshness challenger: draft contract rejected four missing/stale
  result mutations while the unchanged packet remained valid;
- semantic challenger: disguised text/schema fields and unknown nested packet
  fields can still pass shallow current checks; unknown top-level packet fields
  fail.

Important interpretation: these PASS states are bounded process/hash/path/
contract evidence. They are not independent proof of scientific validity,
protected-payload absence, or PIT correctness. Draft challenger contracts were
not integrated into production verifiers.

## 5. Current decision state

| Area | Decision |
|---|---|
| C1/C2/C4 | Structural evidence only; `FUTURE_RESEARCH` |
| C3 | `BLOCKED` by sparse/late financial PIT support |
| Better-than-incumbent claim | Not established |
| Eligibility policy | `POLICY_AUTHORITY_MISSING` |
| Population/PIT authority | Unknown / blocked |
| Identity/survivorship | Unknown / blocked |
| Corporate-action basis | Unknown / blocked |
| Historical capacity | Unknown / blocked |
| Protected predictive evaluation | Closed / not authorized |
| Incumbent/canonical/cloud/capture/telemetry state | Untouched |

## 6. What this run explicitly did not prove

It did not prove:

- any positive or negative predictive performance;
- that C1/C2/C4 are better, orthogonal, or economically deployable;
- that C3 is intrinsically weak rather than source-sparse;
- that the 20-in-60 or complete-60 rule is the final policy;
- that the panel is population-complete or survivorship-safe;
- that ticker continuity equals issuer/security continuity;
- that price/CA basis is correct for every candidate window;
- that turnover proxies equal executable turnover or capacity;
- that provider snapshots, current metadata, or row mappings are PIT-safe;
- that the lane verifier proves runtime-level protected-data isolation.

## 7. Legitimate reopening conditions

The project should remain pre-admission until there is, at minimum:

1. A hash-bound authority record selecting exact eligibility semantics.
2. A population/issuer/ISIN/ticker-reuse/relisting/delisting PIT contract.
3. A corporate-action effective-date, knowledge-time, basis, and event-window
   linkage contract.
4. A financial publication/revision/vintage contract for C3.
5. Historical executable liquidity/capacity evidence if economics are claimed.
6. Independent review of any verifier hardening and a fresh clean replay.
7. Only after those gates: explicitly authorized protected common-support
   H5/H10 evaluation, with frozen candidate IDs and no model selection from
   protected outcomes.

Do not select the eligibility branch by convenience, code majority, sample
size, structural metrics, or perceived conservatism. Do not open protected
outcomes to resolve a structural or policy question. Do not create C5 or
promote a structural hypothesis based on this handoff.

## 8. Minimum audit procedure for the older ChatGPT session

1. Verify the current worktree, branch, baseline, current `HEAD`, dirty paths,
   and external staging root.
2. Read this handoff together with `V3` only as historical context; the
   machine-readable registries and the newer three checkpoints below are the
   current additions.
3. Verify the knowledge base and authority packet without changing them:

   ```powershell
   python research/verify_alpha_knowledge_base_v1.py
   python research/verify_alpha_data_authority_packet_v1.py --packet research_knowledge/data_authority_packet_v1.json
   python -m pytest tests/test_alpha_candidate_era_authority_v1.py tests/test_alpha_candidate_era_mechanics_v1.py tests/test_alpha_eligibility_era_delta_v1.py tests/test_alpha_candidate_score_separation_v1.py tests/test_alpha_data_authority_packet_v1.py tests/test_alpha_eligibility_policy_scenario_v1.py -q
   ```

4. Check that the registries reference files that exist and that the protected
   payload scan remains closed.
5. Verify the three continuation results:

   - `research_knowledge/candidate_era_authority_v1.json`
   - `research_knowledge/eligibility_era_delta_v1.json`
   - `research_knowledge/candidate_era_mechanics_v1.json`
   - `research_knowledge/candidate_score_separation_v1.json`

6. Treat every `PASS_STRUCTURAL_ONLY`, `SUPPORTED_SCOPED`, and verifier PASS as
   bounded evidence, not as a promotion or predictive result.
7. Confirm no protected field, target, outcome, incumbent result, production
   data, cloud, capture, or telemetry state was opened or modified.

## 9. Evidence-of-record map

Read these first:

- `research_knowledge/manifest.json`
- `research_knowledge/experiment_registry.jsonl`
- `research_knowledge/findings_index.jsonl`
- `research_knowledge/knowledge_synthesis.md`
- `research_knowledge/research_frontier.md`
- `research_knowledge/open_questions.md`
- `research_knowledge/research_journal.md`
- `research_knowledge/reproducibility.md`
- `research_knowledge/data_authority_packet_v1.json`
- `research_knowledge/data_authority_packet_v1.md`

Most relevant checkpoints:

- `docs/checkpoints/2026-09-20_ALPHA_HISTORICAL_ARCHAEOLOGY_AUDIT_RESULT_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_CONTINUATION_FRONTIER_AND_CONSTRUCTOR_REPLAY_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_ELIGIBILITY_PROVENANCE_HISTORY_AUDIT_RESULT_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_FORMULA_MUTATION_CHALLENGER_RESULT_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_PACKET_NESTED_SCHEMA_CHALLENGER_RESULT_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_VERIFIER_FRESHNESS_CHALLENGER_RESULT_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_CANDIDATE_ERA_AUTHORITY_RESULT_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_ELIGIBILITY_ERA_DELTA_RESULT_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_CANDIDATE_ERA_MECHANICS_RESULT_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_CANDIDATE_SCORE_SEPARATION_RESULT_V1.md`

## 10. Final handoff sentence

This isolated run substantially mapped and stress-tested the available
outcome-blind alpha research surface, but it found no authorized, PIT-safe,
population-complete, economically validated, or predictively superior model;
the correct handoff state remains `NO-GO / PRE-ADMISSION / OUTCOME-BLIND /
PREDICTIVE STAGE BLOCKED`.
