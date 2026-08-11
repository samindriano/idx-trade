# IDX Trade — Current Status

Date: 2026-08-11 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use the
project ledgers and newest dated checkpoints. If older text conflicts, this
file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- alpha architecture search: **CLOSED**;
- cumulative viewed historical alpha candidates: `17`;
- final historical-development ranker:
  `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- final V3-B refit: **FROZEN SUCCESSFULLY**;
- final model SHA-256:
  `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`;
- exact 33-feature order SHA-256:
  `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- Path Risk V1 / PR-001: **CLOSED — `PATH_RISK_A_DISCOVERY_FAIL_CLOSE`**;
- Path Risk V2 / PR-002 + PR-003: **CLOSED — `PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`**;
- Path Risk V2 winner: **none**;
- Path Risk F5/F6: **SEALED / NOT NEEDED AFTER V2 FAIL_CLOSE**;
- post-2026-07-31 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- calibration / alpha+risk integration / execution-PnL / Kelly / paper/live:
  not authorized automatically.

## Final alpha ranker

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

V3-B is exact V2 `HGB_XS_MARKET` information plus eight frozen causal
Structure-Lite geometry features. It was the only V3 survivor and later passed
its one-shot V2F5/V2F6 late-development confirmation. V4-A Participation,
V4-B Price Path and V4-C Cross-Sectional Context produced no survivor.

Final refit facts:

- rows/tickers/sessions: `292,633 / 737 / 20..1250`;
- training table SHA-256:
  `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe`;
- model SHA-256:
  `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`;
- manifest SHA-256:
  `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9`;
- sessions `1225..1250` were training-only;
- no new historical performance metric was computed in final refit;
- fresh-forward outcomes were not accessed.

Controlling checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REFIT_RUNTIME_RESULT.md`

## Path Risk V1 — closed

PR-001 tested q75 pre-resolution adverse-excursion regression using the exact
33 causal features. It showed useful ordering diagnostics but failed the
frozen proper-scoring gate:

- F1/F2/F3 relative pinball improvement:
  `+0.004267 / +0.011273 / +0.014061`;
- F4: `-0.033463`;
- median improvement: about `+0.00777`, below the `+0.02` gate;
- q25 and worst-fold gates failed;
- Spearman and Q5-Q1 adverse-excursion ordering gates passed.

Frozen verdict:

`PATH_RISK_A_DISCOVERY_FAIL_CLOSE`

PR-001 remains permanently viewed and cannot be rescued/reinterpreted as a
winner.

Controlling files:

- `docs/PATH_RISK_V1_LEDGER.md`;
- `docs/checkpoints/2026-08-10_PATH_RISK_V1_DISCOVERY_RESULT_FAIL_CLOSE.md`.

## Path Risk V2 — closed

Frozen specification:

`docs/PATH_RISK_V2_SPEC.md`

Spec Git blob:

`6d171d3f492b9cd15e0a176428eb9d6e4f6c20c5`

V2 tested exactly two preregistered candidates on Path Risk development folds
F1-F4:

1. PR-002 `PATH-RISK-V2-STOP-H10-HGB-002`
   - exact 33 features;
   - direct HGB `P(stop touch within H10)`.
2. PR-003 `PATH-RISK-V2-DISCRETE-CR-HGB-003`
   - exact 33 features + deterministic horizon step H1..H10;
   - multiclass CONTINUE/STOP/TP discrete hazard model;
   - comparable output = H10 stop cumulative incidence.

The one authorized F1-F4 discovery run completed on code HEAD
`9378943bde44b33e311bec1e1daf38ca5cd9b5d3` after a clean preflight of
`471 passed, 0 failed, 3 warnings`.

Frozen result:

`PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`

Winner: none.

Both PR-002 and PR-003 showed positive risk ordering/discrimination:

- ROC-AUC > 0.5 on all folds;
- Q5-Q1 stop-touch spread positive on all folds;
- both improved log loss versus the fold-specific V3-B alpha-only stop-risk
  mapping on all folds.

But both failed the decision-critical proper-scoring comparison against the
training stop-touch base-rate comparator:

- PR-002 nonnegative log-loss improvement vs base: `0/4`;
- PR-003 nonnegative log-loss improvement vs base: `0/4`;
- PR-002 nonnegative Brier improvement vs base: `1/4`;
- PR-003 nonnegative Brier improvement vs base: `0/4`.

Therefore neither candidate is eligible for promotion. Their useful ordering
signal may not be reinterpreted post hoc as a validated V2 probability/risk
layer.

Artifact hashes:

- candidate metrics:
  `c9e5ea87f66252461bebff2bcbfe91d044618166142b6e9e5de48290ffc22f3c`;
- comparator metrics:
  `c99c89e65710c9aaa2fb95eab57d134885b8054d68f13445b1cae44f4bf06da6`;
- predictions:
  `2fa1204698c207920b6c439eebc5e6123d3b24497c6432e2ba3a23db1b16a7b3`;
- summary:
  `67689476b1cad17b0f39144bcce82e01a00c3f62e30a991ce2c381c5f7b0f332`.

Controlling files:

- `docs/PATH_RISK_V2_LEDGER.md`;
- `docs/checkpoints/2026-08-11_PATH_RISK_V2_DISCOVERY_RESULT_FAIL_CLOSE.md`.

Consequences:

- PR-002 and PR-003 are permanently viewed / closed;
- no Path Risk F5/F6 access is needed or authorized;
- no PR-004 rescue is pre-authorized;
- any future Path Risk V3 must be a genuinely new preregistered hypothesis
  family, not a retune/recalibration/relabeling of V1/V2;
- no risk-veto, alpha reranking, sizing, or alpha+risk integration exists.

## Fresh-forward independent alpha verdict

The final V3-B ranker is independently evaluated only on the first exact
**100 consecutive H10-mature official signal sessions strictly after
2026-07-31**.

Daily outcome-blind operation may record data provenance, exact V3-B features,
scores/ranks, model/artifact fingerprints and maturity state. It must not
expose realized TP/SL, PR-AUC, ROC-AUC, Q5-Q1 performance, realized return or
PnL before the one-shot outcome-access boundary.

Before future outcome access, the exact block and source snapshots must be
hash-pinned, then `FORWARD_OUTCOME_ACCESS_STARTED` must be written atomically
before outcomes are loaded.

## Orchestration execution policy — refreshed 2026-08-11

The project uses **parallel-first LIGHT orchestration for meaningful work** to
reduce wall-clock time with Luna xhigh while preserving frozen research
boundaries.

- MAIN identifies the ready execution frontier before substantial work;
- independent ready scopes should be spawned before MAIN duplicates them;
- `LIGHT` = default for roughly 2–3 useful independent workstreams;
- `HEAVY` = 3–6 independent critical-path scopes or decision-changing review;
- `DIRECT` = small/inherently sequential work;
- dependent scientific experiments remain sequential even when supporting
  implementation/tests/audit work can run concurrently;
- `Luna xhigh` remains MAIN/worker default; `Sol High` remains a bounded
  decision-changing escalation.

The Path Risk V2 hardening milestone demonstrated this with five parallel Luna
workers before the serialized evidence-producing discovery run.

## Immediate next action

Path Risk V2 is closed. Do not automatically open F5/F6 or create PR-004.

Current research-safe priorities are:

1. preserve the final V3-B ranker and continue outcome-blind fresh-forward
   operation/accumulation under the existing 100-session contract;
2. keep Path Risk inactive unless a separately researched and preregistered V3
   hypothesis family is explicitly authorized;
3. keep probability calibration, alpha+risk integration, execution-PnL, Kelly,
   paper/live and forward realized-outcome access blocked unless separately
   authorized.

## PIT sector official raw acquisition update — 2026-08-11

On `data/idx-pit-sector-history-v1`, official IDX raw attachments were
acquired and inspected outside Git at
`D:\Documents\Project\idx-pit-sector-official-raw-20260811`. The factual
inventory and complete hash/layout table are in
`docs/checkpoints/2026-08-11_PIT_SECTOR_OFFICIAL_RAW_ACQUISITION_RESULT.md`.

The inventory remains fail-closed: `3` of `8` canonical sources are ready and
`5` remain `DISCOVERY_REQUIRED`. Annual 2022/2023 packages recovered from
`Peng-00150` and `Peng-00156` are sector-index evaluation evidence, not
canonical issuer-classification history. PALM, 2024, and 2026 raw attachments
are present, but their canonical PDFs do not state effective dates; no dates
were inferred. No model, sector score, Path Risk run, or outcome access was
started. Focused PIT-source tests passed `8/8`.

## PIT sector multi-document effective-date contract — 2026-08-11

The independent review refinement is implemented and tested. A canonical IDX
classification document may now use a separate hash-pinned official IDX
effective-date document only when the linkage explicitly binds the canonical
source ID/ref/hash and affected ticker(s). The canonical top-level
`effective_from` remains mandatory and equal to the evidence date; no date
inference is permitted. Linked evidence will also be hash-checked and recorded
in the acquisition manifest.

PALM passes this contract and is promoted to `READY_FOR_ACQUISITION` with
effective date `2023-10-02`. The inventory is now `4/8` ready and `4/8`
blocked. Official discovery found no explicit effective-date evidence for
`Peng-00128/06-2024` or `Peng-00100/06-2026`, and no dedicated canonical annual
issuer-classification attachments for 2022 or 2023. `Peng-00150` and
`Peng-00156` remain sector-index reconciliation evidence only. Focused PIT
tests passed `14/14`; full pytest passed `483/483` with 3 existing warnings.

## PIT sector 2024 effective-date evidence resolved — 2026-08-11

The official IDX `ListedCompany/GetAnnouncement` endpoint returned the
22-January-2025 MDKA disclosure `Peng-00001/BEI.PP1/01-2025` and its official
`FullSavePath`. The acquired IDX PDF explicitly references `PKIE Peng-00128.pdf`
and states that the classification change is effective `2024-06-24`. Its
SHA-256 is `860a0ab9aa0227b182d7a9c11f68a76fd775651763a962427cfca8cdc66d8f9f`
(5,709 bytes). PANI `Peng-00004/BEI.PP3/01-2025` independently corroborates
the same date. The 2024 canonical source is therefore promoted to
`READY_FOR_ACQUISITION`; its PIT knowledge date is `2025-01-22`.

The inventory is now `5/8` ready and `3/8` blocked: dedicated annual 2022,
dedicated annual 2023, and official 2026 effective-date evidence. Official
queries found only the 2026 canonical `Peng-00100` and sector-index
reconciliation `Peng-00099`; no linked effective-date document was found.
The 2022/2023 historical endpoint queries returned no canonical records.
Focused PIT tests passed `18/18`; full pytest passed `489/489` with 3 existing
FutureWarnings. No parser/materialization, IPO/incidental census expansion,
model, outcome, or `main` merge was started.

## PIT sector exchange-announcement retrieval audit — 2026-08-11

The official IDX public announcements page was traced through the downloaded
frontend bundle. The page calls
`/primary/NewsAnnouncement/GetAllAnnouncement` with `keywords`, `pageNumber`,
`pageSize`, `dateFrom`, `dateTo`, and `lang`; the attachment renderer selects
`Attachments[].FullSavePath` and uses the `IsAttachment=0` file as the primary
document. The page itself states that its public listing covers only the most
recent three years and directs older history to TICMI. The audited frontend
bundles and the raw 2026 attachments are retained outside Git under
`D:\Documents\Project\idx-pit-sector-official-raw-20260811`.

Targeted exchange-level queries through the official endpoint returned no
records for the 2022 June/July and 2023 June/July classification searches
(`ItemCount=0`), so no annual 2022/2023 canonical source or effective date was
promoted. This is a public-retention boundary, not evidence that the historical
announcements did not exist.

The 2026 June query returned canonical exchange announcement
`Peng-00100/BEI.POP/06-2026` on 2026-06-24 18:55 with its official PDF and ZIP
attachments. The PDF was acquired from the equivalent official `idx.id` host;
it is 312,989 bytes with SHA-256
`8b5413f18afc75cc17260c2400611d710e8f270d46a49c5a396f557b27cf8b25`. It lists
the affected issuer classifications but does not state an explicit effective
date. The nearby `Peng-00099/BEI.POP/06-2026` document states that sector-index
periods begin 2026-07-01, but it is an index evaluation/reconciliation source,
not canonical issuer-classification evidence, and was not promoted or used to
infer a date.

The inventory therefore remains `5 ready / 3 blocked`: dedicated annual 2022,
dedicated annual 2023, and linked official effective-date evidence for the
canonical 2026 source. No source inventory or parser behavior changed in this
audit. Focused PIT tests passed `18/18`; full pytest passed `489/489` with the
same 3 existing FutureWarnings. No parser/materialization, IPO/incidental
census expansion, model, outcome, Path Risk, or `main` merge was started.

## PIT sector Zapi/archive discovery — 2026-08-11

The prioritized 2026 issuer-history search covered ARGO, HRUM and PACK from
2026-06-24 through the latest available 2026-08-11 records. The Zapi company
captures contained 6/8/25 rows in that window and zero classification-keyword
matches; bounded Zapi raw issuer probes also returned `ResultCount=0`. No
later official disclosure linking `Peng-00100/BEI.POP/06-2026` with an
explicit effective date was found. The canonical PDF remains hash-pinned but
date-incomplete; no date was inferred from `Peng-00099` or publication time.

For 2022/2023, the stored Zapi/raw captures remain empty (`ItemCount=0`) and
no dedicated official ref, attachment, or effective-date evidence was
recovered. Zapi's raw passthrough did not establish an archive beyond the
public retention boundary. The next highest-value official route is authorized
TICMI/TICMIDATA archive access. Inventory remains `5 ready / 3 blocked`.

No inventory or test contract changed. This was documentation-only discovery;
no parser/materialization, census, model, outcome, OPEN-backfill, Path Risk,
execution/PnL, or `main` work was started.

## Hard boundary

Do not:

- reopen or modify the final V3-B alpha architecture;
- rescue/rewrite PR-001, PR-002, or PR-003;
- add PR-004 as an immediate post-result rescue;
- access Path Risk F5/F6 after the V2 fail-close;
- reinterpret ranking diagnostics as a probability-model PASS;
- access or summarize post-2026-07-31 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED` now;
- create risk-veto, reranking, position-sizing or alpha+risk integration rules;
- start execution/PnL/Kelly/paper/live automatically.
