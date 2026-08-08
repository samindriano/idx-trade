# Handoff

from: MAIN / DATA
to: ChatGPT reviewer / MAIN
task_id: IDX-DATA-002C
model_used: Luna xhigh root and one bounded read-only explorer
reasoning_level: LIGHT
source_repository: samindriano/idx-trade
source_commit: 3e058b3727cc109af347d03d2eacd3b520625e56
branch: data/idx-data-002c
head_commit: handoff commit follows
scope: Audit official IDX Stock Summary ACTIVE anchors near the public-window boundary and recent checkpoints, integrate selected anchors with fail-closed tradability reconstruction, independently reconcile reserved snapshots, and rerun the 35-case adversarial DATA GATE. No modelling, IDX-VAL-002, trading, or merge to main.

## Files changed

- `src/idx_trade/providers/idx_stock_summary.py`: use the currently reachable official `www.idx.id` host for the Stock Summary page, validation request, endpoint, and Referer. The former `www.idx.co.id` host returned HTTP 403 during this audit.
- `tests/test_idx_stock_summary_provider.py`: update the endpoint contract to the current official host.
- `coordination/handoffs/IDX-DATA-002C-DATA.md`: record the audit, evidence boundary, reconciliation results, and blockers.

Runtime Stock Summary payloads, parsed rows, anchor CSVs, reconciliation reports, parquet prices, and adversarial artifacts remain outside Git in the fresh local evidence directory. No runtime market data or generated artifacts were committed.

## Findings

### Validation

- Full project suite before the live audit: `83 passed, 2 warnings`.
- Full project suite after the official-host adapter fix: `83 passed, 2 warnings`.
- The two warnings are existing pandas `FutureWarning` messages from `tradability_anchor_reconstruction.py`; no test failed.
- `git diff --check`: passed.

### Official Stock Summary audit

- Nine representative official checkpoint dates were audited: `2023-08-07`, `2023-08-08`, `2023-08-09`, `2025-07-30`, and `2026-07-31` through `2026-08-07` on available dates.
- `stock_summary_regular_trade_anchors()` was the only ACTIVE derivation used. It requires positive Regular-Market volume after subtracting non-regular volume and positive Regular-Market frequency after subtracting non-regular frequency.
- ACTIVE anchor rows by integrated date: `2023-08-08=761`, `2023-08-09=766`, `2026-07-31=809`, `2026-08-03=810`, `2026-08-05=810`; total `3,956`.
- The independent Stock Summary holdout dates were `2023-08-07=764`, `2026-08-06=810`, and `2026-08-07=808`; total `2,382` rows. These dates were not added to the integrated ACTIVE-anchor set.
- `2025-07-30` produced `820` positive regular-trade rows but was kept out of the ACTIVE-anchor set because that date is reserved for the separate official SUSPENDED snapshot evidence.
- Every audited date had `0` explicit security-status rows. No SUSPENDED state was inferred from row presence, `Remarks`, Yahoo, or zero trading.
- The nine checkpoint payloads contained `8,428` raw records and `8,416` parsed rows; the exact per-date raw/parsed and diagnostic counts are retained in the external Stock Summary checkpoint report. The parsed regular-trade evidence counts were `764`, `761`, `766`, `820`, `809`, `810`, `810`, `810`, and `808` in date order.

### Tradability anchor integration

- The independent official IDX SUSPENDED snapshot contributed `5` anchors: `ALMI`, `BCIC`, `DEAL`, `FASW`, and `FISH`, all `REGULAR`, as of `2025-07-30`.
- Integrated anchor total: `3,961` (`3,956` ACTIVE Stock Summary anchors + `5` SUSPENDED snapshot anchors).
- The existing `config/tradability_coverage_windows.csv` remains empty/incomplete. The resolver therefore emitted `5 ANCHOR_OUTSIDE_COMPLETE_DISCOVERY_WINDOW` diagnostics and synthesized no suspension intervals. This preserves the required left-boundary and initial-state uncertainty.
- Separate Stock Summary holdout rows/dates were reserved for independent reconciliation; they were not reused as integrated anchors.

### Snapshot reconciliation

- SUSPENDED snapshot anchor rows: `0/5` matched (`ALMI`, `BCIC`, `DEAL`, `FASW`, `FISH`); all reconstructed as `UNKNOWN` because no complete discovery window authorizes propagation.
- Independent Stock Summary ACTIVE holdout reconciliation: `0/2,382` matched; every holdout row remained unresolved under the incomplete coverage window.
- These failures are evidence of an incomplete tradability boundary, not permission to mark the rows ACTIVE or SUSPENDED.

### Adversarial DATA GATE before vs after

- Same fresh gate inputs were used for both runs: `43` official sessions, `35` catalog cases, the existing point-in-time security master, existing raw-price semantics evidence, and the reconstructed event intervals.
- Before anchors: `0/35` cases passed; `1,375` UNKNOWN tradability sessions; `0` expected ACTIVE sessions; exact blocker distribution: `SESSION_COVERAGE_INCOMPLETE=35`.
- After integrating the selected anchors: `0/35` cases passed; `1,375` UNKNOWN tradability sessions; `0` expected ACTIVE sessions; exact blocker distribution remained `SESSION_COVERAGE_INCOMPLETE=35`.
- The unchanged result is intentional: the code must not use point-in-time anchors to manufacture a complete public discovery window or an initial ACTIVE complement.

## Decisions made

- Keep the current official IDX host as `www.idx.id` for Stock Summary transport after live verification of the endpoint.
- Use only positive official Regular-Market transaction metrics for ACTIVE anchors.
- Use the five official SUSPENDED snapshot rows as authoritative evidence, but do not propagate them outside a complete discovery window.
- Keep Stock Summary holdout dates separate from integrated anchors for independent reconciliation.
- Keep the public tradability window incomplete and do not infer initial ACTIVE state.
- Do not start modelling or `IDX-VAL-002`.

## Decisions needed

- Decide whether additional authoritative IDX evidence can prove discovery completeness and the left-boundary initial state.
- Resolve the five official snapshot mismatches without converting `UNKNOWN` into a guessed state.
- Only after the tradability and source gates are complete may MAIN consider `IDX-VAL-002`.

## Blocking risks

- `SOURCE_DISCOVERY_INCOMPLETE`: the public announcement history does not yet establish a complete tradability window.
- `LEFT_BOUNDARY_INITIAL_STATE_UNKNOWN`: no evidence authorizes a market-wide or ticker-specific initial ACTIVE complement.
- `TRADABILITY_RECONCILIATION_FAILED`: the five official SUSPENDED snapshot rows remain `0/5` matched, and the independent Stock Summary holdouts remain `0/2,382` matched.
- `SESSION_COVERAGE_INCOMPLETE`: all 35 adversarial cases remain blocked by unresolved tradability.
- Stock Summary provides no explicit SUSPENDED status rows on the audited dates; it cannot by itself resolve suspension state.

## Validation run

- `python -m pytest -c pyproject.toml tests` -> `83 passed, 2 warnings` before and after the final executable change.
- `git diff --check` -> passed.
- Fresh external evidence includes nine official Stock Summary payload audits, regular-trade anchors/diagnostics, anchor integration diagnostics, two independent reconciliation reports, and before/after 35-case gate reports.
- No modelling, `IDX-VAL-002`, trading, merge, runtime-data commit, or orchestra/control-plane propagation into `idx-trade` was performed.

## Recommended next action

`BLOCKED_DATA_READINESS`. Review branch `data/idx-data-002c` from GitHub. Obtain defensible official evidence for the tradability discovery boundary and initial state, then rerun the gate from a new evidence directory. Do not begin modelling or `IDX-VAL-002`.
