# V4 CA Event-Window Semantics V1 — Preflight Parser Remediation

Date: 2026-08-18 Asia/Jakarta
Branch: `data/idx-v4-ca-event-window-semantics-v1`
Parent blocked preflight HEAD: `8224b14070385680588bcb0d987e043a68175cb1`
Parser remediation commit: `beed2e205d4829eb8eac8085c839dce320043a8a`
Status: `PREFLIGHT_BUG_CORRECTED_REVALIDATION_REQUIRED_BEFORE_STAGE1`

## Trigger

The first local validation stopped before any Stage-1 data access with 15 tests passed and 3 schedule-semantic fixtures failed:

- RIGHTS_HMETD expected 2026-04-15, parser returned 2026-04-16;
- STOCK_SPLIT expected 2026-04-15, parser returned 2026-04-17;
- BONUS_SHARES expected 2026-04-17, parser returned 2026-04-20.

No provider call, Stage-1/2/3 artifact, target, model, prediction, performance, or protected outcome was accessed before the failure.

## Root cause

The transition semantic itself was correct. The regex anchor included a greedy trailing wildcard after `Pasar Reguler` / `Regular Market`. That wildcard consumed the intended transition date on the same line. `_date_after(...)` then selected the next date later in the document, typically Recording Date or Distribution Date.

This was a parser implementation defect, not evidence against the frozen event-window contract.

## Correction

The parser now:

1. ends transition regexes at the regular-market semantic anchor;
2. selects the first date after that anchor;
3. preserves the prohibition on Record/Distribution dates as transition fallbacks;
4. additionally accepts the observed spelling variants `Pasar Reguler` and `Pasar Regular` without changing semantics.

The frozen meaning remains unchanged:

- entitlement events use explicit regular-market Ex Date;
- split/reverse-split use explicit first trading date on the new basis;
- no exact transition evidence means unresolved;
- no price-derived or Record/Distribution-date inference.

## Independent fixture check

The three previously failing synthetic fixtures were replayed against the corrected matching logic outside the repository runtime and now resolve to:

- RIGHTS_HMETD: `2026-04-15`;
- STOCK_SPLIT: `2026-04-15`;
- BONUS_SHARES: `2026-04-17`.

This check is not a substitute for local pytest. Exact branch validation must rerun from scratch before Stage 1.

## Next authorization

Local operator must first mark this existing lane ACTIVE in latest canonical `origin/main:coordination/TEAM_STATUS.md`, pull the remediation commit, rerun the exact validation gate from `coordination/handoffs/IDX-V4-CA-EVENT-WINDOW-SEMANTICS-V1.md`, and only proceed to Stage 1 if all tests, py_compile, and `git diff --check` pass.

No source/config changes are allowed after Stage 1 exposes result data. If validation fails again, stop for review.
