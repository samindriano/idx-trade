# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-STATUTORY-FREE-FLOAT-STATE-CONTRACT-V1-REMEDIATION
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 8e0892f6261b4553965949150df95d689ead1376
branch: data/idx-statutory-free-float-state-contract-v1-remediation
head_commit: pending final commit
scope: contract-correctness remediation only; no historical panel materialization

## Files changed

- `src/idx_trade/statutory_free_float_state.py`
- `tests/test_statutory_free_float_state.py`
- `docs/STATUTORY_FREE_FLOAT_KNOWLEDGE_STATE_CONTRACT_V1_REMEDIATION_ADDENDUM.md`
- `docs/checkpoints/2026-08-16_STATUTORY_FREE_FLOAT_STATE_CONTRACT_REMEDIATION_RESULT.md`
- this handoff

## Findings and decisions

- Cross-source chronology is symmetric. `first_known_*` records the earliest
  selected official evidence and `status_effective_*` records the later
  evidence that changes validation/conflict status.
- Backward-compatible `source_published_at` and `eligible_from_session` are
  first-known aliases, not an LBRE preference.
- Identical cross-source shares remain denominator-eligible.
- Any non-identical cross-source percentages, including within 0.01 pp, set
  canonical `free_float_pct` to `None` while retaining both source values and
  the exact delta. Exactly identical percentages may be canonical.
- Single-source official percentages remain exposed.
- Strict post-publication next-session eligibility, economic-date precedence,
  append-only lineage, conflict fail-closed behavior, positive denominator,
  and exact provenance remain unchanged.

## Validation

- Focused: `python -m pytest tests/test_statutory_free_float_state.py -q` —
  `18 passed, 0 failed`.
- Full suite and `git diff --check` must be recorded here before push.
- No provider/network calls and no protected outcome/model/O2 access.

## Blocking risks

The prior repository-wide baseline contained one unrelated
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
failure because current storage revision auditing returns two independent
conflicts. It is outside this lane and must not be changed here unless the
current full-suite result shows a different, in-scope regression.

## Recommended next action

Independent review of the remediation diff and focused/full validation. Do not
materialize the historical session-state panel until separately authorized.

