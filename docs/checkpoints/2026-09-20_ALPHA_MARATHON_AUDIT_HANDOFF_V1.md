# IDX-Trade Alpha Research — Marathon Audit Handoff V1

Date: 2026-09-20 (Asia/Jakarta)  
Purpose: compact, self-contained handoff for an older ChatGPT session to audit the
recent long-running isolated research lane.  
Status: `NO-GO / PRE-ADMISSION RESEARCH / HISTORICAL TARGET STAGE BLOCKED`

## One-paragraph answer

The lane did a broad, outcome-blind audit of the existing IDX-Trade alpha surface.
It reconstructed prior alpha families, corrected the Stage-A implementation,
measured four fixed candidate formulas structurally, stress-tested robustness,
turnover, concentration, corporate-action exposure, identity, source capability,
and future re-entry controls, and preserved the results in checkpoint artifacts.
The work did **not** establish that any model beats the incumbent: protected H5/H10
outcomes, IC, ICIR, OOS returns, target-ranked spreads, and prospective evidence
were never opened. The honest current conclusion is that C1/C2/C4 are conditional
future candidates, C3 is blocked by sparse/late financial support, several new
hypotheses remain pending or economically unsafe, and the entire predictive stage
is blocked by unresolved Data QA/PIT/identity/corporate-action/capacity authority.

## 1. Scope, time, and lane identity

- Isolated worktree:
  `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`
- Branch: `codex/alpha-available-data-20260919`
- Baseline used for lane integrity: `58f094b8`
- Research HEAD before this summary commit: `8f56cfe6eb8dfc1e27c452f6447cca4ab225345b`
- Current HEAD including this summary: `1925bba0b2aeac82a1fd82f6ab952fc85fc54eaa`
- Recorded commit span: `2026-09-19T09:11:47+07:00` to
  `2026-09-20T08:13:12+07:00`, 167 commits, roughly 23 hours of calendar
  span. This is a commit/log span, not a claim of continuous active compute.
- Worktree was clean after the handoff commit.
- All modifications stayed in this isolated branch/worktree.

The lane did not modify, reset, archive, merge, or overwrite the incumbent alpha,
V4-X1, Decision V2, canonical datasets/history, protected target/outcome vault,
capture runtime, cloud/R2, telemetry, scheduler, forward counters, production
artifacts, or model deployment state. No provider/network probe was used to
manufacture missing historical authority.

## 2. What was done, in research order

### A. Reconstructed the prior research program

Prior V2/V3/V4/V4-X1, financial, participation, price-path, regime, ranking,
foreign-flow, and abandoned/orphan families were mapped into a failure taxonomy.
The taxonomy keeps separate:

- engineering-conformance failure;
- source/PIT admission block;
- partial capability/sparse support;
- structural overlap caution;
- economic/capacity caution;
- semantically invalid source interpretation;
- untested family.

This prevents “not evaluated because blocked” from being misreported as “alpha
failed.”

### B. Froze the outcome-blind research contract

The fixed program defined exactly four candidate IDs, fixed formulas, fixed
chronological folds, fixed horizons, fixed friction/stopping rules, and no sign,
weight, lookback, rescue, retry, or search-until-win sweep. The future evaluation
packet is specification-only and cannot execute until a separate Data QA admission
artifact passes.

The protected target contract is the declared H5/H10 comparison under the frozen
population/common-support design. The lane never read the protected target values.

### C. Corrected and independently audited Stage A

The first Stage-A implementation was rejected as invalid engineering evidence due
to a reversed beta denominator, mask/rank ordering, incomplete official-session
rolling grid, and insufficient financial knowledge-time guards. A corrected
implementation was then built without changing the hypothesis budget.

The corrected structural audit covers schema, duplicate keys, source-key closure,
session/anchor hashes, eligibility-mask containment, rank bounds, artifact/code/
source hashes, 600 frozen sessions, and no network/provider imports or HTTP calls.
The independent verifier and later constructor replay passed these target-free
checks.

### D. Measured C1–C4 structurally

The corrected implementation population is 310,761 rows across 711 tickers. The
candidate registry remains exactly C1–C4; no C5 was created.

| ID | Fixed mechanism | Finite support / coverage | Structural/economic evidence | Status |
|---|---|---:|---|---|
| C1 | `residual_reversal_5_v1` | 295,243 / 95.0065% | Top-30 turnover 42.15%; base burden 25.29 bps/NAV; more basis-sensitive | `FUTURE_RESEARCH` |
| C2 | `participation_confirmation_5_v1` | 310,761 / 100.0000% | Top-30 turnover 32.91%; base burden 19.75 bps/NAV; broad support, heavy tails | `FUTURE_RESEARCH` |
| C3 | `financial_quality_growth_v1` | 30,994 / 9.9736% | 278 usable Top-30 dates; Top-10 share 25.77%; sparse/late financial PIT | `BLOCKED` |
| C4 | `path_efficiency_reversal_20_v1` | 310,323 / 99.8591% | Top-30 turnover 23.70%; base burden 14.22 bps/NAV; low-churn but low-value tilt/overlap caution | `FUTURE_RESEARCH` |

These are structural rankings and proxy economics only. They are not IC, ICIR,
returns, OOS, or evidence of superiority.

### E. Robustness, orthogonality, and combinations

- Monotone rank/z/robust-z transformations are Top-30 duplicates, not new
  candidates.
- An earlier positional-merge robustness variant was corrected; key-aligned
  results supersede it.
- Internal Spearman diagnostics were measured only structurally: C1/C2
  `-0.2304`, C1/C3 `-0.0237`, C1/C4 `0.4113`, C2/C3 `-0.0455`, C2/C4
  `-0.1191`, C3/C4 `-0.0326`.
- C1/C4 is the main duplication caution; low Top-K overlap is not treated as
  predictive orthogonality.
- Repeated names contribute approximately 89.33% / 88.83% / 90.68% of selected
  slots for C1/C2/C4 under the measured concentration view.
- Equal-weight C1+C4 had the lowest tested combination turnover, about 34.85%.
  It is a structural hypothesis, not a new candidate and not predictive evidence.

### F. New mechanism research

#### H-LIQ-01 — trading-activity variability state

- 155,679 finite rows; mean Top-30 turnover 10.31%.
- Bottom market-value Q1 share: 39.67%.
- Size-neutral residual reduced Q1 exposure to 14.983% but increased turnover to
  20.785%; it was not a free improvement.
- Q4 dependence on C2 varied about 0.0762–0.3053; bottom-value exposure varied
  about 29.47%–51.30%.
- Same-surface C2 residual retry: explicit `NO-GO`.
- Verdict: `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5.

#### H-VOL-01 — daily volatility compression

- Fixed representation: `-log(median_5(range_pct) / median_60(range_pct))`.
- 308,514 finite rows; mean Top-30 turnover 29.2778%.
- Bottom-value Q1 share: 42.72%.
- Corporate-action stress over 188 retained comparison rows changed 547 scores
  and 8,876 ranks; mean/minimum Top-30 overlap was 99.8307%/86.6667%.
- Fixed horizon forms `5/20`, `5/60`, and `20/120` materially differ; no horizon
  was selected. Verdict remains future research/novelty pending/economic caution.

#### H-EXC-01 and H-EXC-02 — excursion asymmetry

- H-EXC-01 raw form had score tails `-16.2 / 5.0` and 40.9694% Top-30
  turnover: `STRUCTURALLY_REJECTED_AS_WRITTEN`.
- H-EXC-02 bounded absolute-distance balance is in `[-1, 1]`, with 308,067
  finite rows and 40.7750% mean Top-30 turnover. Its `5/20/60` horizons have
  materially different turnover and overlap; no horizon was promoted.
- H-EXC-02 remains future research/novelty pending/economic caution, not C5.

Other ideas—intraday/overnight decomposition, financial change/price
disagreement, flow-conditioned events, quote/foreign-pressure interaction,
effort-vs-result variants, dispersion, ownership/free-float/HSC, and sector
history—remain future specifications, source-blocked, or untested. They were not
converted into extra candidates merely because the surface looked interesting.

### G. Economics and capacity

Completed target-free diagnostics covered Top-10/20/30/50 churn and persistence,
turnover tails, repeat-name concentration, HHI/effective names, market-value/
volume/value quartiles, fixed friction proxies, equal-weight combination burden,
listing-age, and low-value concentration.

The important result is a data-admission warning, not a return claim: historical
executable ADV, spread, queue, fill probability, and capacity authority are
missing. Snapshot or metadata fields were not promoted to historical liquidity
features.

### H. Corporate-action, issuer, and identity forensics

- Retained HLC overlay: 1,657 rows.
- Unresolved non-stable-scale rows: 188, disjoint from the overlay.
- C1 is materially more sensitive under the registered basis stress than C2/C4.
- No price was silently rescaled or repaired; no corporate-action event was
  inferred from share-count or price movement alone.
- Future admission requires complete event-to-window linkage, issuer/ISIN
  continuity, effective date plus knowledge time, adjusted/unadjusted basis
  semantics, and a PASS for every finite candidate window.

### I. Source and data-capability audits

These results describe availability/admissibility, not permission to scrape or
substitute a source:

| Surface | Recorded result | Why it did not admit predictive use |
|---|---|---|
| Official sessions | 1,260 frozen sessions | session grid only; not population/PIT authority |
| Tradability anchors | 1,104,064 rows | structural same-session mask only |
| Main structural panel | about 981,940 unique ticker/date rows | population/PIT/CA completeness unresolved |
| Corrected implementation population | 310,761 rows / 711 tickers | eligibility policy conflict and external QA remain |
| TradingView BBCA | 6,356 rows | basis/source/PIT contract absent; differs from IDX blocks |
| Investing BBCA | 2,065 rows | 0 exact OHLCV matches on 1,568 overlap dates; scale/basis divergent |
| Dataset-Saham-IDX | 1,014 CSVs / 1,146,324 rows | 4 unmapped tickers, 11 non-identical duplicate groups, no row-level PIT/vintage |
| Official foreign flow | 1,129,024 rows / 1,288 sessions | arithmetic/hash/calendar pass; publication time, CA, revision, issuer authority missing |
| Listing/delisting | 440 monthly files; 962 current; 163 delisted | six conflicts and no daily PIT membership |
| LBRE free float | 58,671 manifest files; 25,262 canonical; 868 unresolved lineage rows | monthly lineage, not daily population PIT |
| Statutory free float | 923/956 exact shares at 2025-12-31; 2026-03-31 percentage-only | no continuous historical PIT panel |
| HSC ownership events | 59 events / 55 effective tickers | event-only, not daily population feature |
| Broker/margin snapshot | 326 eligible; 220 margin; 965 stock; 106 eligible absent | one-date snapshot; 0/220 all-six equality; financing semantics unresolved |
| Panel-depth source | 19 fields / 18,835 rows / 12 symbols | structural arithmetic passes; PIT/identity/CA semantics absent |
| Historical Open capability | 201,415/310,761 positive finite, 64.8135%; 20,995 source transitions | source identity, PIT, CA, and basis remain blocked |
| Sector/market context | partial archives/metadata | no population-complete daily PIT membership |

The local-surface closure review found no unrecorded local evidence that would
change candidate, packet, or admission status. Repeating broad provider searches
without a new row-level PIT/vintage/identity/CA contract was classified as no-go.

### J. Red-team and independent reproduction

`research/alpha_c1234_constructor_replay_v1.py` independently rebuilt the
official-session grid, eligibility, C1/C2/C4 scores, and average-tie ranks. It
matched all 981,940 keys with zero eligibility, score, or rank mismatches.

This proves code/artifact reproduction only. It does **not** prove population
completeness, PIT availability, survivorship safety, corporate-action basis,
execution capacity, predictive value, or incumbent improvement.

The red-team found/corrected robustness alignment and combination liquidity
denominator issues, then re-ran structural controls. Those corrections improve
engineering trust; they do not create predictive evidence.

## 3. The most important unresolved blocker: eligibility policy

The protocol and packet prose say the trailing-60 liquidity rule requires at least
20 finite observations. The implementation uses:

`rolling(window=window, min_periods=window)`

for both declared rolling operations.

Therefore:

- implementation-aligned population: 310,761 rows;
- literal prose-aligned minimum-20 interpretation: 348,765 rows;
- difference: 38,004 rows;
- protocol freeze commit: `a02a1547`;
- implementation-addition commit: `1ebced27`;
- packet-closure commit: `9e4e54fa`;
- chronology does not establish policy authority;
- machine guard: `BLOCKED_POLICY_CONFLICT`.

No larger sample was selected for convenience. No panel was regenerated. The
authority record must bind the chosen rule, finite-value/count/median semantics,
session calendar, resulting row count, all protocol/implementation/packet/
manifest hashes, and regeneration authorization. The two legitimate choices are
code-aligned minimum-60 or prose-aligned explicitly defined minimum-20.

## 4. Machine evidence at current lane head

Latest recorded checks:

- packet contract verifier: `PASS`, 65/65;
- privacy/target firewall: `PASS`, 31/31;
- isolated lane integrity verifier: `PASS`, 10/10;
- staging count: 160 (including the current verifier attestation output);
- staging filename digest:
  `0c3bd7a88d5ce352b2ff397084e955b19cfa2a6602943486706183d1d8beddf3`;
- packet SHA-256:
  `7756bc138cd4b7da9ac2a5ad09c7fe5a10addeb76e54f9132b292bb73d212894`;
- packet contract SHA-256:
  `a76cd5acdfe457668b6241c4d28d677e4c2b92a98f2a54b82401338a6d794d4d`;
- eligibility guard SHA-256:
  `743ad3b809a11536506487e26dbb4d57809089960f91dd30ee777be8ccff5dd6`;
- firewall result SHA-256:
  `a55df4853c14f2b27f2b0d1f591ba35af1eadfe0d8cbaae697859f1ff926e397`.

The PASS results mean the controls correctly encode a fail-closed specification.
They do not mean the packet is executable or that the data is scientifically
admitted.

For an audit, bind the verifier result to its embedded `packet_sha256`,
`contract_sha256`, and repository HEAD. Older staging outputs may be historical
reruns with superseded hashes; do not select one by filename alone. The current
rerun used for this handoff reports HEAD `0d9ab3b5`, packet SHA
`7756bc138cd4b7da9ac2a5ad09c7fe5a10addeb76e54f9132b292bb73d212894`, and
contract SHA `a76cd5acdfe457668b6241c4d28d677e4c2b92a98f2a54b82401338a6d794d4d`.

## 5. What is genuinely complete versus not complete

### Complete or substantially complete

- archaeology and failure taxonomy;
- outcome-blind protocol and candidate budget;
- corrected structural C1–C4 construction;
- target-free robustness, orthogonality, concentration, and proxy economics;
- bounded new-mechanism review;
- source/capability inventory and local-surface closure;
- CA/identity/price-basis forensic characterization;
- independent constructor replay;
- packet contract, target firewall, eligibility guard, and lane-integrity
  controls;
- durable checkpoint/handoff documentation and negative-result preservation.

### Not proven and should not be inferred

- incumbent IC or candidate IC;
- IC delta, ICIR, sign consistency, or rank-spread superiority;
- historical OOS superiority;
- incremental information against the incumbent;
- realized friction-adjusted return or executable capacity;
- safe H5/H10 common-support comparison;
- prospective evidence;
- `RESEARCH_SURVIVOR`, `PROSPECTIVE_PASS`, or `READY_FOR_REENTRY`.

## 6. Current verdict/state machine

- A archaeology: `COMPLETE`.
- B data/PIT/provenance: `COMPLETE / ADMISSION BLOCKED`.
- C structural C1–C4: `COMPLETE STRUCTURAL`.
- D C3 capability: `COMPLETE CAPABILITY / BLOCKED SCIENCE`.
- E orthogonality: `COMPLETE STRUCTURAL`.
- F–J mechanism/literature/representation/horizon work: `COMPLETE BOUNDED`.
- K robustness: `COMPLETE STRUCTURAL / CORRECTED`.
- L economics: `PARTIAL / PROXY COMPLETE`.
- M combinations: `COMPLETE STRUCTURAL / LIQUIDITY CAUTION`.
- N rejection: `COMPLETE BOUNDED`.
- O future data: `COMPLETE INVENTORY / BLOCKED ACCESS`.
- P tooling: `COMPLETE MILESTONE`.
- Q red-team: `PARTIAL / CORRECTED; readiness still blocked`.
- R novelty: `COMPLETE MILESTONE; exactly C1–C4 preserved`.
- S question management: `ACTIVE`.
- U firewall: `COMPLETE / RECHECK PER RUN`.
- V re-entry queue: `COMPLETE SPECIFICATION / NONE READY`.
- W future packet: `COMPLETE SPECIFICATION / BLOCKED`.
- X/Y knowledge and negative preservation: `COMPLETE MILESTONE`.
- Z autonomous continuation: `ACTIVE` only for non-redundant outcome-blind work.

## 7. Audit instructions for the older ChatGPT session

Please audit this handoff, not just accept its prose:

1. Verify branch, worktree, HEAD, baseline ancestry, and clean status.
2. Read the frozen protocol, program completion audit, phase matrix, ledger,
   candidate registry, data capability matrix, and eligibility contradiction.
3. Confirm that every displayed metric is structural/capability/proxy evidence,
   not target-derived predictive evidence.
4. Reproduce the eligibility contradiction from protocol, packet, implementation,
   provenance chronology, and guard output.
5. Confirm packet PASS means fail-closed specification validity, not executability.
6. Confirm no candidate is `READY_FOR_REENTRY` and no C5 exists.
7. Confirm that source audit rows do not authorize scraping, backfill, rescaling,
   imputation, fallback-provider substitution, or protected-data access.
8. If policy authority is supplied later, require a hash-bound resolution and
   isolated regeneration/replay before any protected comparison.

## 8. Durable artifacts to read next

Recommended order:

1. This file: `2026-09-20_ALPHA_MARATHON_AUDIT_HANDOFF_V1.md`.
2. `2026-09-20_ALPHA_LONG_RUN_HANDOFF_TO_CHATGPT_V1.md`.
3. `2026-09-20_ALPHA_PROGRAM_COMPLETION_AUDIT_V1.md`.
4. `2026-09-19_ALPHA_RESEARCH_PROGRAM_FINAL_HANDOFF_V1.md`.
5. `2026-09-19_ALPHA_RESEARCH_PHASE_MATRIX_V1.md`.
6. `2026-09-19_ALPHA_RESEARCH_LEDGER_V1.md`.
7. `2026-09-19_CANDIDATE_REGISTRY_V1.md`.
8. `2026-09-19_DATA_CAPABILITY_MATRIX_V1.md`.
9. `2026-09-20_ALPHA_ELIGIBILITY_CONTRACT_CONTRADICTION_V1.md`.
10. `2026-09-20_ALPHA_ELIGIBILITY_POLICY_RESOLUTION_PACKET_V1.md`.
11. `2026-09-19_ALPHA_FAILURE_TAXONOMY_V1.md`.
12. `2026-09-19_REENTRY_QUEUE_V1.md`.

Supporting source/result files are named consistently under `docs/checkpoints/`
and the executable/replay/verifier scripts are under `research/`. The summary is
intended as the navigation layer; the linked checkpoints remain the evidence of
record.

## Final handoff sentence

The last 23-hour recorded lane span produced a substantial, reproducible,
outcome-blind structural audit and a fail-closed admission system. It did **not**
produce a proven better alpha. The next scientifically meaningful decision is
not another blind model tweak; it is authoritative resolution of the eligibility
contract and, separately, Data QA admission of PIT/population/identity/CA/
capacity/common-support evidence. Until those gates pass, the correct state is
`NO-GO`, with C1/C2/C4 conditional, C3 blocked, H-LIQ/H-VOL/H-EXC-02 pending,
and all predictive claims unknown.
