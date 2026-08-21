# V4-X1 Decision V1 — Structural Trajectory Audit Prep

Date: 2026-08-21 Asia/Jakarta

Status: `PREPARED_OUTCOME_BLIND_LOCAL_REPLAY_REQUIRED`

## Purpose

Replay the already-frozen Decision V1 security-selection rule across the exact 600-date clean V4-X1 historical OOS score trajectory. This is a structural/mechanical audit only. It does not evaluate returns or tune Decision V1.

## Frozen source

- Historical replay root: `D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2`
- Source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`
- Score artifact: `clean_challenger_validation_scores.parquet`
- Exact score child SHA is reverified against `MANIFEST.json` at runtime.
- Required score dates: exactly 600.

The audit derives `rank_consensus` independently per date using the same frozen Decision V1 ordering contract: `alpha_consensus DESC, ticker ASC`.

## Frozen Decision V1 applied unchanged

- target 10 names;
- new entries only from Top-10;
- incumbent Top-10 retained;
- rank >20 mandatory exit;
- rank 11–20 replaceable only if best unheld Top-10 candidate is at least 5 ranks better;
- continuous shadow state from empty start across all 600 dates;
- no fold reset.

The runner invokes the actual frozen `plan_decision_v1` implementation. No alternative parameters are exposed.

## Diagnostics preregistered before runtime

1. Decision replacements per session, excluding bootstrap.
2. Exact daily Top-10 replacements as a naive turnover comparator.
3. Decision/naive turnover ratio.
4. Zero-change fraction, 3+ replacement fraction, longest unchanged streak.
5. Target Top-10 overlap and number of retained rank-11–20 incumbents.
6. Mean/median/worst target rank distribution.
7. Holding-spell duration distribution, including right-censored final holdings.
8. SELL/BUY intent reason counts.
9. Per-100-date block diagnostics to verify no fold-boundary reset.

No structural pass/fail threshold is preregistered; the result is descriptive evidence used to understand the already-frozen rule. Any later parameter change must be a separately named Decision V2, not a silent retune of Decision V1.

## Hard guards

Forbidden in this audit:

- target/realized return loading;
- historical portfolio PnL;
- sizing or execution simulation;
- corporate-action transformation;
- model fit/refit/retune;
- protected/fresh-forward outcomes;
- provider/network calls;
- changing Decision V1 parameters.

## Outputs

- `decision_v1_trajectory_daily.csv`
- `decision_v1_holding_spells.csv`
- `summary.json`
- `MANIFEST.json`

Output directory is immutable/refuse-overwrite.
