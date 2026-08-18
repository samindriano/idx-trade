# Handoff — IDX-V4-CA-BLOCKER-ATTRIBUTION-V1

from: ChatGPT
to: local Windows operator / Codex
task_id: `IDX-V4-CA-BLOCKER-ATTRIBUTION-V1`
branch: `data/idx-v4-ca-blocker-attribution-v1`
parent: `data/idx-v4-ca-residual-document-continuity-replay-v1@489891211b872e7f0c561f85af1cb8221f4d00ef`

## Mission

Run one offline diagnostic attribution over the immutable final Stage-B continuity ledger. Do not re-run Stage A/B, do not acquire data, and do not patch scientific code after result exposure.

## Step 0 — coordination

Fetch latest `origin/main:coordination/TEAM_STATUS.md`, confirm no overlapping ACTIVE CA blocker-attribution lane, then add/update exactly one row:

- task: `V4 CA blocker attribution V1`
- status: `ACTIVE`
- owner: `Codex/V4-CA-Blocker-Attribution`
- branch: `data/idx-v4-ca-blocker-attribution-v1`
- boundary: `offline optimistic ceiling attribution from immutable Stage-B ledger only; no provider/semantic/model/target/outcome`

Push only that coordination edit to main under the shared-file safety rule. If overlap exists, STOP.

## Step 1 — validation

Pull the exact branch. Worktree must be clean.

Run:

```powershell
python -m pytest tests/test_v4_ca_blocker_attribution.py
python -m py_compile scripts/run_v4_ca_blocker_attribution.py
git diff --check
```

If any validation fails, STOP. Do not patch locally.

## Step 2 — immutable input preflight

Require:

`D:\Documents\Project\idx-v4-ca-residual-document-continuity-20260818-v2\v4_frozen_continuity_ledger_event_window.csv`

SHA-256 must be exactly:

`585a9c55b200b2fe8e7b8d4a7f0453c3fdc1d659c666b036bbdec797c04ec634`

Use fresh output root:

`D:\Documents\Project\idx-v4-ca-blocker-attribution-20260818-v1`

If output root already exists, STOP. No alternate root without ChatGPT review.

## Step 3 — one exact offline run

```powershell
python scripts/run_v4_ca_blocker_attribution.py `
  --stage-b-ledger "D:\Documents\Project\idx-v4-ca-residual-document-continuity-20260818-v2\v4_frozen_continuity_ledger_event_window.csv" `
  --output-dir "D:\Documents\Project\idx-v4-ca-blocker-attribution-20260818-v1"
```

Run exactly once. No network/provider call is needed or authorized.

## Step 4 — report and STOP

Return:

- final branch HEAD and clean/synced state;
- validation results;
- exact input SHA;
- attribution verdict;
- for every scenario: H5/H10/consensus gate-date counts, minimum rates, worst dates, `all_600_pass`, and newly-resolved-row assumption count;
- baseline reason counts;
- number of known mechanical-crossing rows preserved;
- summary/per-date/manifest hashes;
- provider/model/target/outcome flags.

Promote only small `summary.json`, `MANIFEST.json`, and optionally the per-date diagnostic CSV under `docs/artifacts/`. Full source ledger remains external.

Update the TEAM_STATUS row to `REVIEW` with exact verdict and key ceilings, push, and STOP.

## Interpretation guardrail

All non-baseline scenarios are optimistic row-level upper bounds. They do not reconstruct hidden blockers that could appear after real remediation and therefore can never set `corporate_action_continuity_certified=true`.

No result from this lane automatically authorizes new CA acquisition, threshold/universe changes, R5/R10, target ranks, model fit, predictions, performance, bootstrap, protected outcomes, or fresh-forward access.
