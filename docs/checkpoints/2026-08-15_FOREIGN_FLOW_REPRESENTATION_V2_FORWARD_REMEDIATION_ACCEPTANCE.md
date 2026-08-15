# Foreign Flow Representation V2 Forward Producer — Remediation Acceptance

Date: 2026-08-15 (Asia/Jakarta)
Review type: independent remediation review
Reviewed branch: `integration/foreign-flow-representation-v2-forward-v1`
Reviewed final HEAD: `5374c238d3ed90823a18c49f1b0b1be4a0583469`
Prior review requiring remediation: `review/idx-foreign-flow-representation-v2-forward-v1@9d57bd5f7d4ac6db600d36e7aed7f8ccb84ee253`

## Verdict

`FOREIGN_FLOW_V2_FORWARD_PRODUCER_TIMING_REMEDIATION_ACCEPTED_CONTEXT_NOT_READY`

The prior blocking design issue is closed. The prospective producer now uses a completed source session `t` as its execution boundary and materializes a Representation V2 artifact for the next official feature session `t+1` without requiring any market data, Foreign Flow data, or canonical session directory for `t+1`.

This restores the frozen causal contract: all 15 Representation V2 features are functions of information through source session `t` and are assigned only to official feature session `t+1`.

## Independent review findings

1. **Timing remediation is correct.**
   - `materialize_representation_v2_for_session` takes `source_session=t`.
   - `feature_session=t+1` is derived from the supplied unique official calendar.
   - Market and Foreign Flow inputs are structurally clipped to `<= t` before the frozen builder is called.
   - The producer explicitly requires source-session market and Foreign Flow rows, not target-session rows.

2. **Frozen scientific semantics are preserved.**
   - The accepted `build_foreign_flow_representation_v2` implementation remains authoritative.
   - No feature formula, rolling window, percentile rule, persistence definition, cross-sectional rank definition, divergence definition, or threshold was changed.
   - Listing-aware and primary-liquid cross-sectional semantics remain delegated to the accepted causal context/builder path.

3. **Prospective artifact placement is acceptable.**
   - Before `t+1` capture completes, the immutable representation pair is written under:
     `forward_monitoring/prospective/foreign_flow_representation_v2/<t+1>/`.
   - The existing Foreign Flow catch-up runtime consumes that exact pair after the target session directory becomes available.
   - A simultaneous session-local and prospective representation location fails closed rather than choosing silently.

4. **Outcome protection remains intact.**
   - No provider call, protected outcome access, model fitting/scoring, historical performance test, O2 change, free-float/HSC integration, price-state layer, scheduler, or counter was introduced.

5. **Tests address the prior blocker.**
   - A dedicated test now proves production succeeds when every `t+1` market/flow row is absent.
   - The causal invariance test proves changing `t+1` Foreign Flow and close cannot alter the produced artifact.
   - Focused suite: `26 passed` (5 warnings).
   - Full suite: `110 passed, 1 failed` of 111 (5 warnings); the sole failure is the pre-existing unrelated storage audit-conflict expectation.
   - `git diff --check`: PASS.

## Remaining NO_GO boundary

The producer implementation is accepted, but the current local runtime context is **not authorized for a real run**.

The pinned historical market panel ends at 2026-07-31, while the defensible forward rolling extension is incomplete. In particular, the current evidence records missing/incomplete official calendar/market/flow context for the sessions needed to bridge from the historical cutoff to the current forward runtime. Existing 2026-08-11/12 artifacts must remain immutable and must not be used as synthetic repairs, and the incomplete 2026-08-10 capture must not be treated as complete.

Therefore:

- code/contract readiness: **ACCEPTED**;
- current live-context readiness: **NO_GO_CONTEXT_INCOMPLETE**;
- frozen V2 formulas are not rejected;
- no real prospective artifact should be generated until the existing calendar/EOD-data owner provides a complete, hash-pinned, defensible bridge after 2026-07-31.

## Next boundary

The next material task is data/runtime-context remediation only: establish the complete official session calendar plus verified market and Foreign Flow context from the historical cutoff through the next eligible completed source session, using the existing canonical EOD/calendar infrastructure. Do not modify the accepted producer formulas or reopen Foreign Flow historical alpha research.
