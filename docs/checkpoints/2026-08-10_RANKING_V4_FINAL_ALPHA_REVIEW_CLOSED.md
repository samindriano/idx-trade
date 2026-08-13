# Ranking V4 Final Alpha Review — CLOSED

Date: 2026-08-10 (Asia/Jakarta)
Status: **FINAL V4 ALPHA REVIEW COMPLETE — NO SURVIVOR**

## Decision

`RANKING_V4_FINAL_ALPHA_REVIEW_CLOSED_NO_SURVIVOR`

The authorized frozen V4-A, V4-B and V4-C historical-development experiments are accepted as valid. None of the V4 challengers clears the unchanged promotion gate. The V4 alpha-generation search is therefore closed on the already-consumed historical-development data.

Final active ranking architecture remains:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

This conclusion is ranking-only historical-development evidence. It is not a probability, execution/PnL, paper/live, or independent future-validation claim.

## Accepted results

### V4-A — Participation Quality / Price Impact

- ordinal `012` exact V3-B control: control equivalence PASS;
- ordinal `013` Impact/Absorption: FAIL;
- ordinal `014` Persistent Directional Participation: FAIL;
- survivors: `[]`.

V4-A remains closed without rescue.

### V4-B — Price-Path Quality

- ordinal `015` exact V3-B control: control equivalence PASS;
- ordinal `016` Path Coherence / Jump Concentration: FAIL;
- ordinal `017` Range Acceptance / Rejection: FAIL;
- survivors: `[]`.

Ordinal `016` is a clear robustness failure: paired PR improvement is nonnegative on only `3/6` folds, median paired PR improvement is `-0.000917642`, q25 is `-0.004035100`, worst is `-0.011422974`, and median Q5-Q1 change is negative.

Ordinal `017` has useful-looking aggregate diagnostics but still fails the frozen robustness contract. Median paired PR improvement is `+0.003591194`, median ROC change `+0.008314478`, median Q5-Q1 change `+0.021899858`, and Q5-Q1 is nonnegative on `6/6` folds. However PR improvement is nonnegative on only `4/6` folds, q25 PR is negative, worst PR is `-0.009717536`, and the preregistered late-fold protection fails because V2F6 PR change is `-0.009717536`. This is not eligible for rescue or threshold relaxation.

No B1+B2 integration exists.

### V4-C — Cross-Sectional Opportunity Context

- ordinal `018` exact V3-B control: control equivalence PASS;
- ordinal `019` four-feature opportunity-dispersion bundle: FAIL;
- survivors: `[]`.

Ordinal `019` is not an "almost pass" merely because median paired PR improvement (`+0.001470161`) is close to the frozen `+0.0015` threshold. It also fails multiple robustness gates: only `4/6` nonnegative PR folds, q25 PR `-0.005276296`, worst PR `-0.026579427`, median ROC change `-0.002178033`, median Q5-Q1 change `-0.003855059`, only `2/6` nonnegative Q5-Q1 folds, and the late-fold protection fails. V2F6 is materially adverse.

No B/C integration exists.

## Why V4 stops here

The frozen V4 arena described seven information families but explicitly treated them as a design shortlist, not seven automatic experiments. The intended executable budget was normally three main families plus at most one conditional wildcard only if its data gate became defensible.

The three main market-derived families have now been executed. Selecting a new market-derived family only after seeing all three failures would increase outcome-responsive researcher degrees of freedom and violate the purpose of the bounded V4 program.

The conditional data-dependent families also do not justify a wildcard now:

- Peer / Sector Relative remains blocked by missing defensible PIT IDX-IC history;
- Catalyst / Fundamental Context lacks a frozen PIT availability/provenance data gate;
- Flow / Ownership lacks a frozen complete PIT provenance/correction/versioning data gate.

Systematic-adjusted/idiosyncratic strength remains a useful future research idea, but it is not promoted into this already-viewed V4 generation after the fact.

Therefore no V4 rescue, fourth market-derived family, integration, feature pruning, alternate lookback, threshold change, or model change is authorized.

## Candidate accounting

- V3 evaluated architecture ordinals: `001..007`, `010..011` = `9` viewed;
- V3-D `008..009`: blocked/unviewed;
- V4-A `012..014`: viewed;
- V4-B `015..017`: viewed;
- V4-C `018..019`: viewed;
- cumulative historical evaluated-candidate count: `17`.

The denominator is permanent. Failed candidates remain part of the research record.

## Final ranker and next phase

The final historical-development ranker remains exact V3-B Structure-Lite: frozen V2 HGB_XS_MARKET information plus the exact eight causal Structure-Lite geometry features.

The next ranking task is **not another historical alpha search**. It is to freeze and implement a final V3-B refit plus outcome-blind fresh-forward runtime.

The final refit may use the exact already-consumed historical-development resolved-primary-H10 rows through signal session `1250` solely for one final training fit. Sessions `1225..1250` must not be scored, compared, or used for model/feature selection. Adding them to the final training fit after architecture closure is not a new validation experiment.

The independent forward verdict remains the first exact 100 consecutive H10-mature official signal sessions strictly after `2026-07-31`, under a separately frozen pre-outcome contract. No fresh outcome may be read until the full immutable block, provenance, pre-outcome manifest, and explicit MAIN/ChatGPT authorization exist.

## Protected boundary

At this review:

- session `1225+` was not materialized or scored by V4;
- post-2026-07-31 fresh-forward outcomes remain unaccessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
- no calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge is authorized.

After the final V3-B refit/runtime is frozen, orthogonal work may proceed in a separately named **Path-Risk / Adverse-Excursion** lane while the forward block matures. That lane must not retune the ranker or consume the reserved fresh-forward ranking outcomes.