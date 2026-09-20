# IDX-Trade Population Identity/Lifecycle Authority — Result V1

Date: 2026-09-20  
Branch: `codex/idx-population-identity-lifecycle-20260920`  
Status: `SUPPORTED_OBSERVED_UNION_NO_COMPLETENESS_ADMISSION`

## Result

The isolated crosswalk enumerated 1,176 normalized codes observed anywhere in
the retained research/source corpus. This is an observed research population
superset, not a complete historical IDX denominator.

The clean panel has 945 codes. Official trading has 983 codes, including 44
codes absent from the panel; the historical anchor has 980 codes, including 35
codes absent from the panel. CNTX and CNTB are included in the trading-only
counterexample set. The prior 981,940-key exact replay therefore remains a
key-reconciliation result and cannot prove population completeness or
survivorship safety.

The official delisting archive contributes 159 unique codes, 115 of which are
present only in that retained source family. The public IPO cross-check has
three valid ticker codes that remain source-only after field normalization and
five hyphenated canceled-offering identifiers retained separately. They remain
cross-check evidence, not automatically valid security records.

## KSEI result

All 984 codes in the retained KSEI current registered-share table were attempted
once through the ordinary public detail route. The retained outcomes are:

- 371 internally valid detail pages with matching code, valid ISIN, security
  name, issuer, and type;
- 2 HTTP-200 pages that were empty or mismatched;
- 611 HTTP-500 pages.

The latter two groups are unresolved access/parse outcomes and are not negative
identity evidence. Current KSEI evidence is bounded identity/series evidence,
not historical PIT membership or a complete historical security population.

## Lifecycle and graph

There are 1,112 codes with retained interval or issued-history evidence. The
six retained lifecycle conflict codes are `BUKK`, `INRU`, `ITMA`, `KIAS`,
`SKBM`, and `UNTX`. The graph preserves ticker, security, issuer-name, ISIN,
and lifecycle-event distinctions with edge-level provenance. It does not choose
a winner across conflicting intervals.

No observed code has proven PIT effective/knowledge time. Legal issuer
continuity, ticker reuse, relisting/rename semantics, share-series continuity,
revision/vintage semantics, and exchange-effective corporate-action basis remain
unknown. Predictive research admission remains closed.

The final counterexample search found two profile-name collision groups
(`APAI`/`APIA`, `PIGN`/`PIKI`) and one KSEI issuer-string group mapping `GOTO`
and `GOTOM` to distinct ISIN/security records. The retained corporate-action
probe covers BPII/PBID/RMKE with eight document-evidence records, but no retained
document states an exchange-effective first session or price basis. These
findings strengthen the no-collapse boundary and do not establish legal
continuity, ticker reuse, PIT time, or effective CA authority.

The six conflict codes are heterogeneous: BUKK/INRU have profile, current/
delisting, and issued-history evidence but KSEI HTTP failures; ITMA/KIAS/SKBM
have valid KSEI detail; UNTX is delisting-only in the retained surfaces. The
bounded announcement inventory has only two exact SKBM hits, both subsidiary-name
notices. No exact hit is interpreted negatively, and no lifecycle winner is
selected.

The 115-code official-delisting-only residual also has zero exact matches in
the retained announcement-search files. This is query-bounded no-hit evidence,
not proof of no announcement, relisting, issuer continuity, or effective event.

Final counts are: 1,176 observed codes; 984 KSEI attempts; 371 KSEI/ISIN
resolutions; 1,044 issuer-name evidence codes; zero legal issuer-continuity
proofs; 1,112 interval/event-bearing codes; zero lifecycle-proven codes;
962 current/active listing codes; 159 delisting-record codes; and zero proven
relistings. Relative to the 945-code panel, the crosswalk adds 231 observed
codes; relative to the 979-code security master, 197; relative to the 980-code
anchor, 196. These are coverage deltas, not admission authority.

Fail-closed authority counts are: `IDENTITY_PROVEN` 0,
`IDENTITY_BOUNDED` 1,043, `LIFECYCLE_PROVEN` 0,
`LIFECYCLE_PARTIAL` 1,106, `LIFECYCLE_CONFLICTING` 6,
`PIT_EFFECTIVE_DATE_PROVEN` 0, `PIT_EFFECTIVE_DATE_UNKNOWN` 1,176, and
`POPULATION_COMPLETE` 0. The historical population remains
`POPULATION_UNKNOWN`; it is not relabeled incomplete merely because omissions
from the panel and current master were found.

## Verification

Focused tests: `11 passed`. Parser compilation: PASS. No protected outcomes,
canonical data, production/cloud/capture/telemetry/provider/scheduler state, or
incumbent research state was accessed or mutated.

Machine artifacts and exact hashes are maintained in
`research_knowledge/identity_lifecycle_master_dossier_v1.md` and
`research_knowledge/identity_lifecycle_population_crosswalk_v1.json`.
