# Handoff

from: ChatGPT / MAIN implementation
to: Codex local runtime verifier
task_id: IDX-OPEN-BACKFILL-YAHOO-CENSUS-RUNTIME
model_used: GPT-5.6 Sol
reasoning_level: high
source_repository: samindriano/idx-trade
branch: data/idx-open-backfill-yahoo-census-v1
scope: local execution and verification of already-implemented full-universe Yahoo historical Open census only
files_changed: runtime documentation only unless a concrete local-runtime implementation bug is demonstrated

## Role boundary

ChatGPT owns implementation/methodology. Codex is used here only because the immutable panel, authoritative corporate-action artifact, runtime cache, and network execution are local to the user's Windows environment.

Do not redesign the census. Do not choose new sources. Do not relax a gate. Do not perform speculative refactors.

If the existing implementation runs correctly, make no source/test changes. Execute, verify, document factual results, push documentation-only runtime result, and stop.

If and only if a concrete runtime bug prevents execution, identify the exact failing behavior first, make the smallest bounded fix, run the full test suite, document the fix, then continue.

## Read first

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/CHATGPT_CODEX_WORK_DIVISION.md`
4. `docs/OPEN_BACKFILL_POLICY_V1.md`
5. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_YAHOO_SEMANTICS_RUNTIME.md`
6. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_YAHOO_SEMANTICS_INDEPENDENT_REVIEW.md`
7. `docs/OPEN_BACKFILL_YAHOO_CENSUS_V1.md`
8. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_YAHOO_CENSUS_IMPLEMENTATION_READY.md`
9. this handoff

## Verify repository state

- fetch remote;
- confirm this Codex-managed worktree starts from latest remote `data/idx-open-backfill-yahoo-census-v1`;
- working tree must be clean;
- record exact HEAD before runtime;
- run full pytest before any local census command.

## Immutable panel

Use exactly:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

Required SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Baseline unresolved Open:

`446,843`

## Authoritative split/reverse-split input

Use the exact authoritative corporate-action CSV that was already used successfully in the preceding Yahoo semantics runtime (`2026-08-10_OPEN_BACKFILL_YAHOO_SEMANTICS_RUNTIME`).

Do not fetch a replacement source and do not infer a new split table.

Resolve the exact local path factually from the previous worktree/runtime command, shell history, existing local evidence workspace, or the prior runtime artifacts. Before starting the census, verify that the file exists and contains at least `ticker`, `effective_date`, and `ratio` columns.

If that exact prior authoritative artifact cannot be resolved, STOP and report the blocker instead of substituting another file.

## Output root

Use exactly:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810`

The runtime is intentionally resumable. Do not delete a valid existing `raw_cache/` if a prior attempt was interrupted. Successful ticker cache files must be reused after built-in identity/hash/semantics validation.

## Command

Use the authoritative wrapper, not the older internal orchestration function:

```powershell
python -m idx_trade.yahoo_open_census_runtime `
  --panel "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet" `
  --official-actions "<EXACT_PRIOR_OFFICIAL_ACTIONS_CSV>" `
  --output-dir "D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810"
```

Defaults are frozen:

- start `2021-04-29`;
- end inclusive `2026-07-31`;
- maximum attempts per uncached ticker `3`;
- exponential backoff base `2s`;
- serial ticker requests for provider/rate-limit safety;
- Yahoo raw OHLC with `auto_adjust=False` through the existing provider adapter.

## Mandatory checks

After runtime, verify all of the following factually:

- input panel SHA before/after is unchanged;
- every original panel column exists in the derivative in the same order;
- every existing non-null Open is bit-for-bit unchanged;
- `execution_grade_promoted=false`;
- no Adj Close/dividend/previous-Close/synthetic price was used;
- raw cache is outside Git;
- no runtime artifact was committed;
- no unsupported/error provider row was converted into market state or fabricated Open;
- accepted direct fills have exact raw Yahoo H/L/C == certified H/L/C;
- accepted split-scale fills have an independently verified official factor and exact reconstructed H/L/C;
- unresolved rows remain null.

## Required factual report

Report at minimum:

- exact branch/HEAD used;
- pytest result before runtime and after any bug fix (if any);
- panel SHA before/after;
- panel rows and unique panel tickers attempted;
- Yahoo success / no-data / error ticker counts;
- network attempts, retries, cache hits;
- provider row count;
- exact ticker/date coverage over the full panel;
- full known-existing-Open provider coverage;
- full known-existing-Open H/L/C exact count/rate;
- full known-existing-Open raw Open exact count/rate after H/L/C gate;
- direct missing-Open fills;
- verified split-scale missing-Open fills;
- total fills;
- initial null `446,843`;
- final null;
- exact gap closure count and percentage;
- accepted/unresolved counts by year;
- rejection histogram;
- temporal EARLY/MID/LATE quality summary;
- unsupported/error ticker list or concise summary;
- FREN/MASA/MFIN/PURE status;
- raw-cache manifest SHA;
- derivative panel SHA;
- provenance SHA;
- artifact manifest SHA;
- `execution_grade_promoted=false`.

## Documentation after runtime

Create a factual dated checkpoint such as:

`docs/checkpoints/2026-08-10_OPEN_BACKFILL_YAHOO_CENSUS_RUNTIME.md`

Update this handoff with the factual runtime result. Do not alter methodology based on the result.

Push only a fast-forward to the same branch if remote HEAD has not advanced. If remote advanced, STOP and report the detached/local commit SHA for ChatGPT reconciliation. Never force push or rebase.

## Prohibited

- no Stage-5 rerun;
- no Ranking V1/V2 edits;
- no Probability work;
- no execution-PnL analysis;
- no execution-grade promotion;
- no paper/live trading;
- no broker integration;
- no direct IDX scraping/crawling;
- no Zapi/TradingView/Investing/other source;
- no source averaging;
- no inferred split factor;
- no main merge;
- no force push/rebase.

Then STOP for independent ChatGPT review.

## Runtime result — 2026-08-11

runtime_status: `YAHOO_FULL_UNIVERSE_OPEN_CENSUS_COMPLETE_STOP_FOR_INDEPENDENT_REVIEW`
runtime_head: `c338fe8fafd711eb40dee211897d0ee79842d990`
checkpoint: `docs/checkpoints/2026-08-11_OPEN_BACKFILL_YAHOO_CENSUS_RUNTIME.md`
runtime_output: `D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810`

findings:
- full panel: `981,940` rows / `945` tickers attempted;
- Yahoo: `940` success, `0` no-data, `5` errors;
- network attempts `955`, retries `10`, cache hits `0`, provider rows `1,045,683`;
- exact ticker/date coverage: `975,069 / 981,940`;
- known-Open H/L/C exact: `526,756 / 534,942`;
- known-Open raw Open exact after H/L/C gate: `526,656 / 526,756`;
- direct missing-Open fills: `386,157`;
- verified split-scale missing-Open fills: `11,210`;
- total fills: `397,367`;
- initial null `446,843`, final null `49,476`, gap closure `88.9277%`;
- error tickers: `FREN`, `MASA`, `MFIN`, `RMBA`, `TURI`;
- PURE succeeded with one provider row;
- derivative SHA: `d8d3463362a8c43bdb9e8d3aaba5e66ceffe86803b76979d18e3e2e71a276ea4`;
- provenance SHA: `1c11b832c9a8b049202547e8b76c1a4972e9177afefd9a02deb3ca49795bb17d`;
- raw-cache manifest SHA: `08f37a4100e911049a3535357959e43df94c748cdd7bc8cb525a84d870b3b0f6`;
- artifact manifest SHA: `b6e47c98ac256cb07ac0441be41f599ba21481a5340c6b306b5f3301e207da2f`;
- panel SHA before/after unchanged: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- original columns/order and existing Open values preserved; unresolved rows remain null;
- `execution_grade_promoted=false`.

validation_run:
- full pytest before runtime: `236 passed, 3 warnings`;
- source/test changes: none; no concrete runtime bug occurred.

recommended_next_action:
- independent ChatGPT review of the factual checkpoint and external census artifacts; do not begin execution-grade promotion or downstream modelling from this result.
