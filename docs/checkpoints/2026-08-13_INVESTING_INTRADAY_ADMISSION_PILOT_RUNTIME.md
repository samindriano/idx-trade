# Investing.com Secondary Intraday Admission Pilot — Runtime

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/investing-intraday-admission-pilot-v1`
Runtime code commit: `38d4f30b5d5a4b96fb655f5dd54570849a572a8c`
Final documentation/provenance code commit: `26bca3c06a72c4128e63019a69a139d41bc99a7b`

## Verdict

`PILOT_REJECTED` under the preregistered admission contract. Investing.com
history is reachable with the validated curl-cffi transport and returned
1-hour bars, but the bounded sample did not meet the frozen provider-error,
listed-session coverage, within-session, daily-fidelity, or Open-parity gates.
No secondary source admission, canonical-panel write, bulk acquisition, model
work, Path Risk/O2 work, or protected-outcome access occurred.

## Sample and requests

The exact deterministic sample remained 50 unique tickers, seed `20260813`,
over 150 possible ticker-window pairs. Four identities were unresolved from the
preserved exact Jakarta identity cache (`AUTO`, `FREN`, `MFIN`, `WSKT`), so 46
tickers produced 138 eligible history pairs. No identity network calls were
made. The three windows were:

* old: 2022-04-01–2022-06-30;
* mid: 2024-04-01–2024-06-28;
* recent: 2026-04-01–2026-06-30.

The pre-network sample manifest SHA-256 is
`6c66dd262288b029f5094e58a38371e78ce34692b49b09751c487aaaf3f115af`.
The final external artifact root is:

`D:\Documents\Project\idx-trade-data-gate-20260808v\investing_intraday_admission_pilot_v1_retry3_20260813`

There were 229 network attempts for 138 logical history requests: 91 retries,
33 retry recoveries, 58 final provider errors, and 0 HTTP 429 events. Final
statuses were 67 `AVAILABLE`, 13 `NO_DATA`, and 58 `PROVIDER_ERROR`. HTTP
status sequences were `[200]` 47, `[403, 200]` 33, and `[403, 403]` 58.
Pre-listing/no-identity cases were not counted as provider failures; within-
listed no-data remains unresolved/UNKNOWN as frozen.

## Coverage and structural checks

| era | expected listed sessions | returned sessions | coverage | >=5-bar session-days | HLC exact | volume near | gate |
|---|---:|---:|---:|---:|---:|---:|---|
| old | 1,894 | 839 | 44.2978% | 93.2062% | 83.5518% | 59.3564% | FAIL |
| mid | 1,924 | 1,340 | 69.6466% | 89.0299% | 83.8806% | 93.1343% | FAIL |
| recent | 2,622 | 1,368 | 52.1739% | 99.7807% | 72.0029% | 93.9327% | FAIL |

Across admitted rows there were zero malformed, duplicate, off-session, or
invalid-OHLCV rows. The normalized timestamps used UTC epoch to timezone-aware
Asia/Jakarta conversion; the 08:00 boundary was retained and no timestamps
were heuristically shifted. The comparison contained 3,547 matched daily
rows across 164 unique dates. Overall H/L/C exact was 79.2219%, volume exact
80.9698%, volume-near 85.4525%, and canonical-Open exact 70.4996% over 2,722
canonical-Open rows. The two pre-accepted external corporate-action controls
were quarantined, producing 96 quarantined comparison rows; no factor was
inferred or applied.

## Failure interpretation

The source is operationally reachable, but the pilot is not admissible as a
reproducible secondary historical intraday dataset under the frozen contract:
final 403 errors remain material, all three eras miss listed-session coverage,
old and recent fail fidelity, mid fails within-session completeness, and Open
parity is below its gate. The result does not authorize retry expansion,
another provider, bulk history, or canonical integration. Any future attempt
requires a separately reviewed remediation/preregistration rather than
loosening these gates.

## Hashes and immutability

The canonical panel SHA-256 was verified before and after runtime as
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

Final external artifact hashes:

* `sample_manifest.json`: `6c66dd262288b029f5094e58a38371e78ce34692b49b09751c487aaaf3f115af`;
* `sample_identity_resolution.json`: `95d64efe8d76327442254490b15fba312073a951855e3db1133626058ef6e03f`;
* `normalized/intraday_bars.csv`: `8aeff367f77aa5ce584592ee8fd621d03378f6b43212bbc9f1914ba432235abe`;
* `normalized/daily_comparison.csv`: `c86fb569b7c37d9e432203674a7430c96f068a1d24781e0df7d5591f9b9776f3`;
* `request_manifest.csv`: `79ab072f454042e43b7a61e6b3aa7ec00a6da8fcc0a76ae98b56adf9b7e3e27a`;
* `admission_summary.json`: `b37926fdbdd9b6569cf010ca31fdbb5736a9e8ab8502f0e85adb9cc9c8b66c4c`;
* `artifact_manifest.json`: `2316dd2302451ffb2f5a53fd8ff1f4fcf0296979c81a370c16f94560fc33cc7e`.

The artifact manifest contains 144 hashed files, including 138 raw request
records. Earlier failed implementation attempts remain in separate external
roots and are not included in these final metrics.

## Validation

Focused pilot tests: 8 passed. Full repository suite: 47 passed, 1 pre-existing
failure in `tests/test_storage.py`; the baseline test expects one revision
conflict while the existing storage implementation reports both `raw_close`
and `vendor_adj_close`. No storage/scientific behavior was changed in this
lane. `git diff --check` passed.
