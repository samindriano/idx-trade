# ChatGPT / Codex work division

Date: 2026-08-10 (Asia/Jakarta)

This is the default operating rule for `idx-trade` unless the user explicitly overrides it.

## Default ownership

The parent ChatGPT conversation is the primary architect, implementer, reviewer, and integrator for work that can be completed through repository/web/connector access.

ChatGPT should, by default:

- inspect repository state and existing evidence;
- design the research/data/validation contract;
- write and edit repository code, tests, specifications, checkpoints, handoffs, and PR metadata directly when the required files are accessible here;
- perform web/source research and methodology review;
- decide bounded next actions and guardrails;
- review Codex runtime results independently before authorizing the next stage.

Do not delegate implementation to Codex merely because Codex is available when the same implementation can be completed safely from the parent ChatGPT conversation.

## Codex role

Codex is primarily the local-runtime executor/verifier for work that requires access unavailable to the parent conversation, including:

- local `D:\` runtime datasets and artifacts;
- Windows Task Scheduler, shell/environment configuration, and local filesystem state;
- secrets/API keys that must remain local;
- long-running full-panel/full-universe executions;
- local wall-clock/memory benchmarks;
- reproducibility checks against the exact local environment;
- bounded debugging that depends on local-only behavior.

Preferred flow:

`ChatGPT designs + implements in GitHub -> Codex pulls/runs locally -> Codex reports factual artifacts/hashes -> ChatGPT independently reviews -> ChatGPT implements the next change`

Codex should not independently redesign methodology, relax frozen gates, choose new sources/features/models, or broaden scope unless the parent ChatGPT explicitly authorizes that exact task.

## Exception

If a bug or implementation issue can only be understood through the local runtime, Codex may make the smallest bounded local fix needed to diagnose it, but should stop and return the diff/results for ChatGPT review rather than expanding the design on its own.

This rule supplements, and does not weaken, all existing research, data-provenance, holdout, execution-grade, and no-main-merge guardrails.
