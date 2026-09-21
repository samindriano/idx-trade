# IDX-Trade Shadow Runtime Phase Coverage Audit V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **COMPLETE COVERAGE RECORD / QUALIFICATION NOT COMPLETE**

This is a requirement-by-requirement audit of the Phase 0–18 specification.
It is deliberately not a completion certificate: a phase can have a durable
record while its real-state gate remains blocked. Synthetic evidence is never
promoted to real-artifact evidence.

## Audit identity

| Item | Value |
|---|---|
| Shadow branch | `codex/idx-shadow-runtime-precanary-20260921` |
| Evidence baseline HEAD before this audit commit | `94919f980e72c6467506ca34e8506b825eba52b8` |
| Candidate revision used by earlier adoption tests | `66140b05872e60191ae4090811f168aaef6d71a7` |
| Current shadow candidate revision under review | `5c14b036ee179532903e1d0fd32d486db06cf3c7` |
| Candidate base | `402fca4b27e91cf8c82d21ff1394ba2d6da73656` |
| Active operational checkout | `32eaaa8e50d0521de7faef98faa8081219bc667b` |
| Active E2E runtime census revalidation | 135 files / 79,770 bytes; zero state-like filenames in the read-only check |
| Qualification boundary | isolated shadow only; no live/provider/cloud/outcome/scheduler/alpha mutation |

## Phase coverage

| Phase | Required outcome | Current evidence | Verdict |
|---:|---|---|---|
| 0 | Recover controlling adoption evidence and exact identities | Adoption packet audit, master dossier, runtime/config/task identity records, and current lane identity | PASS WITH LIMITATION |
| 1 | Locate real retained runtime evidence without modifying sources | Real runtime census plus extended 32-file parent-root evidence manifest; real inputs found, paper-state classes absent | PASS WITH LIMITATION |
| 2 | Build immutable manifest with source/copy hash equality | V2 manifest, 237-file full-session copy attestation, and 32-file extended evidence attestation | PASS WITH LIMITATION |
| 3 | Census actual state population before migration | Classification registry records zero snapshots/prepared parents/fill vectors/pending ledgers/CA ledgers and separates input-only classes | PASS WITH LIMITATION |
| 4 | Apply migration classifier to real copied population | Full census classifies all located classes as input-only/unavailable; representative objects from all seven observed real input classes were rejected at the exact canonical-envelope admission boundary; no permissive class invented | BLOCKED BY ABSENT STATE |
| 5 | Migrate and reload eligible real state | No eligible real state artifact exists; no migration was attempted or fabricated | BLOCKED |
| 6 | Replay historical sessions where all inputs exist | 29 packages input-validated (27 input-level passes, 2 boundary failures); calendar lineage and paper-state/CA chain block E2E replay | BLOCKED / INPUT-LEVEL ONLY |
| 7 | Old-runtime versus candidate differential on identical real artifacts | Differential record confirms no real state pair; candidate-only synthetic evidence retained separately | BLOCKED REAL / PASS SYNTHETIC |
| 8 | Hunt real legacy ambiguity cases | All-29 ambiguity hunt and independent challenge: no duplicate/null/date/ticker/close/state-column anomaly; identity/calendar gaps remain explicit | PASS WITH LIMITATION |
| 9 | Compose real CA entitlement/receivable/payment/cash/position/obligation/restart | 38 real CA event rows parse after isolated NaN remediation; no real holdings/obligation/entitlement/settlement chain exists | BLOCKED REAL / PASS INTERFACE |
| 10 | Recover from real snapshot chains | Synthetic recovery contracts pass; no real ancestor/fork/pending-obligation chain exists in admitted evidence | PASS SYNTHETIC / BLOCKED REAL |
| 11 | Compare historical config/runner/checkout lineage | Active task identity is observed; historical manifests lack runtime/config identity and one execution path has a `20260808u`/`20260808v` mismatch | PASS WITH LIMITATION |
| 12 | Construct and execute isolated operational shadow root | Dedicated root contains continuation/controller/fallback/identity outputs; 89-file two-pass attestation, five-session continuation, and weekend/holiday controller no-op completed without side effects | PASS SYNTHETIC / BLOCKED REAL |
| 13 | Continue from migrated real state across multiple sessions | Five synthetic sessions exercise continuation, CA, exact rerun, pending-buy/missed-Open recovery; no real migrated starting state exists | PASS SYNTHETIC / BLOCKED REAL |
| 14 | Rehearse forward-only fallback | Dedicated `fallback-v3` rehearsal freezes V2, fences new execution, injects failure, marks repair, and resumes same V2 state; no V1 downgrade | PASS SYNTHETIC / BLOCKED REAL |
| 15 | Challenge shadow identity artifact interface | Valid hash-pinned artifact accepted; missing ticker, conflict, wrong session/hash, and extra field rejected; authority not admitted | PASS SHADOW / AUTHORITY BLOCKED |
| 16 | Enumerate exact pre-canary blockers and owners/evidence | Gap register separates source, state, identity, policy, config, scheduler, provider, recovery, rollback, and observability blockers, with authority role, local help, and canary-dependency metadata for every gap | PASS |
| 17 | Design but do not execute controlled canary | Controlled-canary design explicitly records all 13 required fields, with real state/production identity/session window marked `UNSET` fail-closed; it remains unexecuted | DESIGN COMPLETE / NO-GO |
| 18 | Fresh independent real-artifact challenge | Independent 29-session hash/schema/calendar challenge completed; no new locally fixable real-state defect found | PASS WITH LIMITATION |

### Phase 16 category coverage

The required blocker categories are explicitly represented in the gap
register: SOURCE (`G-02`, `G-13`, `G-14`, `G-17`), STATE (`G-01`, `G-03`,
`G-04`), IDENTITY AUTHORITY (`G-07`), POLICY (`G-09`), CONFIG (`G-10`,
`G-14`), SCHEDULER (`G-19`), PROVIDER (`G-20`), RECOVERY (`G-06`), ROLLBACK
(`G-08`), and OBSERVABILITY (`G-21`). Cross-cutting review/evidence gaps are
also retained in `G-05`, `G-11`, `G-12`, `G-15`, and `G-16`.

## Durable-output coverage

All twelve durable outputs named by the specification are present in
`docs/shadow` at this audit HEAD:

| # | Output | File | Present |
|---:|---|---|---|
| 1 | Shadow qualification master dossier | `2026-09-21_IDX_SHADOW_QUALIFICATION_MASTER_DOSSIER_V1.md` | YES |
| 2 | Immutable input manifest | `2026-09-21_IDX_IMMUTABLE_SHADOW_INPUT_MANIFEST_V2.md` | YES |
| 3 | Real artifact census | `2026-09-21_IDX_REAL_RUNTIME_ARTIFACT_CENSUS_V1.md` | YES |
| 4 | Real migration classification registry | `2026-09-21_IDX_REAL_MIGRATION_CLASSIFICATION_REGISTRY_V1.md` | YES |
| 5 | Old-vs-candidate differential matrix | `2026-09-21_IDX_OLD_CANDIDATE_DIFFERENTIAL_V1.md` | YES |
| 6 | Real replay matrix | `2026-09-21_IDX_REAL_REPLAY_MATRIX_V1.md` | YES |
| 7 | Shadow recovery matrix | `2026-09-21_IDX_SHADOW_RECOVERY_MATRIX_V1.md` | YES |
| 8 | Forward-only fallback rehearsal | `2026-09-21_IDX_FORWARD_FALLBACK_REHEARSAL_V1.md` | YES |
| 9 | Pre-canary gap register | `2026-09-21_IDX_PRECANARY_GAP_REGISTER_V1.md` | YES |
| 10 | Controlled-canary design | `2026-09-21_IDX_CONTROLLED_CANARY_DESIGN_V1.md` | YES |
| 11 | Active frontier handoff | `2026-09-21_IDX_SHADOW_ACTIVE_FRONTIER_HANDOFF_V1.md` | YES |
| 12 | No-retry log | `2026-09-21_IDX_SHADOW_NO_RETRY_LOG_V1.md` | YES |

Supporting records include the full-session census and copy attestation, all
session ambiguity hunt, calendar reconciliation, extended real-evidence
manifest, CA parser remediation, deterministic real CA/recovery gate audit,
operational-shadow rehearsal, immutable-attestation revalidation, state-name
ambiguity audit, real-classifier admission audit, identity interface
challenge, current validation ledger, parent-root boundary census, and
independent Phase 18 challenge.

## Stop-rule audit

| Stop-rule item | Evidence status |
|---:|---|
| 1. Accessible local real inventory complete | PASS WITH LIMITATION; bounded retained roots were inventoried; cloud/provider/protected surfaces remain outside scope |
| 2. Real artifacts copied immutably | PASS WITH LIMITATION; admitted input classes are hash-attested, but no paper-state class exists |
| 3. Classifier applied to real population | PASS WITH LIMITATION; all located classes classified as input-only/unavailable |
| 4. Migratable real state migrated/reloaded | NOT ACHIEVED; no eligible state artifact |
| 5. Old/candidate differences classified | NOT ACHIEVED FOR REAL STATE; synthetic matrix only |
| 6. Historical replay attempted wherever evidence permits | PASS WITH LIMITATION; input-level checks ran, E2E replay is not permitted without calendar/state chain |
| 7. Real CA/restart/recovery challenged | NOT ACHIEVED FOR REAL STATE; interface/synthetic challenges only |
| 8. Forward-only fallback rehearsed | PASS SYNTHETIC; real-state fallback remains unproven |
| 9. No material locally fixable defect remains | PASS for discovered local parser/verifier defects; external evidence gaps remain |
| 10. Remaining canary blockers explicit | PASS; see gap register |
| 11. Canary design exists and is unexecuted | PASS |

## Completion decision

The documentation and synthetic qualification surfaces are covered, but the
primary objective is not complete. The decisive missing evidence remains a
separately authorized immutable real E2E paper-state package containing
runtime snapshots, prepared/execution lineage, CA obligation/settlement
state, and recovery ancestors. The 28/29 unresolved historical calendar
bindings and external identity/policy authority are independent blockers.

Therefore:

`PRE-CANARY READINESS = NO-GO`

No goal-complete claim is made from this audit, and no live or external action
is justified by the synthetic PASS results.
