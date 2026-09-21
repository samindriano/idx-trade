# IDX-Trade Authoritative Runtime Integration and Adoption Marathon V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **ADOPTION CANDIDATE LOCAL REVIEW READY / NO LIVE ADOPTION**

This dossier is the durable control record for the isolated branch
`codex/idx-authoritative-runtime-adoption-20260921`. It does not authorize a
merge, scheduler change, cloud change, provider capture, canonical-data write,
counter mutation, protected-outcome access, alpha/model change, or production
promotion.

## Objective and boundaries

The objective is to convert the completed hardening implementation into a
clean, lineage-correct, migration-safe, operationally reviewable E2E paper
runtime candidate. The candidate is synthetic/local until a later explicit
authorization.

The following remain outside this lane:

- frozen V4-X1 alpha and Decision V2 substantive science;
- canonical/provider/capture/cloud/R2/telemetry state;
- Windows Task Scheduler state;
- protected H5/H10/OOS/PnL outcomes and counters;
- automatic migration of real artifacts;
- production or controlled-canary activation.

## Verified anchors

| Item | Verified value | Meaning |
|---|---|---|
| Active E2E-Paper task checkout | `32eaaa8e50d0521de7faef98faa8081219bc667b` | Actual scheduled source for the E2E paper task |
| Active OfficialOpen task checkout | `32eaaa8e50d0521de7faef98faa8081219bc667b` | Wrapper delegates to the same pinned checkout |
| Retained reliability integration | `402fca4b27e91cf8c82d21ff1394ba2d6da73656` | 12-commit reliability/evidence integration over 32eaaa8e |
| Completed hardening source | `8ceec523d49500949b5ecf46e3b862cd4eb1c4fd` | Immutable local development evidence; 109 commits after 402 |
| Deep-dive checkpoint | `d007077694ad861abd86f21cc8f42f7575837298` | Original system-frontier evidence |
| Current origin/main | `8b5bc6db1a4d89ca0fb2a49760899d3f18453f23` | Coordination/cloud-main lineage, not the active local runtime source tree |
| New adoption branch | `codex/idx-authoritative-runtime-adoption-20260921` | Isolated candidate lane, currently based on 402 |

The task audit was read-only. The active task actions, runtime roots, and
checkout identities were not edited.

## Lineage decision

The operational lineage is resolved as a **documented split**, not falsely
collapsed into one source:

1. The scheduled Windows E2E-Paper and OfficialOpen paths execute from the
   pinned checkout at `32eaaa8e`.
2. `402fca4` is the retained reliability integration that adds the
   Official-Open/evidence-health changes required by the hardened consumer
   graph.
3. `8ceec523` is the completed hardening development tree and is preserved
   as immutable provenance; it is not the adoption base.
4. `origin/main@8b5bc6d` is substantially divergent and its cloud workflow
   pins a different runtime ref (`045e25a1)); it is not silently adopted.

### Candidate base decision

**Candidate base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`.**

This is a candidate-only decision, not a live replacement. It is defensible
because it is the retained reliability integration directly descended from
the active `32eaaa8e` checkout, it is the exact base used by the completed
hardening work, and its four implementation commits are relevant to the
Official Open and evidence-health consumer graph. The active `32eaaa8e`
checkout remains untouched until a separately authorized operational
adoption decision.

## Phase status

| Phase | Current determination | Evidence / next proof |
|---|---|---|
| 0 contract recovery | PASS | Hardening dossier, completion audit, registry, catalog, migration matrix, challenge records read |
| 1 lineage adjudication | PASS WITH SPLIT | Lineage matrix; actual task and checkout audit |
| 2 clean extraction | PASS LOCAL | Extraction map; six clean candidate commits and disjoint payload groups |
| 3 adoption base | PASS FOR CANDIDATE | 402 selected; no live adoption |
| 4 integrated hardened stack | PASS LOCAL / SYNTHETIC ONLY | Clean candidate extraction and full local suite |
| 5 migration architecture | PASS LOCAL / SYNTHETIC ONLY | State migration matrix and executable compatibility classifier |
| 6 shadow migration rehearsal | PASS LOCAL / SYNTHETIC ONLY | Provenance, activation, reload/replay, and write-failure fence tests |
| 7 multi-session rehearsal | PASS SELECTED SYNTHETIC MATRIX | 22-scenario matrix executed; broader independent challenge pending |
| 8 entrypoint compatibility | PASS STATIC / SYNTHETIC | Static entrypoint matrix, phase binding, and V1/V2 mode guard |
| 9 Windows/cloud interface review | READ-ONLY BASELINE PASS | Task/workflow mapping recorded; no mutation |
| 10 identity authority boundary | CONTRACT READY / AUTHORITY NOT ADMITTED | Hash-pinned caller artifact only |
| 11 policy review | FAIL-CLOSED / EXTERNAL DECISIONS OPEN | No unresolved policy invented |
| 12 backward compatibility | PASS LOCAL / SYNTHETIC ONLY | V1/V2/recovery/migration compatibility tests pass; live authority is open |
| 13 forward false-green challenge | NOT YET PROVEN | Independent semantic chain challenge pending |
| 14 rollback architecture | DEFINED / REHEARSAL PENDING | Rollback matrix |
| 15 adoption packet | PASS LOCAL | This dossier, packet, traceability, and durable companion records |
| 16 independent adoption challenge | NOT YET RUN | Must run against assembled candidate |

No global PASS is claimed.

## Candidate verification snapshot

- Candidate code HEAD at the last full run: 66140b05.
- Full candidate run: 905/905 reached 100% with three pre-existing pandas
  FutureWarnings and no test failures.
- Selected 22-scenario rehearsal matrix: PASS; parameter expansion executed
  the CA timing boundaries and explicit close variants.
- Migration compatibility shape matrix: 11/11 PASS; shadow migration and
  partial-persistence fence: 2/2 PASS.
- No provider, outcome, cloud, capture, scheduler, telemetry, or live runtime
  state was accessed.

## Acceptance levels

`READY_IN_SOURCE`, `READY_IN_SYNTHETIC_RUNTIME`, `READY_FOR_SHADOW`,
`READY_FOR_CONTROLLED_CANARY`, and `PRODUCTION_READY` are separate gates.
At this revision the candidate is at most **READY_IN_SOURCE** for the portions
already extracted from hardening; it is not ready for shadow, canary, or
production.

## Durable companion records

- `2026-09-21_IDX_AUTHORITATIVE_RUNTIME_LINEAGE_MATRIX_V1.md`
- `2026-09-21_IDX_HARDENING_EXTRACTION_MAP_V1.md`
- `2026-09-21_IDX_CONTRACT_ADOPTION_REGISTRY_V1.md`
- `2026-09-21_IDX_STATE_MIGRATION_MATRIX_V1.md`
- `2026-09-21_IDX_ENTRYPOINT_CONFIG_COMPATIBILITY_MATRIX_V1.md`
- `2026-09-21_IDX_POLICY_EXTERNAL_GATE_LOG_V1.md`
- `2026-09-21_IDX_ROLLBACK_MATRIX_V1.md`
- `2026-09-21_IDX_ADOPTION_ACTIVE_FRONTIER_HANDOFF_V1.md`
- `2026-09-21_IDX_ADOPTION_NO_RETRY_LOG_V1.md`
- `2026-09-21_IDX_PHASE_5_13_REQUIREMENT_TRACEABILITY_V1.md`
- `2026-09-21_IDX_MULTI_SESSION_REHEARSAL_MATRIX_V1.md`
- `2026-09-21_IDX_AUTHORITATIVE_RUNTIME_ADOPTION_PACKET_V1.md`

## Required future authorization sequence

1. Review the lineage split and candidate base.
2. Review the clean extraction diff and provenance map.
3. Approve synthetic migration/replay only.
4. Review entrypoint/config compatibility and independent candidate challenge.
5. If all local gates pass, separately authorize a shadow-only operational
   rehearsal with explicit runtime and artifact roots.
6. Separately authorize any scheduler/cloud/source adoption; none is implied
   by this branch.
