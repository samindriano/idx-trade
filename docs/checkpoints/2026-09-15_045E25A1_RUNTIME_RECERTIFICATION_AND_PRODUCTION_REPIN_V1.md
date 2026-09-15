# 045E25A1 Runtime Recertification and Production Repin V1

Date: 2026-09-15 Asia/Jakarta
Status: `REVIEW_READY`
Technical verdict: `NEW_RUNTIME_PRODUCTION_REPIN_PR_REVIEW_READY`

## Incident and runtime fix

The 2026-09-15 POST_EOD chronology failure is an implementation defect, kept
separate from the earlier transient IDX HTTP 503 failures. A completed
`DATA_READY` session binds the then-current canonical
`forward_monitoring/calendar/exchange_sessions.csv` hash in its immutable
manifest. When the next scheduled capture extends that shared calendar, strict
artifact verification rejects the prior session, `_earliest_missing` returns
that earlier date, and the next session is blocked with
`cannot skip an earlier missing session`.

PR #124 changes the cloud E2E runtime to enter the existing clean compatibility
boundary. That boundary admits only the exact valid canonical calendar
extension that still contains the prior session, while retaining strict checks
for every other immutable artifact and restoring the verifier after both
success and exception paths.

A real SQLite/parquet/filesystem regression constructs a prior `DATA_READY`
session, extends the canonical calendar, proves the strict failure and exact
chronology error, and then proves the cloud compatibility path reaches the next
capture. Negative cases reject a substituted calendar path, a removed prior
session, duplicate or malformed calendars, and modifications to the snapshot,
evidence, or manifest. The regression fails against the prior cloud runtime
`cbc09210d6a097f2d96c86ada1e58a7c5e591015` and passes through PR #124.

PR #124 merged as `045e25a19d9f71170d2c863e768102937e59ad73`.
The exact merged runtime passed 82 focused tests, 1,090 full repository tests,
compileall, and diff checking. Hosted PR pytest also passed.

## Immutable production input namespace

The old `e2e-paper-v2/cbc09210` namespace cannot be safely reused for the new
runtime. It contains 24 attempt/result objects in addition to its 17 input
objects, while its manifest and attempt identity do not bind the executing code
commit. Reuse would therefore make old-runtime and new-runtime attempts
ambiguous even though no terminal stage commit was present.

The new runtime-scoped namespace is `e2e-paper-v2/045e25a1`. Its 16 child
objects were copied only after their source bytes matched every manifest SHA,
using `If-None-Match: *`, children first and manifest last. Independent readback
found 17 objects, 16 roles, no session or stage keys, byte-identical children,
and the exact unchanged manifest SHA-256
`f23f45d8b48d386b6755cd272c5c013c04b2c9ee5df0d35473585f878afb2762`.
No canonical session, stage, capture, model, or outcome state was created.

## Production repin candidate

This candidate starts from `origin/main` at
`73116a29afc856e90efe132c863013c9dce96c04`. It repins all active E2E,
Stockbit bridge/preflight/production, synthetic rehearsal, Cloudflare expected
source/config, test, documentation, and coordination contracts to runtime
`045e25a19d9f71170d2c863e768102937e59ad73` and input prefix
`e2e-paper-v2/045e25a1`. The immutable manifest SHA remains unchanged. The
synthetic rehearsal role-count gate is aligned with the 16-role v2 manifest.

Historical mentions of `043003ee`, `8bc3ee3`, and `cbc09210` remain only where
they document old lineage, prior incidents, or negative-test stale pins.

## Candidate validation

- 409/409 repository tests passed with three pre-existing pandas
  `FutureWarning` messages;
- 34 focused repin, recovery, rehearsal, and Stockbit boundary tests passed;
- Cloudflare Node tests passed 126/126 with the locked local Wrangler 4.127.0;
- all 10 workflow YAML files parsed, compileall passed, and `git diff --check`
  was clean;
- the exact merged runtime passed the offline authoritative-calendar POST_EOD
  boundary as `WAITING_UPSTREAM_EOD_SCORE` without a commit, then its canonical
  Intraday reader accepted the fixture as `DATA_READY`;
- the live bridge read `e2e-paper-v2/045e25a1` through exact runtime `045e25a1`
  and returned `READ_ONLY_PREFLIGHT_PASS_WAITING_CANONICAL_EOD` for
  2026-09-15, with the exact manifest SHA, zero provider calls, zero R2 writes,
  no outcome access, and no POST_EOD commit.

## Acceptance boundary

This review candidate does not deploy Cloudflare, activate recovery, disable the
Windows watchdog, dispatch POST_EOD or Intraday, capture or backfill sessions,
or mutate model/outcome state. Static, offline, namespace, and hosted-CI proof
does not establish production acceptance. After review and a separate merge,
the remaining acceptance evidence is the next genuine scheduled market-day
POST_EOD run on the repinned production runtime, followed by the natural
canonical Intraday consumer path.
