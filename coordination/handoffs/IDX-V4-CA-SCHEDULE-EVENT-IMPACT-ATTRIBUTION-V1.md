# Handoff — IDX-V4-CA-SCHEDULE-EVENT-IMPACT-ATTRIBUTION-V1

from: ChatGPT
to: local Windows operator / Codex
task_id: `IDX-V4-CA-SCHEDULE-EVENT-IMPACT-ATTRIBUTION-V1`
branch: `data/idx-v4-ca-schedule-event-impact-attribution-v1`
scientific/code-test anchor: `b28eaab4aca4a2ffb9741b89115ba1fc3b21ebec`
parent: `data/idx-v4-ca-blocker-attribution-v2@1ae3d8f36010a717491ad47396f73dd63bb5e864`

## Mission

Run exactly one offline event-level attribution over the current post-KSEI V4
CA continuity ledger. Determine which of the frozen 39 schedule-required events
actually matter to the failing dates, then produce a deterministic gate-clearing
priority subset under the preregistered optimistic semantics.

This is diagnostic only. Do not acquire any schedule documents in this lane.

## Step 0 — canonical coordination gate

Before validation:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer ACTIVE lane owns this exact schedule-event impact attribution;
3. add/update exactly one row:
   - task: `V4 CA schedule event impact attribution V1`
   - status: `ACTIVE`
   - owner: `Codex/V4-CA-Schedule-Event-Impact`
   - branch: `data/idx-v4-ca-schedule-event-impact-attribution-v1`
   - boundary: `offline exact 39-event impact/subset attribution only; no provider/schedule acquisition/KSEI retry/semantic change/target/model/outcome`;
4. push only that coordination edit to `main` under the shared-file safety rule.

If overlapping ACTIVE scope exists, STOP.

## Step 1 — exact branch and validation

Checkout/pull the branch and confirm code-test anchor
`b28eaab4aca4a2ffb9741b89115ba1fc3b21ebec` exists unchanged in history.
Worktree must be clean.

Run exactly from repository root:

```powershell
python -m pytest tests/test_v4_ca_schedule_event_impact_attribution.py
python -m py_compile scripts/run_v4_ca_schedule_event_impact_attribution.py
git diff --check
```

Expected focused result: **13 passed**.

The runner imports only stdlib + NumPy + pandas; no `PYTHONPATH` adjustment is
required. If any validation fails, STOP. Do not patch locally.

## Step 2 — immutable input preflight

Require exact external ledger:

`D:\Documents\Project\idx-v4-ca-ksei-coverage-gap-continuity-20260818-v1\v4_frozen_continuity_ledger_event_window.csv`

Require repo-promoted schedule needs:

`docs\artifacts\ranking_v4_ksei_coverage_gap_continuity_v1\schedule_evidence_needs.csv`

The runner independently requires:

- ledger SHA-256
  `9dce85c55a9e8a9e1effba5c7e0d24faa150bfb0d70c0162cfb85955d8a435ec`;
- schedule-needs SHA-256
  `1988f2bb679b09835e045235fa7aa46f4d8c62cf9531e76a5b5b889d848a127a`;
- 344,790 rows / 610 tickers / 600 dates / horizons {5,10};
- 39 unique schedule events;
- exact current reason counts;
- exact baseline `462/461/461`;
- exact all-schedule ceiling `600/600/600`;
- 240 known mechanical-crossing rows never resolved.

Fresh output root must NOT exist:

`D:\Documents\Project\idx-v4-ca-schedule-event-impact-attribution-20260818-v1`

If it exists, STOP. Do not delete, overwrite, or invent another root.

## Step 3 — exactly one offline attribution run

Run once:

```powershell
python scripts/run_v4_ca_schedule_event_impact_attribution.py `
  --continuity-ledger "D:\Documents\Project\idx-v4-ca-ksei-coverage-gap-continuity-20260818-v1\v4_frozen_continuity_ledger_event_window.csv" `
  --schedule-evidence-needs "docs\artifacts\ranking_v4_ksei_coverage_gap_continuity_v1\schedule_evidence_needs.csv" `
  --output-dir "D:\Documents\Project\idx-v4-ca-schedule-event-impact-attribution-20260818-v1"
```

Provider/network calls must remain `0`.

Do not rerun the command if it errors. STOP and report exact error.

## Step 4 — record exact result

Report at minimum:

- baseline H5/H10/consensus pass counts and minimum rates;
- schedule-only ceiling pass counts and minimum rates;
- critical event count + IDs/tickers;
- zero-blocking-row event IDs/tickers;
- top 10 events from `schedule_event_impact.csv` by emitted order, including
  ticker/family/blocking rows/affected failing dates/single-event deficit reduction;
- greedy selection count and exact ordered IDs/tickers;
- reverse-pruned event IDs;
- inclusion-minimal subset count and IDs/tickers;
- exact-search status and evaluation count;
- whether global minimum cardinality was actually proven;
- final selected-subset basis, count, IDs/tickers;
- final selected-subset H5/H10/consensus pass counts + minimum rates;
- confirmation that 6,844 KSEI-coverage rows, 1,200 cross-source rows, and 240
  known mechanical-crossing rows were not waived;
- manifest + summary + four CSV hashes.

Interpretation rules:

- `GLOBAL_MINIMUM_CARDINALITY_PROVEN` is allowed only if the runner explicitly
  reports exact search over the complete critical universe.
- Otherwise use `inclusion-minimal`, never `minimum`.
- A passing subset is still an optimistic acquisition-priority diagnostic, not
  continuity certification.

## Step 5 — promote small artifacts and stop

Promote under a new small-artifact directory:

- `summary.json`
- `MANIFEST.json`
- `schedule_event_impact.csv`
- `selected_schedule_event_subset.csv`
- `selected_subset_per_date.csv`
- `greedy_selection_trace.csv`

Create a concise dated result checkpoint + result handoff.

Update the exact canonical TEAM_STATUS row to `REVIEW` with result HEAD,
selected-subset basis/count, and explicit `provider calls 0 / no acquisition`.
Push branch and coordination update. Branch/main must be clean and synced.

Then **STOP for ChatGPT review**.

## Hard stop

No provider call, official schedule acquisition, KSEI retry, parser change,
semantic reclassification, cross-source repair, threshold/universe change,
R5/R10, target/rank, model, prediction, performance/bootstrap, or
protected/fresh-forward outcome access is authorized.
