# Investing Intraday Admission Pilot — Independent Review

Date: 2026-08-13 (Asia/Jakarta)
Reviewer: ChatGPT independent review
Branch reviewed: `data/investing-intraday-admission-pilot-v1`
Reviewed remote HEAD: `27e0b7a1b3f5bb4688efeb585215eb0b6e435ccd`

## Verdict

`PILOT_REJECTED_ACCEPTED_DECISION_VALID`

The bounded Investing.com 1-hour secondary-source admission pilot is accepted as a decision-valid rejection under the preregistered contract. The source is reachable, but this exact acquisition/admission contract does not support secondary historical intraday admission, bulk backfill, canonical-panel integration, Path Risk/O2 work, or protected-outcome access.

No rerun, retry expansion, gate relaxation, or bulk acquisition is authorized by this review.

## Why the rejection is robust

The frozen preregistration requires zero final provider errors; old/mid/recent listed-session coverage of at least 80%/80%/90%; at least 90% of returned session-days with five or more bars; H/L/C exact, volume-near, and canonical-Open exact of at least 90%; and all eras passing.

The runtime misses multiple independent hard gates:

- final provider errors: `58 / 138` logical history pairs, versus required `0`;
- old listed-session coverage: `44.2978%` versus `80%`;
- mid listed-session coverage: `69.6466%` versus `80%`;
- recent listed-session coverage: `52.1739%` versus `90%`;
- mid within-session completeness: `89.0299%` versus `90%`;
- old/mid/recent H/L/C exact: `83.5518% / 83.8806% / 72.0029%`, all below `90%`;
- old volume-near: `59.3564%`, below `90%`;
- overall canonical-Open exact: `70.4996%`, below `90%`.

Therefore the rejection does not depend on any single questionable metric. Even a hypothetical transport-only recovery of the final 403s would not make the observed returned data admission-ready. The recent-era H/L/C fidelity and all three coverage eras independently fail.

The 96 predeclared corporate-action-control comparison rows cannot rescue this decision. Recent H/L/C remains a large independent failure, and all three coverage gates remain failed regardless of those controls.

## Safety / scope review

The implementation is bounded to the frozen 50-ticker sample and three windows, uses at most four workers and one retry, writes artifacts externally, and preserves the canonical panel SHA before/after runtime at:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

The runtime reports zero malformed, duplicate, or off-session structural rejection rows. The external artifact manifest is pinned at:

`2316dd2302451ffb2f5a53fd8ff1f4fcf0296979c81a370c16f94560fc33cc7e`

No evidence in the reviewed diff indicates canonical-panel writes, model work, O2 changes, Path Risk restart, or protected-outcome access.

## Independent engineering findings

Two implementation gaps are real but **non-decision-changing for this completed run**:

1. The runtime script records input SHA-256 values but does not load the frozen JSON contract and fail closed against the preregistered provenance hashes before network acquisition. A future invocation could therefore use different identity/security/calendar/panel inputs while still producing a nominal pilot artifact.
2. The generated summary verdict is fail-open relative to the frozen admission contract: it sets `PILOT_REJECTED` only when final provider errors or structural rejection rows are nonzero. It does not itself enforce the frozen coverage, within-session, H/L/C, volume, Open, unresolved-identity, cross-era, or corporate-action conditions. A hypothetical clean-transport run could therefore receive `PILOT_CONDITIONAL_QUARANTINE_REQUIRED` despite failing hard admission gates.

The focused tests cover normalization, aggregation/parity basics, identity sample invariance, time bounds, and transport headers, but do not cover end-to-end provenance-pin enforcement or final gate/verdict evaluation.

These gaps do not alter this run's result because `58` final provider errors alone force rejection, while several additional frozen gates also fail by wide margins. Since the lane is rejected and closed, rerunning the provider merely to remediate evaluator code is not scientifically justified. If this code is ever reused for a separately preregistered future admission attempt, provenance-pin validation and complete fail-closed gate evaluation must be fixed first and tested explicitly.

## Validation evidence accepted

Reported by the implementation lane:

- focused tests: `8 passed`;
- full pytest: `47 passed, 1 pre-existing failure` in `tests/test_storage.py`;
- `git diff --check`: passed;
- worktree: clean;
- no GitHub combined status checks were present on reviewed HEAD.

This review did not independently execute the local external-data runtime or test suite; it reviewed the pushed source, frozen contract, runtime checkpoint, handoff, branch diff, and reported artifact/test evidence.

## Final boundary

Park this exact Investing secondary-intraday admission path. Do not authorize bulk historical acquisition or a transport/chunking rescue simply to improve gate performance. Reopen only if there is a materially different and preregistered source/acquisition hypothesis that plausibly addresses both reproducibility/coverage and daily-fidelity failures, not merely the 403 transport behavior.
