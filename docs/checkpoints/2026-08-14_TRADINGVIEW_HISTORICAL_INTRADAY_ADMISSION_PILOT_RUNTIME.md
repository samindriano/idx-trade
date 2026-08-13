# TradingView Historical Intraday Admission Pilot V1 - Runtime

Status: `RUNTIME_COMPLETE_PENDING_INDEPENDENT_REVIEW`

This is the frozen, bounded anonymous `prodata` pilot for 2021-2026. It is
not a bulk-acquisition authorization and did not write the canonical panel,
models, features, O2, Path Risk, or protected outcomes.

## Lineage and frozen inputs

- Repository: `samindriano/idx-trade`
- Branch: `data/tradingview-historical-intraday-admission-pilot-v1`
- Initial audit lineage: `data/tradingview-historical-intraday-audit-v1@fb5a6384a49ce2a3c80c07ae2b79134de2f584bb`
- Remediation lineage: `data/tradingview-historical-intraday-remediation-v1@fcfa5084c172c21d21d4e00489808b6bb20f6333`
- Independent remediation review: `6b12d689d06d7e71a5c642f948e590858764fcca`
- Mathieu2301/TradingView-API: `5baea86c8c7e576f13464919c86c3b4c4b0ecf4c` (package 3.5.2)
- endenwer/tradingview-ws: `97c743c8230f732e5a49646dd8f0f44c5981a458`
- Access: anonymous only; no credentials, cookies, session tokens, alternate
  symbols, or authenticated requests.
- Primary request contract: `server=prodata`, `symbol=IDX:<ticker>`,
  `timeframe=60`, regular session, `adjustment=none`, raw epochs/OHLCV kept.
- TV1D control contract: same server/symbol/session/adjustment, timeframe `1D`.
- Endenwer numeric rows are quarantine-only because the pinned resolver uses
  hard-coded split adjustment.

External artifact root (outside Git, new and immutable for this run):

`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_intraday_admission_pilot_v1_20260814`

Input hashes:

- frozen sample manifest: `3de36746942bbf6e7dc201ce14d1aa94c75ab1dc6ebd59989e828f41114971bd`
- config: `7feafca01885486e958b03f1894b7636e63391a1297eaf3059fbd91c33524d5b`
- security master: `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`
- official calendar: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- canonical panel before and after: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- official split/reverse-split evidence: `a0ef73a548b3657260b46a0c497e6f87dd9b5138588e23006d4b538677125b35`

The six fixed windows were frozen before network execution. They are July 1-7
with only preserved official IDX dates: 2021 `Jul 1,2,5,6,7`; 2022
`Jul 1,4,5,6,7`; 2023 `Jul 3,4,5,6,7`; 2024 `Jul 1-5`; 2025
`Jul 1,2,3,4,7`; and 2026 `Jul 1,2,3,6,7`. No session dates were invented.

## Frozen sample and request counts

- 50 unique deterministic tickers, seed `20260814`.
- 40 core common stocks plus 10 listing/liquidity/identity edge controls.
- Mandatory controls: `BBCA BBRI BMRI TLKM ASII INDF UNTR ANTM PTBA DSSA`.
- Mathieu requests: `368` total (`300` fixed 60m, `60` TV1D, `8` deep
  pagination).
- Endenwer corroborator requests: `8`.
- Raw files: `368` Mathieu + `8` endenwer = `376`.
- Mathieu raw period rows: `258,504`; valid rows: `258,504`.
- Mathieu malformed/duplicate/invalid OHLCV rows: `0/0/0`.
- Raw rows outside the requested fixed windows: `181,598`; rows not
  session-admissible (including out-of-window rows retained for audit):
  `185,438`. These rows were excluded from certified-window aggregation; no
  timestamp shifting or silent dropping of evidence occurred.

## Provider status and event evidence

Mathieu status counts:

| phase | AVAILABLE | UNCLASSIFIED_NO_DATA | other |
|---|---:|---:|---:|
| fixed 60m | 296 | 4 | 0 |
| TV1D | 60 | 0 | 0 |
| deep pagination | 8 | 0 | 0 |

The four unavailable fixed pairs are all 2021: `BUKA`, `FLMC`, `NICL`, and
`UVCR`. Each had websocket connection, `symbol_loaded`, and market info, but
no update before the 25-second adapter boundary. They are retained as
`UNCLASSIFIED_NO_DATA`, not reclassified as entitlement or symbol failure.
There were no explicit `SYMBOL_ERROR`, transport error, entitlement error, or
provider-error responses in this run.

Completion observations:

- Fixed/TV1D requests: 356 stopped at `initial_update_no_pagination`.
- Deep requests: 16 page extensions across the 8 requests; 8 later stopped
  with `page_timeout_no_extension` after reaching the same final minimum.
- Mathieu's pinned client does not expose `series_completed`, so empty cases
  remain conservative `UNCLASSIFIED_NO_DATA`.
- Endenwer: `8/8 AVAILABLE`, `8/8 series_completed`, two bounded pages each;
  numeric comparison is `QUARANTINED_ADJUSTMENT_MISMATCH`.

## Coverage

Coverage is calculated only for known-listed ticker/year pairs from the frozen
security master. Pre-listing pairs are excluded from provider-failure counts.

| year | known-listed pairs | available pairs | target-window availability | expected certified sessions | observed admissible sessions | certified session coverage |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 46 | 44 | 95.65% | 230 | 215 | 93.48% |
| 2022 | 50 | 49 | 98.00% | 250 | 236 | 94.40% |
| 2023 | 50 | 48 | 96.00% | 250 | 220 | 88.00% |
| 2024 | 50 | 48 | 96.00% | 250 | 212 | 84.80% |
| 2025 | 50 | 40 | 80.00% | 250 | 195 | 78.00% |
| 2026 | 50 | 42 | 84.00% | 250 | 204 | 81.60% |
| **all** | **296** | **271** | **91.55%** | **1,480** | **1,282** | **86.62%** |

The preferred `2021-2026` range fails the frozen certified-session coverage
gate overall and in 2023-2026. The exact frozen fallback `2022-2026` also fails
certified-session coverage overall and in 2023-2026. No other cutoff was
selected.

Bounded deep pagination reached `2020-01-02` for every long-lived control
(`ASII BBCA BBRI BMRI INDF PTBA TLKM UNTR`), with `81,490` normalized deep
rows through `2026-07-31`. This corroborates depth for the selected controls;
it does not convert the full sample's certified-window coverage into a pass.

## TV60 daily fidelity and volume

The fixed TV60 aggregation produced `1,282` non-corporate-action matched
daily rows. The preserved authoritative CA evidence was loaded and applied as
a quarantine key; no sampled July row matched a split/reverse-split key, so
`corporate_action_quarantined` rows in this fixed comparison were `0`.

| year | matched rows | HLC exact | volume within +/-5% | certified session coverage |
|---|---:|---:|---:|---:|
| 2021 | 215 | 93.95% | 100.00% | 93.48% |
| 2022 | 236 | 95.34% | 91.53% | 94.40% |
| 2023 | 220 | 98.64% | 93.18% | 88.00% |
| 2024 | 212 | 100.00% | 97.64% | 84.80% |
| 2025 | 195 | 95.38% | 91.28% | 78.00% |
| 2026 | 204 | 93.63% | 96.08% | 81.60% |
| **all** | **1,282** | **96.18%** | **95.01%** | **86.62%** |

TV60 field counts over all 1,282 rows were Open `666/1,282`, High
`1,251/1,282`, Low `1,243/1,282`, Close `1,261/1,282`, HLC `1,233/1,282`,
and exact Volume `566/1,282`. The volume ratio had min `0.272727`, max
`1.230769`, mean `0.989149`; q01/q05/q25/q50/q75/q95/q99 were
`0.828220/0.953903/0.991551/0.999786/1.000000/1.000000/1.014191`.
Within +/-0.5%/+/-1%/+/-2%/+/-5%/+/-10% counts were
`854/974/1,101/1,218/1,255`; multiplicative cluster counts near
`0.01/0.1/1/10/100` were `0/0/1,276/0/0`.

The frozen TV60 HLC and volume gates pass at the matched-row level. Coverage
gates still fail and therefore cannot be rescued by fidelity.

## Open semantics and TV1D cross-check

TV60 aggregated Open was exact to the canonical daily Open on `666/1,282`
rows (`51.95%`). The independent TV60-vs-TV1D Open comparison was exact on
`433/731` rows (`59.23%`). The mismatch is not repaired, rescaled, or
forward-filled.

The TV1D comparison had `22,855` non-CA matched rows, of which `21,473` had a
canonical Open. On Open-present rows, exact rates were Open `21,239/21,473`
(`98.91%`), High `21,241/21,473` (`98.92%`), Low `21,247/21,473`
(`98.95%`), Close `21,249/21,473` (`98.96%`), exact Volume `21,119/21,473`
(`98.35%`), and HLC `21,233/21,473` (`98.88%`). The frozen composite TV1D
reference rate, exempting rows without canonical Open, was `22,613/22,855`
(`98.94%`) overall; every evaluated year's composite rate met the frozen
TV1D gate.

This establishes a reproducible provider/session-boundary semantic difference:
TV1D is close to canonical, but the TV60 aggregation's first bar/open
convention is not reliable enough for full OHLCV admission. No deterministic
raw-bar convention was authorized or proven, so the price-path-only fallback
is not admitted because the coverage gates fail first.

## Automatic verdict

`evaluate_frozen_verdict(...)` generated:

`TRADINGVIEW_INTRADAY_ADMISSION_REJECTED`

Preferred `2021-2026` gates failed on certified-session coverage overall and
2023-2026, plus target-window availability in 2025 and 2026. The exact
fallback `2022-2026` also failed certified-session coverage and target-window
availability in 2025 and 2026. HLC, volume, TV1D reference, deep reach, symbol
resolution, and structural validity gates passed. Full-OHLCV is additionally
blocked by TV60 Open (`59.23%` vs TV1D), but price-path-only admission cannot
override the failed coverage gates.

No bulk or downstream authorization follows this result. TradingView remains
unadmitted for this frozen historical intraday contract pending a new,
separately preregistered hypothesis; do not automatically rerun, backfill,
restart Path Risk, modify O2, access protected outcomes, or model.

## Artifact integrity and validation

The external manifest contains `389` entries; all `389/389` entries were
present and SHA-256 verified after aggregation. Manifest SHA-256:

`de7246e447a83b15c083d19a00808f13670d97f720bd1e28ce8756e02186e8ee`

Key artifact hashes:

- `audit_summary.json`: `79be8e3d70b09dc0a047378e87588967a0148bc45d7532d4e8011c62ec439002`
- `input_manifest.json`: `407625adcca35e5f93ddf794e1caa5906bd94f00819b09bba826d69ca7320ca1`
- `normalized/mathieu_request_manifest.csv`: `ca1271ab7551c2f4cdd3029b179a11748cb2a1892726477fa9b2e6b40603d4d8`
- `normalized/mathieu_intraday_bars.csv`: `332c26cb2a7951b2664d99349e4cfffeb516d5c416b0c37a5e6fe4bcdfff4f95`
- `normalized/daily_comparison.csv`: `e05c1b6a1bc7c6f31b3f58fe0e36828c61461f57a355ca3b969757c2cd83670f`
- `normalized/tv1d_comparison.csv`: `47c4cb5bd1d5f9fdf2138c39fefad9aa4b8277a7058d5e2d54f981d3d9aacdf9`
- `normalized/tv60_tv1d_comparison.csv`: `e5acb1be65ff3698027e41aa60d2f58bb928e827c9ed777a1725aad8ba8ca283`
- `normalized/deep_intraday_bars.csv`: `fd9839bf15b270dfc2ebf9617e373cc0fe5cae75c4dc0d46be3c20e32d05bbb4`
- `normalized/deep_pagination_summary.csv`: `8ba7b94289f1f4c7c81a2b4dd231591c9a341ff949afaa879ae6ea2bca5ef7af`
- `normalized/endenwer_depth_summary.csv`: `049b931d7895e0e0e43e53849dec30afbc6f71f1de3afea1a1ff5ddc823ef87e`

The canonical panel SHA before and after runtime remained
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.
Existing audit/remediation artifact roots were not modified. No runtime data
was added to Git.

Validation:

- focused pilot + remediation tests: `14 passed`;
- Python compilation: passed;
- Mathieu and endenwer adapter JavaScript syntax checks: passed;
- adapter dependency install: passed, `0` npm vulnerabilities;
- full pytest: `53 passed, 1 failed`;
- the one failure is pre-existing and outside this lane:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expects one conflict while the existing fixture emits two (`raw_close` and
  `vendor_adj_close`); no storage code or test was changed;
- `git diff --check`: required and run before final push.

This checkpoint stops for independent ChatGPT review.
