# IDX Trade V0 status

Only MAIN may edit this file.

- **Phase:** `BOOTSTRAP_COORDINATION`
- **Operating mode:** `EXPLORATORY_RESEARCH_ONLY`
- **Integration branch:** `main`
- **Current working branch:** `codex/idx-trade-orchestrator`
- **Market / venue:** `IDX listed equities / REGULAR / daily-EOD`
- **Data foundation:** `PRESENT_IN_REPOSITORY; RESEARCH_GATE_NOT_PASSED`
- **Research source approval:** `NOT_APPROVED_FOR_PIT_EVALUATION`
- **Training / prediction / monitoring / trading:** `DISABLED`
- **Active tasks:** `IDX-EXP-001`, `IDX-VAL-001`, `IDX-DATA-001`, `IDX-PROD-001`
- **Web task:** `NOT_STARTED; NO_ACTIVE_WEB_SCOPE`
- **Blocked:** no model or trading phase until the target, horizon, benchmark,
  point-in-time universe, source lineage, session protocol, and data-readiness
  gate are frozen and approved.
- **Completed handoffs:** none
- **Next integration action:** MAIN reviews the initial handoffs, reconciles
  the existing data-foundation contracts with the frozen research
  specification, and records a GO/NO-GO decision before any new data or model
  work.

## Current status correction — 2026-08-21 — Stockbit/EOD recovery validation

The Stockbit intraday post-close gate remediation is complete on
`fix/stockbit-intraday-postclose-v1` at `1ca285c36c4fb34233e22bd2cf222308d1b55e0c`.
The existing EOD catch-up path restored official `DATA_READY` sessions for
2026-08-20 and 2026-08-21. Clean V4-X1 prospective scoring completed once for
2026-08-21 with the official model-run state `DONE` and counter progress 1/100;
protected/fresh-forward outcomes remain untouched. The same-day Stockbit
capture for 2026-08-21 completed with 962 attempted, 832 successful, 103,231
normalized points, and zero retries/HTTP 429s by reusing the verified EOD
Stock Summary. The 2026-08-20 intraday-only session remains unavailable after
provider rollover and was not synthesized. No Corporate Action scheduler or
capture path exists; that lane remains manual/static and is not represented as
automated. Focused tests, full pytest, py_compile, and diff-check passed before
the controlled runtime validation. This branch is awaiting MAIN integration
and independent review.
