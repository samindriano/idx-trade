# Financial PIT Feature Materialization V1

**Status:** `REVIEW`

**Decision:** `FINANCIAL_PIT_FEATURE_PANEL_V1_MATERIALIZED_PIT_SAFE_REVIEW`

## Scope and boundaries

This lane materialized the accepted 13-feature Financial PIT contract using
only the immutable offline fact corpus and its manifest-pinned period-boundary
sidecar. The model-safe scope is exactly `GENERAL + CONSOLIDATED`.

The seven fact rows whose exact instant/duration boundary remains unresolved
were retained in the source audit but excluded fail-closed from feature values.
They did not block valid rows. No annualization, TTM, interpolation,
zero-fill, carry-forward across unresolved states, fuzzy fact mapping,
performance selection, provider call, redownload, model fitting, protected
outcome access, or O2 change occurred.

The output is a sparse change-point as-of panel. Each row is emitted at an
exact UTC filing knowledge timestamp observed in the source corpus; no
publication timestamp or daily decision date is invented. The panel is long
by feature and reporting period so Q1/H1/9M/FY cumulative values remain
explicitly stratified for downstream as-of joining.

## Pinned inputs

| Artifact | SHA-256 |
|---|---|
| `fact_records.jsonl` | `3cba29b53a8f3d68bae016adf59ffe3edb385c690b44d843a1790227b4152575` |
| `filing_diagnostics.jsonl` | `a0a47d4fcfc58518ae97149722f4fb44c96b8c9430b51f1e9199bc09926fb5f4` |
| accepted census `MANIFEST.json` | `95db03c431dadb5a0af749fd63687f39c8a68d450d7dee17c4c5c53c5bf73d7b` |
| `period_boundaries.jsonl` | `f29f50b86100c23c5407325f02d6f42e8d7d03dc9d5779c5da1d2763c20a4168` |
| period-boundary `MANIFEST.json` | `798bba02b8b37c06e2a6e7bd133103df00fbfcccebb2612b9d47facf11e97b49` |

Source roots remain external:

* `D:\Documents\Project\idx-financial-pit-scientific-notation-remediation-census-20260813-v3`
* `D:\Documents\Project\idx-financial-pit-period-boundary-20260814-v3`

## Implementation

`src/idx_trade/financial_feature_panel.py` adds deterministic offline
materialization around the accepted `financial_feature_contract.py` resolver.
For every sparse as-of state it:

1. selects only filing versions with `knowledge_at <= as_of_timestamp_utc`;
2. selects the latest version per issuer/fiscal-period/scope key at that
   timestamp, with same-time hash conflicts failing closed;
3. resolves only `GENERAL + CONSOLIDATED` versions;
4. calculates exactly the 13 frozen candidate features when the existing
   availability contract returns `AVAILABLE`;
5. retains explicit status/reason for missing, unresolved, non-comparable,
   unit-mismatch, and denominator-invalid rows;
6. stores reporting and input version IDs, attachment hashes, publication and
   knowledge timestamps, exact boundaries/evidence locations, fact identities,
   source refs/locations, and contract version in the panel/provenance output.

Duration-sensitive values are never pooled across Q1/H1/9M/FY. The output
does not turn a sparse state timeline into a fabricated daily panel; a later
consumer must perform its own preregistered as-of join against the clean
historical equity panel.

## Certified external output

The final deterministic output is:

`D:\Documents\Project\idx-financial-pit-feature-materialization-20260814-v1-cert-a`

The independent rerun is `...-cert-b`. Both output directories have identical
artifact hashes and manifest hash.

| Artifact | SHA-256 |
|---|---|
| `feature_panel.parquet` | `1d60ee69070546d21040af8c61f2170c5cca2254f131626a19bf4c1d59f3f023` |
| `feature_provenance.jsonl` | `c92a58ffcb4e3a9be38482a3edd03e6bb74919f39ccea3a61a5c9763466d1d3a` |
| `audit.json` | `95d1b0a74388c07dbb9ad3a550a1a7d3c6748a670fcfbec4093eb359ad584c35` |
| `decision_timestamps.jsonl` | `52c34642c82c9a0fcf9a2e2e8d48a7e15dc012ad01153f1ae0cfefdc5687c80f` |
| `revision_transitions.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `MANIFEST.json` | `639fc6e6fe3f7f853d23b6f5244c98ec8ed5c63b219aa59e698c8db908fb2140` |

## Materialization audit

| Measure | Result |
|---|---:|
| feature-state rows | `258,401` |
| unique issuer × decision-date keys | `4,221` |
| unique issuer × exact as-of timestamp keys | `4,226` |
| issuers | `531` |
| sparse decision dates | `478` |
| available feature values | `150,407` |
| unresolved period-boundary rows excluded | `7` |
| knowledge-time violations | `0` |
| period-strata consistency | `PASS` |
| reporting provenance completeness | `100%` |
| available-feature provenance completeness | `100%` |
| observed revision transitions in GENERAL + CONSOLIDATED corpus | `0` |

The full feature/status/date/year/period audit is in `audit.json`. The 13
available counts are:

| Feature | Available |
|---|---:|
| `size_log_total_assets` | `15,266` |
| `size_log_revenue` | `15,207` |
| `leverage_liabilities_to_assets` | `15,266` |
| `capital_equity_to_assets` | `15,266` |
| `liquidity_cash_to_assets` | `15,266` |
| `profitability_net_income_to_assets` | `15,266` |
| `profitability_attributable_income_to_equity` | `14,668` |
| `cash_flow_ocf_to_net_income` | `6,678` |
| `cash_flow_ocf_to_revenue` | `9,136` |
| `margin_net_income_to_revenue` | `15,207` |
| `yoy_revenue` | `4,766` |
| `yoy_net_income` | `3,616` |
| `yoy_total_assets` | `4,799` |

Missing, unresolved, unit-mismatch, and denominator-nonpositive states remain
separately represented in the audit and are not converted to values.

## Validation and readiness boundary

Focused feature-panel, feature-contract, and period-boundary tests:
`18 passed`.

Full repository pytest: `550 passed, 0 failed, 3 warnings`.

The two independent offline materializations produced byte-identical hashes
for all five core artifacts and `MANIFEST.json`. This establishes technical
and PIT-semantic readiness for a separately preregistered feature/model
experiment review. It does **not** authorize feature selection by outcome,
model fitting, protected-outcome access, O2 changes, or any forward vault
operation.
