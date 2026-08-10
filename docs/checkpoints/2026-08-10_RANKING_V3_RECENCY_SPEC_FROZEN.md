# Checkpoint - Ranking V3 Recency Specification Frozen

Date: 2026-08-10 (Asia/Jakarta)

Status: **RANKING_V3_RECENCY_SPEC_FROZEN_BEFORE_OUTCOME_RUN**

## Scope completed

The exact specification for `RANKING_V3_RECENCY_SPEC_V1` is frozen for
independent MAIN/ChatGPT review. This is documentation-only work.

Required reads were completed and acknowledged:

- `docs/CURRENT_STATUS.md`;
- `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`;
- `docs/RANKING_V3_RESEARCH_BACKLOG.md`;
- `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`;
- `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
- frozen V2 research and champion/forward specifications;
- V2 model, feature, validation, and metric implementation;
- newest controlling checkpoint `2026-08-10_RANKING_V3_ROADMAP_AUDIT_FROZEN.md`.

## Frozen choices

- exact control: `HGB_XS_MARKET`, unchanged 25-feature order and HGB pipeline;
- discovery: V2F1-V2F4, with exact 20-session purge and 100-session validation;
- reserved one-time late confirmation: V2F5-V2F6;
- candidates: uniform control plus exactly H=252 and H=504 official-session
  exponential recency variants;
- age: `train_end - signal_session_index`;
- raw weight: `2 ** (-age / H)`;
- normalization: fold-local arithmetic mean exactly one, no class reweighting;
- metrics: exact V2 ranking metrics and paired diagnostics;
- gates: fixed absolute sanity, paired discovery promotion, and one-time
  late-confirmation non-inferiority gates;
- kill/keep/promote verdicts and deterministic tie rule are in the spec;
- ledger: three pre-registered ordinals, zero candidates evaluated at freeze.

Specification artifact:

`docs/RANKING_V3_RECENCY_SPEC_V1.md`

Hypothesis ledger:

`docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`

## Safety result

- no V3 model was fitted;
- no V3 score or outcome evaluation was run;
- no V2 candidate was rerun or retuned;
- no post-`2026-07-31` V2 forward outcome was read or summarized;
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written;
- no Stage 6, `IDX-VAL-002`, probability calibration, execution-PnL,
  paper/live trading, or main merge was started.

## Next action

Stop and return the specification, checkpoint, ledger, and result handoff to
ChatGPT for independent review. A separate authorization is required before
any V3 implementation, fit, or score.
