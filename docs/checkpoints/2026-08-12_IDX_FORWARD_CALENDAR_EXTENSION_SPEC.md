# IDX Forward Calendar Extension — Frozen Specification

Date: 2026-08-12 (Asia/Jakarta)
Branch: `data/idx-forward-calendar-extension-v1`
Parent independent-review commit: `fc1c1a2b531eb0674db961b4d14792a80f8a0345`
Decision: `IDX_FORWARD_CALENDAR_EXTENSION_AUTHORIZED`

## Purpose

Build an immutable, auditable forward Exchange Day calendar extension sufficient to resolve O2's first post-freeze session without changing the frozen historical calendar or weakening the O2 no-backdating contract.

This is a data/evidence task only. It is not an O2 scoring task.

## Frozen anchor

Historical calendar artifact SHA-256:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

It contains exactly 1,260 sessions ending on `2026-07-31` and is read-only.

The forward extension must continue session identity deterministically from this anchor. Do not edit, replace, regenerate, or re-hash the historical artifact.

## Official session-date source

Reuse the existing repository provider in:

`src/idx_trade/providers/idx_sessions.py`

Use only its official IDX source path(s). Preserve its fail-closed behavior when official IDX source date sets conflict.

Network access is authorized only to official IDX domains required by this existing provider and the official IDX trading-hours evidence described below.

Do not use weekday inference, pandas business-day calendars, Yahoo, TradingView, Zapi, Google calendars, or any third-party holiday calendar as the source of Exchange Days.

## Session-start evidence

The O2 resolver requires a timezone-aware `session_start` to prove that a session begins strictly after the final-refit freeze timestamp.

Use the current official IDX equity trading-hours publication as the authority for the earliest regular-market activity on each Exchange Day. The currently reviewed official page states that regular-market pre-opening input starts at `08:45:00` and Session I starts at `09:00:00` on Monday-Friday.

For the forward calendar contract, define:

`session_start = 08:45:00 Asia/Jakarta`

for each official Exchange Day, representing the earliest official regular-market pre-opening activity.

Persist the official trading-hours source identity/reference and retrieval evidence/hash. If the live official source does not support this rule at execution time, STOP fail-closed; do not substitute a remembered schedule.

## Extension construction

Fetch enough official IDX Exchange Days after `2026-07-31` to include the first session strictly after the O2 final-refit independent-review freeze timestamp and a practical forward horizon for continued accumulation. A horizon through at least `2026-12-31` is preferred if the official source supports it without inference.

Construct exactly these core columns:

- `session_index` — deterministic integer continuing from historical session 1,260;
- `session_date` — official Exchange Day in `YYYY-MM-DD`;
- `session_start` — timezone-aware ISO timestamp at `08:45:00 Asia/Jakarta` under the verified official trading-hours rule.

Also persist provenance fields sufficient to audit:

- parent historical-calendar SHA;
- official date-source identity/ref;
- trading-hours source identity/ref;
- retrieval timestamp(s);
- source/raw artifact hash(es) where available;
- extension artifact SHA and manifest SHA.

## Invariants

Must verify before accepting the extension:

1. historical anchor is exactly the expected SHA and last date;
2. first extension index is `1261`;
3. indices are strictly consecutive with no duplicates;
4. dates are unique, strictly increasing and all come from official IDX source evidence;
5. no weekend date appears;
6. `session_start` is timezone-aware and exactly follows the verified official rule;
7. no extension date is inserted from inference;
8. historical artifact remains unchanged;
9. the O2 final-refit freeze timestamp is recorded, and the first session whose `session_start` is strictly later is resolved factually from the extension;
10. no O2 score artifact/counter entry is created in this lane.

## Output decision

Emit exactly one:

- `IDX_FORWARD_CALENDAR_EXTENSION_READY_FOR_O2_REVIEW`
- `IDX_FORWARD_CALENDAR_EXTENSION_BLOCKED`

If ready, persist the resolved first post-freeze session identity/date/start as evidence only. Do not score it.

## Protected boundary

Not authorized:

- O2 or V3-B scoring;
- O2 counter registration;
- protected outcome access;
- model retraining/tuning/calibration;
- historical Open repair;
- third-party calendar fallback;
- changing the O2 forward contract;
- manufacturing a post-close snapshot before the market session is actually complete.

## Validation and checkpoint

Add focused tests for deterministic index continuation, timezone/session-start construction, source/fail-closed behavior, and first-post-freeze resolution using non-protected fixtures.

Run focused and full pytest, persist immutable calendar/provenance artifacts and hashes, write a factual runtime checkpoint, push fast-forward, then STOP for independent ChatGPT review.
