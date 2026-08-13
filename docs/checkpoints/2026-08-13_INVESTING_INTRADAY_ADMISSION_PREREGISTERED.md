# Investing Intraday Admission Pilot — Preregistration

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/investing-intraday-admission-pilot-v1`
Status: frozen before network acquisition

The bounded secondary-source admission contract is frozen in
`config/investing_intraday_admission_pilot_v1.json`, including exact identity,
PIT listing/session, UTC-to-WIB timestamp, raw OHLCV, provenance, sample,
window, retry, and admission rules. The pilot has 50 deterministic unique
tickers and 150 possible ticker-window pairs across official-calendar-backed
windows:

* old: 2022-04-01 through 2022-06-30;
* mid: 2024-04-01 through 2024-06-28;
* recent: 2026-04-01 through 2026-06-30.

The request contract is Investing history at resolution `60`, local-date
bounds converted to UTC epochs, four workers, and at most one bounded retry for
403/429/5xx. No pagination, bulk backfill, canonical panel write, model,
outcome, O2, or Path Risk access is permitted.

The exact gates are frozen before results: zero final provider errors,
zero malformed/duplicate/off-session admitted rows, listed-session coverage of
90% recent and 80% mid/old, 90% of returned session-days with at least five
bars, H/L/C exact >=90%, volume-near >=90%, canonical-Open exact >=90% where
available, all three eras passing, and external corporate-action uncertainty
quarantined rather than ratio-repaired.

Validation before network:

* focused pilot tests: 6 passed;
* full repository suite: 44 passed, 1 pre-existing failure in
  `tests/test_storage.py` because the baseline revision audit reports both
  `raw_close` and `vendor_adj_close` while the test expects one; no unrelated
  storage code was changed;
* `git diff --check`: passed;
* `curl_cffi`: 0.13.0 import available.

No network request has been made by this preregistration checkpoint. The next
authorized action is the bounded runtime using the exact external input paths
and artifact root described in the handoff.
