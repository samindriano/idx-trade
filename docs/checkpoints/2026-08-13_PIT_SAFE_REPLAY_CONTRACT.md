# PIT-Safe V2/V3-B/O2 Replay Contract

Date: 2026-08-13 (Asia/Jakarta)  
Branch: `codex/pit-safe-v2-v3b-o2-reproduction-research-v1`

## Decision boundary

The historical label audit established that the previously reported H10
development-table endpoint was a cache/path selection failure, not a missing
label source. The fast-H10 artifact is byte-stable and exactly equivalent to
the legacy full H10 label table through the 2026-07-31 historical boundary.
This contract therefore authorizes one fresh, outcome-blind historical replay
from the corrected input lineage.

This is a new model-fitting lineage. It does not promote, overwrite, or
reinterpret the old fitted models. The old V2/V3-B/O2 models and metrics remain
`LEGACY_CONTAMINATED_REFERENCE`: historical evidence of their exact contaminated
inputs, but not a canonical PIT-safe release or a basis for a new prospective
counter.

## Frozen inputs

- immutable model-safe panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official exchange calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- PIT security master SHA-256:
  `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`;
- complete fast-H10 label artifact SHA-256:
  `a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677`;
- fast-H10/full-panel equivalence report SHA-256:
  `8f8865b2f133020a94ab8d2507fbb221f4b7f59bd1775b9da51fba2f4084d554`;
- corrected V2 prepared-table SHA-256:
  `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`;
- corrected V3-B training-table SHA-256:
  `7faf7f68b78dff336a908a69e8b02f6b0f741434b4ada6e17c6b1ef8d9385753`;
- corrected O2 input-table SHA-256:
  `8b1f6c917c013a6fb9cb5733d8096b45e0b5712dfa318ad49ca7f9ca43321585`;
- corrected V2 key SHA-256:
  `79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826`;
- corrected O2 key SHA-256:
  `77dbe5aaa32fa7e35779f273bc09501140e1a1363861aa262567f59354dd0644`.

The corrected inputs are consumed read-only from the external runtime root
`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_v2_v3b_o2_reproduction_v1_20260813_002_fast_h10`.
The immutable panel and all prior runtime roots remain unchanged.

## Replay population and labels

The V2 replay uses 292,631 corrected primary-liquid, resolved H10 rows across
737 tickers. The V3-B replay uses the same row identities and appends the exact
eight Structure-Lite columns. The O2 replay uses the corrected 278,166-row
Open-geometry common-support population across 729 tickers. The two removed
KOCI identities are retained as a factual consequence of the PIT-safe panel
repair; no ticker is hard-coded into the runner.

H10 remains exactly `TP_FIRST=1` and `SL_FIRST=0`. The six fixed expanding
folds are unchanged: 20-session H20 purge and 100-session validation for
V2F1 through V2F6. Historical rows through 2026-07-31 are development
knowledge only; no protected fresh-forward outcome is read.

## Models and semantics

The replay fits exactly the frozen model set:

- V2: `V1_HGB_CONTROL`, `LOGISTIC_XS`, `HGB_XS`, `HGB_XS_MARKET`,
  `PAIRWISE_LOGISTIC_XS`;
- V3-B: the canonical `HGB_XS_MARKET` control and the exact
  `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` 33-feature challenger;
- O2: the canonical 33-feature V3-B baseline and `O2_OPEN_GEOMETRY`, which
  appends only `open_position`, `open_to_high`, `open_to_low` in that order.

Model constructors, preprocessing, pair budget, random seed, ranking-score
semantics, fold evaluator, and the V2 champion / V3-B / O2 survivor rules are
reused from repository code. No tuning, new feature, population enlargement,
final refit, calibration, provider call, or outcome access is allowed.

Every replay artifact must carry the corrected input hashes, feature-order
hashes, fold contract, historical boundary, and explicit false values for
`fresh_forward_outcomes_accessed`, `provider_calls`, and
`execution_grade_promoted`.

## Stop rules

- A hash, row-identity, label, feature-order, fold, or provenance mismatch is a
  hard stop.
- A model-fit or artifact failure preserves the external partial root and is
  reported without weakening the contract.
- A historical survivor does not authorize forward scoring, a new 100-session
  counter, modelling beyond this replay, or execution-PnL work.
- After the replay, write a factual runtime checkpoint and handoff, push the
  branch, and stop for independent ChatGPT review.
