# IDX Forward Calendar Extension Runtime

Date: 2026-08-12 (Asia/Jakarta)
Branch: `data/idx-forward-calendar-extension-v1`
Starting HEAD: `bcbdcb06fefd8aa59f497bc3db0c22f87763b2f9`
Runtime status: `IDX_FORWARD_CALENDAR_EXTENSION_BLOCKED`

## Scope and boundary

This run executed only the frozen official IDX forward-calendar extension
task. It used the existing `src/idx_trade/providers/idx_sessions.py` provider
and the official IDX trading-hours page. It did not use a third-party calendar,
weekday inference, O2/V3-B scoring, a counter entry, protected outcomes, model
changes, or data repair.

## Frozen anchor and live trading-hours verification

- historical calendar: 1,260 date-only sessions, ending `2026-07-31`;
- historical calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- live official source:
  `https://www.idx.id/en/products-services/trading-hours-and-mechanism/`;
- trading-hours raw SHA-256:
  `7807ad4ab405ef238834aa91873e7b11bc7c350b03921c2cce64c014c08d9eb5`;
- the live page supported Regular Market pre-opening input Monday-Friday at
  `08:45:00` and Session I Monday-Thursday at `09:00:00`;
- the frozen calendar rule was therefore applied as
  `session_start = 08:45:00 Asia/Jakarta`.

## Official IDX date-source runtime

The existing provider was queried for August through December 2026. It made
10 official IDX JSON requests and parsed 10 responses. August resolved through
the official Daily Statistics publication listing because the monthly Digital
Statistics source was empty/invalid. The parsed official extension contains
exactly seven sessions:

`2026-08-03` through `2026-08-11`

with deterministic session indices `1261` through `1267`. September through
December returned no official publication dates from either existing IDX
source; those four months are recorded as `ERROR` in the source report. No
dates were inferred or synthesized.

## First post-freeze evidence

The final-refit independent-review freeze timestamp is recorded as
`2026-08-12T07:45:30+07:00`. The latest available official extension session
starts at `2026-08-11T08:45:00+07:00`, so no extension session starts strictly
after the freeze. The first post-freeze session therefore remains unresolved
in this run.

No O2/V3-B score artifact or counter entry was created. The output decision is
`IDX_FORWARD_CALENDAR_EXTENSION_BLOCKED`.

## External immutable evidence root

`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_calendar_extension_v1_20260812_retry`

Artifact hashes:

| artifact | SHA-256 |
|---|---|
| `forward_exchange_sessions.csv` | `6b38e82f4927c6c66f997b3b15f3780be6e3c9dd82cf25c14e4d21e773c0261a` |
| `exchange_session_sources.csv` | `5cf0d8259d0873ce93d0e49340aa593bb6e37e94775780462de6f25e409cb34c` |
| `trading_hours.html` | `7807ad4ab405ef238834aa91873e7b11bc7c350b03921c2cce64c014c08d9eb5` |
| `manifest.json` file hash | `3ed053b7ce32dc35b6ed9c3bee71dfa2739046b15c56a0cb69cbca672c5cb3ec` |
| `manifest_sha256` inside manifest | `e286b945f1ef17c31d96f13d01a3e32248f973aec3037c7efe6a8eab87d5ff36` |
| `request_log.json` | `2348191e27af30c32597aaae4bf8317a6c263ceed26e5288a1811cfcb54a4a79` |
| `runtime_summary.json` | `963a29693eeefc660a0a9cb18ca7ffaafe9647766e0aef01b94c867f84b174d5` |
| raw official JSON artifacts | `3f7a9cd9516def3b5b7c9f2312a009784b27e4a54f411e236d143204b7f5473a`, `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`, `f745528a5db86d5401b6642bdd8726d105d067870afbe300892cea6cd5dc6a1b` |

## Validation

- focused extension/provider/session tests: `20 passed`;
- full pytest after implementation: `298 passed, 5 warnings`;
- immutable historical anchor was read-only and hash-verified;
- no O2 scoring, counter registration, or outcome access.

## Decision

`IDX_FORWARD_CALENDAR_EXTENSION_BLOCKED`

The authorized next action is to rerun this same evidence-only extension after
the official IDX publication listing exposes a session strictly after the
freeze. Do not infer the missing session and do not start O2 scoring from this
partial extension.
