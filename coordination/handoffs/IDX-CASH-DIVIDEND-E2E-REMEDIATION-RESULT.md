# Handoff: Cash Dividend + E2E Baseline Paper V1 Remediation

from: Codex local implementation
to: ChatGPT / MAIN independent review
task_id: IDX-CASH-DIVIDEND-E2E-REMEDIATION-20260823
model_used: GPT-5 Codex
reasoning_level: high
source_repository: `samindriano/idx-trade`
branch: `integration/idx-e2e-baseline-paper-v1`
source_commit_before_docs: `95c49c0e2107c9be90256cc9ca221a40260cfd3e`

## Scope

Remediate the accepted Decision V2 → Sizing V1 → Execution V1 paper path for
cash-dividend lifecycle safety and restart/idempotency orchestration. Preserve
the frozen model, sizing, execution mechanics, official Open evidence
contract, and protected outcome boundary.

## Files changed

Implementation:

- `src/idx_trade/e2e_paper_orchestration_v1.py`
- `src/idx_trade/forward_ca_attestation_v1.py`
- `src/idx_trade/forward_dividend_disposition_v1_2.py`
- `src/idx_trade/forward_dividend_execution_v1_1.py`
- `src/idx_trade/forward_dividend_orchestration_v1.py`
- `src/idx_trade/forward_dividend_provenance_v1_2.py`
- `src/idx_trade/forward_dividend_runtime_v1_1.py`
- `src/idx_trade/forward_dividend_semantic_review_v1_2.py`
- `src/idx_trade/forward_dividend_v1.py`
- `scripts/run_e2e_paper_post_eod_v1.py`
- `scripts/run_e2e_paper_preopen_v1.py`
- `scripts/run_e2e_paper_deterministic_replay_v1.py`
- `scripts/run_e2e_paper_production_replay_v1.py`

Tests:

- `tests/test_e2e_paper_orchestration_v1.py`
- `tests/test_forward_dividend_disposition_v1_2.py`
- `tests/test_forward_dividend_execution_v1_1.py`
- `tests/test_forward_dividend_semantic_review_v1_2.py`
- `tests/test_forward_dividend_v1.py`

## Findings addressed

1. Cross-announcement same-event identity now needs explicit lineage or
   multi-document proof; prior payment is not enough.
2. Numeric semantic review rejects ambiguous comma/dot forms rather than
   guessing units or scale.
3. V1.2 review and attestation are POST_EOD-only and journal-bound.
4. Required CA scope is derived from the verified Decision V2 plan and the
   complete current paper state, including pending intents.
5. Certified event registry persistence prevents a later no-event capture
   from erasing an earlier event.
6. Late-known events require exact historical state at cum date.
7. Receivables affect total-return NAV for sizing but never spendable cash;
   the prepared plan is still tied to the raw state hashes used by execution.
8. T0 and prepared/execute parents fail closed on divergent pre-existing state
   or changed CA journal identity.
9. Timestamp parsing now enforces timezone-aware capture cutoffs and treats
   naive IDX timestamps as Asia/Jakarta before UTC comparison.

## Validation and acceptance artifacts

Focused suite: 83 passed.

Full suite: 656 passed with existing pandas `FutureWarning` warnings only.

Deterministic core replay:

- result: `DETERMINISTIC_CORE_REPLAY_PASS`
- summary SHA-256:
  `d2baa3cb442a0cce5496e33f64325134d90807b6d34d60a3bdf8ed53f1f0d510`

Production-path replay:

- result: `PRODUCTION_PATH_REPLAY_PASS`
- resume probe: `RESUME_PROBE_PASS`
- summary SHA-256:
  `0239538b1f7b35236c4a0318b5e35cb752272e35bbbea2b18291eedcbab1589b`
- five sessions; all `EXECUTION_COMPLETE`;
- provider calls: false;
- protected outcome access: false;
- late correction exercised: true;
- POST_EOD-only CA exercised: true.

## Decisions / boundaries

- No real provider request, scheduler installation, model fit/rescore, target
  access, fresh-forward access, or outcome-vault access was performed.
- The old synthetic replay is not used as final acceptance; the two new replay
  scripts are the acceptance paths because they exercise the actual verifier
  and orchestration entry points.
- Branch status: `REVIEW`; independent review remains required.

## Recommended next action

Independent review should verify the diff and both replay manifests/hashes,
then decide whether to accept the remediation. If accepted, only then should
the branch be considered for live/forward operational continuation under the
already frozen boundaries.
