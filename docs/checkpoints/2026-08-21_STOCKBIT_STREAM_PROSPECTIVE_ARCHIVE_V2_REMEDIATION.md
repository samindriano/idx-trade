# Stockbit Stream Prospective Archive V2 — Original Smoke Checkpoint

Date: 2026-08-21  
Scope: acquisition infrastructure only  
Status: `SUPERSEDED_BY_RED_TEAM_HARDENING`

> This document records the original V2 happy-path smoke lineage. Its former `READY_FOR_ROUTINE_PROMOTION` conclusion is withdrawn. The canonical code-side review is now `docs/checkpoints/2026-08-21_STOCKBIT_STREAM_V2_RED_TEAM_REMEDIATION.md` on `audit/stockbit-stream-v2-red-team-v1`.

## Original V2 intent

The first cloud bootstrap used the entire 963-ticker prospective identity list for an `after_close` run. That remains useful only as one-time sparsity/census evidence, not recurring coverage. Original V2 moved recurring acquisition toward top 200 by prior completed IDX-session regular-market traded value and reduced the R2 hot path.

Any V1 full-universe objects already written remain noncanonical bootstrap/census evidence. Do not delete them and do not schedule V1 again.

## Original frozen routine universe

The intended rule was top **200** active identities ranked by immediately prior completed IDX-session regular-market traded value:

`regular_value = Value - NonRegularValue`

Expected normal 22-session Stream-call budget remains approximately:

`200 × 3 × 22 = 13,200 Stream calls/month`

Same-run Stockbit activity, sentiment, returns, model scores, targets, O2, and protected outcomes were not used for selection.

## Nominal schedule

- `08:47 WIB` — pre-open
- `12:07 WIB` — midday
- `16:47 WIB` — after close

These are weekday schedule labels. They are not themselves proof of an official IDX trading session.

## Historical happy-path smoke evidence

Temporary validation PR: `#34` (closed without merge)  
Workflow run: `32450648278`  
Smoke job: `96678410979`

Historical result:

- source session: `2026-08-20`;
- selected universe: top 5 for bounded validation;
- planned Stream calls: 5;
- completed Stream calls: 5;
- successful responses: 5/5;
- response classifications: `OK=5`;
- normalized observations: 150;
- run ID: `2026-08-21_observable_validation_c12c95b65481cfa9`;
- universe SHA-256: `c12c95b65481cfa95f23d06dd5fb7bde89eb82eade3dbc0c54817dd4ee1d995a`;
- manifest SHA-256: `0d9e4ccc3ea224aeae5e396f86d627f64fe6708e06d35c7907df1157c2118bbe`;
- no model, sentiment, target, outcome, O2, or forward-counter access/mutation.

This proves only that the then-current end-to-end path could succeed once:

`GitHub Actions -> Zapi IDX universe -> Zapi Stockbit Stream -> private R2`.

It did **not** prove fail-closed behavior, safe retry semantics, conservative PIT timing, capture-order neutrality, secret minimization, or storage-collision integrity.

## Findings that superseded the original promotion conclusion

Subsequent independent adversarial review found, among other issues:

- incomplete stock-summary pages could be accepted;
- duplicate/nonfinite/impossible universe values were not sufficiently defended;
- partial or total Stream failure could still produce `DATA_READY`;
- post-capture quota telemetry could orphan terminal evidence;
- retries could poison immutable paths;
- R2 collision checking relied on object metadata rather than actual existing bytes;
- provider provenance and received-at PIT semantics were insufficiently enforced;
- secrets were job-wide and Actions were mutable-tag pinned;
- serial capture order tracked liquidity rank and could create observation-time confounding;
- identity roster freshness was not wired into production.

These are fixed in the hardened red-team lineage, not in the original smoke conclusion.

## Current canonical status

See:

- `docs/checkpoints/2026-08-21_STOCKBIT_STREAM_V2_RED_TEAM_REMEDIATION.md`
- `coordination/handoffs/IDX-STOCKBIT-STREAM-PROSPECTIVE-ARCHIVE-V2.md`
- PR #36 / branch `audit/stockbit-stream-v2-red-team-v1`

Final hardened red-team evidence reached **26/26 adversarial PASS**. Repository-wide pytest reached **72 passed, 1 skipped, 1 unrelated pre-existing storage failure**. No Stockbit test remained failing.

## Storage statement correction

The old wording that collision verification trusted stored SHA metadata is obsolete and must not be reused. Hardened V2 conditionally writes immutable objects and, on collision, verifies the actual existing object body hash.

Cloudflare Bucket Lock / retention and R2 token-scope enforcement remain explicitly deferred for a later storage-account review. Application-layer hardening is not a claim of storage-layer WORM.

## Scientific boundary

- model fits = 0
- sentiment scoring = 0
- target/outcome access = 0
- IC calculations = 0
- V4-X1 mutation = 0
- O2 mutation = 0
- forward-counter mutation = 0
- existing local EOD/intraday scheduler mutation = 0

## Promotion rule

Do not use this historical smoke checkpoint as authorization to merge PR #35 or activate the original design. Any promotion must use the hardened red-team implementation and its current handoff. Cloudflare storage policy review remains a separate deferred task.
