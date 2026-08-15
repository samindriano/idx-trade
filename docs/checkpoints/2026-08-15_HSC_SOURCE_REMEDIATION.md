# HSC Source Remediation V1 — bounded official evidence result

Date: 2026-08-15 (Asia/Jakarta)
Branch: data/idx-ownership-hsc-source-remediation-v1
Parent: 69cdd303ad937e6bc90d930955f751f1a2686ab0

## Decision

The bounded HSC/RSC source is ready for a separate contract review:

HSC_SOURCE_READY_FOR_CONTRACT

This does not authorize daily feature materialization, free-float inference,
HHI, Foreign Flow integration, model work, or outcome access.

## Transport and provenance

The IDX frontend route is https://www.idx.id/id/berita/pengumuman/. Its
Nuxt bundle identifies the official GET route
/primary/NewsAnnouncement/GetAllAnnouncement with parameters keywords,
pageNumber, pageSize, dateFrom, dateTo, and lang. The older/issuer route
/primary/ListedCompany/GetAnnouncement remains the relevant metadata route
used by the preserved Financial PIT captures.

In a bounded probe, both API routes returned non-JSON HTTP 503 on the official
hosts, including empty and HSC-filtered requests. The public page itself
returned 200 and exposed canonical StaticData attachment URLs. The canonical
URLs use www.idx.co.id; the same official StaticData paths were retrieved
successfully through www.idx.id, which is the working official web host in this
run. No announcement number or attachment filename was guessed: every HSC/RSC
locator came from preserved official IDX GetAnnouncement response captures.

The external immutable evidence root is:

D:\\Documents\\Project\\idx-ownership-hsc-source-remediation-20260815-v1

Final AUDIT_MANIFEST.json SHA-256:

8cae847d2aa2aad2c16f7510d2c94d4578af522cf37e9f634caaf60bd2b6925c

The manifest records retrieval timestamps, canonical/retrieval URLs, response
status/content type/size, PDF hashes, metadata-capture hashes, normalized
event hashes, and the bounded secondary cross-check.

## Recovered official HSC/RSC evidence

Direct official IDX attachment retrieval succeeded for 24 primary HSC/RSC
PDFs: the nine initial April HSC records, MGRO May HSC, DGWG June-dated HSC
published on 1 July, and LUCY RSC. A separate two-PDF official MGRO correction
lineage was preserved. All were HTTP 200 PDFs and are hash-pinned in the
external manifest.

Examples:

- LUCY initial: announcement Peng-00005-HSC/BEI.WAS/04-2026, KSEI-2152/DIR/0426,
  published by IDX at 2026-04-02 18:02:54, ownership as-of 2026-03-31,
  concentration 95.47%. Attachment SHA-256
  5a5ac1154e5ab10d84bc630223d084539d6b01cee922a14024489096083faaff.
- MGRO: announcement Peng-00012-HSC/BEI.WAS/05-2026, KSEI-3504/DIR/0526,
  published by IDX at 2026-06-02 08:50:46, document date 2026-05-29,
  ownership as-of 2026-05-26, concentration 93.76%. Attachment SHA-256
  76d27ffc31216de6e5c20ec0ce5302f6322c3d455afd26e300466719834c1d67.
- DGWG: announcement Peng-00014-HSC/BEI.WAS/06-2026, KSEI-4448/DIR/0626,
  published by IDX at 2026-07-01 14:36:23, ownership as-of 2026-06-25,
  concentration 97.35%. Attachment SHA-256
  25fd583fa48c8f4ae1f6f288cafa9284a93459e1c87e384259e3ec789ac5c7e2.
- LUCY removal: Peng-RSC-00001/BEI.WAS/07-2026,
  KSEI-4604/DIR/0726, published by IDX at 2026-07-03 15:10:24, source
  methodology date 2026-06-29, explicit status HSC_REMOVED. Attachment
  SHA-256 3d44929314740e599f144aaa0a878d307ac933324d900a32da642d9b00af8e39.

The complete bounded normalized event representation is external:

- hsc_pit_events.csv — 13 rows, SHA-256
  2ef4099861c61a29f964868161829ee6b27c58554ce58b0a79a079b5b54db30a
- hsc_pit_events.json — SHA-256
  eb0ceab268a62cd728699fcde5020d4fa2a0cc7a8c116933ed943b556a6b7527

It contains ticker, ownership_as_of_date, IDX publication timestamp, UTC
normalization with an explicit Asia/Jakarta assumption, status, concentration,
IDX/KSEI announcement numbers, official source URL, and source SHA-256.

## Initial list and correction lineage

The preserved official response capture identifies the initial April HSC cohort
as nine records: AGII, BREN, DSSA, IFSH, LUCY, MGLV, RLCO, ROCK, and SOTS.
Each has a distinct IDX announcement number Peng-00001 through Peng-00009,
an official attachment, KSEI number KSEI-2148 through KSEI-2156, an explicit
2026-03-31 ownership-as-of date, and an explicit percentage in the attachment.

MGRO also has an official same-number KOREKSI publication at
2026-06-02 17:05:50. Its main and attachment bytes are preserved separately;
the correction attachment SHA-256 is
22af3bbc660ea2603f05010560bb2d51131e93b0523d85c71506d30ae84c0e25.
The original and correction were not collapsed into one raw artifact.

## Semantics and PIT policy

The official BEI/KSEI decree is:

https://web.ksei.co.id/files/SKB-Penetapan_Kepemilikan_Saham_Terkonsentrasi_Tinggi.pdf

It establishes Kep-00047/BEI/03-2026 and KEP-0024/DIR/KSEI/0426, issued and
effective 2026-04-02. Its SHA-256 is
920b0a84bcaa18a7c7911e4f7b8acc6557eb31858cef5dbc0acfc60d82a39de0.
The decree says BEI and KSEI review concentrated ownership, publish the
determination on the IDX website, reannounce removal no later than five
exchange days after a completed review when the condition no longer holds, and
do not reannounce when it still holds.

Recovered event attachments explicitly define the calculation over scrip and
scripless shares and provide the aggregate percentage. They do not provide a
general numeric threshold or the full written review mechanism; those remain
unresolved and must not be inferred. Absence of a new HSC publication is not
treated as removal. The bounded event policy is therefore: an HSC event is
usable from its own observed IDX publication timestamp; it remains unresolved
for an end date unless an explicit RSC/removal document or separately approved
official evidence exists.

IDX TglPengumuman is the publication timestamp. PDF signature/document dates
are retained as separate evidence and are not substituted for publication
time. The normalized UTC column assumes the official IDX timestamps are naive
Asia/Jakarta; the original local value remains authoritative in the event
record.

## Monthly >=1% retry

The same preserved IDX metadata path recovered the official monthly attachment
Peng-LKS-00060/BEI.PLP/04-2026, titled Pemegang Saham di atas 1% (KSEI).
IDX published it at 2026-04-02 15:20:12; the attachment embeds snapshot date
31-Mar-2026, has 72 PDF pages and the expected ownership columns. The raw
attachment is 7,935,478 bytes with SHA-256
8fde2ef936c7207d65c7a5187c005dd7edbf34f626c15bba60e557ada8fc02cb.

This confirms official attachment recovery, but it remains separate from HSC,
BalanceposEfek, and the existing CSV parser contract. No monthly ownership
panel was materialized.

## Secondary cross-check

The public LUCY RSC mirror was used only as a locator/content cross-check. Its
bytes do not exactly match the official IDX bytes, although normalized PDF
text matches. The mirror is therefore not canonical and is not used for the
event representation.

## Tests and boundary

Focused ownership provider tests: 10 passed, 0 failed.

Full repository pytest: 49 passed, 1 failed. The single failure is the known
unrelated storage expectation test test_storage.py::test_explicit_revision_mode_returns_audit_conflicts;
the current implementation reports independent raw_close and vendor_adj_close
revision conflicts, while that older test still expects one conflict. No
storage.py change was made in this lane. git diff --check passed.

No models, features, Foreign Flow, BalanceposEfek rewrite, outcomes, or
unrelated lanes were accessed or changed.
