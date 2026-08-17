# V4 CA Event-Window Semantics V1 — Final Preflight Freeze

Date: 2026-08-18 (Asia/Jakarta)
Branch: `data/idx-v4-ca-event-window-semantics-v1`
Final scientific/test code anchor before any new local or provider run: `2a1f18abfdf5bcc540ae179f475c349a628d7a74`
Parent: `data/idx-v4-ksei-ca-history-census-v1@aef9037240849a3bba0b16838f3827e389ce9711`
Status: `FINAL_PREFLIGHT_FROZEN_AWAIT_LOCAL_OFFLINE_STAGE1`

This checkpoint supersedes the earlier code-anchor field only; the scientific contract in the preregistration remains unchanged.

Parent-to-anchor comparison is additive only for this lane: config, event semantics, exact schedule parser/acquisition, support runners, tests, and checkpoints. No V4 target, learner, evaluator, folds, thresholds, historical returns, or model files were modified.

Execution order is frozen:

1. focused tests + py_compile + diff-check;
2. provider-free static-exact event-window support run;
3. if and only if Stage 1 remains blocked, targeted KSEI schedule acquisition through `run_v4_ca_schedule_acquisition_hardened.py`;
4. provenance-verified final event-window support run through `run_v4_ca_event_window_support_with_schedule.py`;
5. STOP for independent review regardless of verdict.

No source/config patch after Stage 1 results is authorized in this generation.
