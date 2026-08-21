# Decision V1 — Failure Modes and Modular Design Principles

Date: 2026-08-21 Asia/Jakarta

Status: `ARCHITECTURAL_LESSONS_RECORDED_NO_DECISION_V2_PREREGISTRATION_YET`

## Purpose

This checkpoint records what the outcome-blind Decision V1 diagnostics have taught us before any Decision V2 rule is preregistered.

The goal is not to make the Decision layer a bespoke compensator for one unstable alpha model. The goal is to keep the architecture modular:

```text
Alpha / Ranking
      ↓
Decision Policy
      ↓
Portfolio / Risk
      ↓
Sizing
      ↓
Execution
```

Each layer should solve its own problem and expose a stable contract to the next layer. A downstream layer should not be forced to reverse-engineer or repair an upstream layer's pathology.

No realized return/PnL, protected/fresh-forward outcome, model retune, or Decision V2 parameter sweep is authorized by this checkpoint.

---

# 1. What Decision V1 was intended to do

Decision V1 was meant to convert a noisy daily cross-sectional ranking into a materially stickier 10-name target portfolio while preserving high rank quality.

Frozen V1 mechanics:

- 10 target names;
- new entrants must be current Top-10;
- existing Top-10 holdings retained;
- rank >20 forces exit intent;
- rank 11-20 may be replaced if the best unheld Top-10 candidate is at least 5 ranks better;
- continuous state across the historical 600-OOS path;
- no fold resets;
- Decision outputs target/intents, not fills.

The implementation was correct. The failure was longitudinal behavior, not a coding bug.

---

# 2. Empirically observed Decision V1 failure modes

## F1 — V1 was too literal about current-day rank

The policy treated today's rank state as almost sufficient evidence for action.

Observed result:

- mean 4.48 replacements per 10-name portfolio per transition;
- median 4 replacements;
- 78.13% of transition days replaced at least 3 names;
- median completed holding spell = 1 session;
- only ~14.1% churn reduction versus naive exact daily Top-10.

Interpretation:

V1 did not create enough separation between "the model likes this name today" and "this name is sufficiently durable to deserve a portfolio seat."

## F2 — Fresh Top-10 spikes were treated like established signals

Temporal persistence diagnosis shows that not all current Top-10 observations are equally durable.

For all current Top-10 rows:

- next-session rank >20 rate = ~33.99%;
- next-session Top-10 survival = ~47.98%.

For names that were fresh Top-10 after being >20 or absent previously:

- next-session rank >20 rate = ~54.80%;
- next-session Top-10 survival = ~30.20%;
- any rank >20 within 3 sessions = ~83.01%.

By contrast, for names already Top-10 on the previous session:

- next-session rank >20 rate = ~20.67%;
- next-session Top-10 survival = ~61.93%.

For Top-10 runs of at least 3 sessions:

- next-session rank >20 rate = ~15.17%;
- next-session Top-10 survival = ~68.47%;
- next-session Top-20 survival = ~84.83%.

Interpretation:

A large fraction of V1 churn came from admitting one-day rank spikes without requiring any evidence that the signal had persisted.

## F3 — Mandatory exit/replacement created a churn feedback loop

The dominant V1 sell reason was `HARD_EXIT_RANK_GT20`:

- 1,978 of 2,686 completed sells (~73.64%).

Many mandatory-exit replacements were themselves short-lived:

- `MANDATORY_EXIT_REPLACEMENT` immediate hard-exit rate ≈ 48.43%;
- hard-exit within 3 sessions ≈ 67.99%.

Interpretation:

The policy could enter a mechanical loop:

```text
incumbent rank shock
→ mandatory exit
→ immediately fill vacancy from today's Top-10
→ replacement is often a fresh spike
→ replacement collapses
→ another mandatory exit
```

This is a policy amplification problem. The Decision layer converted rank volatility into transaction volatility.

## F4 — Entry quality was not distinguished from exit urgency

V1 effectively assumed that once a vacancy existed, the best current Top-10 name was a sufficiently good replacement.

But entry durability varied materially with prior-state evidence.

Interpretation:

"Need to remove an incumbent" and "have a qualified replacement" are separate questions. V1 coupled them too tightly.

A neutral Decision policy should be allowed to temporarily retain an incumbent or leave a transition unresolved rather than automatically chase an unconfirmed candidate, subject to separately defined safety constraints.

## F5 — H5/H10 disagreement mattered, but was not the primary root cause

H5 was less persistent than H10:

- raw H5 median consecutive-session correlation ≈ 0.7215;
- raw H10 ≈ 0.8186.

Entry durability was worse when only one head supported a name.

Examples from support-at-Top-10 classification:

- `BOTH_LE10`: immediate hard-exit ≈ 39.70%;
- `H10_ONLY_LE10`: ≈ 45.98%;
- `H5_ONLY_LE10`: ≈ 51.40%;
- `NEITHER_LE10`: ≈ 60.10%.

However head disagreement is not sufficient as the core explanation:

- among all hard exits, both heads were >20 in ~71.54%;
- among one-session hard exits, both heads were >20 in ~74.23%.

Interpretation:

Cross-head agreement can be useful secondary evidence, but a V4-X1-specific H10 veto should not become the foundational generic Decision mechanism.

## F6 — The rank-20 boundary itself was not the main problem

Hard exits were not mainly rank 19 → 21 jitter.

Among hard exits:

- previous consensus rank median ≈ 6;
- exit rank median ≈ 58;
- one-session rank jump median ≈ +52;
- exit-rank p25 ≈ 31.

Interpretation:

A modest widening from rank 20 to 25/30 would not address the root cause. The bigger issue is how the policy reacts to large one-session rank shocks and how it chooses replacements.

## F7 — Whipsaw was material, but blanket grace periods are too crude

After a hard exit:

- ~27.00% returned to rank <=20 next session;
- ~43.63% returned <=20 within 3 sessions;
- actual V1 re-buy within 5 sessions ≈ 31.70%.

Interpretation:

Some exits were temporary shocks, but most were not immediate reversals. Therefore a universal fixed grace period or minimum holding period would be an overly blunt repair.

## F8 — Strict persistence confirmation alone can create candidate-capacity shortages

Persistence clearly improves durability, but demanding it too strictly can leave fewer than 10 candidates.

Current Top-20 with Top-20 run >=2:

- mean available candidates ≈ 11.10;
- median 12;
- >=10 candidates on only ~67.67% of dates.

Current Top-20 with Top-20 run >=3:

- mean ≈ 7.68;
- >=10 candidates on only ~38.83% of dates.

Current Top-20, previous Top-20, and both heads <=20:

- mean ≈ 7.46;
- >=10 candidates on only ~36.67% of dates.

Interpretation:

Temporal confirmation is useful evidence, but it cannot simply become a hard universal admission gate for all 10 positions. A reusable Decision layer needs graded evidence and stateful fallback behavior rather than one rigid filter.

---

# 3. What is actually wrong with V1 in one sentence

Decision V1 was **too reactive to current-day rank, too willing to treat fresh spikes as portfolio-quality entrants, and too eager to immediately replace exits**, causing it to amplify rather than absorb the temporal instability of the alpha ranking.

The key failure is not merely "threshold 20 was too tight" and not merely "H5 was too noisy."

---

# 4. Modular design principle: do not make Decision a V4-X1 antidote

A future Decision V2 should not be designed as:

> "What special rules do we need to neutralize every quirk of V4-X1?"

It should instead answer a more reusable question:

> "Given a cross-sectional alpha stream with current scores/ranks and historical signal states, what generic evidence is sufficient to admit, retain, replace, or remove a name?"

The distinction matters because future alpha models may have different horizons, score scales, or stability profiles.

---

# 5. Recommended responsibility boundaries

## Alpha layer responsibility

Alpha should answer:

> "Which names are more attractive than others now?"

Alpha should own:

- predictive model fitting;
- raw scores/predictions;
- cross-sectional ranking or normalized alpha;
- model identity/fingerprint;
- optional multi-horizon outputs when scientifically justified.

Alpha should **not** be forced to optimize turnover merely to make the portfolio look stable.

A future alpha challenger may explicitly study temporal stability if stability itself is scientifically motivated, but that must be a separately named research objective rather than a hidden portfolio constraint added to the frozen alpha.

## Decision layer responsibility

Decision should answer:

> "Is the alpha evidence strong and durable enough to change target membership?"

A reusable Decision layer should primarily use model-agnostic evidence such as:

- current relative strength;
- recent persistence of strength;
- deterioration persistence;
- incumbent versus challenger state;
- candidate qualification before replacement;
- explicit emergency/universe-invalid conditions.

Model-specific metadata such as H5/H10 agreement may be optional secondary evidence, not a mandatory architectural dependency.

Decision should absorb ordinary signal noise, but it should not be required to rescue an alpha stream whose useful signal disappears once modest temporal confirmation is applied.

## Portfolio / Risk responsibility

Portfolio/Risk should answer:

> "Given target names, what non-predictive exposure constraints are required?"

It should not repair alpha instability or decide which prediction is more believable.

## Sizing responsibility

Sizing should answer:

> "How many shares/lots correspond to the accepted target names under capital and feasibility constraints?"

It should not smooth target membership by hiding Decision churn in tiny position sizes unless that is an explicit future sizing research design.

## Execution responsibility

Execution should answer:

> "Can the requested target transition be filled under realistic timing, liquidity, fees, and market mechanics?"

It must not become a de facto signal filter used to compensate for Decision instability.

---

# 6. Reusable Decision interface principle

The preferred long-run contract is conceptually:

```text
Alpha produces an immutable daily evidence stream
    current score/rank
    optional independent horizon scores
    model identity

Decision maintains its own state/history
    incumbent membership
    recent rank/score path
    persistence/deterioration evidence
    qualified replacement set

Decision emits
    target names
    BUY/HOLD/SELL intents
    reason codes

Portfolio/Sizing/Execution consume those outputs without reinterpreting alpha
```

Temporal persistence should generally be computed from the historical alpha stream by the Decision layer, rather than baked into the alpha model output merely for this policy.

This keeps the same Decision machinery usable with later alpha generations so long as they satisfy the common score/rank contract.

---

# 7. Neutrality goals for Decision V2

Before implementation, Decision V2 should be judged against these architectural goals:

1. **Model-agnostic core** — should work from a generic rank/score stream, not require V4-X1-specific internals.
2. **Stateful but minimal** — use enough history to distinguish fresh spikes from persistent evidence, without adding a large rule engine.
3. **Asymmetric entry/hold/exit** — a new challenger should need stronger evidence than an incumbent needs merely to remain held.
4. **Qualified replacement separation** — an exit condition should not automatically imply a qualified replacement exists.
5. **No forced 10-name freshness chase** — target-count mechanics must not require buying an unconfirmed spike solely to refill a vacancy.
6. **Graceful capacity fallback** — strict persistence filters must not make the policy unusable on dates with fewer than 10 qualified new candidates.
7. **No hidden alpha retune** — Decision must consume the frozen alpha stream as-is.
8. **No PnL-selected mechanics** — mechanical policy shape should be preregistered from structural evidence before any performance comparison.
9. **Explainable reason codes** — every membership change should state whether it came from confirmed deterioration, qualified replacement, invalid universe state, or another explicit mechanism.
10. **Reusable downstream contract** — Sizing/Execution/CA should not require redesign when Decision V2 replaces V1.

---

# 8. What this checkpoint does NOT decide

This checkpoint does not yet select:

- exact entry confirmation length;
- exact exit confirmation length;
- exact retention rank band;
- emergency exit rank;
- whether score magnitude should supplement rank;
- whether H5/H10 agreement should be used;
- whether candidate slots may remain temporarily unfilled;
- any Decision V2 numerical parameter;
- any alpha V4-X2 design.

Those belong to a separately preregistered Decision V2 design after this architectural lesson is accepted.

---

# 9. Current direction

The current evidence supports continuing with frozen V4-X1 as the alpha baseline and designing a **neutral, stateful Decision V2** whose core mechanism is temporal evidence rather than V4-X1-specific compensation.

A new alpha challenger should be opened only if a reasonably neutral Decision layer still requires extreme intervention to make the signal portfolio-usable, or if later predictive evidence shows that temporal stabilization destroys the useful alpha.

This preserves modularity:

```text
V4-X1 can remain a reusable alpha benchmark.
Decision V2 can remain a reusable rank-to-target policy.
Downstream portfolio/sizing/execution contracts remain reusable.
Future alpha challengers can plug into the same Decision interface.
```
