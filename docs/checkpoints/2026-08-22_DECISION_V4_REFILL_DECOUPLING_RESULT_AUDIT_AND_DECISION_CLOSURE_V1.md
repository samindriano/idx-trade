# Decision V4 Refill Decoupling V1 — Result Audit and Decision Closure

Date: 2026-08-22 Asia/Jakarta

Verdict: `DECISION_V4_REFILL_DECOUPLING_V1_STRUCTURAL_REJECT_ACCEPTED_DECISION_RESEARCH_CLOSED`

## Reviewed execution identity

Frozen runner branch:

`research/idx-decision-v4-refill-decoupling-structural-runner-v1`

Frozen runner HEAD:

`6cc21a70ef4cc8096c296393e3b6404cf9efd9f0`

Independent runner-audit HEAD:

`6a23572bf26348c5bc85f38af135bb1eb9bda0f1`

Runner-audit authorization verdict:

`RUNNER_AUDIT_ACCEPTED_SINGLE_STRUCTURAL_REPLAY_AUTHORIZED`

The user-provided local execution report records exactly one execution with exit code 0, no rerun, and the frozen 600-session / 172,697-row source.

Recorded local artifact hashes:

- `MANIFEST.json` SHA-256: `f1b781d83352611e15e24dcaa2400cc555a020ed9dd38a90db316a4329619c43`
- `summary.json` SHA-256: `9f3dfb2749a3f6892d18278ff35c108c3567d8199cbeba3ca38cfcf2d9537f7d`

The local artifact bytes remain external to the Git repository. This checkpoint records their supplied hashes and independently audits the reported verdict against the immutable repository contract; it does not copy or mutate the runtime artifacts.

## Frozen structural verdict

Reported exact verdict:

`DECISION_V4_REFILL_DECOUPLING_V1_STRUCTURAL_REJECT`

The rejection is independently consistent with the frozen preregistration gates. At least the following reported values are individually sufficient to fail their frozen gate groups:

- mean replacements = `2.814691` versus frozen maximum `2.25` -> fail `B_churn`;
- median completed holding = `2.0` versus frozen minimum `3` -> fail `C_holding_persistence`;
- mean target size = `8.94` versus frozen minimum `9.0` -> fail `E_capacity`.

Reported one-session holding share = `0.265351`, which passes its `<=0.35` subcondition, but the holding gate group still fails because the median holding requirement fails.

Reported mean target rank = `9.300708`, which passes the frozen `<=12.0` rank-quality requirement.

Reported full-target Top-10 overlap = `7.769608`, which passes the frozen `>=6.0` rank-quality requirement.

The execution report states that integrity/correctness, rank-quality, and stale-state gate groups passed. The rejection therefore does not depend on any implementation-integrity failure; it is a substantive structural failure on churn, persistence, and capacity.

## V4 mechanism diagnostics

Reported preregistered descriptive diagnostics:

- severe-exit sessions: `342`;
- Tier-A vacancy fills on severe sessions: `713`;
- Tier-B blocked candidates on severe sessions: `294`;
- Tier-C blocked candidates on severe sessions: `341`;
- underfilled sessions after severity-conditioned refill: `192`;
- vacancy days after severity-conditioned refill: `636`.

These diagnostics remain descriptive only and do not alter the frozen verdict.

## Interpretation

The preregistered intervention did what it was designed to do mechanically: on severe-exit sessions it withheld lower-confidence B/C refill supply and allowed temporary underfill. However, on the frozen development path this was not enough to satisfy the unchanged churn and persistence requirements, while the withholding materially impaired capacity.

The result is therefore not a near-pass that authorizes threshold adjustment. It is exactly the falsification case anticipated in the preregistration: restricting B/C refill on severe sessions does not produce an acceptable structural portfolio policy under the frozen gates.

## Binding post-replay rule

The independently accepted runner audit froze the post-replay rule:

- structural REJECT -> Decision V4 rejected;
- Decision V2 remains incumbent;
- Decision-rule research closes;
- no rescue variant is authorized;
- no V4-vs-V2 economic comparison is authorized after structural rejection.

That rule is now binding.

## Final Decision-layer status

`DECISION_V2_REMAINS_INCUMBENT = true`

`DECISION_V4_REFILL_DECOUPLING_REJECTED = true`

`DECISION_RESEARCH_CLOSED = true`

`V4_VS_V2_ECONOMIC_COMPARISON_AUTHORIZED = false`

`V4_1_OR_V4_2_AUTHORIZED = false`

`THRESHOLD_RESCUE_AUTHORIZED = false`

`DECISION_DEVELOPMENT_SET_REUSE_FOR_NEW_POLICY_SEARCH_AUTHORIZED = false`

Future work may improve upstream information/alpha, execution/accounting infrastructure, or separately preregistered portfolio-risk constraints, but must not reopen this Decision-policy search merely because V4 failed.

## Scientific boundary accepted from local execution

- `STRUCTURAL_REPLAY_EXECUTION_COUNT = 1`
- `STRUCTURAL_REPLAY_RERUN = false`
- `REALIZED_DECISION_OUTCOMES_ACCESSED = false`
- `RETURNS_OR_PNL_ACCESSED = false`
- `PROTECTED_FORWARD_ACCESSED = false`
- `MODEL_REFIT_OR_RESCORE = false`
- `PROVIDER_OR_NETWORK_CALL = false`
- `THRESHOLDS_CHANGED = false`
- `ALTERNATIVE_V4_VARIANT_RUN = false`
- `SOURCE_FILES_EDITED_DURING_EXECUTION = false`
- `EXECUTION_COMMIT_OR_PUSH = false`

## Closure

Decision V4 Refill Decoupling V1 is rejected. Decision V2 is frozen as the incumbent Decision policy. The Decision research lane is closed. No economic outcome opening is warranted for V4 because the structural gate failed before that stage.