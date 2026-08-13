# Corporate Action PIT Source Audit — Result Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-CORPORATE-ACTION-PIT-SOURCE-AUDIT-V1
model_used: GPT-5 Codex / Luna xhigh orchestration
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `423b18c` plus bounded audit implementation
branch: `data/corporate-action-pit-source-audit-v1`
head_commit: see final pushed branch HEAD
scope: bounded live official IDX + public KSEI Corporate Action PIT source and semantics audit, 2018-01-01 through 2026-08-14

## Files changed

- `src/idx_trade/corporate_action_pit_audit.py`
- `tests/test_corporate_action_pit_audit.py`
- `docs/checkpoints/2026-08-14_CORPORATE_ACTION_PIT_SOURCE_AUDIT_RESULT.md`
- this handoff

Raw captures are external and are not committed:

`D:\Documents\Project\idx-corporate-action-pit-source-audit-20260814-v1-final2`

## Findings

- Direct IDX `ListingActivity/GetIssuedHistory` returned 708 ALL rows with
  complete pagination over the bounded date range; the `length=1` adversarial
  probe proved that declared totals must be fully paginated.
- The source exposes only source-native activity/share-count fields and no
  publication timestamp. `TanggalPencatatan` was not relabeled as a generic
  effective date.
- Six public KSEI security pages yielded 235 rows, 223 Active and 12
  Cancelled, with event ratios and Cum/Record/Distribution dates. Five public
  KSEI schedule pages also returned successfully.
- Sixteen bounded IDX issuer announcement calls and 48 official attachments
  returned successfully. MLPT exposed distinct original/KOREKSI announcement
  candidates and attachment hashes.
- Candidate publication matching found 1 unique selected-row candidate, but
  strict KSEI↔IDX date linkage found 0. All 12 selected activity rows remain
  PIT-unresolved under the fail-closed contract.
- No ratio agreement/mismatch was reported because there were zero strict
  comparable event joins. Source ratio text remains non-canonical.
- Split arithmetic diagnostic: 4 positive-derivable, 3 placeholder/invalid,
  and 5 non-share-count-family rows.

## Decision

`CONDITIONAL_SOURCE_USEFUL_PIT_LINKAGE_INCOMPLETE`

Sources are discovery-useful but not ready for canonical PIT event
materialization or market-wide backfill. A deterministic, event-specific
linkage contract is still required.

## External artifact identity

Manifest:
`D:\Documents\Project\idx-corporate-action-pit-source-audit-20260814-v1-final2\MANIFEST.json`

Manifest SHA-256:
`d44b9362909f5c05d8412ff07ca4c5616a74b43930bd1caf92242ed25b5e10cf`

All 7 manifest-listed normalized/summary files matched their recorded hashes
and byte counts after the final run. The manifest contains 88 successful
request records.

## Validation

- Focused tests: `5 passed`.
- Module compilation: passed.
- Full pytest: `44 passed, 1 failed`; failure is the pre-existing unrelated
  storage revision-conflict expectation (`raw_close` plus independent
  `vendor_adj_close` conflicts now yield 2 rather than 1). No unrelated storage
  or Foreign Flow code was changed.
- No models, outcomes, OHLC adjustment, bulk backfill, or protected marker was
  touched.

## Recommended next action

ChatGPT review should decide whether to authorize a separate event-specific
linkage design. Do not promote this audit into a canonical corporate-action
dataset yet.
