# IDX-Trade Pre-Canary Gap Register V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **NO-GO UNTIL EXTERNAL GATES CLOSE**

| ID | Gap | Impact | Closure evidence required |
|---|---|---|---|
| G-01 | No real E2E paper-state population in bounded inventory | real migration/recovery cannot run | immutable manifest containing actual state artifacts |
| G-02 | Selected input class had only a pre-copy manifest | CLOSED for selected 20-file class; paper-state class remains absent | V2 manifest records source pre/post/copy equality |
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
| G-13 | Both selected session manifests have a calendar hash mismatch | session replay lineage is not complete | locate/admit exact historical calendar or mark sessions NOT_REPLAYABLE |
| G-14 | Copied score manifests embed absolute source artifact paths | score validation is closed for 15 clean manifests via explicit derived adapters, but full replay package is not path-consistent; one legacy model-id manifest is rejected | path-preserving immutable package and explicit legacy policy before full replay |
| G-15 | Verifier compared equivalent timezone representations as raw strings | CLOSED in shadow candidate; no alpha/science change | 26 focused tests plus real score adapter validation |
| G-16 | Evidence/stock summaries retain a wider universe than model input across all 29 sessions | CLOSED as a duplicate/state ambiguity; remains an interface-scope constraint | preserve explicit model-input/score universe boundary in any future replay |
| G-17 | Full 29-session package has 28 historical calendar-hash mismatches; none of the 22 distinct historical hashes was found among 128 approved CSVs; boundary sessions also fail current-calendar next-session rules | full historical replay remains blocked despite 27 input-level passes | admit exact historical calendar lineage, then rerun replayability and boundary checks |

## Stop condition

Any attempt to close a gap by reading provider data, protected outcomes,
counters, or live writable state would violate this lane. Gaps remain explicit
until the required authority and isolated inputs exist.
