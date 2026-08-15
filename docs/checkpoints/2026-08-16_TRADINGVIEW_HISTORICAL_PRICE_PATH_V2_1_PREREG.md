# TradingView Historical Price-Path V2.1 Remediation — preregistration checkpoint

Date: 2026-08-16
Branch: `data/tradingview-historical-price-path-v2-1-remediation`
Code checkpoint: `429917f`
Network status: NOT STARTED at checkpoint creation

## Scope and frozen boundaries

This checkpoint continues the existing V2.1 remediation against the immutable
failed-V2 lineage. The frozen V2 verdict remains
`TRADINGVIEW_PRICE_PATH_V2_REJECTED`. No 978-ticker acquisition, panel write,
model fit, Path Risk work, O2/outcome access, or extended-session corpus is
authorized in this lane.

The preregistration is immutable and keeps `network_authorized=false` and
`network_calls=0`. Runtime/network-start state is stored separately by the
preflight runner; it must never mutate `preregistration.json`.

## Preserved offline evidence

The completed retry2 mapping/fidelity work is reused without recomputation:

- expected ticker-session rows identity-mapped: 1,117,184 / 1,117,184;
- existing provider bars identity-mapped: 525,952 / 525,952;
- identity ambiguity: 0;
- UNKNOWN activity sessions: 592;
- official NO_TRADE/provider-bar contradictions: 0;
- official-session-index CA quarantine diagnostic: 11 -> 12;
- preserved offline artifact manifest SHA: `9f1919031658eb6bf355fca016d84bf35327f0b784dc6face1dc323f610f5401`;
- canonical panel SHA before and after offline work:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

The fresh final offline root is:

`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_1_final_20260816_retry5`

Its semantic runtime artifact manifest SHA is
`0952559b79b8edf57030745877f817ebf96e2284f7d4500cee70ce82a59e88c1`.

## Offline decision

The 16 unchanged-contract TradingView `SYMBOL_ERROR` tickers remain:

`CNTB FORZ FREN HDTX JKSW KPAL KPAS KRAH MAMI MASA MFIN MYRX NIPS PRAS RMBA TURI`

They account for 4,074 ACTIVE sessions. The theoretical maximum coverage if
all other provider symbols were perfect is 0.9959025008423308 overall. The
yearly ceilings are 0.9896658546 (2021), 0.9940075934 (2022), 0.9948578620
(2023), 0.9970772166 (2024), 0.9988953882 (2025), and 1.0 (2026). Therefore
the symbol errors do not by themselves fail the frozen 98% overall / 95%
yearly coverage gates; they remain explicit provider blockers, not silently
repaired identities.

Corrected fidelity evidence remains diagnostic only: 85,490 matched rows,
85,478 non-CA rows, HLC exact `0.9437048129`, and volume within 5%
`0.9348838298`. The 2022 forensic subset remains HLC exact `0.754647` and
volume within 5% `0.741636`; no rows or thresholds were changed.

The official Stock Summary H/L/C/Volume audit is not substituted as the
admission oracle. Recommendation:
`OFFICIAL_STOCK_SUMMARY_HLCV_ORACLE_NOT_SUPPORTED`.
It reports 1,033,031 common rows, 975,224 valid rows, joint HLC exact
0.9330768742, volume exact 0.8731583449, and volume within 5%
0.9367196746. The volume-ratio median is 1.0, but the tail is materially
non-uniform (min 0.004, max 2,994,855); no rescaling or repair is applied.

Accordingly the offline taxonomy is:
`V2_1_REMEDIATION_READY_FOR_FULL_PREREGISTRATION`.
This is readiness for the bounded preflight only, not full admission.

## Immutable preregistration

Fresh prereg root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_1_final_20260816_retry5`

- `preregistration.json` SHA-256:
  `5fd9b2eefc69fd0c5a29e9d82e790e9f8490583e82e63522f45c815788b5574e`;
- `prereg_artifact_manifest.json` SHA-256:
  `795b48bd4c53758ac59308f44658e0ad65733d7da77f743c24c856e1f029400b`;
- code HEAD recorded in preregistration: `429917f`;
- adapter: Mathieu TradingView adapter commit
  `5baea86c8c7e576f13464919c86c3b4c4b0ecf4c`;
- provider server: `prodata`, anonymous access, symbol `IDX:<ticker>`;
- timeframe: string `"60"`, session `regular`, adjustment `none`;
- depth: initial range 500, fetch-more batch 5000, hard cap 3;
- required start: 2021-04-01, with one prior official-session buffer;
- controls, in deterministic order: BBCA, BBRI, BMRI, TLKM, ASII;
- maximum future logical provider requests: exactly 5, no retry ladder.

The preflight runner verifies all decision-bearing input hashes, the canonical
fidelity directory manifest, the official Stock Summary archive manifest, the
preserved offline preregistration, and the panel SHA immediately before any
provider request. A mismatch must stop the run.

Next authorized action is only the five-control depth preflight. If any control
fails provider availability, required-start completion, structural integrity,
identity mapping, or boundary checks, stop and preserve diagnostics.
