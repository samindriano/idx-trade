# Historical Open Backfill — Targeted Zapi Residual Audit V1

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-residual-audit-v1`
Parent evidence: accepted Yahoo full-universe census plus residual diagnostic on `data/idx-open-backfill-yahoo-census-v1`.

## Decision

**`ZAPI_TARGETED_RESIDUAL_AUDIT_SPEC_FROZEN_IMPLEMENTATION_LOCAL_VERIFY_REQUIRED`**

This stage audits Zapi only as a bounded independent Source-2 candidate. It does not authorize bulk backfill, execution-grade promotion, corporate-action repair, modelling, Stage-5 work, paper/live trading, or merge to `main`.

## Why this audit exists

Yahoo reduced unresolved historical Open from `446,843` rows to `49,476`. The residual diagnostic separated the remaining rows into materially different problems:

- `32,103` provider H/L/C mismatches without a usable verified split factor;
- `8,804` rows with incomplete official corporate-action evidence;
- `3,840` ordinary no-provider rows;
- `2,876` rows across five Yahoo provider/symbol-error tickers (`FREN`, `MASA`, `MFIN`, `RMBA`, `TURI`);
- `1,853` verified-factor reconstruction failures.

Zapi is **not** being tested against all `49,476` rows. The first audit targets only:

1. Yahoo provider gaps/errors, where a genuinely independent provider may supply missing raw OHLC evidence;
2. Yahoo H/L/C mismatch rows without a verified split factor, where Source-2 can arbitrate whether its raw H/L/C agrees with the certified panel, agrees with Yahoo, or disagrees with both;
3. known-existing-Open controls for source-quality validation.

The `10,657` corporate-action-related residual rows are intentionally excluded from Source-2 recovery in this stage. They require a separate official-evidence/reconstruction track.

## Source and access posture

Candidate Source-2: Zapi IDX `stock-summary`.

Current public documentation exposes historical `date`, optional ticker `code`, pagination up to `length=1000`, and fields including `OpenPrice`, `High`, `Low`, and `Close`. A free account/API key is publicly offered, but endpoint-level plan gating remains possible and must be tested empirically at runtime.

Runtime rules:

- API key only from local `ZAPI_API_KEY`;
- never commit, print, hash, or persist the key;
- if credential is absent, stop as `ZAPI_BLOCKED_CREDENTIAL_ABSENT`;
- if endpoint returns plan/access gating, stop as blocked rather than treating it as data failure;
- no attempt to bypass plan, authentication, quota, or rate limits;
- no bulk endpoint;
- no direct IDX scraping/crawling.

## Immutable inputs

Panel:

- window: `2021-04-29 -> 2026-07-31`;
- rows: `981,940`;
- immutable SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

Yahoo census artifacts are read-only inputs from the accepted external runtime root:

- `yahoo_open_census_row_audit.parquet`;
- `provider_ticker_status.csv`.

The immutable panel and Yahoo artifacts must not be rewritten.

## Frozen sample

Seed: `20260811`.

Target sample: up to `240` rows:

- `120` `RESIDUAL_HLC_MISMATCH` rows from the `32,103` no-factor mismatch class;
- `80` `RESIDUAL_PROVIDER_GAP` rows from ordinary no-provider plus provider/symbol errors;
- `40` `KNOWN_CONTROL` rows where the immutable Open exists and Yahoo already passed exact H/L/C + Open known-answer validation.

Selection must be provider-outcome-independent and deterministic. It must:

- represent every available year before filling additional rows;
- maximize ticker diversity before taking second rows from the same ticker;
- include at least one row from each of the five Yahoo provider-error tickers when such residual rows exist;
- preserve exact sample manifest and SHA before querying Zapi.

No corporate-action residual row may enter the targeted sample.

## Request strategy

Prefer one `stock-summary` request per unique selected date with `length=1000`, then retain only sampled ticker/date rows from that response. This reduces quota consumption and avoids unnecessary per-row calls.

- bounded retries only;
- explicit handling for HTTP 429;
- rate-limit-aware spacing;
- stop immediately on confirmed plan/access gating;
- record request count, retry count, rate-limit events, unique dates, and redacted errors.

## Frozen admission contract

A Zapi row is a recovery candidate only when:

- ticker/security identity matches the sample ticker;
- session date matches exactly;
- Zapi High equals certified panel High exactly;
- Zapi Low equals certified panel Low exactly;
- Zapi Close equals certified panel Close exactly;
- raw `OpenPrice` is finite and `> 0`;
- raw `OpenPrice` lies inside certified `[Low, High]`;
- no existing panel Open is overwritten.

No adjustment, averaging, interpolation, previous Close substitution, or source voting is allowed.

A row passing this contract is **diagnostic recovery evidence only**. This audit does not write it into the panel or authorize bulk use.

## Arbitration contract

For `RESIDUAL_HLC_MISMATCH` rows, classify Source-2 evidence as:

- `SOURCE2_SUPPORTS_CERTIFIED_PANEL`: Zapi H/L/C exactly equals certified panel H/L/C;
- `SOURCE2_SUPPORTS_YAHOO`: Zapi H/L/C exactly equals the preserved Yahoo raw H/L/C instead;
- `THREE_WAY_DISAGREEMENT`: Zapi matches neither panel nor Yahoo;
- `SOURCE2_NO_ROW`: no exact Zapi ticker/date row.

For `RESIDUAL_PROVIDER_GAP` rows:

- `SOURCE2_RECOVERY_CANDIDATE`: full frozen panel-H/L/C + valid Open contract passes;
- otherwise retain the exact rejection reason.

Known controls separately measure panel H/L/C agreement and exact Open agreement.

## Decision gate after runtime

The audit may justify a later targeted Zapi backfill proposal only if all are true:

1. access/plan posture is usable for the project's personal research scope;
2. known controls show strong raw H/L/C and Open agreement;
3. Source-2 supplies genuinely additional admissible evidence on Yahoo provider gaps and/or materially clarifies the no-factor H/L/C class;
4. no systematic date shift, adjusted/raw mixing, identity mismatch, or unexplained source transformation appears.

Even if the audit passes, bulk backfill requires a separate independent review and authorization.

## Required outputs

- exact branch/HEAD and test result;
- panel SHA before/after;
- exact sample manifest + SHA;
- role/year/ticker diversity counts;
- Zapi credential/plan/access status without secret leakage;
- requests, retries, rate-limit events, unique dates;
- rows returned and exact ticker/date coverage;
- known-control H/L/C and Open exact rates;
- provider-gap recovery-candidate count;
- no-factor arbitration counts;
- rejection histogram;
- candidate rows, row audit, arbitration table, summary, and artifact hashes;
- `execution_grade_promoted=false`;
- `bulk_backfill_authorized=false`.

## Stop boundary

After the bounded Zapi runtime completes, STOP for independent ChatGPT review.

Do not:

- query another Source-2 in the same run;
- touch the corporate-action residual track;
- write candidate values into the immutable panel or Yahoo derivative;
- run execution PnL;
- change Ranking V1/V2, Probability, PIT-sector research, or Stage 5;
- paper/live trade;
- integrate a broker;
- merge to `main`.
