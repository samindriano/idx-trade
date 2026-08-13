# TradingView Intraday Price-Path Contract V1 — Runtime Checkpoint

Date: 2026-08-14
Branch: `data/tradingview-intraday-price-path-contract-v1`
Status: `REVIEW`
Scope: semantic/data contract only; no provider calls, acquisition, panel
write, feature generation, model fit, Path Risk, O2, or protected outcomes.

## Decision

The semantic contract is frozen as
`FROZEN_SEMANTICS_DESIGN_ONLY`. It keeps the canonical official daily Open
and the raw first TradingView regular-session-bar Open as separate fields.
It permits raw regular-session H/L/C/V path features with explicit anchor
semantics and prohibits auction claims, arbitrary Open repair, adjusted-price
substitution, volume rescaling, and silent extended-session mixing.

The contract remains design-only and is **not an acquisition/admission
authorization**. Independent official IDX evidence now resolves all 195
previously uncertain keys: exact Stock Summary rows show regular-market
`Volume = 0`, `Value = 0`, and `Frequency = 0`, with `UNRESOLVED = 0`. This
does not generalize to all boards or NonRegular activity.

## Read evidence first

The controlling Stage-1 checkpoint was:
`docs/checkpoints/2026-08-14_TRADINGVIEW_OPEN_SESSION_SEMANTICS_RUNTIME.md`.
The activity-aware checkpoint was also read:
`docs/checkpoints/2026-08-14_TRADINGVIEW_INTRADAY_ACTIVITY_FORENSICS_RUNTIME.md`.

Supported activity-aware evidence:

- 1,282 canonical-active sessions;
- 1,282 TV-covered active sessions;
- zero true TV misses on those canonical-active rows;
- point activity-aware coverage 100.00%;
- 195 independently resolved regular-market no-trade sessions;
- unresolved sessions after independent resolution: 0;
- conservative lower bound after resolution: 100.00%.

Supported fidelity evidence:

- TV60 HLC exact: 96.18% on the frozen matched rows;
- TV60 volume within +/-5%: 95.01%;
- TV1D Open exact on canonical-open rows: 98.91%;
- frozen Stage-1 Open verdict:
  `TV60_OPEN_BOUNDARY_PATTERN_FOUND_MEANING_UNPROVEN`.

Independent activity resolution provenance:

- branch `data/tradingview-intraday-independent-activity-resolution-v1@c943a76`;
- runtime head `3977c51ed00cd798a8e45dc8d8170c82bec4bf67`;
- runtime manifest SHA `f8076b83e170eb6180fbe3c3896000f33894c13e679c31e426816d471b6c0864`;
- exact resolution CSV SHA `c067e089193b281d69d816df282569e6a8080285ea53766892df9dd336659540`;
- 195/195 exact keys; 195 independent no-trade; 0 unresolved.

Stage-1 Open/session evidence:

- stored metadata: regular `09:00-16:30`, public extended `08:45-16:30`;
- 2026 regular pre-open bars: 0;
- 2026 extended pre-open bars: 10 across BBCA, BBRI, BMRI, TLKM, ASII;
- 2021/2024 bounded live requests remained unresolved after symbol load;
- no auction flag, trade classification, or explicit auction-boundary field.

## Contract files

- `config/tradingview_intraday_price_path_contract_v1.json`
- `src/idx_trade/tradingview_intraday_price_path_contract.py`
- `docs/TRADINGVIEW_INTRADAY_PRICE_PATH_CONTRACT_V1.md`
- `tests/test_tradingview_intraday_price_path_contract.py`

The contract's candidate window is 2021-01-01 through 2026-07-31, using only
official IDX sessions. This is a preregistration-ready design target, not a
request to acquire that history now. TradingView 60m outputs are called
provider-session bars, not 60 minutes of continuous IDX trading.

## Immutable Stage-1 provenance

Admission artifact root (read-only):
`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_intraday_admission_pilot_v1_20260814`

Activity-aware output root (read-only):
`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_intraday_activity_forensics_v1_20260814`

Canonical panel SHA before/after Stage 1:
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

Stage-1 admission manifest SHA:
`de7246e447a83b15c083d19a00808f13670d97f720bd1e28ce8756e02186e8ee`.

Stage-1 session-semantics artifact manifest SHA:
`91e0d1de66a4be0f513f0b69c860b06f3b3d072b4d66ff6ac5eddf6c661bff01`.

Activity-aware outputs:

- `activity_support.csv`: `6963fefc5ffa0af0732628b46218a98a8401c729ace0d5c9cc73b14a413777d0`;
- `missing_session_forensics.csv`: `d03f8f2e7399d4337bbb1c550b6330d9bf9a1850fb2d4c967e184d220ab6ef9f`;
- `summary.json`: `5778169260cd0712ee75a1228e2d5ddf1f5d05ac3933e6a99c82d10b2176506b`.

## Validation

- focused contract tests: `6 passed`;
- full pytest: `45 passed, 1 failed`;
- unchanged pre-existing failure:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`;
  the fixture emits two revision conflicts (`raw_close` and
  `vendor_adj_close`) while the assertion expects one;
- no provider/network calls;
- no runtime data or panel artifacts created;
- `git diff --check`: run after final edits.

## Remediation interpretation

The independent activity resolution removes the prior activity-evidence
blocker for preregistration: all 195 missing-session keys are now supported as
regular-market no-trade rows. The semantic contract is therefore
preregistration-ready, while admission V2, acquisition, and modelling remain
closed. This remediation does not retroactively change the original admission
rejection.

TradingView 60m values remain provider-session bars. Auction identity, exact
clock-time microstructure, and provider volume-timing semantics remain
limitations. No model or acquisition starts in this lane. Independent ChatGPT
review is required after remediation.
