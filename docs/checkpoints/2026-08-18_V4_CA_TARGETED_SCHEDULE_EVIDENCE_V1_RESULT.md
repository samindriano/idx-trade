# V4 CA Targeted Schedule Evidence V1 — Result

Date: 2026-08-18 (Asia/Jakarta)
Status: `REVIEW`
Branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`

## Validation / execution boundary

The local Windows execution followed the frozen seven-event handoff after the pre-provider pytest import-harness remediation.

Validation before provider access:

- focused pytest: `11 passed`;
- `py_compile`: PASS;
- `curl_cffi`, `lxml`, `pypdf`, `pandas`, `numpy` runtime preflight: PASS;
- `git diff --check`: PASS;
- dedicated worktree clean and synced;
- acquisition and continuity output roots were both absent before the one-shot run.

No source/parser/semantic/threshold/universe change was made after provider result exposure.

## One-shot targeted acquisition result

Frozen selected subset: `NISP, ISAT, ADRO, PANI, RAJA, PTRO, CUAN`.

Result:

- selected events: `7`;
- NISP static target: `1`;
- mechanical schedule targets: `6`;
- candidate documents: `7`;
- index pages requested: `29`;
- provider request-attempt records: `52`;
- exact static non-blocking events: `1`;
- exact schedule transition events: `0`;
- unresolved selected events: `6`.

Only the frozen NISP Voluntary Conversion event resolved through the strict static security-to-currency rule:

`10e24d3621e0f5e65833655b2e11938fc53d64e68c03e6c87658eb74bb2ae26b`.

The six mechanical selected events remained unresolved:

- ISAT `1285d019c8831fae39ad2909e699680df9071d5ebc38701a71a5a5dba951c60d`;
- ADRO `41c1e8493213d0151799837330c0dc7d8fea633d458c03e40b61ea0247bb9e58`;
- PANI `82e09144ecfe0d4375a9260156fe75dd74ed01a2cd72262f55e14cd85ce6ebc7`;
- RAJA `072cf4b8b2f7f86f3c7a55a1128c85f338cbe7b41307b57a3240ad94dba0afae`;
- PTRO `9b21df59be9d68e088059e2dae04d2d0bd8832d9d1cb5e9dd5a300f05f369610`;
- CUAN `6df97832e47c00fc5653e90659f525a5c8258752f9fc2245803498bdeb30b45e`.

Acquisition hashes reported by the frozen runner:

- acquisition manifest SHA-256: `df1455b80c4b5d76d8bde0c23ac992db81fc93373a9a40af18ca29583b94b79b`;
- request records: `5c3b0a4ab897522ee14911018377561137cff5ed36f7399246a23dca989b8df2`;
- targeted event linkage audit: `230c23d4a816ea7782527f8ccd8cc9d75efeaf232349d55ae4a3f84965f0b523`;
- targeted evidence: `d66acd24b3ac990a14e7182eab74720db2527612943b04aac988859f469c4f3d`;
- targeted schedule document parse audit: `62804e90384c15cca466aad5ea0ce850c59454998f66c3ce0aa3a21104859f95`.

The acquisition runner reported `outcome_blind=true`, `target_or_rank_materialized=false`, `model_fit=false`, `prediction_generated=false`, `performance_computed=false`, and `protected_forward_accessed=false`.

## One-shot continuity replay result

The replay completed exactly once without provider calls or intervening patch.

Verdict:

`V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`

`corporate_action_continuity_certified=false`.

Frozen identity remained:

- rows: `344,790`;
- tickers: `610`;
- dates: `600`;
- KSEI coverage-certified tickers: `598`;
- KSEI unresolved tickers: `12`;
- cross-source conflict tickers: `MEGA`, `SCMA`.

Final relevant event semantics:

- relevant events: `82`;
- `EXACT_TRANSITION`: `44`;
- `SCHEDULE_REQUIRED`: `38` across `34` tickers.

Per-date continuity:

| Head | Passing dates / 600 | Minimum continuity rate |
|---|---:|---:|
| H5 | `515/600` | `0.8846153846153846` |
| H10 | `504/600` | `0.8821656050955414` |
| Consensus | `504/600` | `0.8821656050955414` |

Continuity status counts:

- `RESOLVED_NO_MECHANICAL_DISCONTINUITY`: `313,494`;
- `PRICE_CONTINUITY_UNRESOLVED_COVERAGE`: `8,044`;
- `PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE`: `23,252`.

Reason counts:

- `NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL`: `313,494`;
- `EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED`: `23,012`;
- `KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED`: `6,844`;
- `CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY`: `1,200`;
- `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION`: `240`.

The known mechanical-crossing `240` rows remain blocked and were not waived.

Relative to the accepted post-KSEI baseline, resolving NISP alone deterministically improved:

- H5 gate dates `462 -> 515`;
- H10 gate dates `461 -> 504`;
- consensus gate dates `461 -> 504`;
- schedule-required rows `24,212 -> 23,012`;
- resolved rows `312,294 -> 313,494`.

This is real continuity-support improvement, but it remains below the frozen `>=0.90` every-date gate and therefore does not authorize historical V4 target/model execution.

Continuity hashes reported by the replay:

- continuity summary SHA-256: `46eecaa534854f74e759482a1416dc70c16d6803f2f833210087a39728a65c9d`;
- targeted continuity overlay SHA-256: `0fd567c1f96a41741b9eac22ffc978b9d6549430ce1ac4924a2b29a1e472aedc`;
- rebuilt full continuity ledger SHA-256: `6fc0eb10601a4f2926c36f060d06b68ed372d58f5499dcc2c6a76a77ff1126bb`;
- per-date SHA-256: `9c08a8e73b90c9f8f696a5a8fc9c484761da02b7a90188b31821a7ff14be1bf9`;
- event semantics audit SHA-256: `0f8bfd68d4666e518566609c73d7d1245385d951cfa542f786478d1c75ae90cd`;
- schedule evidence needs SHA-256: `31b183779ea6677afef048fa3a76eb827bf4d10418e691476eff8dc3fbdca930`.

The replay reported `provider_calls=false`, `target_or_rank_materialized=false`, `model_fit=false`, `prediction_generated=false`, `performance_computed=false`, and `protected_forward_accessed=false`.

A pandas mixed-type `DtypeWarning` on base-ledger CSV columns 7/8 was non-fatal and did not change execution or result.

## Interpretation / next boundary

The seven-event optimistic attribution was not invalidated: NISP alone produced the expected monotone improvement. However, the exact official-KSEI schedule acquisition path recovered no exact transition for the other six selected mechanical events. Therefore the next allowed work should be **offline forensic inspection of the already captured seven candidate documents plus linkage/parse audits**, with zero provider retry, to distinguish:

1. exact transition text exists but the frozen parser/linker did not admit it;
2. the candidate document is the wrong event/document identity;
3. the official document lacks the required regular-market Ex / first-new-basis transition semantics.

No provider retry, source substitution, parser relaxation, target/rank materialization, model fit, prediction, performance metric, bootstrap, protected-forward, or fresh-forward access is authorized from this result.
