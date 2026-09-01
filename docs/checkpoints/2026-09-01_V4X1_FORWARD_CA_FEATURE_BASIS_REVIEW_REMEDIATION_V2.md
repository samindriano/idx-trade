# V4-X1 Forward CA Feature-Basis Review Remediation V2

Status: `FORWARD_CA_FEATURE_BASIS_FIREWALL_REVIEW_READY_V2`

This is an outcome-blind remediation candidate on the existing review branch.
It does not activate or certify any forward session and does not change frozen
science, the scorer, model weights, feature formulas, feature order, or
population construction.

## Closed review findings

The existing `PopulationScoreGate` now requires three independently bound
properties before scorer entry:

1. historical/control high, low, close, volume, and regular-market-value basis
   evidence remains complete and window-safe;
2. the fresh Geometry3 candidate `session_ohlcv` artifact contains exactly the
   scorer ticker set and session, has a verified OPEN, source identity, source
   evidence hash, and non-future knowledge/retrieval times;
3. `feature_basis_evidence.json` is covered by a detached root manifest that
   pins the producer implementation, recomputes every retained child file,
   rejects undeclared or duplicate evidence IDs, and binds all source,
   authority, identity, calendar, revision, PIT, OPEN, model-input, and clean
   panel references.

The root manifest identity is non-circular: the manifest binds the evidence
file hash, the evidence binds the manifest identity, and the admission
attestation binds the complete root-manifest SHA-256. Declarative child hashes
are never accepted without recomputation.

## Preserved boundaries

The gate remains an extension of the existing pre-scorer admission path. It
does not remove rows, rewrite `listed_to` into frozen scoring code, fabricate a
no-event result, or alter PREOPEN_CA, PaperState, counters, outcomes, R2,
providers, scheduling, deployment, or production configuration. Frozen
17-blob integrity remains a required runtime check.

The retained 44 transition replay remains `BASIS_UNKNOWN`. The 15 retained
forward sessions remain `SOURCE_CAPTURE_UNRESOLVED` until an independently
authoritative, population-wide bundle is actually produced. No backfill or
retroactive credit is implied.

The producer contract is documented at
`docs/specs/forward_feature_basis_evidence_producer_v1.md`. It is a contract,
not a producer certificate; producer implementation approval and runtime
source authority remain separate gates.

## Validation target

The candidate is ready for independent review after OPEN, root-manifest,
producer-binding, scorer-ordering, frozen-blob, full-test, syntax, parse, and
diff checks pass. Production activation remains `NO-GO` until a genuine future
scheduled session supplies complete authoritative evidence.
