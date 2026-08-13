# Handoff — Ranking V3-A Recency Runner Implemented / Local Outcome Run Pending

Date: 2026-08-10 (Asia/Jakarta)

Status: **IMPLEMENTATION COMPLETE; F1-F4 OUTCOME RUN REQUIRES USER-LOCAL FROZEN DATA STORE**

## Implemented state

Branch: `research/idx-ranking-v2-spec-v1`

Implementation files:

- `src/idx_trade/ranking_v3_recency.py`
- `tests/test_ranking_v3_recency.py`

Implementation lineage:

- initial runner commit: `cab1ad4f0a78bcee63ac75d10997fef1f1122f85`;
- focused tests commit: `57f2b955bee3b48ace31f7eb22327e8d224adef0`;
- sealed-reference-path fix / current code commit: `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f`.

Controlling research docs remain:

- `docs/RANKING_V3_RECENCY_SPEC_V1.md`;
- `docs/RANKING_V3_RECENCY_SPEC_REVIEW_ADDENDUM_V1.md`;
- `coordination/handoffs/IDX-RANKING-V3-RECENCY-DISCOVERY-RUN.md`.

## What is implemented

The runner:

1. verifies the exact frozen prepared-cache and manifest SHA-256;
2. verifies the frozen spec SHA/Git blob and review-addendum Git blob;
3. loads only the exact V2 `HGB_XS_MARKET` 25-feature prepared table;
4. fits the exact uniform V2 control on V2F1-V2F4;
5. hash-verifies the frozen historical V2 HGB_XS_MARKET reference summary/prediction artifact;
6. materializes reference outcome rows only for F1-F4 through a Parquet filter;
7. requires exact row identity/order, score and metric equivalence before recency variants may fit;
8. if equivalence passes, fits H=252 then H=504 sequentially on F1-F4 only;
9. computes the frozen discovery metrics/gates/tie rule;
10. writes immutable/hash-pinned metrics, predictions, models, profiling, verdict and executed-ledger artifacts;
11. explicitly blocks V2F5/V2F6 through the discovery-fold guard.

## Focused validation performed

No GitHub Actions run was available for the pushed commits.

A focused isolated ChatGPT-runtime harness executed the exact final implementation source and the frozen V2 model/metric semantics exercised by the new tests. Result:

`12 passed in 0.63 s`

This is not claimed as full repo pytest and does not replace the required local full suite.

## Why no score result is attached

The ChatGPT container does not mount the user's Windows research store, including the immutable prepared cache under `D:\Documents\Project\idx-trade-data-gate-20260808v\...` or the frozen historical HGB_XS_MARKET candidate prediction Parquet required by the mandatory control-equivalence gate.

Because those artifacts are required for a valid outcome-bearing run, no F1-F4 score was executed and no candidate verdict was fabricated.

## Local execution requirements

Before executing:

1. pull branch remote;
2. verify code is exactly `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f` or a later documentation-only descendant;
3. run full repo pytest and record exact result/warnings;
4. locate the frozen prepared-cache manifest corresponding to SHA `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
5. locate the original V2 HGB_XS_MARKET candidate directory containing:
   - `ranking_v2_hgb_xs_market_summary.json`;
   - `ranking_v2_hgb_xs_market_predictions.parquet`;
6. use a new empty output directory;
7. run the module below once.

Example PowerShell skeleton:

```powershell
$python = "python"
$repo = "C:\Users\Sam\OneDrive\Documents\Project\idx-trade"
$prepared = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet"
$manifest = "<PATH_TO_FROZEN_PREPARED_CACHE_MANIFEST>"
$reference = "<PATH_TO_ORIGINAL_HGB_XS_MARKET_CANDIDATE_DIRECTORY>"
$output = "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_recency_discovery_20260810"

Set-Location $repo
& $python -m idx_trade.ranking_v3_recency `
  --prepared-table $prepared `
  --prepared-manifest $manifest `
  --reference-v2-dir $reference `
  --output-dir $output `
  --code-commit "3e368f7d7d6fa1e8ce0d076039640aaeef06a27f" `
  --spec "docs\RANKING_V3_RECENCY_SPEC_V1.md" `
  --addendum "docs\RANKING_V3_RECENCY_SPEC_REVIEW_ADDENDUM_V1.md"
```

Do not guess the two placeholder paths. Locate the exact frozen artifacts and verify hashes first.

## Stop / safety boundary

The local run must stop after V3-A F1-F4 artifacts are produced and documented.

Still prohibited:

- score/load/summarize V2F5/V2F6 for V3-A;
- reserved post-2026-07-31 V2 forward outcome access;
- `FORWARD_OUTCOME_ACCESS_STARTED`;
- any recency rescue/tuning;
- V3-B or later lane execution;
- V3 integration/final confirmation;
- calibration, Stage 6, IDX-VAL-002, execution-PnL, Kelly, paper/live, or main merge.
