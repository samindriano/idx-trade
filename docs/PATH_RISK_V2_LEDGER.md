# Path Risk V2 Candidate Ledger

Date: 2026-08-11 (Asia/Jakarta)

Status: **V2 FROZEN / IMPLEMENTED + HARDENING PASS PRE-OUTCOME — PR-002/PR-003 RESERVED, UNVIEWED**

Path Risk is separate from the alpha-ranking candidate ledger.  The permanent
alpha evaluated-candidate denominator remains `17`.

V1 remains closed and is not rescued by V2.

| Ordinal | Hypothesis | Candidate | Definition | Development folds | Result viewed | Verdict |
|---|---|---|---|---|---|---|
| PR-001 | `PATH-RISK-A-ADVERSE-EXCURSION-Q75-V1` | `PATH-RISK-A-Q75-HGB-001` | exact 33 features -> HGB q75 adverse-excursion regression | F1-F4 | `true` | `PATH_RISK_A_DISCOVERY_FAIL_CLOSE` |
| PR-002 | `PATH-RISK-V2-STOP-TOUCH-H10-V1` | `PATH-RISK-V2-STOP-H10-HGB-002` | exact 33 features -> direct H10 stop-touch HGB probability | F1-F4 | `false` | `RESERVED_UNVIEWED` |
| PR-003 | `PATH-RISK-V2-DISCRETE-COMPETING-RISK-V1` | `PATH-RISK-V2-DISCRETE-CR-HGB-003` | exact 33 features + deterministic H1..H10 step -> multiclass CONTINUE/STOP/TP HGB hazards -> H10 stop CIF | F1-F4 | `false` | `RESERVED_UNVIEWED` |

Comparators are not candidate ordinals:

- `TRAIN_STOP_TOUCH_BASE_RATE`;
- `FOLD_V3_B_ALPHA_ONLY_LOGIT`.

## 2026-08-11 parallel hardening result

The Orchestra HEAVY pre-outcome hardening task used five isolated Luna xhigh
workers and completed with:

- focused hardening suite: `89 passed`;
- full repository suite: `470 passed, 0 failed, 3 warnings, 34.73s`;
- result: `PATH_RISK_V2_PARALLEL_HARDENING_PASS_READY_FOR_LOCAL_DISCOVERY`.

Worker scopes covered PR-002, PR-003, the alpha comparator, the discovery
runner, and gate selection. The runner worker exposed one real engineering
defect: `_read_v1_model_table` projected requested columns before checking the
physical Parquet schema, allowing extra or reordered source columns to pass.
MAIN fixed this with an exact physical column-name/order check using PyArrow;
the corrected focused suite passed. The frozen research contract was not
changed.

The next step is the separate authorized preflight followed by exactly one
F1-F4 evidence run. No PR-002/PR-003 outcome has been viewed in this
hardening milestone; F5/F6 and fresh-forward outcomes remain sealed.

## Frozen V2 selection

PR-002 and PR-003 are compared only on already-consumed Path Risk development
folds F1-F4 under `docs/PATH_RISK_V2_SPEC.md`.

- no survivor -> `PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`;
- one survivor -> select it;
- both survive -> larger median relative log-loss improvement vs alpha-only;
- difference `<=0.002` -> simpler PR-002 wins.

F5/F6 may not select between candidates.  They remain sealed until a separate
one-shot confirmation spec exists for exactly one selected winner.

## Permanent boundaries

- PR-001 remains viewed / FAIL_CLOSE;
- PR-002/003 may not be changed after their F1-F4 outcome is viewed;
- no PR-004 rescue is pre-authorized;
- no alpha reranking/filtering/sizing/integration rule is authorized;
- no Path Risk F5/F6 access is authorized by this ledger;
- fresh-forward outcomes and `FORWARD_OUTCOME_ACCESS_STARTED` remain untouched.
