# V4-X Last-Mile Support / Selection Audit — 2026-08-19

Status: `COMPLETE_PASS_NO_CRITICAL_ERROR_FOUND`

Branch: `research/v4x-critical-alpha-audit-v1`

Canonical final audit record:

`docs/checkpoints/2026-08-19_V4X_HISTORICAL_ALPHA_CRITICAL_AUDIT_FINAL.md`

## Purpose

Final historical red-team checks before closing the V4-X historical-alpha audit. These checks only re-evaluate already-consumed V4-3R scores and immutable frozen inputs. They do not fit, score, retune, or replace V4-X1, call providers, materialize new targets, or access protected forward outcomes.

## Attack A — exact official-session support

Quantify whether common-support Spearman IC survives after restricting scored/observable rows to exact official-session history.

Reported filters:

1. all common-support rows;
2. exact shift-5;
3. exact shift-5 and shift-20;
4. exact endpoint 5/20/60 row semantics;
5. strict actual-feature-window semantics: shift-5, shift-20, ATR14 continuity, rolling-20 continuity, and rolling-60 continuity.

The strict test is intentionally stronger than the earlier descriptive row-lag census.

### Result

Challenger consensus:

- all common support: `0.09545975125676774` mean daily Spearman RankIC;
- exact shift-5: `0.09572507969929642`;
- exact shift-5 + shift-20: `0.09715105723281318`;
- exact endpoint 5/20/60: `0.08303488625349013`;
- strict actual-feature-window support: `0.08327323251280924`.

Strict support retains `89.9685%` of observable rows and all 600 validation dates. Consensus stays positive in 6/6 folds.

The same strict-support reduction appears in the control (`0.08979323509925058` → `0.07760894276869784`), while Geometry3's common-support incremental advantage remains effectively unchanged (`~+0.00567`).

Interpretation: sparse/irregular ticker history materially affects the absolute V4-family IC level, but it is not future leakage and does not explain Geometry3's incremental improvement.

## Attack B — future target-observability selection

Quantify whether target observability is systematically related to frozen alpha rank using:

- observable vs unobservable mean alpha-rank difference;
- daily alpha-rank / observability correlation;
- two-sample KS distance;
- top-decile and bottom-decile observability relative to overall coverage;
- target-state breakdown by mean alpha rank.

### Result

Challenger consensus:

- overall observable rate: `0.8826880129934163`;
- observable pooled mean alpha rank: `0.4991265400364243`;
- unobservable pooled mean alpha rank: `0.506572155662444`;
- pooled mean-rank gap: `-0.007445615626019642`;
- mean daily alpha/observability correlation: `-0.008701511300880576`;
- pooled KS: `0.02046629796278071`;
- top-decile observable rate: `0.8850636661217741`;
- bottom-decile observable rate: `0.8842570106677249`.

Missingness differs by failure subtype, so the audit does not claim missing-at-random. However, aggregate score-rank selection is small and tail coverage is almost identical to overall coverage. No material observability-selection mechanism capable of explaining RankIC near `0.095` was found.

## Inputs pinned

- historical V4-3R manifest SHA-256: `05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef`
- frozen panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- frozen calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

## Interpretation boundary

Results are descriptive historical audit evidence only. They must not be used to retune V4-X1 or to relabel historical-development evidence as fresh prospective confirmation.

Final verdict and all preceding audit layers are preserved in `2026-08-19_V4X_HISTORICAL_ALPHA_CRITICAL_AUDIT_FINAL.md`.