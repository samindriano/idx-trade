# IDX Decision V4 Alpha-Native Admission Evidence Audit V1

Status: ACTIVE

Branch: `research/idx-decision-v4-alpha-native-admission-evidence-audit-v1`

Purpose: read-only architecture audit of evidence already exposed by the frozen V4-X1 alpha/scoring stack that could support a future Decision V4 admission-confidence primitive. Rank candidates in this order: existing alpha-native reliability/uncertainty, independent-head agreement, same-session score separation, raw score magnitude, and rank-history persistence fallback.

Scope: inspect existing repo specs/code/checkpoints and provenance only. Determine lineage compatibility with V4-X1, whether semantics are truly alpha-native versus a separate/legacy model, whether values are available historically and prospectively, and whether using them in Decision would create a second alpha model or violate prior scientific boundaries.

Boundaries: no Decision V4 rule implementation/replay, no new reliability fit, no threshold search/sweep, no historical outcome access, no PnL/returns, no provider/network data calls, no forward outcome access, no model refit/rescore, no live/paper activation.

Deliverable: audit checkpoint with a KEEP / CONDITIONAL / REJECT verdict for each primitive and a recommendation whether confidence-aware admission is architecturally defensible before any preregistration.
