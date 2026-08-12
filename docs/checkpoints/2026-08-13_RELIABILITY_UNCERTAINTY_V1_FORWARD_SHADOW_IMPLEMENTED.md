# Reliability Uncertainty V1 Forward Shadow — Implemented

Date: 2026-08-13  
Branch: `research/idx-reliability-uncertainty-v1-forward-shadow`  
Frozen specification: `docs/checkpoints/2026-08-13_RELIABILITY_UNCERTAINTY_V1_FORWARD_SHADOW_SPEC.md`  
Frozen specification commit: `3239a319fbd4ff492b16a74d899a20edc9affa7f`

## Decision

`RELIABILITY_V1_FORWARD_SHADOW_IMPLEMENTED_REVIEW_REQUIRED`

The deterministic V0-surviving `score_margin_reliability` proxy is now
implemented as a sidecar to the existing O2 forward archive. It is not a
model, probability, filter, ranking adjustment, sizing input, or independent
counter. The implementation reuses the existing forward-monitoring model-job
fan-out and does not create a second capture, database, or session hierarchy.

## Implementation

- `src/idx_trade/reliability_v1_forward_shadow.py` implements the frozen
  score-only formula, immutable artifact/manifest writes, source pinning, and
  the one-time artifact-only alignment command.
- `src/idx_trade/forward_model_runtime.py` creates the sidecar only after an
  accepted O2 score artifact is produced by the existing runtime.
- `src/idx_trade/forward_monitoring_runtime.py` exposes sidecar status through
  the existing monitoring status response.
- `tests/test_reliability_v1_forward_shadow.py` covers formula semantics,
  unavailable geometry, idempotent alignment, and source revision protection.

The existing O2.1 sealed-shadow implementation remains unchanged in meaning;
the Reliability V1 sidecar is separate and does not alter O2.1 artifacts.

## One-time 2026-08-12 alignment

The authorized alignment read only the already stored O2 score artifact and
its session manifest. No provider call, recapture, repair, O2 refit/rescore,
label/outcome read, or forward-outcome marker was used.

External sidecar directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\reliability_v1_shadow\score_margin\2026-08-12\`

| Item | Result |
|---|---:|
| Session | 2026-08-12 |
| Official session index | 1268 |
| Sidecar rows / tickers | 836 / 836 |
| O2 eligible and scored | 806 |
| Reliability `AVAILABLE` | 806 |
| O2-unscored / not applicable | 30 |
| Reliability finite values | 806 |
| Unavailable reason | `FLAT_RANGE_ZERO_DENOMINATOR` (30) |
| Score IQR | 0.03941221566031 |

The 30 ineligible rows remain in the sidecar with
`NOT_APPLICABLE_O2_UNSCORED`; no synthetic reliability value was created.

## Provenance and hashes

| Artifact | SHA-256 |
|---|---|
| O2 source score artifact | `b7fc6f22230500d65c1a24c4333b5601c0102da5bb99c3cae77a85bdb112c42d` |
| O2 source session manifest | `4f3d7814333b867316092758b8530270a14d2e741bc8cca2c12c1dffbc99b5e2` |
| O2 model | `42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb` |
| O2 feature order | `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f` |
| Reliability sidecar parquet | `76e5b79843e043fd3bff45d67a2a38b260abe7e5690a567c7fb569628be4422e` |
| Reliability sidecar manifest | `910cfc49a338e9f02211480b5af484eb6173a2c186a9ce598ec39d1220f20dbb` |

The sidecar manifest records implementation commit
`ed28bd6afd22eb9907146c496d7a28d7eeb021cb` and formula version
`score_margin_reliability_v1`.

All frozen protection flags are false: provider calls, source recapture or
repair, O2 refit/rescore, reliability model fit, composite score, threshold
or tier optimization, trade filtering, independent counter registration,
fresh-forward outcome access, and outcome marker writing.

## Validation

- Focused tests: `10 passed, 0 failed` for Reliability V1 and the existing
  O2.1 sealed-shadow tests.
- Full repository tests: `272 passed, 0 failed, 3 warnings` in `17.22s`.
- Existing warnings are non-blocking pandas FutureWarnings in the unrelated
  curated-identity and tradability-anchor code paths.

## Stop boundary

No reliability performance metric, forward label, F5/F6 artifact, fresh
forward outcome, filter, threshold, tier, or independent counter was created
or inspected. Further validation requires a separate preregistered
authorization after review.
