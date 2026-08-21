# IDX Stockbit Stream Prospective Archive V2 — Handoff

owner: ChatGPT/Stockbit-Stream-Red-Team  
status: `CODE_SIDE_RED_TEAM_REMEDIATED_CLOUDFLARE_POLICY_DEFERRED`

## Decision

The original V2 happy-path smoke is **not** sufficient promotion evidence. Independent red-team testing found multiple fail-open, retry, provenance, PIT-timestamp, storage-collision, workflow-secret, and capture-order defects. Those code-side defects are remediated on `audit/stockbit-stream-v2-red-team-v1` and covered by a dedicated adversarial gate.

Do **not** merge PR #35 in its original form. Review/promote the hardened implementation instead.

The 963-ticker bootstrap remains noncanonical census/bootstrap evidence only. Do not delete it and do not schedule V1 again.

## Hardened runtime

- workflow: `.github/workflows/stockbit-stream-prospective-capture.yml`
- runner: `scripts/run_stockbit_stream_capture_v2.py`
- capture implementation: `src/idx_trade/stockbit_stream_capture_v2.py`
- V2 provider primitives: `src/idx_trade/stockbit_stream_v2_primitives.py`
- identity whitelist: `config/stockbit_stream_universe_v1.csv`
- identity manifest: `config/stockbit_stream_universe_v1.json`
- hardened storage prefix: `stockbit-stream-v2-hardened`
- red-team checkpoint: `docs/checkpoints/2026-08-21_STOCKBIT_STREAM_V2_RED_TEAM_REMEDIATION.md`

Nominal schedule (Asia/Jakarta): `08:47`, `12:07`, `16:47`, Monday-Friday. This is a weekday scheduler, not an official-session guarantee. Downstream market-session research must use the authoritative exchange-session calendar.

## Frozen acquisition rule

Routine selection is top 200 active pinned identities by the prior completed IDX-session regular-market traded value:

`regular_value = Value - NonRegularValue`

The source page must be complete (`recordsTotal == recordsFiltered == len(data)`), provider rows must be unique by StockCode, numeric fields must be finite and internally valid, and identity CSV bytes must match the pinned manifest.

The manifest's `derivation.as_of_panel_date` is wired into runtime provenance. Production fails closed if the identity roster is older than 35 days.

## Capture/PIT semantics

- valid slots only: `pre_open`, `midday`, `after_close`;
- provider availability time is recorded **after** HTTP response receipt;
- production V2 verifies Stockbit provider provenance;
- serial request order is deterministic but deliberately de-correlated from liquidity rank using `SHA256(capture_date | slot | universe_sha | ticker)`;
- each logical slot may have multiple immutable attempts; retries do not reuse poisoned object paths;
- manifest records capture-order index, attempt duration, first/last observed time, and observation span;
- partial/all failures are `DATA_PARTIAL` / `DATA_FAILED`, never silently `DATA_READY`.

## Storage semantics

Application-layer writes use conditional immutable PUT semantics. Normal writes avoid read-after-write. On an existing-key 412 collision, the hardened implementation reads and hashes the **actual existing object body**; it does not trust mutable object metadata as the integrity oracle.

Raw and normalized observations preserve re-observations. A Stockbit post's global `post_id` is retained; downstream unique-post sentiment/alpha aggregation must deduplicate by `source + post_id` rather than destructively deleting acquisition provenance.

Cloudflare Bucket Lock / retention policy and least-privilege token scope are a separate storage-account control and are intentionally deferred by the user. Do not claim storage-layer WORM until that review occurs.

## Verification

Original bounded live smoke (historical happy-path evidence only):

- run `32450648278`, job `96678410979`;
- source session `2026-08-20`;
- top 5;
- 5/5 Stream responses OK;
- 150 normalized observations;
- manifest SHA-256 `0d9e4ccc3ea224aeae5e396f86d627f64fe6708e06d35c7907df1157c2118bbe`.

Final red-team evidence on hardened code:

- run `32453947316`;
- **26/26 adversarial tests PASS**;
- repository-wide pytest: **72 passed, 1 skipped, 1 failed**;
- the sole repository-wide failure is pre-existing and unrelated: `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`.

No Stockbit test remained failing.

## Scientific boundary

No model fit, sentiment scoring, target/outcome access, IC calculation, O2 access, V4-X1 forward-counter mutation, or local runtime/scheduler mutation was performed by the red-team remediation.

## Remaining action

1. Keep original PR #35 on hold / superseded.
2. Review the hardened PR #36 lineage and promote the hardened implementation rather than the original V2 assumptions.
3. Later, perform the explicitly deferred Cloudflare Bucket Lock / retention / token-scope review before making a storage-layer immutability claim.
4. Do not authorize sentiment fitting, alpha selection, or outcome evaluation merely from this acquisition checkpoint.
