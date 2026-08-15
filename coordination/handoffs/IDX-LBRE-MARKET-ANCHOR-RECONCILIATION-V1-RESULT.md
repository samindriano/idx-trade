# Handoff — LBRE / Market-Wide Free-Float Anchor Reconciliation V1 Result

from: Codex/LBRE-Market-Anchor-Reconciliation
to: ChatGPT/review
task_id: IDX-LBRE-MARKET-ANCHOR-RECONCILIATION-V1
model_used: gpt-5.6-luna
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `b2855061f470bc23e9aed6f91ebf8ec91e1b8e99`
branch: `data/idx-lbre-market-anchor-reconciliation-v1`
status: `REVIEW`
head_commit: see the final branch tip reported with this handoff

## Scope

Offline-only decomposition of the accepted 2025-12-31 comparison using the
immutable monthly LBRE history and historical market-anchor artifacts. No
network, acquisition/redownload, parser or lineage change, source
preference, daily state, forward-fill, effective supply, Foreign Flow,
features, models, or outcomes.

## Parent artifacts verified

- Monthly history manifest:
  `e134809a1f1b745daf2f21c33ab7db78c38d1d5d520f5320564359d5b865bd86`
- Historical snapshot manifest:
  `7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`

## Result

The 923-ticker union contains 885 overlaps. Required six-way classes:

```text
EXACT_AGREE                 260
SHARES_AGREE_PCT_DIFF       616
SHARES_DIFF_PCT_AGREE         0
SHARES_AND_PCT_DIFF           9
LBRE_ONLY                     0
MARKET_ONLY                  38
```

The prior 625 conflicts therefore contain 616 identical-share rows (98.56%)
and 9 genuine share-count conflicts (1.44%). The nine absolute share deltas
range from 400,000 to 2,986,991,880 shares, and relative differences range
from 0.064% to 50.061% of LBRE shares. The largest cases are HOKI, TRIN,
OLIV, WOOD, UNTR, and PANR; the full table and evidence sample are in the
external artifact root.

All 885 LBRE overlaps have listed shares available for the internal implied
percentage diagnostic. No official percentage was replaced. The publication
comparison has LBRE before the market anchor for 882 rows, after for BHIT,
EKAD, and NISP, and equal for none; median LBRE-minus-market delta is
-3,682,606 seconds.

Final verdict:

`LBRE_FF_SHARES_DENOMINATOR_PARTIAL_CONFLICT_REVIEW_REQUIRED`

LBRE shares are conditionally usable for the 876 explicitly share-identical
overlap rows, but not as a blanket denominator source. The nine conflicting
overlaps and 38 market-only rows remain explicit fail-closed gaps. No semantic
source preference was introduced.

## External artifacts

Root:
`D:\Documents\Project\idx-lbre-market-anchor-reconciliation-20260816-v1`

Manifest SHA-256:
`34fe46f9077fe8c6630fbec5f3682718f01cea1456d7bcb904fa7be6a9479840`

Manifest file count: `6`.

Durable files include parent verification, the full classified reconciliation,
class counts, delta distributions, publication-time comparison, and bounded
evidence-review rows.

## Repository changes

- `scripts/run_lbre_market_anchor_reconciliation.py`
  - deterministic six-class inventory including zero-count classes;
  - diagnostic-only share, percentage, implied-percentage, and publication
    deltas.
- `tests/test_lbre_market_anchor_reconciliation.py`
  - separate share/percentage classification axes;
  - reported percentage is not replaced by implied percentage;
  - zero-count class inventory remains explicit.
- Result checkpoint:
  `docs/checkpoints/2026-08-16_LBRE_MARKET_ANCHOR_RECONCILIATION_RESULT.md`

## Validation

- Focused tests: `3 passed`.
- Full pytest: `72 collected; 71 passed, 1 failed`.
- Known unrelated failure:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  (expects one conflict; current independent raw/vendor-adjusted conflict
  audit returns two). No storage file was modified.
- `git diff --check`: required before commit/push and reported in final handoff.

## Stop boundary

Stop after ChatGPT independent review. Do not begin daily free-float state,
market-wide acquisition, effective-supply reconstruction, Foreign Flow
integration, features, models, or outcomes automatically.
