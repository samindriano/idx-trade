# IDX-Trade Shadow Immutable Attestation Revalidation V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **REVALIDATION PASS / NO SOURCE INSTABILITY OBSERVED**

## Scope

This is an independent, read-only revalidation of the already admitted shadow
copies. It does not inspect or modify the active runtime root, scheduler,
provider, cloud/R2, protected outcomes, counters, or canonical data.

The check streamed file bytes for SHA-256 and compared the immutable copies to
their documented local source roots. It did not persist file contents.

## Results

| Copy class | Files checked | Missing source | SHA mismatches | Size mismatches |
|---|---:|---:|---:|---:|
| All retained sessions | 237 | 0 | 0 | 0 |
| Extended parent-root evidence | 32 | 0 | 0 | 0 |
| Operational shadow attestation entries | 89 | 0 | 0 | 0 |

### Operational attestation

The external operational manifest and tracked Git review copy contain identical
89-entry metadata arrays. The external operational shadow root was independently
checked against every entry:

- declared file count: `89`;
- declared total bytes: `810,687`;
- per-file hash/size checks: `89/89` pass;
- `two_pass_source_stability`: `true`;
- `active_runtime_touched`: `false`;
- `provider_calls`: `false`;
- `protected_outcome_access`: `false`;
- `scheduler_touched`: `false`.

The aggregate was recomputed using the manifest's actual serialization contract:
SHA-256 of compact JSON for the insertion-ordered `entries` array, followed by
one LF. The result matches exactly:

`169dda434dd52c74f7456c9876caabdd33aa523db4097ba6a7b78c888b9597bc`

An initial scratch calculation using a different, human-readable row format did
not match; that was a formula mismatch, not a file mismatch. After recovering
the manifest serialization contract, the aggregate matched and no attestation
defect remains.

## Qualification boundary

This revalidation strengthens only immutable-copy integrity. It does not create
paper state, a fill vector, a CA ledger, a recovery chain, or historical runtime
identity. The real migration, real CA composition, real recovery, and
pre-canary gates remain at their existing fail-closed verdicts.
