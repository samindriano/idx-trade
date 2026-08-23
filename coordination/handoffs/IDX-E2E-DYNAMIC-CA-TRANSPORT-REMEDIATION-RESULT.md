# Handoff — E2E Dynamic CA Transport Remediation

from: Codex
to: MAIN / ChatGPT reviewer
task_id: IDX-E2E-DYNAMIC-CA-TRANSPORT-REMEDIATION-RESULT
model_used: GPT-5 Codex
reasoning_level: high
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `91323a9509eda740a6f45294d81c5e0b02c4f34a`
branch: `integration/idx-e2e-baseline-paper-v1`
head_commit: set by the commit containing this handoff

## Scope

Diagnose and remediate the bounded Dynamic CA IDX transport failure without
changing CA semantics, alpha/Decision/Sizing/Execution science, protected
outcomes, or live PAPER state.

## Files changed

- `scripts/capture_forward_ca_idx_bei.py`
- `src/idx_trade/forward_ca_attestation_v1.py`
- `tests/test_capture_forward_ca_idx_bei.py`
- `docs/checkpoints/2026-08-23_E2E_DYNAMIC_CA_TRANSPORT_REMEDIATION_RESULT.md`
- this handoff

Pre-existing user modification intentionally excluded from the commit:
`notebooks/e2e_monte_carlo_v4_x1.ipynb`.

## Findings

The current pinned `idx-bei` client was stateless at the request boundary. The
previous accepted anti-403 transport used a warmed persistent Chrome-
impersonated Session. The bounded live matrix showed transient direct IDX
availability rather than a stable current 403, while the real smoke reproduced
a direct HTTP 503 on `NewsAnnouncement/GetAllAnnouncement`.

Zapi raw passthrough returned the exact three required IDX paths with envelope
`project=finance:idx:raw`, nested `provider=idx`, exact path, and valid payload
schemas. It is admitted only as an IDX transport fallback.

## Decisions

- Keep direct IDX first.
- Use a warmed persistent curl_cffi Session and page-specific Referer.
- Permit exact Zapi raw fallback only after direct transport failure/non-response.
- Reject malformed/invalid direct HTTP 200 without fallback.
- Preserve raw Zapi envelope and normalized artifact separately with hashes.
- Keep `authority=IDX`; no business-level Zapi substitution.

## Validation run

- focused suite: `49 passed`;
- full suite: `706 passed, 0 failed, 3 FutureWarnings`;
- real smoke root:
  `D:\Documents\Project\idx-e2e-dynamic-ca-real-smoke-20260823-v5`;
- phase manifest SHA:
  `7dcb501578eb5dda2f0aee9a8008f5c0eb23fa85a63d7adbeac6bb658bd15535`;
- V1.2 attestation SHA:
  `d27b1a3e49568a9ff7cccc979459672f549dbbdceaeae18ae16964be3b4f6bf2`;
- production phase verifier: PASS;
- idempotency re-entry: stopped with `FORWARD_CA_OUTPUT_EXISTS` before
  provider access; no duplicate publication or artifact mutation;
- no protected outcome access and no live PAPER mutation.

## Decisions needed

1. Independent review of the transport policy and external pin reconciliation.
2. Before the next scheduler cycle, update the external runtime config's
   `expected_commit` and `ca_capture_script_sha256`, refresh its config SHA,
   and update only the `IDXTrade-E2E-Paper` action's config SHA argument.

## Blocking risks

- Direct IDX can still be transiently unavailable; this is why the exact raw
  fallback is retained.
- The real smoke was a bounded historical `POST_EOD` transport validation, not
  a live weekday PAPER execution.
- Only MAIN may update `coordination/TEAM_STATUS.md`; this branch does not
  modify it.

## Recommended next action

Review, push, reconcile the external config/task pin to the final commit, and
then allow the normal weekday E2E scheduler cycle. Do not access protected
outcomes or retroactively create paper execution.
