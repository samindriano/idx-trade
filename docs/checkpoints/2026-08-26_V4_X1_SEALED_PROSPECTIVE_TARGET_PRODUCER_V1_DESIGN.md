# V4-X1 Sealed Prospective Target Producer V1 — Design Only

Status: `DESIGN_ONLY_NOT_IMPLEMENTED`, outcome-blind.

This checkpoint records the dependency boundary for a future sealed target
producer. It does not materialize, read, hash, or expose any protected target
values and does not authorize a target run.

## Required architecture

```text
retained frozen target semantics
  -> isolated sealed producer process
  -> protected target store
  -> public metadata-only attestation
  -> existing pre-access readiness / frozen gate
```

The existing `v4_x1_canonical_target_v1.py`, frozen target specification,
code-pin manifest, and protected-access gate remain authoritative. A future
producer must use a separate process and filesystem boundary, with no import
path from the public readiness adapter into the protected store.

## Public attestation contract

The public side may contain only the canonical target ID, required and matured
session counts, first/last matured session, safe source-manifest path/SHA,
construction-code pin, sealed artifact identity/hash if approved by the access
policy, and explicit guard/status fields. It must not contain target values,
row previews, returns, NAV, P&L, labels, or outcome-like summaries.

The final attestation must be revalidated by the existing frozen gate, not by a
new target-specific gate. It must prove the exact target identity and the
100-session maturity boundary without deriving maturity from a calendar alone.

## Required real inputs and current disposition

The producer would require certified next-session Open, raw Close at H5/H10,
official session calendar, the frozen V4-X1 identity/contract, and any accepted
corporate-action/price-basis continuity evidence. Existing code and schedule
pins are available. A sealed target store, protected target artifact, complete
100-session evidence, and public target attestation are not available in the
current pre-access runtime. No replacement provider or historical backfill is
authorized here.

## Failure and idempotency policy

Missing or stale Open/Close, incomplete session maturity, CA/price-basis
ambiguity, source/hash drift, process-boundary failure, or an existing
conflicting artifact must fail closed. A rerun of an already completed target
session must return the existing immutable identity without duplicate writes;
different bytes at an existing path must fail. A partial sealed run must remain
diagnosable but must never publish a ready attestation.

## Next authorization boundary

Before implementation, MAIN must separately freeze the producer process,
protected-store ACL/location, public attestation schema, exact maturity proof,
and one-shot recovery protocol. Until then the completion lane reports:
`SEALED_PROSPECTIVE_TARGET_MATERIALIZER_OR_ATTESTATION_NOT_FOUND`.
