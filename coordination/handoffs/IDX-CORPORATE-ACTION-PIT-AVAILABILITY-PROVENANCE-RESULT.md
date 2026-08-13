# Handoff

from: Codex / Corporate Action PIT Availability Provenance V1
to: ChatGPT independent review
task_id: IDX-CORPORATE-ACTION-PIT-AVAILABILITY-PROVENANCE-V1
model_used: gpt-5.6-luna
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `5222af3b68bf86765c43017912e990edf02148ad`
branch: `data/corporate-action-pit-availability-provenance-v1`
head_commit: `4c7df4d27b7fffc07be9e1c5b6a2ad6ded3b64e2`

## Scope

Semantic remediation and bounded official KSEI availability-provenance audit.
No market-wide corporate-action table, session mapping, OHLC adjustment,
features, models, outcomes, Foreign Flow, Financial PIT, AKSes, O2, or forward
runtime changes.

## Files changed

- `src/idx_trade/corporate_action_pit_linkage.py`
- `src/idx_trade/corporate_action_pit_documents.py`
- `tests/test_corporate_action_pit_linkage.py`
- `tests/test_corporate_action_pit_documents.py`
- `docs/checkpoints/2026-08-14_CORPORATE_ACTION_PIT_AVAILABILITY_PROVENANCE_RESULT.md`
- this handoff

## External evidence

Runtime root:
`D:\Documents\Project\idx-corporate-action-pit-availability-20260814-v1-final`

Manifest SHA-256:
`c8f8639b2d076fd91cb684925c6a0c6c13d2e3ed87a2e7a2fc0da8cad69a39f7`

Parent manifest SHA:
`d44b9362909f5c05d8412ff07ca4c5616a74b43930bd1caf92242ed25b5e10cf`

Linkage manifest SHA:
`1db444f6ceb815bdc29f1f80c8158c7a2050ebf7a5fe0ec0c4230e65940bb195`

## Findings

- 34 official PDF records audited; 34 PDF byte captures valid.
- 16 strict terminal filename timestamp candidates; 18 generic filenames.
- 14/16 candidate dates equal source date; 2 are later; 0 earlier.
- YOII KSEI-16506/JKU/0626 is a five-day candidate-vs-table/PDF-date
  counterexample.
- 14/14 comparable candidates are within 60 seconds of HTTP Last-Modified
  local time, but that is not a first-public-availability proof.
- No exact KSEI-to-IDX timestamp linkage was established in this bounded run.
- MEGA base/follow-up revision lineage remains independently retrievable and
  append-only.

## Decision

`KSEI_ASSET_TIMESTAMP_CANDIDATE_ONLY`

KSEI is useful for discovery and bounded event evidence, not canonical PIT
availability yet. Generic filenames and source dates remain fail-closed.

## Validation

- Focused corporate-action tests: 28 passed.
- Full pytest: 72 passed, 1 pre-existing unrelated storage assertion failed.
- `git diff --check`: PASS.

## Blocking risks / next review questions

- Public schedule/search pages did not demonstrate target-family coverage over
  three calendar years; no 2025 completeness claim.
- Filename/Last-Modified semantics need an independent official contract or
  deterministic IDX linkage before PIT promotion.
- The full-suite storage failure is outside this lane and remains untouched.

## Recommended next action

Independent ChatGPT review. Keep this lane at `REVIEW`; do not begin session
mapping, canonical acquisition, OHLC adjustment, or feature/model work based on
these candidates.
