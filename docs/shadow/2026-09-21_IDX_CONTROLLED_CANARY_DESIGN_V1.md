# IDX-Trade Controlled Canary Design V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **DESIGN ONLY / CANARY NOT AUTHORIZED OR EXECUTED**

## Preconditions

The canary must not start until the following are independently PASS:

- immutable real shadow input copy with two-pass source stability and copy
  hashes;
- real state migration classifications with no unknown/unreconciled rows;
- old-vs-candidate differential on identical read-only artifacts;
- historical replay and CA composition evidence;
- real recovery and forward-only fallback rehearsal;
- authoritative identity/config lineage;
- explicit policy decisions and an independent challenge;
- active scheduler/cloud/provider scope separately authorized.

## Required canary bindings

The following table makes every required design field explicit. `UNSET` is a
deliberate fail-closed value: it means the design cannot proceed until the
named external evidence exists. It is not a placeholder to be guessed during
execution.

| Required field | Design value | Status / boundary |
|---|---|---|
| Exact immutable candidate commit | `5c14b036ee179532903e1d0fd32d486db06cf3c7` | PINNED shadow candidate code; no live deployment |
| Exact runtime config SHA | `fff7af72d7c761218385faadba11bb09408110c76b9fbaa43e121d5ec9bfb3e0` | PINNED observed config copy; candidate/config pairing still requires authorization |
| Exact state input | `UNSET: no real paper-state artifact was admitted` | BLOCKED; no path or hash is invented |
| State mode | `MIGRATED_REAL_STATE_REQUIRED` | A fresh zero-state canary would not prove the adoption objective |
| Identity artifact requirement | `UNSET production authority; shadow interface only: valid.json SHA d129a74a8329f58b23bf942a6263dc532354cf9bdd776d23c3b5e31c41526d85` | BLOCKED external authority; synthetic artifact cannot be promoted |
| Scheduler/task invocation | `NO SCHEDULED-TASK INVOCATION; one explicitly authorized manual bounded run only` | No task edit, repin, trigger, or scheduler mutation is authorized by this design |
| Execution window | `UNSET until an official session is separately selected and frozen` | Must bind one decision/execution session and its calendar hash before launch |
| Observation period | `one complete decision-to-execution lifecycle plus post-execution verification` | Exact date/time must be frozen with the session input |
| Single-writer guarantee | `TRUE: new isolated canary root only; active E2E root and scheduler remain untouched` | Hard precondition; any competing writer is a kill condition |
| Kill criteria | first hash mismatch; missing/changed identity/config/calendar; provider response outside policy; outcome access; refit/rescore; canonical-data write; unexpected state/CA delta; duplicate writer; timeout; dirty checkout | Stop immediately and freeze artifacts; no retry |
| Success criteria | all predeclared lifecycle/state/CA/recovery hashes verify; no unexplained economic delta; outcome access/refit/rescore/provider mutation/canonical write all false; single-writer attestation valid | Must be evaluated from immutable output, not operator observation |
| Rollback/freeze procedure | freeze V2; stop new execution; retain immutable artifacts; repair candidate; resume same V2 state; no V1 downgrade converter | Synthetic rehearsal PASS; real-state rehearsal remains blocked |
| Allowed provider calls | `NONE` for this shadow design | Any future live/provider scope requires separate explicit authorization; no provider call occurs here |
| Prohibited actions | live migration; scheduler/config repin; live Official Open; cloud/R2 mutation; protected outcomes/H5/H10/OOS/PnL; alpha/refit/rescore; canonical rewrite; counter reset; production promotion | Hard boundary |

The observed config, schedule, and runner identities are recorded for
lineage only. Their presence does not close the real-state, identity-policy,
or canary-authorization gates.

## Proposed controlled sequence

1. Freeze and hash the candidate, config, runner, schedule attestation, and
   identity artifact.
2. Create a new shadow/canary root; never reuse the active writable root.
3. Load only the immutable manifest and verify all hashes before any phase.
4. Run one bounded session with outcome access disabled and no model refit,
   provider mutation, or canonical-data write.
5. Compare lifecycle, state, CA, recovery, and output hashes against the
   predeclared acceptance matrix.
6. Stop on the first gate failure; do not retry the failed live operation.
7. Keep the active pinned runtime unchanged until a separate promotion review.

## Current decision

This design is not a launch authorization. Because the real state input,
production identity authority, historical calendar lineage, differential,
recovery, policy, and external execution scope remain open,
`CONTROLLED_CANARY = NO-GO / NOT EXECUTED` and `PRODUCTION = NO-GO`.
