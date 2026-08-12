# IDX Forward Calendar Extension — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Reviewed branch: `data/idx-forward-calendar-extension-v1`
Reviewed HEAD: `96fa494742c043d7b3e0006592b5919659851512`
Decision: `IDX_FORWARD_CALENDAR_EXTENSION_BLOCKED_ACCEPTED_RERUN_ON_NEW_OFFICIAL_SESSION`

## Accepted evidence

The bounded forward-calendar extension is accepted.

- The frozen historical calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` remained unchanged and was used only as the immutable 1,260-session anchor ending 2026-07-31.
- The existing official IDX session provider produced exactly seven certified August sessions, 2026-08-03 through 2026-08-11, assigned deterministic indices 1261 through 1267.
- Official IDX trading-hours evidence supports the frozen `08:45:00 Asia/Jakarta` session-start convention used by the forward resolver.
- No official source date was synthesized for 2026-08-12 or later. Missing Sep-Dec source dates were correctly recorded as unavailable rather than inferred.
- No O2/V3-B scoring, counter registration, protected outcome access, third-party calendar, or weekday inference occurred.
- Focused tests passed 20/20 and the full suite passed 298 tests with five existing warnings.

## Interpretation

`IDX_FORWARD_CALENDAR_EXTENSION_BLOCKED` is the correct fail-closed result, not an implementation failure.

The O2 final-refit freeze is `2026-08-12T07:45:30+07:00`. The latest certified extension session currently starts on 2026-08-11, so no certified session starts strictly after the freeze.

There is no need to wait for Sep-Dec 2026 calendar publication. The next material event is simply the first newly published official IDX session date after the freeze. If the existing official source subsequently certifies 2026-08-12, it must deterministically extend the calendar as session index 1268 with session start `2026-08-12T08:45:00+07:00`; that session would satisfy the strict post-freeze boundary.

## Authorization

Authorized next action:

1. Rerun the exact same evidence-only calendar-extension workflow after the official IDX source publishes a session strictly after the freeze.
2. Do not change the frozen historical anchor, session-start rule, provider hierarchy, or fail-closed semantics.
3. Do not infer missing dates and do not use a third-party calendar.
4. If a post-freeze session resolves, persist/hash the extended evidence and STOP for a bounded handoff to the O2 forward lane.
5. O2/V3-B scoring still requires a separately certified post-close snapshot for that resolved session; calendar resolution alone must not create counter entry 1/100.

No model, feature, training, or outcome work is authorized in this lane.
