# Reliability Uncertainty V1 Forward Shadow — Review Remediation

Date: 2026-08-13  
Branch: `research/idx-reliability-uncertainty-v1-forward-shadow`  
Frozen specification: `docs/checkpoints/2026-08-13_RELIABILITY_UNCERTAINTY_V1_FORWARD_SHADOW_SPEC.md`  
Frozen specification commit: `3239a319fbd4ff492b16a74d899a20edc9affa7f`  
Implementation remediation commit: `4af006d`

## Scope

This remediation addresses ChatGPT review only. The frozen Reliability V1
formula, existing 2026-08-12 sidecar, O2 model, and O2.1 semantics were not
changed.

## Changes

1. Reliability fan-out is now independent of O2.1 availability. An absent or
   failed O2.1 sealed shadow no longer short-circuits Reliability execution;
   Reliability still runs when an accepted O2 score artifact exists.
2. Existing sidecars are validated fail-closed before reuse. Validation checks
   the immutable sidecar itself, all protected flags, and the exact pinned O2
   score-artifact path/hash plus O2 session-manifest path/hash. A valid sidecar
   is never rewritten or recomputed during this validation.
3. Tests now cover O2-score ties, deterministic tie ordering, tied percentile
   average ranks, fewer-than-two scored rows, source-artifact revision after
   sidecar creation, source-session-manifest revision after sidecar creation,
   protected-flag tampering, O2.1-unavailable independence, and the existing
   idempotent/source-revision contracts.

## Preserved 2026-08-12 sidecar

The existing external artifact was validated through the existing-sidecar
path only. No new Reliability alignment or recomputation was performed.

| Item | Value |
|---|---|
| Session / official index | 2026-08-12 / 1268 |
| Rows / tickers | 836 / 836 |
| `AVAILABLE` | 806 |
| `NOT_APPLICABLE_O2_UNSCORED` | 30 |
| Reliability artifact SHA-256 | `76e5b79843e043fd3bff45d67a2a38b260abe7e5690a567c7fb569628be4422e` |
| Reliability manifest SHA-256 | `910cfc49a338e9f02211480b5af484eb6173a2c186a9ce598ec39d1220f20dbb` |
| Artifact/manifest changed | `false` |

The pinned O2 source identities remain unchanged:

- score artifact: `b7fc6f22230500d65c1a24c4333b5601c0102da5bb99c3cae77a85bdb112c42d`
- session manifest: `4f3d7814333b867316092758b8530270a14d2e741bc8cca2c12c1dffbc99b5e2`

## Validation

- Focused Reliability + O2.1 shadow tests: `16 passed, 0 failed`.
- Full repository pytest: `278 passed, 0 failed, 3 warnings` in `16.59s`.
- Warnings are the existing pandas FutureWarnings in curated-identity and
  tradability-anchor code paths.

## Boundaries preserved

No provider call, recapture, O2 rescore/refit, Reliability recomputation of
the accepted 2026-08-12 artifact, outcome access, tiering, filtering, model
fit, independent counter, or `FORWARD_OUTCOME_ACCESS_STARTED` marker was
used or created. The coordination status remains `REVIEW` pending ChatGPT
re-review.
