# Decision V3 Quality-Supply Diagnosis V1 — Independent Audit

Date: 2026-08-22 Asia/Jakarta

Status: `QUALITY_SUPPLY_DIAGNOSIS_RUNNER_AUDIT_ACCEPTED_SINGLE_LOCAL_EXECUTION_AUTHORIZED`

Reviewed implementation HEAD: `e8fc242590741f163cfbe2284bb47d147c79d80a`.

Frozen contract canonical SHA-256: `aa03d5a016354cd0e98c6577a6b67e31fe3a93dc98cf9358c5e24fd6a59e6f21`.

CI: GitHub Actions run #1145 — `537 passed, 38 warnings, 0 failed`.

## Audit scope and verdict

The implementation is additive-only relative to the completed Decision V3 failure-diagnosis result branch. It does not modify Decision V1/V2/V3 policy engines, alpha models, structural replay artifacts, or forward runtime.

The runner is accepted for exactly one local outcome-blind descriptive execution against the already-pinned V3 structural replay and exact historical V4-X1 consensus-ranking source.

## Verified scientific boundaries

- CLI authorization is checked before contract, structural-root, or historical-root access.
- The historical source loader is the existing strict pinned V4-X1 loader and reads only `ticker/date/fold/mode/alpha_consensus`; consensus is used only to reconstruct deterministic cross-sectional rank.
- Exact source manifest/score hashes, 600 sessions / 172,697 rows, V3 structural status/plan digest, and every V3 structural artifact SHA remain fail-closed through the reused loaders.
- No Decision planner/adapter is imported or invoked by the diagnosis runner.
- No alternative policy, wait-1/wait-2/wait-3 rule, threshold sweep, hypothetical target path, returns/PnL, protected/fresh-forward data, model refit/retune, provider/network call, or paper/live action is reachable from the diagnostic path.
- `t..t+3` are reporting horizons only.
- Tier-A-equivalent is fixed to the already-existing V3 evidence definition: current rank <=10 and immediately previous observed rank <=20.

## Audit hardening applied before acceptance

Two issues were found and corrected before authorization:

1. `converted_within_3_sessions_rate` initially treated entrants near the end of the 600-session replay as failures even when a complete t+3 window did not exist. The final implementation excludes those censored entrants from the within-3 denominator while preserving per-horizon terminal exclusion.
2. B/C entrant conversion reporting initially pooled severe and non-severe entry contexts. The final implementation records `entry_severe_session` and reports severe-session-only versus non-severe scopes separately, so the specific panic-refill mechanism is not diluted.

## Important interpretation limitation

The reported future unheld Tier-A supply follows the **already-observed V3 holdings path**. It intentionally does not add back a B/C name that a hypothetical wait-policy would have left unheld. The separate B/C entrant path reports whether those actual V3 entrants later become Tier-A-equivalent, but the runner never combines those facts into a hypothetical portfolio.

Therefore this diagnosis can support or weaken the architectural plausibility of temporary vacancy/cash, but it cannot claim the performance or exact capacity of any Decision V4 rule.

## Authorization

Exactly one local execution is authorized with token:

`DECISION_V3_QUALITY_SUPPLY_DIAGNOSIS_AUDIT_ACCEPTED_V1`

Required implementation branch/head for execution:

- branch: `research/idx-decision-v3-quality-supply-diagnosis-v1`
- HEAD: `e8fc242590741f163cfbe2284bb47d147c79d80a`

Use a fresh output directory. If execution fails before artifact promotion, stop and review the error; do not improvise source paths, thresholds, or policy logic.

This audit does not authorize Decision V4 preregistration, implementation, replay, returns/PnL access, or downstream activation.