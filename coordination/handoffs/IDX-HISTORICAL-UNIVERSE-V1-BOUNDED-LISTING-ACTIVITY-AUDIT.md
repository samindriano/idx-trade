# Handoff: Historical Universe V1 Bounded Listing-Activity Audit

from: MAIN
to: ChatGPT reviewer
task_id: IDX-HISTORICAL-UNIVERSE-V1-BOUNDED-LISTING-ACTIVITY-AUDIT
model_used: Codex Luna xhigh orchestration
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `37bc7640b43be310a137d815bea5c7f719ff2b52`
branch: `data/historical-universe-v1`
scope: official IDX Listing Activities backend discovery and bounded universe
membership audit for 2024-06-21 through 2026-07-31

## Result

Verdict: `FAIL_NO_COMPLETE_WINDOW`

The exact bounded window has useful official current-snapshot, new-listing,
relisting, and delisting diagnostics, but it is not promoted. The public
relisting route has no completeness metadata and misclassifies the known BUKK
relisting: it is present in `status=ipo` with `RencanaStatus=relisting` but is
absent from the exact `status=relisting` response. Historical Universe V1 is
not frozen. The strict lifecycle table remains fail-closed for six conflict
tickers, and the existing five-ticker/2,280-row price quarantine remains.

## Evidence

- official page: `https://www.idx.id/id/perusahaan-tercatat/aktivitas-pencatatan`;
- listing/relisting route: `/primary/ListingActivity/GetIpoRelisting`;
- delisting route is present in the frontend as
  `/primary/ListingActivity/GetDelisting`, but returned HTTP 404 for GET/POST;
- canonical delisting fallback: official
  `/primary/DigitalStatistic/GetApiDataPaginated` with `urlName=LINK_DELISTING`;
- 506 official `status=ipo` rows for 2013–2026, including BUKK as a relisting;
- exact `status=relisting` scan: SKBM (2012), TALF (2014), INCF (2016);
- 47 new listings and zero exact-filter relistings in the bounded window;
- the mismatch between BUKK's two response modes is why no completeness claim
  is promoted.
- 16 official delisting rows in the bounded window;
- 962 current snapshot rows; 976 valid four-character codes in the bounded
  union after explicit MAMIP/MYRXP exclusions.

## Six tickers

- `BUKK`: exact `RencanaStatus=relisting` in the 2015 IPO response at
  `2015-06-29`; omitted by the exact Relisting response.
- `SKBM`: exact Relisting response at `2012-09-28`; duplicate older exits remain.
- `INRU`, `ITMA`, `KIAS`: no relisting record; authoritative interval starts
  after their old delistings remain unknown.
- `UNTX`: not current and no price file; official 2015-12-07 exit is before the
  window; historical conflict remains quarantined.

## Changed files

- `docs/checkpoints/2026-08-11_HISTORICAL_UNIVERSE_V1_BOUNDED_LISTING_ACTIVITY_AUDIT.md`
- this handoff

## Validation

Pre-change focused tests: 8 passed. Pre-change full suite: 479 passed, 0
failed, 3 existing pandas FutureWarnings. Post-change focused and full test
results are recorded in the final response and commit metadata.

## Boundaries

No PIT sector, OPEN/backfill, corporate actions, model/features, outcomes,
Path Risk, execution/PnL, or `main` work was performed. Raw runtime captures
and credentials remain outside Git.

## Recommended next action

ChatGPT review should retain the fail-closed state. Do not treat the exact
2024-06-21..2026-07-31 period as a certified complete universe, widen the
window, or freeze Historical Universe V1 until relisting archive completeness
and the remaining pre-window conflicts have authoritative evidence.
