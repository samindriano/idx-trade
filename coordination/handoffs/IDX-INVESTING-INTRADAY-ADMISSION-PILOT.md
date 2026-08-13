# Handoff

from: Codex
to: ChatGPT
task_id: IDX-INVESTING-INTRADAY-ADMISSION-PILOT
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: be2c38eb2d93ad7ea95202b52cbe92626c5a8c3b
branch: data/investing-intraday-admission-pilot-v1
head_commit: pending runtime checkpoint commit
scope: Frozen Investing.com 1-hour Jakarta common-stock secondary-source admission pilot; 50 deterministic tickers over old/mid/recent bounded official-calendar windows.
files_changed: config/investing_intraday_admission_pilot_v1.json; docs/INVESTING_INTRADAY_ADMISSION_PILOT_V1.md; src/idx_trade/investing_admission.py; scripts/run_investing_intraday_admission_pilot.py; tests/test_investing_admission.py; pyproject.toml; coordination/TEAM_STATUS.md
findings: Runtime reached Investing with validated curl-cffi headers but failed the frozen admission contract: 67 AVAILABLE, 13 NO_DATA, 58 PROVIDER_ERROR; 229 attempts, 91 retries, 33 recovered, 0 HTTP 429; all three coverage eras failed and overall HLC exact was 79.2219%.
decisions_made: Exact identity only; PIT listing boundaries; timezone-aware Asia/Jakarta normalization; no adjusted OHLCV or CA-factor inference; all three eras must pass frozen gates.
decisions_needed: Independent ChatGPT review of runtime evidence and whether a separately preregistered remediation is worth authorizing.
blocking_risks: Investing coverage, within-listed no-data, daily fidelity, and known external corporate-action controls may fail the admission gates.
validation_run: focused pilot tests 8 passed; full repository suite 47 passed, 1 pre-existing tests/test_storage.py failure; git diff --check passed; canonical panel SHA unchanged; final artifact manifest SHA 2316dd2302451ffb2f5a53fd8ff1f4fcf0296979c81a370c16f94560fc33cc7e.
recommended_next_action: Independent ChatGPT review; do not begin bulk acquisition, canonical integration, model work, Path Risk/O2 work, or outcome access.
