# Cash Dividend + E2E Baseline Paper V1 Adversarial Remediation Result

Date: 2026-08-23 (Asia/Jakarta)
Branch: `integration/idx-e2e-baseline-paper-v1`
Pre-result implementation HEAD: `9436c38d02faa71fc16529433e93a4618568d661`
Remediation is validated in the current working tree; final commit is pending.
Canonical coordination anchor read: `origin/main:coordination/TEAM_STATUS.md`

## Final boundary

This lane preserves the frozen V4-X1 model, Decision V2 rules, Sizing V1
policy, Execution V1 fee/slippage/lot/capacity mechanics, official Open
authority, and protected-outcome boundary. No provider call, protected or
fresh-forward outcome access, model fit/rescore/refit, scheduler mutation, or
secret access occurred. All replay artifacts are synthetic and external to
Git.

## Remediation status

The earlier remediation changes remain in force and this continuation closes
the remaining acceptance-harness gaps:

- POST_EOD no longer requires future PREOPEN CA evidence. PREOPEN is a
  separate immutable phase artifact and is checked monotonically against the
  POST_EOD parent.
- PREOPEN journal `verified_evidence` is a valid evidence source for newly
  certified events; same-announcement recovery is explicit rather than silent
  blocker deletion.
- A fresh PREOPEN transport/hash refresh with no semantic event delta is
  accepted; a genuinely new event is recorded as a semantic extension.
- Previous execution and runtime-snapshot parents are hash- and session-bound
  before a new POST_EOD package is prepared, and the child checks the same
  parent again before PREOPEN execution.
- Calendar verification rejects duplicate dates and weekend dates before they
  can become official execution sessions.
- Deterministic replay now contains explicit economic oracles, rather than
  treating “no exception” as success. The oracle includes cost, lot,
  slippage, stamp, capacity, pending Open recovery, Decision V2 paired
  replacement cancellation, dividend lifecycle, same-announcement blocker
  recovery, receivable accounting, and idempotent payment settlement.
- Production replay now has a real child-process cold-restart acceptance and
  a per-session expected-state oracle.
- Replay summaries use an explicit AST import/call/marker audit with
  hash-pinned source evidence and a declared synthetic boundary. They do not
  claim runtime provider/outcome instrumentation that was not present.

## Fresh acceptance runs

### Deterministic core replay

Command:

```text
python scripts/run_e2e_paper_deterministic_replay_v1.py --output-dir <fresh-temp-dir>
```

Result: `DETERMINISTIC_CORE_REPLAY_PASS`

Summary:

```text
C:\Users\Sam\AppData\Local\Temp\idx-e2e-remediation-core-6c7ef79429f24d82ad82d4fa982cc86a\acceptance_summary.json
SHA-256: 0ea50f1bf46ee6e8b2fa38bc3fb87c4aa466d059062280458fa7caf2f71da0f2
Static boundary-audit SHA-256: `e0f44ad1461455d6d6c702457aecce1b097941d14ba0a8df84300f0b426aab01`.
```

The legacy deterministic state-machine replay remains supplemental evidence
for T0 immutability, late-known historical-state requirements, one-time
settlement, and divergent-bootstrap fail-closed behavior. The companion
economic oracle is the acceptance source for exact mechanics.

### Deterministic economic oracle

Command:

```text
python scripts/run_e2e_paper_deterministic_oracle_v1.py --output-dir <fresh-temp-dir>
```

Result: `DETERMINISTIC_ECONOMIC_ORACLE_REPLAY_PASS`

Summary:

```text
C:\Users\Sam\AppData\Local\Temp\idx-e2e-remediation-oracle-76c9576c4d6742529b61e4e299fcdac8\acceptance_summary.json
SHA-256: b76da401d1afbc1e6cf91771adafa38ac3cd014699954cb1096cdf29a94368b3
Static boundary-audit SHA-256: `8776bcae2931349c223b5cad603781bda0d7f7ef0c5a565a5903144f871aa5fe`.
```

Exact observed oracles include:

- regular buy: 5,000 shares, 100-share lots, effective price IDR 1,001,
  gross turnover IDR 5,004,999.999999999, fee IDR 7,507.499999999998,
  stamp IDR 0;
- threshold-plus-one turnover: IDR 10,009,999.999999998 and stamp IDR
  10,000 exactly once;
- 1% reference-day capacity: 900 shares and gross notional
  IDR 900,899.9999999999;
- cum entitlement: 5,000 shares; ex-date receivable: IDR 125,000;
  total-return NAV: IDR 6,125,000; spendable cash remains IDR 1,000,000;
- payment cash: IDR 1,125,000 and repeated payment leaves one settlement;
- missing BUY Open becomes pending and resolves at the next official session;
- missing SELL Open becomes pending and resolves at the next official session;
- Decision V2 paired replacement clears a peer SELL that was only a
  never-filled pending BUY, so the replacement BUY is not falsely blocked;
- same-announcement `A1 -> A1` recovery clears only that blocker while an
  unrelated live `A2` blocker remains visible.
- stamp duty uses the engine's strict `>` threshold, with below/equal/above
  cases exercised explicitly; equality is turnover IDR 10,000,000 with zero
  stamp, while plus-one applies IDR 10,000 stamp.

### Production-path artifact replay

Command:

```text
python scripts/run_e2e_paper_production_replay_v1.py --output-dir <fresh-temp-dir>
```

Result: `PRODUCTION_PATH_REPLAY_PASS`; internal resume probe:
`RESUME_PROBE_PASS`.

Summary:

```text
C:\Users\Sam\AppData\Local\Temp\idx-e2e-remediation-production-8a34d3735da842d2a4429ae05fcc1e40\acceptance_summary.json
SHA-256: 436c4405ea18e9e0cf3038e9f0b606b64064119267adae464ff2968772172166
Static boundary-audit SHA-256: `52722d7b835a2a1b08310a6a46d857abd8d0dd6a36a69127a7b1068126528a00`.
```

The replay uses synthetic files with the real score, EOD, CA journal/review,
official Open, parent verification, POST_EOD, PREOPEN, execution, and durable
runtime paths. It exercises five chronological weekday sessions (`2026-08-24`
through `2026-08-28`, with the next official session `2026-08-31`). Every
session is `EXECUTION_COMPLETE` and is checked against an explicit oracle:

- first session: 10 fills, gross turnover IDR 49,871,822, fee total IDR
  74,807.733, cash after execution IDR 43,370.267, stamp IDR 10,000;
- later sessions: zero fills and zero turnover/stamp;
- every fill's side/ticker/planned shares/filled shares/raw Open/effective
  price/gross/fee/cash effect/status is compared against the deterministic
  expected fill vector; positions, receivables, settlements, and cash are also
  compared per session;
- session 4: PREOPEN semantic delta true and registry event count 1;
- session 5: registry event count remains 1 without resubmitting the event;
- pending transitions and receivable NAV delta are zero in each production
  session;
- the static boundary audit reports zero provider imports/calls, protected
  outcome imports/reads, model refit calls, and model rescore calls in the
  audited replay paths.
- the production oracle independently computes capacity, lot rounding,
  execution price, and debit allocation from frozen constants and fixture
  inputs; T06 independently expects 4,900 shares. It never derives expected
  values from the execution result.

The production summary explicitly records `post_eod_only_ca_exercised`,
`preopen_no_semantic_delta_exercised`, and `preopen_new_event_exercised`.
Late-known correction entitlement is covered by the deterministic economic
oracle, not mislabelled as a production-path observation.

### Cold restart

Command:

```text
python scripts/run_e2e_paper_cold_restart_replay_v1.py --output-dir <fresh-temp-dir>
```

Result: `PRODUCTION_PATH_REPLAY_PASS`; first child stopped after two sessions,
second child resumed from durable artifacts in a fresh process.

Summary:

```text
C:\Users\Sam\AppData\Local\Temp\idx-e2e-remediation-cold-3d9fd433d75e42d4a3c7ed1d3fb2e562\acceptance_summary.json
SHA-256: c4684a607a73f61ed5275a167fe03aa260a550a9ed0ab783ef75bf42f0d5e73d
```

The resume anchor has two completed sessions and verified runtime snapshot /
runtime-state hashes. The resumed result has five sessions. No RAM dictionary
or monkeypatch state is used to resume.
After resume, a third fresh child re-entered completed execution session
`2026-08-25` and returned `ALREADY_COMPLETE`; execution, runtime snapshot, and
runtime-state SHA-256 values were unchanged. This duplicate-rerun evidence is
embedded in the cold-restart summary.

## Flow answers E1–E17

1. **YES** — POST_EOD completes before any PREOPEN artifact exists.
2. **YES** — required CA scope is positions ∪ pending buys ∪ pending sells ∪
   Decision targets.
3. **YES** — a fresh PREOPEN same-state transport/hash refresh is accepted.
4. **YES** — a new PREOPEN event extends the parent monotonically.
5. **YES** — a relevant unresolved live blocker fails closed.
6. **NO** — one certified event cannot hide another unresolved event.
7. **YES** — the durable certified registry drives later lifecycle sessions
   without resubmitting the same evidence.
8. **YES** — receivable affects total-return NAV, not spendable cash.
9. **YES, conditionally** — late-known events use immutable cum-date state;
   missing/tampered history fails closed.
10. **YES** — explicit same-announcement recovery is supported and tested.
11. **NO** — a historical paid dividend is not enough to corroborate a new
   unresolved event.
12. **NO** — `0,125` is not silently interpreted as `125`.
13. **NO** — divergent T0 bootstrap fails before mutation and preserves the
   original hash.
14. **YES** — child-process cold restart reloads durable artifacts and resumes.
15. **NO** — duplicate/weekend official calendar sessions are rejected.
16. **NO** — tampered/deleted previous execution or changed parent evidence
   fails closed.
17. **YES** — execution/runtime artifacts are idempotency- and hash-bound;
   dividend payment settles once.

## Validation

- focused remediation + execution regression suite: **126 passed**;
- full repository pytest: **662 passed**;
- py_compile for all changed/new Python files: **PASS**;
- git diff --check: **PASS**;
- targeted secret scan: no credential literal found; no credential was read;
- provider calls: **0**;
- protected outcome reads: **0**;
- scheduler mutation: **0**.

## Review state

This checkpoint is for independent ChatGPT review. The branch remains
`REVIEW`; no scheduler installation, live/forward execution, model action, or
protected-outcome evaluation is authorized by this document.
