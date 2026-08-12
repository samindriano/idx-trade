# OHLCV O2 Forward Resume Fix — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-forward-v1`
Reviewed runtime HEAD: `d6cd040737726aa22a2b0e577fa7cda10ab7d811`
Decision: `O2_FORWARD_INFRASTRUCTURE_ACCEPTED_OFFICIAL_SCORING_AUTHORIZED`

## Review result

The bounded resume blocker identified in the prior independent review is resolved.

Accepted controls:

- persisted session manifests contain a deterministic `manifest_sha256` computed from canonical manifest content excluding the self-referential field;
- existing session artifacts are reloadable only after both parquet data hash and persisted manifest hash verify;
- partial, changed, missing-hash, or hash-invalid session artifacts fail closed without overwrite;
- counter state can be reloaded with frozen schema/session-count/H10 checks;
- counter rewind, first-post-freeze boundary mutation, and same-count last-session mutation fail closed;
- explicit regression tests cover write -> restart/reload -> register and counter persist -> reload -> rewind/boundary rejection;
- official O2 artifacts and counter entries remained zero through this review;
- no provider call, protected outcome access, model change, tuning, calibration, or eligibility-contract change occurred.

The implementation is accepted as ready for official prospective O2 accumulation.

## Authorization

Official O2 forward scoring may begin under the already-frozen contract in `2026-08-12_OHLCV_O2_FORWARD_SPEC.md`.

The first official session must be resolved from the frozen official exchange calendar as the first session whose market start is strictly after the final-refit independent-review freeze. Do not hard-code or backdate a session.

For every official session:

1. score only after that session closes;
2. consume an already-certified post-close snapshot; no direct provider call or data repair in the scoring runner;
3. persist and hash the session score artifact before it can enter the official counter;
4. persist paired canonical V3-B scores only on exact O2-eligible rows;
5. keep `outcomes_accessed=false` and do not inspect any H10 outcome during accumulation;
6. preserve exact consecutive official-session counting and fail closed on gaps;
7. checkpoint material forward progress in GitHub.

This authorization does not permit model modification, retraining, tuning, outcome opening, interim performance evaluation, execution/PnL work, or backdated certification.

## State at authorization

- official O2 score artifacts: `0`;
- official O2 counter entries: `0`;
- protected outcomes accessed: `false`;
- O2 model SHA-256: `42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb`;
- V3-B paired baseline model SHA-256: `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`.

Next action: resolve the first eligible official session from the frozen calendar and, only after that session closes, create the first official O2 score artifact and counter entry. Then checkpoint and stop for review of the first prospective capture.
