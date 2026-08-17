# Ranking V4 target-support census remediation — result

Date: 2026-08-17 (Asia/Jakarta)
Branch: `research/idx-v4-target-support-census-remediation-v1`
Parent result superseded for decision use:
`research/idx-v4-target-support-census-v1@5f3c2d7b66cf66b2676ba0a409cdc2f4c9ca8f5d`
Status: `V4_TARGET_SUPPORT_6X100_FEASIBLE`

## Boundary and remediation

The prior census was not decision-valid because it omitted the accepted
Yahoo+TradingView Open derivative and relied primarily on the immutable signal
panel Open column. This run uses the unchanged V4-0/V4-1/V4-2 support rules,
but consumes the accepted Open lineage in the correct order:

1. exact one-to-one Yahoo+TradingView derivative identity;
2. verified CA-scale overlay only for derivative rows still missing Open;
3. no synthetic Open, price-ratio factor inference, provider call, or new CA
   acquisition.

The parent tradability-anchor behavior was restored: conflicting exact anchor
states remain `AMBIGUOUS`, not `UNKNOWN`. The focused regression suite proves
this behavior.

This remains outcome-blind. No labels, returns, IC/performance, model fit,
protected outcomes, V4 contract edits, provider calls, or CA acquisition were
performed.

## Pinned inputs

| Input | SHA-256 |
|---|---|
| official sessions | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| signal panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| tradability anchors | `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e` |
| tradability intervals | `fd255f21a3accd763286fbd0b0c6d9d501d618ae611cc0681017e001bdba83cc` |
| official split/reverse actions | `a0ef73a548b3657260b46a0c497e6f87dd9b5138588e23006d4b538677125b35` |
| scope exclusions | `406e224dcd611f3d5a2f9ad8bbd2c03b3c8a0826cc724b01b4618c9b1c1bd938` |
| signal research manifest | `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a` |
| accepted Open derivative | `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab` |
| Open derivative manifest | `1a6bcc9c7fbbd967cdc69f8876fe1d4aa94b46c0e466469a9643da59251deb14` |
| CA overlay parquet | `2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41` |
| CA overlay manifest | `dfb7219bddec77ced3e3aadfaa2d85d04c19e1d9fd9a8af1badba523ecf91977` |

The exact manifest-pinned signal-contract path remains unavailable. It is
recorded as a provenance warning; no alternate copy was substituted.

## Open lineage result

| Source | Rows |
|---|---:|
| derivative rows | 981,940 |
| derivative Open support | 938,139 |
| CA overlay rows | 2,184 |
| overlay rows overlapping derivative support | 0 |
| incremental overlay Open support | 2,184 |
| final Open support | 940,323 |

Final Open support is 95.6413% of the 981,940-row decision population. The
canonical signal panel was not rewritten.

## Target and continuity support

| Quantity | Supported rows | Rate |
|---|---:|---:|
| immutable-panel Open(t+1) | 529,850 | 53.9595% |
| derivative Open(t+1) | 925,512 | 94.2534% |
| final Open(t+1) | 927,690 | 94.4752% |
| H5 Close | 961,366 | 97.9048% |
| H10 Close | 954,379 | 97.1932% |
| H5 target | 913,621 | 93.0424% |
| H10 target | 906,377 | 92.3047% |
| both targets | 899,739 | 91.6287% |
| H5 CA continuity | 953,151 | 97.0682% |
| H10 CA continuity | 945,757 | 96.3152% |
| both-horizon CA continuity | 938,553 | 95.5815% |

Future mechanism/state counts are unchanged by Open-source selection:

- Entry: ACTIVE 968,095; NO_TRADE 13,015; SUSPENDED 0; UNKNOWN 0;
  AMBIGUOUS 0; NO_FUTURE_SESSION 830.
- H5: ACTIVE 961,366; NO_TRADE 16,401; SUSPENDED 0; UNKNOWN 5;
  AMBIGUOUS 0; NO_FUTURE_SESSION 4,168.
- H10: ACTIVE 954,379; NO_TRADE 19,196; SUSPENDED 0; UNKNOWN 15;
  AMBIGUOUS 0; NO_FUTURE_SESSION 8,350.

The zero future-leg `SUSPENDED` count is only for this active-panel
population; it is not a claim that the interval artifact has no suspensions.

## Eligible session identities and 6×100 feasibility

The locked ≥90% per-date gates produce:

| Identity list | Eligible sessions | SHA-256 |
|---|---:|---|
| H5 | 910 | `a58b0ef0f6562ad417d0f8c2dce24b811eee865bc82706499cceb7d51cea6d1d` |
| H10 | 891 | `37b44ffbec99c7fd1e3024c8447ab0128177ce73a0149f85af7cd85db1baf634` |
| Consensus | 815 | `7336454fed8aaefffbc92cfae5860a1486c11a9235820894eb896bf4f82312ee` |

Each list contains at least 600 ordered eligible signal sessions, so the
technical six-fold/100-session requirement is feasible for H5, H10, and the
consensus. Calendar adjacency is diagnostic only; V4-2's consecutive eligible
session rule is evaluated on the filtered ordered identity lists. Whether the
eventual V4-3 preregistration uses one shared list or separate H5/H10 lists
remains explicitly unchosen and outcome-blind.

The full 1,260-session identity artifact is
`v4_session_identities_1260.csv`, SHA-256
`c5a0d03b17234cc657bd472f23c3fbaf66698883768493641ee30021f97f2ae0`.

## Verdict

**`V4_TARGET_SUPPORT_6X100_FEASIBLE`**.

This is a data-support feasibility result only. It authorizes no target
materialization, model fitting, performance evaluation, fold selection beyond
the frozen pre-outcome rules, or fresh-forward access. The missing pinned
signal-contract file remains a provenance warning that must be resolved before
claiming fully reproducible downstream execution.

## External artifacts

Root:
`D:\Documents\Project\idx-v4-target-support-census-remediation-20260817-v1`

| Artifact | SHA-256 |
|---|---|
| `v4_target_support_per_date.csv` | `3ac18580c48bcb904c0109c60c796ebb1ed001ab6a3b1134f81d295ec03495a7` |
| `v4_session_identities_1260.csv` | `c5a0d03b17234cc657bd472f23c3fbaf66698883768493641ee30021f97f2ae0` |
| `v4_eligible_h5_sessions.csv` | `a58b0ef0f6562ad417d0f8c2dce24b811eee865bc82706499cceb7d51cea6d1d` |
| `v4_eligible_h10_sessions.csv` | `37b44ffbec99c7fd1e3024c8447ab0128177ce73a0149f85af7cd85db1baf634` |
| `v4_eligible_consensus_sessions.csv` | `7336454fed8aaefffbc92cfae5860a1486c11a9235820894eb896bf4f82312ee` |
| `census_summary.json` | `c67e3d904d6a2c7c072135609c8a4ff7cabc5214012368e4ad386c57f87722e9` |
| `manifest.json` | `4a08c745b4d32b6a2b3d65d444de92dc226048a2d9647e7b07626781dc772249` |

## Validation

- Focused tests: `3 passed`.
- Full pytest: `41 passed, 1 failed`; sole failure is the unrelated existing
  storage expectation `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`.
- `py_compile`: PASS.
- No source/provider/outcome/model artifacts were modified.
