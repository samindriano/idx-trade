# V4 CA Residual Document Continuity Replay V1 — Result

Status: `REVIEW`

## Scope and immutable preflight

- branch: `data/idx-v4-ca-residual-document-continuity-replay-v1`
- execution HEAD: `ef1beef0f3b91f15772c10b5dbf44756c5399788`
- parent result present: `67fc2c7f3bef7feee4c95890ea4c074ffb373712`
- Stage-A rerun: `NO`
- provider calls: `0`
- source/config patch: `NO`

Exact preflight passed:

- promoted prior event evidence SHA: `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`
- Stage-A manifest SHA: `6f2070dbd89307c39579aa9617807c2c8ae746390466476f29504b31ae4988a5`
- continuity ledger, KSEI census root, and official calendar: present
- fresh output root: absent before run

## Stage-B result

Exactly one Stage-B offline replay completed successfully using the corrected,
hash-pinned repository event evidence. Final verdict:

`V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`

| Measure | Result |
|---|---:|
| Frozen tickers | 610 |
| Frozen rows | 344,790 |
| Frozen dates | 600 |
| Relevant event rows | 80 |
| Exact-transition events | 42 |
| Schedule-required events | 38 |
| Schedule-required tickers | 34 |
| Coverage-certified tickers | 567 |
| Coverage-unresolved tickers | 43 |
| H5 dates at `>=90%` | 0/600 |
| H10 dates at `>=90%` | 0/600 |
| Consensus dates at `>=90%` | 0/600 |
| Corporate-action continuity certified | `false` |

Minimum per-date rates:

- H5: `0.8237179487179487`
- H10: `0.821656050955414`
- consensus: `0.821656050955414`

Stage-A evidence copied into the continuity overlay:

- exact non-blocking events: `22`
- exact transition events: `1`
- conflict events: `0`
- unresolved events: `38`

Continuity status counts:

| Status | Rows |
|---|---:|
| `RESOLVED_NO_MECHANICAL_DISCONTINUITY` | 292,467 |
| `PRICE_CONTINUITY_UNRESOLVED_COVERAGE` | 29,084 |
| `PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE` | 23,239 |

The full continuity ledger remains external; it is not committed.

## Hashes

External output root:
`D:\Documents\Project\idx-v4-ca-residual-document-continuity-20260818-v2`

Input hashes:

- continuity ledger: `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`
- prior event evidence: `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`
- schedule evidence: `6be49b4fc8a930c9bc61fde64a0652a7cb6233459f5a2e140cb4b4ad0f56592e`
- KSEI history: `3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d`
- official calendar: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

Output hashes:

- `MANIFEST.json`: `89c3bcf45d115d1ae0f8e6cc9ac4cb8e11672d56220f08ded34c39347fcb0827`
- `summary.json`: `034068663da617359baf7a8bdbcc9efbe1576b303bcd5af8e2ff99c2135fa9d5`
- `event_semantics_audit.csv`: `7e65afe9993988555ea1c2398d431d88bb60da770072a388a74beca4e72b6ebe`
- `schedule_evidence_needs.csv`: `81aa0f9b18ba90cead2e8e9fde3ccfa0b9fa19d28ccc2ed7d1e061ea4addaece`
- `v4_frozen_continuity_per_date_event_window.csv`: `2a014541751563b4de630bd48de7e2492fd7392c9d4e2ab49d7e90c1dedd99cd`
- `residual_document_continuity_overlay.json`: `440cec0515b3d5222fab6d53b2a87fd4a001873e8676840e62b74bb843b26f7f`
- external full ledger: `585a9c55b200b2fe8e7b8d4a7f0453c3fdc1d659c666b036bbdec797c04ec634`

No R5/R10, target/rank, model, prediction, performance, protected outcome, or
fresh-forward access occurred. Stop for ChatGPT review.
