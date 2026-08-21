# Decision V4 Refill Decoupling V1 — Preregistration Audit

Date: 2026-08-22 Asia/Jakarta

Verdict: `PREREG_REVIEW_ACCEPTED_IMPLEMENTATION_ONLY_REPLAY_NOT_AUTHORIZED`

Reviewed prereg HEAD: `c3ff5ecaa930a9792047a98d6354094129ffe28f`

## Accepted scope

The candidate changes exactly one Decision V3 mechanism: severity-conditioned vacancy refill permission.

- start-of-session incumbent rules and all rank thresholds are unchanged;
- severe exit remains immediate at current rank >50;
- mild grace remains unchanged;
- Tier A/B/C definitions remain unchanged;
- Tier D remains forbidden;
- soft-replacement gap and semantics remain unchanged;
- on a session where at least one start-of-session incumbent is classified `SEVERE_DETERIORATION_EXIT`, all vacancy slots on that session may be filled only by Tier A;
- on sessions without severe exit, V3 A -> B -> C vacancy priority remains unchanged;
- temporary underfill remains allowed.

The severe-session flag is frozen before refill/soft replacement and therefore is not circular.

## Why the hypothesis is evidence-supported

The completed outcome-blind V3 failure diagnosis found:

- 373/599 non-bootstrap transitions were severe-exit sessions;
- 373/373 severe-exit sessions also had vacancy fills;
- 77.8567% of observed replacements occurred on severe-exit sessions;
- high-churn share was 66.4879% on severe-exit sessions vs 19.0265% without severe exits;
- next-session severe-exit rates were A vacancy 22.9167%, B 30.1527%, C 38.8693%, A-soft 8.7886%;
- Blocks 3+6 amplified the same severe/refill mechanism rather than showing a separate regime mechanism.

## Surviving risks — not blockers

1. **Replacement-count mechanics.** The frozen structural metric counts `max(sells, buys)`. Suppressing B/C buys does not mechanically erase same-session mandatory sells. Any churn improvement must therefore come primarily through fewer fragile entrants and fewer later exits, not bookkeeping. This makes the hypothesis falsifiable rather than guaranteed.
2. **Capacity risk.** Severe-exit sessions are common, especially in Blocks 3+6. Restricting all vacancy slots on those sessions to Tier A may create substantial temporary underfill. Existing V3 capacity gates remain unchanged and may reject the candidate.
3. **Session-level intervention is deliberately coarse.** A severe-session flag restricts B/C for every vacancy on that session regardless of whether a specific slot originated from severe, mild, universe, or pre-existing underfill. This is accepted because it is explicit, deterministic, and avoids post-hoc slot attribution. No alternative slot-level variant is allowed in the same replay.
4. **Soft replacement remains active.** This may preserve some churn, but the diagnosis showed A-soft entrants were materially more durable and soft replacement was not the dominant stress-block mechanism. Disabling it now would add a second mechanism.

## Frozen evaluation

All V3 structural gates remain unchanged. No alternative refill cap, threshold, cooldown, min-hold, turnover cap, regime rule, Tier-D permission, or soft-gap change is authorized in the same replay.

Required descriptive diagnostics are non-gating and may only explain the frozen verdict.

## Authorization

Implementation of exactly this preregistered Decision V4 candidate is authorized. Historical 600-OOS replay is **not** authorized until implementation parity is independently audited and a separate guarded structural replay runner is frozen/audited.
