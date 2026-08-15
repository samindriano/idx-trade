# Joint Setup Readiness V1.1 Generic Runner — Parent Semantic Remediation Acceptance

Date: 2026-08-16 (Asia/Jakarta)

## Verdict

`JOINT_SETUP_READINESS_V1_1_PARENT_SEMANTIC_REMEDIATION_ACCEPTED_SCHEDULER_AUTHORITY_ROLLOVER_REQUIRED`

Reviewed implementation:
`integration/joint-setup-readiness-v1-1-generic-runner-v1@0a0943e3f86bc5b1200ca55cf4bc18a3a9a528ff`

Controlling prior review:
`review/idx-joint-setup-readiness-v1-1-forward-acceptance@2bdc8608d1900076b6e94f5f5c8b4c76c71b547f`

## Accepted remediation

The prior parent-semantic gap is closed for the accepted 2026-08-12 -> 2026-08-13 lineage.

- Price State is no longer admitted from self-consistent artifact/manifest metadata alone. The accepted context verifier runs first and the Price State frame is replayed from the pinned causal H/L/C/Volume context before parent hashes are recorded.
- Valid frozen-state mutations (for example UPTREND -> DOWNTREND and valid confirmation-state changes) with rewritten artifact SHA/distribution metadata are covered by adversarial tests and rejected.
- Foreign Flow Setup is verified against Representation V2, while Representation V2 is replayed from hash-verified archive/context/security-master authorities. A valid-domain Representation mutation plus regenerated Setup and rewritten parent metadata is rejected.
- Parent hashes are recorded only after upstream semantic verification.
- The accepted joint artifact remains immutable. Compatibility replay returns `created=false` and preserves artifact SHA `d83593b61a25f9f32a82c153001e0c548f29ffb255485b29a84760ae6ae03418` and manifest SHA `c3007af5af3061ee91be176fb0d29dc000cfc162fcc0c3642c5f26723646d646`.
- Frozen V1/V1.1 classifier, thresholds, domain policy, output schema, O2/counter, outcomes, models, and trade semantics remain unchanged.

Validation reported by the implementation lane: focused 47 passed; full pytest 81 passed / 1 known unrelated storage expectation failure / 82 collected; git diff --check PASS.

## New scheduler boundary

The remediation is accepted, but scheduler integration is **not yet authorized** because the new upstream semantic verification path is still tied to the controlled-smoke authority horizon.

Price State `_strict_price_parent_verify()` calls `approved_runtime_context_pins()`. Those pins hard-code the bridge calendar `2026-07-31_2026-08-13`, SHA `51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`, and combined session-set SHA `dd51d3dbcb29915ff80612d84a912da237331e979ee3847bd8fd4984ead413dd`. The replay path also requires the requested source session to be present in that bridge session set. Therefore a later real source session cannot pass this verifier unchanged.

Foreign Flow replay similarly pins the accepted bridge-session SHA in `_FF_SOURCE_AUTHORITIES`. This is valid authority for the accepted compatibility pair, but it is not yet a prospective authority-rollover contract for future sessions.

This is not a failure of the accepted 2026-08-13 artifact and not a regression in the semantic remediation. It is a separate prospective-runtime integration requirement.

## Next authorized scope

A separate bounded lane may define a future-session authority-rollover / parent-verification contract that:

1. preserves immutable historical/archive/security-master roots;
2. allows the official forward calendar/context authority to advance session-by-session without trusting mutable parent declarations;
3. validates each new canonical EOD / Foreign Flow context addition through the already accepted capture/provenance contracts;
4. constructs the Price State and Foreign Flow semantic verifier inputs from those accepted authorities;
5. proves one synthetic/future-session compatibility case without provider calls or touching O2/outcomes;
6. leaves the joint classifier and accepted 2026-08-13 artifact unchanged.

Only after that verifier is genuinely session-generic should scheduler integration be reviewed.
