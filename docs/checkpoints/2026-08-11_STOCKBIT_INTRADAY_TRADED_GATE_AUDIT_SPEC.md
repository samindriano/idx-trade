# Stockbit Intraday Traded-Today Gate Audit V1 — Frozen Spec

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/stockbit-intraday-forward-capture-v1`
Base evidence: broad census remote HEAD `805da755380bbdc723c84463e8378b2103ed256b`

## Decision

`STOCKBIT_INTRADAY_TRADED_TODAY_GATE_AUDIT_AUTHORIZED`

The 2026-08-11 broad census proved that Stockbit intraday chart acquisition works at current-universe scale, but 130/962 official-current IDX tickers returned HTTP 404. Before authorizing recurring capture, test whether a cheap current-session IDX stock-summary snapshot can identify tickers that actually traded and therefore should receive a Stockbit chart request.

This is a data-acquisition efficiency audit only. It does not authorize recurring scheduling, model/feature research, Open work, PIT-sector work, or trading.

## Frozen evidence

Broad census:
- official current IDX universe: 962 tickers
- ticker-list SHA-256: `fe131ec56913ce232382c4220cfb61649b334ea42fe2180f5f585ab414825613`
- universe snapshot SHA-256: `5086d4f36a540fcc427134f97d696d030acce7268c1a6715a1929d2ba7be3a97`
- Stockbit chart SUCCESS: 832
- Stockbit chart HTTP_404: 130
- identity/session validation failures among returned chart payloads: 0
- broad-census artifact manifest SHA-256: `c59949645e88e71fb72c5bbec53fca43b0ef1d62dd70f3960299b3d695a9807a`

## Audit source

Use Zapi `finance:idx/stock-summary` for exact session `2026-08-11`, requesting the broad current stock summary with `length=1000`, `start=0`, and no ticker filter.

Do not use returned Open as evidence in this experiment. The only candidate gating fields are exact ticker identity plus current-session trading-activity fields such as `volume`, `value`, and/or `frequency` if present.

Preserve the complete provider payload and normalized snapshot in a new immutable external artifact root.

## Exact matching

Join only by exact normalized 4-character IDX ticker to the frozen 962-ticker universe.

Fail closed on:
- duplicate conflicting ticker rows;
- wrong or ambiguous session date;
- response truncation/pagination uncertainty;
- schema changes that remove ticker or trading-activity fields.

Do not infer trading activity from price changes alone.

## Required comparison

For all 962 frozen tickers, compare broad-census Stockbit chart status against IDX stock-summary activity.

Report at minimum:
- exact IDX summary coverage / 962;
- summary rows and duplicate ticker count;
- field availability for `volume`, `value`, `frequency`;
- counts for activity rules individually:
  - `volume > 0`
  - `frequency > 0`
  - `value > 0`
  - robust OR rule across available activity fields;
- confusion matrix against Stockbit chart SUCCESS vs HTTP_404;
- precision/recall of predicting chart SUCCESS;
- false negatives: Stockbit chart SUCCESS but IDX rule says no trade;
- false positives: Stockbit chart 404 but IDX rule says traded;
- exact ticker lists for every mismatch;
- estimated Stockbit chart calls saved per session if the gate were used;
- estimated 20/21/22-session monthly chart-call burden using the observed 962 universe;
- quota before/after for this audit;
- artifact hashes and manifest SHA;
- focused and full pytest results.

## Acceptance gate

A daily traded-today prefilter may be proposed only if the evidence is strong enough to avoid losing valid intraday paths.

Preferred acceptance condition:
- zero false negatives against the 832 successful broad-census Stockbit charts; and
- material reduction in unnecessary chart calls.

If false negatives exist, do not silently weaken data acquisition. Stop and review whether the gate can be made safe or whether recurring capture should use a different supported-universe strategy.

## Stop

After the audit, STOP for independent ChatGPT review.

Do not start the recurring scheduler or another full Stockbit capture inside this run.