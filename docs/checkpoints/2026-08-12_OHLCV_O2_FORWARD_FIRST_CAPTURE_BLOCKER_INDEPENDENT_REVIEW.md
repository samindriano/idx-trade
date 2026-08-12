# OHLCV O2 First Capture Blocker — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Reviewed branch: `research/idx-ranking-ohlcv-o2-forward-v1`
Reviewed HEAD: `77ecca8be113aa74b52603e3798cdcd131ea142c`
Decision: `O2_FORWARD_FIRST_CAPTURE_BLOCKER_ACCEPTED_UPSTREAM_CALENDAR_REFRESH_REQUIRED`

## Review

The fail-closed stop is accepted and required by the frozen O2 forward contract.

Verified from the submitted checkpoint:

- the frozen historical calendar SHA remains `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- that artifact contains 1,260 date-only sessions and ends at 2026-07-31;
- preserved forward-monitoring calendars end at 2026-08-10 and therefore cannot establish the first post-freeze session;
- no certified post-close snapshot exists for a post-freeze session;
- official O2 score artifacts remain `0` and the counter remains `0/100`;
- no provider call, protected outcome access, model change, backdating, or scoring occurred.

This is an upstream calendar/evidence readiness blocker, not an O2 model or forward-ledger defect.

## Required next step

Do not weaken or amend the frozen O2 no-backdating contract.

Create a separate data/evidence lane that builds an immutable forward calendar extension anchored to the frozen historical calendar. Reuse the repository's existing official IDX session provider, which obtains Exchange Day dates from official IDX sources and fails closed on conflicting official date sets.

The forward extension must provide at least:

- deterministic consecutive `session_index` continuing after the frozen 1,260-session historical calendar;
- official `session_date`;
- timezone-aware `session_start` derived from an explicitly recorded official IDX trading-hours source/rule;
- source identities/refs and hashes;
- parent historical-calendar SHA;
- immutable artifact/manifest hashes.

Do not replace or rewrite the frozen historical calendar.

After the calendar extension is independently reviewed, wait until an eligible post-freeze session is closed and a certified post-close snapshot exists. Only then rerun the first O2 capture on the forward branch.

## Protected boundary

This review does not authorize O2 scoring, counter registration, outcome access, model changes, retraining/tuning, or historical Open repair while calendar evidence remains unresolved.
