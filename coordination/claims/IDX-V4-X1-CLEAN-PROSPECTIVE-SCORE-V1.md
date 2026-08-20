# Claim — V4-X1 Clean Prospective Score V1

Date: 2026-08-20 (Asia/Jakarta)
Status: `WAITING_LOCAL_READONLY_READINESS_R2`
Owner: `ChatGPT/V4-X1-Clean-Prospective-Score`
Branch: `integration/v4-x1-clean-prospective-score-v1`
Base operational lineage: `integration/v4-x1-eod-auto-score-v1`

## Scope

Prepare and freeze the clean V4-X1 fresh prospective score-only capture by reusing the existing canonical EOD + V4-X1 automation path. Do not create a second market-data capture system.

Controlling scientific acceptance:
- Phase-B acceptance commit: `ec9e8dc55ccdf458a67b63f612c8eb06660cf829`
- accepted clean model manifest SHA-256: `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`
- prospective preregistration blob: `f33663bc7e4d14941a12974cc453ab90ac5b85ba`
- acceptance timestamp used as conservative prospective freeze boundary: `2026-08-20T12:08:44Z` (`2026-08-20T19:08:44+07:00`)

Preparation parent:
- checkpoint `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_SCORE_PREPARED.md`
- blob `690e5eb2a3e903b2e1165523c2c363b8bfbfd5ec`

Static-guard remediation:
- first local preflight stopped fail-closed before runtime inspection because a raw substring test rejected the literal manifest safety key `historical_performance_computed`;
- source inspection confirmed the clean scorer only reads that accepted manifest field and requires it to be false; it does not import/reference/call a historical performance evaluator;
- clean scorer blob stayed exactly `f00528422a42835e5a969bfe503e29f91e0bf957`;
- only the static test was changed to an AST/code-symbol guard: `tests/test_v4_x1_clean_forward_score.py` blob `53f2d6648dcde43c765ac754b10c09eeb2f1643d`;
- remediation checkpoint `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PROSPECTIVE_STATIC_GUARD_REMEDIATED.md`, blob `177b95214c49f0c44748389aaef5ef20d3881267`;
- repinned machine contract blob `fbdbed664259cf685a71dbbfebcc38ba7e558c92`;
- R2 handoff `coordination/handoffs/IDX-V4-X1-CLEAN-PROSPECTIVE-READINESS-R2.md`, blob `d734fb4e411d161ae1225311c0ac89e37289096d`.

The machine contract remains `deployment_authorized=false` and `score_capture_authorized=false`. Expected clean counter before deployment remains `0/100`.

## Required scientific invariants

- fresh-only score capture; no historical/pre-freeze backscoring;
- first counter-eligible observation must have both canonical session EOD and canonical DATA_READY completion strictly after the acceptance freeze boundary;
- same-day Jakarta operational anti-backfill rule remains active;
- exactly the accepted clean four-model bundle is used;
- CONTROL 25 features and CHALLENGER 28 features remain unchanged;
- consensus remains 50/50 H5/H10 within-date percentile ranks;
- canonical EOD remains the only provider/capture path;
- score layer itself performs zero provider/network calls;
- no model fit, tuning, historical scoring, outcome access, or performance evaluation;
- forward counter is keyed by the clean model manifest fingerprint and starts independently from zero;
- outcome vault stays locked until the preregistered 100/100 + H10 maturity condition;
- V4-X2 session-aligned semantics are excluded.

## Clean representation migration

- historical feature state must use the accepted Stage-A clean panel, not the legacy historical panel;
- accepted clean security master is the immutable baseline;
- forward security-master additions are allowed only for genuinely post-freeze new listings (`listed_from` strictly after 2026-08-20); existing baseline identities are never rewritten by mutable runtime files;
- candidate-session Geometry3 Open continues to come only from the immutable canonical sibling OHLCV after exact H/L/C/V reconciliation with the model-input snapshot.

Canonical `main:coordination/TEAM_STATUS.md` was read before remediation. Its lane currently records the first fail-closed attempt as `REVIEW`. The next local agent must make the minimal canonical row transition to `ACTIVE` for R2 and back to `REVIEW` afterward, preserving every other row. No canonical overwrite is attempted from this connector because the shared ledger is too large to safely replace from a truncated read.