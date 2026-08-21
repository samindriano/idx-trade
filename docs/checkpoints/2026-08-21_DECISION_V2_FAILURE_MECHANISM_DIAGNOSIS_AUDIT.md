# Decision V2 — Failure-Mechanism Diagnosis Runner Audit

Date: 2026-08-21 Asia/Jakarta

Status: `DIAGNOSIS_RUNNER_AUDIT_ACCEPTED_SINGLE_LOCAL_EXECUTION_AUTHORIZED`

Audited implementation HEAD: `f34e39954c3a67e05173be936b1878f2ec882045`

## Verdict

The diagnosis runner is accepted for exactly one local outcome-blind execution.

Audit findings:

- consumes the already-created frozen Decision V2 structural result; it does not call or rerun the Decision V2 planner/replay;
- pins structural result manifest SHA `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba` and plan digest `51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4`;
- revalidates every required structural artifact against the artifact SHA map in the frozen manifest;
- consumes the same pinned 600-session / 172,697-row alpha score source using the guarded projected score loader;
- preregistration is canonical-JSON SHA pinned at `72b2bfe43c37f5a1a5fd1c8ad5f91e3cf8c2e7393371b9a11e12dcbd287b64da` before source access;
- fixed rank bins are descriptive strata only and no alternative Decision rule is simulated;
- rejected fresh Top-10 next-session persistence is measured only from alpha ranks, never realized returns;
- terminal index 599 is excluded only from next-session rate denominators; ticker absence on a real next session remains a valid non-persistence observation;
- residual churn attribution uses only the frozen intent reasons and sequencing already emitted by the structural replay;
- output creation is fail-closed and non-overwriting;
- no returns, PnL, target outcome ledger, protected/fresh forward outcomes, provider/network calls, model refit/retune, parameter sweep, alternative threshold test, or Decision replay rerun are authorized.

Full repository CI on the audited implementation: `454 passed, 26 warnings, 0 failed`.

## Authorized local token

`DECISION_V2_FAILURE_MECHANISM_DIAGNOSIS_REVIEW_ACCEPTED_V1`

Authorization is for one local diagnosis execution only. The result must be frozen before any successor Decision policy is designed or simulated.
