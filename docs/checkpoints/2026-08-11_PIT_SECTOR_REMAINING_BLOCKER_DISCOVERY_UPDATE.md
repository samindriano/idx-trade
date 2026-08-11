# PIT Sector Remaining Blocker Discovery Update

Date: 2026-08-11
Branch: `data/idx-pit-sector-history-v1`
Status: `DISCOVERY_PROGRESS_RECORDED_NO_READINESS_CHANGE`

## Scope

Continue source discovery for the four remaining canonical PIT IDX-IC blockers only:

- annual 2022 dedicated issuer-classification source;
- annual 2023 dedicated issuer-classification source;
- annual 2024 explicit official effective-date evidence for canonical `Peng-00128/BEI.POP/06-2024`;
- annual 2026 explicit official effective-date evidence for canonical `Peng-00100/BEI.POP/06-2026`.

This checkpoint does **not** authorize parser/materialization, IPO census, incidental census expansion, model work, realized-outcome access, Path Risk work, execution/PnL work, or merge to `main`.

## Inventory remains fail-closed

No source is promoted by this discovery pass. Canonical inventory remains:

- `4 READY_FOR_ACQUISITION`
- `4 DISCOVERY_REQUIRED`

Third-party mirrors and media articles are discovery aids only. They are not accepted as canonical provenance and do not satisfy the official-IDX URL/SHA requirements.

## 2024 — effective-date evidence content identified, official acquisition path still unresolved

The canonical annual source remains:

- `Peng-00128/BEI.POP/06-2024`
- announced `2024-06-24`
- official canonical raw SHA already pinned in inventory: `4ecf5ebb2809c9007b68bfe0aa1c426428d77178ff9acbf744364afba00ad223`
- canonical raw PDF itself does not state an explicit effective date.

A discovery pass found multiple issuer-level **official IDX document contents** mirrored by a third party. Two independently inspected examples are especially useful:

### MDKA wrapper

- title: `Perubahan Klasifikasi Industri`
- ticker: `MDKA`
- announcement ref printed inside the document: `Peng-00001/BEI.PP1/01-2025`
- electronic document creation timestamp: `2025-01-22`
- explicit statement: change effective `24 June 2024`
- attached canonical references printed inside the document:
  - `PKIE Peng-00128.pdf`
  - `1_PKIE Peng-00128.pdf`
- mirror-file SHA-256 inspected during discovery: `6d22c0e81c8f1fa2d08e2bb82155be3b6c2be93aeb26b07abf06ec8b4e6b0d19`

### PANI wrapper

- title: `Perubahan Klasifikasi Industri`
- ticker: `PANI`
- announcement ref printed inside the document: `Peng-00004/BEI.PP3/01-2025`
- electronic document creation timestamp: `2025-01-22`
- explicit statement: change effective `24 June 2024`
- attached canonical reference printed inside the document: `PKIE Peng-00128.pdf`
- mirror-file SHA-256 inspected during discovery: `41333dfc76dfda611973606b8385924cf7585fc9be9cefcb40971addd5534df8`

Both documents state that they are official PT Bursa Efek Indonesia documents generated electronically and explicitly bind the issuer-level classification change to `Peng-00128`. Their **content** therefore provides a strong candidate for the multi-document effective-date provenance contract.

However, the copies inspected in this pass were third-party mirrors. The exact official IDX HTTPS `FullSavePath` / `From_EREP` URL for either wrapper has not yet been recovered and hash-pinned from the official host. Under the existing provenance contract this is insufficient for promotion.

Therefore 2024 remains `DISCOVERY_REQUIRED`.

### Important PIT implication if official copy is recovered

If one of the 22 January 2025 issuer wrappers is ultimately used as the decision-critical effective-date evidence, the current knowledge-time contract implies:

```text
effective_from                 = 2024-06-24
canonical announced_at         = 2024-06-24
supporting evidence announced  = 2025-01-22
knowledge_at / PIT usable      = 2025-01-22
```

This is intentional. The historical classification can be effective in June 2024 while the model must not treat the decision-critical linked evidence as knowable before the official wrapper exists.

Do not silently backdate `knowledge_at` to June 2024 merely because the wrapper later describes a June effective date.

## 2026 — canonical omission independently reconfirmed

The canonical source remains:

- `Peng-00100/BEI.POP/06-2026`
- dated `2026-06-24`
- changes `ARGO`, `HRUM`, and `PACK`
- official canonical raw SHA already pinned in inventory: `d95b27f4bab74a2da9ab737c3bdd96bc4626cfb97635ffa32a9449be78d7db98`

A full two-page copy of the IDX document was re-inspected during this discovery pass. It contains the old/new classifications for all three issuers and closes with the date `24 Juni 2026`, but it does **not** contain an explicit effective-date statement.

This confirms that the 2026 blocker is real and is not merely a parser/text-extraction miss. 2026 still requires separate official linked effective-date evidence.

A third-party important-notice mirror lists `Perubahan Klasifikasi Industri Perusahaan Tercatat` on `2026-06-25`, but that listing is discovery evidence only and must not populate `effective_from`.

## 2022 — event facts corroborated, dedicated canonical ref still missing

Discovery corroborates the previously recorded event facts:

- BEI annual evaluation announcement date: `2022-06-24`;
- seven affected issuers;
- reported effective date: `2022-07-01`;
- known affected examples include `BIPI`, `TELE`, `MITI`, `YELO`, and `WIFI`.

`Peng-00150/BEI.POP/06-2022` remains a sector-index evaluation/reconciliation package and must not be promoted as the dedicated issuer-classification source.

The exact dedicated canonical classification announcement ref/official attachment remains unresolved. Media reporting is retained only as a discovery pointer.

## 2023 — event facts corroborated, dedicated canonical ref still missing

Discovery corroborates:

- BEI annual classification announcement date: `2023-06-22`;
- fourteen affected issuers;
- `BMTR` is one confirmed affected issuer; reporting also identifies related MNC-group changes including `MNCN`/`MSIN` in the same classification-change context.

`Peng-00156/BEI.POP/06-2023` remains a sector-index evaluation/reconciliation package and must not be promoted as the dedicated issuer-classification source.

The dedicated canonical classification announcement ref and a bound explicit effective date remain unresolved.

## High-value next discovery path

An open-source client for the IDX website confirms that the public IDX frontend uses:

```text
/primary/ListedCompany/GetAnnouncement
```

and that announcement responses expose attachment metadata including the official `FullSavePath`.

The highest-value next retrieval attempts are therefore:

1. query `MDKA` and/or `PANI` for `2025-01-22` and recover the official IDX `FullSavePath` for `Peng-00001/BEI.PP1/01-2025` or `Peng-00004/BEI.PP3/01-2025`;
2. acquire the official wrapper bytes, verify their SHA-256, and only then evaluate promotion of 2024 under the existing linkage contract;
3. query `ARGO`, `HRUM`, and `PACK` around `2026-06-24` to `2026-06-25` for issuer-level classification wrappers that may explicitly state the 2026 effective date;
4. query known changed tickers from the 2022 event around `2022-06-24` / `2022-07-01` to recover the dedicated attachment/ref;
5. query `BMTR` plus other known changed issuers around `2023-06-22` to recover the dedicated 2023 attachment/ref and explicit date evidence.

No announcement number should be guessed from numerical adjacency to sector-index packages.

## Decision

Keep all four blockers fail-closed.

The 2024 blocker is now narrower: the effective-date/linkage **content** is identified, but official IDX acquisition provenance is unresolved. This is meaningful progress, but not sufficient for `READY_FOR_ACQUISITION`.
