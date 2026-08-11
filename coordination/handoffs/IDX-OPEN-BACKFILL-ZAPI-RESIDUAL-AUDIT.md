# Handoff

from: ChatGPT / MAIN methodology + implementation
to: Codex local verifier/runtime
task_id: IDX-OPEN-BACKFILL-ZAPI-RESIDUAL-AUDIT
source_repository: samindriano/idx-trade
branch: `data/idx-open-backfill-zapi-residual-audit-v1`
parent_commit: `2a40b1da4f75a0c8c80b2045e5e07f3ea0ed50e7`
scope: local verification and bounded Zapi Source-2 residual audit only

## Read first

1. `AGENTS.md`
2. `docs/OPEN_BACKFILL_ZAPI_RESIDUAL_AUDIT_V1.md`
3. `docs/checkpoints/2026-08-11_OPEN_BACKFILL_YAHOO_CENSUS_INDEPENDENT_REVIEW.md`
4. `docs/checkpoints/2026-08-11_OPEN_BACKFILL_YAHOO_CENSUS_RESIDUAL_DIAGNOSTIC.md`
5. this handoff

## Branch boundary

Work only on `data/idx-open-backfill-zapi-residual-audit-v1`.

Do not touch or merge the parallel PIT-sector, Ranking, frontend, or Yahoo-census branches. No rebase/force-push.

## Implementation already present

- `src/idx_trade/zapi_residual_audit.py`
- `tests/test_zapi_residual_audit.py`

The implementation is a ChatGPT-authored draft and requires local verification before any network runtime.

Before runtime:

1. fetch remote and verify clean worktree on latest branch HEAD;
2. run focused tests for `tests/test_zapi_residual_audit.py`;
3. run full pytest;
4. inspect the new module for concrete correctness issues only.

Two pre-runtime invariants require explicit verification:

- known-control exact-Open classification must treat pandas/numpy boolean truth correctly; do not rely on Python object identity for nullable/numpy booleans;
- artifact manifest must not contain a stale hash caused by hashing `zapi_targeted_summary.json` before that summary is finalized. Follow the existing Yahoo census pattern: exclude manifest and final summary from the manifest payload, then write manifest hash into the final summary.

If either invariant is violated, make the smallest bounded fix and add/adjust a focused test. Do not redesign sample sizes, roles, gates, provider, or arbitration semantics.

## Immutable/local inputs

Panel:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

Required SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Accepted Yahoo census root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810`

Required inputs from that root:

- `yahoo_open_census_row_audit.parquet`
- `provider_ticker_status.csv`

Do not alter those artifacts.

## Zapi credential

Read only local environment variable:

`ZAPI_API_KEY`

Never print or commit the secret.

If absent:

- run no network calls;
- report `ZAPI_BLOCKED_CREDENTIAL_ABSENT`;
- do not substitute another source;
- STOP.

If endpoint is plan/access gated:

- preserve factual HTTP/access classification;
- do not upgrade, bypass, scrape, or substitute another source automatically;
- STOP.

## Runtime output

Use a new external directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_residual_audit_v1_20260811`

It must be empty before first runtime. Do not put runtime artifacts in Git.

## Command

After tests and any smallest required implementation fix:

```powershell
python -m idx_trade.zapi_residual_audit `
  --panel "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet" `
  --yahoo-census-audit "D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810\yahoo_open_census_row_audit.parquet" `
  --provider-status "D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810\provider_ticker_status.csv" `
  --output-dir "D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_residual_audit_v1_20260811"
```

## Frozen runtime semantics

Target sample is deterministic, seed `20260811`, up to 240 rows:

- 120 no-factor Yahoo H/L/C mismatch rows;
- 80 Yahoo provider-gap/error rows;
- 40 known-answer controls.

Do not change quotas after seeing Zapi outcomes.

Corporate-action-related residual rows are excluded.

Zapi requests are grouped by unique selected date using `stock-summary?length=1000&date=...`, with bounded retries and rate-limit-aware spacing. No bulk API.

## Mandatory factual report

At minimum report:

- exact pre-runtime and final branch HEAD;
- focused + full pytest;
- any bounded bug fix and exact changed files;
- panel SHA before/after;
- sample rows, role counts, unique tickers/dates, sample SHA;
- credential present/absent without exposing secret;
- access/plan status;
- requests, retries, HTTP 429 events, unique dates requested;
- provider rows returned and exact ticker/date coverage;
- known-control H/L/C exact and Open exact metrics;
- provider-gap `SOURCE2_RECOVERY_CANDIDATE` count;
- H/L/C mismatch arbitration counts:
  - `SOURCE2_SUPPORTS_CERTIFIED_PANEL`;
  - `SOURCE2_SUPPORTS_YAHOO`;
  - `THREE_WAY_DISAGREEMENT`;
  - `SOURCE2_NO_ROW`;
- rejection histogram;
- all output artifact hashes and final manifest hash;
- panel unchanged;
- `execution_grade_promoted=false`;
- `bulk_backfill_authorized=false`.

## Documentation

After runtime, create:

`docs/checkpoints/2026-08-11_OPEN_BACKFILL_ZAPI_RESIDUAL_AUDIT_RUNTIME.md`

Update this handoff with factual runtime result. Commit only source/test fixes required by concrete verification plus documentation; never commit API key or external artifacts.

Push normal fast-forward if remote did not advance. If remote advanced, stop rather than force/rebase.

## Prohibited

- no bulk Source-2 backfill;
- no corporate-action repair;
- no source averaging/voting;
- no inferred split factor;
- no Yahoo rerun;
- no direct IDX scraping/crawling;
- no alternate Source-2;
- no execution-grade promotion;
- no execution-PnL;
- no Ranking/Probability/PIT-sector experiments;
- no paper/live trading;
- no broker integration;
- no main merge.

Then STOP for independent ChatGPT review.

## Runtime result — 2026-08-11

runtime_status: `ZAPI_BLOCKED_CREDENTIAL_ABSENT`
runtime_head_before_local_fix: `cf896b2b3677f807a39fb6050291eda7dcf60875`
checkpoint: `docs/checkpoints/2026-08-11_OPEN_BACKFILL_ZAPI_RESIDUAL_AUDIT_RUNTIME.md`

ZAPI_API_KEY was absent. The Zapi endpoint was not called, zero Zapi network
requests were made, no alternate source was used, and the required external
runtime output directory was not created.

The two authorized implementation invariants were repaired only:

- nullable/numpy known-control booleans are evaluated by value rather than
  Python identity;
- the artifact manifest excludes the final summary and itself, then its hash
  is written into the finalized summary.

Changed files:

- `src/idx_trade/zapi_residual_audit.py`
- `tests/test_zapi_residual_audit.py`
- `docs/checkpoints/2026-08-11_OPEN_BACKFILL_ZAPI_RESIDUAL_AUDIT_RUNTIME.md`
- this handoff

validation_run:

- focused pytest before fix: `3 passed`;
- full pytest before fix: `236 passed`, `5 warnings`;
- focused pytest after fix: `5 passed`, `2 warnings`;
- full pytest after fix: `236 passed`, `5 warnings`;
- immutable panel SHA verified unchanged:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

decision: stop for independent ChatGPT review. Do not start the Zapi runtime,
Source-2 backfill, corporate-action repair, modelling, Ranking/PIT-sector work,
or execution-PnL until credential/access is separately authorized.

## Credentialed runtime attempt — 2026-08-11

The branch was fast-forwarded to remote HEAD
`2274342c775074230326fb1bc241daa4a0fa4c37` and remained clean. The immutable
panel SHA remained
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

Credential preflight found `ZAPI_API_KEY` absent from the process, Windows User,
and Windows Machine environments. The key was not printed or persisted. The
Zapi endpoint was not called, zero Zapi network requests were made, and the
external output directory was not created. Runtime status remains
`ZAPI_BLOCKED_CREDENTIAL_ABSENT`.

validation_run:

- focused pytest: `5 passed`, `2 warnings`;
- full pytest: `236 passed`, `5 warnings`.

No sample, provider, coverage, arbitration, or artifact result exists for this
attempt. Stop and request a credential visible to this runtime process before
retrying the already-frozen command. Do not substitute another provider or
widen scope.

## Final credentialed runtime result — 2026-08-11

runtime_status: `ZAPI_TARGETED_RESIDUAL_AUDIT_COMPLETE_STOP_FOR_INDEPENDENT_REVIEW`
runtime_base_head: `574f7223bf4f98ff933d8d7c31c44007e85aa78f`
final_checkpoint: `docs/checkpoints/2026-08-11_OPEN_BACKFILL_ZAPI_RESIDUAL_AUDIT_RUNTIME_FINAL.md`

Zapi access was `ACCESSIBLE` / `EMPIRICALLY_REACHED`. The frozen sample was
`240` rows, `206` tickers, `178` dates, with sample SHA
`9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`.
All five Yahoo provider-error tickers were represented.

requests: `178`; retries: `0`; HTTP 429/rate-limit events: `0`; request errors:
`[]`; provider rows: `240`; exact ticker/date rows: `240/240`.

quality:

- H/L/C exact: `240/240`;
- known-control H/L/C exact: `40/40`;
- known-control Open exact: `20/40` (`50%`);
- provider-gap recovery candidates: `0`;
- `SOURCE2_SUPPORTS_CERTIFIED_PANEL`: `120`;
- `SOURCE2_SUPPORTS_YAHOO`: `0`;
- `SOURCE2_PANEL_HLC_MATCH_OPEN_REJECTED`: `80`;
- `SOURCE2_RECOVERY_CANDIDATE`: `0`;
- `SOURCE2_NO_ROW`: `0`;
- `THREE_WAY_DISAGREEMENT`: `0`;
- controls: `CONTROL_PANEL_HLC_OPEN_EXACT=20`,
  `CONTROL_PANEL_HLC_ONLY=20`.

The first credentialed runtime was preserved externally and superseded because
the shared auditor did not recognize `KNOWN_CONTROL`; the final run used the
smallest role-alias fix. No quota, methodology, admission, provider, or
arbitration redesign occurred.

final artifact manifest SHA:
`899def2f280d49695a85f6fa2ddc34a4c793dcdf240ce114a02dd0055787fd1d`.
Panel SHA before/after remained
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

validation_run:

- focused pytest after fix: `6 passed`, `2 warnings`;
- full pytest after fix: `236 passed`, `5 warnings`.

execution_grade_promoted: `false`
bulk_backfill_authorized: `false`
corporate_action_repair_performed: `false`

recommended_next_action: STOP for independent ChatGPT review. Do not start
bulk backfill or any downstream research/modeling lane.
