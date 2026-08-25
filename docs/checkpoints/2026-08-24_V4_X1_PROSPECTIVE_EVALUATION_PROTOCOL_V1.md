# V4-X1 Prospective Evaluation Protocol V1

Date: 2026-08-24 (Asia/Jakarta)
Branch: `research/idx-v4-x1-prospective-evaluation-protocol-v1`
Decision: `V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1_FROZEN_OUTCOME_BLIND`

## 0. Purpose and controlling scope

This document preregisters the confirmatory evaluation of the active 100-session prospective IDX-Trade experiment **before protected prospective outcomes are opened**.

Controlling experiment identity:

- model: `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`;
- generation: `V4-X1-CLEAN`;
- model fingerprint: `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`;
- ranking order: `alpha_consensus DESC`, ticker ascending as deterministic tie-break;
- prospective gate: 100 official sessions under the already-frozen forward counter contract;
- Decision layer: frozen Decision V2 Minimal;
- Sizing layer: frozen Sizing V1;
- Execution layer: frozen Execution V1;
- historical OOS Spearman IC approximately `0.098054`, used only as prior context and **not** as a forward acceptance cutoff.

The older `IDX Trade — 100-Session Forward Evaluation Protocol V1` committed on the historical `research/idx-forward-evaluation-protocol-v1` lane governs the older O2/Reliability experiment. It is useful as governance precedent but **does not govern this V4-X1 prospective experiment**.

This protocol does not change the model, score, rank, universe, Decision, Sizing, Execution, counter, outcome protection, or forward capture contract. It does not authorize any model retuning or strategy change during the 100-session gate.

## 1. Outcome-blindness and access rule

Protected prospective outcomes remain sealed throughout accumulation.

### 1.1 Before final evaluation

For sessions 0 through 99, permitted inspection is limited to operational/provenance health that is already allowed by the forward contract, including:

- capture success and source identity;
- universe/session identity;
- score/rank artifact existence and hashes;
- Decision/Sizing/Execution artifact existence and hashes;
- Official Open provenance and legitimate pending state;
- PaperState continuity/invariants;
- CA/dividend evidence state;
- scheduler/runtime health;
- model/fingerprint and feature-order identity.

Forbidden before final outcome access:

- protected forward returns or target labels;
- forward IC or rank-bucket realized returns;
- realized prospective alpha hit rates;
- prospective PAPER P&L/NAV performance if it is protected by the controlling outcome-vault contract;
- Sharpe, Sortino, drawdown, CAGR, benchmark excess return, or any other protected economic result;
- any model/feature/Decision/Sizing/Execution tuning informed by prospective outcomes.

If the controlling forward-vault contract is stricter than this document, the stricter rule controls.

### 1.2 Earliest final access

Final confirmatory outcome access is permitted only when all of the following are true:

1. the canonical forward counter is exactly `100/100`;
2. all 100 score/session artifacts required by the frozen experiment validate against the V4-X1 fingerprint and provenance contract;
3. the canonical forward outcome target required for the alpha evaluation is mature for every session that must mature under the frozen target contract;
4. PaperState continuity and execution provenance required for economic evaluation are valid, or any invalidity is explicitly classified before outcomes are loaded;
5. this protocol is committed and hash-pinned;
6. evaluator implementation, if separate, is committed and hash-pinned before it loads protected outcomes;
7. no prior unauthorized prospective outcome access is known.

If the canonical alpha target is not uniquely resolvable from the frozen V4-X1 manifest/signoff lineage, the evaluator must fail closed. It must not choose a target or horizon after looking at outcomes.

## 2. Scientific questions

The final report must answer five separate questions. A single Sharpe ratio must not substitute for them.

### Q1 — Alpha ranking

Does frozen V4-X1 ranking contain genuinely prospective cross-sectional information about the same canonical future outcome used by the accepted V4-X1 historical OOS signoff?

### Q2 — Decision behavior

Does frozen Decision V2 turn ranks into a stable portfolio-selection process without pathological churn, concentration, or underfill?

### Q3 — Execution implementation

What portion of realized economics is attributable to Official-Open availability, pending orders, capacity, fees, slippage, stamp duty, and other frozen execution mechanics?

### Q4 — Portfolio economics

Does the actual frozen PAPER state path produce positive prospective net economics with tolerable risk?

### Q5 — Experiment validity

Was the forward evidence complete and deterministic enough that Q1–Q4 can be interpreted scientifically?

Alpha, Decision, Execution, Portfolio, and Operational verdicts must remain separable. One layer must not rescue a failure in another by post-hoc reinterpretation.

## 3. Canonical evaluation sample

### 3.1 Alpha sample

The alpha sample is the exact accepted V4-X1 scored/eligible cross-section for each official signal session, joined only to the canonical frozen V4-X1 outcome target.

`CANONICAL_V4_X1_OUTCOME_TARGET` is defined as:

> the exact outcome/forward-return construction used by the accepted V4-X1 historical OOS signoff that produced the frozen historical OOS IC of approximately 0.098054, resolved from the model/signoff manifest tied to model fingerprint `30e1b505...f79cf`.

The evaluator may not substitute H5, H10, H20, a different return definition, a different corporate-action treatment, or another target unless the frozen model/signoff manifest itself identifies that target as the canonical target. If more than one target was formally primary in the frozen signoff, their PRIMARY/SECONDARY ordering must be resolved from pre-existing frozen artifacts before outcome access; it may not be chosen from forward results.

### 3.2 Portfolio sample

The portfolio sample is the actual sequential PAPER state generated by frozen Decision V2, Sizing V1, and Execution V1.

A certified `OpenPrice <= 0` or otherwise unavailable official Open is a legitimate pending economic state under the frozen execution contract. It is not silently excluded merely because it hurts execution.

A capture/runtime failure is not the same as a legitimate unavailable Open and must remain separately classified.

### 3.3 No silent exclusions

Every counted forward session must appear in an evaluation ledger with one of these states:

- `EVALUABLE`;
- `LEGITIMATE_PENDING_OPEN`;
- `OPERATIONAL_FAILURE`;
- `DATA_INCOMPLETE`;
- `EXCLUDED_IMPLEMENTATION_DEFECT`;
- `NOT_YET_TARGET_MATURED`;
- `MARKET_NONTRADING` where the frozen counter contract itself recognizes such a state.

The original 100-session counter semantics are not altered by this evaluation protocol. Evaluation exclusions do not retroactively rewrite the forward counter.

## 4. Primary alpha metrics

The confirmatory alpha family is intentionally small.

### A1 — Mean daily cross-sectional Spearman IC — PRIMARY

For each evaluable session `t`, compute the cross-sectional Spearman rank correlation:

`IC_t = Spearman(alpha_consensus_t, CANONICAL_V4_X1_OUTCOME_TARGET_t)`

using only the exact frozen eligible/scored rows for that signal session with a resolved canonical outcome.

Report:

- number of metric-eligible sessions;
- number of evaluated rows per session;
- `mean(IC_t)` — PRIMARY alpha statistic;
- `median(IC_t)`;
- sample standard deviation of `IC_t`;
- positive-IC session fraction;
- 95% session-block-bootstrap confidence interval for mean IC.

Do not pool all ticker rows and pretend they are independent observations.

### A2 — IC information ratio — SECONDARY

Unannualized:

`ICIR = mean(IC_t) / sample_std(IC_t)`

If an annualized display is shown, use:

`ICIR_ann = ICIR * sqrt(252)`

and label it explicitly as annualized. The unannualized value remains the canonical ICIR statistic.

### A3 — Rank-bucket monotonicity — SECONDARY

Within each evaluable session, form deterministic rank groups from the frozen ranking:

- ranks 1–10;
- ranks 11–20;
- ranks 21–50;
- ranks >50 where available.

Report the session-aggregated canonical outcome for each group and whether the broad ordering is directionally monotonic. These groups are fixed now and may not be optimized after outcome access.

### A4 — Top-k economics — SECONDARY

Report canonical outcome summaries for frozen top-10 and top-20 ranks, including mean, median, and bootstrap uncertainty across sessions.

These are supporting diagnostics; they do not replace A1 as the primary alpha metric.

## 5. Primary portfolio and risk metrics

Let `NAV_t` be the official end-of-session PAPER total-return NAV produced by the frozen accounting contract, including valid dividend receivables where required by that contract. Let:

`r_t = NAV_t / NAV_(t-1) - 1`.

No alternative NAV reconstruction may be selected after observing performance.

### P1 — Net total return — PRIMARY economic statistic

`NetTotalReturn = NAV_end / NAV_start - 1`.

The strategy result is after frozen fees, slippage, stamp duty, capacity, pending-order mechanics, and dividend accounting.

### P2 — Annualized volatility — PRIMARY risk statistic

Using sample standard deviation (`ddof=1`):

`AnnualizedVol = std(r_t) * sqrt(252)`.

### P3 — Sharpe ratio — PRIMARY risk-adjusted statistic

The preregistered primary Sharpe convention uses a zero daily risk-free rate:

`Sharpe_0 = mean(r_t) / std(r_t) * sqrt(252)`.

This is a stable reporting convention chosen before outcomes are opened. It is not a claim that the true opportunity cost of cash is zero. No changing risk-free series may be introduced into the PRIMARY Sharpe after outcomes are observed.

A separately sourced risk-free-adjusted Sharpe may be shown later only as a clearly labeled SECONDARY sensitivity using a source/rule frozen before outcome access.

### P4 — Maximum drawdown — PRIMARY risk statistic

For cumulative NAV path `NAV_t`:

`Drawdown_t = NAV_t / max_{s<=t}(NAV_s) - 1`

`MaxDrawdown = min(Drawdown_t)`.

Report the peak date, trough date, and recovery status without changing the definition.

### P5 — Sortino — SECONDARY

Use minimum acceptable daily return `MAR = 0`.

`DownsideDev_daily = sqrt(mean(min(r_t, 0)^2))`

`Sortino_0 = mean(r_t) / DownsideDev_daily * sqrt(252)`.

If no negative daily return exists, report the ratio as undefined/infinite by convention and do not use it as a rescue gate.

### P6 — Annualized geometric return / CAGR-equivalent — SECONDARY descriptive

For `N` evaluated trading-session transitions:

`AnnualizedGeometricReturn = (NAV_end / NAV_start)^(252/N) - 1`.

Because the confirmatory window is only about 100 sessions, this is labeled a CAGR-equivalent annualization, not a directly observed one-year CAGR, and it is not an independent PASS gate.

### P7 — Calmar — SECONDARY descriptive

`Calmar = AnnualizedGeometricReturn / abs(MaxDrawdown)` when denominator is nonzero.

## 6. Benchmark protocol

Benchmark comparisons are preregistered but must not create false apples-to-apples precision.

### B1 — IHSG / IDX Composite price-index comparator — PRIMARY contextual benchmark

Use the official/pinned IHSG closing index level on the same first and last portfolio marking sessions:

`IHSG_Return = IHSG_end / IHSG_start - 1`.

Then:

`NetExcessReturn_vs_IHSG = NetTotalReturn - IHSG_Return`.

The IHSG comparator is a price-index comparator unless an already-authoritative total-return series is explicitly pinned before outcome access. Therefore it must be labeled as such; the strategy includes its frozen dividend accounting and is not perfectly cost/dividend matched to the index.

The IHSG artifact/source rule must be acquired and hash-pinned before the evaluator opens strategy outcomes. If a trustworthy aligned benchmark cannot be pinned outcome-blind, B1 becomes `BENCHMARK_UNAVAILABLE` rather than being reconstructed ad hoc after seeing strategy returns.

### B2 — Eligible-universe equal-weight gross comparator — SECONDARY

If it can be constructed solely from the same frozen eligible universe and already-authorized market-price evidence, report a daily equal-weight eligible-universe close-to-close **gross** comparator.

It must be labeled gross and non-executable unless matching costs/execution are genuinely modeled. Strategy net return must not be presented as directly cost-matched to this comparator.

### B3 — Cash / zero-return reference — SECONDARY

A zero-return line may be shown as an absolute sign reference. It is not treated as a realistic investable benchmark.

### No post-hoc benchmark shopping

Do not add a benchmark because it makes the strategy look better or worse after the outcome vault is opened. Any additional benchmark is exploratory and must be labeled as post-confirmatory unless it was separately committed before outcome access.

## 7. Decision and execution diagnostics

These diagnostics explain *why* economics occurred; they do not alter the alpha target.

Report at minimum:

- entries and exits per session;
- average and median number of holdings;
- average and median holding duration in official sessions;
- rank at entry and rank at exit;
- underfill frequency;
- daily and aggregate turnover;
- intended versus executed notional;
- pending-order-leg count and rate;
- pending duration distribution;
- official-Open unavailable rate;
- capacity-truncation count and rate;
- cash utilization;
- explicit buy fees;
- explicit sell fees;
- modeled slippage;
- stamp duty;
- total explicit modeled cost;
- dividend contribution/receivables where applicable.

### 7.1 Turnover convention

For session `t`:

`Turnover_t = (gross executed buy notional_t + gross executed sell notional_t) / NAV_(t-1)`.

Aggregate turnover is `sum(Turnover_t)` over the evaluation path.

### 7.2 Pending-order rate

`PendingOrderRate = number of prepared execution legs that remain pending because the frozen execution contract could not execute them / total prepared execution legs requiring an Open execution decision`.

A legitimate unavailable official Open remains in the denominator.

### 7.3 Cost drag

Always report each modeled cost component in rupiah and as a fraction of starting NAV and gross turnover.

If the frozen engine already exposes a mechanically identical pre-cost/gross shadow, the evaluator may additionally report `gross-shadow return - net return`. If no such frozen shadow exists, do not invent one after outcome access; report cost components directly.

## 8. Statistical uncertainty

One hundred sessions is a modest sample. Effect sizes and uncertainty are mandatory; p-values are secondary.

### 8.1 Session-level moving-block bootstrap

Frozen bootstrap convention:

- resampling unit: ordered official sessions, not ticker rows;
- method: moving-block bootstrap;
- block length: 5 sessions;
- replicates: 10,000;
- deterministic seed: `20260824`;
- interval: percentile 95% confidence interval (`2.5%`, `97.5%`).

For IC, bootstrap the ordered session IC series.

For PAPER economics, bootstrap ordered daily NAV returns and reconstruct each bootstrap path by compounding returns. Report bootstrap uncertainty for mean daily return, Sharpe, and compounded return. A bootstrap distribution of MaxDrawdown may be shown as descriptive uncertainty.

Any non-finite bootstrap replicates must be counted and reported. They may not be silently replaced. If bootstrap computation becomes numerically invalid, the uncertainty field is `INCONCLUSIVE_STATISTICS`, not a reason to choose a different method after seeing results.

### 8.2 Hypothesis test boundary

If a formal alpha test is reported, the only confirmatory null is:

`H0: mean session IC <= 0` versus `H1: mean session IC > 0`.

The bootstrap confidence interval and effect size remain primary. No multiple-testing garden or new significance family may be introduced after outcome access.

## 9. Fixed temporal and robustness slices

Confirmatory robustness diagnostics are limited to:

1. sessions 1–50 versus sessions 51–100 in frozen forward-counter order;
2. rank groups fixed in Section 4.3;
3. market-up versus market-down sessions using same-session IHSG close-to-close return with the frozen split `UP >= 0`, `DOWN < 0`, only if the IHSG source was pinned outcome-blind.

These are diagnostics, not alternate routes to PASS.

Forbidden confirmatory additions after outcome access include arbitrary sectors, volatility thresholds, hand-selected dates, alternative rank cutoffs, different halves, or regime definitions chosen from the observed result.

## 10. Interim milestone policy

The active experiment uses a strict no-peek policy.

### Sessions 0–19

Operational/provenance health only. No protected performance inspection.

### Session 20

Operational completeness checkpoint only. No forward IC, P&L, Sharpe, hit rate, or realized top-k outcome review. No retune.

### Session 50

Operational/provenance midpoint checkpoint only. Fixed first-50/last-50 evaluation boundaries may be verified, but outcomes remain sealed. No retune and no threshold change.

### Session 100

Do not immediately inspect outcomes merely because the counter reaches 100. First verify the final access gates in Section 1.2, including canonical target maturity and protocol/evaluator pins. Then perform the one confirmatory evaluation.

No poor-looking operational proxy or anecdotal market observation may justify early model replacement. Pure implementation defects may be repaired, but must be documented outcome-blind.

## 11. Operational validity and denominator rules

### 11.1 Alpha denominator

Alpha metrics use only sessions with:

- valid frozen V4-X1 scored/eligible cross-section;
- uniquely resolved canonical target;
- matured target evidence;
- enough finite rows to compute the preregistered statistic.

Every non-evaluable session remains listed with exact reason. No silent deletion is allowed.

### 11.2 Portfolio denominator

Portfolio metrics require a continuous deterministic PaperState path. Legitimate pending execution is part of that path and remains included.

If a counted session cannot be deterministically reconstructed because required PIT evidence/state was lost or corrupted, the portfolio evaluation is operationally invalid unless an accepted outcome-blind remediation can reconstruct the exact state from immutable evidence without changing scientific contracts.

### 11.3 Invalidity triggers

The overall experiment is `PROSPECTIVE_INVALID_OPERATIONAL` if any of the following occurs and cannot be remedied under the existing outcome-blind defect policy:

- unauthorized prospective outcome access before the final access marker/gate;
- model/fingerprint substitution;
- outcome-informed model, feature, Decision, Sizing, or Execution change;
- unreconstructable sequential PaperState continuity;
- outcome/score/session alignment cannot be proven;
- canonical V4-X1 target cannot be uniquely resolved from frozen pre-outcome lineage.

Operational invalidity is not relabeled as alpha failure.

## 12. Attribution boundary

The final report should explain the realized result using only mechanically supportable components:

- alpha/rank quality;
- Decision turnover/holding behavior;
- intended versus executed exposure;
- pending/Open availability;
- capacity truncation;
- fees;
- slippage;
- stamp duty;
- dividend contribution;
- cash utilization.

Do not claim a precise causal decomposition if the engine does not expose the required frozen counterfactual states. In particular, a Decision-V2 incremental-return counterfactual or pre-cost gross strategy may not be invented after outcome access merely to create an attractive attribution chart.

## 13. Frozen component verdicts

### 13.1 Alpha verdict

`ALPHA_CONFIRMED_POSITIVE` if:

- experiment/alpha sample is valid;
- `mean(IC_t) > 0`; and
- the 95% moving-block-bootstrap lower bound for mean IC is strictly `> 0`.

`ALPHA_DIRECTIONALLY_POSITIVE` if:

- sample is valid;
- `mean(IC_t) > 0`; but
- the 95% CI includes or crosses zero.

`ALPHA_FAIL` if:

- sample is valid; and
- `mean(IC_t) <= 0`.

`ALPHA_INVALID` if canonical labels/alignment/provenance are not evaluable.

The historical IC near 0.098054 is reported only as context. Forward IC is not required to exceed it.

### 13.2 Economic verdict

`ECONOMIC_POSITIVE` if:

- continuous PaperState evaluation is valid;
- `NetTotalReturn > 0`; and
- `Sharpe_0 > 0`.

`ECONOMIC_MIXED` if the portfolio evaluation is valid and exactly one of those two directional conditions is positive.

`ECONOMIC_FAIL` if:

- evaluation is valid;
- `NetTotalReturn <= 0`; and
- `Sharpe_0 <= 0`.

Benchmark excess return and MaxDrawdown are mandatory context but are not allowed to rescue a negative net economic verdict. `NetExcessReturn_vs_IHSG > 0` is reported as `BENCHMARK_OUTPERFORM` when B1 is available; otherwise benchmark status is explicitly unavailable.

### 13.3 Execution verdict

`EXECUTION_HEALTHY` if the full sequential execution/accounting path satisfies frozen invariants and remains reconstructable. Cost, pending, and capacity statistics may be material without making the implementation broken.

`EXECUTION_MATERIAL_DRAG` if execution remains contract-valid but the mechanically supportable cost/pending/capacity evidence shows substantial erosion of otherwise positive selection/economic evidence. This is a diagnostic classification and may not change frozen mechanics retroactively.

`EXECUTION_BROKEN` if frozen execution/accounting invariants are breached or state continuity cannot be reconstructed.

## 14. Frozen overall verdict matrix

The final confirmatory result is exactly one of:

### `PROSPECTIVE_PASS`

Required:

- experiment is operationally valid;
- Execution is not `EXECUTION_BROKEN`;
- Alpha is `ALPHA_CONFIRMED_POSITIVE`;
- Economics is `ECONOMIC_POSITIVE`.

### `PROSPECTIVE_MIXED`

Used when the experiment is valid and does not satisfy PASS, but evidence is genuinely split rather than jointly negative. This includes, for example:

- `ALPHA_DIRECTIONALLY_POSITIVE` with `ECONOMIC_POSITIVE`;
- `ALPHA_CONFIRMED_POSITIVE` with `ECONOMIC_MIXED` or `ECONOMIC_FAIL`;
- `ALPHA_FAIL` with `ECONOMIC_POSITIVE`;
- alpha positive/directional with benchmark underperformance or material execution drag.

The component verdicts must be shown so `MIXED` cannot hide which layer failed.

### `PROSPECTIVE_FAIL`

Used when the experiment is valid and:

- `ALPHA_FAIL`; and
- economics is `ECONOMIC_FAIL` or `ECONOMIC_MIXED`.

A valid economic loss does not get relabeled as operational invalidity merely because it is disappointing.

### `PROSPECTIVE_INVALID_OPERATIONAL`

Used only for the invalidity conditions in Section 11.3, including unrecoverable state/provenance failure or prospective-outcome contamination. It is not a rescue label for weak performance.

No secondary metric, benchmark, robustness slice, or post-hoc analysis may upgrade the preregistered overall verdict.

## 15. Reporting table required at final evaluation

The final report must contain at least these fields:

### Identity and validity

- model name/generation/fingerprint;
- exact 100 session dates/indices;
- protocol commit and file identity;
- evaluator commit;
- outcome-access marker/time;
- alpha evaluable session count;
- PaperState continuity status;
- exclusions and reasons.

### Alpha

- mean/median/std session IC;
- IC 95% block-bootstrap CI;
- ICIR and positive-session rate;
- fixed rank-bucket outcomes;
- fixed first-50/last-50 alpha diagnostics.

### Economics

- starting and ending NAV;
- NetTotalReturn;
- AnnualizedVol;
- Sharpe_0;
- Sortino_0;
- MaxDrawdown;
- annualized geometric return/CAGR-equivalent;
- Calmar;
- IHSG return and net excess where available.

### Decision/execution

- entries/exits;
- turnover;
- holding duration;
- holdings/concentration summary;
- pending rate/duration;
- unavailable Official Open frequency;
- intended versus executed notional;
- capacity truncation;
- cash utilization;
- fees/slippage/stamp;
- dividend contribution.

### Verdicts

- Alpha verdict;
- Economic verdict;
- Execution verdict;
- Benchmark status;
- Overall prospective verdict.

## 16. Anti-metric-shopping rules

After protected outcome access begins, the following are forbidden as confirmatory changes:

- selecting a different outcome horizon/target;
- changing the 100-session block;
- dropping poor sessions outside frozen admissibility rules;
- changing the IC aggregation from mean to a more favorable statistic;
- changing bootstrap block length/seed/replicate count to improve significance;
- changing annualization from 252;
- introducing a favorable risk-free series into PRIMARY Sharpe;
- changing rank bucket boundaries;
- changing first-50/last-50 boundaries;
- adding hand-selected regimes/sectors;
- changing benchmark because the preregistered benchmark was harder to beat;
- changing PASS/MIXED/FAIL thresholds;
- using secondary metrics to rescue a failed primary verdict.

Post-confirmatory exploratory work is allowed only if explicitly labeled exploratory and may not rewrite the preregistered result.

## 17. Amendment policy before outcome access

A protocol amendment is permitted before protected outcome access only for:

- a demonstrated ambiguity or impossible-to-compute field;
- an implementation defect;
- a source/provenance contract change that is independent of outcomes;
- a clarification required to make the evaluator deterministic.

Every amendment must record:

- old commit/file identity;
- new commit/file identity;
- exact reason;
- whether protected prospective outcomes had been accessed (`FALSE` required for confirmatory amendment);
- whether the amendment changes any metric, denominator, target, benchmark, statistical method, or verdict rule.

Once protected outcome access begins, this confirmatory protocol is immutable. Any later methodological change is exploratory only.

## 18. Evaluator implementation requirement

The metric engine should be implemented and tested before final outcome access, but implementation is a separate task from this protocol freeze.

It should use only synthetic fixtures or already-authorized non-prospective fixtures during development. It must not contain an automatic vault-unlock shortcut and must fail closed on ambiguous canonical target, session alignment, missing hashes, or invalid PaperState continuity.

At minimum its tests should independently cover:

- Spearman IC;
- NAV daily returns;
- total return;
- annualized volatility;
- Sharpe;
- Sortino;
- MaxDrawdown;
- turnover;
- pending denominator;
- benchmark alignment;
- exclusion ledger behavior;
- deterministic 5-session moving-block bootstrap with seed `20260824`.

## 19. Freeze declaration

At the commit containing this file:

- `PROSPECTIVE_OUTCOMES_ACCESSED = FALSE`;
- `MODEL_RETUNED = FALSE`;
- `DECISION_CHANGED = FALSE`;
- `SIZING_CHANGED = FALSE`;
- `EXECUTION_CHANGED = FALSE`.

Controlling protocol verdict:

`V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1_FROZEN_OUTCOME_BLIND`

The next scientific implementation task is to build/test the deterministic evaluator against synthetic/non-prospective fixtures without accessing protected forward outcomes.
