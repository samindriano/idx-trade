# Ranking V3 Hypothesis Ledger V1

Status: **V3-A COMPLETE/KILLED; V3-B COMPLETE/PROMOTED; V3-C COMPLETE/KILLED; V3-D BLOCKED/UNVIEWED; V3-E COMPLETE/KILLED; 9 CANDIDATES EVALUATED**

All F1-F4 results are historical-development evidence only. The cumulative evaluated counter is `9`.

Ordinals `001`-`007` have been viewed. Ordinals `008`-`009` are reserved for V3-D but remain unviewed because the PIT sector data gate blocked before model outcomes. Ordinals `010`-`011` were executed and viewed on F1-F4. Pre-score engineering/data/provenance/dependency blocks do not increment the denominator.

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 001 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-CONTROL-001` | exact V2 control | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 002 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL252-002` | exponential recency H=252 | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 003 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL504-003` | exponential recency H=504 | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 004 | `V3-B-STRUCTURE-LITE-V1` | `V3-B-STRUCTURE-LITE-V1-CONTROL-004` | exact V2 control | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 005 | `V3-B-STRUCTURE-LITE-V1` | `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` | V2 25 + fixed 8-feature causal geometry bundle | `COMPLETE` | `true` | `PROMOTE_FOR_NEXT_RESEARCH_STEP` |
| 006 | `V3-C-REGIME-V1` | `V3-C-REGIME-V1-CONTROL-006` | exact V2 control | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 007 | `V3-C-REGIME-V1` | `V3-C-REGIME-V1-TWO-EXPERT-007` | frozen NORMAL/STRESS two-expert architecture | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 008 | `V3-D-SECTOR-RELATIVE-V1` | `V3-D-SECTOR-RELATIVE-V1-CONTROL-008` | exact V2 control | `BLOCKED_PIT_SECTOR_HISTORY` | `false` | `UNVIEWED_RESERVED` |
| 009 | `V3-D-SECTOR-RELATIVE-V1` | `V3-D-SECTOR-RELATIVE-V1-CANDIDATE-009` | V2 25 + fixed 6-feature PIT sector-relative bundle | `BLOCKED_PIT_SECTOR_HISTORY` | `false` | `UNVIEWED_RESERVED` |
| 010 | `V3-E-TRUE-RANKING-V1` | `V3-E-TRUE-RANKING-V1-CONTROL-010` | exact V2 HGB control on F1-F4 | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 011 | `V3-E-TRUE-RANKING-V1` | `V3-E-TRUE-RANKING-V1-LAMBDAMART-011` | exact V2 25 + frozen XGBoost LambdaMART same-date ranker | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |

## V3-A Recency — executed

- exact control equivalence PASS on 84,732 F1-F4 rows, max diff `0.0`;
- H252 and H504 both failed paired promotion;
- final `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`;
- no recency rescue is allowed.

## V3-B Structure-Lite — executed / survivor

Controlling spec: `docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`.

- control equivalence PASS on 84,732 rows, max diff `0.0`;
- median paired PR improvement `+0.0039258450`;
- q25 `+0.0026897894`;
- worst `+0.0018412974`;
- positive PR improvement `4/4` folds;
- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`;
- final `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`.

V3-B is the only surviving V3 component so far. Its viewed definition is closed.

## V3-C Regime — executed / killed

- cache SHA `1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`;
- manifest SHA `c4b090de65c291af21ea0a49f63d5d2d0dc1acbd18fff1c995494e1212f1418b`;
- control equivalence PASS on 84,732 rows, max diff `0.0`;
- candidate absolute sanity PASS;
- overall paired promotion FAIL;
- regime robustness FAIL;
- overall median PR improvement `-0.0123171892`;
- NORMAL median `-0.0014712226`;
- STRESS median `-0.0289646749`;
- final `V3_C_REGIME_KILL_KEEP_V2_CONTROL`.

No regime rescue/threshold change/new expert/blending/rescaling is allowed.

## V3-D Sector-Relative — blocked without outcome access

Controlling blocked checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_PIT_DATA_GATE_BLOCKED.md`

- full pytest `290 passed, 0 failed, 3 warnings`;
- result `BLOCKED_PIT_SECTOR_HISTORY`;
- no V3-D cache/manifest/outcome metric was created;
- ordinals 008/009 remain `result_viewed=false`;
- current-sector backfill and guessed report-month dates remain prohibited.

A future defensible immutable PIT IDX-IC archive may unblock this frozen lane.

## V3-E True Ranking — dependency erratum applied pre-outcome

Original controlling spec:

`docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`

- SHA-256 `79534d29d414a08b60cca85e68e8781849aabefa1a103d9f43ab0ead47308c55`;
- Git blob `20df2927b6663ea16955919760db9c1429cff3a5`.

Original review addendum:

`docs/RANKING_V3_TRUE_RANKING_SPEC_REVIEW_ADDENDUM_V1.md`

- SHA-256 `6652e1f934f58630619a9cab5afb0bdfaa3317894977bad8bfa9ca5ffe980812`;
- Git blob `01c4dca87ff52fca678c948e4ee23d3e3c82dbcd`.

First local attempt stopped before artifact/outcome access because the original dependency identity `xgboost==3.2.1` has no public package release. That block remains recorded in:

`docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_BLOCKED_DEPENDENCY.md`

No candidate was evaluated by that stop.

The one pre-outcome dependency correction is frozen in:

`docs/RANKING_V3_TRUE_RANKING_DEPENDENCY_ERRATUM_V1.md`

- SHA-256 `bd029458f7a7cd14424af9b748cb7522f1d23b0fe8eaf20ad8f6b44d48894bea`;
- Git blob `327e053c2a1b4270acc4e7de313bba97680eff8b`;
- corrected exact dependency **`xgboost==3.2.0`**.

Research semantics are unchanged: one `XGBRanker`, `rank:ndcg`, exact date qid, exact V2 25 features, binary H10 target, training-only V2-style median imputation, 200 trees, LR .05, depth 5, seed 42, `n_jobs=1`, mean pair method, 8 pairs/sample, normalization enabled, no early stopping/tuning/second ranker.

Corrected implementation lineage:

- `88b1ceb3a9eea30a89fa367a040fc396e90bfda0` — dependency erratum document;
- `d6d727758a5d90c673e0e7c3845cb282a2fc221b` — erratum runner wrapper;
- `98863ce24e99d247be5755f8d568b8abbb07c61f` — dependency pin `3.2.0`;
- `e6373cdb8827abb2c5d49b68c1f1fcb8e4826d61` — corrected focused tests;
- `b68376e38ea3d8b4edbd5133547dbe0f2f381fb5` — erratum review/run reauthorization checkpoint;
- `daf425d407a030884e381dc195d20fc18a806c86` — corrected local-run handoff.

Executed result:

- final code commit used: `d6d727758a5d90c673e0e7c3845cb282a2fc221b`;
- environment: Python `3.13.5`, NumPy `2.4.2`, pandas `2.3.3`, PyArrow `23.0.1`, scikit-learn `1.8.0`, XGBoost `3.2.0`;
- discovery output: 169,464 combined control/candidate rows, 474 tickers, 400 dates, session indices `525..984`, dates `2023-06-23..2025-06-05`;
- ordinal 010 control equivalence: PASS on 84,732 rows; max score diff `0.0`; all metric diffs `0.0`;
- ordinal 011 LambdaMART: absolute sanity PASS; paired promotion FAIL;
- paired PR-delta improvement: median `+0.0049421451`, q25 `-0.0034997915`, worst `-0.0253353754`, positive/non-below folds `3/4`;
- paired robustness: median ROC change `+0.0036990136`; median Q5-Q1 change `-0.0072112874`, non-below folds `1/4`; median top-decile lift change `-0.0025193041`;
- final decision: `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`;
- ordinals 010/011 are now result viewed `true`; cumulative evaluated count is `9`;
- no rescue, second ranker, integration, or later stage was started.

Allowed final decisions were:

- `V3_E_TRUE_RANKING_PROMOTE_LAMBDAMART`; or
- `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`.

No rescue/second ranker is authorized. V2 HGB_XS_MARKET remains the active ranking control.

## Required future execution record

Every executed row must record hypothesis/candidate/ordinal, controlling spec/review/erratum identities, prepared/reference identities, fold set, feature-order hash, model identity, result-viewed status, metrics/artifact hashes, verdict, cumulative candidate count, code commit, environment, and notes.

A viewed candidate remains in the denominator permanently. A pre-score data/provenance/dependency block does not fabricate an evaluated result.
