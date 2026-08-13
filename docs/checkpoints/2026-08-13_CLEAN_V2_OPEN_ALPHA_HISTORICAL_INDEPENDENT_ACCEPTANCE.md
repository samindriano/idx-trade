# Clean V2 Open Alpha — Independent Historical Acceptance

Date: 2026-08-13 (Asia/Jakarta)
Review branch: `review/idx-v2-open-alpha-historical-acceptance-v1`
Reviewed branch: `research/idx-v2-open-alpha-prereg-v1`
Reviewed HEAD: `d9e0cd8a75026a56f341e3aa51015c70ac5fdfad`
Reviewed run commit: `c05b990420aa2f826786bb8972c31f760a75a6a4`
Verdict: **CLEAN_V2_OPEN_ALPHA_HISTORICAL_ACCEPTED_RETAIN_CLEAN_V2**

## Independent review

The single authorized historical-development run is accepted as decision-valid.

The runner:

- hash-pins the accepted 277,244-row / 729-ticker common-support cache and exact clean-V2 label source;
- loads only the frozen three model identities: CONTROL 25 features, V2.1 28 features, V2.2 28 features;
- rejects any unfrozen/31-feature combined feature order;
- uses the six frozen V2 folds, identical fold row identities, exact HGB preprocessing/parameters, and exact H10 mapping;
- evaluates the preregistered paired survivor rule without tuning or post-hoc selection;
- writes a fresh immutable external artifact root and does not access providers, protected fresh-forward outcomes, canonical models, or counters.

The reported paired results are consistent with the per-fold PR-AUC values:

- V2.1 vs CONTROL: median delta `+0.00007359`, q25 `-0.00250461`, 3/6 positive folds -> FAIL;
- V2.2 vs CONTROL: median delta `+0.00029955`, q25 `-0.00240718`, 3/6 positive folds -> FAIL.

Both challengers fail the frozen q25 paired-improvement requirement. Therefore the deterministic historical-development decision is:

**`RETAIN_CLEAN_V2`**

No V2.1/V2.2 rescue, additional Open-derived challenger, V2.3, combined six-Open model, alternate gate, or post-outcome feature/hyperparameter search is authorized from this result.

## Interpretation

This result closes the bounded Open-alpha remediation experiment. It does not mean the Open signal is exactly zero: both challengers had slightly positive median paired PR-AUC deltas, but the lower-quartile fold behavior was negative, so the incremental signal was not robust enough under the preregistered gate.

The surviving clean historical alpha architecture remains V2 `HGB_XS_MARKET`. This acceptance is historical-development evidence only. It does not itself create a canonical fitted model identity, perform final refit, promote execution grade, or start/transfer any prospective counter.

The existing legacy O2 fresh-forward archive remains separate immutable diagnostic evidence and must not be reinterpreted as validation of clean V2 or transferred to a future clean-model counter.

## Validation notes

- focused historical tests reported `12 passed`;
- full pytest reported `51 passed, 1 pre-existing failure` in the untouched storage revision-conflict test;
- the final branch commit after the run changes only the handoff pin, so there is no post-result scientific code drift between `c05b990` and `d9e0cd8`.

## Boundary

The Clean V2 Open-alpha V2.1/V2.2 historical lane is **DONE**. Any future alpha family requires a new, separately motivated and preregistered research question; do not automatically continue feature mining from this consumed historical dataset.
