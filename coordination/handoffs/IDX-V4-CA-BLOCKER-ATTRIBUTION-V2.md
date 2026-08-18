# Handoff — IDX-V4-CA-BLOCKER-ATTRIBUTION-V2

from: ChatGPT
to: local Windows operator / Codex
task_id: `IDX-V4-CA-BLOCKER-ATTRIBUTION-V2`
branch: `data/idx-v4-ca-blocker-attribution-v2`
scientific/code-test anchor: `7a70f0643296019bc7bf3150137b65b000a0b344`
parent: `data/idx-v4-ksei-coverage-gap-remediation-v1@8414ff04f4e89afafd07a55b7065e0f585bb7235`

## Mission

Run exactly one offline blocker-attribution V2 calculation over the exact
post-KSEI-remediation full continuity ledger. No provider/network work and no
scientific patching are authorized.

## 0. Canonical coordination gate

Before execution:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer ACTIVE lane owns this exact post-KSEI CA attribution scope;
3. add/update one row:
   - task: `V4 CA blocker attribution V2`
   - status: `ACTIVE`
   - owner: `Codex/V4-CA-Blocker-Attribution-V2`
   - branch: `data/idx-v4-ca-blocker-attribution-v2`
   - boundary: `offline optimistic attribution on exact post-KSEI ledger only; no provider/semantics/target/model/outcome`;
4. push only that coordination edit to main.

If an overlapping ACTIVE lane exists, STOP.

## 1. Checkout + validation

Pull the branch and verify anchor
`7a70f0643296019bc7bf3150137b65b000a0b344` exists unchanged in history.
Worktree must be clean.

Run:

```powershell
python -m pytest tests/test_v4_ca_blocker_attribution_v2.py
python -m py_compile scripts/run_v4_ca_blocker_attribution_v2.py
git diff --check
```

Expected focused result: `13 passed`.

The V2 script has no `idx_trade`/`src` import dependency; do not set or patch
`PYTHONPATH` for this lane.

If any validation fails: STOP. Do not patch locally.

## 2. Exact immutable input preflight

Require:

`D:\Documents\Project\idx-v4-ca-ksei-coverage-gap-continuity-20260818-v1\v4_frozen_continuity_ledger_event_window.csv`

Expected SHA-256:

`9dce85c55a9e8a9e1effba5c7e0d24faa150bfb0d70c0162cfb85955d8a435ec`

Fresh output root must not exist:

`D:\Documents\Project\idx-v4-ca-blocker-attribution-v2-20260818-v1`

Do not delete/overwrite an existing output root and do not choose another root
without ChatGPT review.

## 3. Exactly one offline attribution run

Run once:

```powershell
python scripts/run_v4_ca_blocker_attribution_v2.py `
  --continuity-ledger "D:\Documents\Project\idx-v4-ca-ksei-coverage-gap-continuity-20260818-v1\v4_frozen_continuity_ledger_event_window.csv" `
  --output-dir "D:\Documents\Project\idx-v4-ca-blocker-attribution-v2-20260818-v1"
```

The script independently verifies:

- exact ledger SHA;
- 344,790 rows / 610 tickers / 600 dates / H5+H10;
- exact current reason counts;
- exact current baseline gate counts/minimum rates;
- known mechanical-crossing rows are never waived.

Do not retry the command if it errors. STOP and report.

## 4. Record exact result

Report all eight scenarios:

- `BASELINE`
- `SCHEDULE_ONLY_CEILING`
- `KSEI_COVERAGE_ONLY_CEILING`
- `CROSS_SOURCE_ONLY_CEILING`
- `ALL_COVERAGE_CEILING`
- `SCHEDULE_PLUS_KSEI_COVERAGE_CEILING`
- `SCHEDULE_PLUS_CROSS_SOURCE_CEILING`
- `SCHEDULE_PLUS_ALL_COVERAGE_CEILING`

For each record:

- H5/H10/consensus passing-date counts;
- H5/H10/consensus minimum rates;
- worst dates;
- `newly_resolved_rows_assumed`;
- `all_600_pass`.

Also record:

- verdict;
- `minimal_clearing_scenarios`;
- reason counts;
- known mechanical-crossing rows preserved;
- input ledger SHA;
- summary / manifest / per-date hashes.

Non-baseline scenarios are optimistic upper bounds only, never certification.

## 5. Promotion + STOP

Promote only:

- `summary.json`
- `MANIFEST.json`
- `blocker_attribution_v2_per_date.csv`

under a small artifact directory such as:

`docs/artifacts/v4_ca_blocker_attribution_20260818_v2/`

Create a concise dated result checkpoint and result handoff. Keep no large
ledger copy in Git.

Update the canonical TEAM_STATUS row to `REVIEW` with exact verdict/minimal
clearing scenario and final branch HEAD, push, ensure branch/main clean/synced,
and STOP for ChatGPT review.

## Hard stop

No provider/network calls, KSEI retry, schedule acquisition, cross-source
repair, CA semantic change, threshold/universe/date change, R5/R10, targets,
ranks, model fit, prediction, performance, bootstrap, or protected/fresh-
forward outcome access.
