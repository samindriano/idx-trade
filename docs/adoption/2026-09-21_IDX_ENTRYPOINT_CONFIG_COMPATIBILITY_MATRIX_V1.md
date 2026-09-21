# Entrypoint and Config Compatibility Matrix V1

Date: 2026-09-21

This is a static candidate interface inventory. It does not invoke a phase,
provider, scheduler, cloud runner, or live artifact.

| Surface | Current active source | Candidate source | Required binding | Current determination |
|---|---|---|---|---|
| POST_EOD V1 | pinned checkout 32, run_e2e_paper_post_eod_v1.py | same interface plus runtime-lineage/identity gates | runtime root, config path/SHA, parent identity, session date | STATIC AUDIT PENDING |
| POST_EOD V2 | pinned checkout 32, run_e2e_paper_post_eod_v2.py | hardened phase binding | config SHA, branch/commit, identity artifact, dual calendar | STATIC AUDIT PENDING |
| PREOPEN_CA | current orchestration schedule | candidate controller/orchestration | schedule attestation, session date, CA timing parent | STATIC AUDIT PENDING |
| PREOPEN V1 | pinned checkout 32, run_e2e_paper_preopen_v1.py | hardened phase binding | prepared parent, config SHA, identity evidence | STATIC AUDIT PENDING |
| PREOPEN V2 | pinned checkout 32, run_e2e_paper_preopen_v2.py | hardened phase binding | dual-calendar binding, prepared parent, config SHA | STATIC AUDIT PENDING |
| missed-Open continuity | operational controller/orchestration | candidate controller recovery | exact schedule-bound prepared parent; no late order creation | STATIC AUDIT PENDING |
| controller V1 | e2e_paper_operational_controller_v1.py | recovered phase/attempt boundary | durable boundary, recovery fence, runtime lineage | SYNTHETIC EVIDENCE ONLY |
| controller V2 | e2e_paper_operational_controller_v2.py | recovered dual-calendar controller | same plus dual calendar | SYNTHETIC EVIDENCE ONLY |
| runtime config | e2e_paper_runtime_config_v1.py | hash-pinned candidate config | config SHA, branch, commit, schedule, identity path/SHA | STATIC AUDIT PENDING |
| Official Open | active task delegates to pinned v2 runner | candidate v2 runtime | official authority, retry policy, evidence replay | BASE 402 EVIDENCE; candidate recheck pending |
| evidence health | not used as execution authority | forward_evidence_health_v1.py | outcome-blind paths and explicit guard flags | CANDIDATE DIAGNOSTIC ONLY |

## Required config fields

The candidate must reject missing, stale, or conflicting values for:

- runtime root and session identity;
- expected branch and commit;
- config file and SHA-256 sidecar;
- schedule/dual-calendar attestation and SHA;
- hash-pinned identity artifact and canonical payload hash;
- prepared parent and runtime-lineage hash;
- phase/trigger slot and exact session date;
- provider checkout identity where the operational interface requires it.

## External interface separation

Source adoption, runtime-config adoption, Task Scheduler adoption, and cloud
adoption are separate gates. A source branch cannot silently change any of
them. Current task evidence remains read-only and the active 32eaaa8e source
is not changed by this candidate.
