# PIT-Safe V2/V3-B/O2 Historical Replay Runtime

Date: 2026-08-13 (Asia/Jakarta)  
Branch: `codex/pit-safe-v2-v3b-o2-reproduction-research-v1`  
Runtime root: `D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_historical_replay_v1_20260813_001`

## Decision

The fresh historical replay completed on the corrected PIT-safe reconstruction
lineage. The result is **not** a canonical release or prospective validation:

- V2 historical champion: `HGB_XS_MARKET`;
- V3-B Structure-Lite: `V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`;
- O2 geometry: `O2_SURVIVOR` under its frozen historical-development rule.

The V3-B failure is a new result on corrected inputs, not a reinterpretation
of the old contaminated result. The old V2/V3-B/O2 models and metrics remain
`LEGACY_CONTAMINATED_REFERENCE` and were not overwritten. The corrected input
lineage remains `PIT-SAFE-RECONSTRUCTION-V1`; no new executable model lineage
or forward counter is created by this checkpoint.

## Boundary and preflight

The exact fast-H10 artifact was verified against the full-panel equivalence
report as `FULL_PANEL_LEGACY_FAST_EQUIVALENT` with `legacy_fast_equal=true`.
H10 remains `TP_FIRST=1` and `SL_FIRST=0`. The replay used the unchanged six
expanding folds with a 20-session purge and 100-session validation window, and
historical development knowledge ends at 2026-07-31.

Corrected populations:

| stage | rows | tickers | key SHA-256 |
|---|---:|---:|---|
| V2 prepared table | 292,631 | 737 | `79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826` |
| V3-B table | 292,631 | 737 | same V2 identities |
| O2 common support | 278,166 | 729 | `77dbe5aaa32fa7e35779f273bc09501140e1a1363861aa262567f59354dd0644` |

The two removed KOCI-derived model identities are a consequence of the
generic PIT-safe listing-domain repair; no ticker-specific exception was
added. No provider call, protected fresh-forward outcome, canonical-model
overwrite, or execution-grade promotion occurred.

## V2 replay

Exactly the frozen control and four candidates were fit on the corrected V2
population. The champion gate summary is:

| candidate | median PR delta | q25 PR delta | positive PR folds | median ROC-AUC | ROC > .50 folds | median Q5-Q1 | eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| `V1_HGB_CONTROL` | 0.02310942 | 0.01766978 | 6/6 | 0.51829043 | 5/6 | 0.03002639 | no |
| `LOGISTIC_XS` | 0.00931842 | 0.00507168 | 6/6 | 0.50613126 | 5/6 | 0.01925865 | yes |
| `HGB_XS` | 0.01829351 | 0.01582069 | 6/6 | 0.51539832 | 6/6 | 0.04153618 | yes |
| `HGB_XS_MARKET` | 0.02419450 | 0.01265903 | 6/6 | 0.52517063 | 5/6 | 0.05308354 | yes |
| `PAIRWISE_LOGISTIC_XS` | 0.01071192 | 0.00922985 | 6/6 | 0.50832195 | 6/6 | 0.02475658 | yes |

The frozen selection rule selected `HGB_XS_MARKET`.

## V3-B replay

The 33-feature V3-B control and exact Structure-Lite candidate used identical
corrected rows, folds, labels, evaluator, HGB parameters, and feature order.
The paired challenger-minus-control changes were:

| fold | PR-AUC change | ROC-AUC change | Q5-Q1 change |
|---|---:|---:|---:|
| V2F1 | +0.00790704 | +0.00259663 | +0.01396779 |
| V2F2 | +0.00272251 | +0.00330468 | +0.01930785 |
| V2F3 | -0.00116421 | -0.00105720 | -0.00860860 |
| V2F4 | +0.01454598 | +0.01342507 | +0.02505553 |
| V2F5 | -0.01309503 | -0.00753950 | -0.01727346 |
| V2F6 | +0.01692841 | +0.01639913 | -0.00396765 |

The absolute V3-B late gate passed, but the paired gate failed because the
late fold comparison was not non-inferior: V2F5 had negative PR-AUC and Q5-Q1
changes, and the exact paired rule requires non-negative late changes. Result:
`V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`.

## O2 replay

The O2 baseline and full three-feature geometry challenger used the corrected
278,166-row common-support table. O2 paired PR-AUC changes by fold were:

| fold | O2 PR-AUC change |
|---|---:|
| V2F1 | +0.00382139 |
| V2F2 | +0.00082592 |
| V2F3 | +0.00104233 |
| V2F4 | -0.00059971 |
| V2F5 | +0.00157412 |
| V2F6 | +0.01101882 |

The frozen O2 rule produced median `+0.00130823`, q25 `+0.00088002`,
positive folds `5/6`, and no aggregate ROC/Q5 guardrail reversal. Result:
`O2_SURVIVOR` for historical development only.

## Validation and artifacts

- focused replay tests: `4 passed`;
- full pytest after implementation: `494 passed, 0 failed`; the normal run
  emitted four pre-existing warnings, and the warning-suppressed rerun also
  exited 0;
- model-fitting runtime: V2 `63.06s`, V3-B `46.19s`, O2 `50.11s`;
- external artifact count: `72`;
- artifact manifest internal verification: `72/72` hashes match;
- artifact manifest SHA-256:
  `9ed7079a510e2e5e070211e69ab9f811fb9ced51e72230e53e28de20d63b874f`;
- preflight contract SHA-256:
  `04bd94715560c8a41f4b06f2c5906e8d35d2f1157ffb44fcb4e4984d3caf64aa`;
- replay summary SHA-256:
  `d5c805f79e62c2d4edf26b156408ed9e30df2646fafac7109d8aa3b1c028c5e0`;
- V2 fold metrics SHA-256:
  `43ecd629c77ca5b55e0e1658938fab3ae312cdc57272b99d9873c61613802cbd`;
- V3-B paired metrics SHA-256:
  `568dca335c1109f3bd663cbaa0f495fe8aac73f776a9f193b7fddb485e164d9e`;
- O2 fold metrics SHA-256:
  `452a182a33b3e6a90dee64e479ba69cfcb08557b47ba6ba19b43a864976575d2`.

All runtime files remain outside Git. The repository contains only the runner,
tests, frozen contract, this factual checkpoint, and the handoff.

## Stop condition

Stop for independent ChatGPT review. Do not overwrite canonical V2/V3-B/O2,
start a new forward counter, access protected outcomes, tune/rescue V3-B,
start a new model family, run IDX-VAL-002, or merge to `main`.
