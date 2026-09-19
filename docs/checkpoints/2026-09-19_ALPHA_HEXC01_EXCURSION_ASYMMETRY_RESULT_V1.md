# H-EXC-01 Previous-Close Excursion Asymmetry — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `STRUCTURALLY_REJECTED_AS_WRITTEN / MECHANISM_NOT_CLOSED`  
Candidate: none; no C5 created.

## Fixed construction

The preregistered score was:

`median_5(((high-prev_close)-(prev_close-low)) /
((high-prev_close)+(prev_close-low)))`

on the official-session grid, using no Open, volume, target, or future return.
No clipping, denominator floor, winsorisation, or sign selection was applied.

## Structural result

- Finite eligible support: `305,814` rows, `1,201` dates, `711` tickers.
- Top-30 turnover: mean `40.9694%`, median `40.0000%`, q95 `56.6667%`,
  maximum `93.3333%`.
- Selected value quartiles Q1/Q2/Q3/Q4:
  `17.7491% / 21.6264% / 25.3872% / 35.2373%`.
- Selected dollar-turnover quartiles Q1/Q2/Q3/Q4:
  `17.7713% / 21.6375% / 25.3594% / 35.2318%`.
- Score distribution: mean `0.01844`, median `0`, standard deviation
  `0.49900`, 1%/99% `-1.0 / 1.0`, minimum/maximum `-16.2 / 5.0`.

The extreme minimum and maximum show that the apparently normalized
excursion-asymmetry score is not bounded when the previous close lies outside
the current high/low interval or when the denominator becomes small. This is a
numerical/representation failure, not evidence of extreme economic pressure.

## Structural distinctness

| Comparison | Mean Top-30 overlap | Minimum overlap | Mean daily Spearman |
|---|---:|---:|---:|
| C1 | `1.2708%` | `0%` | `-0.5012` |
| C2 | `25.1624%` | `0%` | `0.1269` |
| C4 | `4.7960%` | `0%` | `-0.2454` |
| H-LIQ-01 | `14.2770%` | `0%` | `0.0825` |
| H-VOL-01 5/60 | `11.8568%` | `0%` | `-0.0398` |

The low overlap is not predictive orthogonality. The negative dependence with
C1/C4 and positive dependence with C2 are consistent with a distinct geometric
input, but the representation cannot be carried forward in its raw form.

## Disposition

The exact H-EXC-01 representation is `STRUCTURALLY_REJECTED_AS_WRITTEN` due to
unbounded numerical tails and high churn. This closes the exact formula, not
the broader previous-close excursion/rejection mechanism. A bounded or robust
alternative would require a new hypothesis card, a new fixed contract, and a
fresh preregistration; no rescue variant is authorized by this result.

No candidate ID, protected packet entry, predictive claim, or status upgrade
was created. No target, provider, cloud, capture, telemetry, or canonical data
was accessed or modified.

## Provenance

- Preregistration: `2026-09-19_ALPHA_HEXC01_EXCURSION_ASYMMETRY_PREREGISTRATION_V1.md`
- Code: `research/alpha_hex01_excursion_asymmetry_diagnostic_v1.py`
- Code SHA-256: `9ab40ee19d2627e43fd206c3b40cd1ce211d2f06ebe756c282328839dc55ea3e`
- Output: external staged `alpha_hex01_excursion_asymmetry_diagnostic_v1.json`
- Output SHA-256: `5aca711dd718e47d68b079206113da50f7a5ccbe996e58ee6f96421f9da28c00`
- Repository head used: `84fff2d47a65b3c190f536ef1ee5141ba689b8fb`
- H-VOL comparison output SHA-256: `7fe2f266c2ee5a8cdffe59bbb006ae491351704423e1db4458b01b41a9fa4f7b`
- Manifest SHA-256: `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96`
- Panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Guarded features SHA-256: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Official sessions SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Tradability anchors SHA-256: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`
