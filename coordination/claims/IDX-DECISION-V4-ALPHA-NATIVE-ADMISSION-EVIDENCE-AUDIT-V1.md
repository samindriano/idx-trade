# IDX Decision V4 Alpha-Native Admission Evidence Audit V1

Status: REVIEW

Branch: `research/idx-decision-v4-alpha-native-admission-evidence-audit-v1`

Purpose: read-only architecture audit of evidence already exposed by the frozen V4-X1 alpha/scoring stack that could support a future Decision V4 admission-confidence primitive. Rank candidates in this order: existing alpha-native reliability/uncertainty, independent-head agreement, same-session score separation, raw score magnitude, and rank-history persistence fallback.

Scope: inspect existing repo specs/code/checkpoints and provenance only. Determine lineage compatibility with V4-X1, whether semantics are truly alpha-native versus a separate/legacy model, whether values are available historically and prospectively, and whether using them in Decision would create a second alpha model or violate prior scientific boundaries.

Boundaries: no Decision V4 rule implementation/replay, no new reliability fit, no threshold search/sweep, no historical outcome access, no PnL/returns, no provider/network data calls, no forward outcome access, no model refit/rescore, no live/paper activation.

Result checkpoint: `docs/checkpoints/2026-08-22_DECISION_V4_ALPHA_NATIVE_ADMISSION_EVIDENCE_AUDIT.md`

Verdict: `CONFIDENCE_AWARE_ADMISSION_ARCHITECTURALLY_DEFENSIBLE_ONLY_VIA_SINGLE_V4_X1_NATIVE_CROSS_HORIZON_COHERENCE_PRIMITIVE`.

Key disposition: H5/H10 cross-horizon coherence = KEEP / strongest; existing Reliability V1 = REJECT direct reuse because O2-specific; raw-score separation = CONDITIONAL/new derived primitive; raw score magnitude = REJECT; persistence/history = REJECT as primary confidence primitive.

No Decision V4 implementation or replay is authorized by this audit. Next action is design/attack of a semantically anchored H5/H10 coherence admission rule, without threshold mining or composite confidence construction.
