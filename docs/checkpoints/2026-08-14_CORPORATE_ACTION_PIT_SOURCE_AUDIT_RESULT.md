# Corporate Action PIT Source Audit — Bounded Live Result

Date: 2026-08-14 (Asia/Jakarta)
Branch: `data/corporate-action-pit-source-audit-v1`
Base lineage: `5b3053623d6bbf444807fb2228aed20d139e69ee`
Status: `REVIEW`
Verdict: `CONDITIONAL_SOURCE_USEFUL_PIT_LINKAGE_INCOMPLETE`

## Scope and boundaries

This was one bounded live source/semantics audit. It did not perform a market-
wide backfill, write the canonical corporate-action table, adjust OHLC, derive
features, train or score models, access protected outcomes, or use KSEI AKSes
credentials. Raw captures remain outside Git under:

`D:\Documents\Project\idx-corporate-action-pit-source-audit-20260814-v1-final2`

The source dates remain source-native. `TanggalPencatatan`, KSEI Cum Date,
Record Date, Distribution Date, and IDX `TglPengumuman` were not collapsed into
a new generic `effective_date`.

## Direct official IDX sources

### Listing activity

Endpoint:

`https://www.idx.id/primary/ListingActivity/GetIssuedHistory`

Parameters used for the bounded history:

`caType`, `dateFrom=20180101`, `dateTo=20260814`, `start`, and `length=250`.

The ALL query returned 708 rows over three pages (`250 + 250 + 208`). The
requested category results were fully paginated and matched their declared
`recordsFiltered` totals:

| IDX action type | Rows |
|---|---:|
| `ipo` | 207 |
| `waran` | 163 |
| `hmetd` | 81 |
| `stockSplit` | 73 |
| `tanpaHmetd` | 58 |
| `delist` | 33 |
| `partialDelisting` | 31 |
| `kurangModal` | 22 |
| `sahamBonus` | 15 |
| `gabungUsaha` | 9 |
| `Dividen Saham` | 7 |
| `obligasiWajibKonversi` | 4 |
| `esopMsop` | 3 |
| `partialRelisting` | 2 |

The explicit category probes for `hmetd`, `PrivatePlacement`, `stockSplit`,
`reverseStock`, `BuybackSaham`, `ipo`, `companyListing`, and
`partialDelisting` returned respectively 81, 0, 73, 0, 0, 207, 0, and 31
rows. Zero is recorded as the source response, not interpreted as proof that
the category is historically complete outside this endpoint's semantics.

The pagination adversarial probe requested `hmetd` with `length=1`: the source
declared 81 rows and returned 1. Therefore a single page is explicitly
rejected as incomplete by the adapter.

The source fields observed were `id`, `KodeEmiten`, `TanggalPencatatan`,
`JenisTindakan`, `JumlahSaham`, and `JumlahSahamSetelahTindakan`. The selected
sample contained 12 rows: 7 stock-split rows, 1 HMETD, 1 bonus-share row, 1
capital-reduction row, 1 partial-delisting row, and 1 IPO row. It had source
dates from 2023-10-06 through 2026-08-10.

### Issuer announcements

Endpoint:

`https://www.idx.co.id/primary/ListedCompany/GetAnnouncement`

Parameters used per ticker window:

`kodeEmiten`, `emitenType=*`, `indexFrom=0`, `pageSize=1000`, `dateFrom`,
`dateTo`, `lang=id`, and `keyword=`.

Sixteen bounded ticker/event windows were queried, with 48 official IDX
attachments downloaded from their advertised `FullSavePath` URLs. All 16
announcement responses and all 48 attachments returned HTTP 200 and non-empty
content. Naive `TglPengumuman` values were interpreted as Asia/Jakarta only for
the audit's UTC representation; this is an observed publication timestamp, not
an inferred effective date.

The strongest concrete revision example was MLPT: the 2026-07-15 source
window exposed both announcement `048/MLPT/PDC/VII/2026` and its `KOREKSI`
announcement `049/MLPT/PDC/VII/2026`, with distinct publication timestamps and
distinct official attachment hashes. The audit preserves both candidates and
does not select a canonical version from title/date proximity alone.

## Public KSEI sources

Security pages:

`https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}`

Sampled tickers: `IDPR`, `TRST`, `SINI`, `MEGA`, `MLPT`, and `RAJA`.

The visible table exposes `Type of CA`, `Ratio`, `Cum Date`, `Record Date`,
`Distribution Date`, and `Status`. The six pages yielded 235 normalized rows,
with 223 `Active` and 12 `Cancelled`. Sample history reached as far back as
2002 for some tickers and through 2026 for all sampled current-event pages:

| Ticker | Earliest observed event date | Latest observed event date |
|---|---|---|
| IDPR | 2016-05-20 | 2026-07-17 |
| TRST | 2002-06-03 | 2026-07-27 |
| SINI | 2020-07-15 | 2026-07-13 |
| MEGA | 2002-05-03 | 2026-04-30 |
| MLPT | 2014-03-25 | 2026-07-23 |
| RAJA | 2003-06-18 | 2026-07-24 |

KSEI event-family counts in the sample were Cash Dividend 79, Proxy Voting
131, Mixed Dividend 9, Right Distribution 9, Mandatory Conversion 3, Stock
Dividend 3, and Voluntary Conversion 1. KSEI ratios are retained as source
text with parse status; no economic ratio was promoted without a strict
cross-source event join.

The cancelled sample includes TRST cash dividend with Record Date 2020-09-04
and Distribution Date 2020-09-25. This demonstrates why status and cancellation
must be retained append-only rather than treated as a later overwrite.

Schedule pages:

`/publications/corporate-action-schedules/cash-dividend`

`/publications/corporate-action-schedules/share-bonus`

`/publications/corporate-action-schedules/rights-distribution`

`/publications/corporate-action-schedules/mix-dividend`

`/publications/corporate-action-schedules/masr`

All five schedule pages returned HTTP 200. Five ticker-filtered schedule rows
were retained, each with a KSEI reference, subject, source page hash, and
official KSEI document URL. The sample includes MEGA bonus, SINI HMETD, and
MASR schedule records; the MASR page also demonstrates that its current
schedule family is broader than stock split/reverse split alone.

## Cross-source linkage and audit diagnostics

The matching logic is intentionally a candidate audit, not a semantic date
guess. A ±120-day IDX issuer-announcement window and event-family tokens
produced 48 announcement candidate rows. Only 1 of the 12 selected IDX
activity rows had a unique event-family publication candidate; the other 11
had multiple or no candidates. All 12 selected rows remain unresolved under
the strict PIT contract because:

- `strict_ksei_idx_linkages = 0`;
- no KSEI security row had an exact match on the IDX
  `TanggalPencatatan` for the selected sample; and
- publication candidates were not promoted from proximity/title matching.

Ratio agreement/mismatch is therefore **not adjudicated**: there were zero
strictly comparable KSEI↔IDX event joins. This is safer than reporting a
false 0% or 100% ratio-parity rate.

The old share-count arithmetic was separated from event semantics:

- 4 selected stock-split rows had positive `JumlahSaham` and
  `JumlahSahamSetelahTindakan` values from which a mechanical change could be
  derived as a diagnostic;
- 3 stock-split rows were placeholders/invalid (`0 -> 1` or `0 -> 0`);
- 5 non-split rows were not assigned split arithmetic.

No generic old/new share-count or price-adjustment rule was promoted.

## Provider/capture result

Final capture request count: 88. All final requests were HTTP 200:

- 12 IDX issued-history requests including the deliberate pagination probe;
- 16 IDX announcement responses;
- 48 IDX announcement attachments;
- 6 KSEI registered-security pages;
- 5 KSEI schedule pages;
- 1 KSEI home request.

The preceding attempts showed transient public-KSEI HTTP 500 behavior when
KSEI was queried after a larger IDX burst. The final run changed only request
ordering and used the separate KSEI session before the IDX batch; it completed
without a provider failure. This is evidence of operational sensitivity, not a
claim that KSEI is permanently stable.

## Immutable artifact manifest

External root:

`D:\Documents\Project\idx-corporate-action-pit-source-audit-20260814-v1-final2`

Manifest SHA-256:

`d44b9362909f5c05d8412ff07ca4c5616a74b43930bd1caf92242ed25b5e10cf`

The manifest contains 7 normalized/summary files and 88 request records. The
final local verification found every manifest-listed file hash and byte count
matching. Raw HTTP files are referenced by path, timestamp, URL, params,
status, content type, byte count, and SHA-256 in the manifest; raw files are
kept external to Git.

## Decision

The official sources are useful for discovery and bounded candidate ledgers:

- IDX `GetIssuedHistory` is useful for paginated activity/share-count
  candidates, but has no publication timestamp and source-specific date only.
- KSEI public pages add ratios, operational dates, statuses, long sample
  history, and cancellation evidence, but the bounded sample did not establish
  deterministic issuer-event linkage to IDX activity rows.
- IDX `GetAnnouncement` supplies official publication/attachment provenance,
  including observable correction candidates, but event-family/date proximity
  is insufficient for automatic linkage.

Therefore the PIT source is **not ready for canonical or market-wide event
materialization**. Keep the result as:

`CONDITIONAL_SOURCE_USEFUL_PIT_LINKAGE_INCOMPLETE`

The next safe step requires a separately authorized deterministic linkage
contract (likely event-specific and attachment-aware). Do not bulk backfill,
adjust prices, or infer effective dates from this audit.

## Validation

Focused audit tests: `5 passed`.

`python -m py_compile src/idx_trade/corporate_action_pit_audit.py`: passed.

Full repository pytest: `1 failed, 44 passed` in the final run. The unrelated
failure is the existing `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` expectation of one conflict, while
current `src/idx_trade/storage.py` reports independent `raw_close` and
`vendor_adj_close` conflicts (two). No storage/Foreign Flow change was made in
this lane; the failure is reported rather than hidden or modified.

No protected outcome marker was accessed or written.
