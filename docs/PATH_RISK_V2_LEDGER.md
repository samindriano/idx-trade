# Path Risk V2 Candidate Ledger

Date: 2026-08-11 (Asia/Jakarta)

Status: **V2 CLOSED — `PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`**

Path Risk is separate from the alpha-ranking candidate ledger. The permanent
alpha evaluated-candidate denominator remains `17`.

V1 remains closed and is not rescued by V2.

| Ordinal | Hypothesis | Candidate | Definition | Development folds | Result viewed | Verdict |
|---|---|---|---|---|---|---|
| PR-001 | `PATH-RISK-A-ADVERSE-EXCURSION-Q75-V1` | `PATH-RISK-A-Q75-HGB-001` | exact 33 features -> HGB q75 adverse-excursion regression | F1-F4 | `true` | `PATH_RISK_A_DISCOVERY_FAIL_CLOSE` |
| PR-002 | `PATH-RISK-V2-STOP-TOUCH-H10-V1` | `PATH-RISK-V2-STOP-H10-HGB-002` | exact 33 features -> direct H10 stop-touch HGB probability | F1-F4 | `true` | `PATH_RISK_V2_DISCOVERY_FAIL_CLOSE` |
| PR-003 | `PATH-RISK-V2-DISCRETE-COMPETING-RISK-V1` | `PATH-RISK-V2-DISCRETE-CR-HGB-003` | exact 33 features + deterministic H1..H10 step -> multiclass CONTINUE/STOP/TP HGB hazards -> H10 stop CIF | F1-F4 | `true` | `PATH_RISK_V2_DISCOVERY_FAIL_CLOSE` |

Comparators are not candidate ordinals:

- `TRAIN_STOP_TOUCH_BASE_RATE`;
- `FOLD_V3_B_ALPHA_ONLY_LOGIT`.

## 2026-08-11 parallel hardening result

The Orchestra HEAVY pre-outcome hardening task used five isolated Luna xhigh
workers and completed with:

- focused hardening suite: `89 passed`;
- full repository suite: `470 passed, 0 failed, 3 warnings, 34.73s`;
- result: `PATH_RISK_V2_PARALLEL_HARDENING_PASS_READY_FOR_LOCAL_DISCOVERY`.

The hardening exposed and fixed a runner schema-validation defect without
changing frozen V2 research semantics.

## 2026-08-11 discovery result

The one authorized PR-002/PR-003 F1-F4 development execution completed on code
HEAD `9378943bde44b33e311bec1e1daf38ca5cd9b5d3` after a full preflight of
`471 passed, 0 failed, 3 warnings`.

Frozen result:

`PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`

Winner: none.

Both candidates showed positive discrimination/risk-ordering diagnostics:

- ROC-AUC above 0.5 on all folds;
- Q5-Q1 stop-touch spread positive on all folds;
- both beat the fold-specific V3-B alpha-only -> stop-risk mapping on log loss
  across all folds.

However, both failed the decision-critical proper-scoring gate versus the
training base-rate comparator:

- PR-002 nonnegative log-loss improvement vs base: `0/4` folds;
- PR-003 nonnegative log-loss improvement vs base: `0/4` folds;
- PR-002 nonnegative Brier improvement vs base: `1/4` folds;
- PR-003 nonnegative Brier improvement vs base: `0/4` folds.

Therefore the useful ordering signal cannot be promoted or reinterpreted as a
validated probability/risk layer under V2.

Controlling checkpoint:

`docs/checkpoints/2026-08-11_PATH_RISK_V2_DISCOVERY_RESULT_FAIL_CLOSE.md`

Artifact hashes recorded there include:

- candidate metrics:
  `c9e5ea87f66252461bebff2bcbfe91d044618166142b6e9e5de48290ffc22f3c`;
- comparator metrics:
  `c99c89e65710c9aaa2fb95eab57d134885b8054d68f13445b1cae44f4bf06da6`;
- predictions:
  `2fa1204698c207920b6c439eebc5e6123d3b24497c6432e2ba3a23db1b16a7b3`;
- summary:
  `67689476b1cad17b0f39144bcce82e01a00c3f62e30a991ce2c381c5f7b0f332`.

## Frozen V2 selection consequence

The predeclared selection rule was:

- no survivor -> `PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`;
- one survivor -> select it;
- both survive -> larger median relative log-loss improvement vs alpha-only;
- difference `<=0.002` -> simpler PR-002 wins.

Because neither candidate survived the base-rate proper-scoring gate, the
selection logic terminates at `no survivor`. F5/F6 are not needed and remain
sealed.

## Permanent boundaries

- PR-001 remains viewed / FAIL_CLOSE;
- PR-002 and PR-003 are now permanently viewed / FAIL_CLOSE;
- no PR-004 rescue is pre-authorized;
- no alpha reranking/filtering/sizing/integration rule is authorized;
- no Path Risk F5/F6 access is authorized after this V2 result;
- fresh-forward outcomes and `FORWARD_OUTCOME_ACCESS_STARTED` remain untouched;
- any future Path Risk V3 would require a genuinely new preregistered hypothesis
  family and explicit authorization, not a post-hoc repair of V1/V2.
