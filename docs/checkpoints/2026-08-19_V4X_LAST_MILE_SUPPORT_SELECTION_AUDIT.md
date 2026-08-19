# V4-X Last-Mile Support / Selection Audit — 2026-08-19

Status: `IMPLEMENTED_LOCAL_EXECUTION_PENDING`

Branch: `research/v4x-critical-alpha-audit-v1`

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

## Attack B — future target-observability selection

Quantify whether target observability is systematically related to frozen alpha rank using:

- observable vs unobservable mean alpha-rank difference;
- daily alpha-rank / observability correlation;
- two-sample KS distance;
- top-decile and bottom-decile observability relative to overall coverage;
- target-state breakdown by mean alpha rank.

This diagnostic cannot reconstruct missing outcomes and therefore cannot prove missing-at-random. It only measures visible selection pressure.

## Inputs pinned

- historical V4-3R manifest SHA-256: `05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef`
- frozen panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- frozen calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

## Interpretation boundary

Results are descriptive historical audit evidence only. They must not be used to retune V4-X1 or to relabel historical-development evidence as fresh prospective confirmation.
