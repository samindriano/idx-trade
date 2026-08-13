# Clean V2 Open Alpha — Preregistration Remediation

Date: 2026-08-13 (Asia/Jakarta)
Status: **REMEDIATION_COMPLETE_OUTCOME_RUN_STILL_BLOCKED_FOR_REVIEW**
Branch: `research/idx-v2-open-alpha-prereg-v1`
Review input: `review/idx-v2-open-alpha-prereg-v1@1352833`

## Scope

Only the three independent-review findings were repaired. No model fitting,
scoring, target/outcome loading, provider/network call, forward access,
canonical model/counter change, or population redesign occurred.

## Remediation

### Separate candidate identities

The code now pins three distinct executable feature orders:

- CONTROL: exact clean V2 `HGB_XS_MARKET`, 25 features,
  SHA-256 `1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72`;
- V2.1: CONTROL + `open_position`, `open_to_high`, `open_to_low`, 28 features,
  SHA-256 `9bf62fd9fec1edeaebd7b3024512f942fcef9c7d12dd01797f2c2020bf636c34`;
- V2.2: CONTROL + `open_position_prev_active_range`, `open_to_prev_high`,
  `open_to_prev_low`, 28 features,
  SHA-256 `228c3afad2d4f786923c480e9b91be0467a646b08e770097552c8905dd30ff74`.

The 31-feature all-six-Open concatenation is diagnostics-only and marked
`PROHIBITED`; it is not a candidate identity.

### Survivor and winner rule

The frozen gate for each challenger/comparator pair is median paired PR-AUC
delta > 0, q25 paired PR-AUC delta > 0, positive paired folds >= 2, and no
simultaneous candidate-median ROC-AUC and Q5-Q1 reversal. Neither survivor
means `RETAIN_CLEAN_V2`; one survivor is the winner; both survivors trigger
the same gate head-to-head in both directions. If neither direction is the
sole pass, the verdict is `MULTIPLE_SURVIVORS_NO_UNIQUE_CHAMPION`. Selection by
era, aggregate metric, feature importance, or subjective preference is
forbidden.

### PIT ancestor and boolean hardening

V2.2 previous ancestors now require explicit:

- previous listing interval validity;
- official exchange-session identity/date validity;
- previous `ACTIVE` state;
- no regular suspension conflict;
- previous session index strictly before current;
- `signal_session_index == panel_session_index` for every joined row.

External `universe_primary_liquid`, `open_feature_ready`, `open_known`, and
panel `open_available` flags use strict parsing. Text `"False"` is false;
unknown values fail closed.

## Rerun result

External runtime root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\open_alpha_prereg_v1_20260813_remediation1_retry1`.

- common support: **277,244 rows / 729 tickers**;
- common-support key SHA: `e058e5ce4ce650eeab5acd57a7d697c155548e40bbbb8ffe0eab120987d857df`;
- population unchanged from reviewed blind cache;
- all ancestor/session checks: zero violations;
- immutable panel SHA before/after: `6f6e83c229e9d50c5bff5ef02706ffd2ea7f0d08125c0b66326e3c994752789e`;
- audit summary SHA: `82a7814d1ef52776eef0766005468e9297230e89ba13338776cd6324737cc0fb`;
- artifact manifest SHA: `a9ecc02744e815a6581e053422bfc219affd036205e780ad82e9caf36083c247`.

## Validation and stop condition

- focused tests: **9 passed**;
- full pytest: **48 passed, 1 pre-existing storage assertion failure**;
- model fit/score: false;
- target/outcome columns loaded: false;
- provider calls: 0;
- protected outcomes accessed: false.

Stop for independent ChatGPT review and authorization of the single atomic
historical V2 vs V2.1 vs V2.2 run. Do not start that run in this checkpoint.
