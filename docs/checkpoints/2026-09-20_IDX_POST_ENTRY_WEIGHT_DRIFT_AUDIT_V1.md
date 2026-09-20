# IDX Post-Entry Weight Drift Audit V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`
Runtime checkout: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational`
Runtime HEAD: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## Verdict

`RISK_OVERLAY_NOT_CERTIFIED — ENTRY CAP IS NOT A CONTINUING WEIGHT CAP`

The pinned configuration has `max_entry_weight_per_name=0.15`, but the
runtime has no active post-entry weight or concentration enforcement. A
synthetic price-drift case moves a winner to 25% of mark-to-market NAV while
the entry cap remains 15%.

## Evidence

The read-only probe `research/idx_post_entry_weight_drift_probe_v1.py` pinned
runtime HEAD `402fca4b...` and found:

- sizing config `max_entry_weight_per_name=0.15`;
- execution config `strategic_cash_overlay=false`;
- execution config
  `post_entry_weight_drift_policy=NO_COSMETIC_REBALANCE_PORTFOLIO_RISK_OVERLAY_FUTURE`;
- ten equal synthetic positions initially worth IDR10,000,000 each;
- one name triples to IDR30,000,000 while the other nine remain at
  IDR10,000,000;
- resulting winner weight is `30 / 120 = 25%`;
- `PaperPortfolioState` has no mark price, market value, or weight field;
- `paper_state_hash` has no mark price, market value, or weight input;
- no active post-entry rebalance/concentration/drawdown risk marker was found
  in the pinned execution/sizing source;
- `writes_performed=False`.

## Interpretation

This is a hidden system assumption and economic/exposure risk, not evidence of
arithmetic corruption. The current design may intentionally be a fixed-seat
allocator with no risk overlay. However, an entry guard cannot be presented as
a continuing portfolio-risk bound. The state hash also identifies holdings and
cash without identifying the mark set used to interpret current concentration.

This finding composes with the exposure/cash-cause taxonomy gap: a future risk
hold would need a state-owned cause and exact valuation/config lineage, rather
than being inferred from a position snapshot alone.

## Reopen condition and boundaries

Do not add a risk overlay or tune the model in this lane. Reopen only after an
authorized policy decides whether continuing weight/concentration control is
required, then defines PIT-safe marks, risk state ownership, cost/turnover
semantics, and restart/replay behavior. No protected outcome, provider,
canonical data, production state, or incumbent state was accessed or changed.

Validation: focused probe `1 passed`; compilation passed; no writes, retry,
push, or merge performed.
