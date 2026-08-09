# Open Backfill Tier-2 — Independent Review

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-tier2-audit-v1`
Reviewed runtime commit: `cecca565b9678d76b58681508078321a33f4d7a2`

## Decision

**`TIER2_PILOT_ACCEPTED_BULK_BACKFILL_BLOCKED_YAHOO_SEMANTICS_FOLLOWUP_AUTHORIZED`**

The bounded Tier-2 runtime is accepted as a valid source-audit experiment. The immutable 1260-session panel was preserved, the sample was constructed before provider outcomes were observed, the frozen H/L/C + positive/in-range Open gate was not relaxed, and no candidate value was written into the panel.

This review does **not** authorize bulk historical Open ingestion or execution-grade promotion.

## Source decisions

### Zapi

Status remains **BLOCKED / UNTESTED**.

No `ZAPI_API_KEY` was present, so zero requests were made. No conclusion about Free-tier access, plan gating, coverage, or data quality is permitted from this run.

### Yahoo / yfinance

Status is **PROMISING BUT NOT BULK-READY**.

Observed pilot evidence:

- 8 ticker-bounded requests;
- 1,035 provider rows returned;
- exact sampled ticker/date rows: 8/50;
- exact H/L/C: 7/8;
- known-Open exact: 4/5 among returned known-Open rows;
- 3 missing-Open rows passed the unchanged admission contract: `AADI 2024-12-05`, `ALDO 2024-07-08`, `BREN 2024-05-06`;
- FREN/MASA/MFIN produced explicit provider errors/no-timezone outcomes;
- BBCA `2021-08-03` was correctly rejected because Yahoo prices were on a different corporate-action scale from the certified raw exchange panel.

The BBCA mismatch is exactly factor 5 across OHLC (`6025/6180/5985/6145` versus `30125/30900/29925/30725`). BBCA subsequently executed a 1:5 stock split on 2021-10-13. This strongly supports a **split-normalization / historical price-scale hypothesis** for Yahoo relative to the certified raw exchange panel. It is evidence for a bounded semantics-reconstruction audit, not permission to transform values automatically.

## Important pilot limitation

The 50-row sample is deterministic and outcome-independent, but it is not broad cross-sectional evidence.

The runtime made 8 Yahoo requests and `run_yahoo_audit()` makes exactly one request per unique sampled ticker. Therefore the 50 sampled rows contain only 8 unique tickers. The sample-selection implementation prioritizes the named `PREFERRED_SAMPLE_TICKERS` before filling quotas, so the pilot is concentrated in the adversarial/named set.

This is appropriate for finding failure modes, but it is insufficient to estimate universe-wide Yahoo coverage or known-answer agreement. Do not extrapolate `3/30` missing-Open recovery or `4/5` known-Open agreement to the full 446,843-row gap.

## Authorized next bounded work

A separate Yahoo semantics/coverage follow-up is authorized before any bulk backfill.

Required questions:

1. Can Yahoo historical OHLC be transformed back to certified raw exchange units using independently verified stock-split events, without dividend adjustment and without changing any signal/model semantics?
2. Does the transformed H/L/C exactly reproduce certified panel H/L/C on a materially broader known-answer sample?
3. What is Yahoo availability across a broad, deterministic ticker sample rather than only the eight preferred edge tickers?
4. Are provider failures concentrated in delisted/renamed/identity-edge securities, or common across ordinary listed securities?
5. Does a split-aware reconstruction recover pre-split rows such as BBCA exactly, including Open, while leaving already-compatible rows unchanged?

Minimum follow-up design:

- deterministic, outcome-independent sample;
- at least 100 unique tickers if provider limits permit;
- balanced known-existing-Open and missing-Open rows;
- explicit split and non-split strata;
- official/PIT-safe split evidence preferred for scale reconstruction;
- Yahoo `Adj Close` must remain excluded from execution prices;
- no dividend-based adjustment;
- transformed candidate H/L/C must still exactly match the certified panel before Open can be admitted;
- existing panel Open remains immutable;
- no bulk write to the 1260 panel;
- runtime artifacts remain outside Git.

Zapi may be audited independently later if a local Free-tier credential becomes available. Its absence must not block the Yahoo semantics follow-up.

## Permanent guardrails

- `execution_grade_promoted=false`;
- 446,843 unresolved Open rows remain the official baseline until a separately authorized backfill writes an audited derivative;
- do not average/vote sources;
- do not synthesize Open;
- do not use previous Close as Open;
- do not loosen H/L/C equality after observing provider outcomes;
- no Stage-5 rerun or Ranking-V1 rescue;
- no execution-PnL, paper trading, live trading, or main merge from this review.
