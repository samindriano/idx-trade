# IDX-Trade — Transaction-Cost, Slippage, and Capacity Audit V1

Date: 2026-09-20 (Asia/Jakarta)

Status: `STRUCTURAL COST MODEL PASS / EXECUTABLE ECONOMICS UNKNOWN`

This checkpoint audits the cost and capacity assumptions that connect turnover
to portfolio economics. It is not a return, PnL, or hidden-outcome analysis.
No provider, production, canonical, cloud, capture, or protected state was
accessed or changed.

## 1. Runtime cost contract

Pinned runtime: `045e25a19d9f71170d2c863e768102937e59ad73`.

The execution contract declares:

- buy fee: 15 bps;
- sell fee: 25 bps;
- slippage: 10 bps per side;
- stamp duty: Rp10,000 above Rp10,000,000 account-level daily turnover;
- sizing reference price: verified raw close at T;
- sell projection: raw close at T minus primary slippage;
- buy execution: raw Open plus primary slippage;
- capacity reference: verified regular-market-value causal EOD;
- maximum order notional: 1% of reference-day value;
- fill semantics: simulated paper Open plus slippage, not a broker-fill claim.

The fee/slippage components sum to a nominal 60 bps round-trip before stamp
duty when a position is sold and replaced. This aligns with the historical
structural friction diagnostic, but does not make the cost empirically valid.

## 2. What is enforced

Static/runtime checks provide useful bounded safeguards:

- effective buy/sell prices are deterministic transformations of the supplied
  raw price;
- fee arithmetic is applied to gross filled notional;
- stamp duty is applied at the account turnover threshold;
- capacity limits convert reference value into maximum lots;
- cash and fee affordability are checked;
- zero/partial capacity can create pending execution state;
- whole-lot and non-negative-cash invariants are checked;
- the simulated fill is explicitly not represented as a broker execution claim.

These controls make the paper simulation internally reproducible under its
declared assumptions.

## 3. What remains unproven or incomplete

### 3.1 Fixed slippage is an assumption, not calibration

The config labels the slippage reference
`PREREGISTERED_ASSUMPTION_NOT_EMPIRICALLY_CALIBRATED`. There is no evidence in
the admitted system for spread, queue position, volatility-dependent impact,
opening-auction mechanics, order size relative to live depth, or adverse
selection.

Therefore a 10 bps per-side result is a scenario, not an estimate of realized
execution cost.

### 3.2 Fixed fees do not capture policy/time variation

The fee reference is a Stockbit snapshot dated 2026-08-05. The model does not
show a time-varying fee schedule, account-specific commission contract, tax
policy, or broker-rule lineage. Dividend tax is separately unresolved in the
cash-accounting audit.

### 3.3 Regular-market-value is only a capacity proxy

The capacity denominator is regular-market-value, not historical ADV, traded
value, spread, queue, or fill probability. The source contract itself says the
fill is simulated rather than broker-observed.

Historical structural capacity work correctly labels this as:

`PASS_STRUCTURAL_ONLY / CAPACITY REMAINS UNADMITTED`

and

`PASS_STRUCTURAL_ONLY / EXECUTABLE CAPACITY BLOCKED`.

### 3.4 Capacity is not a portfolio-level execution budget

The per-name 1% reference-value limit is applied to individual orders. It does
not by itself model simultaneous orders competing for the same market liquidity,
opening auction congestion, correlated names, or a session-level liquidity
budget. A ten-name replacement can pass each per-name test while the aggregate
order set is operationally large.

### 3.5 Partial fill semantics are asymmetric

The system has explicit pending handling for zero/partial exits, but the prior
audit found that a positive partial BUY can be held without preserving the
unfilled planned remainder. This is a cost/capacity issue as well as an
accounting issue: the model can understate future intended turnover and future
cost if the residual is silently discarded.

## 4. Historical structural friction evidence

The fixed 600-session structural diagnostic used one-way turnover times 60 bps
base and 110 bps sensitivity. Its results were:

| Surface | Mean turnover | Q95 | Q99 | Max | Base burden mean / Q99 / max |
|---|---:|---:|---:|---:|---:|
| C1 | 42.1536% | 56.6667% | 63.3333% | 66.6667% | 25.2922 / 38.00 / 40.00 bps/NAV |
| C2 | 32.9104% | 50.0000% | 56.6667% | 63.3333% | 19.7462 / 34.00 / 38.00 bps/NAV |
| C4 | 23.6950% | 36.6667% | 40.0000% | 46.6667% | 14.2170 / 24.00 / 28.00 bps/NAV |
| H-LIQ-01 | 10.3061% | 16.6667% | 20.0000% | 26.6667% | 6.1836 / 12.00 / 16.00 bps/NAV |
| H-VOL-01 | 29.7718% | 43.3333% | 50.0000% | 53.3333% | 17.8631 / 30.00 / 32.00 bps/NAV |
| H-EXC-02 | 41.5971% | 56.6667% | 66.7333% | 86.6667% | 24.9583 / 40.04 / 52.00 bps/NAV |

The same audit measured low-value and dollar-turnover concentration. H-LIQ-01
and H-VOL-01 had Q1 market-value shares of 39.6722% and 40.6889%; H-EXC-02 had
the highest turnover tail. These are descriptive structural diagnostics only.

The interpretation is important: a lower mean turnover or lower proxy burden
does not prove better economics when the denominator is not executable capacity
and the cost is not empirically calibrated.

## 5. Interactions that matter system-wide

1. **Decision churn × fixed friction:** high replacement rates repeatedly pay the
   same nominal cost and can make small structural edge claims uneconomic.
2. **Capacity × partial fills × state:** a capacity-limited order changes
   holdings, cash, pending state, and next-session Decision reconciliation.
3. **Open availability × slippage:** missing or source-ambiguous Open prevents
   the execution-price contract from being evaluated, even when ranking data
   is available.
4. **CA projection × sizing × cost:** projected cash/NAV can change lot count;
   if the persisted CA hash describes the unprojected state, the cost and
   capacity audit is attached to the wrong sizing state.
5. **Nominal fee model × tax:** a 60 bps nominal round trip plus stamp duty is
   not a complete net-cost model while dividend tax remains unresolved.
6. **Per-name capacity × aggregate session load:** ten individually permitted
   orders can still exceed a realistic opening-liquidity budget.

## 6. Verdict

`COST_ARITHMETIC_PASS_BOUNDED / EXECUTABLE_ECONOMICS_UNKNOWN`

The current model is a deterministic paper-cost scenario with local cash/lot/
capacity guards. It is not evidence of realized fills, executable capacity, or
net profitability.

## 7. Highest-value next tests

Without opening protected outcomes, the next useful synthetic tests are:

- aggregate session liquidity budget across simultaneous buy/sell orders;
- spread/volatility/size-dependent slippage scenarios;
- fee/tax policy versioning and exact ledger replay;
- partial-buy residual preservation and future cost accounting;
- CA-projected NAV/cost hash consistency;
- restart after a partially filled, fee-charged order;
- explicit distinction between capacity-limited, Open-missing, and risk-held
  cash.

No provider call, model sweep, retry, or production mutation was performed.

