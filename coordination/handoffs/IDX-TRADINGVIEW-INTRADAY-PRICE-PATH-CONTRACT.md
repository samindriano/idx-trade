# Handoff

from: Codex/TradingView-Price-Path-Contract
to: ChatGPT independent review
task_id: IDX-TRADINGVIEW-INTRADAY-PRICE-PATH-CONTRACT
model_used: Luna xhigh root; worker unavailable because concurrency limit was full
reasoning_level: xhigh
source_repository: C:\\Users\\Sam\\OneDrive\\Documents\\Project\\idx-trade
source_commit: 7328c4905a85fb0bf7486adc3adc96f2ffa2bc27
branch: data/tradingview-intraday-price-path-contract-v1
head_commit: b5351e585f93435ee2fa8ec9c897612798ca540a
scope: Freeze TradingView IDX historical intraday semantic fields, permitted path feature families, session-state handling, and prohibited Open/session interpretations. Design-only.
files_changed: config/tradingview_intraday_price_path_contract_v1.json; src/idx_trade/tradingview_intraday_price_path_contract.py; tests/test_tradingview_intraday_price_path_contract.py; docs/TRADINGVIEW_INTRADAY_PRICE_PATH_CONTRACT_V1.md; docs/checkpoints/2026-08-14_TRADINGVIEW_INTRADAY_PRICE_PATH_CONTRACT_RUNTIME.md; coordination/handoffs/IDX-TRADINGVIEW-INTRADAY-PRICE-PATH-CONTRACT.md; coordination/TEAM_STATUS.md
findings: Official daily Open and raw first regular-session TradingView Open must remain separate. Raw regular-session H/L/C/V path features are semantically usable only with exact session/state validation. Stage-1 supports strong matched-row fidelity and zero known active-session TV misses, but the canonical activity checkpoint still has 195 UNCERTAIN_CANONICAL_ROW_MISSING sessions and 86.80% conservative lower bound.
decisions_made: Freeze the semantic schema; do not treat TV regular Open as auction Open; do not mix extended bars; do not repair/rescale/substitute raw values. Mark acquisition/admission V2 not ready until the 195-session evidence conflict is checkpointed and resolved.
decisions_needed: Independent review of the semantic contract and whether a dated official evidence artifact resolves the 195 activity rows. No bulk acquisition or modeling is proposed.
blocking_risks: Current canonical Stage-1 checkpoint contradicts the task-provided claim that 195/195 TV-missing sessions are official zero Volume/Value/Frequency. Stage-1 auction identity remains unproven. 2021/2024 live probes were unresolved after symbol load.
validation_run: focused contract tests 6 passed; full pytest 45 passed and 1 unchanged storage assertion failed (`raw_close` plus `vendor_adj_close` conflicts versus expected 1); no provider calls; git diff --check pending after final edits.
recommended_next_action: Review the contract. If the 195-session evidence is independently checkpointed and resolved, create a separate frozen acquisition/admission V2 spec; otherwise stop fail-closed.
