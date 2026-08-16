# Ranking O2 Forensic Audit — Stage 3 Final Adjudication

Date: 2026-08-16 (Asia/Jakarta)  
Branch: `research/idx-ranking-v1-forensic-audit-v1`  
Starting HEAD: `9fc49b79728f519626c177e19b58b37e35f761f8`  
Status: `O2_FORENSIC_CLOSED_RETAIN_SESSION_GEOMETRY_AS_CONDITIONAL_CANDIDATE_BLOCK_NO_CLEAN_MODEL_PROMOTION`

## Scope

This checkpoint closes the forensic review of the historical O2 Open-geometry lineage. It is an adjudication only. No model was fit, no historical or protected-forward outcome was accessed, no provider call was made, no feature threshold was changed, no existing forward counter was read or modified, and no clean O2 successor was created.

The controlling forensic question is not whether the old O2 runtime was numerically positive. That is already known. The question is which O2 conclusions survive the corrected PIT-safe lineage and which claims must be withdrawn before designing a new generation.

## Frozen factual reconstruction

Historical O2 appended three same-session Open-geometry coordinates to the then-canonical 33-feature V3-B Structure-Lite baseline:

1. `open_position = (Open_t - Low_t) / (High_t - Low_t)`;
2. `open_to_high = High_t / Open_t - 1`;
3. `open_to_low = Low_t / Open_t - 1`.

The model remained the frozen HGB pipeline and retained the inherited resolved-only H10 `TP_FIRST` versus `SL_FIRST` target anchored to `Close_t`.

The original historical-development O2 run reported median paired PR-AUC uplift `+0.00727622`, lower-quartile uplift `+0.00470965`, and `6/6` positive folds versus the old V3-B baseline. The robustness audit reproduced the metrics and showed that the result did not disappear when TradingView rows or Yahoo split-scale reconstructed rows were excluded. The three geometry columns are algebraically redundant representations of one underlying same-session geometry, but the frozen HGB minimality study retained the full three-coordinate representation as the strongest historical-development version.

The corrected PIT-safe replay materially reduced the O2 incremental magnitude but did not eliminate it against the corrected V3-B baseline: median paired PR-AUC uplift `+0.00130823`, lower quartile `+0.00088002`, and `5/6` positive folds, with the frozen O2 historical rule still producing `O2_SURVIVOR`.

However, the same corrected replay rejected V3-B Structure-Lite as the clean successor to V2 under the frozen late paired gate. Therefore the full O2 lineage became an orphaned-parent diagnostic rather than a clean promoted model.

A separately preregistered direct-parent remediation then tested the exact O2 Open-geometry family on clean V2 common support. `V2.1_CLEAN_V2_OPEN_GEOMETRY` failed its frozen paired gate: median PR-AUC delta approximately `+0.00007359`, lower quartile `-0.00250461`, and only `3/6` positive folds. Clean V2 remained the surviving historical architecture.

## What O2 actually proved

### 1. Same-session Open geometry contains historical conditional information

The corrected PIT-safe O2 replay remained positive against the corrected V3-B baseline. Therefore the O2 result cannot be dismissed solely as the original KOCI/listing-lineage defect or a provider-only artifact.

This is historical-development evidence only. It does not establish prospective or executable alpha.

### 2. The useful Open representation was not simply overnight gap or Open-to-Close return

The earlier O1 experiment tested overnight gap, intraday Open-to-Close return, and their decomposition and failed its frozen survivor rule. O2 therefore supports a narrower lesson: the useful representation, where present, is closer to completed-session shape/location geometry than to a generic statement that `Open` or gap direction is predictive.

### 3. The three O2 columns do not represent three independent factors

They are algebraically linked. Their value is best interpreted as exposing one geometry through several coordinates that may simplify finite-tree partitioning. This is a representation effect, not evidence for three distinct sources of alpha.

### 4. Provider fingerprint is not the leading explanation

Historical robustness diagnostics retained positive uplift after removing TradingView and after removing Yahoo split-scale reconstructed rows. The corrected Open audit also enforced PIT/session/listing guards and no synthetic forward fill. Provider risk is not zero, but it is no longer the primary O2 concern.

## What O2 did not prove

### 1. O2 did not prove that Open geometry is a standalone additive alpha block

The clean V2 + exact Open-geometry test failed. Therefore the strongest current interpretation is conditional rather than additive.

### 2. O2 did not prove that the clean full 36-feature model beats clean V2

The old direct O2-versus-V2 common-support comparator was accepted as valid historical-development evidence for its historical lineage, but it predates the corrected clean lineage. It cannot substitute for a corrected clean-parent successor claim.

No new corrected full-O2-versus-clean-V2 experiment is authorized by this forensic checkpoint.

### 3. O2 did not prove a Structure-Lite × Open synergy mechanism

The observed evidence is consistent with several mechanisms:

- genuine complementary information between structural state and same-session geometry;
- Open geometry acting as a reliability/conditioning variable for noisy Structure-Lite signals;
- completed-candle representation becoming easier for HGB when both blocks are present;
- target/barrier mechanics being easier to classify when current-session range geometry is exposed.

Existing experiments do not isolate these alternatives on one identical corrected support using a frozen factorial design. Therefore `Structure × Open synergy` remains a hypothesis, not a finding.

### 4. O2 did not prove executable trading value

The signal is known only after session `t` closes, while the inherited research target is anchored to `Close_t`. A real post-close system cannot observe the completed `Open_t/High_t/Low_t/Close_t` geometry and then execute retrospectively at `Close_t`. The earliest defensible entry is a future executable state, typically session `t+1` Open or another explicitly modeled next-session execution event.

## Final adversarial adjudication

| concern | adjudication | consequence |
|---|---|---|
| resolved-only H10 TP/SL estimand | `CONFIRMED_ARCHITECTURAL_FLAW` | fatal to treating O2 as final product model; target population must be redesigned |
| after-close signal but `Close_t` target anchor | `CONFIRMED_ARCHITECTURAL_FLAW` | fatal to executable-alpha claim; future target must use an executable next-session reference |
| V3-B parent fails clean promotion | `CONFIRMED_LINEAGE_BREAK` | fatal to automatic O2 model promotion; O2 becomes orphaned-parent diagnostic |
| exact Open3 on clean V2 fails | `CONFIRMED_NON_STANDALONE_RESULT` | Open geometry cannot be promoted as a standalone additive block |
| full clean O2 versus clean V2 | `UNRESOLVED` | no superiority claim is allowed |
| Structure-Lite × Open interaction | `PLAUSIBLE_UNPROVEN_MECHANISM` | retain only as a future preregistered hypothesis, not a current conclusion |
| target/barrier-mechanics coupling | `REAL_RISK_UNPROVEN` | future target redesign should precede any attempt to interpret O2 economically |
| Open-ready common-support selection | `REAL_MANAGEABLE_RISK` | all future comparisons require exact common support and explicit missingness/exclusion diagnostics |
| three-column algebraic redundancy | `MANAGEABLE_REPRESENTATION_ISSUE` | retain geometry concept; do not treat three columns as three factors |
| provider fingerprint | `SUBSTANTIALLY_MITIGATED_NOT_ZERO` | provenance guards remain required but no rescue/provider hunt is justified |
| O1 gap/intraday alternatives | `CLOSED_NO_SURVIVOR` | do not recycle consumed O1 variants as supposedly new Open hypotheses |

## Fatality by claim type

### Fatal to O2 as a clean production/execution model

- inherited resolved-only target population;
- `Close_t` pseudo-entry after the signal is only known after close;
- rejected clean V3-B parent;
- no established corrected full-O2 superiority over clean V2.

### Fatal to the claim that Open geometry is independently additive

- exact Clean-V2 + Open3 remediation failed its frozen gate.

### Not fatal to O2 as scientific information

- corrected PIT-safe Open3 increment versus V3-B remained positive under the frozen O2 rule;
- provider-exclusion diagnostics did not erase the historical result;
- O1 and O2 differences indicate that session geometry is more specific than generic gap/intraday-return information;
- the conditional/interaction hypothesis remains legitimate for future preregistration.

## What should be retained for a future clean generation

Retain the following **concepts**, not automatic feature inheritance:

1. `completed-session geometry` as a candidate information family;
2. exact common-support Open provenance and fail-closed session/listing semantics;
3. same-parent paired evaluation for incremental feature blocks;
4. representation minimality awareness: algebraic redundancy can still affect finite-tree learnability;
5. explicit distinction between standalone feature value and conditional/contextual feature value.

Do **not** automatically retain:

- the old 36-feature O2 fitted model;
- old V3-B as parent;
- exact three O2 columns as mandatory features;
- old H10 resolved-only labels;
- `Close_t` as economic entry reference;
- the old direct O2-versus-V2 comparator as proof of clean superiority;
- any post-hoc Structure/Open combination test using the already-consumed development results.

## Required sequencing before any future O2-like model

The forensic conclusion is that target and evaluation architecture have higher priority than another Open-feature search.

A genuinely new generation should first preregister:

1. candidate population including explicit treatment of non-resolution/no-hit rather than conditioning them away by default;
2. executable information/entry clock, with next-session execution semantics where appropriate;
3. date-centric ranking evaluation and exact common-support comparison;
4. incumbent-eligible control governance so the parent can win;
5. only then a small, frozen feature-block matrix that may include completed-session geometry and structural context.

Any future Structure × Open interaction test must be designed prospectively as a bounded candidate family. The old development results must not be mined to tune thresholds, subsets, or interaction rules.

## Relationship to existing prospective O2 machinery

Existing legacy O2 forward-scoring / 100-session infrastructure is not invalidated operationally by this forensic checkpoint, and this checkpoint does not read or modify its protected outcome vault. However, because the historical clean parent changed, that legacy prospective lineage cannot by itself validate a new clean V2-based or redesigned-target generation.

## Final disposition

`O2_FORENSIC_CLOSED_RETAIN_SESSION_GEOMETRY_AS_CONDITIONAL_CANDIDATE_BLOCK_NO_CLEAN_MODEL_PROMOTION`

In plain language:

- keep O2 as evidence that completed-session Open geometry may matter conditionally;
- do not call Open geometry standalone alpha;
- do not call the old full O2 a clean champion;
- do not rescue O2 by rerunning combinations on the consumed historical development sample;
- redesign target/execution/evaluation first, then decide whether a tightly preregistered session-geometry block deserves a place in a new generation.

Stop here. The next forensic step, if requested, is a synthesis across V1 -> V2 -> V3 -> O2. No new model fit or outcome access is authorized by this checkpoint.
