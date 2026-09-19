# Capacity, Friction-Tail, and Concentration Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Category: `C / G / K / L — bounded structural economics`
Status: `PASS_STRUCTURAL_ONLY / EXECUTABLE CAPACITY BLOCKED`

## Question

Do the existing selected portfolios have hidden turnover tails, repeated-name
concentration, or bucket exposures that are not visible in mean turnover and a
single market-value proxy?

This artifact is outcome-blind. It uses the fixed final `600` official
sessions, deterministic Top-30 selection, the guarded C1/C2/C4 ranks, and
recomputed H-LIQ-01, H-VOL-01, and H-EXC-02 diagnostics. It does not estimate
ADV, spread, queue position, fill probability, executable capacity, or
profitability.

## Contract

- Selected slots: `600 * 30 = 18,000` per surface.
- Turnover: `1 - consecutive Top-30 name overlap / 30`, adjacent official
  sessions only.
- Friction burden: one-way turnover multiplied by fixed `60 bps` base or
  `110 bps` sensitivity matched-turnover burden. This is a diagnostic burden,
  not realized return.
- Quartiles: same-day eligible cross-sectional quartiles for regular market
  value, raw volume, and `close * volume` dollar turnover.
- Quartile shares are selected-slot fractions among bucketable rows, not
  notional/value-weighted exposure.
- C3 is not included in this six-surface tail artifact because its broad
  600-session selection support is absent and its PIT contract remains
  blocked.

## Results over the fixed 600-session window

| Surface | Mean turnover | Q95 | Q99 | Max | Base burden mean / Q99 / max (bps/NAV) | Q1 market-value share | Top-10 slot share | HHI | Effective names |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C1 | 42.1536% | 56.6667% | 63.3333% | 66.6667% | 25.2922 / 38.00 / 40.00 | 26.6333% | 5.8833% | 0.003192 | 313.27 |
| C2 | 32.9104% | 50.0000% | 56.6667% | 63.3333% | 19.7462 / 34.00 / 38.00 | 21.2556% | 7.1222% | 0.003131 | 319.42 |
| C4 | 23.6950% | 36.6667% | 40.0000% | 46.6667% | 14.2170 / 24.00 / 28.00 | 34.4556% | 7.3889% | 0.003432 | 291.38 |
| H-LIQ-01 | 10.3061% | 16.6667% | 20.0000% | 26.6667% | 6.1836 / 12.00 / 16.00 | 39.6722% | 10.7667% | 0.004417 | 226.38 |
| H-VOL-01 | 29.7718% | 43.3333% | 50.0000% | 53.3333% | 17.8631 / 30.00 / 32.00 | 40.6889% | 5.3500% | 0.002763 | 361.90 |
| H-EXC-02 | 41.5971% | 56.6667% | 66.7333% | 86.6667% | 24.9583 / 40.04 / 52.00 | 17.8944% | 7.2667% | 0.003643 | 274.51 |

All six surfaces had `18,000/18,000` bucketable selected rows for each of the
three bucket types. The Q1 raw-volume shares were C1 `26.8444%`, C2
`17.6556%`, C4 `32.5778%`, H-LIQ-01 `27.5778%`, H-VOL-01 `35.8611%`, and
H-EXC-02 `21.0333%`. The Q1 dollar-turnover shares were C1 `26.7611%`, C2
`21.3000%`, C4 `34.5722%`, H-LIQ-01 `39.6889%`, H-VOL-01 `40.6611%`, and
H-EXC-02 `17.9000%`.

## Adjudication

| Question | Result |
|---|---|
| Slot coverage and quartile arithmetic | `PASS — structural` |
| Repeated-name concentration | `PASS — descriptive only` |
| Turnover-tail visibility | `PASS — newly quantified` |
| H-LIQ low-value concentration | `CAUTION` |
| H-VOL low-value and dollar-turnover concentration | `CAUTION` |
| H-EXC-02 turnover-tail burden | `CAUTION / FAIL for economic sufficiency` |
| ADV/spread/queue/fill/executable capacity | `UNKNOWN / BLOCKED` |
| Candidate status or packet membership | `UNCHANGED` |

The artifact strengthens economic caution for H-LIQ-01, H-VOL-01, and
H-EXC-02, especially where Q1 exposure and turnover tails co-occur. It does
not reject C1/C2/C4 economically and does not establish a preferred candidate.
The value/volume fields remain frozen-panel proxies with unresolved unit,
PIT, corporate-action, and execution semantics.

## Reproducibility

- Builder: `research/alpha_capacity_friction_tail_concentration_v1.py`
- Builder SHA-256: `3da49aebb10b86e74856ffb97ecc685036997cd2d642a1d19d66431438d6335a`
- Independent verifier: `research/verify_alpha_capacity_friction_tail_concentration_v1.py`
- Independent verifier SHA-256: `66cd171038873a9bd2af1cf46a17f6daf6d5f4eb2b86595178dc6b9eb0d2c0fc`
- Source artifact SHA-256:
  `0ea19c6de96e368b025ca70f2a7550628b04865d78a8d390d0217afa122b6ea7`
- Inputs: panel `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`,
  features `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`,
  sessions `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`,
  anchors `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`.
- Verification result: `PASS`; all candidate, quartile, concentration,
  turnover, friction, hash, and privacy-scope checks passed.
- Target/privacy firewall SHA-256:
  `63f8f4f3449607ecf64ad881a5d7e3dfec1d9b5de00ad8b838071c60df710cda`;
  result `PASS`.
- Staged JSON:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_capacity_friction_tail_concentration_v1.json`

No target, outcome, provider, cloud, canonical, capture, scheduler, telemetry,
or production state was accessed or modified.
