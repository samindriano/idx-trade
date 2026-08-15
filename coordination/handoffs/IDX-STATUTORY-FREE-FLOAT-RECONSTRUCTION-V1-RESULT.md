# Handoff

from: Codex/Statutory-Free-Float-Reconstruction
to: ChatGPT reviewer
task_id: IDX-STATUTORY-FREE-FLOAT-RECONSTRUCTION-V1
model_used: Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 414f4c232326f4da6e3fb1430d824eb1329877e7
branch: data/idx-statutory-free-float-reconstruction-v1
head_commit: `fc5dc986fcd410066bad9bc62ea99f10aac60344`
scope: bounded official statutory free-float rule/report/issuer-LBRE recovery and fail-closed reconstruction audit

## Findings

* Exact IDX static attachment transport from preserved `FullSavePath` metadata works: 34/34 bounded attachment requests returned HTTP 200 PDF bytes.
* `Peng-S-00006/BEI.PLP/02-2026` and `Peng-S-00011/BEI.PLP/04-2026` were recovered with official bytes; each parses to 956 company rows.
* The selected issuer sample is DCII, WBSA, RLCO, BREN, BBCA, TLKM, and MAYA: 15 LBRE records, 5 corrections, 15 explicit official reported free-float values.
* Main LBRE PDFs expose an explicit Free Float section and share-bucket evidence, but this run does not promote an independently reconstructed point estimate.
* Direct `ListedCompany/GetAnnouncement` probes on 2026-08-15 returned HTTP 503 for both broad February 2026 and `Kep-00045` March 2026 probes.
* Exact official bytes/locators for `Kep-00045/BEI/03-2026`, `SE-00004/BEI/03-2026`, and `Kep-00101/BEI/12-2021` remain unresolved.
* Preserved free-float/sanction capture depth is April 2024–August 2026; 2021–2023 completeness is not demonstrated.

## Decisions

* Official reported free float is retained as `OFFICIAL_REPORTED`.
* Independently reconstructed point values are not promoted: all 15 issuer records are `BOUNDED_ONLY`.
* No `100% - sum(>=1%)`, HSC, investor-type, current-profile, or other unproven inference is used.
* Final verdict: `STATUTORY_FREE_FLOAT_SOURCE_REMEDIATION_REQUIRED`.

## External artifacts

Root: `D:\Documents\Project\idx-statutory-free-float-reconstruction-20260815-v1`

Manifest: `artifact_manifest.json`

Manifest SHA-256: `ff25cefed69af8cd221530a23f6fc31e85e0c510a21ef5bfb78526d618a45454`

## Validation

Focused statutory tests: `8 passed, 0 failed`.
Full pytest: `1 failed, 50 passed`; the only failure is the known unrelated
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
expectation (`raw_close` and `vendor_adj_close` are independently reported, so
the current implementation returns 2 conflicts while the old test expects 1).
`git diff --check`: PASS.

## Recommended next action

Keep the lane in review/remediation. Recover exact official rule attachments
and establish 2021–2023 market-report depth before any historical statutory
free-float panel or feature contract is considered.
