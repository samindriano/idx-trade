# Handoff

from: ChatGPT/TradingView-Activity-Forensics
to: local runtime / independent review
task_id: IDX-TRADINGVIEW-INTRADAY-ACTIVITY-FORENSICS
branch: data/tradingview-intraday-activity-forensics-v1
prepared_head: 9848ed71b0eca425a23c68a992afa5aecb63b3e2
scope: Offline-only activity-aware reclassification of missing certified ticker-sessions from the frozen TradingView 2021-2026 admission pilot.
scientific_boundary: The frozen pilot verdict remains TRADINGVIEW_INTRADAY_ADMISSION_REJECTED. This diagnostic cannot retroactively rescue or change it.
implementation: config/tradingview_intraday_activity_forensics_v1.json; src/idx_trade/tradingview_activity_forensics.py; scripts/run_tradingview_intraday_activity_forensics.py; prepared checkpoint.
inputs_required: Exact local admission artifact root D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_intraday_admission_pilot_v1_20260814 and the exact canonical panel SHA 67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76.
blocker: Those external local bytes are not accessible from the ChatGPT GitHub connector/runtime, so no exact missing-session numerical result is claimed yet.
network_calls: 0
next_runtime_action: Execute the offline runner against the exact hash-pinned local inputs, preserve the output root, then return summary.json plus artifact manifest for independent review. Do not call TradingView or any provider.
