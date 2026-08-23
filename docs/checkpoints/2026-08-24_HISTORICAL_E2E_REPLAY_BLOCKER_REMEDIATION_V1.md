# Historical E2E Replay Blocker Remediation V1

Date: 2026-08-24
Branch: `research/idx-historical-e2e-replay-v1`
Parent: `5fab5a9a56ce21989ed27474566c5817db6cc1df`
Scope: bounded, outcome-blind remediation audit

## Verdict

`TRUE_HISTORICAL_E2E_ENGINE_READY_PERFORMANCE_BLOCKED_BY_DATA`

The remediation pass recovered useful source evidence but did not produce a
non-empty strict replay scope. No historical performance, NAV, labels,
protected outcomes, future returns, or Monte Carlo was opened.

## Open support

Pinned certified Open acquisition:

- root: `D:\Documents\Project\idx-historical-open-acquisition-20260824-v1`
- manifest SHA-256: `dc74485c6d4ade01e125b08871105c8daea9c64f9daa2af6cc00d26592a8fcbf`
- 600/600 session manifests certified; 568,555 source rows; 0 duplicate keys.
- BUY: 905/1,297 positive certified Open; 392 unavailable/non-positive.
- SELL: 895/1,287 positive certified Open; 392 unavailable/non-positive.
- 1,703 unique ticker×execution-date identities support 1,800 intents.

The previous SELL count of 891 was stale; the current pinned bytes audit to
895. Other historical Open roots did not add coverage. A derivative-only
overlay may preserve the 1,703 positive identities (or 1,701/1,798 intents
under the older exact-HLC side rule), but it is not materialized or admitted
here and cannot make the 6×100 scope pass.

## Close/RMV and tradability

External audit root:
`D:\Documents\Project\idx-historical-e2e-close-rmv-tradability-audit-20260824-v2`

Summary SHA-256:
`36d35aa5a453b21441b209ffdb4b2553212d342fab25698e2f7ff5787b392bcb`

All 5,693 current exposure rows have valid H/L/C/Volume; RMV is complete for
600/600 signal sessions. Key alignment and price invariants pass. The audit
does not independently certify listing/tradability, so this remains a
separate gap.

## Corporate actions

Frozen inputs remain unchanged:

- schedule-needs SHA-256:
  `441253ec7a40a789eac00b4dd4159fc9470c6e4dcab23cd7c2c20bc9596cffed`
- frozen continuity ledger SHA-256:
  `0c48aa4d12a66241378e1b95e2f51615b5ca3469a4c63692c5d9e7b8818a337f`

The official attachment audit covers 35/94 event IDs. Conservative
classification: 16 exact event-specific schedule matches, 1 effective-date
only, 3 partial, 5 wrong-family/multi-event, 10 insufficient/mismatched, and
59 uncovered. The exact candidates remain candidate evidence only; no frozen
CA ledger or continuity row was modified.

## Dividends

Pinned complete source corpus:

- raw manifest SHA-256:
  `9c89e0e089827a46c51a18ee3d2ddba36861fc02660f677942315d9d367e25bf`
- normalized manifest SHA-256:
  `a94a04b7d8c2dcefafbd8397e03e36059efbdeaab609068644d53371d1b6b167`
- 347/347 ticker responses and 53,637/53,637 rows matched their source
  metadata; 921 candidates (844 cash, 60 ambiguous, 17 unsupported).

The corpus contains JSON metadata only and no local attachments. Metadata-only
replay yielded 0/844 semantic passes: publication/title/filename metadata is
not proof of amount or cum/ex/record/payment dates. Absence of a candidate is
not evidence of no event; the market-wide dividend no-event gate remains
blocked.

## Replay boundary

The replay engine and synthetic durability controls are usable for a valid
non-empty scope, but the current scope freezer remains
`STRICT_SCOPE_EMPTY_BLOCKED`. It does not yet enforce a 6×100 scope manifest
or validate the full historical execution-state dependency graph. Therefore
no replay, no scoring, no NAV construction, and no Monte Carlo is authorized
by this result.

## Required next gate

Only a separately reviewed bundle may reopen the path: complete execution-grade
Open support, accepted CA continuity evidence, market-wide dividend semantic or
no-event proof, tradability/session eligibility evidence, and an explicit
hash-pinned 6×100 scope with multi-session replay validation.
