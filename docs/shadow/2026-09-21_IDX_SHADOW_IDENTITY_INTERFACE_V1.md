# IDX-Trade Shadow Identity Interface V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **IDENTITY INTERFACE SHADOW-READY / EXTERNAL AUTHORITY NOT ADMITTED**

## Active read-only identity

The active runtime config binds:

- expected branch `runtime/idx-e2e-baseline-paper-v1-pinned-20260824`;
- expected commit `32eaaa8e50d0521de7faef98faa8081219bc667b`;
- config SHA `fff7af72d7c761218385faadba11bb09408110c76b9fbaa43e121d5ec9bfb3e0`;
- dual-calendar contract `DUAL_CALENDAR_V1`;
- schedule-attestation SHA
  `6c81eb8457cbb5558339e08bd7a159fe700adbe441e287f56a99fb237e081a65`;
- runner SHA `ff560f13e696e1e3f9e101385e4e8134d375191baa78e55b067f6f824b968595`.

The config also names a CA attestation root and provider checkout. Those paths
were recorded as configuration references only; the provider checkout was not
read and no provider call was made.

## Candidate identity boundary

The prior candidate contract accepts a hash-pinned caller artifact and rejects
missing/conflicting lineage. It does not itself admit an authoritative real
identity artifact. This shadow packet therefore records `IDENTITY INTERFACE =
CONTRACT READY / AUTHORITY BLOCKED`.

No identity artifact was invented from session data, model data, discovery
metadata, or a provider path.

## Shadow artifact challenge

An explicitly labelled synthetic identity artifact was written and verified
only under:

`C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-operational-shadow\identity-interface\valid.json`

Its file SHA-256 is
`d129a74a8329f58b23bf942a6263dc532354cf9bdd776d23c3b5e31c41526d85`.
The loader accepted the hash-pinned file for `T00` at session
`2026-08-28`, with `outcome_access=false`.

The following cases were then challenged and all failed closed as required:

| Case | Result |
|---|---|
| valid hash-pinned artifact | accepted |
| missing ticker | rejected as `IDENTITY_EVIDENCE_ROW_INVALID` |
| conflicting interval/revision | rejected as unresolved required identity |
| wrong session | rejected as `IDENTITY_EVIDENCE_SESSION_MISMATCH` |
| wrong source file hash | rejected as `IDENTITY_EVIDENCE_FILE_SHA_MISMATCH` |
| extra/noncanonical field | rejected as `IDENTITY_EVIDENCE_PAYLOAD_NOT_CANONICAL` |

Challenge report:
`...\\identity-interface\\challenge_report.json`.

This establishes `IDENTITY INTERFACE = SHADOW-READY`; it does not establish
identity authority production-ready, and no external identity source was
read or promoted.
