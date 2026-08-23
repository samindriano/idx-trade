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

## Branch-local handoff — 2026-08-23

- **Lane:** `integration/idx-e2e-baseline-paper-v1`
- **Status:** `REVIEW`
- **Result:** Cash-dividend V1.2 and restart/idempotency E2E remediation
  completed; deterministic core replay and production-path replay passed.
- **Boundary:** no provider calls, protected outcome access, model work, or
  scheduler mutation. Await independent review before operational continuation.
- **Checkpoint:** `docs/checkpoints/2026-08-23_CASH_DIVIDEND_E2E_REMEDIATION_RESULT.md`
- **Handoff:** `coordination/handoffs/IDX-CASH-DIVIDEND-E2E-REMEDIATION-RESULT.md`
