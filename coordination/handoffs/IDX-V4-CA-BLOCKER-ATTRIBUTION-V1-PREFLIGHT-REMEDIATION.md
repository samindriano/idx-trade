# Handoff — IDX-V4-CA-BLOCKER-ATTRIBUTION-V1-PREFLIGHT-REMEDIATION

from: ChatGPT
to: local Windows operator / Codex
branch: `data/idx-v4-ca-blocker-attribution-v1`
parent Stage-B result: `489891211b872e7f0c561f85af1cb8221f4d00ef`

## Mission

Perform one retry of the blocker-attribution lane after the preflight helper bug was corrected. Do not design, patch, or reinterpret anything locally.

The first attempt never read the Stage-B ledger and never created the output root, so no attribution result has been exposed.

## Step 0 — coordination

Fetch latest `origin/main:coordination/TEAM_STATUS.md`. Confirm no overlapping ACTIVE lane owns this exact scope. Change only `V4 CA blocker attribution V1` from `REVIEW` back to `ACTIVE` with the same branch/boundary, then push the coordination-only update to main under the safe shared-file rule.

If overlap exists, STOP.

## Step 1 — pull latest branch and validation

Pull the latest `data/idx-v4-ca-blocker-attribution-v1`.

Run exactly:

```powershell
python -m pytest tests/test_v4_ca_blocker_attribution.py
python -m py_compile scripts/run_v4_ca_blocker_attribution.py
git diff --check
```

The updated focused suite contains 8 tests. All must pass. If any validation fails, STOP immediately. Do not patch locally.

## Step 2 — immutable input and output-root preflight

Require:

`D:\Documents\Project\idx-v4-ca-residual-document-continuity-20260818-v2\v4_frozen_continuity_ledger_event_window.csv`

SHA-256 must equal exactly:

`585a9c55b200b2fe8e7b8d4a7f0453c3fdc1d659c666b036bbdec797c04ec634`

Require fresh/nonexistent output root:

`D:\Documents\Project\idx-v4-ca-blocker-attribution-20260818-v1`

The previous validation failure did not create this root. If it now exists for any reason, STOP; do not delete it and do not choose another root.

## Step 3 — one exact offline attribution run

Run exactly once:

```powershell
python scripts/run_v4_ca_blocker_attribution.py `
  --stage-b-ledger "D:\Documents\Project\idx-v4-ca-residual-document-continuity-20260818-v2\v4_frozen_continuity_ledger_event_window.csv" `
  --output-dir "D:\Documents\Project\idx-v4-ca-blocker-attribution-20260818-v1"
```

No provider/network call is needed or authorized.

## Step 4 — promote/report and STOP

If the run completes, promote only small `summary.json`, `MANIFEST.json`, and `blocker_attribution_per_date.csv` under `docs/artifacts/`; keep the immutable Stage-B ledger external.

Report:

- final branch HEAD, clean/synced state;
- focused pytest count, `py_compile`, `git diff --check`;
- exact input ledger SHA;
- attribution verdict;
- for all six scenarios: H5/H10/consensus gate-date counts, minimum rates, worst dates, `all_600_pass`, newly-resolved-row assumption count;
- baseline reason counts;
- `known_mechanical_crossing_rows_never_waived` (expected from accepted Stage B: 227);
- summary/per-date/manifest SHA-256;
- provider/model/target/outcome flags.

Update only the matching TEAM_STATUS row to `REVIEW` with the exact result and push. STOP regardless of verdict.

## Hard boundaries

Do not rerun Stage A or Stage B. Do not modify CA semantics, scenario definitions, thresholds, universe, source files, provider data, target/rank materialization, model, predictions, performance, bootstrap, protected outcomes, or fresh-forward data.
