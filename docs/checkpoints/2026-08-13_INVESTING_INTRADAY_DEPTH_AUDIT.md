# Investing Historical Intraday Depth Audit

Date: 2026-08-13
Owner: Codex/Investing-Intraday-Depth-Audit
Branch: `data/investing-intraday-depth-audit-v1`
Source commit: `3704955e17a471b7a63b4da9f75fe1223fd79bbd`
Status: `REVIEW`

## Scope and boundary

This was a bounded source audit only. It did not modify canonical panels, model
artifacts, O2 counters, protected outcomes, or research/model semantics. It did
not start a continuous historical intraday acquisition or a Path Risk lane.

The frozen input was the prior V2/V3-B universe of 737 tickers and its preserved
Investing identity cache: 726 exact Jakarta common-stock identities and 11
identity-unresolved tickers. The prior census artifact manifest was
`0aba06cb942bf5b0bda6f532018be5e6e2e95f7ab6c188da7ddfcd35938bca65`.

Five sparse 1-hour probes were run:

| Probe year | Requested window |
|---|---|
| 2026 | 2026-07-01 through 2026-07-07 |
| 2024 | 2024-07-01 through 2024-07-07 |
| 2022 | 2022-07-01 through 2022-07-07 |
| 2020 | 2020-07-01 through 2020-07-07 |
| 2018 | 2018-07-02 through 2018-07-06 |

The request contract was the proven curl-cffi transport, Investing history
endpoint, resolved pair ID, `resolution=60`, UTC epoch bounds, no pagination,
four low-concurrency workers, and at most one retry after HTTP 403/429.

## Depth result

All 3,685 planned requests completed. There were 58 bounded 403-to-200
retries, zero 429 events, and zero final provider errors.

| Year | Available / 737 | Percent | Available / 726 resolved | Percent | NO_DATA | Identity unresolved |
|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 326 | 44.23% | 326 | 44.90% | 400 | 11 |
| 2020 | 369 | 50.07% | 369 | 50.83% | 357 | 11 |
| 2022 | 519 | 70.42% | 519 | 71.49% | 207 | 11 |
| 2024 | 650 | 88.20% | 650 | 89.53% | 76 | 11 |
| 2026 | 671 | 91.05% | 671 | 92.42% | 55 | 11 |

The resolved-ticker survival patterns are informative:

- 256 resolved tickers were available in all five probe years.
- 129 first appeared in the 2024/2026 probes.
- 96 first appeared in the 2022/2024/2026 probes.
- 79 first appeared in the 2020/2022/2024/2026 probes.
- 60 were available only in the 2026 probe.
- Three resolved tickers (`AIMS`, `PTMR`, `SWAT`) returned `NO_DATA` in all
  five probes.

## Failure interpretation

The canonical PIT security master was used only for diagnostic classification;
it was not rewritten. It has SHA-256
`9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

For `NO_DATA` rows, the listing-boundary cross-check found:

| Year | NO_DATA before `listed_from` | NO_DATA within listed interval |
|---:|---:|---:|
| 2018 | 355 | 45 |
| 2020 | 265 | 92 |
| 2022 | 181 | 26 |
| 2024 | 41 | 35 |
| 2026 | 0 | 55 |

Therefore:

- identity mapping explains the fixed 11-ticker unresolved group;
- listing date explains most early-year gaps;
- gaps inside a listed interval remain ambiguous between no trading,
  suspension, provider coverage, or incomplete provider history and are not
  treated as a negative trading conclusion;
- the monotonic improvement toward recent years is consistent with listing
  dates plus per-symbol historical coverage/retention;
- because some symbols have 1-hour data in 2018, there is no evidence of a
  single universal hard history cutoff;
- no provider failure survived the bounded retry, so transport failure does
  not explain the depth curve.

Identity-unresolved tickers were:
`AUTO`, `BANK`, `CENT`, `DUCK`, `EURO`, `FREN`, `HEAL`, `MFIN`, `REAL`,
`TECH`, `WSKT`.

Observed available-bar timestamps in the summarized band were UTC 02:00–09:00.
Because Asia/Jakarta is UTC+7, that band is 09:00–16:00 WIB, not 08:00–16:00
WIB. The preserved raw responses also contain a small number of UTC 01:00
opening-boundary rows, which convert to 08:00 WIB; this explains why the
artifact metadata records an observed 08:00–16:00 boundary. These are provider
bar-boundary conventions, not evidence of a different market timezone, and any
future adapter must normalize them explicitly. No available-row timestamp was
outside the observed raw boundary after timezone-aware conversion.

## Bounded daily fidelity check

Because multi-year 1-hour depth was material, a deterministic 20-ticker check
was run locally against the existing canonical daily panel. The sample had 14
HIGH, 3 MID, and 3 LOW history-stratum names, including liquid controls such as
BBCA, BBRI, BMRI, TLKM, ASII, AMRT, ICBP, INDF, UNTR, ANTM, and MDKA.

Investing 1-hour epochs were converted timezone-aware to Asia/Jakarta before
daily aggregation to Open/High/Low/Close/Volume. The preserved
`fidelity_summary_v2.json` records 54 `WIB_PROVIDER_BOUNDARY_08_TO_16`
available probes, 6 `NO_ROWS`, and no rows outside the boundary; the comparison
artifact carries the same alignment label for every available probe. No fixed
08:00 local offset was used in place of the UTC→Asia/Jakarta conversion. The
canonical panel's Open was compared only where it was present. Rechecking the
preserved raw epochs confirms UTC 02:00→09:00 WIB and UTC 09:00→16:00 WIB; the
few UTC 01:00 rows map to the documented 08:00 opening boundary. Therefore the
review finding was documentation-only and does not affect daily date keys or
any fidelity metric.

- 60 ticker-year probes; 54 had provider rows.
- 256 matching daily dates; no date-set gap appeared in the matched ranges.
- H/L/C exact: 190/256 (74.22%).
- OHLC exact where both Opens existed: 136/224 (60.71%).
- Open exact where both Opens existed: 159/224.
- Volume exact: 203/256 (79.30%).
- Volume near-parity: 213/256 (83.20%).
- Median provider/canonical volume ratio: 1.0; no general unit-scale issue was
  observed.
- Ten CA-like scale discrepancies were retained as anomalies, not repaired:
  BMRI in 2022 had close/volume ratios near 0.5, and DSSA in 2024 had ratios
  near 0.1. No split factor was inferred or applied.

### Conditional coverage among securities listed by the probe year

This descriptive diagnostic excludes the 11 identity-unresolved tickers and
conditions only on `AVAILABLE + NO_DATA within listed interval`. It is not
proof that an in-listed `NO_DATA` row is a provider failure or evidence of no
trading.

| Probe year | Available | Within-listed NO_DATA | Conditional availability |
|---:|---:|---:|---:|
| 2018 | 326 | 45 | 326 / 371 = 87.87% |
| 2020 | 369 | 92 | 369 / 461 = 80.04% |
| 2022 | 519 | 26 | 519 / 545 = 95.23% |
| 2024 | 650 | 35 | 650 / 685 = 94.89% |
| 2026 | 671 | 55 | 671 / 726 = 92.42% |

The 2020 conditional dip remains a provider/data-quality question for any
future pilot.

## Remediation disposition

`TIMEZONE_DOCUMENTATION_ONLY_METRICS_UNCHANGED`. No network request was
rerun, no fidelity artifact was regenerated, and no canonical/model artifact
was modified. The final external artifact manifest remains
`58b77c7d4d875d0e6e296f2f036162cf0e6f147419639aaa2a4dd8d14d0beca2`.

The parity result is useful as a secondary-source diagnostic but is not clean
enough for direct canonical replacement. Corporate-action evidence and exact
session/time-boundary normalization must be part of any future admission gate.

## Verdict

`DEPTH_JUSTIFIES_PREREGISTERED_SECONDARY_INTRADAY_LANE_NOT_BULK_READY`

Investing.com is more than a narrow blue-chip-only source: recent 1-hour depth
covers 671/737 training-universe tickers, and 256 resolved names survive all
five sparse years. That is sufficient to justify a separately preregistered,
secondary historical-intraday acquisition pilot.

It does not authorize bulk acquisition or panel integration. The next lane,
if approved after review, must freeze identity/date semantics, WIB bar
normalization, corporate-action reconciliation, exact/near-fidelity gates,
and explicit treatment of `NO_DATA` within listed intervals.

## External artifact hashes

Artifact root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\investing_intraday_depth_audit_v1_20260813`

- pre-network depth manifest: `197073dd956fe426aa1620fa563b7e44db526f11540e46678fee1a4a54d3c653`
- depth status CSV: `0caf87ced6aa681aab03ddf5cb1d7eff3541c49b3cf5ca3505b7a45b6a056816`
- survival table: `2c09cd8120521705d64b8f463b798bb486f33be9ee8e7c0c74fcbd8a4b6bc496`
- failure classification: `feb6535d92d7b971621c902fa336fbc87d33cb956194e353346305c0fd2513c4`
- fidelity sample manifest: `affe3b25f5672e36d5a65eee71d2c57dda0ab16014961eb467bd983ab962875a`
- fidelity mismatch details: `7f6073054fac76c32630099f4b7377a23df0b64931d472ca6666c5803419970d`
- fidelity summary: `4c09137e527c06a614b20b94d9f07e08491eba50afcf2a644b5973bc50ad5b47`
- final artifact manifest: `58b77c7d4d875d0e6e296f2f036162cf0e6f147419639aaa2a4dd8d14d0beca2`
- failure-reason summary: `feb6535d92d7b971621c902fa336fbc87d33cb956194e353346305c0fd2513c4`

No canonical panel, model, outcome, O2, or Path Risk artifact was changed.
