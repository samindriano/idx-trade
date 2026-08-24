# Historical E2E Replay V1 — Final Blocker Reconciliation

Date: 2026-08-24
Branch: `research/idx-historical-e2e-replay-v1`
Parent: `571a856d8c87be30ec9e3baa01820803c392198e`
Mode: outcome-blind readiness and provenance audit only

## Result

`STRICT_SCOPE_EMPTY_BLOCKED`

The frozen 600-session decision exposure universe remains outcome-blind and
has no defensible contiguous replay scope. No historical paper replay,
performance calculation, true-NAV Monte Carlo, or protected-outcome access was
performed.

The latest scope payload is pinned by:

- path: `D:\Documents\Project\idx-historical-e2e-scope-recompute-20260824-v9\REPLAY_SCOPE.json`
- file SHA-256: `cb765a5f1675ea35c2a4d075302c64fd6ac09d413ba8edb4a8198079ed203ae0`
- payload SHA-256: `f75cf7302f4bd27927e36e296634c7ae9adfcd32849ed8fc78555a9e27dc6fd7`
- candidate sessions: `600`
- strict sessions: `0`
- blockers: `NO_CONTIGUOUS_EXPOSURE_COMPLETE_RANGE`,
  `DIVIDEND_EXPOSURE_WINDOW_PROOF_INCOMPLETE`

## Readiness evidence

### Official Open

The latest outcome-blind scope refresh found complete certified source
evidence for every exposure-side BUY/SELL ticker/date identity:

- BUY required/evidence/positive/nonpositive/missing: `1297 / 1297 / 905 / 392 / 0`
- SELL required/evidence/positive/nonpositive/missing: `1287 / 1287 / 891 / 396 / 0`
- all 600 candidate sessions have BUY and SELL evidence readiness.

Certified non-positive Open evidence remains an execution-pending state under
the frozen contract; it is not converted to a synthetic price and does not
block readiness by itself.

### Corporate action continuity

Pinned final CA artifacts:

- manifest SHA-256: `c635ee354c923eebdb586bc4d82a6693d230e1a347df50879dda4c1f5f56bff4`
- continuity ledger SHA-256: `0c48aa4d12a66241378e1b95e2f51615b5ca3469a4c63692c5d9e7b8818a337f`
- schedule-evidence-needed SHA-256: `441253ec7a40a789eac00b4dd4159fc9470c6e4dcab23cd7c2c20bc9596cffed`
- exposure rows: `5693`
- CA-ready rows: `4471`
- unresolved rows: `1222`

The unresolved exposure rows include `749` exact official transition-date
requirements, `420` uncertified KSEI registered-security-history cases,
`38` unavailable CA-evidence cases, and `6` source-candidate/coverage cases.
The targeted KSEI schedule artifact contains `95` schedule-required events:
`1` exact linked transition and `94` without an exact linked transition. The
schedule acquisition cannot safely promote those 94 events by filename,
publication date, price ratio, or approximate date.

### Dividend economics

Pinned complete announcement corpus:

- discovery manifest SHA-256: `9c89e0e089827a46c51a18ee3d2ddba36861fc02660f677942315d9d367e25bf`
- normalized manifest SHA-256: `a94a04b7d8c2dcefafbd8397e03e36059efbdeaab609068644d53371d1b6b167`
- source coverage: `347/347` tickers, `53637` source rows, query window
  `2023-12-28..2026-07-17`, complete page-count/row-count checks.

The corpus is complete as an announcement-page source, but its absence of a
keyword candidate is not an official no-event proof. Attachment metadata
references `2023` candidate documents but no event attachments are preserved
in this corpus. Consequently:

- cash candidates: `921` (`844` cash, `60` ambiguous, `17` unsupported);
- candidate-ticker exposure intersection: `4380` rows / `965` spells;
- no-candidate-ticker exposure intersection: `1313` rows / `332` spells;
- bounded certified event overlaps: `2` spells / `11` rows;
- dividend-ready rows after exposure expansion: `11/5693`;
- dividend-ready sessions under the all-exposure gate: `0/600`.

The two certified overlaps are BBCA spell 935 and BBRI spell 964, already
represented in the accepted dividend gap artifact. The remaining `1295`
spells remain `NO_MARKET_WIDE_NO_EVENT_PROOF` and are intentionally not
promoted.

### Tradability and price inputs

The close/RMV/tradability audit supports exact scoped points:

- 5693/5693 current exposure HLCV/RMV rows complete;
- 5692/5693 next-session HLCV/RMV rows complete;
- 600/600 session-level RMV coverage;
- 6990/6990 unique target ticker/date pairs have official IDX Stock Summary
  anchors: `6989 ACTIVE`, `1 NO_TRADE`, `0 UNKNOWN` or identity conflicts;
- 1296/1297 spells have active/listed entry and exit transition evidence.

The single `NO_TRADE` point is SRAJ spell 818 exit `2025-09-15`, whose
preceding next-session HLCV/RMV evidence is incomplete. This is a pointwise
execution boundary, not the dominant blocker; CA and dividend evidence still
prevent a full-scope replay.

## Decision

No safe scope reduction, ticker subset, synthetic no-event assumption, or
non-zero-start replay was introduced. The replay runner has a zero-holding
bootstrap, so a non-zero start is fail-closed until a predecessor-state anchor
is frozen. No model or runtime semantics were changed.

Next permissible work requires a separately authorized official-source lane
that can either:

1. produce exact official CA transition evidence for the remaining exposure
   event windows; and
2. prove dividend no-event semantics or acquire exact event attachments and
   dates for the exposure universe.

Until then, the longest defensible strict contiguous scope is zero sessions.

## Validation

- focused replay/scope/Open suite: `58 passed`;
- full suite: `745 passed, 0 failed, 3 existing pandas FutureWarnings`;
- `py_compile`: PASS;
- `git diff --check`: PASS;
- no provider calls, outcome access, labels, model fit, or performance metric
  access in this reconciliation.

Canonical `coordination/TEAM_STATUS.md` was not edited because MAIN owns that
file.
