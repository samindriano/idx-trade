# IDX-Trade Authoritative Runtime Adoption Packet V1

Date: 2026-09-21 (Asia/Jakarta)

Status: PROVISIONAL LOCAL REVIEW PACKET; no live adoption.

## Final verdicts by gate

| Gate | Verdict | Scope |
|---|---|---|
| SOURCE INTEGRATION | PASS | clean candidate extraction from 402; no opaque merge |
| STATE MIGRATION | PASS SYNTHETIC / BLOCKED LIVE | compatibility classifier, provenance, activation, and shadow replay only |
| SYNTHETIC RUNTIME | PASS | candidate full suite 905 passed, 3 pre-existing warnings |
| ENTRYPOINT COMPATIBILITY | PASS STATIC / SYNTHETIC | four phase scripts, controller boundaries, child interruption tests |
| CONFIG COMPATIBILITY | PASS STATIC | hash/branch/commit/dual-calendar mode binding |
| IDENTITY AUTHORITY | BLOCKED EXTERNAL | contract accepts hash-pinned caller artifact; authority not admitted |
| POLICY READINESS | BLOCKED EXTERNAL | unresolved close, pairing, expiry, FULL, concentration, tax/net, structural CA |
| RECOVERY | PASS SYNTHETIC | quarantine, verified ancestor, fork rejection, recovery fence |
| ROLLBACK | BLOCKED EXTERNAL | forward-only implications documented; no live downgrade proof |
| CONTROLLED CANARY READINESS | NO-GO | requires explicit external authority and operational adoption |
| PRODUCTION READINESS | NO-GO | not requested or authorized in this lane |

The packet intentionally contains separate verdicts; it does not collapse them
into one global green result.

## Integration identity

- Branch: codex/idx-authoritative-runtime-adoption-20260921
- Candidate base: 402fca4b27e91cf8c82d21ff1394ba2d6da73656
- Immutable hardening source: 8ceec523d49500949b5ecf46e3b862cd4eb1c4fd
- Active Windows task source: 32eaaa8e50d0521de7faef98faa8081219bc667b
- Current origin/main: 8b5bc6db1a4d89ca0fb2a49760899d3f18453f23
- Deep-dive checkpoint: d007077694ad861abd86f21cc8f42f7575837298

The active task checkout was not changed. The candidate is a clean local
lineage experiment, not a repin or deployment.

## Clean extraction commits

1. 1a99ab3d — runtime lineage and extraction contract.
2. 37a214d3 — hardened contract/state integration.
3. 370c6e9d — controller recovery and phase entrypoints.
4. c602017f — migration compatibility and V1/V2 config mode gates.
5. 25b69a17 — synthetic multi-session rehearsal matrix.
6. 66140b05 — shadow migration rehearsal.

The first three implementation commits are direct final-state extractions
from the immutable hardening source, grouped by dependency closure. The last
three are candidate-only adoption remediations and rehearsal evidence.

## Evidence

- Full candidate pytest: 905 passed, 3 pre-existing pandas FutureWarnings.
- Full run was executed against candidate code HEAD `66140b05` and reached
  100%.
- Selected 22-scenario rehearsal matrix: PASS.
- Migration compatibility matrix: 11 shape cases PASS.
- Shadow migration/reload/replay and partial-persistence fence: 2 PASS.
- V1/V2 config mode and phase binding focused tests: PASS.
- Hardening independent challenge records V1/V2: PASS on the original
  hardening source. A fresh candidate-specific independent challenge is still
  a separate review gate; it does not authorize live adoption.

## Required external gates before any shadow or canary

- reconcile the active 32eaaa8e Windows checkout with the candidate and
  authorize any config/runner repin;
- admit an authoritative identity artifact separately from the identity
  contract;
- supply explicit Decision-seat close/pairing/expiry/FULL policy;
- resolve structural CA and external reconciliation authority;
- authorize an immutable shadow runtime root and migration input manifest;
- define operational fallback for V2-only state before any canary;
- independently review the candidate-specific challenge result.

No provider, canonical data, protected outcome, scheduler, cloud, capture,
telemetry, counter, alpha, or production state was mutated or accessed by
this packet's local work.
