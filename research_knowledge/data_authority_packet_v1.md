# IDX-Trade data-authority and admission packet V1

## Verdict

`ELIGIBILITY_POLICY_AUTHORITY_MISSING` and `POPULATION_AUTHORITY_UNKNOWN`.
The package is outcome-blind and structurally reproducible, but it is blocked
for predictive re-entry. No protected target, forward outcome, incumbent
result, provider, cloud, or canonical production state was accessed or changed.

The packet was created against branch `codex/alpha-available-data-20260919`
and source packet-head `855bb153cd7a5a4a7b862cd6986a81556eb0020e`. Later
documentation and tooling commits may advance the checkout; revalidate the
hash-bound packet, evidence refs, and lane state after any commit.

## Authority and exact meanings

The frozen protocol prose states a trailing-60 official-session liquidity rule
with at least 20 finite observations. The Stage-A implementation uses
`min_periods=window` for both rolling count and median, so its effective rule
is 60/60. The chronology is explicit: protocol freeze `a02a1547`, implementation
`1ebced27`, and the later resolution packet `e446c1e8`; none is an owner-issued
binding that selects one interpretation. Therefore the packet records both
interpretations and selects neither.

This is separate from security-date eligibility, listing-age warm-up, feature
warm-up, and rolling-estimator availability. The generic security path exposes
`minimum_warmup_sessions=60`/`IPO_WARMUP`; that does not resolve the liquidity
policy conflict. Candidate finiteness and candidate support are also measured
separately from population eligibility.

## Structural counterfactual

The outcome-blind replay in `eligibility_policy_scenario_v1.json` evaluates both
rules on the frozen panel, financial bundle, official-session calendar, and
regular-ACTIVE tradability anchors. It does not admit either branch.

| Interpretation | Eligible rows | Tickers | Dates |
|---|---:|---:|---:|
| minimum-20 | 348,765 | 740 | 1,241 |
| min-periods-60 | 310,761 | 711 | 1,201 |
| mask difference | 38,004 | 619 affected | 1,241 affected |

The mask difference is not interpreted as new listings, delistings, ticker
reuse, or survivorship evidence. Listing-age distribution, delisting
completeness, and PIT-safe sector composition are unavailable.

On common finite rows, rank changes are C1 `73.1086%`, C2 `0%`, C3
`96.6122%`, and C4 `99.5192%`. C2 is unchanged because its feature warm-up
still requires 60 observations; this supports the taxonomy distinction but
does not select a policy. The 600-session structural Top-30 summaries and
native/common support counts are retained as diagnostics only.

The same replay measures native support and frozen Top-30 geometry. The
coverage denominator is each policy's eligible row count; Top-30 overlap and
turnover are consecutive official-session set diagnostics.

| Candidate | Min-20 finite rows / coverage | Min-60 finite rows / coverage | Top-30 overlap 20 / 60 | Top-30 turnover 20 / 60 |
|---|---:|---:|---:|---:|
| C1 | 304,808 / 87.3964% | 295,243 / 95.0065% | 0.5831 / 0.5825 | 0.4169 / 0.4175 |
| C2 | 310,761 / 89.1033% | 310,761 / 100.0000% | 0.6737 / 0.6737 | 0.3263 / 0.3263 |
| C3 | 34,412 / 9.8668% | 30,994 / 9.9736% | 0.8913 / 0.8900 | 0.1087 / 0.1100 |
| C4 | 340,917 / 97.7498% | 310,323 / 99.8591% | 0.7630 / 0.7673 | 0.2370 / 0.2327 |

These are structural rank-denominator and selection-set diagnostics, not
performance, outcome, or economic evidence. Rank denominators, finite dates,
and tickers are preserved in the full staging result referenced by the compact
summary.

## Candidate-specific authority and bounded eras

The follow-up era map uses natural calendar years, not result-optimized
subsets. C1/C2/C4 have broad finite structural support from 2022 onward. C3
has zero finite rows through 2024, begins on 2025-04-25, and remains partial
through 2026-07-17. No era is admitted.

Every observed panel key is an ACTIVE tradability-anchor key and none is a
NO_TRADE key. However, the anchor table contains 458 ACTIVE rows absent from
the panel in 2021-2024. This is evidence of structural overlap and panel
coverage, not proof of a complete historical population.

The dependency split is candidate-specific: C1/C4 directly require price and
corporate-action basis authority; C2 additionally requires volume/liquidity
semantics and capacity; C3 directly requires financial publication timing,
revision, and provenance authority, while still inheriting the upstream
liquidity mask. This narrows future admission work but changes no candidate
status and does not replace population or policy authority.

## Population, identity, corporate actions, and financial PIT

The available regular-ACTIVE anchors provide bounded structural masks, not a
population-complete daily PIT universe. Delisted/relisted membership,
ticker-reuse, issuer/ISIN continuity, and survivorship authority remain
unknown. Ticker identity, security identity, and issuer identity are not
interchangeable.

The official IDX current company-profile directory is a separately bounded
current snapshot: 962 unique codes, exact agreement with the prior official
current snapshot by code and listing date, and a subset relation to the anchor.
It supports current-directory identity cross-checks only; it does not supply
historical daily membership, issuer/ISIN transitions, publication time,
revision/vintage semantics, or corporate-action basis.

Corporate-action and price-basis lineage is not event-complete at the
event-to-window level. No split, rights, bonus, conversion, or adjustment is
inferred from dates, ratios, price movement, or missing rows. Price candidates
therefore remain structurally reproducible but not predictive-admissible.

C3 has finite structural rows, but financial publication/available-at,
revision/vintage, issuer mapping, YoY history, and common-support authority
are incomplete. Dropping YoY or silently using a larger quality-only subset
would be a different candidate and is not allowed.

Liquidity, volume, and exception evidence are similarly bounded: current
structural fields do not establish historical PIT ADV, spread, queue, fill,
or executable capacity. Proxy economics remain proxy-only.

## Candidate and support matrix

| Candidate | Structural state | Predictive re-entry | Blocking authority |
|---|---|---|---|
| C1 | `STRUCTURALLY_ADMISSIBLE` | `BLOCKED` | population, identity, CA/basis, PIT and capacity |
| C2 | `STRUCTURALLY_ADMISSIBLE` | `BLOCKED` | population, historical liquidity, PIT and capacity |
| C3 | `BLOCKED` | `BLOCKED` | sparse all-five/YoY PIT support, revision, identity, common support |
| C4 | `STRUCTURALLY_ADMISSIBLE` | `BLOCKED` | population, identity, CA/basis, PIT and capacity |
| H-LIQ | `BLOCKED` | `BLOCKED` | same-surface dependence, basis, capacity |
| H-VOL | `BLOCKED` | `BLOCKED` | horizon and price-basis stability |
| H-EXC | `BLOCKED` | `BLOCKED` | H-EXC-01 not applicable; H-EXC-02 remains future research |

The current native rows are C1 `295,243`, C2 `310,761`, C3 `30,994`, and C4
`310,323`. Exact all-four common support is `30,861` rows (`9.9308%` of the
current eligible mask), with 277 dates meeting at least 30 names and a maximum
of 175. This is a methodology result under the current non-authoritative mask,
not a final admission population.

## Verifier and firewall audit

The durable packet allowlist passes with policy unset, re-entry closed, a
candidate allowlist of C1-C4/H-LIQ/H-VOL/H-EXC, and relative evidence paths.
The synthetic mutation suite records 13/13 expected assertions: corrupt code,
input, and manifest hashes fail; candidate injection, policy selection, and
re-entry opening fail; obvious forbidden tokens, network imports, and true
access markers fail.

The current firewall is a hybrid required-path/hash plus denylist/token scan,
not a semantic schema allowlist. Synthetic disguised fields and unexpected
non-denylisted schema columns pass, and are recorded as known gaps. The hash
contract also does not independently recompute producer formulas. These are
blocking limitations, not reasons to broaden access.

## Remaining decisions and re-entry gate

Before any protected access, an owner must bind the exact eligibility rule,
count/median/finite treatment, official calendar, population/PIT universe,
identity and CA basis, financial publication/revision semantics, candidate
support and tie handling, target semantics, execution lag, evaluation dates,
Top-K/turnover/friction, multiple-testing, and promotion/failure criteria.
Then the admitted structural artifacts must be regenerated in isolation,
hash-bound, and reverified. No candidate is `READY_FOR_REENTRY_PACKET` here;
the protected boundary remains closed.

## Durable evidence

- Machine packet: `research_knowledge/data_authority_packet_v1.json`
- Counterfactual: `research_knowledge/eligibility_policy_scenario_v1.json`
- Verifier audit: `research_knowledge/verifier_mutation_audit_v1.json`
- Firewall audit: `research_knowledge/firewall_mutation_audit_v1.json`
- Reproduction record: `research_knowledge/reproducibility.md`
- Candidate-era map: `research_knowledge/candidate_era_authority_v1.json`
- Eligibility delta by era: `research_knowledge/eligibility_era_delta_v1.json`
- Candidate-era mechanics: `research_knowledge/candidate_era_mechanics_v1.json`
- Official current-directory audit: `research_knowledge/official_idx_directory_audit_v1.json`
- Official current-directory checkpoint: `docs/checkpoints/2026-09-20_ALPHA_OFFICIAL_IDX_DIRECTORY_AUDIT_RESULT_V1.md`
