# H-VOL-01 Volatility Compression — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `PASS_STRUCTURAL_ONLY / FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`  
Candidate ID: none; C5 was **not** created.

## Fixed construction

The preregistered state is:

`-log(median_5((high-low)/close) / median_60((high-low)/close))`

using official-session grids, observed EOD data through decision session `t`,
and the guarded decision universe. No parameter sweep, sign flip, threshold
search, target, forward return, or incumbent score was used.

## Structural result

- Finite eligible support: `308,514` rows, `1,201` dates, `711` tickers;
  `99.2767%` of the `310,761` eligible rows.
- Score distribution: mean `0.01085`, median `0.01063`, standard deviation
  `0.38417`, 1%/99% quantiles `-1.04737 / 0.90418`, min/max
  `-3.42042 / 3.14688`.
- Top-30 membership turnover: mean `29.2778%`, median `30.0000%`, q95
  `43.3333%`, max `53.3333%`.
- Selected value quartiles Q1/Q2/Q3/Q4: `42.7200% / 24.9931% / 18.9759% /
  13.3111%`.
- Selected dollar-turnover quartiles Q1/Q2/Q3/Q4:
  `42.6978% / 25.0542% / 18.9122% / 13.3361%`.

## Structural distinctness

| Comparison | Mean Top-30 overlap | Minimum overlap | Mean daily Spearman |
|---|---:|---:|---:|
| C1 | `9.5209%` | `0%` | `0.1047` |
| C2 | `8.0155%` | `0%` | `-0.0410` |
| C4 | `15.5676%` | `0%` | `0.1856` |
| H-LIQ-01 | `13.5803%` | `0%` | `-0.0780` |

The low overlap supports structural distinctness from the current candidates,
but does not prove predictive orthogonality. H-VOL has positive daily rank
dependence with C4 in most dates and substantial bottom-value concentration.
Historical archaeology also contains adjacent range/flat-range families (V4-B
range acceptance/rejection and O2/O2.1 flat-range geometry), so exact novelty
is not established.

## Disposition

The mechanism remains open as a future research direction, but not as a
candidate. The main adverse evidence is its Q1 value/turnover concentration
and `29.28%` Top-30 churn. Executable economics remain `UNKNOWN` because ADV,
spread, queue depth, fill probability, and historical capacity are not
admitted. Price-basis/PIT authority is also unresolved.

The independent review therefore concluded:

- construction/support: `PASS` narrowly;
- novelty: `UNKNOWN`, not a pass and not a rejection;
- economics: `UNKNOWN` with adverse structural warning;
- C5 admission: `NO-GO`.

## Integrity completion

The first deterministic run correctly produced support, turnover, and overlap
but omitted score distribution and daily rank-dependence fields that were
already declared in the preregistration. It also did not include the bounded
H-LIQ comparison. The script was corrected by an integrity-completion patch
without changing formula, inputs, windows, direction, or candidate budget, then
rerun from the committed code below.

## Provenance

- Preregistration: `docs/checkpoints/2026-09-19_ALPHA_HVOL01_COMPRESSION_PREREGISTRATION_V1.md`
- Preregistration SHA-256: `009780e37254a9c6a2f1457101793b2b1ce4c6a6f5bec81f6e3a327adb330d3d`
- Code: `research/alpha_hvol01_compression_diagnostic_v1.py`
- Code SHA-256: `ce1abf005724b6a337c37ebce2349fb32ed95af0c6e33ff70decc1774e55c02f`
- Output: external staged `alpha_hvol01_compression_diagnostic_v1.json`
- Output SHA-256: `7fe2f266c2ee5a8cdffe59bbb006ae491351704423e1db4458b01b41a9fa4f7b`
- Output status: `PASS_STRUCTURAL_ONLY`
- Repository head used: `f7bf8e6195a55c911a40081036c0edb99a6ad5f6`
- Manifest SHA-256: `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96`
- Panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Guarded features SHA-256: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Official sessions SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Tradability anchors SHA-256: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`

## Boundary

This is target-free structural evidence only. It does not clear corporate
actions, PIT/as-of, identity continuity, survivorship, capacity, or predictive
evaluation. No protected target/outcome, provider, network, cloud/R2, capture,
telemetry, scheduler, or canonical dataset was accessed or modified.
