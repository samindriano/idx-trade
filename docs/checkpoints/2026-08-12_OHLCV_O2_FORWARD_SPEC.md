# OHLCV O2 — Frozen Fresh-Forward Scoring and Validation Specification

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-forward-v1`
Parent independent-review commit: `aee7f597a927a2679b8d4e38a9deeba857dcf508`
Decision: `O2_FRESH_FORWARD_CONTRACT_FROZEN_IMPLEMENTATION_AUTHORIZED`

## Candidate identity

Frozen challenger:

`O2-GEOMETRY-FULL3-V1-CANDIDATE-001`

Required final model SHA-256:

`42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb`

Required final-refit artifact manifest SHA-256:

`a7045257aa85c9d1020d3fe4ceb60a1ee100aadc827305ddf5c608a616adc2d3`

Feature-order SHA-256:

`a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`

The candidate remains a historical-development challenger until this independent forward gate is completed and reviewed.

## No-backdating rule

O2 official fresh-forward evidence begins only with the first official IDX signal session whose market session starts strictly after the parent final-refit independent-review freeze commit above.

Sessions occurring before that freeze must not be retroactively counted toward O2 certification, even though their outcomes were not inspected.

Resolve the first eligible session from the frozen official exchange calendar. Do not hard-code a date if the calendar says otherwise.

## Gate length and sealing

The official gate is exactly `100` consecutive eligible official signal sessions.

For a session to count:

1. the official session is in the frozen calendar;
2. the post-close feature snapshot is generated under the frozen model-safe/PIT contract;
3. the O2 score ledger is persisted and hash-manifested before any corresponding H10 outcome is opened for evaluation;
4. the exact scored row identities and feature/data provenance are persisted;
5. no model or eligibility rule has changed.

A missing official session may not be silently skipped. If a required score artifact was not safely frozen before outcome access/maturity, fail closed and record the gap; do not reconstruct it later and pretend it was prospective.

No forward outcome may be inspected, summarized, scored, or used for adaptation during accumulation. Maturity can be determined from the official calendar alone without reading outcome values.

The gate becomes evaluation-eligible only after all 100 frozen signal sessions have H10 matured.

## Daily scoring contract

Score only after session-t close.

Use:

- the frozen O2 final model above;
- canonical V3-B 33 causal features under the existing PIT/universe contract;
- exactly `open_position`, `open_to_high`, `open_to_low` appended in frozen order;
- valid session-t Open/High/Low from the certified model-safe forward snapshot;
- no synthetic Open or geometry fill.

A ticker/session with missing or invalid required geometry is O2-ineligible for that session.

The scoring runtime must consume already-certified data artifacts and must not directly call providers or repair historical Open.

Persist immutable per-session artifacts containing at least:

- session identity/calendar index;
- candidate/model hashes;
- feature-contract hash;
- ticker row identities;
- O2 raw score;
- eligibility/exclusion reason;
- input/provenance hashes;
- generation timestamp and artifact hashes;
- explicit `outcomes_accessed=false` marker.

## Paired frozen V3-B baseline

For scientific attribution, also produce a read-only score from the frozen canonical V3-B final model on the exact O2-eligible rows for each forward session.

This parallel baseline does not reset, modify, shorten, or replace canonical V3-B's already-running official forward gate. It exists only to enable apples-to-apples O2-vs-V3-B comparison on identical forward rows.

The V3-B model artifact/manifest identity must be resolved from the existing canonical frozen manifest and hash-pinned before the first O2 forward score is accepted.

Do not refit or recalibrate V3-B.

## Frozen final evaluation

After all 100 sessions have matured, and only in a separately authorized outcome-opening runtime, evaluate O2 versus the frozen V3-B baseline on exact common-forward support.

Primary evidence:

- aggregate PR-AUC for O2 and V3-B;
- paired aggregate PR-AUC delta `O2 - V3-B`;
- PR-AUC minus prevalence;
- ROC-AUC;
- Q5-Q1;
- top-decile lift;
- exact eligible/scored row counts and coverage.

Temporal robustness must be reported on four chronological non-overlapping 25-session blocks, frozen now before outcomes are observed.

`O2_FORWARD_PASS` requires all of:

1. aggregate paired PR-AUC delta > 0;
2. median of the four 25-session block paired PR-AUC deltas > 0;
3. at least 3 of 4 chronological blocks have positive paired PR-AUC delta;
4. no clear aggregate ranking guardrail reversal, defined as both aggregate ROC-AUC and aggregate Q5-Q1 below V3-B on common-forward support.

Otherwise the decision is `O2_FORWARD_FAIL`.

No post-hoc threshold, block redefinition, regime exclusion, provider exclusion, recalibration, or feature change is allowed after outcomes are opened.

Secondary diagnostics may report O2 coverage and standalone performance, but they cannot rescue a failed frozen paired decision.

## Relationship to canonical V3-B forward gate

Canonical V3-B's existing protected forward program remains fully independent and unchanged. Do not inspect its sealed outcomes or use them to alter O2.

O2 starts its own no-backdated 100-session gate under this contract. The two programs may overlap in calendar time, but their certification counters and authorization boundaries remain distinct.

## Implementation authorization now

Authorized in this branch before the first score:

- implement the forward-scoring runner/ledger;
- resolve and hash-pin canonical V3-B baseline artifacts;
- validate contract enforcement with synthetic/unit fixtures or already-public historical fixtures that are not part of the protected forward gate;
- produce a readiness checkpoint and tests.

Not authorized now:

- open any protected forward outcome;
- backfill pre-freeze sessions into the official O2 counter;
- retrain/tune/calibrate either model;
- change features/universe/eligibility based on forward observations;
- execution/PnL, Path Risk, probability/payoff/reliability, paper/live, or broker work.

After implementation, STOP for independent review before counting/scoring the first official O2 session if the runner has not already been explicitly reviewed as ready.
