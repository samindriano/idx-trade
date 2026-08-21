# Decision V3 Kill Diagnosis — Runner Audit

Date: 2026-08-21 Asia/Jakarta

Status: `DIAGNOSIS_RUNNER_AUDIT_ACCEPTED_SINGLE_LOCAL_EXECUTION_AUTHORIZED`

Audited implementation HEAD: `5f6b75d615f4e1326889c3868d79e20e8eca8923`

## Scope

Independent adversarial review of the preregistered Decision V3 kill-diagnosis runner. This audit does not execute the local diagnosis because the frozen structural and historical artifact roots live on the user's Windows machine.

## Contract alignment

PASS:

- prereg normalized SHA is pinned and checked before source loading;
- exact V2 structural manifest/artifact hashes and plan digest are verified through the frozen structural-ledger loader;
- exact historical manifest/score hashes, 600 sessions, 172,697 rows and naive Top-10 comparator are verified;
- authorized CLI uses `run_kill_diagnosis_safe` only;
- historical parquet projection reads only `ticker`, `date`, `fold`, `mode`, and `alpha_consensus`; H5/H10, returns, labels and extra columns remain unread;
- `rank_consensus` is reconstructed deterministically from alpha consensus plus ticker tie-break;
- no Decision V3 planner/engine is imported or called by the authorized execution path;
- no alternative Decision policy or threshold is simulated;
- global fresh-current-Top10 population is defined against frozen V2 start-of-session target membership;
- terminal index 599 is excluded only from next-session persistence denominators;
- ticker absence on an actual next frozen session counts as non-persistence;
- severe-collapse context is descriptive and does not execute exits/fills;
- severe-collapse candidate supply is measured from the same-session unheld current Top-10 pool;
- V2 high-churn context uses the already-frozen session replacement ledger;
- underfill decomposition is computed from **residual** current Top-10 supply after the frozen V2 end target is formed, preventing double-counting of core candidates already consumed by V2;
- exact 135 underfilled sessions and 307 frozen vacancy-days are fail-closed invariants;
- output and staging directories refuse overwrite;
- outputs are hashed into a manifest;
- no returns/PnL, protected/fresh-forward outcomes, providers/network, model refit/retune, H5/H10 Decision internals, or parameter sweep are accessed.

## Remediation found during audit

Two issues were corrected before authorization:

1. the first implementation path reused the V2 source loader, which projected H5/H10 columns even though they were not used; the authorized path now uses a consensus-only loader and never reads those columns;
2. the first underfill decomposition counted raw start-of-session core supply, which could double-count core challengers already used by frozen V2; the authorized path now measures residual supply after the frozen V2 target is formed.

Both fixes are methodological hardening only. No diagnostic result has been seen and no policy threshold/rule was changed.

## Tests

GitHub Actions on audited implementation HEAD:

- `462 passed`
- `26 warnings`
- `0 failed`

Focused tests cover prereg hash pinning, reporting bins, candidate supply classification, terminal next-session denominator semantics, consensus-only projection, output overwrite refusal, safe CLI routing, and residual underfill supply without double-counting.

## Authorized entrypoint

Exactly one local execution is authorized via:

`scripts/run_v4_x1_decision_v3_kill_diagnosis.py`

with authorization token:

`DECISION_V3_KILL_DIAGNOSIS_REVIEW_ACCEPTED_V1`

No other function/module entrypoint is scientifically authorized.

## Output interpretation boundary

The local run may only produce descriptive mechanism evidence. It does not ACCEPT/REJECT Decision V3 and does not authorize implementation of the current V3 preregistration automatically.

After the one local run, freeze the result and decide whether the graded-evidence prereg should be revised, retained, or killed.
