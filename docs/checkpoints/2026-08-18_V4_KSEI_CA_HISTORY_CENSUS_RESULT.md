# V4 KSEI Corporate-Action History Census V1 — Result

Date: 2026-08-18 (Asia/Jakarta)
Branch: `data/idx-v4-ksei-ca-history-census-v1`
Scientific code anchor: `57a15599cf96205bc75f3f5e8b593eac0a77c4cd`
Parent continuity ledger SHA-256: `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`
Prior event evidence SHA-256: `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`
Status: `RESULT_REVIEW`

## Validation

- Focused test: `tests/test_v4_ksei_ca_history.py` — `8 passed`.
- `py_compile` passed for the two source modules and two census/gate runners.
- `curl_cffi` import passed: `0.13.0`.
- `git diff --check` passed.
- Scientific implementation/configuration remained unchanged from the anchor;
  only coordination/docs and promoted small artifacts were added.

## Exact KSEI census

The frozen runner was executed once with the exact 610-ticker population and
the frozen public KSEI registered-security transport. No alternate provider or
URL was used.

- Census status: `KSEI_610_HISTORY_CENSUS_COMPLETE_WITH_COVERAGE_GAPS`.
- Requested ticker count: `610`.
- Coverage-certified tickers: `567`.
- Coverage-unresolved tickers: `43`.
- Ticker identity SHA-256: `2db45fde63e5f5d755abd81858242bf2089fa5cbb397de1f2b8a78bb37db5f4c`.
- Total parsed KSEI history rows: `14,723`.
- Active mechanical or unknown rows: `739`.
- Active unknown rows: `37`.
- Raw captures: `804` files / `49,961,415` bytes, retained outside Git.
- Request records: `804`, retained outside Git.

Normalized event-family counts among active mechanical/unknown rows:

| Event family | Rows |
|---|---:|
| Mandatory Conversion | 280 |
| Rights/HMETD | 378 |
| Stock Dividend | 44 |
| Unknown | 37 |

The corresponding KSEI source labels were: `Right Distribution=378`,
`Stock Dividend=44`, `Mandatory Conversion=181`, `Voluntary Conversion=99`,
`Mixed Dividend=36`, and `Redemption=1`.

Provider/error accounting:

- Final unresolved: `43` tickers, all with final HTTP status `0` in the
  coverage table.
- `41` unresolved tickers ended with the frozen HTTP/empty-response failure
  path; `2` also had an unparseable identity response (`AMAN`, `PRIM`).
- `113` unique tickers had at least one failed attempt across the append-only
  request records; transient attempts that later succeeded are not counted as
  unresolved.
- No provider substitution occurred.

## Offline continuity gate V2

The frozen offline gate was run once after the census, against the original
blocked ledger and prior event evidence.

- Verdict: `V4_CA_CONTINUITY_STILL_BLOCKED`.
- `corporate_action_continuity_certified`: `false`.
- Frozen dates: `600`.
- Resolved tickers: `464`.
- Unresolved tickers: `146`.
- H5 gate dates: `0/600`; minimum rate `0.7100271002710027`.
- H10 gate dates: `0/600`; minimum rate `0.7100271002710027`.
- Consensus gate dates: `0/600`; minimum rate `0.7100271002710027`.
- Ticker status counts: `464` resolved with no mechanical discontinuity,
  `44` unresolved coverage, `102` unresolved effective date.

Reason histogram:

```text
KSEI_COMPLETE_HISTORY_NO_ACTIVE_MECHANICAL_CA_IN_V4_PERIOD: 464
KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED: 43
CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY: 1
KSEI_ACTIVE_MECHANICAL_OR_UNKNOWN_CA_IN_V4_PERIOD:MANDATORY_CONVERSION: 53
KSEI_ACTIVE_MECHANICAL_OR_UNKNOWN_CA_IN_V4_PERIOD:MANDATORY_CONVERSION|RIGHTS_HMETD: 6
KSEI_ACTIVE_MECHANICAL_OR_UNKNOWN_CA_IN_V4_PERIOD:MANDATORY_CONVERSION|RIGHTS_HMETD|STOCK_DIVIDEND: 1
KSEI_ACTIVE_MECHANICAL_OR_UNKNOWN_CA_IN_V4_PERIOD:RIGHTS_HMETD: 35
KSEI_ACTIVE_MECHANICAL_OR_UNKNOWN_CA_IN_V4_PERIOD:RIGHTS_HMETD|STOCK_DIVIDEND: 3
KSEI_ACTIVE_MECHANICAL_OR_UNKNOWN_CA_IN_V4_PERIOD:STOCK_DIVIDEND: 1
KSEI_ACTIVE_MECHANICAL_OR_UNKNOWN_CA_IN_V4_PERIOD:STOCK_DIVIDEND|UNKNOWN: 1
KSEI_ACTIVE_MECHANICAL_OR_UNKNOWN_CA_IN_V4_PERIOD:UNKNOWN: 2
```

The 90% per-date continuity gate therefore remains blocked. No event date was
inferred from KSEI Cum/Record/Distribution dates.

## Hashes and promotion

Promoted small, reproducibility-critical artifacts are under
`docs/artifacts/ranking_v4_ksei_ca_history_census_v1/`:

| Artifact | SHA-256 |
|---|---|
| Census `MANIFEST.json` | `7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25` |
| Census `summary.json` | `a046637fbcff69cbc42c09e4cac30d9181b2ce93a3cf7297a9a01cfc23a2f422` |
| Census `ticker_coverage.csv` | `bb5414125862411e5d3ee760f8e7415b8418803c71d1cc1ef26fb0c55397bc70` |
| Continuity V2 `MANIFEST.json` | `503afd04e8e6b932adfed1ad316e77c5601cc2d494551e0752fdd0ce92ce1d25` |
| Continuity V2 `summary.json` | `d55fd0614b4df292191cc0e96b5e65f3befad9e5a2d41cfa1c095096e3dcc110` |
| Continuity V2 `ticker_classification.csv` | `6b8e85db11dba5fce0bf921c2117419876d2476abd2e852c58fb1d87a8878633` |
| Continuity V2 `v4_frozen_continuity_per_date_v2.csv` | `8e81ef96b67ddeab69b11f53745094e6dd5e4148aa603c03018773375e307784` |

The full KSEI history, request records, raw HTML, and full continuity ledger
remain external and were not promoted.

## Boundaries

No R5/R10, target/rank materialization, model fit, predictions, performance,
protected/fresh-forward outcomes, provider substitution, V4 contract change,
or post-result policy tuning occurred. Source and config files were not edited
after the KSEI response.

Final decision: stop at `V4_CA_CONTINUITY_STILL_BLOCKED` for ChatGPT review.
