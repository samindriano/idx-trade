# Alpha Frontier Research V1 — Bootstrap

Date: 2026-08-26 Asia/Jakarta
Branch: `research/idx-alpha-frontier-v1`
Status: `FOREIGN FLOW MECHANISM DISCOVERY / PHASE A`

## Purpose

Open a clean challenger-research lane for new alpha discovery without retuning or modifying the frozen incumbent V4-X1 / Decision V2 / Sizing V1 / Execution V1 stack.

The initial pilot is **Foreign Flow Mechanism Discovery V1**. The purpose is not to rescue the closed Foreign Flow V2 model experiment. It is to understand the information family more deeply before forming new predictive hypotheses.

## Hard boundaries

- V4-X1 incumbent remains frozen.
- Decision V2, Sizing V1, and Execution V1 remain frozen.
- Do not use prospective protected outcomes or Outcome Vault to generate/tune hypotheses.
- Do not change production capture/runtime behavior from this research branch.
- Historical V1/V2 Foreign Flow folds are development/discovery laboratory only, not untouched confirmation data.
- A failed exact historical experiment is not rewritten as a success.
- Phase A is descriptive/outcome-blind: no future-return calculation, IC, Sharpe, TP/SL outcome, or model fitting.

## Historical interpretation reset

`FOREIGN_FLOW_V2_CORE_NO_SURVIVOR` remains final for the exact prior question: adding the frozen eight-feature Foreign Flow V2 block to the Clean V2 HGB control for the binary H10 target did not improve the preregistered gate.

That verdict does **not** establish that the entire Foreign Flow data family has no edge in all horizons, state-dependent roles, or trading architectures.

Financial PIT is treated similarly: its prior exact H10 additive challenger failed, but that does not close every slower-moving/event/relative-value financial hypothesis.

## Phase A notebook

Human-facing notebook:

`notebooks/07_foreign_flow_mechanism_discovery.ipynb`

It covers:

- representation identity and coverage;
- missingness;
- signal distributions;
- extreme Foreign Flow observations and repeated extreme tickers;
- 5-session vs 20-session persistence;
- ticker-level drill-down;
- optional raw-flow long-memory views using 5/20/60/120/250-session directional balance.

The optional long-memory representation is descriptive only:

`sum(foreign_net) / sum(foreign_buy + foreign_sell)`

It is not an accepted alpha feature and is not connected to future returns in Phase A.

## Research questions for Phase A

1. Is source/feature coverage stable through time?
2. Which Foreign Flow representations are sparse and why?
3. Are pressure/shock distributions symmetric or heavily skewed?
4. Are extreme observations genuine market phenomena or denominator/source artifacts?
5. Are extreme observations concentrated in repeated tickers?
6. Does short-term persistence contain a materially different state from medium-term persistence?
7. Do long-memory 60/120/250-session states look meaningfully different from 5/20-session states?
8. Which phenomena are sufficiently coherent to justify a frozen predictive hypothesis?

## Phase B boundary

Only after Phase A observations are written down do we authorize a separately frozen historical-development outcome-opening study.

Current intended maximum outcome horizons are:

`H1 / H3 / H5 / H10 / H20`

Signal formation may use substantially longer historical memory, including 60/120/250-session accumulation states, without extending the trading outcome horizon beyond H20.

Phase B should begin with interpretable event/quantile/decay diagnostics rather than model fitting. Incremental model comparison versus the incumbent belongs later.

## Other frontier data families retained

After the Foreign Flow pilot methodology matures, the true-new frontier shortlist remains:

- P0: SBL / securities lending / lendable-stock;
- P0: broker × stock × buy/sell side, if sourceable;
- P1: historical index membership;
- P1: UMA event history;
- P2: structured-warrant / underlying activity.

Historical ownership/KSEI, free-float/HSC, structural share-supply, and suspension work should reuse existing evidence rather than restart generic source discovery.
