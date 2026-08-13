# Investing.com Secondary Intraday Admission Pilot V1

Status: preregistered bounded pilot; no canonical-source admission has been made.

## Purpose and boundary

This lane tests whether Investing.com 1-hour IDX history can be admitted as a
reproducible secondary historical intraday source. It is not authorization for
bulk 2018–2026 acquisition, canonical-panel writes, model work, Path Risk,
O2/fresh-forward work, or execution claims.

The pilot is frozen in
`config/investing_intraday_admission_pilot_v1.json` before network acquisition.
The accepted source lineage is the 737-name V2/V3-B research universe from the
accepted Investing depth audit, with the canonical PIT security master and
official exchange-session calendar used for listing/session checks. The
external input hashes are recorded in the config and in the runtime sample
manifest.

## Identity and listing contract

Only an exact Jakarta common-stock Investing identity with a persisted pair ID
from the accepted identity census is eligible for a history request. Ambiguous
or unresolved identities are reported and fail closed. A renamed or delisted
symbol is never silently substituted. The PIT `listed_from`/`listed_to`
interval determines expected listed sessions; pre-listing no-data is not a
provider failure, while within-listed no-data remains UNKNOWN.

The deterministic sample contains 50 unique tickers: 15 controls (including
BMRI, DSSA, and the FREN identity edge), 10 LONG, 10 MID, 8 LOW, 4 previous
within-listed-no-data cases, and 3 additional unresolved identity edges.
Ordering and seed `20260813` are fixed. The exact list is in the JSON contract
and is hashed in the external sample manifest before any request is made.

## Time and OHLCV semantics

Requests cover inclusive local dates converted from Asia/Jakarta midnight to
UTC epochs, at resolution `60`. Raw response epochs are UTC and are preserved
unchanged. Normalized timestamps are timezone-aware Asia/Jakarta timestamps.
An observation is admitted only when its local session date is an official IDX
session and its time is 08:00:00–16:00:00 WIB. 08:00 is retained as a possible
opening-boundary observation; the normal observed band is 09:00–16:00 WIB.
There is no heuristic timestamp shifting.

Duplicate timestamps, malformed arrays/timestamps, off-session rows, invalid
OHLCV, and invalid price ranges are quarantined and excluded from normalized
admission. Raw OHLCV values are never adjusted. No split or corporate-action
factor is inferred or applied. The previously accepted BMRI/old and DSSA/mid
periods are explicit external anomaly controls; unresolved scale anomalies are
quarantined, not repaired from ratios.

Daily aggregation is chronological: first Open, maximum High, minimum Low,
last Close, and sum Volume. The provider daily frame is compared to canonical
daily rows without modifying either source.

## Frozen windows and gates

The pilot requests the same deterministic sample over three bounded,
calendar-backed windows: 2022-04-01–2022-06-30 (`old`), 2024-04-01–2024-06-28
(`mid`), and 2026-04-01–2026-06-30 (`recent`). These windows provide exact
official session expectations without inventing pre-2021 calendar history.
Maximum concurrency is four and each request has at most one bounded retry for
403/429/5xx. No pagination is used.

Gates are frozen before results are inspected:

* final provider error rate must be 0%; 429 events are separately reported;
* malformed, duplicate, and off-session admitted rows must be 0;
* listed-session coverage must be at least 80% for old and mid, and 90% for
  recent;
* at least 90% of returned session-days must contain five or more admitted
  bars;
* H/L/C exact rate and volume-near rate must each be at least 90%;
* Open exact rate must be at least 90% where canonical Open exists;
* all three eras must pass; recent-only success is insufficient;
* external corporate-action uncertainty remains a quarantine/blocker.

The final labels are `PILOT_ADMITTED_SECONDARY_INTRADAY`,
`PILOT_CONDITIONAL_QUARANTINE_REQUIRED`, or `PILOT_REJECTED`. No model metric
is part of admission.

## Artifacts and review boundary

Raw request/response records, normalized bars, daily comparisons, request
manifest, summary, and artifact hashes are written only under the external
artifact root configured by the runtime command. Each request records ticker,
pair ID, UTC bounds, resolution, retrieval time, HTTP statuses, retries, raw
hash, and normalized lineage. The immutable canonical panel is rehashed and
never written.

The runtime checkpoint will report coverage, session completeness, parity,
volume ratios, Open availability, anomalies/quarantines, cross-era stability,
source hashes, and the final gate label for independent ChatGPT review.
