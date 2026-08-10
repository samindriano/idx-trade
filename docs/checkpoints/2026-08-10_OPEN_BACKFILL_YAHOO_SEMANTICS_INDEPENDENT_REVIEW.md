# Yahoo Historical Open Semantics Audit — Independent Review

Date: 2026-08-10 (Asia/Jakarta)
Reviewed branch: `data/idx-open-backfill-yahoo-semantics-v1`
Reviewed runtime HEAD: `c90ce1347651023fa48073182f771d27df8d7565`

## Decision

**`YAHOO_SEMANTICS_AUDIT_ACCEPTED_FULL_UNIVERSE_RECOVERY_CENSUS_AUTHORIZED`**

The bounded Yahoo semantics + broad-coverage audit is accepted as valid source evidence. The result is strong enough to authorize the next step: a full-universe historical Open recovery census against the immutable 1260-session panel, with derivative output only and the frozen admission contract unchanged.

This is **not** execution-grade promotion. The immutable panel remains unchanged, existing non-null Open remains immutable, and `execution_grade_promoted=false` remains mandatory until the full-universe census is independently reviewed.

## Evidence accepted

- deterministic sample: `300` rows / `270` unique tickers;
- sample SHA-256: `fc5a6f73e36ddf4ab2e52e3dcce82f310379ff54b4d4ff0c01990f8a575c0147`;
- Yahoo returned `266/270` tickers and `296/300` exact sample dates;
- direct raw H/L/C exact: `280/296 = 94.5946%`;
- direct known-Open exact: `170/172 = 98.8372%`;
- direct admissible missing-Open: `110/128 = 85.9375%`;
- independently verified split-scale reconstruction added `2` missing-Open admissions;
- total admissible missing-Open evidence in the deliberately stratified sample: `112/128 = 87.5%`;
- no duplicate provider keys;
- raw/adjusted fields remained separated;
- panel SHA before/after remained `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- final pytest: `229 passed, 3 pre-existing warnings`.

The sample was deliberately stratified, so the `87.5%` figure must **not** be extrapolated as a universe-wide recovery estimate. The full-universe census is required to measure actual recoverability.

## Interpretation

Yahoo is not uniformly raw-exchange-scale across all historical rows. The 16 direct split-scale mismatches confirm that stock-split semantics must remain explicit. However, the very high direct known-Open agreement and broad ticker/date coverage support using Yahoo as a recovery candidate when each row independently passes the certified H/L/C gate.

The split-scale path remains strictly secondary. A scale transformation is admissible only when an independently verified official split/reverse-split factor exists and transforms O/H/L/C consistently; transformed H/L/C must still equal the certified panel exactly. No factor may be inferred merely from a Yahoo/panel price ratio.

Provider gaps for FREN, MASA, MFIN and PURE are genuine unresolved cases for Yahoo and must remain unresolved unless a separately audited source supplies evidence.

## Authorized next scope

Run one **full-universe Yahoo recovery census** over the exact 1260-session window.

The census may:

1. fetch/cache Yahoo raw OHLC/action data for every panel ticker for the full window using a resumable, rate-limited external cache;
2. evaluate all existing known-Open rows as a full known-answer audit;
3. evaluate all `446,843` missing-Open rows under the unchanged direct admission rule;
4. separately evaluate verified split-scale reconstruction under the already frozen official-factor rule;
5. write a new derivative candidate panel/artifact outside Git with accepted Open fills and complete row-level provenance;
6. report actual residual Open count and exact recovery percentage.

The census must not modify the immutable panel or silently promote execution grade.

## Required gates for the census

Direct evidence:

- exact ticker and session date;
- raw Yahoo High == certified High;
- raw Yahoo Low == certified Low;
- raw Yahoo Close == certified Close;
- raw Yahoo Open finite and > 0;
- raw Yahoo Open within `[certified Low, certified High]`.

Split-scale evidence:

- independently verified official cumulative split/reverse-split factor;
- same factor applied consistently to O/H/L/C;
- transformed H/L/C exact against certified H/L/C;
- transformed Open finite, positive and inside certified range;
- classify separately from direct evidence.

Never use `Adj Close`, dividends, inferred factors, previous Close, averaging, interpolation, forward fill, or source voting to manufacture Open.

## Full-universe reporting required

At minimum report:

- panel/input SHA before and after;
- total panel tickers attempted / returned;
- provider request/retry/error counts;
- raw cache manifest and hashes;
- exact ticker/date coverage over all ACTIVE rows;
- full known-Open H/L/C exact rate;
- full known-Open Open exact rate;
- direct missing-Open accepted count;
- verified split-scale missing-Open accepted count;
- accepted rows by year and ticker;
- rejection histogram;
- residual missing Open count and percentage;
- list/summary of completely unsupported tickers;
- any systematic date-era degradation;
- derivative artifact SHA-256 and provenance manifest SHA-256;
- `execution_grade_promoted=false`.

## Stop boundary

After the full-universe recovery census, STOP for independent review. Do not start execution-PnL, paper/live trading, or execution-grade promotion automatically. Ranking V2 remains a separate research track and is not changed by this authorization.
