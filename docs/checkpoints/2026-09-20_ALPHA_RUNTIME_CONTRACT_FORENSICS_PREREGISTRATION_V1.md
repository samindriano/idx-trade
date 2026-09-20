# Runtime Contract Forensics — Preregistration V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `READ_ONLY / OUTCOME_BLIND`

## Questions

1. Does the exact Decision V2 API itself enforce immediate official-session
   adjacency, or is adjacency supplied by the production controller?
2. Does the available frozen structural panel contain zero, nonfinite, or
   negative `regular_market_value` states in the eligible universe or fixed
   Top-30 C1-C4 selections?
3. Which runtime safeguards are caller-level versus enforced at the execution
   boundary?

## Fixed scope

- Inspect only the pinned runtime commit
  `045e25a19d9f71170d2c863e768102937e59ad73` and existing frozen panel,
  features, and official-session artifacts.
- Do not access outcomes, targets, PnL, providers, cloud, capture, telemetry,
  canonical data, or production state.
- Do not modify runtime code or change any incumbent policy.
- Measure denominator states only; do not reinterpret them as executable
  capacity or predictive evidence.
