# V4 CA Event-Window Semantics V1 — Final Result

Date: 2026-08-18 Asia/Jakarta  
Branch: `data/idx-v4-ca-event-window-semantics-v1`  
Execution HEAD: `8affe6d6024109b438f4d9d4b55e43759c4f8b71`  
Parser/input-pin remediation lineage: `beed2e205d4829eb8eac8085c839dce320043a8a`

## Scope and boundary

The frozen Stage 1 result was reused unchanged. Stage 1 was not rerun. Stage 2
used only the hardened official KSEI schedule launcher, and Stage 3 used the
frozen semantics with the Stage 2 schedule evidence. No source/configuration,
event semantics, provider substitution, retry policy, threshold, V4 target,
model, prediction, protected outcome, or fresh-forward artifact was changed or
accessed.

## Validation

- Focused validation: `21 passed`.
- Required `py_compile`: PASS.
- `git diff --check`: PASS.

## Immutable Stage 1 result

External root:
`D:\Documents\Project\idx-v4-ca-event-window-static-20260818-v2`

- Verdict: `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`.
- Frozen rows/tickers/dates: `344,790 / 610 / 600`.
- Relevant event rows: `136`.
- Exact transitions: `41`.
- Schedule-required events/tickers: `95 / 75`.
- H5/H10/consensus passing dates: `0 / 0 / 0`.
- H5/H10/consensus minimum rate: `0.7588075881 / 0.7588075881 / 0.7588075881`.
- `corporate_action_continuity_certified=false`.
- Output hashes: event semantics `ba08fbdab5b72b377888320163ba8b893e7d1a19f69384ba7be0fdac5ca33908`; schedule needs `6de55e202c1b3f0795f1b09c5de55af33e136766ee47fe21af29c2b214110c50`; per-date `eefd6cbeed7381b01935a95b777cd88cfa4e073c0abc7d318005c2bc381fd85d`; continuity diagnostic `12f80f3f26083cf8bacedd0016284b7432711461006336bb55da5a4206b385ff`.

## Stage 2 — targeted KSEI schedule acquisition

External root:
`D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v3`

- Status: `V4_CA_TARGETED_KSEI_SCHEDULE_ACQUISITION_COMPLETE`.
- Index pages requested: `77`.
- Candidate documents: `100`.
- Parsed exact-transition documents: `1`.
- Exact event links: `1`.
- Unresolved event links: `94`.
- Schedule-required events/tickers: `95 / 75`.
- Provider: official KSEI launcher only; `source_substitution=false`.
- Schedule manifest SHA: `5073adb3178a90e71ea9105ddb6ff737896e86a709d1998eefbdb14ca12b6f8c`.
- Schedule evidence SHA: `c9f396951ae82f2526c6e7943bff2ed359aa488697d3086f1afdb64127e8d3b4`.
- Linkage audit SHA: `e0aa6880035e78396c992b443f73389123dc130df61570fdad1de331f37c7006`.
- Parse audit SHA: `d7ded2bf29ad8355ff7ce22af89004a4bbe7e7fd0bb01524f582be2ad1e4e796`.
- Request records and raw HTML/PDF remain external.

## Stage 3 — final event-window gate

External root:
`D:\Documents\Project\idx-v4-ca-event-window-final-20260818-v3`

- Verdict: `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`.
- Frozen rows/tickers/dates: `344,790 / 610 / 600`.
- Relevant event rows: `136`.
- Exact transitions: `42`.
- Schedule-required events/tickers: `94 / 74`.
- H5/H10/consensus passing dates: `0 / 0 / 0`.
- H5/H10/consensus minimum rate: `0.7596153846 / 0.7596153846 / 0.7596153846`.
- Continuity statuses: resolved no mechanical discontinuity `273,713`; unresolved coverage `29,084`; unresolved effective date `41,993`.
- `corporate_action_continuity_certified=false`.
- Final manifest SHA: `c635ee354c923eebdb586bc4d82a6693d230e1a347df50879dda4c1f5f56bff4`.
- Final event semantics SHA: `6d750de249396667775a4b9da55a7d7458b65a845427cd2bbfa9dd5fe66765ff`.
- Final schedule-needs SHA: `441253ec7a40a789eac00b4dd4159fc9470c6e4dcab23cd7c2c20bc9596cffed`.
- Final per-date SHA: `96a77f22691c1cd736c5e21ce40ac3d67501a4494cb140e1f8c46aa606672558`.
- Final continuity diagnostic SHA: `0c48aa4d12a66241378e1b95e2f51615b5ca3469a4c63692c5d9e7b8818a337f`.

## Promoted small artifacts

Small manifests, summaries, audits, and per-date outputs are under:

- `docs/artifacts/v4_ca_event_window_static_20260818_v2/`
- `docs/artifacts/v4_ca_schedule_evidence_20260818_v3/`
- `docs/artifacts/v4_ca_event_window_final_20260818_v3/`

The full continuity ledger, raw request records, raw HTML/PDF, and other large
provider artifacts remain external.

## Decision

The final continuity gate remains blocked. No V4 target/model execution is
authorized by this result. Lane status: `REVIEW`.
