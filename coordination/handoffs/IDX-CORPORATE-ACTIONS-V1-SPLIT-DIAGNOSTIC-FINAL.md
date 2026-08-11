# Handoff — Corporate Actions V1 Split Diagnostic

from: Codex MAIN  
to: ChatGPT reviewer / next Corporate Actions V1 task  
task_id: IDX-CORPORATE-ACTIONS-V1-SPLIT-DIAGNOSTIC-FINAL  
model_used: GPT-5.6 Luna xhigh  
reasoning_level: xhigh  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: `957b7d0c2fc6ef8b6138ab959aabfb2cd01eefdf`  
branch: `data/corporate-actions-v1`  

## Scope

Final bounded stock-split diagnostic using 39 logical positive-ratio official
IDX events and the existing 1260-session price panel. No candidate date was
promoted and no price was adjusted.

## Result

Verdict: `SPLIT_METADATA_DISCOVERY_ONLY_CANONICAL_PROMOTION_FAIL_CLOSED`.

`scan_split_candidate_transitions(..., window_sessions=10)` found 1/39
matches within both 10% and 20%. The only match was FISH, offset -5 observed
sessions. There was no offset cluster. Best relative-error quantiles were
0.000 / 0.839 / 0.909 / 3.666 / 3.832 / 21.198 (min/p10/p25/median/p75/max).

FISH official IDX/issuer documents prove the exchange schedule is:
old-nominal last trading 2025-09-08 and new-nominal Regular/Negotiated trading
from 2025-09-09. The panel's 10x OHLC transition occurs on 2025-09-01, while
the provider `stock_splits=10` flag appears on 2025-09-09. The price match is
therefore a provider/date-alignment anomaly, not a canonical effective date.

The repository's provider path is Yahoo/yfinance with `auto_adjust=False`, but
the empirical panel behavior is mixed: 37/39 events have nearby provider split
flags while only 1/39 has a mechanical OHLC transition. `raw_open/raw_close`
are aliases, not independent proof of exchange-unadjusted semantics.

## Evidence

- external scan summary SHA-256:
  `7109c9b9112f5844a0fd2f4571a99899b2029896d23c1a0cd83a67837463ce98`;
- FISH theoretical-price PDF SHA-256:
  `10cf9e9f4a25e86163eeb9a9ed3c72b09d76f8213fc6f62cd71a7a90988e0c58`;
- FISH IDX listing PDF SHA-256:
  `019eb57b1963ee36290bf94a09280359141600a50fcdb7b2fd4c48e33c8bfcd6`;
- FISH issuer correction PDF SHA-256:
  `e76d7d41988c39169fc8385a77b444fb696bf4de92d67dbef79b5e1d0d3a493b`.

All raw/diagnostic/PDF captures remain outside Git under
`D:\Documents\Project\idx-trade-corporate-actions-20260811`.

## Validation

- focused: `python -m pytest tests/test_corporate_action_diagnostics.py -q` — 3 passed;
- full: `python -m pytest -q` — 482 passed, 0 failed, 3 existing warnings.

## Next safe action

Keep split metadata as discovery evidence only. If canonical event promotion is
needed later, build a separate official-document effective-session table and a
provider-specific revision/alignment contract. Do not infer it from nearby
price matching.
