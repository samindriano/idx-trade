# Handoff — Free Float / Effective Supply V1 Source Audit

from: Codex/Free-Float-Effective-Supply
to: ChatGPT independent review
task_id: IDX-FREE-FLOAT-EFFECTIVE-SUPPLY-V1-SOURCE-AUDIT
model_used: Luna
reasoning_level: xhigh
source_repository: https://github.com/samindriano/idx-trade
source_commit: 36a874da865b9d7f4e03b14f284b047e77bd8cc2
branch: data/idx-free-float-effective-supply-v1
head_commit: pending documentation commit
scope: bounded live source audit only

## Files changed

- \`docs/checkpoints/2026-08-15_FREE_FLOAT_EFFECTIVE_SUPPLY_SOURCE_AUDIT.md\`
- \`coordination/handoffs/IDX-FREE-FLOAT-EFFECTIVE-SUPPLY-V1-SOURCE-AUDIT.md\`

No provider implementation was changed. No raw live data was added to Git.

## Findings

1. Official IDX Company Profile Detail was successfully acquired for DCII,
   BBCA, BAIK, WBSA, and RLCO through a Chrome-impersonated \`curl_cffi\`
   transport. The strict existing parser normalized 7/20/7/10/6 current
   named-holder rows.
2. The complete bounded payload schema contains no explicit reported
   free-float/public-shares/shares-outstanding field. \`EfekEmiten_Saham\` is
   only a stock-security boolean. The profile endpoint is current-snapshot
   evidence, not historical PIT evidence.
3. Official KSEI \`BalanceposEfek\` ZIPs were acquired for 2026-02-27,
   2026-05-29, and 2026-07-31. They are aggregate local/foreign
   investor-category holdings, with 3,680/3,712/3,802 unique instrument
   rows. The archive page visibly lists monthly files from 2026-01-30 through
   2026-07-31.
4. The official KSEI/IDX 2026-03-03 press release confirms the monthly >=1%
   disclosure program, but the bounded official IDX \`GetAnnouncement\` calls
   returned non-JSON HTTP 503 responses. No official >=1% attachment bytes or
   deterministic attachment linkage was promoted.
5. The public mirror has a useful schema but one exact MAYA holding
   reconciliation mismatch; the existing parser correctly rejects it.

## Decisions

- \`OwnershipSnapshotMeta.reported_free_float_pct\` remains \`None\`.
- No holder complement, locked-holder classification, HHI, supply score, or
  Foreign Flow integration was performed.
- Source readiness is \`SOURCE_REMEDIATION_REQUIRED\`, not
  \`READY_FOR_OWNERSHIP_CONCENTRATION_CONTRACT\`.

## External artifacts

Root:
\`D:\\Documents\\Project\\idx-trade-free-float-effective-supply-20260815-v1\`

Consolidated manifest:
\`AUDIT_MANIFEST.json\`

Manifest SHA-256:
\`344b59cd84da8adc8866cb3e47f942a6ea92c1b32a6fb763d74b2a54647fed94\`

## Validation

- Focused provider tests: 10 passed.
- Full repository suite: 49 passed, 1 pre-existing unrelated failure,
  0 warnings.
- Failing test:
  \`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts\`
  (expected one conflict; current storage reports independent
  \`raw_close\` and \`vendor_adj_close\` conflicts).
- \`git diff --check\`: pass.

## Boundaries respected

No effective-float calculation, supply-tightness score, Foreign Flow V2
integration, outcomes, labels, model fitting, historical bulk acquisition, or
changes to other lanes were made.

## Recommended next action

Keep this lane in \`REVIEW\`. If ChatGPT authorizes remediation, recover the
official monthly >=1% IDX attachment and exact announcement/attachment
provenance before designing an ownership-concentration contract.
