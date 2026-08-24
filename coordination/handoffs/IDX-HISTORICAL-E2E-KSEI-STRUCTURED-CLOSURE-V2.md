# Handoff

from: PRIMARY IMPLEMENTER + KSEI/STRUCTURED SOURCE AUDITORS  
to: MAIN / independent reviewer  
task_id: IDX-HISTORICAL-E2E-KSEI-STRUCTURED-CLOSURE-V2  
model_used: Codex + Orchestra read-only explorers  
reasoning_level: xhigh  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: `44f5d2e018c706bccda5d2dbc453b15a4de4d799`  
branch: `research/idx-historical-e2e-replay-v1`  
head_commit: `44f5d2e018c706bccda5d2dbc453b15a4de4d799`

## scope

Complete the bounded KSEI + structured IDX/Zapi feasibility closure for the
historical true-E2E replay lane. Reuse existing immutable captures, validate
positive controls, rerun the outcome-blind strict scope freeze, and stop
before replay/performance unless a non-empty strict scope is proven.

## files_changed

- `docs/checkpoints/2026-08-24_HISTORICAL_E2E_KSEI_STRUCTURED_CLOSURE_V2.md`
- this handoff

No source, runtime, model, outcome, or `TEAM_STATUS.md` file was changed.

## findings

- KSEI positive controls passed for 11 controls with exact event type, dates,
  ratio, and status. One additional control matched event/date/status but had
  no ratio. Three repeat controls were HTTP 500 and fail-closed.
- Existing KSEI history covers all 347 exposure tickers; 343 are certified and
  `AYAM`, `FREN`, `SLIS`, `SOCI` remain unresolved.
- KSEI pages support positive evidence only. No defensible no-event proof,
  complete historical negative certification, or revision lineage was
  established.
- Zapi `stock-splits` and bounded `additional-listings` reproduced known event
  identity/ratio rows, but their exact market-effective/search semantics are
  not safe for negative enumeration.
- `rights-offerings`, `delistings`, and `issued-history` failed independent
  known-positive controls. The prior known-positive `dividends` route remains
  failed and was not queried again.
- Fresh strict scope recompute: 600 candidates, 0 strict sessions; CA-ready
  4,471 rows / 40 sessions; dividend-ready 11 rows / 0 sessions.

## decisions_made

- Retain the existing KSEI and structured raw captures as external immutable
  evidence; do not promote them as complete negative/continuity sources.
- Do not freeze a target closure window because no exact all-exposure strict
  session exists.
- Do not run the true historical paper engine, performance, NAV, or Monte
  Carlo.
- Keep the disposition
  `TRUE_HISTORICAL_E2E_ENGINE_READY_PERFORMANCE_BLOCKED_BY_DATA`.
- Do not edit canonical `coordination/TEAM_STATUS.md`; MAIN owns it.

## decisions_needed

MAIN/reviewer should decide whether to authorize a separate official paid/data-
reference source feasibility lane. The current admissible public surfaces are
insufficient for market-wide no-event certification.

## blocking_risks

- `NO_CONTIGUOUS_EXPOSURE_COMPLETE_RANGE`;
- `DIVIDEND_EXPOSURE_WINDOW_PROOF_INCOMPLETE`;
- official KSEI normalized corpus lacks identity/ISIN and retrieval-time
  fields and retains per-page hashes rather than raw bytes for every ticker;
- unresolved KSEI exposure tickers: `AYAM`, `FREN`, `SLIS`, `SOCI`;
- no certified revision/correction chronology on the KSEI history surface;
- structured routes return false-empty known positives or unsafe search results.

## validation_run

- KSEI source audit: 10 bounded official KSEI GETs; 9 HTTP 200 full CA tables,
  1 HTTP 500; no `finance:ksei` investor-statistics endpoint;
- structured catalog/positive controls: existing bounded raw artifacts reused;
- strict scope validator: `STRICT_SCOPE_EMPTY_BLOCKED`, 600 candidates, 0
  strict sessions;
- fresh scope artifact:
  `D:\Documents\Project\idx-historical-e2e-scope-closure-v3-20260824\REPLAY_SCOPE.json`;
- fresh scope artifact SHA:
  `cb765a5f1675ea35c2a4d075302c64fd6ac09d413ba8edb4a8198079ed203ae0`;
- outcome/P&L/NAV/model/protected-outcome access: `false`;
- repository `git diff --check`: PASS before documentation.

## recommended_next_action

Stop this lane for independent review. If the project continues, acquire or
validate one authoritative structured IDX/KSEI historical archive with exact
CA/dividend effective-date, revision, identity, and coverage semantics. Do
not fall back to arbitrary announcement-PDF crawling and do not open outcomes
to select a convenient partial window.
