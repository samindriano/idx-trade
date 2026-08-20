# V4-X1 Clean Prospective — One-Shot Self-Elevating Deployment Wrapper

Date: 2026-08-20 (Asia/Jakarta)  
Branch: `integration/v4-x1-clean-prospective-score-v1`

## Decision

`V4_X1_CLEAN_PROSPECTIVE_ONE_SHOT_SELF_ELEVATING_DEPLOY_AUTHORIZED`

The prior privilege retry stopped before any updater invocation because the calling PowerShell process was not Administrator. To remove further manual privilege choreography, a bounded operational wrapper has been added:

`scripts/deploy_v4_x1_clean_prospective_one_shot_v2.ps1`

Git blob:

`ba9b28e8af9e8e1662b8e712f64a93350c58ec6b`

This wrapper does not change scorer, model, feature, target, session, universe, CA80, or forward-evaluation semantics.

## Behavior

When launched from a normal PowerShell process, the wrapper:

1. requests Windows UAC elevation itself using `Start-Process ... -Verb RunAs`;
2. only the elevated child continues;
3. verifies the frozen deployment/updater/pipeline/readiness/scorer blobs;
4. resolves the accepted clean panel and clean security master by exact SHA-256;
5. verifies the accepted clean model manifest SHA-256;
6. verifies `IDXTrade-ForwardEOD` is still `Ready` and still points to the old V4-X1 model root;
7. runs the clean readiness audit read-only and requires counter `0/100`;
8. exports pre-task XML evidence;
9. invokes the already frozen updater exactly once;
10. verifies task state/action/triggers/LastRunTime read-only;
11. exports post-task XML evidence;
12. reruns readiness read-only and requires counter still `0/100`;
13. writes `deployment_summary.json` and returns the summary to the original non-elevated console.

The wrapper does not manually start the scheduled task, does not run the EOD pipeline, does not score a session, does not mutate the forward registry directly, and does not access outcomes.

## Frozen scientific/operational parents

- deployment contract blob `7919b21f3bf5451cc68687ee2fc2cf25b341fca2`;
- privilege retry contract blob `bf9ca2bdc9a1c7f7ab60a1fa3984f3f508c6196a`;
- updater blob `7b06fa4914c090a5aa76f767347de71bd9dd95a1`;
- clean pipeline PowerShell blob `5b3c3939ae87ce666bb9b1cd02ae4689d743122d`;
- readiness runner blob `07c38a0e27a0acfb7f5af49a7ea9b8b8fb822e1d`;
- clean scorer blob `f00528422a42835e5a969bfe503e29f91e0bf957`;
- accepted model manifest SHA-256 `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`;
- accepted clean panel SHA-256 `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`;
- accepted clean security master SHA-256 `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`;
- clean prospective freeze boundary `2026-08-20T12:08:44+00:00`.

## User interaction boundary

Only two unavoidable local actions remain:

1. update the local checkout so this wrapper exists;
2. approve the Windows UAC prompt.

No Codex agent is required for this deployment attempt.

## Next

`RUN_ONE_SHOT_WRAPPER_ONCE; APPROVE_UAC; RETURN_DEPLOYMENT_SUMMARY_FOR_INDEPENDENT_ACCEPTANCE`
