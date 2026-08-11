# Handoff

from: Codex
to: Independent ChatGPT review
task_id: IDX-OPEN-RESEARCH-COVERAGE-GATE
model_used: Codex direct executor
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `97b4075410cf80b01e9eb33b2883aece3475c0c5`
branch: `data/idx-open-research-coverage-gate-v1`
head_commit: pending

## scope

Executed only the frozen Open research-grade coverage gate. Applied exactly
the accepted SMBR 2023-03-14 TradingView candidate to a new external
read-only derivative overlay. Reused the frozen V3-B Structure-Lite final
refit population and preserved the immutable panel.

## files_changed

- `src/idx_trade/open_research_coverage.py`
- `tests/test_open_research_coverage.py`
- `docs/checkpoints/2026-08-12_OPEN_RESEARCH_COVERAGE_GATE_RUNTIME.md`
- `coordination/handoffs/IDX-OPEN-RESEARCH-COVERAGE-GATE.md`

## findings

- Global Open coverage after SMBR overlay: 938,140/981,940 = 95.5394423%.
- Exact V3-B final-refit population: 292,633 rows / 737 tickers.
- V3-B Open known/missing: 280,044 / 12,589 = 95.6980245% coverage.
- All five causal Open features usable on 278,168 rows = 95.0569485%.
- 652 tickers fully known, 78 partial, 7 fully missing.
- Top 20 tickers contain 7,471/12,589 missing rows = 59.3455%.
- Worst session: 2021-06-03, 175/209 = 83.7321% coverage.
- Remaining-missing provenance: TV H/L/C disagreement 4,887; TV history
  window unavailable 4,632; corporate-action/outside TV target 2,101; TV
  identity/provider error 969.
- Immutable panel SHA remained
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## decisions_made

- Recommendation: `CONDITIONAL_PASS_FOR_OHLCV_ALPHA_RESEARCH`.
- Any future baseline-vs-OHLCV comparison must use the exact same
  278,168-row Open-feature common-support intersection.
- Historical 2021/2022 and concentrated missing tickers require explicit
  reporting/restriction; no rows were silently removed to improve coverage.

## decisions_needed

- Independent review to accept/reject the conditional research gate.
- If accepted, define the exact restricted common-support policy before any
  OHLCV challenger implementation; this run did not train or tune anything.

## blocking_risks

- Unrestricted V3-B rows are not fully Open-complete.
- Seven V3-B tickers have zero known Open rows; the top 20 concentration is
  59.3455% of remaining missingness.
- 2021 and 2022 coverage is 88.0497% and 92.3195%, respectively.

## validation_run

- Focused pytest: 3 passed.
- Full pytest: 274 passed; 6 existing `FutureWarning` locations; 0 failures.
- Runtime network calls: 0.
- Training/tuning: not performed.
- External output root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\open_research_coverage_gate_v1_20260812`
- Artifact manifest SHA:
  `7e15220bedc3f12c9576f43e8e0efcb8f906301828788a56fca36c1a5caf9e87`

## recommended_next_action

Stop for independent ChatGPT review. Do not train an OHLCV model, access
fresh-forward outcomes, modify the immutable panel, repair corporate actions,
run providers, alter V3-B, or start execution-grade promotion.
