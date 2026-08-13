# Investing Historical Intraday Depth Audit — Independent Review

Date: 2026-08-13 (Asia/Jakarta)
Reviewer: ChatGPT / independent review
Branch reviewed: `data/investing-intraday-depth-audit-v1`
Reviewed remote HEAD: `a7c937aa2ef990558c825a6fbe8fcb1184f7123a`
Decision: `INVESTING_INTRADAY_DEPTH_REVIEW_CHANGES_REQUIRED_SMALL`

## High-level judgment

The audit is decision-useful and the main scientific conclusion is directionally accepted: Investing.com has enough historical 1-hour IDX depth to justify a separately preregistered **secondary** historical-intraday acquisition pilot. It is not clean enough for canonical replacement, bulk acquisition, panel integration, or automatic Path Risk restart.

Transport is no longer the material blocker in this bounded setup: all 3,685 planned probes completed, 58 transient HTTP 403 responses recovered to 200 under the frozen bounded retry, no HTTP 429 event occurred, and no final provider error remained.

## Coverage interpretation

The raw current-universe survival curve is materially informative:

- 2018: 326 / 737 = 44.23%
- 2020: 369 / 737 = 50.07%
- 2022: 519 / 737 = 70.42%
- 2024: 650 / 737 = 88.20%
- 2026: 671 / 737 = 91.05%

However, the raw denominator includes securities that were not yet listed in the earlier probe years. Using the checkpoint's own `NO_DATA before listed_from` versus `NO_DATA within listed interval` classification, availability among resolved identities that were actually inside their listed interval is substantially stronger:

| Probe year | Available | Within-listed NO_DATA | Conditional availability |
|---:|---:|---:|---:|
| 2018 | 326 | 45 | 87.87% |
| 2020 | 369 | 92 | 80.04% |
| 2022 | 519 | 26 | 95.23% |
| 2024 | 650 | 35 | 94.89% |
| 2026 | 671 | 55 | 92.42% |

This does **not** prove complete historical coverage, because within-listed `NO_DATA` remains ambiguous, but it shows that the 44–50% early-year raw coverage is driven heavily by listing-date support rather than a universal provider history cutoff. The 2020 conditional dip remains a real provider/data-quality question and should stay visible in any pilot admission contract.

## Fidelity judgment

The 20-ticker fidelity check is strong enough for secondary-source research admission work but not for canonical promotion:

- H/L/C exact: 190 / 256 = 74.22%
- OHLC exact on comparable Open rows: 136 / 224 = 60.71%
- Volume exact: 203 / 256 = 79.30%
- Volume near-parity: 213 / 256 = 83.20%
- Median provider/canonical volume ratio: 1.0

The BMRI 2022 and DSSA 2024 scale discrepancies are correctly retained as unresolved corporate-action-like anomalies rather than repaired by inferred ratios. Any future pilot must freeze corporate-action reconciliation/exclusion rules before data acquisition or model evaluation.

## Required correction before acceptance

The checkpoint contains a timezone arithmetic inconsistency:

> observed timestamps were UTC 02:00–09:00, then described as approximately 08:00–16:00 WIB.

Asia/Jakarta is UTC+7 with no DST, so UTC 02:00–09:00 corresponds to **09:00–16:00 WIB**, not 08:00–16:00 WIB.

This may be documentation-only because the fidelity section says aggregation was performed explicitly in `Asia/Jakarta`, but the review cannot assume that. Before final acceptance:

1. correct the checkpoint/handoff wording to 09:00–16:00 WIB if the raw timestamps are indeed UTC 02:00–09:00;
2. confirm from the preserved audit logic/artifact metadata that the daily fidelity aggregation used UTC→`Asia/Jakarta` conversion correctly and did not apply an 08:00 local offset assumption;
3. no network rerun is needed if this is only a documentation error.

## Boundary after remediation

If the timezone issue is confirmed documentation-only, the expected final verdict is:

`DEPTH_AUDIT_ACCEPTED_PREREGISTER_SECONDARY_INTRADAY_PILOT`

That verdict would authorize only a separately frozen acquisition/admission specification covering identity mapping, historical support, timezone/session semantics, corporate actions, daily reconciliation gates, and treatment of within-listed `NO_DATA`.

It would **not** authorize continuous bulk backfill, canonical panel replacement, model fitting, forward outcome access, O2 changes, or automatic Path Risk V3/restart. A new Path Risk experiment would still require a genuinely new preregistered hypothesis family after the data pilot is independently admitted.
