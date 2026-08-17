# Handoff — V4 CA Event-Window Input-Pin Remediation

Branch: `data/idx-v4-ca-event-window-semantics-v1`
Parent failed run: `a281c91a313e8c4ed2ecd823e7f53ccf500ec5b4`
Status: `READY_FOR_LOCAL_REVALIDATION_AND_STAGE1`

## Before run

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md` and set only `V4 CA event-window semantics V1` to `ACTIVE`.
2. Pull latest branch. Do not edit source/config after Stage 1 exposes results.
3. `PYTHONPATH=src`.

## Validation

```text
python -m pytest tests/test_v4_ca_event_windows.py tests/test_v4_ca_schedule_semantics.py tests/test_v4_ca_schedule_dates.py tests/test_v4_ca_schedule_provenance.py tests/test_v4_ca_input_pin_remediation.py
```

```text
python -m py_compile src/idx_trade/v4_ca_event_windows.py src/idx_trade/v4_ca_schedule_semantics.py scripts/v4_ca_input_pin_remediation.py scripts/run_v4_ca_event_window_support.py scripts/run_v4_ca_event_window_support_pin_remediated.py scripts/run_v4_ca_schedule_acquisition.py scripts/run_v4_ca_schedule_acquisition_pin_remediated.py scripts/run_v4_ca_event_window_support_with_schedule.py scripts/run_v4_ca_event_window_support_with_schedule_pin_remediated.py
```

Then `git diff --check`. Any failure => STOP.

## Stage 1 — offline, corrected manifest pin

Use fresh output root `D:\Documents\Project\idx-v4-ca-event-window-static-20260818-v2`.

```text
python scripts/run_v4_ca_event_window_support_pin_remediated.py --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" --prior-event-evidence "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\event_family_evidence.csv" --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" --ksei-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" --output-dir "D:\Documents\Project\idx-v4-ca-event-window-static-20260818-v2"
```

If certified => no provider; promote small result artifacts, set REVIEW, push, STOP.
If blocked and schedule-required events = 0 => set REVIEW with blocker, push, STOP.
If blocked with schedule-required events > 0 => proceed unchanged to Stage 2.

## Stage 2 — targeted KSEI schedules only if required

Fresh root `D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v2`.

```text
python scripts/run_v4_ca_schedule_acquisition_pin_remediated.py --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" --ksei-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" --output-dir "D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v2"
```

No provider substitution, manual search insertion, manual retry, or code patch.

## Stage 3 — provenance-verified final gate

Fresh root `D:\Documents\Project\idx-v4-ca-event-window-final-20260818-v2`.

```text
python scripts/run_v4_ca_event_window_support_with_schedule_pin_remediated.py --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" --prior-event-evidence "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\event_family_evidence.csv" --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" --ksei-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" --schedule-root "D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v2" --output-dir "D:\Documents\Project\idx-v4-ca-event-window-final-20260818-v2"
```

STOP regardless of verdict. No target/model authorization is implied.

## Return

Return validation counts; Stage-1 verdict/event semantic counts/schedule-required counts/H5-H10-consensus gate dates + min rates; whether Stage 2 ran; if yes provider/linkage counts and manifest SHA; Stage-3 final verdict and continuity rates; final branch HEAD and clean/synced status.

Keep raw provider bytes/full ledgers external. Promote only small summaries/manifests/audits/per-date artifacts. Update only this lane to REVIEW and push.
