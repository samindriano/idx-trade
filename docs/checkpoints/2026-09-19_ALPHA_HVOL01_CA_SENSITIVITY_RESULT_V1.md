# H-VOL-01 Corporate-Action Sensitivity — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `PASS_STRUCTURAL_ONLY / PARTIAL FORENSIC EVIDENCE`  
Candidate: none; no C5 created.

## Question and boundary

This audit tested whether the fixed H-VOL-01 compression state changes when the
retained `idx_close` comparison values are substituted for the 188 unresolved
non-stable-scale rows. The substitution was in-memory only. The comparison
values are not admitted corrections, and this result does not certify PIT,
corporate-action completeness, issuer continuity, or predictive value.

No target, forward return, incumbent score, provider, network, cloud, capture,
telemetry, canonical dataset, refit, or model artifact was accessed or changed.

## Fixed construction

The score remained exactly:

`-log(median_5((high-low)/close) / median_60((high-low)/close))`

using the guarded official-session universe. Only `close` was replaced for the
188 retained comparison keys; high, low, volume, universe, windows, direction,
and eligibility were unchanged.

## Result

- Baseline and counterfactual support were identical: `308,514` finite
  eligible rows.
- The 188-row artifact covers `19` tickers; `65` of those rows were finite
  eligible score rows in the comparison.
- Total score changes: `547`; total rank changes: `8,876`.
- Direct unresolved rows: `60` score changes / `57` rank changes out of `65`
  finite compared rows; mean absolute score change `0.38819`.
- Spillover rows: `487` score changes / `8,819` rank changes out of `308,449`
  finite compared rows; mean absolute score change `0.11771`.
- Top-30 sets changed on `37` of `1,201` common dates.
- Mean Top-30 overlap: `99.8307%`; minimum overlap: `86.6667%`.
- Changed Top-30 slots classified as direct/spillover: `14 / 108`.

## Interpretation

The fixed H-VOL representation is relatively stable at the Top-30 portfolio
level under this bounded counterfactual, but it is not basis-insensitive:
almost all finite direct rows in the unresolved artifact change, and the
counterfactual creates rank spillover across the cross-section. The minimum
Top-30 overlap of `86.6667%` is a material forensic caution, not a rejection
of the mechanism and not a clearance of the price basis.

The result therefore narrows, but does not resolve, H-VOL's data risk. Keep
the disposition at `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`.
Do not create C5, do not promote H-VOL to the protected evaluation packet, and
do not treat `idx_close` as truth.

## Provenance

- Preregistration: `2026-09-19_ALPHA_HVOL01_CA_SENSITIVITY_PREREGISTRATION_V1.md`
- Code: `research/alpha_hvol01_ca_sensitivity_v1.py`
- Code SHA-256: `95e3a781f0021945515370f4e99bc92c64da9d9866fbf39a56811cf2b2a81aa3`
- Output: external staged `alpha_hvol01_ca_sensitivity_v1.json`
- Output SHA-256: `ba2f47d378815691877b8c1661551bb9f89e71f49c7b585f8c853f128381609e`
- Repository head used: `c6f4157669e5e51aaf4135dac32df173be59aa31`
- H-VOL structural output SHA-256: `7fe2f266c2ee5a8cdffe59bbb006ae491351704423e1db4458b01b41a9fa4f7b`
- Manifest SHA-256: `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96`
- Panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Guarded features SHA-256: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Official sessions SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Tradability anchors SHA-256: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`
- Unresolved-scale source SHA-256: `eaedba187a3645a83c06c3885dac2c819e818fb68636cfedf2d32e7792432743`

## Decision

`PASS_STRUCTURAL_ONLY`: bounded CA sensitivity is quantified; global
price-basis/PIT admission remains `UNKNOWN`, and H-VOL remains a future
research hypothesis only.
