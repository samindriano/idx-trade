# Decision V4 Alpha-Native Admission Evidence Audit V1

Date: 2026-08-22 Asia/Jakarta
Status: `COMPLETE_READ_ONLY_ARCHITECTURE_AUDIT_NO_V4_RULE_AUTHORIZED`
Branch: `research/idx-decision-v4-alpha-native-admission-evidence-audit-v1`

## Purpose

Audit what evidence already exists in the frozen V4-X1 alpha/scoring stack that could support a future Decision V4 admission-confidence primitive. This is architecture/provenance review only: no Decision V4 rule, replay, threshold search, outcome access, refit, rescore, provider call, or PnL analysis is authorized or performed.

The audited candidate order was:

1. existing alpha-native uncertainty/reliability;
2. cross-head / cross-horizon agreement;
3. same-session score separation;
4. raw score magnitude;
5. rank-history persistence fallback.

## Key source facts

### V4-X1 is natively multi-head

The frozen V4-X1 stack fits separate H5 and H10 models for CONTROL and CHALLENGER. Historical OOS scoring stores, for each challenger row, `raw_h5`, `alpha_h5`, `raw_h10`, `alpha_h10`, and `alpha_consensus`; consensus is the frozen 50/50 average of H5 and H10 within-date percentile ranks.

The clean prospective scorer likewise loads separate frozen H5/H10 models and writes `raw_challenger_h5`, `alpha_h5`, `raw_challenger_h10`, `alpha_h10`, and `alpha_consensus` into the immutable score artifact. Therefore H5/H10 cross-horizon agreement can be computed from already-produced alpha-native artifacts on both historical OOS and prospective paths without model refit or rescore.

Important semantic guard: H5 and H10 are separate target-horizon heads using the same feature family/model class. Their agreement is **cross-horizon coherence**, not statistically independent-model confidence and not calibrated uncertainty.

### Historical raw scores are fold-model predictions

Historical OOS replay fits separate H5/H10 models inside each of six folds. The raw outputs are model predictions before within-date percentile normalization. The training targets are target ranks (`target_rank_h5`, `target_rank_h10`). Therefore raw score values have a model-output interpretation but are not demonstrated to be calibrated probabilities, expected returns, or stable absolute scales across folds versus the final prospective refit.

### Existing Reliability V1 is O2-specific

`reliability_v1_forward_shadow.py` explicitly describes itself as an outcome-blind score-margin sidecar for the O2 archive. It imports and verifies O2 model IDs, model hashes, feature-order hashes, and O2 score artifacts. Its score-margin formula is nearest raw O2 score gap divided by same-session O2 score IQR, then percentile-ranked.

This is useful architectural precedent, but it is not a V4-X1-native reliability output and cannot be directly reused as a Decision V4 primitive without creating a new V4-X1 formula/sidecar and separately governing that work.

## Primitive verdicts

| Primitive | Exists now? | V4-X1 native? | Historical OOS bytes | Prospective bytes | Verdict | Reason |
|---|---|---|---|---|---|---|
| Existing Reliability V1 / `score_margin_reliability` | Yes, for O2 | No | O2 lineage only | O2 shadow sidecar only | **REJECT direct reuse** | Hard-pinned to O2 identity/model/feature order. Conceptual precedent only. |
| H5/H10 cross-horizon agreement/coherence | Yes, as underlying H5/H10 alpha outputs | **Yes** | `alpha_h5`, `alpha_h10` persisted | `alpha_h5`, `alpha_h10` persisted | **KEEP — strongest candidate** | Zero new fit/rescore; same semantics on historical and prospective paths; preserves possibility of fresh strong alpha because it is same-day evidence rather than persistence. |
| Same-session raw-score separation | Raw inputs exist; separation primitive itself does not | Partially | `raw_h5`, `raw_h10` persisted | raw challenger H5/H10 persisted | **CONDITIONAL / NOT YET A PRIMITIVE** | A scale-normalized margin formula would be new Decision/sidecar science. Which head, normalization, and combination create degrees of freedom. Do not call it existing reliability. |
| Raw score magnitude | Yes | Yes as raw model output | persisted but produced by fold-specific models | persisted from final refit models | **REJECT as admission primitive** | No demonstrated calibration as probability/expected return; absolute cross-fold/final-refit comparability is not established. Normalizing it within date largely returns to rank semantics. |
| Rank-history persistence | Yes from prior ranks | Decision-derived, not alpha-native uncertainty | available | available prospectively | **REJECT as primary confidence primitive** | Prior Decision diagnosis shows association with structural durability, but using it risks circular rank-persistence optimization, V2-like confirmation/underfill, and suppressing genuine fresh alpha. Keep only as descriptive fallback/context, not primary V4 evidence. |

## Why H5/H10 coherence survives the architecture attack

A candidate can have the same 50/50 consensus alpha while being composed very differently across horizons. Therefore the consensus scalar does not fully identify the pair `(alpha_h5, alpha_h10)`. Cross-horizon coherence adds already-existing information about whether the short and longer horizon heads support the candidate similarly.

This does **not** prove that agreement predicts economic outcomes or structural durability. No such claim is authorized by this audit. It only establishes that this is the cleanest available primitive to test because it is:

- frozen-alpha-native rather than Decision-created;
- same-day rather than a lag/persistence confirmation filter;
- present in both historical OOS and prospective score artifacts;
- available without model refit, rescoring, new provider data, or outcome access;
- one primitive rather than a fitted composite meta-model.

## Major attack / limitations

1. H5 and H10 share the same feature family and model class, so agreement is not independent evidence in the statistical sense.
2. Consensus already averages H5/H10, so coherence is additional composition information, not a new source of alpha.
3. A continuous disagreement cutoff chosen after inspecting Decision failures would create threshold-mining risk.
4. Using coherence to suppress entries could still mechanically reduce turnover and improve structural gates without improving economic decisions.
5. It does not solve the cash/capacity problem by itself; capacity gates must remain hard in any future structural replay.
6. Existing O2 Reliability V1 must not be transplanted or renamed as V4-X1 reliability.

## Recommendation

`CONFIDENCE_AWARE_ADMISSION_ARCHITECTURALLY_DEFENSIBLE_ONLY_VIA_SINGLE_V4_X1_NATIVE_CROSS_HORIZON_COHERENCE_PRIMITIVE`

If Decision V4 proceeds, the cleanest next design direction is to use **one** H5/H10 cross-horizon coherence concept to alter admission permission while leaving alpha ranking and severity-aware exits unchanged. Do not build a composite confidence score, do not add persistence as a second confidence input, do not reuse O2 Reliability V1, and do not optimize a continuous disagreement threshold.

Before preregistration, the design should prefer a semantically anchored rule derived from already-frozen horizon/rank concepts rather than a numerically optimized `abs(alpha_h5-alpha_h10) < x` threshold. Exact rule selection remains a design/attack task; this audit does not authorize implementation or replay.

## Scientific boundary

- Decision V4 implemented/replayed: **false**
- alternative portfolio simulated: **false**
- historical outcomes/returns/PnL accessed: **false**
- protected/fresh-forward outcomes accessed: **false**
- model refit/rescore/retune: **false**
- reliability model/formula fit: **false**
- threshold search/sweep: **false**
- provider/network data calls: **false**
- live/paper activation: **false**
