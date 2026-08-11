# OHLCV O2 Final Refit Direction

Date: 2026-08-12 (Asia/Jakarta)
Decision: `O2_FULL_3_FINAL_REFIT_DIRECTION_RECORDED`

The independent minimality review selected the accepted full three-feature O2 geometry representation for final freeze. The next lane should perform exactly one historical final refit on the exact 278,168-row common-support population, using the canonical V3-B 33 features plus `open_position`, `open_to_high`, `open_to_low`, the accepted feature-order hash, frozen HGB pipeline/parameters, H10 target semantics, and no tuning.

The final-refit lane must produce deterministic model/data/feature hashes and a forward-scoring contract, but must not access post-2026-07-31 outcomes, overwrite canonical V3-B, or start forward evaluation automatically. A separate forward-validation specification is required after final-refit review.
