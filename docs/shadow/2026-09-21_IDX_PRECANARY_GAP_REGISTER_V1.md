# IDX-Trade Pre-Canary Gap Register V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **NO-GO UNTIL EXTERNAL GATES CLOSE**

| ID | Gap | Impact | Closure evidence required |
|---|---|---|---|
| G-01 | No real E2E paper-state population in bounded inventory | real migration/recovery cannot run | immutable manifest containing actual state artifacts |
| G-02 | Candidate shadow input manifest has only one hash snapshot | copy immutability is unproven | second identical hash/metadata pass plus copy hashes |
| G-03 | Session corpus is not paper state | replay cannot be promoted | interface proof that consumes it without state fabrication |
| G-04 | No real CA ledger/attestation admitted | CA composition cannot be challenged | separately authorized immutable CA evidence |
| G-05 | No real old-vs-candidate artifact pair | equivalence is unproven | dual-runtime read-only differential on identical copied inputs |
| G-06 | No real recovery chain | restart/fork/quarantine remains synthetic | real ancestor/lineage chain in shadow root |
| G-07 | Identity authority remains external | operational binding cannot be promoted | authoritative hash-pinned identity artifact and policy |
| G-08 | Fallback rehearsal is design-only | operational rollback safety unproven | isolated forward-only rehearsal |
| G-09 | Policy decisions remain external | canary admission cannot be decided | explicit close/pairing/expiry/FULL/concentration/tax/CA policy |
| G-10 | Active runtime/config remains pinned to old checkout | candidate is not deployed | separate explicit repin authorization and validation |
| G-11 | Inherited adoption docs have identity/matrix/provenance defects | review authority is split | corrected doc-only audit and exact immutable references |
| G-12 | Raw synthetic test evidence is not self-contained | reproduction is incomplete | exact commands, selectors, environment, and hashed result logs |

## Stop condition

Any attempt to close a gap by reading provider data, protected outcomes,
counters, or live writable state would violate this lane. Gaps remain explicit
until the required authority and isolated inputs exist.
