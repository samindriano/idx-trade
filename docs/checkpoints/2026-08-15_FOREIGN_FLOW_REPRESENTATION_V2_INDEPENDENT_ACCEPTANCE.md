# Foreign Flow Representation V2 — Independent Acceptance

Date: 2026-08-15 (Asia/Jakarta)
Reviewer: ChatGPT/Foreign-Flow-Representation-V2-Review
Reviewed branch: `research/idx-foreign-flow-representation-v2`
Reviewed HEAD: `10a72f25b840d3689e39352c779d95ca33c40f77`
Verdict: `FOREIGN_FLOW_REPRESENTATION_V2_CENSUS_ACCEPTED`

## Decision

The Foreign Flow Representation V2 offline materialization, coverage census, and final distribution/behavior review are accepted as decision-valid outcome-blind research artifacts.

This acceptance freezes the existing V2 representation artifact and its provenance. It does **not** authorize model fitting, scoring, H10 outcome access, feature-subset search, winsorization/clipping, free-float integration, or promotion.

Authoritative external output root:
`D:\Documents\Project\idx-trade-foreign-flow-representation-v2-20260815-001`

Frozen manifest SHA-256:
`4e8e7278b6505a356c2f95c4ac69a47cb4dc91803cc819cf6b0aaafbe34c98dc`

Frozen main feature artifact SHA-256:
`0c2212a166115b2f5b974b93096ea06b222b7451d70fa7d58257a9bed0f7a1f0`

## Accepted evidence

- 1,102,400 rows, 979 tickers, 1,259 feature sessions.
- Flow-through 2021-04-29 through 2026-07-30; feature sessions 2021-04-30 through 2026-07-31.
- 318,592 fully available, 783,240 partial, 568 all-missing rows.
- Exact `feature_session = next_official(flow_through_session)` verified.
- Listing filtering occurs before historical state; the known KOCI pre-listing row is excluded.
- Own-history percentile excludes the current observation.
- Cross-sectional ranks are restricted to reconstructed causal primary-liquid source-session rows.
- Zero duplicate `(ticker, feature_session)` keys and zero infinities.
- Rank distributions are non-collapsed and remain inside `[0,1]`.
- 120-session percentile is non-collapsed: median 0.5000, Q25 0.3083, Q75 0.6750, exact-zero 1.0768%, exact-one 1.0306%.
- Persistence and streak features retain meaningful interior mass.
- Missingness is explicitly partitioned into warm-up, rank-not-applicable, and source-data/invalid categories.

## Heavy-tail review

Raw economic shock features contain sparse extreme tails. The largest absolute one-day observations cluster in names including FUJI, CASA, JGLE, and PSKT. These observations are preserved unchanged.

The tails do not invalidate the representation census:

- `foreign_flow_shock_1` P99 is 1.178470 despite a maximum of 62062.306900;
- `foreign_flow_shock_mean_5` P99 is 0.946044 despite a maximum of 15786.679712;
- `foreign_flow_shock_mean_20` P99 is 0.809857 despite a maximum absolute value near 4,000;
- only 1,301 / 963,971, 1,225 / 930,448, and 1,231 / 870,581 finite observations respectively have `abs(value) > 20`.

These are therefore recorded as explicit tail-risk/data-quality observations, not silently clipped, removed, or tuned. Any future robust transform would be a new preregistered representation, not a retroactive mutation of V2.

## Primary-liquid reconstruction review

No authoritative full-universe stored `universe_primary_liquid` artifact exists in the accepted lineage, so artifact-level full-universe parity cannot be proven directly.

This is not treated as a blocker because the V2 runner reconstruction matches the frozen Clean V2 rule in `research_features.py` at the accepted Clean V2 semantics lineage:

- lookback: 60 official exchange sessions;
- minimum finite/active observations: 20;
- statistic: median `regular_market_value`;
- threshold: IDR 1,000,000,000.

The accepted 292,631-row Clean V2 prepared model-support table overlaps the reconstructed context 292,631 / 292,631 with zero primary-flag mismatches. The remaining limitation is correctly classified as missing full-universe stored-parity evidence rather than a false PASS.

## Scientific boundary

Foreign Flow V1 remains `FOREIGN_FLOW_V1_NO_SURVIVOR`; this acceptance does not reinterpret or rescue that result.

Foreign Flow Representation V2 is a distinct, outcome-blind representation family motivated by economic semantics and the previously identified V1 representation mismatch. No V2 outcome has been observed.

Do not automatically fit all 15 features merely because the representation artifact is accepted. A separate preregistration must freeze the exact challenger feature family, comparator, support, folds, preprocessing, metrics, and no-rescue gate before outcome access.

The active Free Float / Effective Supply source lane must remain separate. Its result should be reviewed before deciding whether the next Foreign Flow alpha preregistration should proceed with the current accepted V2 representation or wait for a separately frozen PIT-safe effective-supply normalization family.

## Final status

`FOREIGN_FLOW_REPRESENTATION_V2_CENSUS_ACCEPTED`

Representation/census lane: `DONE`.
Alpha experiment: **not yet authorized**.
