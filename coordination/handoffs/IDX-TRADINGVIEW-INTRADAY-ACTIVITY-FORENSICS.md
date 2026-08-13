# Handoff

from: ChatGPT/TradingView-Activity-Forensics
to: local runtime / independent review
task_id: IDX-TRADINGVIEW-INTRADAY-ACTIVITY-FORENSICS
branch: data/tradingview-intraday-activity-forensics-v1
prepared_head: 97b1f01c4ec4171e438cff6e4ad9118afde7e3b8
scope: Offline-only activity-aware reclassification of missing certified ticker-sessions from the frozen TradingView 2021-2026 admission pilot.
scientific_boundary: The frozen pilot verdict remains TRADINGVIEW_INTRADAY_ADMISSION_REJECTED. This diagnostic cannot retroactively rescue or change it.
implementation: config/tradingview_intraday_activity_forensics_v1.json; src/idx_trade/tradingview_activity_forensics.py; scripts/run_tradingview_intraday_activity_forensics.py; prepared checkpoint.
inputs_required: Exact local admission artifact root D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_intraday_admission_pilot_v1_20260814 and the exact canonical panel SHA 67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76.
runtime_head: recorded after offline runtime checkpoint commit
output_root: D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_intraday_activity_forensics_v1_20260814
result: 1,477 listed certified sessions; 1,282 canonical-active sessions; 1,282 TV-covered active sessions; 0 true TV misses; 0 explained no-trade sessions; 195 uncertain sessions, all `UNCERTAIN_CANONICAL_ROW_MISSING`. Activity-aware coverage is 100.00% overall and every year; conservative lower bound is 86.80% overall, with yearly lower bounds 94.71%, 94.40%, 88.00%, 84.80%, 78.00%, and 81.60% for 2021-2026. Automatic interpretation: `ACTIVITY_AWARE_COVERAGE_INCONCLUSIVE_DUE_TO_UNCERTAIN_ACTIVITY`.
output_hashes: activity_support.csv=6963fefc5ffa0af0732628b46218a98a8401c729ace0d5c9cc73b14a413777d0; missing_session_forensics.csv=d03f8f2e7399d4337bbb1c550b6330d9bf9a1850fb2d4c967e184d220ab6ef9f; summary.json=5778169260cd0712ee75a1228e2d5ddf1f5d05ac3933e6a99c82d10b2176506b
panel_sha256_before_after: 67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76
blocker: Resolved for this local runtime. The exact external bytes were available; no provider/network calls were made.
network_calls: 0
validation: focused TradingView tests 14 passed; full pytest 53 passed and 1 pre-existing storage assertion failed; git diff --check passed. The frozen admission verdict remains `TRADINGVIEW_INTRADAY_ADMISSION_REJECTED`.
next_runtime_action: Independent ChatGPT review of the runtime checkpoint and external output hashes. Do not call TradingView or any provider, rerun the pilot, change the verdict, or start downstream research.
