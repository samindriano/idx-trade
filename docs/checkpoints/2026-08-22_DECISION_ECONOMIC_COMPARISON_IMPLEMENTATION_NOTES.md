# Decision Economic Comparison V1 — Implementation Notes

Status: `IMPLEMENTED_AWAITING_SINGLE_LOCAL_RESULT`

Goal: compare naive daily Top10 and frozen Decision V1/V2/V3 economically on the already-consumed 600-session Decision development window. This is intentionally a single lightweight comparison lane after extensive structural research.

## Important scope correction before outcome access

The earlier idea of reconstructing full historical NAV, CAGR, Sharpe, and drawdown is **not** used. Existing Execution V1 / hard-audit documentation explicitly keeps historical executable PnL blocked because quantity/cash continuity across corporate actions is not certified. This lane does not bypass that blocker.

Instead, the comparison consumes the canonical clean V4-X1 `clean_target_ledger.parquet`, whose available H5/H10 returns already require:

- entry at official Open(t+1);
- observable positive admitted entry Open;
- observable terminal Close;
- active market state at entry/terminal;
- resolved price continuity for the exact horizon.

The experiment therefore measures **policy-level economic target quality**, not an executable historical portfolio path.

## Frozen comparison

Policies:

1. `NAIVE_TOP10` — exact daily consensus Top10 derived from the same frozen score artifact;
2. `DECISION_V1` — exact frozen target memberships from its structural trajectory artifact;
3. `DECISION_V2` — exact frozen membership ledger from its rejected structural replay;
4. `DECISION_V3` — exact frozen membership ledger from its rejected structural replay.

All must match the exact frozen source hashes:

- source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`;
- challenger score SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`.

No policy is rerun or retuned. Naive Top10 is reconstructed deterministically from `alpha_consensus DESC, ticker ASC` because it is the already-used baseline, not a new policy variant.

## Economic target accounting

- target capacity is ten fixed seats;
- each occupied seat contributes `10%` notional weight;
- an unfilled seat contributes `10%` cash with zero return;
- V2 underfill is therefore **not** redistributed across fewer names;
- H5 basket outcome on date t is `0.10 * sum(r5)` for selected names when every selected name has canonical H5 support;
- H10 is analogous;
- missing/unresolved selected-name outcomes are never imputed or reweighted away;
- headline comparisons use dates with **complete support for all four policies** at that horizon, so availability differences cannot favor one policy mechanically.

H5/H10 observations overlap in calendar time. Their distributions are therefore target-outcome development evidence; the runner does **not** annualize them or report Sharpe/CAGR/drawdown.

## Frozen friction proxy

Existing Execution V1 retail assumptions are reused without tuning:

- buy fee `15 bps`;
- sell fee `25 bps`;
- primary slippage `10 bps` per side;
- slippage sensitivities `0` and `25 bps` per side;
- reference NAV `Rp50m`;
- account stamp duty `Rp10,000` when fixed-seat gross turnover exceeds `Rp10m`.

Scenarios are fixed as:

- `ZERO`;
- `FEES_ONLY` = 15/25 bps, zero slippage;
- `PRIMARY` = 15/25 bps + 10 bps per side;
- `HIGH_SLIPPAGE` = 15/25 bps + 25 bps per side.

The friction calculation is deliberately a **membership-turnover burden proxy**, not executable PnL. Each changed seat is treated as 10% of the reference NAV. It does not model lot rounding, liquidity partial fills, drifted weights, capacity, or corporate-action quantity transforms.

A `net_proxy` subtracts that date's membership-friction burden from the canonical forward basket outcome. Because horizons overlap and actual intervening trades are not replayed, `net_proxy` must never be described as historical portfolio return.

## Outputs

- `summary.json`
- `policy_signal_outcomes.csv`
- `membership_turnover_cost_proxy.csv`
- `MANIFEST.json`

Summary reports for H5 and H10:

- own complete-support coverage per policy;
- all-policy common-support date count;
- gross mean/median/IQR/dispersion/positive share;
- gross excess and win share versus naive Top10;
- the same distribution under each fixed net-proxy cost scenario;
- policy ranking by gross mean and each cost-adjusted mean;
- turnover/cost burden separately.

## Scientific boundary

- Decision V4 implementation/replay: false;
- V1/V2/V3 parameter changes: false;
- policy threshold sweep: false;
- alpha refit/retune/rescore: false;
- protected/fresh-forward access: false;
- provider/network calls: false;
- executable historical NAV/PnL: false;
- CA quantity/cash transformations: false;
- final untouched validation claim: false.

This 600-session sample is now a **Decision development set**. The result can determine whether a Decision layer is economically promising enough to continue, but cannot serve as final out-of-sample proof.
