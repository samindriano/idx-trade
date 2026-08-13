# TradingView Historical Intraday Remediation V1 - Runtime

Status: `BOUNDED_RUNTIME_COMPLETE_PENDING_INDEPENDENT_REVIEW`

This checkpoint records the frozen anonymous remediation run. It does not
modify the prior audit artifacts, the canonical panel, model inputs, O2, or
protected outcomes.

## Lineage, inputs, and artifacts

- Branch: `data/tradingview-historical-intraday-remediation-v1`
- Prior reviewed lineage: `data/tradingview-historical-intraday-audit-v1` at
  `fb5a6384a49ce2a3c80c07ae2b79134de2f584bb`
- Mathieu2301/TradingView-API pinned commit:
  `5baea86c8c7e576f13464919c86c3b4c4b0ecf4c` (package 3.5.2)
- endenwer/tradingview-ws pinned commit:
  `97c743c8230f732e5a49646dd8f0f44c5981a458`
- New external artifact root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_intraday_remediation_v1_20260814_retry1`
- Frozen sample manifest SHA-256:
  `966b164182218816a24a2f535c48ee9fae01d80e93ec979b2ce4bdd4b14578cf`
- New artifact manifest SHA-256:
  `aa57118d2def02e87fd6b9664203fcc0caa8228df01e0d14205782952d8cba24`
- New artifact manifest contains 303 hashed artifacts. Key hashes:
  - `audit_summary.json`:
    `435e93dc5622b14a62efd73d8909082653e602047e5dd934b8c2cce0fbe13622`
  - `forensic_summary.json`:
    `8291cb8eeea7d5fa19c80225028e091d3fd8158f567ca299e3a52dd19e06e89a`
  - `normalized/mathieu_request_manifest.csv`:
    `b4a720c63d0193f6952c27231cf1fb15c6d38d5a795bace4dfbe2da5f09c3aae`
  - `normalized/mathieu_intraday_bars.csv`:
    `9a5a91af85e82b06b754f9b01ea0e7f899596f7ec2ee4830eac10c2195887a2c`
  - `normalized/daily_comparison.csv`:
    `7337b9423f482b198272b85976617e88a838d0ee8ae434ed38c2d2e927df9f6d`
  - `normalized/three_way_reconciliation.csv`:
    `a198b4858dca09b59a0239e42d5f24145ddeee84d6880a1c9aa5bdef2d8e686a`
  - `normalized/tv1d_daily.csv`:
    `4be485b47f27b9b196b9c9e3a94bfddccfdf6fac9b4fe900aae390748b89c6e4`
  - `normalized/endenwer_intraday_bars.csv`:
    `57bf281936381c9bf5d1b5e29fcbd420fab1e439f56641d8eed81319e7f5d9bf`
- Manifest verification after runtime: 303/303 entries present, 0 hash
  mismatches. The canonical panel re-hash after runtime remained unchanged.
- Prior artifact root was read-only and remains unchanged:
  - manifest:
    `ebd5d86dfb673e5a86aef51b11cc4724f5c9a5831b99782e272c683cdd1d4602`
  - sample:
    `768c1f1db4d999c97f6cbfbbd1babd490c7bb21a2c180cea01efa8263a79d9c4`
- Canonical panel SHA-256 before and after:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- Official calendar and security master were read-only inputs; no historical
  2018/2020 official session rows were available in the preserved calendar.

## Frozen runtime and access boundary

The deterministic sample contained 20 tickers across five July eras:
2018, 2020, 2022, 2024, and 2026. Anonymous requests only were used. The
Mathieu matrix made 270 requests: 200 paired `data`/`prodata` 60-minute
requests, 50 bounded pagination requests, and 20 `prodata` 1D requests. The
endenwer cross-check made 20 `prodata` requests. No credentials, cookies,
alternate symbols, pagination beyond the frozen limits, or alternate data
providers were used.

## Mathieu data versus prodata

The phase-1 paired sample has 100 requests per server. Raw status counts were:

| server | AVAILABLE | UNCLASSIFIED_NO_DATA | SYMBOL_ERROR |
|---|---:|---:|---:|
| data | 42 | 53 | 5 |
| prodata | 70 | 25 | 5 |

The five `SYMBOL_ERROR` requests per server are the five MFIN era probes. No
explicit entitlement, permission, transport, or provider error was observed.
Prodata therefore improved raw availability from 42/100 to 70/100 and exact
requested-window presence from 38/100 to 65/100. The improvement was largest
in the 2018/2020/2022 probes; the 2024/2026 raw availability was already
similar.

| era | data raw | prodata raw | data exact window | prodata exact window |
|---|---:|---:|---:|---:|
| 2018 | 1/20 | 4/20 | 1/20 | 4/20 |
| 2020 | 2/20 | 14/20 | 2/20 | 14/20 |
| 2022 | 3/20 | 16/20 | 3/20 | 15/20 |
| 2024 | 17/20 | 17/20 | 16/20 | 16/20 |
| 2026 | 19/20 | 19/20 | 16/20 | 16/20 |

### Event and timeout classification

The thin Mathieu adapter captured websocket/event traces, market-info
presence, elapsed time, and bounded fetch-more steps. Its pinned upstream
client does not expose `series_completed`, so the adapter deliberately leaves
completion-empty cases as `UNCLASSIFIED_NO_DATA` rather than guessing
`SERIES_COMPLETED_EMPTY` or entitlement failure.

The phase-1 no-data traces generally had `connected` + `symbol_loaded` + the
adapter timeout and no update. MFIN traces had `connected` + `symbol_error`.
The old audit's 55 timeout rows all had market info, zero periods, and roughly
25.019-25.036 seconds elapsed, but no persisted event trace; the remediation
confirms that the old `TIMEOUT` label was too coarse. There was no evidence to
claim entitlement failure.

## Bounded pagination

The 50 phase-2 requests produced 30 `max_steps` completions and 20
`request_timeout` outcomes, with 300 observed extensions and 550 periods in
the available phase-2 responses. The available `data`/`prodata` traces showed
the requested repeated `request_more_data` steps. Three phase-1 available
responses also stopped without an extension (DSSA 2018, DSSA 2020, and GOTO
2022), so pagination is not uniformly deterministic through this client.

## Independent endenwer protocol cross-check

All 20 requests returned `AVAILABLE` and `series_completed`; each used two
bounded pagination pages. Returned depth was 10,248-10,269 periods per
request, with 205,184 normalized rows in total. The common raw depth reached
2020-01-02 09:00 WIB through 2026-08-13 16:00 WIB for the cross-check subset.
The pinned public API does not accept the frozen `to` timestamp, so this is a
transport/depth/completion observation rather than an exact era-date numeric
pair. Its resolver hard-codes `adjustment=splits`; all numeric endenwer rows
are therefore quarantined as `QUARANTINED_ADJUSTMENT_MISMATCH`, not treated as
raw-price reconciliation evidence.

## Volume and daily reconciliation

The prior immutable non-corporate set had 162 matched daily rows. The raw
provider/canonical volume ratio had min/max/mean
`0.5513419093 / 1.0208202401 / 0.9794315455`, quantiles
`q01=0.7978736632, q05=0.9282391500, q25=0.9802290535, q50=0.9920428330,
q75=0.9982896321, q95=1.0000000000, q99=1.0000152027`, and counts within
`+/-0.5%, +/-1%, +/-2%, +/-5%, +/-10%` of `66, 88, 121, 147, 156`.
The factor-cluster counts near `0.01/0.1/1/10/100` were `0/0/161/0/0`.
No rescaling or repair was performed.

The new bounded TV60/TV1D/canonical comparison contained 404 matched rows,
379 non-corporate rows, and 25 quarantined corporate-action/control rows:

| source slice | matched | non-CA | HLC exact | Open exact when present | volume within 5% |
|---|---:|---:|---:|---:|---:|
| data TV60 | 172 | 162 | 158/162 (97.53%) | 90/145 (62.07%) | 147/162 (90.74%) |
| prodata TV60 | 232 | 217 | 95.85% | 59.00% | 90.78% |
| combined | 404 | 379 | 96.57% | 60.29% | 90.77% |

For all-present rows, TV1D was exact to canonical for HLC/Open and near the
canonical volume, while TV60 HLC was near-equivalent but not always exact.
The reconciler found 2 genuine three-way disagreements. The remaining class
counts are explicit missing-row classes, not disagreements:

`TV1D_NO_ROW=235`, `TV1D_AND_CANONICAL_NO_ROW=69`,
`TV60_AND_CANONICAL_NO_ROW=50`, `TV60_NO_ROW=25`,
`TV60_APPROX_TV1D_APPROX_CANONICAL=106`,
`TV60_DIFF_TV1D_APPROX_CANONICAL=17`, and
`THREE_WAY_DISAGREEMENT=2`.

The combined non-CA volume ratio was min/max/mean
`0.5513419093 / 1.0208202401 / 0.9796951657`, with quantiles
`q01=0.8046762536, q05=0.9280151176, q25=0.9796508481, q50=0.9912493363,
q75=0.9980203812, q95=1.0000000000, q99=1.0082726043`; 344/379 (90.77%)
were within 5%, and the factor-cluster counts were `0/0/377/0/0`.

## Listing-aware denominators and time semantics

For the 100 phase-1 ticker/era pairs per server, the security master marks 84
as known listed. Only 60 have preserved official calendar/session evidence;
2018/2020 results remain timestamp/depth diagnostics, not certified session
coverage. For the official-session eras 2022/2024/2026, the exact-window rate
among 54 known-listed pairs was 35/54 (64.81%) for `data` and 47/54 (87.04%)
for `prodata`. Pre-listing pairs are not classified as provider failures.

Provider timezone metadata was offset-equivalent UTC+7. Raw epochs were
converted explicitly to `Asia/Jakarta`; session admissibility used the
08:00-16:00 WIB band without inventing dates or shifting timestamps.

## Decision and boundaries

Decision: `TRADINGVIEW_SOURCE_REMEDIATION_SUPPORTS_ADMISSION_PILOT`.

The paired server result shows a material anonymous access-path improvement,
the independent protocol exposes deterministic series completion and deep
2020-2026 depth on the bounded liquid subset, and TV1D/HLC/Open reconciliation
is strong enough to justify a separately preregistered bounded admission pilot.
This is not an execution-grade or bulk-history approval: TV60 pagination has
timeouts, MFIN remains a symbol-error case, 2018 remains shallow in the
sample, and volume is not exact. A future pilot must freeze its own source,
session, volume, Open, corporate-action, and failure gates. No pilot is
started by this checkpoint.

No fork was needed. The thin adapters were sufficient to expose the required
events and preserve the independent client as a quarantined protocol/depth
cross-check.

No canonical panel write, bulk historical backfill, feature/model work,
Path Risk restart, O2 modification/access, protected-outcome access,
authenticated experiment, or execution-PnL claim occurred. `execution_grade`
and all forward counters remain untouched.

## Validation

- Focused remediation tests: `7 passed`.
- Python compilation and both adapter JavaScript syntax checks: passed.
- Full repository-local pytest: `46 passed, 1 pre-existing failure`.
- Pre-existing failure: `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`; the existing fixture emits two revision conflicts (`raw_close` and `vendor_adj_close`) while asserting one. This lane did not modify storage code or that test.
- `git diff --check`: required before final push.

The external artifact manifest is the authoritative complete hash listing for
all 303 runtime artifacts. This branch stops here for independent ChatGPT
review.
