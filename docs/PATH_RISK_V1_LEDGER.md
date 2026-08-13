# Path Risk V1 Candidate Ledger

Date: 2026-08-10 (Asia/Jakarta)

Status: **V1 CLOSED — PR-001 VIEWED / FAIL_CLOSE**

Path Risk is a separate research lane from alpha ranking. It does not change the ranking evaluated-candidate denominator of `17`.

| Ordinal | Hypothesis | Candidate | Definition | Discovery folds | Result viewed | Verdict |
|---|---|---|---|---|---|---|
| PR-001 | `PATH-RISK-A-ADVERSE-EXCURSION-Q75-V1` | `PATH-RISK-A-Q75-HGB-001` | exact frozen V3-B 33 features -> HGB q75 adverse-excursion regression | F1-F4 | `true` | `PATH_RISK_A_DISCOVERY_FAIL_CLOSE` |

Comparator `TRAIN-Q75-CONSTANT-BASELINE` is not a candidate ordinal.

## Discovery result

- nonnegative relative pinball improvement: `3/4` folds;
- median relative pinball improvement: approximately `+0.00777`, below frozen `+0.02` gate;
- q25 relative pinball improvement: approximately `-0.00517`, below `0` gate;
- worst relative pinball improvement: `-0.033463`, below frozen `-0.01` floor;
- positive Spearman: `4/4` folds;
- median Spearman: above `+0.10` gate;
- positive Q5-Q1 realized adverse-excursion spread: `4/4` folds;
- median Q5-Q1 spread: above `+0.10 R` gate.

The proper-scoring promotion gate failed despite useful ordering diagnostics. The frozen experiment cannot be reinterpreted after the fact as a pure ordering model.

Controlling result checkpoint:

`docs/checkpoints/2026-08-10_PATH_RISK_V1_DISCOVERY_RESULT_FAIL_CLOSE.md`

## Permanent boundary

- PR-001 remains permanently viewed;
- no Path Risk F5/F6 confirmation;
- no q50/q90/q75 rescue;
- no alternate model family or feature pruning;
- no risk-veto or alpha+risk integration;
- final V3-B ranker unchanged;
- post-2026-07-31 fresh-forward outcome block remains untouched.
