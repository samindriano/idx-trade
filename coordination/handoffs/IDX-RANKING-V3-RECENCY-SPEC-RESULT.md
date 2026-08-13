# Handoff

from: LOCAL / Codex Luna xhigh
to: MAIN / ChatGPT review
task_id: `RANKING_V3_RECENCY_SPEC_V1`
model_used: Codex Luna xhigh
reasoning_level: xhigh
source_repository: `C:/Users/Sam/OneDrive/Documents/Project/idx-trade`
source_commit: `d91337e30d4da08ef310c9fac05e32d4efbcd4ee`
branch: `research/idx-ranking-v2-spec-v1`
head_commit: `bc39642e4b218d89859564596d6ced427d6ae173`
scope: specification, checkpoint, hypothesis ledger, continuity update, and review handoff only

## files_changed

- `docs/RANKING_V3_RECENCY_SPEC_V1.md`
- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
- `docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_SPEC_FROZEN.md`
- `docs/CURRENT_STATUS.md`
- `coordination/handoffs/IDX-RANKING-V3-RECENCY-SPEC-RESULT.md`

## required_reads_acknowledged

Read before drafting:

- `docs/CURRENT_STATUS.md`;
- `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`;
- `docs/RANKING_V3_RESEARCH_BACKLOG.md`;
- `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`;
- `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
- frozen V2 research and champion/forward specifications;
- V2 model, feature, validation, and metric code;
- `docs/checkpoints/2026-08-10_RANKING_V3_ROADMAP_AUDIT_FROZEN.md`;
- newest V2 forward-spec review checkpoint.

## findings

- The exact V2 champion/control is `HGB_XS_MARKET` with the frozen 25-feature
  order, preprocessing, HGB parameters, score transform, H10 target, and
  causal universe semantics unchanged.
- Discovery is frozen to V2F1-V2F4 with the existing 20-session purge and
  100-session validation blocks.
- V2F5-V2F6 are reserved for one late-development confirmation after a
  discovery winner is frozen; they are not independent validation.
- The only recency variants are official-session half-lives 252 and 504,
  alongside the uniform control.
- Raw weights are `2 ** (-age / H)` with `age = train_end - signal_session_index`.
  Fold-local normalization makes mean weight exactly one and does not apply
  class reweighting.
- Exact V2 fold metrics, paired control comparisons, fixed absolute sanity
  gates, paired promotion gates, late-confirmation gates, kill/diagnostic/
  promotion statuses, and the deterministic tie rule are frozen in the spec.
- The V3 ledger starts with zero evaluated candidates and three pre-registered
  candidate ordinals; no metrics are fabricated.

## decisions_made

- Specification SHA-256:
  `53c5bc3e90af12fea62a73815e1e85352e836d69938ce0e9287437a52c1d58fa`.
- Specification Git blob:
  `b6e055ad4fe5e964e29892ef2bd0d9b8a4921c83`.
- Prepared-cache SHA-256:
  `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`.
- Prepared-cache manifest SHA-256:
  `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`.
- Runtime recommendation acknowledged: one deterministic Python orchestrator
  with bounded workers; profile post-cache stages before concurrency; prove
  reference/optimized equivalence before any outcome-bearing use.

## decisions_needed

ChatGPT/MAIN must independently review the frozen specification and decide
whether to authorize a later implementation/run. This handoff does not grant
that authorization.

## blocking_risks

- No V3 implementation, fit, score, or outcome evaluation is authorized by this
  handoff.
- Reserved post-`2026-07-31` V2 forward outcomes were not accessed.
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written.
- A future run must verify the exact cache/provenance hashes and implementation
  equivalence before scoring.

## validation_run

- `git fetch origin` and `git pull --ff-only origin
  research/idx-ranking-v2-spec-v1` succeeded before drafting.
- `git diff --check` passed for the documentation change set; only normal
  Windows LF/CRLF conversion warnings were emitted during commit.
- No pytest or runtime command was run because this task is specification-only.
- The branch was clean after the specification commit before this handoff was
  added.

## recommended_next_action

Review `docs/RANKING_V3_RECENCY_SPEC_V1.md`, its checkpoint, and ledger. Stop
here. Only a separate explicit authorization may begin V3 implementation or
outcome scoring.
