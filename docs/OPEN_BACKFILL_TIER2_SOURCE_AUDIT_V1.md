# Historical Open Backfill — Tier-2 Source Audit V1

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-tier2-audit-v1`
Parent evidence: Tier-1 Wildan runtime + independent review on `data/idx-open-backfill-v1`.

## Purpose

Evaluate whether a second external source can provide genuinely additional historical `Open` evidence for the immutable 1260-session IDX signal panel without relaxing the existing execution-data admission contract.

Tier-1 Wildan is closed as a missing-Open recovery source: it preserved H/L/C perfectly on known overlap but recovered 0 of 446,843 missing Open rows under the frozen contract. Tier-2 must therefore test sources with genuinely different upstream semantics before any bulk backfill is authorized.

## Frozen immutable input

- panel window: `2021-04-29 -> 2026-07-31`;
- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- ACTIVE rows: 981,940;
- initial unresolved Open rows after Tier-1: 446,843;
- existing non-null Open values are immutable;
- `execution_grade_promoted=false` remains mandatory.

## Source order

### Candidate A — Zapi IDX

Public documentation currently exposes `finance:idx / stock-summary` with:

- historical `date` parameter;
- optional ticker `code` filter;
- `length` up to 1000 rows;
- free account availability without a credit card;
- free quota documented as 2,000 billable requests/month and 100 requests/minute.

However, every Zapi endpoint has a `minPlan`; the public page does not establish that `stock-summary` is callable on Free. The runtime audit must therefore determine plan eligibility before using quota. If a credential is absent or the endpoint requires an upgrade, classify Zapi as `BLOCKED`, not failed data quality.

No Zapi API key may be committed, printed in handoffs, or embedded in artifacts. Read it only from a local environment variable or other non-Git secret mechanism.

### Candidate B — Yahoo Finance via yfinance

`yfinance` is an unofficial client using Yahoo Finance public APIs and explicitly describes the Yahoo Finance API as intended for personal use. It is acceptable only as a bounded personal-research candidate source, not automatically as an execution-grade authority.

Yahoo rows must be treated as raw provider evidence and must pass the same H/L/C and raw-price-semantic checks before any Open can be admitted.

## Audit shape

This is a **pilot audit only**, not a 979-ticker bulk backfill.

Construct a deterministic adversarial sample from the immutable panel. Target approximately 50 unique ticker/date rows and preserve the exact sample manifest/hash. Include, where data permits:

1. at least 20 rows with an existing certified/non-null Open for known-answer validation;
2. at least 20 rows whose panel Open is null and for which Tier-1 Wildan had a secondary row;
3. at least 5 rows whose panel Open is null and Wildan had no row;
4. explicit coverage of `FREN`, `MASA`, and `MFIN` where applicable;
5. large liquid names such as `BBCA`/`BBRI` where applicable;
6. IPO/new-listing, suspension/resumption, ticker-identity edge cases, and corporate-action-adjacent dates when deterministically identifiable from repository evidence.

Use a fixed seed and deterministic ordering. Do not choose rows based on whether a candidate provider looks favorable.

## Frozen admission rules

For a candidate provider row to be considered `ADMISSIBLE_OPEN_EVIDENCE`:

- ticker/security identity matches;
- session date matches exactly;
- candidate raw High equals certified panel High;
- candidate raw Low equals certified panel Low;
- candidate raw Close equals certified panel Close;
- candidate raw Open is finite and `> 0`;
- candidate raw Open lies within `[certified Low, certified High]`;
- no adjusted-price substitution is used;
- no existing panel Open is overwritten.

Known-answer rows additionally report exact Open agreement with the existing panel Open.

Do not average sources, vote between prices, synthesize Open, forward-fill, infer from previous close, or loosen equality after inspecting results.

## Required source-level metrics

For each source separately report:

- source access status and plan/credential status;
- requested rows;
- rows returned;
- exact ticker/date coverage;
- H/L/C exact-match count/rate;
- known-answer Open exact-match count/rate;
- missing-Open rows with valid candidate Open;
- missing-Open rows passing the full frozen admission contract;
- rejection breakdown by reason;
- corporate-action/identity anomalies;
- request count, errors, and rate-limit behavior;
- raw response/artifact hashes without secrets.

## Decision gate

A source may advance to a separately authorized bulk Tier-2 backfill only if all are true:

1. access/licensing posture is acceptable for the project's personal exploratory research scope;
2. known-answer H/L/C agreement is sufficiently strong to support common raw-price semantics;
3. known-answer Open agreement does not indicate systematic transformation/adjustment mismatch;
4. at least some currently-missing Open rows supply valid additional Open evidence under the unchanged contract;
5. no evidence suggests silent adjusted/raw mixing, date shifts, or security-identity mismapping.

The pilot does not itself promote execution grade and does not authorize execution-PnL research.

## Stop conditions

Stop and report `BLOCKED` if credentials, plan eligibility, rate limits, or source terms prevent a clean audit.

Stop and report `REJECTED_SOURCE` if the candidate produces systematically incompatible raw-price semantics or no genuinely additional Open evidence.

Stop after the pilot. Do not bulk-fetch 446,843 target rows, do not modify the immutable panel, do not rerun Stage 5, do not alter Ranking V2, do not paper/live trade, and do not merge `main`.