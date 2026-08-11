# IDX Trade — Mandatory Progress Checkpoint Discipline Reaffirmed

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o1-v1`

## Decision

`MANDATORY_PROGRESS_CHECKPOINT_DISCIPLINE_REAFFIRMED`

IDX-Trade treats GitHub as the project source of truth. Every material research/data/model/architecture/runtime decision or completed progress step must be recorded in GitHub before advancing to the next materially dependent step.

This is a repository-wide operating rule, not a per-chat preference and not something that should depend on conversational memory.

## Required behavior going forward

For every material progress step:

1. preserve the relevant branch/spec boundary;
2. record the factual result, decision, hashes/provenance where applicable, and next authorization boundary in a dated checkpoint or equivalent authoritative repository document;
3. update handoff/status material when the new result changes what a future agent should do next;
4. do not rely on chat history as the only record of project state;
5. when a new chat/session begins, bootstrap from the newest repository checkpoint/status before continuing work.

A branch-local newer checkpoint may supersede an older `docs/CURRENT_STATUS.md` section, consistent with root `AGENTS.md`, but stale central status should be consolidated when practical so repository navigation remains clear.

## Context

Recent Open-backfill, TradingView/Investing diagnostics, Open research coverage gating, and OHLCV O1 specification were individually checkpointed. However, central status consolidation lagged behind those branch-local checkpoints. This reaffirmation closes that process gap: checkpointing is mandatory and automatic for material IDX-Trade progress.

No research semantics, model contract, data artifact, outcome boundary, or authorization is changed by this checkpoint.
