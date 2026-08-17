# Ranking V4 target-support census — outcome-blind result

Date: 2026-08-17 (Asia/Jakarta)
Branch: `research/idx-v4-target-support-census-v1`
Parent: `research/idx-ranking-v4-2-evaluation-contract-v1@86981922c41354bc5629c5e6a327839667ccc6c6`
Status: `V4_TARGET_SUPPORT_BLOCKED_6X100_INFEASIBLE`

## Scope and boundary

This is a support/observability census only. It does not load labels or
realized outcomes, compute returns/IC/performance, fit a model, call a
provider, acquire corporate-action data, or modify V4-0/V4-1/V4-2 contracts.

The decision population is the accepted active-only signal panel. Future
states are resolved from exact official regular-market Stock Summary anchors;
regular-market suspension intervals are applied only where an exact anchor is
absent. Missing state is `UNKNOWN`; a date beyond the official calendar is
`NO_FUTURE_SESSION`. No ACTIVE state is inferred from row presence, Yahoo,
zero volume, or missing evidence.

For each signal row, Open(t+1) support requires an ACTIVE future session and a
positive finite Open from the canonical panel or the already verified
Historical Open overlay. H5/H10 Close support requires an ACTIVE future row
with a positive finite Close. Corporate-action continuity requires the signal,
entry, and relevant exit rows to carry the accepted continuity flag and be
ACTIVE. The canonical panel was not rewritten.

## Pinned inputs

| Input | SHA-256 |
|---|---|
| official exchange sessions | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| signal panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| tradability anchors | `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e` |
| tradability intervals | `fd255f21a3accd763286fbd0b0c6d9d501d618ae611cc0681017e001bdba83cc` |
| official split/reverse actions | `a0ef73a548b3657260b46a0c497e6f87dd9b5138588e23006d4b538677125b35` |
| scope exclusions | `406e224dcd611f3d5a2f9ad8bbd2c03b3c8a0826cc724b01b4618c9b1c1bd938` |
| signal research manifest | `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a` |
| Historical Open overlay parquet | `2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41` |
| Historical Open overlay manifest | `dfb7219bddec77ced3e3aadfaa2d85d04c19e1d9fd9a8af1badba523ecf91977` |

The overlay contains 2,184 verified rows and was consumed without network
calls. Its accepted status remains `VERIFIED_WITH_METADATA_WARNING`: the
diagnostic-summary self-hash warning is preserved and is not used to admit
additional rows. The remaining 47,292 residual Open rows were not attempted.

The V4 contract files were also read and hash-recorded:

| Contract | SHA-256 |
|---|---|
| V4-0 decision contract | `d1277fe96fbd5561c628b7a7f56729321ab9e15118e936dd8e83e5da37e09ebd` |
| V4-1 target contract | `9e40db5376606e048c6216ab57be712fc6992d941527254e1076b4a73d4b876a` |
| V4-2 evaluation contract | `cb955748887c344948d61a4f3cf4bc84a51dcf3468eaf16a995354ada7401e6c` |

The V4-2 manifest-pinned `SIGNAL_RESEARCH_HLCV_CONTRACT.md` path is not
present at its exact recorded path. No alternate copy was substituted; this
is a reproducibility blocker.

## Exact support result

The panel has 981,940 decision rows across 945 tickers and 1,260 official
sessions from 2021-04-29 through 2026-07-31. Overall row support is:

| Quantity | Supported rows | Rate |
|---|---:|---:|
| Open(t+1), ACTIVE future state | 532,028 | 54.1813% |
| H5 Close, ACTIVE future state | 961,366 | 97.9048% |
| H10 Close, ACTIVE future state | 954,379 | 97.1932% |
| H5 target: Open + H5 Close | 523,956 | 53.3593% |
| H10 target: Open + H10 Close | 518,145 | 52.7675% |
| both H5 and H10 targets | 515,257 | 52.4734% |
| H5 CA continuity | 953,151 | 97.0682% |
| H10 CA continuity | 945,757 | 96.3152% |
| both-horizon CA continuity | 938,553 | 95.5815% |

Open(t+1) detail: 968,095 rows have an ACTIVE future state; 532,028 have
usable Open and 436,067 ACTIVE-state rows do not. The remaining future-state
rows are 13,015 `NO_TRADE`, 830 `NO_FUTURE_SESSION`, 0 `SUSPENDED`, and 0
`UNKNOWN`.

H5 future-state detail: 961,366 `ACTIVE`, 16,401 `NO_TRADE`, 5 `UNKNOWN`,
4,168 `NO_FUTURE_SESSION`, and 0 `SUSPENDED`.

H10 future-state detail: 954,379 `ACTIVE`, 19,196 `NO_TRADE`, 15 `UNKNOWN`,
8,350 `NO_FUTURE_SESSION`, and 0 `SUSPENDED`.

The zero `SUSPENDED` counts above are for the future legs of this active-only
panel population, not a claim that the accepted interval artifact contains no
suspension intervals.

## Per-date gate and session identity result

The frozen 90% date gate produces:

| Date gate | Passing dates / 1,260 |
|---|---:|
| Open(t+1) | 275 |
| H5 target | 270 |
| H10 target | 265 |
| both targets | 264 |
| H5 CA continuity | 1,255 |
| H10 CA continuity | 1,250 |
| both-horizon CA continuity | 1,250 |
| consensus eligible = both target + both CA gates | **264** |

The exact consensus identity list is hash-pinned:

`v4_eligible_consensus_sessions.csv`

SHA-256: `cdad58189694d71d1ca4ebce1c12da7dea4a663d3930262325a637ca53fca7dc`

It contains 264 eligible sessions. The longest official-calendar-consecutive
run is 196 sessions, session indices 1054–1249 (2025-09-19 through
2026-07-17). Even if “consecutive” were interpreted as the filtered eligible
sequence rather than official-calendar adjacency, there are only 264 eligible
sessions, not the 600 required for six 100-session blocks.

The full identity artifact contains all 1,260 official sessions:

`v4_session_identities_1260.csv` SHA-256:
`b7c8662aa9a1e12bed53242ef3526eaf5b795555029a6218d5f9b230dcc9de1a`

## Verdict and blockers

Verdict: **`BLOCKED_6X100_TARGET_SUPPORT`**.

Exact blockers:

1. Only 264 dates satisfy the frozen both-target and CA-continuity date gates;
   V4 requires 600 eligible sessions for 6×100.
2. The longest calendar-consecutive eligible run is 196, so official-calendar
   contiguity cannot produce even one 600-session sequence.
3. The exact signal-contract file pinned by the parent manifest is missing;
   substituting a differently hashed copy would break reproducibility.
4. The accepted 1260 signal-research manifest still records strict execution
   grade `FAIL`; this census does not silently upgrade that status.
5. V4-2 leaves three identity-sequence details for V4-3 to define: calendar
   versus filtered-list consecutiveness, treatment of below-gate dates in the
   identity sequence, and whether H5/H10/consensus share one identity list.

No V4 target labels/returns, IC/performance metrics, model scores, model fit,
provider calls, CA acquisition, protected outcomes, or evaluator changes were
performed.

## Artifacts

External output root (immutable after creation):
`D:\Documents\Project\idx-v4-target-support-census-20260817-v1`

| Artifact | SHA-256 |
|---|---|
| `v4_target_support_per_date.csv` | `1d268697c5b1e3256ce08e23b8520613e1c4d52e5f3cdacf5bd2e269194e99e5` |
| `v4_session_identities_1260.csv` | `b7c8662aa9a1e12bed53242ef3526eaf5b795555029a6218d5f9b230dcc9de1a` |
| `v4_eligible_consensus_sessions.csv` | `cdad58189694d71d1ca4ebce1c12da7dea4a663d3930262325a637ca53fca7dc` |
| `census_summary.json` | `3c13c83a5764058922f37dd76e10263c92e989d26017a0174264b178827596e9` |
| `manifest.json` | `e8679e9fe6913bab1470b26ba5b90eb1ae827ecddaa8c36ca9acc9a54aebe6ff` |

Validation: `python -m py_compile scripts/run_v4_target_support_census.py`
passed; the generated manifest records `outcome_blind=true`,
`model_fit=false`, and `labels_or_outcomes_loaded=false`.
