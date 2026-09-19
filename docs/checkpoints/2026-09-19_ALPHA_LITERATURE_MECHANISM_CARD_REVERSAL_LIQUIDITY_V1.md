# Literature-to-Mechanism Card — Reversal, Liquidity, and Industry Adjustment V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Category: `H — literature / mechanism research`
Status: `FUTURE_RESEARCH / CONTRACT_PENDING / NO CANDIDATE`

## Question

Does the literature point to a genuinely new IDX-Trade mechanism beyond the
already audited C1 residual reversal, C2 participation confirmation, and
H-LIQ-01 temporal-liquidity representations?

## Literature synthesis

The literature supports a conditional, mechanism-based view of short-horizon
reversal rather than a generic “reversal always works” claim:

- Campbell, Grossman, and Wang connect return autocorrelation to trading
  volume and risk-sharing/liquidity trades; the sign and persistence of the
  return-volume interaction matter. See the [NBER working paper](https://www.nber.org/papers/w4193).
- Dai, Medhat, Novy-Marx, and Rizova find that volatility and turnover affect
  the speed and persistence of reversal, including outside the US. See the
  [NBER working paper](https://www.nber.org/papers/w30917).
- Butt, Högholm, and Sadaqat report stronger emerging-market reversal in
  smaller/illiquid and more volatile names, consistent with liquidity
  provision. See the [SSRN paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3105846).
- Da, Liu, and Schaumburg distinguish liquidity-shock-driven long-side
  reversal from sentiment/short-sale-constraint effects on the short side. See
  the [SSRN paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2022061).
- Recent international work argues that industry-adjusted reversal can differ
  materially from raw reversal when industry components mask firm-specific
  shocks. See the [SSRN paper](https://papers.ssrn.com/sol3/Delivery.cfm/6630998.pdf?abstractid=6630998&mirid=1&type=2).

These are literature mechanisms, not IDX evidence.

## Mapping to the available lane

| Mechanism | Existing local representation | New information needed | Disposition |
|---|---|---|---|
| Raw short-horizon reversal | C1 | None for structural review; predictive target still blocked | Already covered; do not create another raw reversal candidate |
| Return-volume/liquidity interaction | C2, H-LIQ-01, H-FRAG/EXECSTATE diagnostics | Independent field semantics and executable-capacity evidence | Likely overlapping; no new candidate now |
| Volatility-conditioned reversal | Existing market-state/robustness diagnostics plus C1/C2 | Target-free state contract is available, but outcome testing is protected | Structural question already substantially covered; do not sweep variants |
| Industry/sector-adjusted reversal | Sector archive only has 2022/2023 snapshots and no daily PIT membership | Daily membership intervals, publication timing, identity continuity, revisions | Genuine future opportunity, not currently implementable |
| Liquidity-shock versus information shock | OHLCV/volume and partial execution state | PIT event/news or authoritative order-flow/identity fields | Contract missing; no candidate |

## Scientific decision

The literature search does not justify a new candidate under current data.
Most immediately available mechanisms are already represented by C1/C2/H-LIQ
or were structurally audited. The industry-adjusted direction is genuinely
distinct enough to preserve as a future specification, but the local sector
archive cannot be expanded into a daily PIT-safe feature. The current result is
therefore a useful negative/re-entry specification rather than an alpha claim.

## Future specification, when data admission exists

If an authoritative sector-history package becomes available, define one fixed
industry-adjusted reversal contract before any target read:

1. freeze sector membership as-of each decision date using publication time;
2. compute the stock's prior return residual to its sector on the same frozen
   universe and session calendar;
3. retain explicit singleton/missing-sector rules and identity transitions;
4. compare its structural overlap to C1/C2/C4 before considering evaluation;
5. do not add both raw and industry-adjusted forms to the protected packet
   without a separate frozen candidate-budget decision.

This is a future research specification only. It is not a candidate ID,
feature artifact, or authorization to use protected outcomes.

## Boundaries

No target/outcome, IC/ICIR/OOS, provider/network, cloud, incumbent,
canonical/capture/scheduler/telemetry, or production state was accessed or
modified. No code or data artifact was created from the literature claims.
