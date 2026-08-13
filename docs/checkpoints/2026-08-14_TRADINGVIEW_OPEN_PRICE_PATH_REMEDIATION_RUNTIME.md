# TradingView Open / Price-Path Remediation V1 — Runtime Checkpoint

Date: 2026-08-14
Branch: `data/tradingview-open-price-path-remediation-v1`
Status: `REVIEW`
Scope: one bounded Stage-1 + Stage-2 remediation lane. No bulk acquisition,
canonical-panel write, model fit, Path Risk, O2, protected-outcome access, or
Historical OPEN recovery.

## Decision

`TRADINGVIEW_PRICE_PATH_CONTRACT_REMEDIATION_ACCEPTED_PREREGISTRATION_V2_READY`

The semantic contract is ready for a separately preregistered 2021-2026
price-path admission V2. This does not authorize acquisition, admission,
modelling, or a change to the original frozen rejection.

The original Stage-1 result remains:
`TV60_OPEN_BOUNDARY_PATTERN_FOUND_MEANING_UNPROVEN`.
The original admission result remains:
`TRADINGVIEW_INTRADAY_ADMISSION_REJECTED`.

## Input lineage and activity resolution

The remediation reused, without modification, the Stage-1, admission, and
independent activity artifacts. The independent activity result is exact
regular-market evidence only:

- 195/195 expected keys resolved from official IDX Stock Summary;
- all 195 rows have `Volume = 0`, `Value = 0`, and `Frequency = 0`;
- unresolved rows: 0;
- no inference about NonRegular or all-board activity.

Independent activity lineage:

- branch: `data/tradingview-intraday-independent-activity-resolution-v1`;
- branch head: `c943a76fd56872d981a87519c2eb7072c413322c`;
- runtime head: `3977c51ed00cd798a8e45dc8d8170c82bec4bf67`;
- runtime manifest SHA-256: `f8076b83e170eb6180fbe3c3896000f33894c13e679c31e426816d471b6c0864`;
- resolution CSV SHA-256: `c067e089193b281d69d816df282569e6a8080285ea53766892df9dd336659540`.

## Classifier remediation

The classifier now fail-closes contradictory evidence. Rows with positive
regular pre-open observations are not upgraded to
`TV60_NATIVE_EXTENDED_INCLUDES_OPENING_AUCTION`; the bounded conclusion stays
`TV60_OPEN_BOUNDARY_PATTERN_FOUND_MEANING_UNPROVEN`. A regression test covers
this contradiction path.

## Offline evidence — zero provider calls

The preserved 2026-07-01 1m/5m extended artifacts were reconciled for
BBCA/BBRI/BMRI/TLKM/ASII. Results:

- pre-open rows: 10;
- pre-open Open = official Open: 10/10;
- pre-open Open = TV1D Open: 10/10;
- official Open inside pre-open H/L: 10/10;
- regular first Open = official Open: 4/10;
- no value was selected, repaired, shifted, or written back.

The broader preserved fixed-session offline summary contains 1,282 rows and
shows 666 first-bar Opens equal to canonical Open, 526 equal to previous
canonical Close, and 170/292 TV60-vs-TV1D Open exact with 122 mismatches. These
are diagnostics only; no transformation was introduced.

## Bounded live extension

The frozen matrix was exactly 30 requests: five tickers
(`BBCA`, `BBRI`, `BMRI`, `TLKM`, `ASII`) × three dates
(`2021-07-01`, `2024-07-01`, `2026-07-01`) × 60m × `regular`/`extended`,
using Mathieu adapter commit
`5baea86c8c7e576f13464919c86c3b4c4b0ecf4c`, `server=prodata`, anonymous
access, adjustment `none`, and no pagination/fetch-more.

- requests: 30;
- `AVAILABLE`: 30/30;
- retries: 0;
- fetch-more steps: 0;
- regular pre-open rows: 0;
- extended pre-open rows: 15;
- every extended first timestamp: 08:45 WIB;
- every regular first timestamp: 09:00 WIB;
- paired rows: 15/15;
- extended first Open = official Open: 14/15;
- regular first Open = official Open: 9/15;
- extended first Open = TV1D Open: 14/15;
- regular first Open = TV1D Open: 9/15;
- official Open inside extended first-bar H/L: 15/15;
- mean extended-vs-official Open difference: `-0.0006833401` bps;
- mean regular-vs-official Open difference: `5.2438079754` bps.

The extended/regular timestamp boundary is reproducible and the extended
first bar is strongly aligned with the official Open in this bounded sample.
It is still not proof of an auction execution: the provider exposes no
auction flag, trade classification, or explicit auction-boundary field.
Extended bars therefore remain a separate forensic layer and are not merged
into the regular path.

All 30 raw responses were preserved. The first finalization attempt hit a
local runner directory-creation bug after the 30 network calls had completed.
The raw files were reused by `--mode finalize`; no request was repeated and no
provider result was reinterpreted.

## Frozen readiness boundary

- `semantic_contract_ready = true`;
- `historical_price_path_preregistration_ready = true`;
- `admission_v2_ready = false`;
- `modeling_authorized = false`;
- `acquisition_authorized = false`.

Permitted semantics keep `official_open` and `tv_regular_open` as separate
fields. Raw TradingView provider-session H/L/C/V path features may be used
only after exact session/activity/identity validation. Auction microstructure,
arbitrary Open repair, nearest-bar correction, adjusted-price substitution,
and volume rescaling remain prohibited.

## Artifact provenance

External artifact root (not committed):
`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_open_price_path_remediation_v1_20260814`

Key artifact SHA-256 values:

- `artifact_manifest.json`: `1c4ae4b69fbfb0a2e5912feafa251d805facb8c0e04ba8790fdec1e148c6ac02`;
- `live/summary.json`: `562550beaaa2d8b8a9a944a182182467be63c77f9eab49738bc648b297730931`;
- `live/probe_summary.csv`: `6c86cc965983dd63849bf22e2f34595b267579bf700e18816f29f58d2439ee68`;
- `live/first_60m_pair_reconciliation.csv`: `60a86693fd1e80af38d13854716bb7053b2eb499b49e117abbccad954ee6fddf`;
- `offline/preopen_bars_2026-07-01.csv`: `7da2d90eb79f301afe6be57a5f21e9d1cfb979ba178bd7a3c7d828ee3a16026f`;
- `offline/open_reconciliation_2026-07-01.csv`: `050c70290d019f594986900b2add24f161ddcdac5a0fe5462302f6de4bb2210f`;
- `offline/summary.json`: `34a14bf9b217e5fd927a6baf446068d412681ed1f4cbd9956c30a5dfc8ca8b89`;
- `pre_network_preparation.json`: `dc455ee3fcffcf51626876fad0358905aecf88ee49023ec834498bd205e86ac1`.

The canonical panel SHA before and after is unchanged:
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## Validation and stop boundary

Focused tests: `19 passed`. Full pytest: `58 passed, 1 failed`. The single
failure is the unchanged unrelated
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
fixture assertion: the current fixture emits two revision conflicts
(`raw_close` and `vendor_adj_close`) while the test expects one. The focused
TradingView tests and all remediation tests pass. `git diff --check` passed;
the storage assertion was not changed in this lane.

Stop for independent ChatGPT review. Do not begin admission V2, bulk
acquisition, model work, Historical OPEN recovery, Path Risk, O2, or outcome
access from this lane.
