# V4-3 CA Schedule-59 KSEI News Adjudication Closure

Date: 2026-08-19
Branch: `research/idx-ranking-v4-3-ca-schedule59-news-adjudication-v1`

## Status

`V4_3_CA_SCHEDULE_59_KSEI_NEWS_ROUTE_CLOSED_NO_ADMISSIBLE_EVIDENCE`

This checkpoint freezes the result of the secondary official-KSEI News acquisition and its offline semantic adjudication. The route is closed for this generation. Do not retry provider calls, relax parser/linkage rules, or rerun a combined continuity replay merely to reproduce an unchanged state.

## Immutable acquisition evidence

- Acquisition root: `D:\Documents\Project\idx-v4-3-ca-training-domain-schedule59-ksei-news-20260819-v1`
- Acquisition manifest SHA-256: `96c11caa6ed728cbd19af8f13cc30bedde45c04e7a256e6d0c9a591dd62fc7d1`
- Successful raw response identity SHA-256: `45132e0b5ae17b74ee005c55d26ddb464bdd5bb692b4a3a62d6649189f7ff7a8`
- Frozen residual events: 59
- Residual event identity SHA-256: `f1c587eca59a9e7ec68cb8b1b2fc0980489a8f8a1b608f10403f2cc9f6d85707`
- Search queries: 227
- Failed search queries: 159
- Search parse failures: 0
- Pagination-truncated queries: 6
- Unique KSEI News results/articles requested: 1,114
- Events with KSEI News candidate: 56/59
- Events with ticker-evidenced News: 56/59
- Provider-failed News articles: 4
- News parse failures: 0
- Attachments requested: 1; provider-failed attachments: 1

No target, model, prediction, performance, or protected-forward access occurred.

## Immutable offline adjudication evidence

- Adjudication root: `D:\Documents\Project\idx-v4-3-ca-training-domain-schedule59-ksei-news-adjudication-20260819-v1`
- Adjudication manifest SHA-256: `cda56ccd03949aa2f95030179e14ee07328072b1ed59b6b7845b9e2257e07c76`
- Verified successful raw News documents: 1,110
- Frozen event-News links: 1,815
- Parsed unique event-News links: 1,756
- Missing raw candidate links: 6
- Exact transitions: 0
- Exact non-blocking events: 0
- Conflicts: 0
- Resolved events: 0
- Unresolved events: 59/59

No network/provider calls occurred during adjudication. No target, rank, model, prediction, performance, or protected-forward access occurred.

## Why a combined replay is intentionally skipped

The existing schedule replay helper changes a parent `SCHEDULE_REQUIRED` event only for `EXACT` or `EXACT_NON_BLOCKING` evidence. `UNRESOLVED` evidence executes `KEEP_UNRESOLVED`; `CONFLICT` fails closed.

The News adjudication produced:

- `EXACT = 0`
- `EXACT_NON_BLOCKING = 0`
- `CONFLICT = 0`
- `UNRESOLVED = 59`

Therefore overlaying this adjudication onto the already executed schedule-80 replay is a deterministic semantic no-op. A new full continuity replay would reproduce the prior actual replay state and add no scientific information.

The authoritative prior actual replay remains:

- Root: `D:\Documents\Project\idx-v4-3-ca-training-domain-schedule80-replay-20260819-v1`
- Manifest SHA-256: `aaaa39d5cb1da709c1c9f2214ea3c7955df29b4148899dff865ea3cc8e970810`
- Adjudication resolved: 21/80
- Schedule-required residual: 59
- Frozen H5 minimum support rate: `0.8347457627118644`
- Frozen H10 minimum support rate: `0.831275720164609`
- Frozen consensus minimum support rate: `0.831275720164609`
- Frozen 600 fully eligible: false
- Tail-600 identity unchanged: false
- Full eligible sessions H5/H10/consensus: 0/0/0
- All fold/head training sets non-empty: false

Thus the frozen 0.90 target-support gate remains failed and historical model execution remains unauthorized for this generation.

## Scientific interpretation

The KSEI News route had high retrieval recall but zero admissible semantic yield under the already-frozen exact linkage contract. This is evidence that the blocker is not simple document discovery. The remaining 59 events lack the combination required by the preregistered rules: exact event identity, compatible family, source-date linkage, and explicit official regular-market Ex / first-new-basis transition (or exact voluntary cash identity for non-blocking treatment).

No parser/semantic relaxation is authorized after observing this corpus. Record or distribution dates remain linkage-only and must never be used as transition fallbacks.

## Decision

For the current V4-3 generation:

1. Do not rerun KSEI News acquisition.
2. Do not run a redundant combined replay.
3. Do not load historical targets or fit the V4-3 model while the 0.90 support gate remains failed.
4. Do not rescue the gate by dropping affected rows/tickers/dates, lowering the threshold, or changing event semantics.
5. Treat this KSEI secondary-evidence path as closed.

A future attempt to make V4-3 executable must be a separately frozen evidence generation using a genuinely different official evidence surface (for example official IDX/issuer corporate-action notices) while retaining exact transition semantics, or a separately preregistered new scientific generation with a different target/data contract. Neither is automatically authorized by this checkpoint.

## Coordination note

Canonical `main:coordination/TEAM_STATUS.md` was re-read before closure. Its visible state remains stale (`Last coordinated update: 2026-08-16 00:08 Asia/Jakarta`) and no overlapping active schedule-59 lane was visible. This checkpoint does not claim that canonical `TEAM_STATUS.md` was edited.
