# IDX Trade — Repository-Wide Team Status

Last coordinated update: 2026-08-12 12:05 Asia/Jakarta
Canonical location: `main:coordination/TEAM_STATUS.md`

## Authority

This is the **single live cross-chat coordination ledger** for the entire `samindriano/idx-trade` repository.

- The canonical copy is always the one on `origin/main`.
- A copy on a feature branch is non-authoritative and may be stale.
- Scientific authorization still comes from the newest controlling branch-local spec/checkpoint. This file coordinates ownership/status and prevents duplicate work; it does not bypass research gates.

## Mandatory agent protocol

Before **starting, continuing, or proposing any material IDX-Trade work**, every ChatGPT/Codex agent must:

1. fetch/read the latest `origin/main:coordination/TEAM_STATUS.md`;
2. check whether another active task already owns the same scope;
3. if starting new material work, claim/update a task row before implementation;
4. update the row whenever a material checkpoint, blocker, verdict, branch, or ownership state changes;
5. update the row again when work becomes `REVIEW`, `DONE`, `PARKED`, or `BLOCKED`.

No agent may duplicate an `ACTIVE` scope unless the user explicitly asks for independent/adversarial review.

### Safe shared-file update rule

This file is intentionally shared across branches/chats. On every write:

- refetch the latest `main` version first;
- preserve every other agent's row/change;
- change only the relevant task row(s) plus necessary global notes;
- never force-push or overwrite a newer version;
- on conflict, refetch and reapply the small status edit.

A coordination-only commit directly to `main` is permitted **only for this file** unless separately authorized. Feature/research implementation must remain on its own branch.

Suggested owner labels: `ChatGPT/<purpose>` or `Codex/<purpose>`.

Status vocabulary: `PLANNED`, `ACTIVE`, `AUTOMATED`, `WAITING`, `BLOCKED`, `REVIEW`, `DONE`, `PARKED`.

## Current live work / ownership

| Task / lane | Status | Owner | Branch / anchor | Current boundary / next action |
|---|---|---|---|---|
| O2 vs V2 common-support comparator | `DONE` | ChatGPT review + Codex | `research/idx-ranking-o2-v2-common-support-comparator-v1` / acceptance `a2c5666637f2e879ce107cd44fc2dae8cc22a5c5` | Historical-development evidence accepted; **do not rerun or extend automatically**. |
| Market / Index / Breadth History V1 | `PARKED` | ChatGPT review + Codex | `data/market-index-breadth-history-v1` / review `d3827f1506736ec64c957e10f50f5447196d9983` | `CONDITIONAL_SOURCE_READY_PIT_BLOCKED`; no historical PIT bulk acquisition/model use. |
| Stockbit intraday forward capture | `AUTOMATED` | Existing runtime | `data/stockbit-intraday-forward-capture-v1` | Daily capture infrastructure already exists. **Do not build it again.** Accumulate evidence for possible future Path Risk research. |
| Path Risk | `WAITING` | none | prior V1/V2 lineage | V1/V2 failed. Do not restart/retune now; wait for richer intraday accumulation and a genuinely new preregistered hypothesis family. |
| O2 fresh-forward | `WAITING` | existing O2 forward lane | `research/idx-ranking-ohlcv-o2-forward-v1` | Frozen challenger. No backdating/outcome peeking. Resume only when certified post-freeze session + post-close snapshot requirements are satisfied. |
| IDX forward calendar extension | `WAITING` | existing data lane | `data/idx-forward-calendar-extension-v1` | Evidence-only extension; rerun when a new official session is source-certified. Do not infer dates. |
| Historical OPEN recovery | `PARKED` | none | OPEN/Yahoo/TV accepted lineage | Research coverage gate passed conditionally; substantial residual remains. Do not restart broad provider search/backfill without a new explicit reason. |
| PIT sector history | `PARKED` | none | `data/idx-pit-sector-history-v1` | Research direction recorded; blocked/not authorized for dependent modeling until PIT evidence improves. |
| Frontend monitoring / capture system | `REVIEW` | `Codex/Frontend Editorial Tech` | `codex/frontend-compare-v2` / `bc91a5f` | Read-only monitoring now presents the automated session archive and all three monitored lanes: O2, V3-B, and V2. UI was simplified to a compact archive, three score cards, and a slim shared-session summary; manual capture/date controls remain removed. Build and `/monitoring`, `/compare`, and `/api/monitor/status` HTTP 200 pass. Local runtime reports V2 + V3-B artifacts for 2026-08-10; O2 remains awaiting runtime score artifact. |
| Market/index prospective EOD archive extension | `WAITING` | `Codex/Forward-EOD-Automation-UI` | `integration/forward-eod-automation-monitoring` / `cd2a834` | Single 18:00 EOD runner, logon catch-up, official-calendar/exact-date validation, and legacy Open-task disable path are implemented and tested. Awaiting one post-18:00 controlled capture before local scheduler enablement. |

## Cross-chat no-duplicate rules currently in force

- Do not create a second generic EOD capture system until the existing frontend/backend capture path and forward archive infrastructure are inspected.
- Do not recreate Stockbit intraday automation.
- Do not reopen Path Risk V1/V2 or silently create a V3 rescue before the new-data prerequisite and preregistration are satisfied.
- Do not rerun the completed O2-vs-V2 comparator unless a specific audit/reproduction request requires it.
- Do not treat Market/Index/Breadth historical session-date data as PIT-complete or bulk-model-ready.
- Before suggesting a “next task,” check this file first; a suggestion counts as coordination and can itself cause duplicate work.

## Agent update template

When claiming/updating a row, keep it compact:

`<task> | ACTIVE/REVIEW/etc | <owner> | <branch + HEAD if useful> | <what is being done, blocker, or exact next boundary>`

If a material lane is missing, add it before starting the work.
