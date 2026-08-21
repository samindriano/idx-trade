# Stockbit Stream V2 Red-Team Remediation — 2026-08-21

Status: `CODE_SIDE_REMEDIATION_COMPLETE_CLOUDFLARE_STORAGE_POLICY_DEFERRED`

Branch: `audit/stockbit-stream-v2-red-team-v1`

Scope is acquisition/archive infrastructure only. No model, sentiment fit, target, outcome, O2, V4-X1 forward counter, or local runtime was accessed or mutated.

## Why this audit exists

The initial live GitHub Actions → Zapi → private R2 smoke proved only the happy path. Before promotion, an independent adversarial review attempted to falsify the data-integrity, PIT, retry, quota, storage, workflow-security, and capture-design assumptions.

PR #35 must not be promoted in its original form. The hardened implementation in this audit branch supersedes its unsafe assumptions pending review/promotion.

## Confirmed failures found and remediated

1. Incomplete IDX stock-summary pages could influence the top-N universe. Now fail closed unless `recordsTotal == recordsFiltered == len(data)`.
2. Duplicate provider StockCode rows were silently tolerated. Now fail closed.
3. Non-finite, negative, or impossible `Value` / `NonRegularValue` inputs could corrupt activity ranking. Now rejected from ranking; impossible `NonRegularValue > Value` is rejected.
4. Partial Stream failures could still report `DATA_READY`. Status is now `DATA_READY`, `DATA_PARTIAL`, or `DATA_FAILED` from actual successful/planned calls.
5. All Stream failures could still report `DATA_READY`. Now `DATA_FAILED`.
6. Post-capture quota telemetry failure could orphan a successful/partial attempt. It is now best-effort telemetry and terminal evidence is still written with `quota_after_error`.
7. Same logical-slot retries could poison immutable paths. Logical slot and immutable attempt identity are now separate; each retry has a distinct attempt ID.
8. R2 collision verification trusted object SHA metadata. A 412 collision now verifies the actual existing object body hash.
9. Wrong/missing Stockbit provider provenance could be accepted. Production V2 uses `V2ZapiClient`, which validates provider provenance and fails closed.
10. PIT availability timestamp was taken before response receipt. V2 timestamp is now taken after the HTTP response returns.
11. Malformed identity tickers could reach provider access. Identity validation now happens before provider access.
12. Identical provider bytes re-observed later could collide because normalized bytes include observation time. Distinct immutable attempt identities make re-observation recoverable.
13. Arbitrary slot names were accepted. V2 accepts only `pre_open`, `midday`, and `after_close`.
14. Repository secrets were exposed job-wide. Secrets are now scoped only to the capture step.
15. Production GitHub Actions used mutable major-version tags. Production and red-team actions are pinned to full commit SHAs.
16. Serial capture followed liquidity/activity rank, creating a possible `activity_rank ↔ observation_time` confound. Capture order is now deterministic but de-biased with `SHA256(capture_date | slot | universe_sha | ticker)`.
17. Same logical-slot retries need the same de-biased ordering. The ordering material excludes attempt ID, so retries are stable.
18. Observation-window skew was not observable. Manifest now records capture-order index, first/last observed timestamps, observation span, and attempt duration.
19. Prior-session lookup burned calls on known weekends. Saturdays/Sundays are skipped before provider access.
20. Identity-roster age was not explicit. Runtime universe now records identity source SHA, roster as-of date, age, and status.
21. Production runner initially did not wire the manifest roster as-of date into the runtime. It now consumes `derivation.as_of_panel_date` from the hash-verified universe manifest.
22. A stale identity roster could otherwise run indefinitely. Production runner now fails closed once roster age exceeds the frozen 35-day maximum.

## Additional hardening

- Identity CSV is verified against its pinned manifest before runtime selection.
- R2 hardened data uses a separate `stockbit-stream-v2-hardened` prefix.
- Manual `top_n` is bounded to 1..200 in the production workflow.
- Capture request exceptions are terminally recorded instead of deleting the evidence of the whole attempt.
- Raw and normalized observations remain append-only at the application layer.
- Normalized observations retain global `post_id`, `requested_symbol`, content hash, author pseudonym, mentioned tickers, and observed availability. This intentionally preserves cross-symbol re-observations; downstream sentiment/alpha aggregation must deduplicate globally by source + post identity before counting unique posts.

## Verification

Code/CI checkpoint: `54b4ed8d72a7f2f03f8cc3521e99be0b90c14441` plus subsequent documentation-only trigger updates.

Dedicated GitHub Actions red-team run:

- Run: `32453755923`
- Result: SUCCESS
- Adversarial suite: **26 passed / 26 total**

Repository-wide pytest on the same hardened code:

- **72 passed**
- **1 skipped**
- **1 failed**
- Sole failure: `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
- The remaining failure is pre-existing/unrelated to Stockbit and is outside this lane. The earlier Stockbit legacy-order failure was remediated and no Stockbit test remained failing.

## Deliberately deferred / not code-side defects

### Cloudflare/R2 storage-policy enforcement — deferred by user

Application code now uses conditional immutable writes and verifies collision bodies, but storage-account policy is a separate control. Bucket Lock / retention policy and least-privilege R2 token scope are intentionally deferred for a later Cloudflare review. Do not claim storage-layer WORM/retention until verified.

### Exchange-holiday admission

The workflow is weekday scheduled and the universe lookup skips deterministic weekends. No guessed holiday list was added because no canonical future official-session calendar is committed in this lane. This is not treated as a capture-integrity defect: Stockbit community observations on an exchange holiday remain valid prospective source observations. Any downstream market-session research must admit observations only through the authoritative official session calendar, so weekday scheduling must never be interpreted as an official-session guarantee.

### Cross-symbol duplicates

The archive intentionally preserves re-observations from multiple requested symbols. They share the global Stockbit `post_id`; acquisition must not delete provenance. The required deduplication boundary is downstream unique-post aggregation (`source + post_id`), before sentiment/alpha counting. This audit therefore does not destructively deduplicate raw/normalized archive observations.

### Observation-span threshold

The manifest now measures observation span. No arbitrary maximum span was introduced without empirical live timing evidence. Any future bounded timing gate must be preregistered before seeing alpha/outcome results.

## Promotion rule

All confirmed code-side findings from this red-team exercise are remediated and covered by the adversarial gate. Do not merge original PR #35 as-is. Review/promote the hardened implementation instead. Before a stronger storage-layer immutability claim, separately verify the deferred Cloudflare storage policy. No historical backfill, sentiment fit, model selection, or outcome evaluation is authorized by this checkpoint.
