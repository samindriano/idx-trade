# Handoff

from: Codex
to: ChatGPT independent review
task_id: IDX-TRADINGVIEW-HISTORICAL-PRICE-PATH-V2-1-REMEDIATION
model_used: Luna xhigh / DIRECT
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `429917f`
branch: `data/tradingview-historical-price-path-v2-1-remediation`
head_commit: `429917f`
scope: Continue the existing V2.1 remediation; harden the confirmed data/acquisition contracts, reuse the completed offline evidence, freeze the preregistration, and run at most the five-control anonymous TradingView depth preflight.
files_changed: `config/tradingview_historical_price_path_v2_1.json`; `src/idx_trade/tradingview_price_path_v2.py`; `src/idx_trade/tradingview_price_path_v2_1.py`; `adapters/tradingview/index.js`; `scripts/run_tradingview_historical_price_path_v2_1_offline.py`; `scripts/finalize_tradingview_historical_price_path_v2_1_offline.py`; `scripts/run_tradingview_historical_price_path_v2_1_preflight.py`; focused V2/V2.1 tests; preregistration checkpoint.
findings: Offline mapping is complete and unambiguous; UNKNOWN remains 592; corrected CA quarantine is 12; theoretical symbol-error ceiling clears frozen coverage gates; official Stock Summary HLCV is diagnostic and not supported as the admission oracle.
decisions_made: Keep the failed V2 verdict unchanged. Use 500/5000/3 depth with required-start early stop. Keep immutable preregistration separate from runtime marker/manifests. Do not silently resolve provider symbol errors or substitute the Stock Summary oracle.
decisions_needed: Independent review of the preregistration and the bounded preflight result after the five authorized controls.
blocking_risks: Sixteen exact `IDX:<ticker>` provider SYMBOL_ERROR cases remain; a full 978-ticker acquisition has not run and remains unauthorized in this lane. Any preflight depth, structural, identity, or boundary failure is fail-closed.
validation_run: `PYTHONPATH=src;.` focused V2/V2.1 tests: 22 passed; full pytest: 81 passed; `node --check adapters/tradingview/index.js`: passed; `git diff --check`: passed. No provider requests yet in V2.1.
artifact_root: `D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_1_final_20260816_retry5`
preregistration_sha256: `5fd9b2eefc69fd0c5a29e9d82e790e9f8490583e82e63522f45c815788b5574e`
prereg_manifest_sha256: `795b48bd4c53758ac59308f44658e0ad65733d7da77f743c24c856e1f029400b`
recommended_next_action: Run only the exact five-control bounded depth preflight after confirming these hashes; do not start full acquisition or downstream modeling.
