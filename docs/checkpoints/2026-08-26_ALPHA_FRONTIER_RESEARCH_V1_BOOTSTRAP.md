# Alpha Frontier Research V1 — Bootstrap

Date: 2026-08-26 Asia/Jakarta
Branch: `research/idx-alpha-frontier-v1`
Status: `DISCOVERY / HYPOTHESIS FORMATION`

## Purpose

Open a clean challenger-research lane for genuinely new alpha information without retuning or modifying the frozen incumbent V4-X1 / Decision V2 / Sizing V1 / Execution V1 stack.

This checkpoint exists to prevent the project from rediscovering or rebuilding historical data lanes that were already audited, rejected, or partially solved.

## Hard boundaries

- V4-X1 incumbent remains frozen.
- Decision V2, Sizing V1, and Execution V1 remain frozen.
- Do not use prospective protected outcomes or Outcome Vault to generate/tune hypotheses.
- Do not change production capture/runtime behavior from this research branch.
- New work begins with source semantics and hypothesis formation, not model fitting.
- Historical research must remain PIT-aware; source `as_of_date` is not automatically `knowledge_at`.
- A failed historical idea is not reopened merely because its old branch was archived/deleted.

## Historical inventory — do not rediscover

### Already alpha-tested

1. **Financial PIT / representation**
   - Historical financial source/representation work exists.
   - 52-feature financial challenger was evaluated on common support.
   - Final conclusion: no survivor versus the clean control.
   - Do not restart generic financial-ratio feature search without a materially new hypothesis or data representation.

2. **Foreign Flow**
   - Official IDX `TradingSummary/GetStockSummary` / Zapi foreign-flow semantics were audited.
   - Historical Foreign Flow V2 representation and alpha experiment exist.
   - Final conclusion: no survivor versus control.
   - Do not recycle rolling foreign-buy/sell/net features as a new frontier.

### Source/data work already deep, but not fully alpha-tested

3. **Ownership / KSEI**
   - PR #23 performed a bounded source audit.
   - Zapi IDX ownership-file categories were discovered: `lima-persen`, `satu-persen`, `klasifikasi`, `tipe`.
   - Zapi KSEI endpoints `ownership`, `demographics`, and `distribution` were audited.
   - Per-security KSEI ownership exposes local/foreign totals plus nine investor categories per side.
   - Direct KSEI vs Zapi parity passed 198/198 sampled fields across BBCA/AADI/BBRI and May/June/July 2026.
   - Direct KSEI archive samples were verified from 2021-12 through 2026-07.
   - Binding blocker was historical PIT publication/version timing: position date exists, but timezone-resolved first-publication time and immutable correction lineage were not established.
   - Do not repeat basic ownership source discovery. Reopen only if publication/version metadata can be improved or a separately justified conservative knowledge-time policy is preregistered.

4. **Free float / ownership concentration / HSC**
   - Multiple source/reconstruction lanes already exist historically.
   - Official statutory free-float reports, LBRE monthly history, correction lineage, and HSC event ledger were investigated.
   - LBRE monthly acquisition covered 2024-04 through 2026-06 but retained unresolved lineage/conflict cases.
   - HSC full-history ledger reached a bounded state suitable for an ownership-concentration contract, but no final alpha experiment was completed.
   - Reuse historical evidence; do not restart generic free-float scraping.

5. **Share supply / dilution / structural corporate actions**
   - `ListingActivity/GetIssuedHistory` and Zapi raw parity were already audited in Corporate Actions work.
   - Historical inventory included stock splits, HMETD/rights, bonus shares, stock dividends, capital reductions, and other share-structure events.
   - Endpoint revision behavior and effective-date semantics require care.
   - A future `share_supply_growth` / dilution alpha hypothesis can reuse this lineage; no new generic IssuedHistory source lane is needed first.

6. **Suspension / resumption**
   - Official IDX suspension/resumption ingestion and market-specific state handling already exist historically.
   - Do not rebuild source ingestion solely to test event alpha.

### Explicitly deprioritized / rejected as interpreted signal

7. **Margin summary as leverage/crowding flow**
   - Historical Broker/Margin source audit concluded that the available margin view does not establish actual margin-financing usage/flow.
   - Final interpretation rejected margin-usage/leverage/crowding features.
   - Do not revive this interpretation without genuinely new source semantics.

8. **Existing Broker Summary**
   - Existing source is aggregate broker × day and does not provide the desired stock × broker × buy/sell-side decomposition.
   - Aggregate Broker Summary alone is not the intended new stock-selection signal.

## True frontier shortlist after historical de-duplication

### P0 — SBL / securities lending / lendable-stock

No material prior IDX-Trade research/data lane was found for lendable-stock/SBL/SLB/borrow-fee semantics.

Questions to resolve before any feature work:
- Is reported volume lendable availability, actual borrowed volume, or another inventory concept?
- What exactly do `regularBorrowFee` and `frontEndBorrowFee` represent?
- Is historical data available daily, and how far back?
- Are entry/exit from the lendable universe meaningful state changes?
- What are publication time, revision, and missing-row semantics?
- Can current Zapi output be reconciled to official IDX/KPEI/KSEI source artifacts?

Potential hypotheses only after semantics are certified:
- lendable supply scarcity;
- borrow-fee pressure;
- change in lendable capacity;
- entry/exit from lendable universe;
- interaction with momentum, liquidity, ownership, or future broker-flow data.

Do not label lendable volume as `short interest` until source semantics prove it.

### P0 — Broker × stock × side

Desired information family is not the existing aggregate Broker Summary.

Ideal normalized schema:
- `date`
- `stock_code`
- `broker_code`
- `buy_value`, `buy_volume`, `buy_frequency`
- `sell_value`, `sell_volume`, `sell_frequency`
- `net_value`, `net_volume`
- source publication/provenance metadata

Potential hypotheses:
- persistent broker accumulation/distribution;
- buyer/seller concentration;
- broker entropy;
- repeat top-buyer/top-seller behavior;
- broker rotation/crowding.

First determine whether an official/raw upstream endpoint exists. If not, this is a high-priority candidate to request from Zapi development.

### P1 — Historical index membership

Need actual constituent membership history, not merely Index Summary levels.

Desired fields:
- `index_code`
- `stock_code`
- `effective_from`
- `effective_to`
- `weight` when available
- publication/announcement time and provenance

Potential hypotheses:
- inclusion/exclusion anticipation and post-effective drift;
- passive-flow pressure;
- constituent-status interactions with liquidity/momentum.

### P1 — UMA event history

No material prior dedicated UMA research lane was found.

Potential hypotheses:
- pre-UMA run-up state;
- continuation vs reversal after UMA;
- repeated UMA intensity;
- interaction with liquidity, ownership, or attention.

Source timing and event semantics must be certified before feature construction.

### P2 — Structured warrants / underlying activity

Potentially useful as a derivative-attention / hedging / speculative-demand proxy, but lower priority until P0/P1 sources are characterized.

## Preferred Zapi requests after existing-surface audit

Do not ask for wrappers that already exist. Highest-value missing products are likely:

1. **Broker × stock × side daily flow**, if sourceable.
2. **Ownership publication/version metadata** or an immutable prospective first-seen archive:
   - `sourcePublishedAt` when truly known;
   - `firstSeenAt`;
   - `revisionId` / supersession lineage;
   - source file SHA and URL.
3. **Historical index membership** with effective dates and weights.
4. **Historical SBL/lendable series** if current endpoint does not expose sufficiently deep history.

## Research order

1. Build a source/information-family map.
2. Audit P0 source semantics and historical depth.
3. Write economic mechanism hypotheses before looking at target performance.
4. Preregister feature definitions, horizons, universe, and acceptance/rejection criteria.
5. Perform descriptive/EDA diagnostics without target mining.
6. Run simple univariate / cross-sectional predictive tests.
7. Test stability by time, regime, liquidity, and universe slices.
8. Only then test incremental value against the frozen incumbent/control.
9. Promote only if the effect survives common-support, cost/turnover, and robustness checks.

## Current next action

Begin with a bounded **SBL/lendable-stock source and semantics audit**, while separately checking whether broker × stock × side and historical index membership are obtainable from existing official/Zapi raw surfaces before requesting new Zapi endpoints.
