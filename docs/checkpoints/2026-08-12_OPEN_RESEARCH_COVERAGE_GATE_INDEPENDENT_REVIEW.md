# Open Research Coverage Gate — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Reviewed branch: `data/idx-open-research-coverage-gate-v1`
Reviewed HEAD: `80e9a55466d7d020b11739cf152b64a8d926915b`
Decision: `OHLCV_ALPHA_RESEARCH_COMMON_SUPPORT_AUTHORIZED`

## Review conclusion

The runtime recommendation `CONDITIONAL_PASS_FOR_OHLCV_ALPHA_RESEARCH` is accepted.

The exact V3-B final-refit population is 292,633 rows / 737 tickers. Open is known on 280,044 rows (95.6980%), while the complete five-feature Open-derived set is available on exactly 278,168 rows (95.0569%). This exact 278,168-row set is the mandatory common-support population for the first HLCV-vs-OHLCV historical-development comparison.

The comparison must not use different row populations between baseline and challengers. Missing-Open rows must not be imputed, forward-filled, synthetically reconstructed, or silently dropped differently by candidate.

The lower historical coverage in 2021/2022 and concentration of missingness by ticker remain a real selection-bias threat. Therefore the first OHLCV experiment must report paired fold, year, and ticker diagnostics and must not generalize a common-support result to the unrestricted 292,633-row population without additional evidence.

Protected post-2026-07-31 fresh-forward outcomes remain completely off-limits. This authorization applies only to frozen historical-development data and does not reopen or retune canonical V3-B.

## First authorized modelling experiment

Create a new isolated research branch and run a small, preregistered Open-decomposition experiment.

Mandatory baseline:

- `V3B_COMMON_SUPPORT_BASELINE`: exact frozen V3-B Structure-Lite feature contract and HGB pipeline/parameters, retrained/evaluated only on the exact 278,168-row common-support population using the existing six chronological development folds and existing purge/gap semantics.

Authorized challengers only:

1. `O1A_OVERNIGHT`: baseline + `overnight_gap = Open_t / prior_close - 1`;
2. `O1B_INTRADAY`: baseline + `intraday_return = Close_t / Open_t - 1`;
3. `O1C_DECOMPOSITION`: baseline + both `overnight_gap` and `intraday_return`.

No Open-position, Open-to-High/Low, interaction, market-relative Open, ATR-normalized gap, or additional Open family is authorized in this first run. Those remain later hypotheses.

Before execution, the implementation must load and verify the exact canonical V3-B final feature order, model parameters, fold identities, target/label semantics, and relevant artifact hashes from frozen repository/external artifacts. Do not approximate or recreate V3-B from memory.

## Comparison protocol

All four models must use:

- identical 278,168 row identities;
- identical six chronological development folds;
- identical H10 target/label semantics;
- identical HGB hyperparameters/pipeline except feature count/order;
- identical evaluation code and metric semantics;
- no hyperparameter search or candidate-specific tuning.

Report at minimum, per fold and aggregate:

- PR-AUC and PR-AUC delta vs prevalence;
- paired PR-AUC delta challenger minus common-support baseline;
- ROC-AUC;
- Q5-Q1 under the frozen ranking semantics;
- top-decile lift where already supported by the frozen evaluator;
- training/prediction row counts and feature completeness;
- metrics by year or equivalent diagnostic showing whether 2021/2022 common-support selection drives the result.

A challenger is only a survivor for further Open research if its improvement is broad rather than a single-fold spike. At minimum, both median and lower-quartile paired PR-AUC improvement versus the common-support baseline must be positive and the challenger must not show a clear aggregate reversal in the existing ranking guardrail metrics. This run does not authorize replacing canonical V3-B or performing a final refit of a challenger.

## Prohibitions

Do not:

- touch or retrain canonical V3-B artifacts;
- access protected fresh-forward outcomes;
- change target/label definitions;
- change folds, gap/purge rules, universe rules, or common-support row identities after seeing metrics;
- search HGB hyperparameters;
- add more Open features after observing O1A/O1B/O1C results;
- use the original 292,633-row V3-B historical metrics as the primary baseline for candidate attribution;
- repair remaining Open rows during the modelling task;
- run Path Risk, probability, sizing, execution-PnL, paper/live, or broker integration.

Stop after the bounded O1 result and push a factual checkpoint for independent review.
