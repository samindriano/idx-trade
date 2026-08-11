# Handoff

from: Codex  
to: MAIN / independent ChatGPT review  
task_id: IDX-RANKING-OHLCV-O1  
model_used: Luna xhigh orchestra DIRECT/one-writer  
reasoning_level: xhigh  
source_repository: `samindriano/idx-trade`  
source_commit: `b9567f212bf7af94ad58bd6b78bfe192ee52ee78`  
branch: `research/idx-ranking-ohlcv-o1-v1`  
head_commit: pending push  

scope: Execute the frozen historical-development OHLCV O1 experiment only.

files_changed:
- `src/idx_trade/ohlcv_o1_research.py`
- `tests/test_ohlcv_o1_research.py`
- `docs/checkpoints/2026-08-12_OHLCV_O1_RESEARCH_RUNTIME.md`
- `coordination/handoffs/IDX-RANKING-OHLCV-O1.md`

findings:
- Exact preserved common-support population: 278,168 rows, 729 tickers.
- Exact V3-B canonical feature order/hash, H10 labels, HGB parameters, and six
  V2F1-V2F6 fold identities were verified before fitting.
- All four models used identical rows, labels, folds, evaluator, and HGB
  parameters; O1 additions were limited to overnight_gap and intraday_return.
- Runtime completed without network calls or fresh-forward outcome access.
- Final decision: `O1_NO_SURVIVOR`.

decisions_made:
- No O1 challenger meets the frozen survivor rule.
- No canonical V3-B artifact was overwritten.
- No O2/Open-geometry/interaction experiment was started.

decisions_needed:
- Independent ChatGPT review of the persisted checkpoint and external artifact
  manifest.

blocking_risks:
- O1A/O1B/O1C show intermittent positive fold deltas, but all have negative
  lower-quartile paired PR-AUC deltas; O1B also shows a clear aggregate
  ranking-guardrail reversal under the recorded rule.

validation_run:
- focused pytest: `5 passed`;
- full pytest: `279 passed, 5 warnings`;
- external runtime: 24 fits / six folds / approximately 80.8 seconds;
- external artifact manifest SHA-256:
  `2441f9fcadc9a496ed5d15306bb7bbcb87c9978ecdc26033f5bd7619c2d08714`.

recommended_next_action:
Stop for independent ChatGPT review. Do not begin another Open-derived
experiment or fresh-forward evaluation from this branch without explicit
authorization.
