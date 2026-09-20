# Eligibility Policy versus Top-30 Selection Overlap V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_POLICY_SELECTION_OVERLAP / POLICY UNRESOLVED`

## Question

Does the unresolved minimum-20 versus min-periods-60 eligibility conflict alter
actual daily Top-30 membership, rather than only changing row counts or rank
denominators?

## Method

Both policy branches were reconstructed independently from the frozen panel,
financial capability bundle, official sessions, and regular ACTIVE anchors. Each
branch recomputed the market-side and C3 scores, applied its own eligibility
mask, ranked by candidate, and selected fixed Top-30 sets with an ascending
ticker tie-break. The comparison uses only dates where both branches have at
least 30 finite eligible names.

This is a counterfactual structural comparison. It does not choose the policy,
regenerate the canonical feature artifact, or open any target/outcome.

## Result

| Candidate | Common dates | Mean Top-30 overlap | Mean Jaccard | Exact daily matches | Mean symmetric difference |
|---|---:|---:|---:|---:|---:|
| C1 | 1,141 | 96.52% | 93.48% | 32.52% | 2.09 names |
| C2 | 1,201 | 100.00% | 100.00% | 100.00% | 0.00 names |
| C3 | 278 | 94.05% | 89.20% | 22.30% | 3.57 names |
| C4 | 1,201 | 91.71% | 85.24% | 12.74% | 4.98 names |

The selection effect is candidate-specific. C2 is exactly invariant because its
finite feature support is still constrained by a 60-session warm-up in both
branches. C4 is most sensitive to the policy fork; its mean overlap is lowest
in 2025 at 89.60% and remains 91.90% in 2026 partial year. C3 is sparse and
has only 278 common selection dates, so its comparison remains support-limited.

## Interpretation boundary

The policy conflict changes actual decision sets for C1, C3, and C4; it is not
merely a larger-sample bookkeeping choice. However, overlap is not predictive
robustness, and a high overlap does not make either branch authoritative. No
candidate, era, policy, or population was admitted.

The result strengthens the existing `POLICY_AUTHORITY_MISSING` blocker:
future candidate comparisons must bind the policy first and must not mix masks.

## Reproducibility

- Script: `research/alpha_eligibility_selection_overlap_v1.py`
- Script SHA-256: `324489e8c58eeca0946e30f17d94c0a2e780eda020a646c0d576f108d19f94c4`
- Focused test: `tests/test_alpha_eligibility_selection_overlap_v1.py` (`1/1`)
- Test SHA-256: `5f1de7a86ec36d6cae7a3d7fd4a945489a712cb32aefb6feeaf75b1fb76c87ae`
- External result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-eligibility-selection-overlap\eligibility_selection_overlap_v1.json`
- External result SHA-256: `6f10edb5cae05fec82d9cfbe4ffe2f93aa95b30938ef70b4d9a0bc21e2818b72`
- Machine-readable result: `research_knowledge/eligibility_selection_overlap_v1.json`
- Panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Financial bundle SHA-256: `c6004832e651b380161ec216efb2020dddbe86419d89c4521f77aeb09335876b`
- Official sessions SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Tradability anchors SHA-256: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`

## Adjudication

| Gate | Result |
|---|---|
| Cross-policy Top-30 calculation | `PASS` |
| Eligibility policy authority | `BLOCKED / MISSING` |
| Candidate or era selection | `NO` |
| Predictive/capacity interpretation | `FORBIDDEN / NOT TESTED` |
| Protected boundary | `CLOSED` |
