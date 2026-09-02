# INC-001 V17 Promotion Blast-Radius Audit V1

Date: 2026-08-31 Asia/Jakarta
Repository: `samindriano/idx-trade`
Lane: `data/ca-aware-feature-basis-remediation-v1`
Audit tree: `ad6f3bdf10f7768db5b1f597e81fd0d7dc2158a9`
Mode: read-only, outcome-blind

## Scope

This one bounded follow-up traces whether the external V17 residual
certification can silently alter frozen science, the CA population gate, or
production state. It inspects the actual R3 gate, feature-basis gate, V4
recompute contract, reconciliation primitives, canonical runner, and tracked
source/test references. No source/runtime/science code was changed.

## Result

`PROMOTION_BLAST_RADIUS_AUDIT=PASS`

`CHECKS=10 PASSED=10 FAILED=0`

- The canonical reconciliation runner imports
  `idx_trade.ca_aware_feature_basis_r3.global_ca_population_gate`.
- That runner passes `structural_event_complete=False`; its current R3 result
  therefore remains `FAIL_STRUCTURAL_CA_COVERAGE_NOT_CERTIFIED` regardless of
  the external V17 artifact.
- Tracked `src`, `scripts`, and `tests` contain no V17 artifact/path reference.
- The V17 economic ledger does not have the runtime event schema
  (`event_identity`, `effective_transition_state`,
  `event_semantics_certified`, `semantic_evidence_sha256`); it cannot be read
  directly by the event gate without an explicit reviewed adapter.
- With synthetic complete evidence, the actual R3 gate returns `PASS`; with
  structural completion false, bad family hash, or missing temporal semantics,
  it returns a fail-closed verdict.
- A promoted event without semantic certification and certified coverage without
  a SHA are both rejected by the actual gate helpers.

## Boundary checks

The R3 global gate requires, in order, structural completion, KSEI date-level
attestation, explicit fit/application/closure identity containment, the exact
frozen structural-family set with source/hash provenance, and temporal as-of
attestation. V4 recomputation masks only admitted direct features, rebuilds
derived columns, preserves universe membership, and does not fit or score.
The reconciliation primitive admits a transition only with an accepted
semantic, valid date, existing source event ID, and source-bound provenance.

V17 is therefore evidence for a future explicit admission decision, not an
automatic runtime input or production mutation. The V17 manifest remains bound
to V16 manifest `3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030`
and V17 manifest `8d2139c9388c6b94c4131ca692f0de3add433c294e4a7b20f2db6d7f22b106e8`.

## Immutable code references

SHA-256 of the audited working-tree files:

- `src/idx_trade/ca_aware_feature_basis_r3.py`:
  `e3b60090ca84e3de6cb654c720df7ded0d468c08890a10b0378f5db06367d738`
- `src/idx_trade/ca_feature_basis_gate_v1.py`:
  `b55a5f7156fa570573068a5750854f10024664223ff10d65435314f80bf502bc`
- `src/idx_trade/ca_feature_basis_family_coverage_v1.py`:
  `29bdb1f40ba6777bb7f77a9505ab5c2ea83034fb43db4eb1985dfd213ec77b59f`
- `src/idx_trade/ca_economic_event_reconciliation_v1.py`:
  `d31a3a14052077e9ca70cb6fb4ffb520849630a6c0caa5fa75d6ef93aba03814`
- `scripts/run_ca_aware_feature_basis_reconciliation_v1.py`:
  `f15bfdcb2b19dfd1ba24159f5504955adc93168f8b6c75908b6e176f70022d70`

## Non-blocking maintenance finding

Two modules define `global_ca_population_gate`: the canonical R3 module used by
the runner and the older `ca_source_authority_audit_v11` module used by a
historical source-audit builder. The current V17 path does not use either as an
implicit adapter, so this audit is PASS. Future work should consolidate or
explicitly document ownership before adding another integration layer; do not
silently treat the duplicate as equivalent.

## Safety result

No provider market call, outcome/target access, Phase-E, fit/refit/score,
counter/PaperState/R2 mutation, V16 mutation, production execution, deployment,
backfill, or Actions rerun occurred.

## Next decision

Keep V17 external and fail-closed. If admission is pursued later, add only one
reviewed adapter at the canonical boundary, bind its source/event/temporal
manifests, and prove the full existing gate contract before any Data/Research
admission. Do not add another V2/V3 path to bypass this boundary.
