# Forward Evidence Health V1

Date: 2026-08-25 Asia/Jakarta
Branch: `fix/idx-forward-evidence-health-v1`
Parent reliability head: `839fa77b1e1c4bc6351679ef99d3e4bdd87689ab`
Final branch head: `3bef0060ffaf7a480d9a627c24d492340442bd99`
Integration base: `integration/idx-e2e-baseline-paper-v1@cb0f9f5680b608be16e4fd09999ae2da8991e4a4`

## Contract

The layer is an outcome-blind completeness/readiness diagnostic. It checks
declared artifact existence, SHA-256, session identity, selected safe manifest
fields, and explicit outcome-blind guard flags. It never loads parquet values,
labels, realized outcomes, protected vault content, or a protected loader.

Missing required evidence is `PENDING_EXPECTED`; it is never silently promoted
to `COMPLETE`. Hash/identity/guard failures are `PROVENANCE_INVALID`.

The safe rolling summary reports current session, forward-counter availability,
Stockbit status, Official Open status, Decision state, prepared-order state,
PaperState continuity, CA/dividend readiness, blockers, and next action. The
counter is reported as `NOT_READ` unless an explicitly safe caller supplies it.

## Known safe artifact graph

For a session the discovery path checks only:

- canonical EOD `manifest.json`;
- V4-X1 score `manifest.json`;
- Official Open manifest;
- Decision V2 result metadata;
- prepared order;
- execution result;
- PaperState snapshot;
- non-protected operational status metadata.

Paths whose components contain `outcome`, `label`, `realized`, or `vault` are
refused before reading. The report always includes
`PROTECTED_NOT_READ`, `accessed=false`, and `values_loaded=false`.

## Outcome-blind run against 2026-08-24

Inputs were existing external artifacts only:

- forward monitoring root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring`
- E2E runtime root:
  `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1`
- Stockbit summary:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\stockbit_intraday_recurring_v1\sessions\2026-08-24\final\run_summary.json`

Result: `PENDING_EXPECTED`.

- EOD manifest: `COMPLETE`
- V4-X1 score manifest: `COMPLETE`
- Stockbit: `COMPLETE_SHADOW`
- Official Open: `PENDING_EXPECTED` (no certified manifest after transport failure)
- Decision V2: `PENDING_EXPECTED`
- prepared order: `PENDING_EXPECTED`
- execution result: `PENDING_EXPECTED`
- PaperState: `PENDING_EXPECTED`
- CA/dividend state: `PENDING_EXPECTED`
- protected outcomes: not read

External report path:
`C:\Users\Sam\AppData\Local\Temp\idx-forward-health-20260824-final-936b6e5ca19748c187c35205f0a02566.json`

Report SHA-256:
`922163578e424c509981d39ce99e963b992e29be2a52ba4660884ee54f1a2560`

The result is intentionally not a prospective evaluation result and does not
change any model or counter.

## Validation

- focused health tests: 8 passed
- explicit outcome-access/guard hardening tests: 2 added; focused health tests: 10 passed
- full pytest: passed (760 tests, 3 pre-existing pandas FutureWarnings)
- py_compile: pass
- `git diff --check`: pass
- no provider call, model run, protected loader, outcome marker, or outcome
  value access
