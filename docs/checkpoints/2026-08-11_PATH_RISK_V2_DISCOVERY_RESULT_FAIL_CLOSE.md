# Path Risk V2 F1-F4 Discovery Result — FAIL_CLOSE

Date: 2026-08-11 (Asia/Jakarta)
Status: **`PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`**

This checkpoint records the one authorized local F1-F4 development execution of
Path Risk V2 after the pre-outcome hardening pass.

## Runtime identity

- branch: `research/idx-ranking-v2-spec-v1`;
- code HEAD used by the local run:
  `9378943bde44b33e311bec1e1daf38ca5cd9b5d3`;
- working tree: clean / synced before execution;
- pytest preflight: `471 passed, 0 failed, 3 warnings, 24.92s`;
- discovery runner runtime: `175.10s`;
- V2 verdict: `PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`;
- selected winner: none.

The run stopped after F1-F4 result production as required. No F5/F6 or
fresh-forward outcome access occurred.

## Frozen input verification

- V1 joined model-table SHA-256:
  `b66fc7e40f18940ae9db418331a421e0f36d23b86597500b1d3ba73a8e3777fe`;
- calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- V2 spec Git blob:
  `6d171d3f492b9cd15e0a176428eb9d6e4f6c20c5`;
- model-table rows: `252,198`;
- signal sessions: `20..984`;
- stop-touch prevalence: `0.52927065`.

Status composition:

- `SL_FIRST`: `132,307`;
- `TP_FIRST`: `84,165`;
- `NO_BARRIER_HIT`: `34,552`;
- `AMBIGUOUS_SAME_BAR`: `1,174`.

## Comparator summary

The training base-rate comparator remained difficult to beat on proper
probability scoring. The fold-specific V3-B alpha-only mapping showed weak
positive discrimination but materially worse calibration/proper scores than the
base-rate comparator.

Base-rate fold log loss:

- F1 `0.692298`;
- F2 `0.692133`;
- F3 `0.694065`;
- F4 `0.689670`.

Alpha-only fold log loss:

- F1 `0.757279`;
- F2 `0.730461`;
- F3 `0.736937`;
- F4 `0.783417`.

Alpha-only ROC-AUC was `0.530303 / 0.533081 / 0.535962 / 0.526270` on F1-F4.

## PR-002 — direct H10 stop-touch HGB

PR-002 produced useful ranking/discrimination diagnostics but failed the frozen
proper-scoring gate versus the training base-rate comparator.

| Fold | Log loss | Brier | Rel log-loss vs base | Rel Brier vs base | Rel log-loss vs alpha | ROC-AUC | PR-AUC | Q5-Q1 stop-touch | Spearman |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F1 | 0.701230 | 0.253100 | -0.012902 | -0.014124 | +0.074014 | 0.554165 | 0.562641 | +0.149123 | 0.101171 |
| F2 | 0.692679 | 0.249408 | -0.000789 | +0.000339 | +0.051723 | 0.561093 | 0.557949 | +0.138244 | 0.110978 |
| F3 | 0.700780 | 0.253602 | -0.009675 | -0.012553 | +0.049064 | 0.553159 | 0.548170 | +0.135429 | 0.114466 |
| F4 | 0.712742 | 0.258995 | -0.033453 | -0.043232 | +0.090215 | 0.553739 | 0.576542 | +0.126165 | 0.077217 |

All PR-002 predictions were finite. Unique prediction counts were
`27,049 / 24,464 / 24,544 / 23,111`.

## PR-003 — discrete competing-risk HGB

PR-003 also produced useful discrimination/risk ordering but failed the same
frozen proper-scoring gate versus base rate.

| Fold | Log loss | Brier | Rel log-loss vs base | Rel Brier vs base | Rel log-loss vs alpha | ROC-AUC | PR-AUC | Q5-Q1 stop-touch | Spearman |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F1 | 0.718303 | 0.258804 | -0.037564 | -0.036979 | +0.051468 | 0.560038 | 0.564181 | +0.153887 | 0.109501 |
| F2 | 0.693679 | 0.249591 | -0.002234 | -0.000394 | +0.050353 | 0.563105 | 0.560276 | +0.151402 | 0.110751 |
| F3 | 0.703627 | 0.254939 | -0.013777 | -0.017892 | +0.045201 | 0.549141 | 0.547047 | +0.140720 | 0.106532 |
| F4 | 0.714641 | 0.259729 | -0.036207 | -0.046187 | +0.087790 | 0.556452 | 0.577490 | +0.116439 | 0.083869 |

All PR-003 predictions were finite. Unique prediction counts were
`27,053 / 24,464 / 24,546 / 23,112`.

PR-003 probability-mass conservation was numerically clean: maximum reported
error was `8.88e-16`.

## Frozen gate decision

Both candidates passed:

- finite-metric checks;
- relative log-loss improvement versus alpha-only on all 4 folds;
- median improvement versus alpha-only;
- ROC gates;
- positive Q5-Q1 stop-touch spread on all 4 folds;
- median Q5-Q1 threshold.

Both candidates failed the decision-critical proper-scoring gates against the
training base-rate comparator:

- PR-002 nonnegative log-loss improvement vs base: `0/4` folds;
- PR-003 nonnegative log-loss improvement vs base: `0/4` folds;
- PR-002 nonnegative Brier improvement vs base: `1/4` folds;
- PR-003 nonnegative Brier improvement vs base: `0/4` folds;
- required median log-loss improvement versus base was not met by either.

Therefore neither candidate is eligible for promotion. The positive ranking
signals must not be reinterpreted as a V2 survivor after the frozen proper-score
gate failed.

Frozen verdict:

`PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`

Winner: `none`.

## Artifact identities

Local output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v2_discovery_run_20260811_002`

- candidate metrics SHA-256:
  `c9e5ea87f66252461bebff2bcbfe91d044618166142b6e9e5de48290ffc22f3c`;
- comparator metrics SHA-256:
  `c99c89e65710c9aaa2fb95eab57d134885b8054d68f13445b1cae44f4bf06da6`;
- predictions SHA-256:
  `2fa1204698c207920b6c439eebc5e6123d3b24497c6432e2ba3a23db1b16a7b3`;
- summary SHA-256:
  `67689476b1cad17b0f39144bcce82e01a00c3f62e30a991ce2c381c5f7b0f332`.

Per-fold model/comparator hashes remain recorded in the local frozen summary.

## Permanent interpretation and boundary

Path Risk V2 is closed at F1-F4 discovery. PR-002 and PR-003 are permanently
viewed development candidates and may not be silently rescued, recalibrated,
retuned, or reinterpreted as winners under a different primary objective.

This result does **not** authorize:

- Path Risk F5/F6 access;
- PR-004 or another immediate rescue candidate;
- post-hoc probability calibration;
- risk-veto / alpha reranking / position sizing / alpha+risk integration;
- execution-PnL, Kelly, paper, or live trading;
- post-2026-07-31 forward-outcome access.

Confirmed untouched by the run:

- session `985+` Path Risk outcomes;
- Path Risk F5/F6;
- post-2026-07-31 fresh-forward outcomes;
- `FORWARD_OUTCOME_ACCESS_STARTED`;
- frozen V3-B alpha ranker.
