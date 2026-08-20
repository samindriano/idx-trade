# Claim — V4-X1 Clean Prospective Score V1

Date: 2026-08-20 (Asia/Jakarta)
Status: `AUTOMATED_WAITING_FIRST_FRESH_SESSION`
Owner: `ChatGPT/V4-X1-Clean-Prospective-Score`
Branch: `integration/v4-x1-clean-prospective-score-v1`
Base operational lineage: `integration/v4-x1-eod-auto-score-v1`

## Current accepted state

The clean V4-X1 prospective deployment is complete and accepted.

Controlling deployment acceptance:

- checkpoint: `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_DEPLOYMENT_ACCEPTED_AUTOMATED.md`
- deployment execution HEAD: `80ee635a5e6e7f6d63f3749a5759a3de2651cab1`
- deployment status: `V4_X1_CLEAN_PROSPECTIVE_DEPLOYMENT_COMPLETE_VERIFY_ONLY`
- Windows task: `IDXTrade-ForwardEOD`
- post-deployment task state: `Ready`
- scheduler mutation: `true`
- manual task start: `false`
- manual pipeline run: `false`
- score capture during deployment: `false`
- outcome access: `false`
- LastRunTime unchanged during migration: `true`

Accepted model/data lineage remains:

- clean model manifest SHA-256 `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`;
- clean panel SHA-256 `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`;
- clean security master SHA-256 `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`;
- freeze boundary `2026-08-20T12:08:44Z` / `2026-08-20T19:08:44+07:00`.

Counter state immediately after deployment:

- `0/100`;
- readiness `V4_X1_CLEAN_FORWARD_READYNESS_WAITING_FIRST_POST_FREEZE_SESSION`.

## Ongoing operating boundary

The existing canonical EOD task is now the only clean V4-X1 prospective score path. No second capture system is authorized.

The lane is now automated. Do not manually run or backfill scores. The first counter-eligible observation must be determined by immutable runtime evidence and satisfy all frozen fresh-only / same-day / post-freeze rules.

The 2026-08-20 session is permanently ineligible for clean prospective credit.

Outcome vault remains locked until `100/100` score sessions plus H10 maturity for session 100.

V4-X2 session-aligned semantics remain a separate lane and must not be mixed into V4-X1.

## Next

`WAIT_FOR_FIRST_FRESH_AUTOMATED_SCORE; VERIFY/REVIEW ONLY IF THE AUTOMATION REPORTS A FAILURE OR WHEN FORWARD-MONITORING CHECKPOINTS ARE DUE.`

Canonical `main:coordination/TEAM_STATUS.md` was read before acceptance. Its deployment row still reflects the earlier Administrator-blocked attempt; because the connector read is truncated, this branch-local acceptance is authoritative scientifically until a safe minimal canonical ledger update is performed from a local checkout.
