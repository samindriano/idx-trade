# OHLCV O2 Forward — Flat-Range Contract Review

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-forward-v1`
Controlling frozen spec: `docs/checkpoints/2026-08-12_OHLCV_O2_FORWARD_SPEC.md`
Decision: `O2_FLAT_RANGE_IS_EXISTING_INVALID_GEOMETRY_EXCLUSION_NOT_NEW_SEMANTICS`

## Trigger

The certified 2026-08-12 EOD snapshot contains a set of genuinely traded ticker/session rows with positive official IDX volume/frequency and current Stockbit intraday evidence, but with a fully flat bar:

`open == high == low == close`

For these rows, frozen O2 feature `open_position = (open-low)/(high-low)` has a zero denominator.

No synthetic value, suspension relabel, price-floor exception, or provider repair is authorized.

## Review finding

This case is already covered by the frozen O2 forward contract. The controlling spec states:

- use valid session-t Open/High/Low;
- no synthetic Open or geometry fill;
- a ticker/session with missing or invalid required geometry is O2-ineligible for that session;
- persist exact eligibility/exclusion reason;
- compare paired frozen V3-B only on exact O2-eligible rows.

The accepted forward runtime implements the same rule. `_valid_geometry(...)` requires `high > low`; therefore a true flat-range bar is invalid O2 geometry. `score_forward_session(...)` computes:

`o2_eligible = v3b_eligible & geometry_valid`

and retains invalid-geometry rows as unscored exclusions rather than failing the entire session.

Therefore **no new research-semantic decision is required** and no feature definition may be changed.

## Required handling for 2026-08-12 and future sessions

1. Preserve the certified source OHLCV exactly as observed.
2. Do not define `open_position` for `high == low` by convention (no `0`, `0.5`, carry-forward, epsilon denominator, or other synthetic value).
3. Mark those ticker/session rows `o2_eligible=false` under the existing invalid-geometry exclusion contract.
4. Prefer a precise diagnostic such as `FLAT_RANGE_ZERO_DENOMINATOR` if the integration layer supports more granular exclusion reasons; otherwise the already-frozen `MISSING_OR_INVALID_OPEN_GEOMETRY` reason is sufficient. Diagnostic wording must not alter eligibility.
5. Score O2 and the paired V3-B comparator only on the exact O2-eligible subset.
6. Persist the complete per-session artifact, including excluded rows, exact counts, source/snapshot hashes, model/feature hashes, and `outcomes_accessed=false`.
7. If all other frozen session requirements are met, the official O2 session **may be registered and counted even though some ticker rows are geometry-ineligible**. The frozen gate is session-based; it does not require 100% ticker coverage.
8. Do not change the frozen O2 model, feature order, eligibility semantics, forward start, counter, or protected-outcome boundary.

## Implementation boundary

If the current EOD integration incorrectly treats any flat-range row as a session-fatal blocker, a bounded integration fix is authorized to route those rows through the existing O2 invalid-geometry exclusion path and then persist/register the session normally.

Required tests should include at least one V3-B-eligible flat-range row (`open == high == low > 0`) and verify:

- row is retained in the session artifact;
- `o2_eligible=false`;
- no O2/V3-B paired score is produced for that row;
- non-flat eligible rows still score;
- session artifact remains outcome-clean and immutable;
- counter registration succeeds for the session when all other frozen requirements are satisfied.

This is a contract-alignment/runtime fix, not an O2 research change.
