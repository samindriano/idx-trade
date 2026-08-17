# Ranking V4-3 target / execution freeze — lane claim

Date: 2026-08-17 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-3-target-execution-freeze-v1`
Owner: `ChatGPT/V4-3-Target-Execution-Freeze`
Status: `ACTIVE`
Parent runtime acceptance: `research/idx-ranking-v4-3-prefit-runtime-v1@dead19a31e514770570c8afa9d16b48fcfc4cc91`

## Scope

Outcome-blind implementation and freeze of the exact V4 target-materialization / execution-semantic code contract, using synthetic fixtures only.

Authorized work:

- explicit official-session `t+1`, `t+5`, `t+10` identity handling;
- accepted-Open entry semantics with no synthesis and no `Close_t` fallback;
- fail-closed target observability states;
- explicit forward corporate-action continuity evidence interface;
- target rank transform and consensus construction exactly as frozen by V4-1/V4-3;
- synthetic/adversarial tests;
- hash-pinned execution protocol/checkpoint.

Not authorized:

- materializing historical R5/R10 values or target ranks;
- model fit, prediction, IC, Top30, raw-return performance, or bootstrap result;
- provider/network calls;
- new corporate-action acquisition;
- treating `TanggalPencatatan` as generic market-effective date;
- inferring corporate actions from prices;
- changing V4 target, folds, learner, features, thresholds, Top30, observability gates, or promotion rules;
- accessing protected/fresh-forward outcomes.

## Coordination

Latest canonical `origin/main:coordination/TEAM_STATUS.md` was reviewed before this claim. Existing Corporate Action lanes are bounded source/linkage/review work and do not authorize market-wide acquisition or OHLC adjustment. This lane consumes no CA lane output as a market-wide truth; it only defines the fail-closed target interface needed before a separate continuity-support census.

The canonical TEAM_STATUS row should be synchronized to this lane at the next coordination write; no overlapping implementation lane was found in the latest ledger.
