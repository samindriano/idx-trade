# Alpha Challenger — Breakout Event V1 Historical Result

Status: `NO-GO / EXACT FIXED CHALLENGER`

Branch: `codex/alpha-challenger-pit-safe-20260919`  
Preregisration: `2026-09-19_ALPHA_CHALLENGER_BREAKOUT_EVENT_V1_HISTORICAL_PREREGISTRATION.md`

## Scope and safety

This was a one-shot historical-development diagnostic. It used only the
accepted historical replay target ledger through `2026-07-17` and the accepted
V4-X1 challenger validation scores. It did not read fresh/protected outcomes,
call a provider, mutate a counter, refit a model, or change any production
artifact. The incumbent was used only as the already-accepted score column for
an apples-to-apples common-support comparison.

## Common support

- valid incumbent rows: `152,171`
- candidate rows: `152,171`
- valid dates: `600`
- candidate coverage ratio: `100%`
- valid date range: `2023-12-28` through `2026-07-17`
- daily metric method reproduced the accepted common-support incumbent IC:
  `0.09755404`

## Results

| Score | Mean daily IC | Q25 daily IC |
|---|---:|---:|
| Accepted incumbent | `0.09755404` | `-0.01019388` |
| Event overlay | `-0.01412768` | `-0.06426953` |
| Fixed 80/20 blend | `0.09617224` | `-0.00742799` |

Paired deltas versus the incumbent:

- event overlay mean delta: `-0.11168172`
- event overlay q25 delta: `-0.22600141`
- fixed blend mean delta: `-0.00138179`
- fixed blend q25 delta: `-0.00479846`
- fixed blend positive-date deltas: `253/600`
- fixed blend non-negative 20-session blocks: `5/30` (`16.6667%`)

## Verdict

`BREAKOUT_EVENT_V1_NO_SURVIVOR`.

The fixed blend failed all performance components of the preregistered gate;
coverage was the only gate that passed. The exact candidate is closed. No
alternate weight, window, sign, event definition, horizon, model, or rescue
search was run after observing the result.

The frozen V4-X1 alpha, its artifacts, Decision/runtime, prospective evaluator,
forward data, and counters remain unchanged.
