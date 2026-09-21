# IDX-Trade Adoption Documentation Audit V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **DOC-ONLY AUDIT / SYNTHETIC ADOPTION STILL NO-GO FOR LIVE USE**

This audit records review findings against the inherited adoption packet. It
does not invalidate the candidate code tests, but it prevents the inherited
packet from being treated as a self-contained operational qualification record
without the limitations below.

## Identity and lineage

- The inherited adoption records intentionally identify the preceding
  candidate branch, codex/idx-authoritative-runtime-adoption-20260921.
- This shadow packet identifies the current branch,
  codex/idx-shadow-runtime-precanary-20260921, separately.
- Candidate code was last tested at 66140b05872e60191ae4090811f168aaef6d71a7.
  Documentation commits cda31d2d, 2be0295b, and 221e9564 followed it; no
  src/tests/scripts changes were found after the candidate code HEAD.
- The lineage matrix contains a malformed active E2E-Paper action path. This
  shadow packet records the exact pinned path for review, but does not rewrite
  the inherited historical file:
  C:\Users\Sam\.codex\worktrees\idx-e2e-baseline-paper-pinned-20260824\scripts\run_e2e_paper_scheduled_v2.py.
- Lineage remains split: active 32eaaa8e, candidate base 402fca4b, hardening
  source 8ceec523, and origin/main 8b5bc6db are not silently collapsed.

## Matrix and review limitations

1. The Markdown entrypoint/config matrix describes more surfaces than the
   machine-readable JSON matrix. Controller V1, controller V2, and
   evidence-health are not represented one-for-one in JSON, and PREOPEN_CA
   plus missed-Open continuity are combined there.
2. The challenge report is MAIN-run. A delegated observer did not return a
   result, so the report is candidate-local challenge evidence, not an
   independent external review.
3. The adoption records report test counts but do not include exact commands,
   selectors, environment/dependency versions, timestamps, exit codes,
   warning sources, or hashed raw result logs. Reproduction is therefore not
   fully self-contained.
4. The hardening dossier and completion records are historical evidence at
   8ceec523 and are not all present in the current HEAD. They must be treated
   as external immutable references, not as files silently available in this
   branch.
5. Local status documents have older dates and are not authoritative for the
   current active runtime. The exact active task/config observations in the
   shadow census and the canonical coordination snapshot at origin/main are
   higher-priority evidence for current operational lineage.
6. The defensible claim is that scheduler state was inspected read-only and
   no scheduler mutation or invocation occurred. A broader claim that no
   scheduler state was accessed would be inaccurate.
7. The contract registry retains several stale-looking remaining-gate labels
   even though later adoption records report the corresponding local
   synthetic checks as PASS. This shadow packet keeps the real gates open
   rather than silently reconciling the conflict.

## Impact

These are documentation/provenance defects and unresolved external gates. They
do not authorize a source rewrite, scheduler repin, provider access, live
migration, canary, or production promotion. The candidate remains
READY_IN_SYNTHETIC_RUNTIME only.

## Corrected interpretation

The inherited adoption packet is useful historical candidate evidence. This
shadow packet is the current review authority for real retained-artifact
discovery and explicitly records that real migration, replay, CA composition,
recovery, fallback, canary, and production gates remain blocked or unrun.
