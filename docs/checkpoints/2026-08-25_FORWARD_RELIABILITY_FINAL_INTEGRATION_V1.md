# Forward Reliability Final Integration V1

Date: 2026-08-25
Lane: `integration/idx-e2e-baseline-paper-v1`
Result: `FORWARD_RELIABILITY_REMEDIATED_NEXT_SESSION_PROOF_PENDING`

## Integrated lineage

- `main` after the accepted prospective-evaluation merge: `ce301d0e1ed5b8a363093a7d057a3a61a7a64c23`.
- E2E integration after PR #85 and PR #86: `9a2d5f45ab8ee7d79d8714139a25b9ee11f663d5`.
- PR #83 (V4-X1 prospective evaluation protocol): merged to `main` as `bd251c1ce253936f672ea8a1e194f0dfe37ca0f6`.
- PR #84 (Stockbit forward reliability): merged to `main` as `88043816a2d414a4f3cb8528077a172d8967257e`.
- PR #85 (E2E official Open reliability): merged to integration as `cb0f9f5680b608be16e4fd09999ae2da8991e4a4`.
- PR #86 (forward evidence health, outcome-blind): merged to integration as `9a2d5f45ab8ee7d79d8714139a25b9ee11f663d5`.

No model, target, sizing, execution science, historical E2E, or Monte Carlo artifact was changed in this integration closeout.

## Runtime and scheduler

The deployed runtime checkout is clean at integration HEAD `9a2d5f45ab8ee7d79d8714139a25b9ee11f663d5`:

`C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational`

The `IDXTrade-E2E-OfficialOpen` task remains enabled and bound to `run_official_open_capture_v2.ps1` in that checkout. Read-only verification found:

- retries at 09:02, 09:07, 09:12, 09:17, and 09:22 Asia/Jakarta, plus AtLogOn;
- `StartWhenAvailable=true`, `MultipleInstances=IgnoreNew`, network requirement enabled;
- RunLevel `Limited`, current user `Sam`, no credential in action arguments;
- last run 2026-08-25 09:22, result `0`;
- 2026-08-25 was a no-session holiday: `HOLIDAY_NO_SESSION` / `NO_PLANNED_OFFICIAL_SESSION_TODAY`;
- no provider capture was forced and no historical backfill was attempted;
- next scheduled slot observed: 2026-08-26 09:02 Asia/Jakarta.

Runtime-root evidence was read only under `%LOCALAPPDATA%\IDXTrade\e2e_baseline_paper_v1`; the latest holiday no-op is not evidence of a genuine trading-session capture. The next genuine weekday is the required operational proof.

## Validation

- Integration focused suite: `63 passed`.
- Integration full suite on the health candidate: `760 passed, 3 warnings`.
- Integration full suite again on exact post-merge HEAD `9a2d5f45`: `760 passed, 3 warnings`.
- Main full suite on exact post-merge HEAD `bd251c1c`: `178 passed`.
- Relevant Python compile/import smoke: PASS.
- PowerShell parser smoke for `run_official_open_capture.ps1` and `run_official_open_capture_v2.ps1`: PASS, zero syntax errors.
- `git diff --check`: PASS on integration validation worktree.

The three full-suite warnings are existing pandas `FutureWarning`s in curated identity and tradability-anchor tests; no test failed.

## Boundaries and flags

This closeout did not open the protected outcome vault, call the protected loader, force a provider capture, or alter a counter. The holiday run was provider-free.

```text
PROSPECTIVE_OUTCOMES_ACCESSED=FALSE
REAL_PROTECTED_LOADER_CALLED=FALSE
REAL_OUTCOME_ACCESS_MARKER_WRITTEN=FALSE
FORWARD_COUNTER_CHANGED=FALSE
MODEL_CHANGED=FALSE
MODEL_REFIT=FALSE
MODEL_RETUNED=FALSE
DECISION_CHANGED=FALSE
SIZING_CHANGED=FALSE
EXECUTION_SCIENCE_CHANGED=FALSE
HISTORICAL_E2E_REOPENED=FALSE
MONTE_CARLO_REOPENED=FALSE
```

## Next action

Observe the first genuine scheduled trading-session run on the installed task. Verify the certified current-session artifact, hashes, and runtime health read-only. Do not backfill the holiday or claim 1/100 until the calendar/session and artifact gates pass.
