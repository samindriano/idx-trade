# C1-C4 Rank-to-Open State Transition Audit — Preregistration V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `OUTCOME_BLIND / STRUCTURAL SHADOW ONLY`

## Question

Among the fixed Top-30 selections of the already-frozen C1-C4 stored ranks,
how many requested slots have a positive finite same-row Open that is inside
the recorded High/Low range, and how do pending Open states affect transition
burden and slot occupancy?

## Fixed contract

- Use the existing frozen 600-session tail window and the stored rank columns.
- Sort descending stored rank, then ascending ticker as deterministic tie-break.
- Mark a selected row `READY_OPEN` only for positive finite Open with
  `Low <= Open <= High` on the same `(ticker, date)` row.
- Mark every other selected row `PENDING_OPEN`; never fill or forward-fill.
- Keep `ENTRY`, `HOLD`, `EXIT_RANKED_OUT`, and `EXIT_RANK_MISSING` separate.
- Report rank bands `1–10`, `11–20`, and `21–30`, pending duration, requested
  turnover, and Open-ready turnover. Both turnover metrics use the fixed K=30
  denominator so pending slots remain visible as vacancy rather than being
  silently renormalized.

## Boundaries

This is not a new alpha, refit, score replay, Decision V2 change, PaperState
run, target/outcome evaluation, source admission, provider probe, or execution
claim. The frozen Open field is used only as a structural capability field;
PIT timing, source authority, corporate-action basis, survivorship, auction,
fill, and executable capacity remain unknown.

Inputs are hash-pinned to the existing isolated staging artifacts. The output
must remain under the isolated staging root, and no canonical/capture/cloud/
telemetry/protected artifact may be modified.
