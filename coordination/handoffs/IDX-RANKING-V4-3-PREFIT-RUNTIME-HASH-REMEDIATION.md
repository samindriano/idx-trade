# Handoff — V4-3 prefit runtime hash remediation

Status: `READY_FOR_LOCAL_CAPTURE_RETRY`
Branch: `research/idx-ranking-v4-3-prefit-runtime-v1`

Root cause: frozen SHA pins were compared to raw Windows working-tree bytes. The preregistration config itself did not change from the original preregistration anchor.

Remediation: keep all frozen expected SHA-256 values unchanged, verify them against canonical `HEAD:<path>` bytes via `git show`, and record working-tree hashes separately. Clean worktree remains mandatory.

Before retry:

1. pull the branch;
2. read latest `origin/main:coordination/TEAM_STATUS.md`;
3. update only the existing V4-3 prefit row from BLOCKED to ACTIVE/REVIEW as appropriate;
4. run focused preregistration + prefit tests and compile/diff checks;
5. run only the environment capture into a fresh empty output directory;
6. promote only the small environment manifest/checkpoint metadata;
7. stop before target/model execution.

Do not change scientific config, package versions in response to outcomes, targets, folds, features, learner params, or promotion thresholds. No R5/R10, ranks, fit, predictions, performance, provider calls, or protected/fresh-forward outcomes.
