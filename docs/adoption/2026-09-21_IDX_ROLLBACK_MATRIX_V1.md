# Rollback and Forward-Only Migration Matrix V1

Date: 2026-09-21

No rollback action is performed here. This is an architecture record for a
future separately authorized adoption.

| Adoption state | Code revision | Config | State/artifacts | Safe rollback statement |
|---|---|---|---|---|
| pre-adoption | active 32eaaa8e task checkout | current pinned config/SHA | current V1 artifacts | existing state remains untouched |
| candidate-only | adoption branch HEAD | synthetic candidate config | synthetic V2/migration roots only | freely discardable as an isolated lane |
| shadow V2 | authorized candidate revision | hash-pinned shadow config | V2 state plus immutable source/provenance | fallback must preserve both roots; no V1 overwrite |
| controlled canary | explicitly approved immutable revision | separately approved config | forward-only state migration | rollback requires a proven reader for new state |
| production V2 | separately approved revision | separately approved operational config | V2 canonical state | arbitrary downgrade is unsafe once V2-only obligations exist |

## Forward-only rule

Once V2 state contains obligations, migration provenance, or V2-only recovery
boundaries, V1 code must not be assumed to read it. A safe fallback therefore
requires one of:

1. a V1-compatible shadow reader proven against the exact state schema;
2. an operational freeze that preserves the V2 state until V2 resumes; or
3. an explicit, audited downgrade converter that never fabricates quantity,
   identity, CA, or pending state.

A code checkout rollback without a state plan is NO-GO.

## New obligations during fallback

New obligations must be rejected or durably held under a typed recovery fence;
they must not be silently recreated from target membership, current position,
or seat count. Any accepted fallback must preserve source hashes and event
identity.

## Configuration rollback

Code and runtime config are a pair. Restoring code without its matching
config/runner/branch/SHA binding is a lineage mismatch and must fail closed.
