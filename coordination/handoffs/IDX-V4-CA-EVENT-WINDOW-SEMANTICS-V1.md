# Handoff — IDX-V4-CA-EVENT-WINDOW-SEMANTICS-V1

from: ChatGPT
to: local Windows execution operator
branch: `data/idx-v4-ca-event-window-semantics-v1`
branch checkpoint HEAD: `d7f0252c6ee7fc3e83fcb8383314aa130864ceff`
scientific/test code anchor: `2a1f18abfdf5bcc540ae179f475c349a628d7a74`
status: `READY_FOR_BOUNDED_LOCAL_STAGE1`

## Before execution

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md`.
2. Claim/update only a new row `V4 CA event-window semantics V1` as `ACTIVE`; do not modify unrelated rows.
3. Pull this branch. Verify the scientific/config/script/test files at current branch are byte-identical to code anchor `2a1f18ab...`; later commits are checkpoint/handoff only.
4. Set `PYTHONPATH=src`.
5. Do not edit source/config after Stage 1 exposes results.

## Exact local inputs

Blocked CA gate root:

`D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3`

- `v4_frozen_continuity_ledger.csv` SHA-256 `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`
- `event_family_evidence.csv` SHA-256 `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`

KSEI census root:

`D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1`

- `ksei_ca_history.jsonl` SHA-256 `3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d`
- existing manifest/summary/coverage hashes are pinned in code.

Official calendar:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv`

SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`.

Do not substitute SHA-different files.

## Validation gate

Run:

```text
python -m pytest tests/test_v4_ca_event_windows.py tests/test_v4_ca_schedule_semantics.py tests/test_v4_ca_schedule_dates.py tests/test_v4_ca_schedule_provenance.py
```

Then:

```text
python -m py_compile src/idx_trade/v4_ca_event_windows.py src/idx_trade/v4_ca_schedule_semantics.py scripts/run_v4_ca_event_window_support.py scripts/run_v4_ca_schedule_acquisition.py scripts/run_v4_ca_schedule_acquisition_hardened.py scripts/run_v4_ca_event_window_support_with_schedule.py
```

Then `git diff --check`.

Any failure => STOP. Do not patch in the same generation.

## Stage 1 — provider-free static exact event-window census

Fresh output root:

`D:\Documents\Project\idx-v4-ca-event-window-static-20260818-v1`

Run:

```text
python scripts/run_v4_ca_event_window_support.py --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" --prior-event-evidence "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\event_family_evidence.csv" --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" --ksei-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" --output-dir "D:\Documents\Project\idx-v4-ca-event-window-static-20260818-v1"
```

If verdict is `V4_CA_EVENT_WINDOW_CONTINUITY_CERTIFIED`, do **not** call KSEI. Promote small Stage-1 summary/manifest/event-semantics/schedule-needs/per-date artifacts, update lane to REVIEW, and STOP.

If blocked and `schedule_required_events == 0`, update lane to REVIEW with blocker and STOP.

If blocked with one or more schedule-required events, continue exactly to Stage 2. Do not alter semantics based on Stage-1 coverage.

## Stage 2 — targeted official KSEI schedule acquisition only

Fresh output root:

`D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v1`

Run only the hardened launcher:

```text
python scripts/run_v4_ca_schedule_acquisition_hardened.py --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" --ksei-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" --output-dir "D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v1"
```

No alternate provider, URL substitution, manual search result insertion, manual retries, or code patch. The frozen runner determines the KSEI month/category/document scope from immutable unresolved events.

## Stage 3 — provenance-verified final event-window gate

Fresh output root:

`D:\Documents\Project\idx-v4-ca-event-window-final-20260818-v1`

Run:

```text
python scripts/run_v4_ca_event_window_support_with_schedule.py --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" --prior-event-evidence "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\event_family_evidence.csv" --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" --ksei-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" --schedule-root "D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v1" --output-dir "D:\Documents\Project\idx-v4-ca-event-window-final-20260818-v1"
```

STOP regardless of final verdict. No target/model authorization is implied.

## Return

Return concise:

- branch final HEAD / clean-synced status;
- focused tests / py_compile / diff-check;
- Stage-1 verdict;
- Stage-1 exact-transition vs schedule-required event/ticker counts;
- Stage-1 H5/H10/consensus gate dates and minimum rates;
- whether Stage 2 was needed;
- if Stage 2 ran: index pages requested, candidate documents, parsed exact-transition docs, exact vs unresolved event links, provider failure counts, schedule manifest SHA;
- Stage-3 final verdict, H5/H10/consensus gate dates and minimum rates, continuity status/reason counts, `corporate_action_continuity_certified`;
- exact external output paths and promoted small-artifact hashes.

Promote only small summary/manifest/event audit/schedule-needs/linkage audit/schedule evidence/per-date artifacts. Keep raw HTML/PDF, request records, full history, and full continuity ledgers external.

Update only the new canonical TEAM_STATUS row to `REVIEW` with exact verdict/blocker, push, STOP.

## Hard prohibitions

No R5/R10, target ranks, model fit, predictions, IC, Top30, spread, bootstrap/raw-return performance, protected/fresh-forward outcomes, price-derived CA inference, V4 contract/gate changes, provider substitution, or post-Stage-1 semantic tuning.
