# Cash Dividend + E2E Baseline Paper V1 Remediation Result

Date: 2026-08-23 (Asia/Jakarta)
Branch: `integration/idx-e2e-baseline-paper-v1`
Implementation anchor before documentation: `95c49c0e2107c9be90256cc9ca221a40260cfd3e`
Canonical coordination anchor read before this work: `origin/main:coordination/TEAM_STATUS.md`

## Scope and boundary

This remediation stays inside the accepted Decision V2 → Sizing V1 →
Execution V1 paper path. It does not change the frozen Decision V2 model,
sizing policy, fee/slippage/capacity mechanics, official Open contract, or
protected forward outcome vault. No provider call, outcome access, scheduler
mutation, or historical backfill was performed.

## Remediated contract

- V1.2 cash-dividend reviews now preserve explicit cross-announcement lineage.
  A same-economic-event link requires explicit lineage or at least two shared
  official documents; a prior payment alone cannot corroborate a new event.
- Post-cum announcements are admissible only as knowledge-time evidence with
  an explicit announcement/knowledge timestamp. The economic event still uses
  its own cum, ex, record, and payment dates.
- V1.2 execution evidence is POST_EOD-only. The immutable journal is the
  source of truth for relevant certified events and per-event review paths;
  required tickers without a certified review remain blockers.
- Decision V2 resolves the required corporate-action universe before the
  attestation request: held positions, target positions, and pending buy/sell
  intents are all included.
- The certified event registry persists across sessions. A newly discovered
  event is not lost when the next session has no new current announcement.
- Late-known events use an immutable historical snapshot at the cum-date for
  entitlement calculation. Missing historical state fails closed; entitlement
  is not inferred from a later snapshot.
- Pre-EOD sizing projects the dividend lifecycle without persisting a second
  state. A receivable contributes to total-return NAV but does not become
  spendable cash until payment. The prepared plan remains bound to the raw
  runtime state and ledger hashes used by execution.
- T0 bootstrap is inspect-before-write and rejects divergent or pre-existing
  runtime state. Prepared/execution parent checks remain hash- and
  semantics-bound, including V1.2 journal identity.
- Numeric semantic review rejects ambiguous three-digit separator values such
  as `123,456` while accepting explicit decimal `0,125`, ordinary decimal
  `0.125`, and unambiguous grouped numbers.
- V1.2 capture timestamps are required to be timezone-aware UTC. Naive IDX
  announcement timestamps are interpreted as Asia/Jakarta. An event whose
  knowledge time is after the attested capture cutoff is rejected.

## Replays

### Deterministic core replay

Command:

```text
python scripts/run_e2e_paper_deterministic_replay_v1.py --output-dir <fresh-temp-dir>
```

Result: `DETERMINISTIC_CORE_REPLAY_PASS`

Acceptance summary SHA-256:
`d2baa3cb442a0cce5496e33f64325134d90807b6d34d60a3bdf8ed53f1f0d510`

The replay proves, with no provider or outcome access:

- cum-date entitlement: 5,000 shares;
- ex-date receivable: IDR 125,000;
- raw NAV: IDR 6,000,000;
- total-return NAV: IDR 6,125,000;
- payment cash after settlement: IDR 1,125,000;
- exactly one settlement and idempotent repeated payment;
- late-known event requires and successfully uses the historical cum-date
  snapshot;
- missing historical state fails closed;
- divergent T0 fails closed without changing the original T0 hash.

### Production-path replay

Command:

```text
python scripts/run_e2e_paper_production_replay_v1.py --output-dir <fresh-temp-dir>
```

Result: `PRODUCTION_PATH_REPLAY_PASS`; `RESUME_PROBE_PASS` also returned after
the second session. The replay uses the real artifact verifiers and the real
POST_EOD/PREOPEN orchestration path with synthetic, hash-pinned fixtures only.

Acceptance summary SHA-256:
`0239538b1f7b35236c4a0318b5e35cb752272e35bbbea2b18291eedcbab1589b`

Five chronological weekday sessions completed with
`status=EXECUTION_COMPLETE`. The summary records fills, turnover, stamp duty,
pending transitions, cash, and dividend NAV diagnostics. The late-correction
session carried a +IDR 125,000 receivable NAV delta while cash remained
unchanged; the payment session settled the same event exactly once and
increased cash by IDR 125,000. The production replay reports
`provider_calls=false`, `protected_outcomes_accessed=false`,
`late_correction_exercised=true`, and `post_eod_only_ca_exercised=true`.

## Validation

- Focused remediation suite: **83 passed**.
- Full repository pytest: **656 passed**, with only the repository's existing
  pandas `FutureWarning` warnings.
- `py_compile`: PASS for every changed/new Python file.
- `git diff --check`: PASS.

The earlier failed production replay attempt was caused by a defect in the
new diagnostic summary field name (`available_cash_idr` did not exist on the
portfolio state), not by the runtime contract. It was corrected to use the
actual immutable `cash_idr` field, and the fresh production replay above then
passed. No failed run was used as an acceptance artifact.

## Review state

This is a remediation result for independent ChatGPT review. No independent
subagent verdict is claimed here. The branch should remain `REVIEW` until that
review accepts the result; no live/paper scheduler or protected-forward
evaluation is authorized by this checkpoint.
