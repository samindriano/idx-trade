# IDX System Frontier Challenge V1

Date: 2026-09-20  
Lane: isolated `codex/alpha-available-data-20260919`  
Verdict: `FAIL — FRONTIER_CHALLENGE_FALSE_GREEN_BOUNDARIES_CONFIRMED`

## Purpose

This is the dedicated end-of-frontier challenge required before treating the
system deep-dive as complete. It composes already audited, bounded probes; it
does not patch runtime code, acquire provider data, open protected outcomes,
or mutate canonical/production state.

## Challenge gates

| Gate | Evidence | Result |
|---|---|---|
| Execution evaluation quantity completeness | A synthetic 5,000-share planned BUY and 2,500,000 IDR filled aggregate are accepted through the four-column execution boundary; planned/filled/residual fields are absent. | FAIL |
| Obligation conservation | The isolated design harness retains 2,600 shares remaining after a 2,400/5,000 first fill, with JSON reload and duplicate-fill idempotency. | PASS for the design harness; runtime adoption absent |
| Reconciliation provenance | Pinned runtime carries a false/default flag and prior-true gate, but no audited mismatch detector that produces `true`. | FAIL |
| Post-entry risk state | A synthetic 3x winner reaches 25% mark-to-market weight against a 15% entry cap, while paper state/hash has no mark/weight. | FAIL |
| Latest snapshot recovery | Malformed and payload-tampered latest snapshots fail closed, but remain in place; valid ancestors are not automatically selected or quarantined. | FAIL |

## Cross-component result

The same system can therefore satisfy local structural checks while losing
economic or operational meaning at a boundary:

- planned quantity `5,000` versus first fill `2,400` leaves a real design
  remainder of `2,600`, but the current evaluation boundary sees only the
  filled aggregate (`5%` turnover versus a `10%` planned reference);
- the state can carry `reconciliation_required=false` without evidence that
  reconciliation was actually performed;
- entry-weight control does not imply continuing mark-to-market concentration
  control; and
- hash verification can correctly reject the newest snapshot while the normal
  latest-state path remains unavailable despite an intact ancestor.

This is not a protected-performance claim. It is a structural counterexample
to the stronger claim that green component tests imply complete portfolio-system
correctness.

## Stop-rule assessment

- Major local surfaces in the frontier matrix are no longer `NOT_REVIEWED` or
  `SHALLOW`; remaining blockers are explicitly classified.
- Meaningful local contracts have adversarial or cross-component evidence,
  including quantity, CA, identity, risk, evaluation, artifact, restart, and
  recovery boundaries.
- Blast radius, history archaeology, persistence/restart, and no-retry limits
  are documented in the master dossier and findings log.
- Remaining high-value questions require protected outcomes, authorized real
  legacy fixtures, external/provider ownership, or an explicitly authorized
  implementation lane; they are not silently inferred here.

## Reproduction

- Probe: `research/idx_system_frontier_challenge_v1.py`
- Test: `tests/test_idx_system_frontier_challenge_v1.py`
- The probe invokes only existing outcome-blind synthetic/static probes.
- No runtime source, canonical data, provider, capture/cloud/telemetry,
  scheduler, or protected dataset was modified.
