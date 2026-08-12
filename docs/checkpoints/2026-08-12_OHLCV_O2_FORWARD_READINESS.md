# OHLCV O2 Fresh-Forward Infrastructure Readiness

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-forward-v1`
Starting remote HEAD: `2cc53a4ec60e33b9a64e03f2f1fbbd98d1e28e71`
Status: `O2_FORWARD_INFRASTRUCTURE_IMPLEMENTED_PENDING_INDEPENDENT_REVIEW`

## Scope

This lane implemented and tested only the frozen O2 fresh-forward scoring and
ledger infrastructure. It did not score an official O2 session, create an
official counter entry, open an outcome, call a provider, retrain, tune,
calibrate, or access protected forward data.

Synthetic fixtures only were used for runtime behavior tests.

## Hash-pinned model contract

The frozen O2 final model and canonical V3-B baseline were verified read-only
by model SHA, model-manifest SHA, candidate/architecture identity, feature
order, and clean outcome-access flags. Both joblib artifacts loaded
successfully.

| role | identity | model SHA-256 | model manifest SHA-256 | feature-order SHA-256 |
|---|---|---|---|---|
| O2 | `O2-GEOMETRY-FULL3-V1-CANDIDATE-001` | `42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb` | `535875e74a1b3a6532e95addf819521758798a767bc49ee9b30d54054a0ae7c2` | `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f` |
| V3-B | `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` | `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6` | `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9` | `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e` |

O2 final-refit artifact manifest SHA-256:
`a7045257aa85c9d1020d3fe4ceb60a1ee100aadc827305ddf5c608a616adc2d3`

## Implemented controls

- `resolve_first_post_freeze_session(...)` resolves the first official
  calendar session strictly after an explicit freeze timestamp; no date is
  hard-coded.
- `score_forward_session(...)` requires an official calendar identity,
  post-close snapshot identity, V3-B eligibility, valid Open/High/Low, exact
  O2 geometry, per-row input provenance SHA-256, and a snapshot SHA-256.
- Only exact O2-eligible rows receive O2 and paired V3-B raw scores.
  Ineligible rows are retained with an explicit exclusion reason and no score.
- No synthetic geometry fill, provider repair, or historical backfill path is
  present in the scoring API.
- `persist_session_score_artifact(...)` writes a hash-manifested parquet plus
  JSON record and refuses partial or changed overwrites.
- `OfficialO2Counter` accepts only hash-manifested, outcome-clean artifacts in
  exact consecutive session-index order beginning at the first post-freeze
  session. Pre-freeze submissions and gaps raise fail-closed errors.
- Counter maturation uses the official session index and frozen H10 horizon;
  it does not read outcome values.
- `persist_counter_state(...)` refuses boundary changes, outcome-tainted state,
  and counter rewinds.
- `OutcomeAccessGuard` and explicit protected-column checks reject outcome
  access in the scoring lane.

The official gate remains exactly `100` consecutive eligible official signal
sessions. A session is not counted merely because it is present in a calendar;
its score artifact must already be persisted and hash-manifested. No official
O2 counter has been started in this lane.

## Validation

- focused synthetic/infrastructure pytest: `4 passed`;
- full pytest: `286 passed, 5 warnings`;
- model verification: O2 and V3-B loaded successfully after hash checks;
- official O2 session score artifacts created: `0`;
- official O2 counter entries created: `0`;
- protected outcomes accessed: `false`;
- provider/network calls: `0`.

The five warnings are existing pandas FutureWarnings in unrelated modules.

## Stop condition

The infrastructure is stopped here for independent ChatGPT review. Official
O2 scoring must not begin until this branch is independently reviewed and a
separate authorization opens the first post-freeze session.
