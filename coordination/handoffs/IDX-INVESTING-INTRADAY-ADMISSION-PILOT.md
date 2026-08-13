# Handoff

from: Codex
to: ChatGPT
task_id: IDX-INVESTING-INTRADAY-ADMISSION-PILOT
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: be2c38eb2d93ad7ea95202b52cbe92626c5a8c3b
branch: data/investing-intraday-admission-pilot-v1
head_commit: pending preregistration commit
scope: Frozen Investing.com 1-hour Jakarta common-stock secondary-source admission pilot; 50 deterministic tickers over old/mid/recent bounded official-calendar windows.
files_changed: config/investing_intraday_admission_pilot_v1.json; docs/INVESTING_INTRADAY_ADMISSION_PILOT_V1.md; src/idx_trade/investing_admission.py; scripts/run_investing_intraday_admission_pilot.py; tests/test_investing_admission.py; pyproject.toml; coordination/TEAM_STATUS.md
findings: Contract frozen before network. No canonical panel/model/outcome/O2/Path Risk changes are allowed.
decisions_made: Exact identity only; PIT listing boundaries; timezone-aware Asia/Jakarta normalization; no adjusted OHLCV or CA-factor inference; all three eras must pass frozen gates.
decisions_needed: Independent ChatGPT review of runtime evidence and admission label.
blocking_risks: Investing coverage, within-listed no-data, daily fidelity, and known external corporate-action controls may fail the admission gates.
validation_run: focused pilot tests 6 passed; full repository suite 44 passed, 1 pre-existing tests/test_storage.py failure; git diff --check passed; curl_cffi 0.13.0 available.
recommended_next_action: Review preregistration commit, then authorize/review bounded runtime artifacts; do not begin bulk acquisition.
