# IDX-Trade Shadow Runtime Active Frontier Handoff V1

Date: 2026-09-21

## Completed in this lane

- created isolated shadow worktree and branch from the prior adoption docs;
- preserved active runtime, scheduler, provider, cloud, alpha, and canonical
  data boundaries;
- read the prior adoption packet and synthetic evidence;
- audited active task identities read-only;
- inventoried the active E2E runtime and retained forward-monitoring roots;
- identified 29 retained session dates and selected real manifest hashes;
- separated real session/model evidence from absent paper-state evidence;
- created a 20-file immutable shadow copy with source/copy hash equality;
- validated both copied sessions at input level and validated the copied real
  score artifact through an explicitly labelled shadow adapter;
- ran a copy-only legacy ambiguity hunt: no duplicate required keys, required
  field nulls, invalid dates, model/OHLCV ticker differences, or model/OHLCV
  close differences; wider evidence/stock universe was recorded as a scope
  boundary;
- copied all 29 retained session packages plus calendar/provenance files into
  a second isolated discovery root; all 237 source/copy hashes matched;
- applied the input-level validator to all 29 copies: 27 passed, while the
  two explicit calendar-boundary failures remained fail-closed;
- ran the legacy ambiguity hunt across all 29 copied packages: zero duplicate,
  null/date, model/OHLCV set, close-value, or state-column anomalies; wider
  evidence/stock universe was recorded as an interface boundary;
- validated all 16 real V4-X1 score manifests through isolated adapters: 15
  clean candidate-id artifacts passed and one legacy model-id artifact was
  rejected fail-closed;
- searched 128 approved-root CSVs against all 23 embedded calendar hashes; only
  the current calendar matched, so the historical lineage blocker remains
  explicit;
- fixed and regression-tested one timezone-representation defect in the
  candidate verifier without changing alpha/science;
- recorded the V2 manifest, gap register, and canary design without executing
  migration, replay, fallback, canary, or production work.

## Next safe frontier

Only after separate authorization:

1. recover/admit the exact historical calendar bytes referenced by the 29
   session manifests, or preserve the affected sessions as NOT_REPLAYABLE;
2. locate an immutable paper-state/CA/recovery package in a separately
   authorized shadow input root, without provider/outcome access;
3. inspect candidate interfaces against admitted copies while preserving the
   explicit model-input/score universe boundary;
4. run only a bounded read-only replay if all lineage and interface gates are
   closed;
5. update the dossier with measured results or fail-closed blockers.

## Main ownership

MAIN retains integration, policy decisions, final verdicts, and any future
write/commit/push. Workers remain read-only observers. No live task or shared
coordination file is changed by this handoff.
