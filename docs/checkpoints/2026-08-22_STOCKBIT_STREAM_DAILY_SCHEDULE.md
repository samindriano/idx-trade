# Stockbit Stream Daily Schedule Update

Date: 2026-08-22
Branch: `data/stockbit-stream-prospective-archive-v1`

## Change

The cloud GitHub Actions schedule now runs the three existing Stockbit Stream
slots every calendar day, including weekends and IDX market holidays:

- `08:47` Asia/Jakarta — `pre_open`
- `12:07` Asia/Jakarta — `midday`
- `16:47` Asia/Jakarta — `after_close`

The workflow still uses the existing single capture job, immutable R2 prefix,
120-minute timeout, concurrency group, and `workflow_dispatch` path. No local
IDX scheduler, EOD/intraday runtime, model, counter, or outcome path changed.

## Semantics

Calendar-day capture does not imply an exchange session. The capture date and
observed timestamp remain the social-stream observation identity. The existing
runtime universe may use the latest valid IDX source session; that source
session must remain recorded separately and must not be treated as the current
calendar date's market session.

No provider call or real workflow run was performed in this change. The next
operational check is a read-only `workflow_dispatch`/R2 manifest verification.

## Validation

- `python -m pytest tests/test_stockbit_stream_archive.py -q` — PASS (6)
- `git diff --check` — required before commit

