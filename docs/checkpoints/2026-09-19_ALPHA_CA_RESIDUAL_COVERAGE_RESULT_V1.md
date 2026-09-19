# Corporate-Action Residual Coverage Check — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_NARROW_RESIDUAL_COVERAGE / GLOBAL_BASIS_BLOCKED`

## Question

Are the 188 unresolved non-stable price-scale rows already covered by the
retained 1,657-row HLC overlay, or does the earlier HLC PASS leave a separate
unresolved residual population?

This is a read-only, outcome-blind coverage check. It does not infer event
semantics, repair prices, refit/rescore candidates, or establish corporate-
action admission.

## Reproduced evidence

- Residual artifact rows: `188`.
- Residual unique `(ticker,date)` keys: `188`.
- Residual tickers: `19`.
- Retained HLC overlay rows: `1,657`.
- Residual/HLC key overlap: `0 / 188`.
- Every residual key has exactly one active security-master listing interval:
  `188 / 188`.

The narrow result is therefore clear: the residual rows are not merely a
subset of the already-covered HLC overlay. The one-interval security-master
match reduces ticker-interval ambiguity only. The available master contains
`security_id` and ticker listing intervals, but no issuer/ISIN transition chain;
the residual artifact also lacks event-level `event_id`/`ca_type` semantics.

## Disposition

| Question | Result |
|---|---|
| Residual keys unique | `PASS` |
| Residual rows covered by HLC overlay | `FAIL — 0/188` |
| One active listing interval per residual key | `PASS — narrow` |
| Issuer/ISIN transition chain | `UNKNOWN` |
| Event-specific CA semantics | `UNKNOWN` |
| Global price-basis/CA readiness | `FAIL / BLOCKED` |

This sharpens the existing CA risk matrix but does not identify whether the
cause is a corporate action, issuer/security transition, or vendor basis issue.
No further local check is justified without new event-level transition
evidence. Do not treat the residual `idx_*` values as certified corrections.

## Reproducibility and firewall

- Audit script: `research/alpha_ca_residual_coverage_audit_v1.py`; SHA-256
  `401f656ed60ad9cf68abe941ac81f2cf81f8b78385bfd75b4786f839c7bfb6cf`.
- Result JSON SHA-256:
  `1e26231ca4be838fb3adb0caf3d9cbd3e7ede9ee962b472d1cf24384449feb64`.
- Hash-contract output SHA-256:
  `f121444e5484ec4f8bfb66178ab8e1df283c3226012527986a3a1ac957a57ab3`;
  status `PASS`.
- Target/privacy firewall output SHA-256:
  `bb9785acce3def286d6b5a5b6717290fe422496ca7ac520a8089df1078763db5`;
  status `PASS`.
- Residual source SHA-256:
  `eaedba187a3645a83c06c3885dac2c819e818fb68636cfedf2d32e7792432743`.
- HLC overlay source SHA-256:
  `0b372d1925ae8f0a5342e7ed3c3d8b91b77ae547dbc75ad9ed9d8c28fefc5b02`.
- Security master source SHA-256:
  `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`.

No target, provider, cloud, canonical dataset, incumbent, capture, scheduler,
or production artifact was accessed or modified.
