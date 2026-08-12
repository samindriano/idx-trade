# Reliability Uncertainty V1 Forward Shadow — Independent Acceptance

Date: 2026-08-13 (Asia/Jakarta)
Branch: `research/idx-reliability-uncertainty-v1-forward-shadow`
Frozen specification commit: `3239a319fbd4ff492b16a74d899a20edc9affa7f`
Initial implementation: `ed28bd6afd22eb9907146c496d7a28d7eeb021cb`
Review remediation: `4af006d545f9017096e0da4599f4448b73b9f0e2`
Remediation documentation HEAD: `5927a5df5dce1b7b48827ef7b88c20496b557925`

## Verdict

`RELIABILITY_V1_FORWARD_SHADOW_ACCEPTED`

Independent re-review accepts the Reliability V1 deterministic forward-shadow implementation after the bounded remediation requested during first review.

This acceptance is engineering/spec-compliance acceptance only. It does **not** constitute forward-performance validation and does not authorize outcome access, threshold/tier optimization, filtering, position sizing, a Reliability model, or an independent Reliability counter.

## Review findings

The implementation now conforms to the frozen contract on the material boundaries reviewed:

- Reliability remains subordinate only to an accepted O2 score artifact and no longer depends on O2.1 availability or success.
- O2.1 absence or failure cannot short-circuit Reliability execution.
- Existing sidecars are reused without rewrite/recomputation only after fail-closed validation of the sidecar state and the exact pinned O2 score artifact/session manifest.
- Source artifact or source session-manifest revisions after sidecar creation fail closed.
- Protected runtime flags and locked outcome state are checked before existing-sidecar reuse.
- Frozen score-margin semantics are preserved, including deterministic O2-score ties, tied average-rank display percentiles, and unavailable geometry for fewer than two scored rows or zero/non-finite IQR.
- Reliability does not mutate the O2 counter or create an independent counter.

## Preserved first forward sidecar

The accepted 2026-08-12 / official session index 1268 sidecar remained immutable through remediation and review:

- rows/tickers: `836 / 836`
- Reliability `AVAILABLE`: `806`
- `NOT_APPLICABLE_O2_UNSCORED`: `30`
- Reliability artifact SHA-256: `76e5b79843e043fd3bff45d67a2a38b260abe7e5690a567c7fb569628be4422e`
- Reliability manifest SHA-256: `910cfc49a338e9f02211480b5af484eb6173a2c186a9ce598ec39d1220f20dbb`
- pinned O2 score artifact SHA-256: `b7fc6f22230500d65c1a24c4333b5601c0102da5bb99c3cae77a85bdb112c42d`
- pinned O2 session manifest SHA-256: `4f3d7814333b867316092758b8530270a14d2e741bc8cca2c12c1dffbc99b5e2`

No 2026-08-12 Reliability recomputation was required or authorized.

## Validation evidence

Remediation validation reported:

- focused Reliability + O2.1 tests: `16 passed`
- full repository pytest: `278 passed, 0 failed, 3 warnings`
- warnings are existing unrelated pandas FutureWarnings

The remediation tests add coverage for O2-score ties, tied percentile average ranks, fewer-than-two scored rows, source artifact and source manifest mutation after sidecar creation, protected-flag tampering, idempotent immutable reuse, and independence from unavailable O2.1.

## Scientific boundary after acceptance

Reliability V1 remains `EXPLORATORY_FORWARD_SHADOW` while the existing O2 fresh-forward cohort accumulates. It has no separate outcome gate.

Continue collecting the frozen `score_margin_reliability` sidecar prospectively alongside accepted O2 sessions. The existing O2 vault remains the sole gate. Before any protected outcome is read when that gate becomes eligible, a separate outcome-blind Reliability V1 forward-evaluation checkpoint must preregister the exact pass/fail aggregation thresholds required by the frozen specification.

Until such forward evaluation passes, do not interpret Reliability percentile as probability, create LOW/MEDIUM/HIGH tiers, filter trades, alter O2 ranking, or expose realized Reliability performance.
