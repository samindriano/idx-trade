# Investing Historical Intraday Depth Audit — Independent Review

Date: 2026-08-13 (Asia/Jakarta)
Reviewer: ChatGPT / independent review
Branch reviewed: `data/investing-intraday-depth-audit-v1`
Reviewed remediation HEAD: `d083581c561c5777cc221b4a16bc48d4b98b4685`
Decision: `DEPTH_AUDIT_ACCEPTED_PREREGISTER_SECONDARY_INTRADAY_PILOT`

## Final judgment

The bounded Investing.com historical 1-hour depth audit is accepted after narrow timezone remediation.

The prior review finding was documentation/arithmetic-only. The preserved audit confirms timezone-aware UTC epoch conversion to `Asia/Jakarta` was already used before daily aggregation; no fixed local offset assumption affected date keys or fidelity metrics. The summarized UTC 02:00–09:00 band maps to 09:00–16:00 WIB, while a small number of preserved UTC 01:00 rows explain the observed 08:00 opening-boundary metadata. No network rerun or artifact regeneration was required.

The main scientific conclusion is therefore accepted: Investing.com has enough historical 1-hour IDX depth to justify a separately preregistered **secondary** historical-intraday acquisition/admission pilot. It is not clean enough for canonical replacement, unrestricted bulk acquisition, panel integration, or automatic Path Risk restart.

## Transport and historical depth

All 3,685 planned sparse probes completed. Fifty-eight transient HTTP 403 responses recovered to 200 under the bounded retry contract, with zero HTTP 429 events and zero final provider errors.

Raw current-universe availability was:

- 2018: 326 / 737 = 44.23%
- 2020: 369 / 737 = 50.07%
- 2022: 519 / 737 = 70.42%
- 2024: 650 / 737 = 88.20%
- 2026: 671 / 737 = 91.05%

Because the current universe includes securities not yet listed in earlier probe years, the listing-aware diagnostic is more informative for source depth:

| Probe year | Available | Within-listed NO_DATA | Conditional availability |
|---:|---:|---:|---:|
| 2018 | 326 | 45 | 87.87% |
| 2020 | 369 | 92 | 80.04% |
| 2022 | 519 | 26 | 95.23% |
| 2024 | 650 | 35 | 94.89% |
| 2026 | 671 | 55 | 92.42% |

This is descriptive only. Within-listed `NO_DATA` remains ambiguous between no trading, suspension, provider coverage, and incomplete history; it is not treated as proof of provider failure or proof of no trading. The 2020 conditional dip remains a specific data-quality question for the next pilot.

## Fidelity judgment

The preserved 20-ticker daily reconciliation metrics are unchanged:

- H/L/C exact: 190 / 256 = 74.22%
- OHLC exact on comparable Open rows: 136 / 224 = 60.71%
- Volume exact: 203 / 256 = 79.30%
- Volume near-parity: 213 / 256 = 83.20%
- Median provider/canonical volume ratio: 1.0

These metrics are sufficient for a secondary-source admission pilot, not for canonical promotion. BMRI 2022 and DSSA 2024 scale discrepancies remain unresolved corporate-action-like anomalies and were correctly left unrepaired. Ratio-derived split-factor inference is not authorized.

## Accepted boundary

`DEPTH_AUDIT_ACCEPTED_PREREGISTER_SECONDARY_INTRADAY_PILOT` authorizes only the creation of a separately frozen acquisition/admission specification before any wider historical retrieval.

That next specification must freeze at minimum:

- exact Investing identity/pair-ID mapping and ambiguity handling;
- supported historical date/session semantics;
- explicit UTC-to-Asia/Jakarta bar normalization, including the observed 08:00 opening-boundary cases;
- corporate-action reconciliation/exclusion rules using authoritative evidence;
- exact/near daily OHLCV reconciliation thresholds and fail-closed admission outcomes;
- treatment of within-listed `NO_DATA`, suspensions, delistings, renames, and provider gaps;
- raw-response provenance, hashes, manifests, retries, and reproducibility rules;
- acquisition scope and stopping rules before any continuous/bulk backfill.

This acceptance does **not** authorize canonical panel replacement, model fitting/retraining, protected forward-outcome access, O2 changes, or resurrection of Path Risk V1/V2. Any future Path Risk research still requires a genuinely new preregistered hypothesis family after the secondary intraday data pilot itself is admitted.

## Artifact integrity

No audit artifact changed during remediation. The accepted external artifact manifest remains:

`58b77c7d4d875d0e6e296f2f036162cf0e6f147419639aaa2a4dd8d14d0beca2`

The existing fidelity and mismatch artifacts remain hash-stable. The remediation passed `git diff --check` and did not rerun network acquisition.
