# IDX-Trade Population Identity and Lifecycle Authority Dossier V1

Date: 2026-09-20  
Lane: `codex/idx-population-identity-lifecycle-20260920`  
Scope: outcome-blind population, identity, lifecycle, PIT, and research-admission authority.

## Executive result

The retained corpus now has an explicit observed research-population union of
1,176 normalized codes across panel, anchors, official IDX trading, reports,
financial bundle, foreign flow, profiles, issued history, listings/delistings,
sector, KSEI, and public cross-check surfaces. This is a source union, not a
complete historical IDX denominator.

The strongest new security-level surface is the KSEI current registered-share
table: 984 codes. One ordinary public attempt was retained for every code. Of
those attempts, 371 pages were internally valid detail records with matching
code, valid Indonesian ISIN, security name, issuer, and type; 2 returned HTTP
200 but were empty or mismatched; and 611 returned HTTP 500. The latter two
classes are unresolved access/parse outcomes, not evidence that the securities
do not exist. The KSEI table and detail pages are current-surface evidence, not
historical daily PIT membership or issuer-continuity authority.

The population challenge is confirmed at scale. The panel has 945 codes, while
official trading has 983 codes and 44 official-trading-only codes, including
CNTX and CNTB. The historical anchor has 980 codes and 35 anchor-only codes
relative to the panel. Therefore panel replay completeness is a property of the
observed panel keys; it is not historical population completeness or
survivorship safety. The prior 981,940-key zero-mismatch result must remain a
key-reconciliation result only.

## Authority classifications

| Surface | Classification | What is supported | What remains unknown |
|---|---|---|---|
| Observed source union | `POPULATION_UNKNOWN` | Exact retained union and set differences | Historical denominator, omitted nodes, temporal scope |
| Current code/security mapping | `IDENTITY_BOUNDED` | Current profile/master/KSEI code-level evidence for bounded subsets | Legal issuer continuity, ticker reuse, share-series continuity |
| KSEI detail identity | `IDENTITY_BOUNDED` | 371 internally valid current detail pages with code/ISIN/issuer/type | Historical identity, publication vintage, complete KSEI historical coverage |
| Lifecycle | `LIFECYCLE_PARTIAL` | 1,112 codes have retained interval/event observations; 6 codes retain explicit conflict rows | Relisting/rename semantics, effective sessions, issuer/security continuity |
| PIT effective date | `PIT_EFFECTIVE_DATE_UNKNOWN` | No source binds all observed rows to researcher-available membership time | Daily eligible population, knowledge time, revisions |
| Legal issuer continuity | `UNKNOWN` | Names and issuer strings can be crosswalked | Legal-entity continuity through mergers/restructures |
| Corporate-action identity/basis | `UNKNOWN` | Event/announcement discovery exists in prior lanes | Exchange-effective first session, price basis, security-level linkage |
| Research admission | `BLOCKED` | Evidence-only structural artifacts | No candidate admission follows from this lane |

## Source census

The machine-readable packet contains exact code lists and pairwise set
differences. Counts are:

| Source family | Codes |
|---|---:|
| Clean OHLCV panel | 945 |
| Historical anchor | 980 |
| Official trading history | 983 |
| Official profiles | 1,043 |
| Official issued history | 971 |
| Official current listings / active listings | 962 / 962 |
| Official delisting records | 159 unique codes / 163 rows |
| Annual + quarterly report indexes | 1,009 code union / 5,870 annual rows / 9,971 quarterly rows |
| Financial bundle | 729 |
| Foreign flow | 983 |
| Sector constituents | 837 |
| KSEI current registered-share table | 984 |
| Official corporate-action document probe | 3 codes / 8 document-evidence records |
| Public dataset cross-checks | 958 and 983 |
| Observed union | **1,176** |

Key exact counterexample sets include:

- official trading minus panel: 44 codes;
- historical anchor minus panel: 35 codes;
- KSEI share table minus panel: 44 codes;
- profile-file union minus panel: 104 codes;
- observed union minus security master: 197 codes;
- observed union minus profile-file union: 133 codes.
- official delisting-only source membership: 115 codes;
- those 115 codes account for 117 retained rows with delisting dates from
  1993-05-05 through 2019-11-11, confirming a historical-only delisted class;
- public IPO-only cross-check membership: 3 valid ticker codes (cross-check
  evidence, not automatically valid security records);
- five nonstandard canceled-offering identifiers (`AKSL-C1`, `BITU-C1`,
  `BSMT-C1`, `CABR-C1`, `ZEUS-C1`) retained outside the normalized union.

The exact lists are in `identity_lifecycle_population_crosswalk_v1.json`.

## KSEI acquisition and interpretation

The isolated acquisition attempted each of the 984 codes once using the
ordinary public KSEI registered-share detail route. It retained URL, retrieval
timestamp, HTTP status, byte count, raw path, and SHA-256 in the external
staging root. The raw response set is therefore auditable, including failures.

`DETAIL_VALID` means the retained 200 page has a matching requested short code,
an `ID...` ISIN, non-empty security name, issuer, and security type. It does not
mean historical PIT identity. `HTTP_200_EMPTY_OR_MISMATCH` means a successful
transport response did not satisfy the detail contract. `HTTP_NON_200` means
the source did not provide a usable detail response; it is not a negative
security lookup.

The source is consequently useful for bounded current identity and series/type
discovery, but not for asserting that the 984-code share table is the complete
historical equity population or that absent/failed pages are absent securities.

## Lifecycle and identity graph

The crosswalk preserves current listing rows, delisting rows, security-master
interval rows, and issued-history events independently. It does not silently
merge intervals or choose a winner. The retained conflict set is:
`BUKK`, `INRU`, `ITMA`, `KIAS`, `SKBM`, and `UNTX`.

The graph contains typed ticker, security, ISIN, issuer-name, and lifecycle
event nodes with edge-level source provenance. Current graph counts are 1,176
ticker nodes, 371 ISIN nodes, 1,383 issuer-name nodes, 3,667 lifecycle-event
nodes, and 6,775 edges. All identity edges are `SUPPORTED_BOUNDED`, not
`PROVEN`; interval conflicts remain `CONFLICTING`; global historical
population completeness and PIT effective time remain `UNKNOWN`.

Issuer names are not legal-entity identity. A code may have a profile/master
name and still lack issuer continuity, ticker-reuse, or share-series authority.
Likewise, an observed lifecycle event is not automatically a listed interval
or an exchange-effective trading transition.

The final collision census preserves two current profile-name groups mapped to
multiple codes (`APAI`/`APIA` and `PIGN`/`PIKI`) and one valid KSEI issuer-string
group mapping `GOTO` and `GOTOM` to distinct ISIN/security records. These are
counterexamples to name-as-security-key collapse, not proof of legal continuity
or historical ticker reuse. The one-detail-per-code KSEI contract cannot test
multiple-ISIN-per-code history.

The retained corporate-action document probe covers `BPII`, `PBID`, and `RMKE`
with eight document-evidence records. Plan, approval, advertisement, correction,
and underlying-event semantics are preserved; no retained document states an
exchange-effective first session or price basis. Document/event dates therefore
remain anatomy evidence, not effective-transition authority.

The named conflict audit shows that the six conflict codes are heterogeneous:
`BUKK` and `INRU` have current profiles, current/delisting intervals, and
issued-history evidence but KSEI HTTP failures; `ITMA`, `KIAS`, and `SKBM` have
valid KSEI detail/ISIN records; `UNTX` is delisting-only in the retained
surfaces. The bounded announcement inventory has only two exact `SKBM` hits,
both subsidiary-name notices. No exact hit is a negative event result, and no
interval or event is selected as the historical winner.

The 115-code official-delisting-only class has zero exact code hits in the
retained announcement-search files. This is bounded query coverage, not proof
of no announcement, no relisting, no issuer continuity, or no effective event;
the result is retained as an explicit no-hit-not-negative residual.

## Residuals and high-value consequences

All 1,176 observed codes remain PIT-effective-date unknown. The residual packet
retains per-code source membership, fields observed, source families examined,
missing authorities, and lifecycle records. The key residual counts are:

- 802 codes have no valid KSEI detail record in this acquisition;
- 6 codes have explicit retained lifecycle conflicts;
- 368 codes have no valid KSEI detail but do have other bounded identity/lifecycle
  evidence, leaving a PIT/identity residual rather than a population-negative;
- 133 observed codes are outside the retained profile-file union;
- 197 observed codes are outside the retained 979-code security master.

The final counterexample search is complete for the retained source families:
it found explicit issuer/name and issuer-string multi-security mappings, while
historical ticker reuse, relisting/rename identity, multiple-ISIN-per-code
history, and issuer legal continuity remain unresolved rather than silently
collapsed.

CNTX/CNTB remain the concrete regression class: code presence in trading or
anchors can coexist with panel absence and KSEI current-table absence. This is
whole-security population evidence, not a repair instruction.

## What this disproves or narrows

1. Panel absence cannot be interpreted as historical security absence.
2. Exact panel/trading key agreement cannot establish population completeness.
3. KSEI current-table membership cannot be treated as historical PIT membership.
4. An HTTP failure or empty KSEI detail page cannot be treated as a negative
   identity result.
5. Current profile names and listing dates do not prove issuer continuity,
   ticker reuse, relisting, or daily eligibility.
6. Event/interval rows cannot be collapsed into a single lifecycle winner when
   sources disagree.

## What remains uncertain

The decisive unresolved authorities are a population-wide versioned security
master with issuer/ISIN/series continuity, daily PIT membership and knowledge
time, revision/vintage semantics, exchange-effective lifecycle transitions,
corporate-action basis linkage, and an explicit candidate-specific admission
contract. Free/public snapshots can improve bounded cases but cannot supply
these global guarantees by themselves.

## No-retry and reopening rules

Do not repeat the same KSEI page attempts merely to convert HTTP 500 into a
count. Reopen that question only with a new stable public endpoint/response
contract, a bounded backoff/access authorization, or a different authoritative
source class. Do not turn public mirrors into canonical identity authority.

The missing population denominator should not be attacked with more panel
replay. Reopen with a source that explicitly enumerates historical membership,
or with a new independently versioned security/issuer/ISIN lifecycle dataset.

Issuer/OJK/archive research remains worthwhile only for a named residual class
where it can establish a typed identity or lifecycle edge; it cannot be
generalized into population completeness without an enumerating contract.

## Durable artifacts

- `research_knowledge/identity_lifecycle_population_crosswalk_v1.json`
  SHA-256 `e413e7364cee58185bb2010c514c7a0dd7ffb7b5006d9581448dbe43679c3552`
- `research_knowledge/security_identity_lifecycle_graph_v1.json`
  SHA-256 `e1ce93c7f1e2d0e944365d98abfdeff9083448121c602976a84b66d1715cecd7`
- `research_knowledge/identity_lifecycle_residuals_v1.json`
  SHA-256 `8fc07f74b594472b1b32327675f3daffd319e71d0f823f3e2258b782b74aa3ca`
- External KSEI metadata SHA-256
  `7b07c0fbaaf443ec7440a8159c8f349d3196978a8af2638a9089cef907589cc7`
- External KSEI share-table packet SHA-256
  `d5b93b89fca721b99a0c7d85ac0e79f55bcd1a6a2a8ef1dbe1f874bdaad46c2d`

Protected outcomes, canonical datasets, production/cloud/capture/telemetry,
provider credentials, scheduler state, and incumbent research state were not
accessed or mutated.
