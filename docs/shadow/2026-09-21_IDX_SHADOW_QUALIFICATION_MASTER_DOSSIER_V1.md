# IDX-Trade Shadow Runtime and Pre-Canary Qualification Master Dossier V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **REAL-ARTIFACT DISCOVERY COMPLETE WITH LIMITATION / PRE-CANARY NO-GO**

## Objective

Qualify the authoritative-runtime adoption candidate against real retained
runtime evidence in an isolated, read-only-source shadow lane. The work is
fail-closed: synthetic candidate evidence is recorded separately from real
artifact evidence, and missing real state is not fabricated.

## Lane and source identity

| Item | Exact value |
|---|---|
| Shadow branch | `codex/idx-shadow-runtime-precanary-20260921` |
| Shadow worktree | `C:\Users\Sam\.codex\worktrees\idx-shadow-runtime-precanary-20260921` |
| Documentation base | `221e95640be73dd6f4887a27863ca93c2fd1b0d6` |
| Candidate code HEAD used by earlier tests | `66140b05872e60191ae4090811f168aaef6d71a7` |
| Candidate base | `402fca4b27e91cf8c82d21ff1394ba2d6da73656` |
| Shadow CA remediation commit | `5c14b036` (`NaN` optional-count handling; isolated lane only) |
| Active E2E task checkout | `32eaaa8e50d0521de7faef98faa8081219bc667b` |
| Active E2E runtime root | `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1` |
| Real forward-monitoring root | `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring` |

## Work actually performed

1. Read the user-provided shadow-runtime qualification specification.
2. Read the repository `AGENTS.md`, project status, and coordination status.
3. Created a separate shadow worktree/branch from the prior adoption packet.
4. Read the preceding adoption dossier and all companion adoption records.
5. Audited the active scheduled E2E-Paper and OfficialOpen task identities
   read-only.
6. Counted and inspected the bounded real runtime roots without writing to
   them.
7. Inspected the active runtime terminal metadata and two real session
   manifests plus EOD pipeline metadata.
8. Excluded synthetic pytest roots, Cloudflare handoff state, provider roots,
   protected outcomes, and counters from shadow inputs.
9. Prepared this documentation packet. No source artifact was copied into a
   shadow runtime and no migration/replay entrypoint was executed.
10. Ran a copy-only legacy ambiguity hunt over the two selected real sessions:
    required-key, null/date, ticker-set, and close-value checks were recorded
    without reading protected or live state.
11. Expanded the immutable discovery copy to all 29 retained session packages,
    plus current calendar files and calendar provenance attestations.
12. Applied the existing input-level validator to all 29 copied sessions.
13. Ran the legacy ambiguity hunt across all 29 copied session packages.
14. Validated all 16 real V4-X1 score manifests through isolated adapters:
    15 clean candidate-id artifacts passed and one legacy model-id artifact was
    rejected fail-closed.
15. Searched all 128 retained CSVs in the approved forward-monitoring root
    against the 23 distinct embedded calendar hashes; no historical embedded
    hash was recovered.
16. Performed a bounded metadata-only extension over the local E2E runtime,
    rollback-package, and operational-source surfaces; no additional retained
    paper-state root was found.
17. Ran one bounded synthetic continuation/recovery challenge in the isolated
    worktree: 86 selected contract tests passed with exit code 0; no retry was
    performed and no real runtime or retained state was touched.
18. Ran an independently constructed metadata/schema challenge against the
    immutable 29-session copy: all 29 child-hash sets and outcome-blind flags
    passed, no paper-state schema appeared, and the 28/29 calendar-lineage
    blocker was independently reproduced.
19. Extended the bounded discovery to retained parent-root evidence classes,
    then copied 32 files / 85,180,491 bytes into a separate shadow root: CA
    event registry, execution-anchor inputs, historical calendars, and
    Official Open archive metadata/logs. All source pre/post/copy hashes were
    equal; these classes were classified as input-only, not paper state.
20. Found and fixed a local candidate CA boundary defect: scalar `NaN`
    optional share counts in the copied canonical CA registry are now treated
    as unknown rather than invalid. The focused CA/attestation/dividend/V4-X1
    regression set passed 38/38, and the candidate parsed all 38 copied real
    CA rows without network access.
21. Ran a dedicated operationally-shaped shadow rehearsal in a new isolated
    output root: five synthetic continuation sessions passed with the exact
    rerun fence `ALREADY_COMPLETE`, the CA extension was exercised, and the
    controller persisted a weekend/holiday no-op against the copied
    516-session calendar. No provider, outcome, refit, rescore, live-runtime,
    or shared-state operation was performed.

## Root census snapshot

| Root | Files | Bytes | Interpretation |
|---|---:|---:|---|
| Active E2E runtime | 135 | 79,770 | operational metadata/logs; no paper-state population found |
| Forward monitoring | 819 | 63,136,721 | real session/model-input/EOD evidence corpus |
| Forward E2E source tree | 605 | 5,223,913 | source/tests, not a runtime state root |
| Pinned operational checkout | 569 | 4,838,475 | active source checkout, not a state root |

The extended parent-root evidence copy is separate from this census:

| Extended class | Files | Bytes | Interpretation |
|---|---:|---:|---|
| corporate actions | 6 | 25,332 | real event registry, not CA ledger |
| execution anchors | 5 | 85,032,239 | real input evidence, not fills/transactions |
| historical sessions/calendars | 12 | 118,860 | calendar input, not runtime binding |
| Official Open archive | 9 | 4,060 | capture metadata/logs, not execution state |
| **Total** | **32** | **85,180,491** | immutable shadow copy; no migration candidate |

The full per-file attestation and classification are in
`2026-09-21_IDX_EXTENDED_REAL_EVIDENCE_SHADOW_MANIFEST_V1.md`.

The retained Official Open archive is explicitly
`BLOCKED_SOURCE_NOT_FROZEN` with no selected provider module or network price
source; it cannot serve as an execution-grade state transition.

## Active runtime evidence

The active `IDXTrade-E2E-Paper` task was `Ready`, enabled, last-run result
`0`, with last run `2026-09-21T09:22:01+07:00`. Its action used the pinned
checkout and runtime-root config SHA
`fff7af72d7c761218385faadba11bb09408110c76b9fbaa43e121d5ec9bfb3e0`.

The retained terminal record says:

- controller contract: `DUAL_CALENDAR_V1`;
- controller status: `WAITING_PREPARED_EXECUTION`;
- execution session: `2026-09-21`;
- reason: `NO_PREPARED_EXECUTION_FOR_TODAY`;
- `outcome_access=false`, `provider_calls=false`, `model_refit=false`, and
  `model_rescore=false`.

The retained OfficialOpen record says the capture window was closed and did
not produce an execution-grade capture:
`AFTER_WINDOW_NO_EXECUTION_GRADE`.

This is evidence of an ordinary no-prepared-execution terminal path. It is not
evidence that a paper state, pending row, execution artifact, or CA ledger
exists elsewhere.

## Real forward-monitoring evidence

The forward-monitoring root has 29 retained session-date directories from
`2026-08-03` through `2026-09-18`. The selected `2026-09-16` and
`2026-09-17` manifests both report `DATA_READY`, `outcome_blind=true`, and
`forward_outcomes_accessed=false`. The complete 29-session copy and its
expanded lineage results are recorded in
`2026-09-21_IDX_FULL_SESSION_SHADOW_CENSUS_V1.md`.
The per-file source/copy hash attestation is recorded in
`2026-09-21_IDX_FULL_SESSION_COPY_ATTESTATION_V1.md`.

Selected session facts:

| Session | Listed | Model rows | Session OHLCV SHA-256 | Model-input SHA-256 | Evidence SHA-256 |
|---|---:|---:|---|---|---|
| 2026-09-16 | 963 | 828 | `6d5b5b2977928835aa50a0fcf7a36a5910e58e46db9223ad4ae505f747aa4860` | `f5d39e7ee642f376ee9b50949a4fe77adfceda607eb436e304592e538fb3efde` | `aa86b96e88311891acfe6f48bf3190344ff4ead0caf231a32119b4eb08549639` |
| 2026-09-17 | 963 | 831 | `4481137b79086db1d8249806d5f575fe7a461849b693edcce8f87a9eafabf433` | `f7bdebb038d110425225311b0fa99122370d4b6ac2076ee6d3a3d129025be4e8` | `09a9318ccb585f7ad8f7fcc327bf578ee8bebe0d4aad88120555a09466e8a026` |

These are eligible candidates for a separately authorized historical-input
replay only if the candidate interface can consume them without inventing
paper state, CA authority, identity authority, or outcomes. They are not
equivalent to E2E paper-state migration inputs.

## Gate verdicts

| Required gate | Verdict | Evidence boundary |
|---|---|---|
| REAL ARTIFACT DISCOVERY | PASS WITH LIMITATION | Real roots/corpus found; eligible paper-state population absent in bounded census |
| IMMUTABLE SHADOW INPUT | PASS WITH LIMITATION | 20-file validation package, 237-file discovery copy, and 32-file extended evidence copy are hash-attested; paper-state class still absent |
| REAL MIGRATION | BLOCKED | No real migratable paper state, prepared artifact, pending ledger, or CA ledger found |
| HISTORICAL REPLAY | BLOCKED / INPUT+SCORE VALIDATION ONLY | Input validator passed for 27/29 copied sessions and the V4-X1 score verifier passed 15/16 real manifests; two boundary failures, 28/29 calendar mismatches, absent paper-state/CA chain, and one legacy model-id rejection remain explicit |
| OLD-vs-CANDIDATE EQUIVALENCE | BLOCKED REAL / PASS SYNTHETIC | Prior candidate tests only; no real artifact differential |
| CA COMPOSITION | BLOCKED REAL | The real CA event registry now passes the isolated parser boundary, but no retained entitlement/settlement ledger or holdings/obligation chain exists; provider was not accessed |
| RECOVERY | PASS SYNTHETIC / BLOCKED REAL | Recovery contracts were tested locally; no real chain was available |
| CONFIG LINEAGE | PASS WITH LIMITATION | Active config/task lineage observed read-only; historical manifests omit runtime identity and the extended execution summary retains a `20260808u` cache path under a `20260808v` source root |
| SHADOW CONTINUATION | PASS SYNTHETIC / BLOCKED REAL | 86 contract tests plus a dedicated five-session operational shadow rehearsal passed; no real operational state was admitted |
| FORWARD FALLBACK | DESIGN ONLY | Fallback design exists; real rehearsal was not run |
| IDENTITY INTERFACE | CONTRACT READY / AUTHORITY BLOCKED | Candidate accepts hash-pinned artifact shape; authority is not admitted |
| PRE-CANARY READINESS | NO-GO | Real migration/replay/CA/recovery evidence is missing |
| CONTROLLED CANARY | NO-GO / NOT EXECUTED | No canary was authorized or started |
| PRODUCTION | NO-GO | Explicitly outside this lane |

## Earlier candidate work retained in this branch

The prior adoption packet remains the source for synthetic implementation
evidence: full candidate suite `905/905`, selected rehearsal `29 passed`,
migration compatibility `11/11`, shadow migration/reload/fence `2/2`, and
entrypoint/config/scheduler focus `111` plus synthetic OfficialOpen focus
`16`. Those results remain **synthetic/local only** and do not upgrade any
blocked real gate above.

## Final interpretation

The current evidence supports a real-artifact discovery result with a hard
boundary: real forward-monitoring inputs exist, while the retained E2E paper
state required for migration/recovery/old-vs-new differential is absent from
the bounded inventory. The next safe action is to reconcile the historical
calendar/path lineage and locate the missing paper-state/CA chain inside a
separate authorized shadow package; it is not to run against the active
writable runtime.

## Actual immutable copy

The selected input class is now cryptographically copied into
C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921. The
V2 manifest records 20 files and 750,681 bytes with source hash before copy,
source hash after copy, and copy hash equal for every file. The copy is not
treated as paper state: no paper portfolio, prepared execution, fill vector,
pending ledger, or CA ledger was present in this admitted class.

The copied class now also contains one real schedule attestation and one real
score manifest plus score artifact. The score manifest still embeds an
absolute source artifact path, so it is retained for lineage review but not
loaded from the shadow root without a separately labelled adapter.

The separately labelled score adapter exposed and enabled repair of one local
candidate defect: raw string comparison rejected equivalent timezone
representations of the freeze boundary. The isolated verifier now compares
timezone-aware instants while still rejecting naive or different timestamps.
Focused verifier/property tests passed 26/26, and the real 2026-09-17 score
artifact validated at 296 rows. This does not open the paper-state replay gate.

The copy-only schema census found 11/13 embedded hash checks passing: the
session child artifacts and config sidecar matched, but both manifests'
calendar_sha256 values do not match the currently referenced calendar file.
That calendar lineage mismatch is recorded as REQUIRES_RECONCILIATION and
blocks replay of these sessions.

The expanded 29-session copy found 28/29 calendar hash mismatches; the sole
matching 2026-09-18 session still cannot pass the next-session boundary because
the copied current calendar ends there. The existing input-level validator was
applied to all 29 copies: 27 returned `PASS_INPUT_LEVEL`; 2026-08-03 failed
because it is not an official session in the copied current calendar; and
2026-09-18 failed because no next official session is available. These are
structural observations only and do not establish paper-state, CA, recovery,
or economic replay.

The all-session ambiguity hunt found zero duplicate required keys, required
field nulls, invalid dates, model/OHLCV ticker-set mismatches, model/OHLCV
close mismatches, or state-like columns across the checked session families.
Evidence and stock summaries contain wider-universe rows in every session;
the exact counts and scope interpretation are recorded in
`2026-09-21_IDX_ALL_SESSION_LEGACY_AMBIGUITY_HUNT_V1.md`.

The all-manifest V4-X1 score validation passed 15 clean candidate-id artifacts
and rejected one legacy `V4_X1_GEOMETRY3_PROSPECTIVE` model-id artifact. The
result is recorded in `2026-09-21_IDX_ALL_V4X1_SCORE_VALIDATION_V1.md` and is
still score-level evidence, not historical E2E replay.

The calendar reconciliation searched 143 CSVs across the approved root and
bounded sibling evidence roots and found only the current calendar hash,
matching 2026-09-18. None of the 22 distinct historical embedded hashes was
recovered. The exact result is recorded in
`2026-09-21_IDX_CALENDAR_LINEAGE_RECONCILIATION_V1.md`.

The independent Phase 18 challenge is recorded in
`2026-09-21_IDX_INDEPENDENT_REAL_ARTIFACT_SHADOW_CHALLENGE_V1.md`. It found no
new material locally fixable defect and did not upgrade any real gate. It also
confirmed that none of the 29 session manifests carries a runtime/config/
checkout identity field, so historical identity remains missing rather than
inferable.

The real CA interface remediation and its focused regression evidence are
recorded in `2026-09-21_IDX_REAL_CA_INTERFACE_REMEDIATION_V1.md`. The local
shape defect is closed in the shadow candidate; it does not upgrade real CA
composition or pre-canary readiness.

The copy-only legacy ambiguity hunt found no duplicate required keys, required
field nulls, invalid session dates, model/OHLCV ticker-set differences, or
model/OHLCV close-value differences for 2026-09-16 and 2026-09-17. Evidence
and stock-summary files contain the wider retained listed universe: 135 and
132 extra non-model rows respectively. That is recorded as a scope distinction
in 2026-09-21_IDX_REAL_LEGACY_AMBIGUITY_HUNT_V1.md, not promoted to a paper
state or duplicate-state finding. The calendar mismatch and missing paper/
CA/recovery artifacts remain open.

## Final-format evidence metrics

These metrics distinguish the approved-root inventory from the admitted
immutable copy and distinguish absent candidates from failed migration runs.

| Requested metric | Measured result |
|---|---|
| Real source artifact count | 819 files / 63,136,721 bytes in the approved forward-monitoring root; 817 files / 63,005,440 bytes after excluding the protected counter surfaces |
| Immutable shadow artifact count | 237 files / 27,907,223 bytes in the session discovery copy, plus a separate 32-file / 85,180,491-byte extended evidence copy; all admitted copy hashes equal |
| Real paper-state artifacts located | 0 snapshots, prepared parents, fill vectors, pending ledgers, CA ledgers, or recovery chains in the bounded admitted inventory; 38 CA event rows and 479,471 execution anchors are input-only |
| Real migration attempted | 0; fail-closed because no eligible paper-state candidate exists |
| Migrated real artifacts | 0 |
| Blocked real migration candidates | 0 artifact rows; the required paper-state classes are unavailable rather than individually rejected |
| Historical sessions | 29 retained session packages; 27 input-level passes, 2 current-calendar boundary failures |
| Fully replayable historical sessions | 0; full E2E replay is blocked by state/CA/recovery absence and calendar lineage |
| Calendar binding | 1/29 matches current calendar; 28/29 historical hashes unresolved; the matching session still has no next official session in the copy |
| Old-vs-candidate real differential | 0 real artifact pairs; no unexplained divergence can be measured without a pair |
| Real recovery cases | 0; no real snapshot chain, fork, parent, or obligation ancestor admitted |
| Synthetic recovery/continuation evidence | 86/86 selected contract tests passed; synthetic-only |
| Post-remediation focused regression | 38/38 CA/attestation/dividend/V4-X1 tests passed; pinned full suite passed 907/907 |
| Operational shadow rehearsal | 72 files / 788,621 bytes; five synthetic sessions; controller persisted `WEEKEND_OR_HOLIDAY_NOOP`; no provider/outcome/refit/rescore |
| Forward fallback | 0 real rehearsals; design recorded only |
| External blockers | historical calendar authority, real paper-state/CA/recovery package, historical runtime/config identity, identity authority, policy decisions, and separate canary authorization |
| Canary design | `2026-09-21_IDX_CONTROLLED_CANARY_DESIGN_V1.md`; design only, not executed |
| Worktree state | clean isolated branch; active operational checkout and runtime were not modified |

## Inherited documentation audit

The inherited adoption packet is linked for history, but it contains
documentation/provenance limitations recorded in
2026-09-21_IDX_ADOPTION_DOCUMENTATION_AUDIT_V1.md: inherited branch identity
is not the current shadow identity, the active E2E action path needed repair,
the Markdown/JSON surface matrices are not one-for-one, the challenge was
MAIN-run rather than an external independent review, and exact test
reproduction artifacts were not included. The current shadow records retain
these as explicit limitations instead of silently upgrading them.

After the real-artifact timestamp finding, the shadow candidate suite was
rereun: 906 tests were collected before the NaN remediation, execution reached
100%, exit code was 0, and the same three pre-existing pandas FutureWarnings
remained. After the remediation, the correctly source-pinned full suite
collected and passed 907/907 tests with those same three warnings. A later bounded
continuation/recovery challenge selected 86 relevant contract tests and
recorded 86 passes; its exact command and scope are in
`2026-09-21_IDX_SYNTHETIC_CONTINUATION_CHALLENGE_V1.md`.
