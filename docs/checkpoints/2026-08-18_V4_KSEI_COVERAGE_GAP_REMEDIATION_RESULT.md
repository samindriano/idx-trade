# V4 KSEI Coverage-Gap Remediation V1 — Result

## Decision

`V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`

The import-path retry completed the authorized one-shot targeted KSEI run and
the authorized one-shot outcome-blind continuity replay. The continuity gate
remains fail-closed; no source/configuration patch was made.

Branch: `data/idx-v4-ksei-coverage-gap-remediation-v1`
Code/handoff HEAD before result documentation:
`15dfe535f091b23ad510100a7002830e982415e2`
Scientific/provider code anchor: `5b311e0398afb9099887cf7558c92f15d99029b8`

## Preflight

- `PYTHONPATH` resolved to the retry worktree `src` directory.
- `idx_trade.v4_ksei_coverage_gap` resolved to the current worktree module.
- Focused pytest: `7 passed`.
- `py_compile`: PASS for the four handoff scripts/modules.
- `git diff --check`: PASS.
- Runtime preflight: `V4_KSEI_COVERAGE_GAP_RUNTIME_PREFLIGHT_PASS`.
- Preflight network calls: `0`.
- Frozen gap tickers: `43`.
- Gap identity SHA-256:
  `1cd050985841519d24f58a38d10014693ff4a843cbd438586237ad4419ffe812`.
- All five immutable input paths existed; both fresh output roots were absent
  before execution.

## Targeted KSEI acquisition

The command from the retry handoff was executed exactly once and exited 0.

- Status: `V4_KSEI_COVERAGE_GAP_REMEDIATION_COMPLETE_WITH_REMAINING_GAPS`.
- Provider requests/raw captures: `76 / 76`.
- Parent gap population: `43`.
- Parent dominant failures: `HTTP_NON_200_OR_EMPTY=41`,
  `PARSE_IDENTITY_MISMATCH=2`.
- Recovered strict-parse tickers: `31`.
- Recovered tickers: ACRO, BDKR, BJTM, CBRE, DFAM, DGIK, HELI, IBOS, ISAP,
  ISAT, JPFA, KEJU, KRAS, MAPA, MAPI, MIDI, MIKA, MINA, MSJA, NASI, OLIV,
  PMMP, PMUI, PSAB, SDMU, STAA, STRK, TCPI, TEBE, TOSK, VISI.
- Remaining unresolved: `12` — AMAN, AVIA, AYAM, BCIP, ICBP, PRIM, SKRN,
  SLIS, SMAR, SNLK, SOCI, SOFA.
- Recovery failure classes for unresolved rows:
  `HTTP_NON_200_OR_EMPTY=11`, `PARSE_IDENTITY_MISMATCH=1` (PRIM).
- Recovered history rows: `636`.
- Recovered active mechanical/unknown rows: `24 / 0`.
- Merged coverage: `598 certified`, `12 unresolved` tickers.
- Merged history rows: `15,359` (parent `14,723` + recovered `636`).
- No parser relaxation, alias remap, alternate provider, or 567-ticker recrawl.

Acquisition manifest SHA-256:
`7e86f5e52d7c2ff609ee9dd4be28ff1aefea1e4d5c7d7d9dbffb6abd07185f50`

Promoted acquisition artifact hashes:

- `summary.json`: `9ec069e9a9baaaeac05c0be90459b0ec211bba3981f2d3d478f21abbb09a855b`
- `coverage_gap_results.csv`: `75b2aedef93343c2a374136b6e8ae6b081665d6da06165afae2db4f9b02ef280`
- `parent_failure_diagnostic.csv`: `d8ba6b9a6f1d3b472222d4a0ddf9a5aa427353cfe9cd569397c3a21d7ac7031b`

## Continuity replay

The exact handoff replay was executed once after successful acquisition.

- Verdict: `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`.
- `corporate_action_continuity_certified`: `false`.
- Frozen dates/rows/tickers: `600 / 344,790 / 610`.
- Relevant event rows: `83`.
- Event semantics: `EXACT_TRANSITION=44`, `SCHEDULE_REQUIRED=39`.
- Schedule-required tickers: `35`.
- Cross-source conflict tickers: MEGA, SCMA.
- H5 gate dates: `462`; minimum rate `0.8814102564`.
- H10 gate dates: `461`; minimum rate `0.8789808917`.
- Consensus gate dates: `461`; minimum rate `0.8789808917`.
- The frozen required rate is `0.90`, so the continuity gate does not pass.

Continuity reason counts:

- `NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL`: `312,294`
- `EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED`: `24,212`
- `KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED`: `6,844`
- `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION`: `240`
- `CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY`: `1,200`

Continuity status counts:

- `RESOLVED_NO_MECHANICAL_DISCONTINUITY`: `312,294`
- `PRICE_CONTINUITY_UNRESOLVED_COVERAGE`: `8,044`
- `PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE`: `24,452`

Continuity summary SHA-256:
`3939fbd7e5d63d702782ca7851c8249802a0341a8ac97d5ee15133f265a155ec`

Promoted continuity artifact hashes:

- `MANIFEST.json`: `1670d63f4041ee238809a89750ac0978d9dde54a812bff126ab735b551ecc35e`
- `summary.json`: `3939fbd7e5d63d702782ca7851c8249802a0341a8ac97d5ee15133f265a155ec`
- `event_semantics_audit.csv`: `c88b267de29c7712219a67578b80399c2bc258afe1dd7bd276d2e3badcfd4d0d`
- `schedule_evidence_needs.csv`: `1988f2bb679b09835e045235fa7aa46f4d8c62cf9531e76a5b5b889d848a127a`
- `v4_frozen_continuity_per_date_event_window.csv`: `874a087152af219c74d3dbce01cca15669085aa84c081da44350a391c6f6d591`
- `ksei_coverage_gap_continuity_overlay.json`: `bda80ad53a6e1426f147177c50896e6776ec78196602e45fb9b5489282e7c026`

Large raw HTML, request deltas, full merged history, and the 73 MB continuity
ledger remain external and were not committed.

## Boundary confirmation

No R5/R10, target/rank materialization, model fit, prediction, IC/performance,
bootstrap, protected/fresh-forward outcomes, source substitution, parser
relaxation, schedule acquisition, or V4 contract rescue was performed.
