# Ranking V4-3R CA80 — immutable historical postmortem

Date: 2026-08-19 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-3r-ca80-prereg-v1`
Generation: `V4_3R_CA80`
Frozen verdict: `V4_3R_GENERATION_NO_SURVIVOR`

## Scope

This is a read-only interpretation of the already-consumed V4-3R historical one-shot result. It does not change the verdict, gates, model, data, targets, folds, or any scientific contract.

External result root:
`D:\Documents\Project\idx-v4-3r-historical-one-shot-20260819-v1`

Result manifest SHA-256:
`05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef`

## Execution validity

The one-shot completed exactly 24 preregistered fits. H5/H10/consensus target-support parity mismatches were all zero. Historical target loading, model fitting, prediction generation, and performance computation completed. Protected-forward outcomes were not accessed and provider calls were zero.

The Windows `wmic` / `cp1252` joblib warnings were non-fatal runtime noise and do not affect the scientific result.

## Main finding: rank signal was strong, portfolio-metric admissibility failed

The frozen verdict is `NO_SURVIVOR`, but the failure is not because the rank IC was weak.

### Control

Consensus:
- median fold mean daily IC: `0.08415844149089491` vs frozen minimum `0.025` — PASS
- q25 fold mean daily IC: `0.0642562654582539` vs minimum `0.01` — PASS
- positive IC folds: `6/6` vs minimum `5` — PASS
- bootstrap 95% mean daily IC: `[0.07017554012052232, 0.118465515014911]`; lower bound > 0 — PASS

H5:
- median fold mean IC: `0.06307281127949277` vs minimum `0.015` — PASS
- q25: `0.043872084762329615` vs minimum `0.0` — PASS
- positive folds: `6/6` vs minimum `4` — PASS

H10:
- median fold mean IC: `0.07818608378224626` vs minimum `0.015` — PASS
- q25: `0.06171157305858683` vs minimum `0.0` — PASS
- positive folds: `6/6` vs minimum `4` — PASS

### Challenger Geometry3

Consensus:
- median fold mean daily IC: `0.09775243938276076`
- q25 fold mean daily IC: `0.07275787380618584`
- positive folds: `6/6`
- bootstrap 95% mean daily IC: `[0.07596040021990692, 0.12337528363943043]`

H5 median/q25 IC: `0.07891122009359626 / 0.05447715991397155`.
H10 median/q25 IC: `0.09095594288451861 / 0.06827553924752909`.

All IC-oriented absolute gates therefore passed for both Control and Challenger.

## Geometry3 incremental IC evidence

Challenger minus Control:
- consensus median fold mean IC delta: `+0.013593997891865855` vs minimum `+0.005` — PASS
- consensus q25 IC delta: `+0.008501608347931941` vs minimum `0.0` — PASS
- H5 median IC delta: `+0.01583840881410349` vs minimum `0.0` — PASS
- H5 q25 IC delta: `+0.010605075151641934` vs minimum `-0.005` — PASS
- H10 median IC delta: `+0.012769859102272352` vs minimum `0.0` — PASS
- H10 q25 IC delta: `+0.006563966188942262` vs minimum `-0.005` — PASS
- consensus bootstrap 95% IC-delta CI: `[0.0014116604765849416, 0.01005689409146089]`; lower bound > 0 — PASS
- consensus positive-fold IC-delta count gate — PASS

Therefore Geometry3 produced a robust positive rank-IC increment inside this historical sample.

This does not override the frozen `NO_SURVIVOR` decision because the promotion contract required all absolute and incremental gates, not IC gates alone.

## Exact blocker: Top30 / spread observability

The V4 evaluator fixes Top30 and Bottom30 identities before future target observability, performs no refill, requires at least `27/30` target-observable names for a Top30 metric, and requires at least `90/100` admitted dates per fold for each primary metric.

V4-3R changed only the date-level target-coverage threshold from `0.90` to `0.80`. It deliberately did not change the 27/30 extreme-basket observability rule or the 90 admitted metric dates/fold rule.

Under CA80, all 600 validation dates were admissible for IC, but Top30 and spread metrics were not sufficiently observable.

Challenger consensus Top30 admitted dates by fold:
`41, 22, 59, 80, 46, 71`.

Challenger consensus spread admitted dates by fold:
`29, 17, 35, 22, 20, 41`.

Control consensus Top30 admitted dates by fold:
`45, 19, 51, 81, 51, 76`.

Control consensus spread admitted dates by fold:
`36, 14, 29, 13, 27, 50`.

Every fold is below the frozen `90` admitted-date requirement. Consequently:
- valid Top30 folds = `0/6` for both models;
- valid spread folds = `0/6` for both models;
- Top30 percentile and Top30-minus-Bottom30 spread aggregates are null;
- `all_six_primary_metric_folds_valid = false`;
- Control absolute pass = false;
- Challenger absolute pass = false;
- Challenger incremental promotion pass = false.

## Interpretation of the CA80 adaptation

The CA80 adaptation successfully made date-level rank-IC evaluation feasible, but it did not make the stricter extreme-basket portfolio metrics feasible.

This is an important distinction:

- `V4_3R_GENERATION_NO_SURVIVOR` remains the only valid generation-level verdict.
- The result is not evidence that the Control or Geometry3 rank signal is absent.
- Geometry3 in fact improved IC robustly under every frozen IC-oriented incremental gate.
- The generation failed because the full preregistered decision rule required portfolio metrics that remained under-observed under the unchanged no-refill 27/30 + 90-dates-per-fold contract.

The 541/600 validation dates in the `[0.80, 0.90)` support bucket make this mismatch especially relevant: lowering only the date-level gate to CA80 left a substantially stricter 90% observability requirement at the fixed extreme-basket level.

## Scientific boundary / next-direction rule

Do not rescue V4-3R by lowering Top30 observability, lowering the 90 admitted-date rule, changing K, refilling extreme baskets, changing promotion thresholds, or rerunning the same generation. Those choices would now be post-outcome.

The original V4-3 remains separately failed and closed at its preregistered 90% CA support gate. V4-3R is also consumed and closed with `NO_SURVIVOR`.

If this line is revisited, it must be a separately preregistered new generation whose evaluation design is justified before any new outcome access. The defensible research takeaway to carry forward is narrow: completed-session Geometry3 showed positive incremental rank-IC evidence, while the CA80 historical corpus could not support the frozen Top30/Bottom30 promotion metrics at the required frequency.
