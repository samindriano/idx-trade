# H-LIQ-01 Novelty No-Retry Adjudication — 2026-09-20

## Scope

This is an independent read-only adversarial review performed by a Luna XHigh
worker in the isolated alpha lane. It used only existing H-LIQ artifacts and
checkpoint evidence. No code or data was modified; no provider, target,
forward-return, incumbent-predictive, canonical, capture, cloud, telemetry, or
production state was accessed.

## Verdict

| Question | Verdict |
|---|---|
| Artifact/firewall integrity | `PASS` |
| Unqualified temporal persistence | `FAIL` |
| Mechanism-level novelty | `UNKNOWN` |
| Economic worth/capacity | `FAIL / UNKNOWN` |
| Same-surface H-LIQ retry | `NO-GO` |
| C5 creation or packet expansion | `NO` |

The review found that the apparent residual novelty is not independent enough
to justify another experiment on the same surface. The source-decomposition
residual is constructed by same-date OLS residualization of H-LIQ rank on C2
turnover-level rank (`research/alpha_hliq01_source_decomposition_v1.py`,
lines 127–149). Therefore, its low dependence on the removed component is not
evidence of a new economic mechanism.

The existing residual artifact still has `0.0843185` mean Spearman dependence
with full C2 and worsens selected bottom-value exposure from `39.6722%` to
`50.3889%`. The temporal red-team reports Q4 H-LIQ/C2 dependence varying from
`0.0762` to `0.3053` across six blocks, with bottom-value Q1 share varying from
`29.47%` to `51.30%`.

## Evidence

- `2026-09-19_ALPHA_HLIQ01_SOURCE_DECOMPOSITION_RESULT_V1.md`
- `2026-09-19_ALPHA_HLIQ01_TEMPORAL_PERSISTENCE_REDTEAM_RESULT_V1.md`
- Existing source decomposition JSON SHA-256:
  `352a422086d540318f0464aaec2b80b3eb427a87176caa0326559242dacfc35e`
- Existing independent verification JSON SHA-256:
  `0919c0df9f04d67fdc37e40a3d4a59aa1501478fab5f7a3c2399eba3c3f52d60`

## Disposition and next legal trigger

H-LIQ-01 remains `FUTURE_RESEARCH / NOVELTY_PENDING /
ECONOMIC_CAUTION`, with no C5 ID and no protected-packet change. Do not repeat
the same C2-level residualization, size-neutralization, or temporal-persistence
question without either:

1. a genuinely new preregistered mechanism; or
2. an independently admissible liquidity/PIT/identity/capacity source
   contract.

This is a no-retry decision for the current evidence, not a claim that H-LIQ
can never be useful.
