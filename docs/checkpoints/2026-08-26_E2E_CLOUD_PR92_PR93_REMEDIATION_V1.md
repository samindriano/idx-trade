# E2E Cloud PR #92/#93 Remediation V1

Status: REVIEW pending independent review; no merge or scheduler activation was
performed in this remediation.

## Scope

This remediation addresses the bounded correctness gaps identified against PR
#92 (`integration/e2e-cloud-first-orchestration-v1`) and PR #93
(`ops/e2e-paper-cloud-launcher-v1`). Existing E2E/PaperState, Decision,
Sizing, Execution, Official Open, outcome-blindness, and single-runtime
architecture contracts remain unchanged.

## Fixes

1. `CloudPaperArchive.latest_snapshot()` now checks the later `POST_EOD`
   lifecycle state before `PREOPEN` within the newest session. A next-session
   restore therefore prefers the newest committed lifecycle snapshot, while
   create-only commit/idempotency behavior is unchanged.
2. `materialize_official_open_from_cloud()` now implements an explicit
   downstream prospective-admission boundary. It requires the exact Official
   Open cloud schema, capture-only admission marker, session/slot schedule
   timestamp, timezone-aware source timestamp, exact non-negative capture lag,
   authority/upstream/field/transport contract, scheduled GitHub provenance,
   all required false guard flags, same-session/same-slot child keys, exact
   child SHA reads, and source-manifest timestamp/contract parity. Capture
   timestamps must be no later than the existing `09:22:59 Asia/Jakarta`
   hard PREOPEN deadline and cannot be future-dated relative to the consumer.
   Manual/workflow-dispatch captures, stale or malformed outer manifests, and
   the old 18:00 source-capture pattern are rejected. The producer remains
   capture-only; the returned consumer result records the admission boundary.
3. The cloud PREOPEN consumer polls for at most 90 seconds, capped by the
   existing hard deadline, so a producer commit arriving shortly after the
   consumer starts is observed without extending execution eligibility. The
   default-branch launcher retries were also offset to 09:03 and 09:13 while
   retaining the final 09:22 retry. A producer that never commits or commits
   after the deadline does not create a late fill.
4. `scripts/smoke_e2e_cloud_conditional_s3_v1.py` provides an explicitly
   activated, caller-prefixed, non-deleting live-storage smoke mechanism for
   first write, identical replay, conflicting write rejection, and read-back
   SHA verification. It was not activated in this remediation.

The documented manual dispatch is from a clean checkout with the existing
`E2E_CLOUD_STORAGE_BACKEND=s3`, `E2E_CLOUD_S3_ENDPOINT`,
`E2E_CLOUD_S3_BUCKET`, `E2E_CLOUD_S3_ACCESS_KEY_ID`, and
`E2E_CLOUD_S3_SECRET_ACCESS_KEY` environment variables set:

```powershell
$env:E2E_CLOUD_STORAGE_BACKEND = "s3"
python scripts/smoke_e2e_cloud_conditional_s3_v1.py `
  --activate RUN_LIVE_CONDITIONAL_S3_SMOKE_V1 `
  --prefix "smoke/e2e-conditional-s3-YYYYMMDDTHHMMSSZ"
```

The prefix must be new and throwaway; the script intentionally does not
delete the probe object. This command is documented only and was not run.

The Official Open producer now records `GITHUB_EVENT_NAME` so downstream
admission can distinguish scheduled capture from manual dispatch. This is
provenance only and does not authorize execution by the producer.

## Validation

- Cloud runtime, Official Open cloud, and conditional-store focused tests:
  PASS (36 collected, 36 passed).
- Relevant E2E/Official Open regression group: PASS (149 collected, 149
  passed).
- Full pytest: PASS (all collected tests passed; 3 pre-existing FutureWarnings
  in curated identity/tradability-anchor tests).
- py_compile for all changed Python entrypoints, YAML parse, and
  `git diff --check`: PASS.
- No provider, R2, model, PaperState, scheduler, or outcome access was run.

## Remaining live-proof gates

PRs #92/#93 remain open. Private R2 input-bundle provisioning, one future live
cloud capture, and live conditional-store smoke activation remain separately
authorized gates. Windows/manual retirement remains unauthorized.
