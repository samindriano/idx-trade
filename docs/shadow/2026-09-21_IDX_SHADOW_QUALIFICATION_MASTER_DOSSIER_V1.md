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

## Root census snapshot

| Root | Files | Bytes | Interpretation |
|---|---:|---:|---|
| Active E2E runtime | 135 | 79,770 | operational metadata/logs; no paper-state population found |
| Forward monitoring | 819 | 63,136,721 | real session/model-input/EOD evidence corpus |
| Forward E2E source tree | 605 | 5,223,913 | source/tests, not a runtime state root |
| Pinned operational checkout | 569 | 4,838,475 | active source checkout, not a state root |

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
`forward_outcomes_accessed=false`.

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
| IMMUTABLE SHADOW INPUT | PASS WITH LIMITATION | 20 selected files copied to a new shadow root; source pre/post/copy hashes equal; paper-state class still absent |
| REAL MIGRATION | BLOCKED | No real migratable paper state, prepared artifact, pending ledger, or CA ledger found |
| HISTORICAL REPLAY | BLOCKED / INPUT+SCORE VALIDATION ONLY | Input validator passed for two sessions and real score passed via explicit shadow adapter; full paper-state/CA chain is absent and calendar lineage is inconsistent |
| OLD-vs-CANDIDATE EQUIVALENCE | BLOCKED REAL / PASS SYNTHETIC | Prior candidate tests only; no real artifact differential |
| CA COMPOSITION | BLOCKED REAL | No retained CA ledger/attestation admitted; provider was not accessed |
| RECOVERY | PASS SYNTHETIC / BLOCKED REAL | Recovery contracts were tested locally; no real chain was available |
| CONFIG LINEAGE | PASS WITH LIMITATION | Active config/task lineage observed read-only; candidate not operationally bound |
| SHADOW CONTINUATION | BLOCKED | No isolated runtime root was started |
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
rerun: 906 tests were collected, execution reached 100%, exit code was 0, and
the same three pre-existing pandas FutureWarnings remained.
