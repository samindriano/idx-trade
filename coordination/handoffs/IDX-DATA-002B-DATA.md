# Handoff

from: MAIN / IDX-DATA-002B
to: ChatGPT reviewer / MAIN
task_id: IDX-DATA-002B
model_used: Luna xhigh root and bounded workers
reasoning_level: LIGHT
source_repository: samindriano/idx-trade
source_commit: 2d10b5204ed3a21e7f93d9a7aa1294270744794b
branch: data/idx-data-002b
head_commit: ea75c36b85c97c173f24d98454a0d41ecc5e1763 (handoff commit follows)
scope: Add official IDX session fallback, official split/reverse-split evidence, fail-closed V1 data-gate semantics, tradability diagnostics, and fresh adversarial evidence. No modelling, IDX-VAL-002, trading, or merge to main.

## Files changed

- `src/idx_trade/providers/idx_sessions.py`: official IDX Daily Statistics publication-listing fallback when monthly Digital Statistics is empty or incomplete; source identity and fallback audit.
- `src/idx_trade/session_backfill.py`: persist per-month official source identity and reference.
- `src/idx_trade/providers/idx_corporate_actions.py`: official IDX Listing Activity Stock Split/Reverse Stock parser, directional share-total semantics, and Yahoo diagnostic cross-check.
- `src/idx_trade/data_gate.py`, `src/idx_trade/coverage.py`: `split_history_verified`, informational dividend state, and conditional price requirements.
- `src/idx_trade/providers/idx_tradability.py`, `src/idx_trade/tradability_pipeline.py`, `src/idx_trade/security_master.py`: deterministic Indonesian effective-date parsing, explicit manual/unknown diagnostics, and left-boundary coverage evidence.
- `src/idx_trade/adversarial.py`: pass the new split/dividend/price semantics flags into the gate.
- `tests/`: provider, coverage, gate, session, tradability, and adversarial regression coverage.
- `docs/DATA_GATE_RUNBOOK.md`: official-source and gate-policy updates.

## Findings

### Full validation

- `python -m pytest -c pyproject.toml tests`: `69 passed`.
- Final executable diff check: `git diff --check` passed before commit.
- Required base commits `f2b76e0b3ec0f9f3c5cada0db20cd72f9075c231` and `2d10b5204ed3a21e7f93d9a7aa1294270744794b` remain ancestors of the review branch.

### Official IDX Exchange-Day result

- June 2026: `20` sessions from `IDX_DIGITAL_STATISTICS_DAILY_TRADING_TABLE`.
- July 2026: `23` sessions from `IDX_DAILY_STATISTICS_PUBLICATION_LISTING`, `2026-07-01` through `2026-07-31`, with `0` weekend rows.
- Fresh June-July result: `43` sessions, `2026-06-02` through `2026-07-31`, `2/2` months parsed, `0` month errors, `complete=true`, and one July fallback month.
- Yahoo/JCI were not used as Exchange-Day truth. Official IDX references are the Digital Statistics API and Daily Statistics publication listing.

### Split/reverse-split verification

- Official IDX Listing Activity audit window: `2023-01-01` through `2026-08-08`; `38` Stock Split rows and `0` Reverse Stock rows.
- Yahoo was used only for cross-checking: `22 MATCH`, `16 IDX_RATIO_UNAVAILABLE` for invalid/sentinel official share totals, `5 YAHOO_ONLY`, and `0 MISMATCH`.
- The parser interprets IDX `JumlahSaham` as action amount and `JumlahSahamSetelahTindakan` as total after action; it derives old/new totals directionally and keeps invalid ratios unknown. IDX remains authoritative.
- No dividend-adjusted technical OHLC was created.

### Manual tradability diagnostics before vs after

- Before: `66 PARSED`, `16 MANUAL_REVIEW` (`11 EFFECTIVE_DATE_NOT_FOUND`, `5 MULTI_ACTION_INTRADAY_DOCUMENT`); compiler diagnostics were `10 UNMATCHED_RESUME` and `2 REDUNDANT_SUSPEND`.
- After fresh rerun: `71 PARSED`, `11 MANUAL_REVIEW`; compiler diagnostics `0`.
- Remaining manual rows: `5 MULTI_ACTION_INTRADAY_DOCUMENT`, `5 PARTIAL_SESSION_OR_CALL_AUCTION_RESUME`, and `1 AMBIGUOUS_EFFECTIVE_DATE` for a continuation document with no new effective date. These remain fail-closed.
- Deterministically recovered wording includes `pada perdagangan tanggal`, weekday-qualified Session-I dates, and `Pencabutan Penghentian Sementara` with a pre-opening date.
- Independent official snapshot reconciliation remains `0/5` matched (`ALMI`, `BCIC`, `DEAL`, `FASW`, `FISH`); all five reconstruct as `UNKNOWN`, not invented `ACTIVE` or `SUSPENDED`.

### Tradability coverage window

- The narrowest public-source reach is the rolling three-year announcement listing, approximately `2023-08-08` through `2026-08-08` for this run.
- No clean historical window is claimed. Public reach does not prove discovery completeness, and there is no defensible left-boundary evidence establishing initial `ACTIVE` state. The coverage window remains incomplete/unknown.

### Adversarial DATA GATE before vs after

- Before: `0/35` passed; all `35` had `SESSION_COVERAGE_INCOMPLETE` and `CORPORATE_ACTIONS_UNVERIFIED`; `5` additionally had `PRICE_SEMANTICS_UNVERIFIED`.
- After fresh rerun with the official 43-session calendar and fresh tradability output: `0/35` passed; all `35` remain blocked only by `SESSION_COVERAGE_INCOMPLETE`.
- After the conditional-price change, zero expected active sessions do not add split-history or price-semantics blockers. The gate still fails because unknown tradability is not treated as active.

## Decisions made

- Use official IDX Daily Statistics as the July fallback; never use Yahoo/JCI for session truth.
- Use IDX Listing Activity as authoritative for Stock Split and Reverse Stock; Yahoo is diagnostic only.
- Replace broad corporate-action verification with `split_history_verified`; dividend verification is informational and non-blocking for V1 technical-price construction.
- Preserve raw OHLC/vendor-adjusted separation and do not create dividend-adjusted technical OHLC.
- Preserve manual review for genuine multi-action, partial-session, call-auction, and ambiguous documents; do not infer initial ACTIVE state.
- Keep the public tradability coverage window incomplete and keep the adversarial gate failed.

## Decisions needed

- Decide whether an additional authoritative source can prove public-window discovery completeness and the left-boundary initial state.
- Decide how to resolve the five independent snapshot mismatches without converting `UNKNOWN` into a guessed state.
- Only after the data gate passes may MAIN consider `IDX-VAL-002`; this task did not start it.

## Blocking risks

- `SOURCE_DISCOVERY_INCOMPLETE`: public IDX announcement history is bounded and the left boundary/initial state is unproven.
- `TRADABILITY_RECONCILIATION_FAILED`: official snapshot remains `0/5` matched and reconstructed states remain `UNKNOWN`.
- `SESSION_COVERAGE_INCOMPLETE`: all 35 adversarial tickers remain blocked by unknown tradability in the evaluated window.
- No modelling, scoring, paper trading, or live trading was started.

## Validation run

- Full repository test suite: `python -m pytest -c pyproject.toml tests` -> `69 passed`.
- Fresh external runtime evidence includes official session source reports, corporate-action/Yahoo cross-check reports, tradability parse/compile reports, snapshot reconciliation, and adversarial gate reports. Runtime market data, PDFs, parquet files, and artifacts were kept outside Git.

## Recommended next action

`BLOCKED_DATA_READINESS`. Let ChatGPT review branch `data/idx-data-002b`, then obtain the missing official tradability boundary/reconciliation evidence or narrow the period only when the boundary is defensible. Do not start modelling or `IDX-VAL-002`.
