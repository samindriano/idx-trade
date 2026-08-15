# Handoff

from: Codex/Ownership-HSC-Source-Remediation
to: ChatGPT independent review
task_id: IDX-OWNERSHIP-HSC-SOURCE-REMEDIATION-V1
model_used: Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 69cdd303ad937e6bc90d930955f751f1a2686ab0
branch: data/idx-ownership-hsc-source-remediation-v1
head_commit: 18650f8a2d83df12a6caa83235893d6273583406
scope: Official IDX/KSEI HSC/RSC transport, raw attachment/hash/provenance recovery, bounded PIT event representation, and one official monthly >=1% attachment retry.
files_changed: docs/checkpoints/2026-08-15_HSC_SOURCE_REMEDIATION.md; coordination/handoffs/IDX-OWNERSHIP-HSC-SOURCE-REMEDIATION-V1.md
external_artifact_root: D:\\Documents\\Project\\idx-ownership-hsc-source-remediation-20260815-v1
external_manifest_sha256: 8cae847d2aa2aad2c16f7510d2c94d4578af522cf37e9f634caaf60bd2b6925c
findings:
  - Official IDX GetAnnouncement metadata was recovered from preserved Financial PIT response captures; no HSC/RSC locator was guessed.
  - The public Nuxt announcement page and bundle expose the official route and FullSavePath attachment contract.
  - Bounded live API calls to GetAllAnnouncement and GetAnnouncement returned HTTP 503, but canonical StaticData paths were directly retrievable via www.idx.id.
  - Nine initial April 2026 HSC records, MGRO May HSC, DGWG July publication, LUCY July RSC, and MGRO correction bytes were recovered and SHA-pinned.
  - Official BEI/KSEI decree confirms joint review/publication and reannouncement/removal semantics, but does not expose a general numeric threshold in the recovered evidence.
  - Official monthly >=1% attachment Peng-LKS-00060/BEI.PLP/04-2026 was recovered as a 72-page PDF with embedded 31-Mar-2026 date.
decisions_made:
  - Verdict is HSC_SOURCE_READY_FOR_CONTRACT for a separate event contract review.
  - Keep HSC/RSC events separate from BalanceposEfek and monthly >=1% ownership.
  - Preserve original and MGRO KOREKSI bytes independently.
  - Treat IDX TglPengumuman as publication time; retain PDF signing/document date separately.
  - Do not infer a threshold, free float, locked shares, or daily forward-filled status.
decisions_needed:
  - ChatGPT review of the proposed HSC event contract and the explicit unresolved threshold/methodology boundary.
  - Separate authorization before any daily HSC panel, feature design, or broad monthly >=1% acquisition.
blocking_risks:
  - Live announcement APIs were 503 during the bounded probe; the current recovery path depends on preserved metadata locators plus direct StaticData retrieval.
  - The decree delegates the detailed review mechanism to a written BEI/KSEI agreement not included in the recovered public PDF.
  - HSC persistence is safe only as an explicit event-state rule; absence of a repeated HSC publication must not be interpreted as removal.
validation_run: focused ownership provider tests 10 passed; full pytest 49 passed / 1 unrelated pre-existing storage expectation failed; git diff --check passed
recommended_next_action: Independent ChatGPT review; do not integrate into free-float/effective-supply features until the event contract and methodology boundary are accepted.
