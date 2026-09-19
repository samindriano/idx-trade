# C3 Capability Denominator and Contract Red-Team Erratum — V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Category: `D / J — financial capability and adversarial review`
Status: `ERRATUM / C3 REMAINS BLOCKED`

## Question

Does the existing C3 financial contract map report coverage against a clearly
defined denominator, and does its `quality_core` capability island already
constitute a separately frozen candidate contract?

This is a read-only, outcome-blind erratum. It does not alter the financial
bundle, create C3A/C3B/C3C, open targets, or change the protected packet.

## Denominator correction

The current map reports coverage against the full frozen eligible panel of
`310,761` rows. That is a useful population-relative rate, but it is not the
same as coverage among financial rows that actually match an eligible panel
key. The financial source has `249,333` matched eligible rows.

| Contract | Final rows | Reported full-panel denominator | Full-panel rate | Matched-source eligible denominator | Matched-source rate |
|---|---:|---:|---:|---:|---:|
| `quality_core` | 64,406 | 310,761 | 20.7253% | 249,333 | 25.8313% |
| `all_five` / fixed C3 | 30,994 | 310,761 | 9.9736% | 249,333 | 12.4308% |

Both denominators are mathematically meaningful, but they answer different
questions. Future reports must label them explicitly; a single unlabeled
“coverage” rate is ambiguous.

## Contract adjudication

The red-team replay confirms the structural quality-core island:

- `70,520` raw finite rows;
- `64,406` final rows after frozen validity/eligibility;
- `525` supported dates;
- `505` dates with at least 30 names;
- all final rows carry `SELECTED` source status in the existing bundle;
- no observed same-bundle or selected-knowledge-time violations in the finite
  provenance-complete subset.

This does not make `quality_core` a candidate. It has no separately frozen
formula, weights, rank direction, novelty decision, or candidate contract. The
existing protected C3 contract still explicitly requires all five fields. Its
status is therefore:

`QUALITY_CORE = STRUCTURAL_CAPABILITY_ISLAND / CONTRACT_NOT_ESTABLISHED / PIT_BLOCKED`

The growth-core and either-YoY variants remain exactly bottlenecked at
`34,412` raw finite rows and `30,994` final rows with `278` usable Top-30 dates.
No YoY rescue is established.

## Population governance remains blocking

- `206,313` rows lack knowledge time, period date, reporting version, and
  attachment lineage;
- `186,764` rows are `NO_FINANCIAL_STATE`;
- `19,549` rows are `UNRESOLVED_PERIOD_BOUNDARY`.

The finite capability island is therefore not population-complete historical
PIT evidence. No fill, forward-fill, fallback provider, sparse-period rescue,
or outcome-driven contract selection is authorized.

## Decision

Preserve the existing C3 result documents for lineage, but use this erratum
for interpretation. Keep fixed C3 `BLOCKED`; do not create a new candidate ID.
A future quality-core candidate would require a predeclared formula/weights,
rank/direction contract, novelty review, independent PIT admission, and a
separately frozen evaluation decision.

## Reproducibility

- Financial bundle SHA-256: `c6004832e651b380161ec216efb2020dddbe86419d89c4521f77aeb09335876b`
- Guarded features SHA-256: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Official sessions SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Existing capability builder: `research/c3_financial_capability_audit_v1.py`
- Existing contract-map builder: `research/c3_financial_contract_map_v1.py`
- Existing contract-map verifier: `research/verify_c3_financial_contract_map_v1.py`
- Relevant source logic: `research/c3_financial_contract_map_v1.py:152`.

No target, outcome, provider, network, cloud, canonical, capture, scheduler,
telemetry, incumbent, or production state was accessed or modified.
