# Claim — V4-X1 Clean Prospective Score V1

Date: 2026-08-20 (Asia/Jakarta)
Status: `ACTIVE_PREPARATION`
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

Canonical `main:coordination/TEAM_STATUS.md` was read before preparation. No duplicate `ACTIVE` owner for this clean successor scope was present. The canonical shared ledger is too large to safely replace from a truncated connector read; local deployment must update only this lane before any runtime mutation.