# Handoff

from: MAIN / DATA
to: ChatGPT reviewer / MAIN
task_id: IDX-DATA-002C-PRICE-REPAIR
model_used: Luna xhigh root; direct sequential execution
reasoning_level: LIGHT
source_repository: samindriano/idx-trade
source_commit: 5e6f6bd38a5af3ee11bca93a15f50fadf9515eb2
branch: data/idx-data-002c
head_commit: handoff commit follows
scope: Independently repair FREN, MASA, and MFIN official missing ACTIVE prices; implement a generic cross-validated secondary-open witness; stop fail-closed when the public secondary source is unavailable. No 252, 1260, modelling, IDX-VAL-002, or main merge.
files_changed:
- src/idx_trade/secondary_open_witness.py
- tests/test_secondary_open_witness.py
- docs/PROJECT_LEDGER.md
- docs/checkpoints/2026-08-09_FULL_MARKET_504_SECONDARY_OPEN_UNAVAILABLE.md
- coordination/handoffs/IDX-DATA-002C-PRICE-REPAIR-DATA.md
findings:
- Regenerated missing ACTIVE counts: FREN 196, MASA 22, MFIN 249.
- Official IDX fallback filled 0 FREN, 0 MASA, and 77 MFIN rows; 390 rows remain missing.
- Official unresolved diagnostics are OFFICIAL_OHLC_MISSING_OR_NONPOSITIVE.
- Automatic semantics: FREN=false, MASA=false, MFIN=true.
- Investing.com normal public requests returned HTTP 403 for all three pages; no bypass was attempted.
decisions_made:
- Preserve official IDX as the authority for ACTIVE, H/L/C, and Volume.
- Accept a secondary Open only with exact H/L/C cross-validation and explicit dual-source provenance.
- Preserve existing primary rows and fail closed on unavailable secondary access.
- Do not run the 126/504 ladder because missing ACTIVE prices remain.
decisions_needed:
- Review whether a normally accessible public secondary OHLC source or authoritative opening-price evidence can be supplied without bypassing access controls.
blocking_risks:
- FREN 196 missing ACTIVE prices.
- MASA 22 missing ACTIVE prices.
- MFIN 172 missing ACTIVE prices.
- Secondary source unavailable under normal request (HTTP 403).
validation_run:
- python -m pytest tests -q -> 149 passed, 3 warnings.
- Targeted witness tests -> passed.
- Official fallback sessions -> FREN 196, MASA 22, MFIN 249; fetch_errors=0.
recommended_next_action: Obtain a normally accessible secondary OHLC source or authoritative official opening-price evidence, then rerun the three exact fallbacks and only certify/run 1260 after a genuine 504 PASS.
