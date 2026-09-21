# IDX-Trade Pre-Canary Gap Register V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **NO-GO UNTIL EXTERNAL GATES CLOSE**

| ID | Gap | Impact | Closure evidence required |
|---|---|---|---|
| G-01 | No real E2E paper-state population in bounded inventory | real migration/recovery cannot run | immutable manifest containing actual state artifacts |
| G-02 | Selected input class had only a pre-copy manifest | CLOSED for selected 20-file class; paper-state class remains absent | V2 manifest records source pre/post/copy equality |
| G-03 | Session corpus is not paper state | replay cannot be promoted | interface proof that consumes it without state fabrication |
| G-04 | Real CA event registry is admitted, but no CA entitlement/settlement ledger or holdings/obligation attestation is admitted | CA composition cannot be challenged | separately authorized immutable ledger/holdings/obligation evidence |
| G-05 | No real old-vs-candidate artifact pair | equivalence is unproven | dual-runtime read-only differential on identical copied inputs |
| G-06 | No real recovery chain | restart/fork/quarantine remains synthetic | real ancestor/lineage chain in shadow root |
| G-07 | Identity authority remains external | operational binding cannot be promoted | authoritative hash-pinned identity artifact and policy; shadow interface challenge is now PASS only |
| G-08 | Real-state fallback remains unavailable; synthetic forward-only rehearsal is complete | actual historical-state rollback/resume safety remains unproven | real migratable V2 state plus separate fallback authorization; synthetic closure is recorded in `2026-09-21_IDX_FORWARD_FALLBACK_REHEARSAL_V1.md` |
| G-09 | Policy decisions remain external | canary admission cannot be decided | explicit close/pairing/expiry/FULL/concentration/tax/CA policy |
| G-10 | Active runtime/config remains pinned to old checkout | candidate is not deployed | separate explicit repin authorization and validation |
| G-11 | Inherited adoption docs have identity/matrix/provenance defects | review authority is split | corrected doc-only audit and exact immutable references |
| G-12 | Raw synthetic test evidence is not self-contained | reproduction is incomplete | exact commands, selectors, environment, and hashed result logs |
| G-13 | Both selected session manifests have a calendar hash mismatch | session replay lineage is not complete | locate/admit exact historical calendar or mark sessions NOT_REPLAYABLE |
| G-14 | Copied score manifests embed absolute source artifact paths | score validation is closed for 15 clean manifests via explicit derived adapters, but full replay package is not path-consistent; one legacy model-id manifest is rejected | path-preserving immutable package and explicit legacy policy before full replay |
| G-15 | Verifier compared equivalent timezone representations as raw strings | CLOSED in shadow candidate; no alpha/science change | 26 focused tests plus real score adapter validation |
| G-16 | Evidence/stock summaries retain a wider universe than model input across all 29 sessions | CLOSED as a duplicate/state ambiguity; remains an interface-scope constraint | preserve explicit model-input/score universe boundary in any future replay |
| G-17 | Full 29-session package has 28 historical calendar-hash mismatches; none of the 22 distinct historical hashes was found among 143 bounded CSVs; boundary sessions also fail current-calendar next-session rules | full historical replay remains blocked despite 27 input-level passes | admit exact historical calendar lineage, then rerun replayability and boundary checks |
| G-18 | Candidate CA parser rejected canonical copied CSV rows whose optional share counts were materialized as scalar `NaN` | CLOSED in shadow candidate; no share count or ratio fabricated | focused CA/provider plus CA/attestation/dividend/V4-X1 regression set 38/38 and 38/38 copied real CA rows parsed |
| G-19 | Scheduler/task scope is not authorized for candidate invocation or repin | canary single-writer and task identity cannot be proven | explicit scheduler authorization, task/runner binding, and single-writer attestation without editing the active task |
| G-20 | Provider checkout/call scope is not admitted in this shadow lane | real forward capture/execution cannot be qualified | separately authorized provider scope or immutable provider evidence package; no provider fallback may be inferred |
| G-21 | Live canary observability/side-effect evidence does not exist | lifecycle, writer, outcome, and external-side-effect gates cannot be observed in a real run | predeclared telemetry/log/attestation contract and an immutable canary observation package |

## Closure ownership and canary dependency

This table supplies the Phase 16 decision metadata for every gap. “Owner” is
an authority role, not an inferred person. “Yes” under canary dependency means
the canary remains impossible until the specified evidence or authorization is
present.

| ID | Required provider/authority or decision owner | Remaining local help | Canary impossible without closure |
|---|---|---|---|
| G-01 | runtime/state archive owner must provide immutable paper-state package | inventory and admission tooling ready; cannot recover absent state | Yes |
| G-02 | shadow evidence maintainer | closed for admitted class; keep source/copy attestations | No, independent of missing paper state |
| G-03 | runtime-state owner must define an authoritative state interface | adapter design can remain outcome-blind; no state may be fabricated | Yes |
| G-04 | CA/settlement evidence authority and state owner | parser and event-shape checks are complete; no ledger can be inferred | Yes |
| G-05 | old-runtime artifact owner plus candidate integrator | comparator can run once identical real pair is admitted | Yes |
| G-06 | runtime snapshot archive owner | recovery contracts and quarantine checks are ready | Yes |
| G-07 | identity authority and policy owner | shadow loader/negative cases complete | Yes |
| G-08 | runtime/state owner plus rollback policy owner | synthetic freeze/resume rehearsal complete | Yes for real-state fallback |
| G-09 | explicit policy owner | can encode a supplied policy; cannot choose economic/tax/CA policy | Yes |
| G-10 | deployment owner with explicit repin authorization | can validate a separately authorized candidate; no live repin allowed | Yes |
| G-11 | review owner / documentation maintainer | corrected shadow audit is committed | Yes if review authority remains split |
| G-12 | shadow evidence maintainer | exact commands and selectors can be retained; raw logs remain synthetic | Yes for reproducibility approval |
| G-13 | historical calendar authority | bounded local search is complete; no substitution permitted | Yes for affected replay |
| G-14 | score-artifact owner / immutable package authority | path-preserving adapter exists; cannot rewrite source manifest | Yes for full replay |
| G-15 | local engineering | closed and regression-tested | No |
| G-16 | replay-interface owner | preserve explicit model-input/score-universe boundary | Yes if a future replay collapses the universes |
| G-17 | historical calendar authority | rerun reconciliation after exact bytes are admitted | Yes for historical replay |
| G-18 | local engineering / CA parser maintainer | closed in shadow candidate with 38/38 evidence | No, provided the fix is separately reviewed |
| G-19 | scheduler/deployment owner | can validate a supplied task identity and lock contract; no active task edit is allowed | Yes |
| G-20 | provider/data authority | parser and captured-input adapters are ready; no provider call or checkout admission is allowed | Yes |
| G-21 | runtime operations/observability owner | synthetic lifecycle/file attestation exists; live telemetry cannot be fabricated | Yes |

## Stop condition

Any attempt to close a gap by reading provider data, protected outcomes,
counters, or live writable state would violate this lane. Gaps remain explicit
until the required authority and isolated inputs exist.
