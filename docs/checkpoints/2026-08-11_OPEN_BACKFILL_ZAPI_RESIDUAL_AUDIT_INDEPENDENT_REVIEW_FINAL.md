# Targeted Zapi Residual Audit — Independent Review Final

Date: 2026-08-11 (Asia/Jakarta)
Reviewed branch: `data/idx-open-backfill-zapi-residual-audit-v1`
Reviewed runtime commit: `c640ac8742ab20188eead6ce3e52c8178522fb3a`

## Decision

**`ZAPI_OPEN_RECOVERY_REJECTED_HLC_ARBITER_ACCEPTED_SOURCE3_SCREENING_AUTHORIZED`**

The final credentialed Zapi audit is accepted as valid bounded evidence. Zapi is rejected as a historical Open-recovery source under the tested `finance:idx/stock-summary` semantics, but accepted as useful independent H/L/C corroboration evidence.

This review does not authorize bulk Zapi backfill, execution-grade promotion, corporate-action repair, modelling, Ranking/PIT-sector work, execution PnL, paper/live trading, broker integration, or main merge.

## Runtime integrity accepted

- frozen sample unchanged: `240` rows / `206` tickers / `178` dates;
- sample SHA-256: `9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`;
- Zapi access: `ACCESSIBLE` / `EMPIRICALLY_REACHED`;
- requests: `178`, retries `0`, rate-limit events `0`, request errors `[]`;
- exact ticker/date coverage: `240 / 240`;
- immutable panel SHA before/after unchanged: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- final manifest SHA: `899def2f280d49695a85f6fa2ddc34a4c793dcdf240ce114a02dd0055787fd1d`;
- focused tests: `6 passed`;
- full suite: `236 passed`, `5 warnings`.

The `KNOWN_CONTROL` alias correction is accepted as a bounded wiring fix. It changes no source, sample quota, admission rule, or arbitration semantics; it only makes the shared known-answer auditor treat the new control-role label as the existing-Open role it was intended to represent.

## Zapi Open-recovery decision

Zapi produced no admissible Open recovery in the outcome-independent targeted sample:

- missing-Open rows tested: `200`;
- admissible missing-Open rows: `0`;
- provider-gap recovery candidates: `0 / 80`;
- rejection on missing rows: `CANDIDATE_OPEN_INVALID = 200`;
- known controls H/L/C exact: `40 / 40`;
- known controls Open exact: `20 / 40`;
- the other `20` controls returned invalid Open (`0`).

Therefore a bulk Zapi Open backfill is not justified. The tested endpoint appears capable of reproducing H/L/C while historical Open is absent/zero on the rows for which Open recovery is needed. Do not reinterpret zero as a valid Open and do not synthesize from another field.

## H/L/C arbitration decision

Zapi is valuable as independent evidence about the Yahoo mismatch class:

- overall H/L/C exact: `240 / 240`;
- Yahoo no-factor H/L/C mismatch sample: `120` rows;
- `SOURCE2_SUPPORTS_CERTIFIED_PANEL = 120`;
- `SOURCE2_SUPPORTS_YAHOO = 0`;
- `THREE_WAY_DISAGREEMENT = 0`.

This is strong evidence that the sampled Yahoo mismatch is Yahoo-specific rather than evidence that the certified panel H/L/C is wrong. However, the sample must not be extrapolated mechanically to all `32,103` no-factor mismatch rows. No full-class reclassification is authorized from this sample alone.

A full Zapi mismatch census is not prioritized because it would not recover Open. Zapi remains available as a corroborator if a future source produces conflicting H/L/C on a row under review.

## Source-3 research direction

The next Open-track work is **source screening only** before any new provider experiment.

Preferred candidate for the next bounded pilot: **EOD Historical Data (EODHD)**, because its current official documentation explicitly lists Jakarta Exchange (`JK / XIDX`) and documents raw daily `open`, `high`, `low`, `close` values as unadjusted for splits/dividends, with `adjusted_close` separate.

Cost/risk gate:

- EODHD free access currently permits EOD history for arbitrary tickers only within the past year and is rate-limited;
- older full history requires the paid `EOD Historical Data — All World` package (currently advertised from about USD 19.99/month);
- therefore do **not** purchase a plan yet.

Recommended next experiment, only after a separately frozen spec:

1. create/use a free EODHD personal-research key;
2. run a recent-year semantics pilot first (preferably 2025 residual rows plus known controls) within the free data window;
3. require exact certified H/L/C, exact-date/ticker identity, positive in-range raw Open, and strong known-control Open agreement;
4. only if the free pilot shows genuine missing-Open recovery should paying for one month of older historical access be considered;
5. stop for review before any paid subscription or broader historical fetch.

Other screened candidates remain secondary:

- Twelve Data explicitly exposes IDX historical OHLC, but broad global EOD access is tied to paid-market plans beyond the basic trial posture;
- Alpha Vantage documents 20+ years of global raw daily OHLCV, but IDX/Jakarta symbol coverage has not yet been independently established for this project.

## Not authorized

- no bulk Zapi requests;
- no Zapi Open fill;
- no purchase/subscription to EODHD or another provider yet;
- no EODHD API runtime until a dedicated source-3 pilot spec is frozen;
- no corporate-action residual repair in this lane;
- no weakening of exact H/L/C/Open admission rules;
- no execution-grade promotion or downstream modelling.

## Stop boundary

Stop here. Next safe step is to freeze a bounded **free-tier EODHD recent-year pilot** spec, then use Codex only after the user has created a free API key and the branch/spec is ready.
