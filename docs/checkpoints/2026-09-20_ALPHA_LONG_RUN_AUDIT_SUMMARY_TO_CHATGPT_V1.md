# IDX-Trade Alpha Research — Long-Run Audit Summary to ChatGPT V1

Date: 2026-09-20 (Asia/Jakarta)  
Purpose: one compact handoff for an older ChatGPT session to audit the work
performed during the long isolated research run.

## Executive conclusion

The work produced a broad, outcome-blind pre-admission audit of the existing
IDX-Trade alpha surface. It reconstructed prior research and failure modes,
corrected the Stage-A structural implementation, measured the fixed C1-C4
candidate set, tested bounded new mechanisms, audited robustness and proxy
economics, mapped available data/source capability, and installed fail-closed
re-entry and privacy controls.

It did **not** prove a better model. Protected H5/H10 outcomes, IC, ICIR, OOS
returns, PnL, target-ranked spreads, incumbent comparisons, and prospective
performance were not opened. No candidate is `READY_FOR_REENTRY`.

Current scientific verdict:

`NO-GO / PRE-ADMISSION RESEARCH / PREDICTIVE STAGE BLOCKED`

The main unresolved gates are authoritative eligibility semantics, historical
PIT/available-at population, survivorship and issuer identity, corporate-action
price basis, revision/vintage, and executable capacity. These blockers are
independent; passing structural or tooling checks does not clear them.

## Lane and duration accounting

- Worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`
- Branch: `codex/alpha-available-data-20260919`
- Baseline: `58f094b8`
- Source research state audited before this summary: `855bb153cd7a5a4a7b862cd6986a81556eb0020e`.
- Source branch delta at that snapshot: 31 commits.
- Source branch commit interval at that snapshot: 2026-09-20 03:28:29 to
  09:02:02 Asia/Jakarta.
- The summary itself is recorded in later documentation-only commits; those
  commits do not alter the scientific evidence summarized here.
- The earlier marathon handoff records a wider research/documentation calendar
  span of roughly 23 hours. That is elapsed calendar span, not a claim of 23
  continuous hours of active compute or human attention.

All changes stayed in this isolated research/docs lane. The incumbent alpha,
canonical datasets/history, protected target/outcome vault, provider access,
cloud/R2, capture, telemetry, scheduler, counters, production artifacts, and
deployment state were not modified, reset, archived, or merged.

## Work completed, in research order

### 1. Archaeology and failure taxonomy

Prior alpha families and abandoned directions were mapped into separate
classes: engineering defects, source/PIT admission blocks, sparse capability,
structural overlap, economics/capacity caution, semantically invalid source
interpretations, and genuinely untested families. This prevents a blocked idea
from being mislabeled as a failed alpha.

### 2. Frozen, outcome-blind research contract

The lane froze exactly four candidate IDs, fixed formulas, chronological folds,
horizons, friction/stopping rules, and the no-sweep/no-rescue/no-retry boundary.
The future evaluation packet is specification-only. It cannot execute before an
independent Data-QA/admission artifact passes.

### 3. Stage-A engineering correction

The initial Stage-A implementation was rejected as engineering evidence because
of a reversed beta denominator, mask/rank ordering problems, incomplete official
session rolling behavior, and insufficient financial knowledge-time guards. A
corrected implementation was built without expanding the candidate budget.

Independent structural checks and a constructor replay then matched 981,940
panel keys, eligibility, scores, and average-tie ranks with zero mismatches.
That proves implementation reproducibility only; it does not prove PIT,
population completeness, survivorship safety, corporate-action basis, capacity,
or predictive value.

### 4. Fixed C1-C4 structural audit

| Candidate | Mechanism | Finite support | Structural/economic observation | Current status |
|---|---|---:|---|---|
| C1 `residual_reversal_5_v1` | residual short-horizon reversal | 295,243 / 95.0065% | Top-30 turnover 42.15%; proxy burden 25.29 bps/NAV; most basis-sensitive | `FUTURE_RESEARCH` |
| C2 `participation_confirmation_5_v1` | participation confirmation | 310,761 / 100.0000% | Top-30 turnover 32.91%; proxy burden 19.75 bps/NAV; broad support, heavy tails | `FUTURE_RESEARCH` |
| C3 `financial_quality_growth_v1` | financial quality/growth | 30,994 / 9.9736% | 278 usable Top-30 dates; Top-10 share 25.77%; sparse/late PIT support | `BLOCKED` |
| C4 `path_efficiency_reversal_20_v1` | path-efficiency reversal | 310,323 / 99.8591% | Top-30 turnover 23.70%; proxy burden 14.22 bps/NAV; low-churn overlap caution | `FUTURE_RESEARCH` |

These are structural rankings and proxy economics, not predictive metrics.

### 5. Orthogonality, robustness, and combinations

- Monotone rank/z/robust-z variants reproduced the same Top-30 sets and were
  closed as representation duplicates.
- C1/C4 showed the main structural dependence caution; low Top-K overlap was
  not treated as proof of predictive orthogonality.
- Structural Spearman diagnostics were measured only on features/scores; they
  were not target correlations.
- Key-aligned robustness replay superseded an earlier positional-merge result.
- Equal-weight combinations were measured structurally, but no weight search
  and no new candidate ID were created.

### 6. New mechanism review

| Hypothesis | Result | Disposition |
|---|---|---|
| H-LIQ-01 activity variability | 155,679 finite rows; mean Top-30 turnover 10.31%; bottom-value Q1 share 39.67%; size-neutral variant lowered Q1 exposure but raised turnover | `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; same-surface C2 residual retry `NO-GO` |
| H-VOL-01 volatility compression | 308,514 finite rows; mean Top-30 turnover 29.2778%; bottom-value Q1 share 42.72%; CA stress changed 547 scores and 8,876 ranks | future only; horizon-sensitive; not admitted |
| H-EXC-01 raw excursion asymmetry | score tails -16.2/5.0; turnover 40.9694% | `STRUCTURALLY_REJECTED_AS_WRITTEN` |
| H-EXC-02 bounded excursion balance | 308,067 finite rows; score bounded [-1,1]; turnover 40.7750% | future only; horizon-sensitive; not admitted |

No C5 was created. Other directions such as intraday/overnight, financial
change disagreement, flow-conditioned events, ownership/free-float, sector
history, effort-vs-result, breakout/rejection, and dispersion were either
source-blocked, redundant, untested, or left as future specifications.

### 7. Economics and capacity

The lane measured fixed Top-K churn, persistence, turnover tails, repeat-name
concentration, HHI/effective names, value/volume quartiles, and friction
proxies. The result is a warning, not a return claim: historical ADV, spread,
queue, fill probability, and executable capacity authority are missing.
Snapshot or metadata fields were not promoted into historical liquidity features.

### 8. Corporate-action, issuer, and identity forensics

- HLC overlay: 1,657 rows.
- Unresolved non-stable-scale stress rows: 188, disjoint from the overlay.
- C1 is the most fragile under the registered unresolved price-basis stress.
- No price was silently rescaled or repaired.
- No corporate-action event was inferred from share-count or price movement
  alone.
- Future admission requires complete event-to-window linkage, issuer/ISIN
  continuity, effective date plus knowledge time, explicit adjusted/unadjusted
  semantics, and PASS for every finite candidate window.

### 9. Available-data and source capability audit

| Surface | Observed capability | Why it remains non-admitted |
|---|---:|---|
| Official sessions | 1,260 sessions | calendar only, not population/PIT authority |
| Tradability anchors | 1,104,064 rows | same-session structural mask only |
| Main structural panel | ~981,940 unique ticker/date rows | population/PIT/CA completeness unresolved |
| Foreign flow | 1,129,024 rows / 1,288 sessions | publication time, revision, issuer, CA, and completeness unknown |
| Dataset-Saham-IDX | 1,014 CSVs / 1,146,324 rows | 4 unmapped tickers, 11 non-identical duplicate groups, no row-level PIT/vintage |
| Listing/delisting | 440 monthly files; 962 current; 163 delisted | six conflicts; no daily PIT membership |
| LBRE free float | 58,671 manifest files; 25,262 canonical; 868 unresolved lineage | monthly lineage, not daily PIT population |
| Statutory free float | 923/956 exact shares at 2025-12-31; 2026-03-31 percentage-only | no continuous historical PIT panel |
| HSC ownership events | 59 events / 55 effective tickers | event-only; no daily PIT feature |
| Broker/margin | 326 eligible; 220 margin; 965 stock; 106 eligible absent | snapshot-only; financing semantics unresolved |
| Panel depth | 19 fields / 18,835 rows / 12 symbols | no row-level PIT, identity, revision, CA, or execution semantics |
| Historical Open | 201,415/310,761 positive finite; 20,995 source transitions | source/PIT/CA/basis semantics unresolved |
| TradingView / Investing BBCA | 6,356 / 2,065 rows | partial and basis-divergent; 0/1,568 exact OHLCV overlap |

The local-surface closure review found no new admissible source contract. More
provider/source searching without row-level PIT, vintage, identity, CA, and
deterministic duplicate-source semantics was classified as low-value/no-retry.

### 10. Eligibility contract contradiction

This is the most important policy blocker:

- protocol/packet prose says a 60-session lookback with at least 20 finite
  observations;
- both Stage-A implementations use `rolling(window=window, min_periods=window)`;
- current implementation-aligned population: 310,761 rows;
- literal minimum-20 interpretation: 348,765 rows;
- difference: 38,004 rows.

The provenance review clarified that 60 is described as the trailing official
session lookback and 20 as the minimum finite-observation rule; a generic
security-master warm-up path is separate. It did not locate authoritative
incumbent-specific authority. The correct classification is
`POLICY_AUTHORITY_MISSING` / `BLOCKED_POLICY_CONFLICT`.

No population was selected by convenience, chronology, code majority, or sample
size. No alternative panel was regenerated.

### 11. Common-support census

Under the current implementation-aligned mask, the exact finite intersection
of C1/C2/C3/C4 is 30,861 rows, or 9.9308% of current eligible rows. There are
277 dates with at least 30 all-four names; maximum daily all-four support is
175 and median daily support is 0 because C3 is sparse/late.

This is a structural support census only. It does not open outcomes and does
not select the future evaluation population. The first daily aggregation
attempt was caught as wrong, corrected, and rerun before the accepted result.

## Current gates and controls

- Packet/firewall verification: `PASS`, 31/31.
- Future packet contract verifier: `PASS`, 65/65.
- Isolated lane integrity verifier: `PASS`, 10/10.
- Constructor replay: 981,940 keys, zero eligibility/score/rank mismatches.
- Durable knowledge base: 30 experiment records, 21 findings, 12 no-retry
  records, 17 source-capability entries.
- Current staging count: 160; current filename digest:
  `0c3bd7a88d5ce352b2ff397084e955b19cfa2a6602943486706183d1d8beddf3`.
- Packet SHA-256:
  `7756bc138cd4b7da9ac2a5ad09c7fe5a10addeb76e54f9132b292bb73d212894`.
- Contract SHA-256:
  `a76cd5acdfe457668b6241c4d28d677e4c2b92a98f2a54b82401338a6d794d4d`.
- Protected payloads persisted: `false`.

Important interpretation: PASS means that the controls and fail-closed
specification are internally consistent. It does not mean the packet is
executable, the data is admitted, or the alpha is profitable.

Validation caveat at handoff time: a read-only worker unexpectedly left two
untracked files in the isolated worktree,
`research/alpha_eligibility_policy_scenario_v1.py` and
`tests/test_alpha_eligibility_policy_scenario_v1.py`. They are not part of the
audited evidence, were not staged or committed, and were not used to support
any conclusion here. Therefore the clean-worktree assertion applies to the
last verified clean snapshot, not to the final post-worker filesystem state.

## What is complete vs. what is not proven

### Substantially complete

- archaeology and failure taxonomy;
- fixed outcome-blind protocol and candidate budget;
- corrected structural C1-C4 construction;
- structural robustness, overlap, concentration, and proxy economics;
- bounded new-mechanism review;
- source/capability and local-surface inventory;
- corporate-action/identity/price-basis forensic characterization;
- constructor replay;
- packet contract, firewall, eligibility guard, and lane controls;
- durable registry, findings, no-retry, source matrix, and handoff docs.

### Explicitly not proven

- incumbent or candidate IC/ICIR;
- IC delta, sign consistency, rank-spread superiority;
- historical OOS superiority or PnL;
- incremental information versus incumbent;
- friction-adjusted realized return or executable capacity;
- safe H5/H10 common-support comparison;
- prospective evidence;
- `RESEARCH_SURVIVOR`, `PROSPECTIVE_PASS`, or `READY_FOR_REENTRY`.

## No-retry boundary

Do not repeat the same Stage-A implementation, monotone transforms, raw
H-EXC-01, same-surface H-LIQ residualization, exact foreign-flow formulation,
unsupported margin interpretation, current C3 YoY bundle, broad provider/source
search, CA rescaling/repair, eligibility selection by convenience, protected
predictive comparison, or C5 creation without genuinely new authoritative
evidence and an explicit re-entry decision.

## What the older ChatGPT audit should verify

1. Confirm the current branch/worktree/HEAD and clean status before reading
   historical claims.
2. Read the protocol, phase matrix, ledger, candidate registry, capability
   matrix, completion audit, and eligibility contradiction packet.
3. Reproduce the 60-versus-20 contradiction and confirm no population choice
   was silently made.
4. Distinguish structural/capability/proxy metrics from predictive evidence.
5. Confirm that packet/firewall/lane PASS states are scoped control evidence,
   not scientific admission.
6. Confirm there are exactly C1-C4, no C5, and zero
   `READY_FOR_REENTRY` candidates.
7. Confirm that source audits do not authorize scraping, backfill, rescaling,
   imputation, fallback providers, or protected-data access.
8. Confirm that the next legitimate gate is hash-bound policy/Data-QA/PIT/CA/
   identity/capacity admission, not another blind model tweak.

## Primary evidence paths

- `docs/checkpoints/2026-09-20_ALPHA_MARATHON_AUDIT_HANDOFF_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_LONG_RUN_HANDOFF_TO_CHATGPT_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_PROGRAM_COMPLETION_AUDIT_V1.md`
- `docs/checkpoints/2026-09-19_ALPHA_RESEARCH_PROGRAM_FINAL_HANDOFF_V1.md`
- `docs/checkpoints/2026-09-19_ALPHA_RESEARCH_PHASE_MATRIX_V1.md`
- `docs/checkpoints/2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`
- `docs/checkpoints/2026-09-19_CANDIDATE_REGISTRY_V1.md`
- `docs/checkpoints/2026-09-19_DATA_CAPABILITY_MATRIX_V1.md`
- `docs/checkpoints/2026-09-20_ALPHA_ELIGIBILITY_CONTRACT_CONTRADICTION_V1.md`
- `research_knowledge/manifest.json`
- `research_knowledge/knowledge_synthesis.md`
- `research_knowledge/research_frontier.md`
- `research_knowledge/open_questions.md`
- `research_knowledge/reproducibility.md`

## Final handoff sentence

The long isolated run produced a substantial and reproducible outcome-blind
structural audit, a durable negative-result knowledge base, and a fail-closed
pre-admission control system. It did not produce a proven better alpha. The
next scientifically meaningful action is authoritative resolution of the
eligibility contract and Data-QA admission of PIT/population/identity/CA/
revision/capacity evidence; until then the correct state is `NO-GO`.
