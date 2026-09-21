# IDX-Trade Shadow Identity Interface V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **CONTRACT READY / EXTERNAL AUTHORITY NOT ADMITTED**

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
