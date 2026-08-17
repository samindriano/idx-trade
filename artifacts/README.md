# IDX-Trade artifact layout

This directory contains only small, reproducibility-critical metadata unless a
file is explicitly covered by the repository policy.

## Git-owned areas

- `registry/` — registry and schema for logical artifact identities.
- `manifests/` — small, hash-pinned manifests that describe external bytes.
- `schemas/` — versioned data and artifact schemas.
- `fixtures/` — sanitized, small test fixtures only.

## External-only areas

`external/`, `raw/`, `cache/`, `runtime/`, `models/`, and `outcomes/` are
ignored. Existing external data is not moved into these folders by this task;
the canonical external root is configured outside Git and referenced by a
logical root key in the registry.

Never commit raw provider archives, full OHLCV/financial/flow panels, large
JSONL/CSV exports, parquet files, model binaries, credentials, runtime
databases, or protected outcomes. A Git manifest may record their logical
relative path, source identity, byte size, SHA-256, and provenance without
containing the payload.

Each registry entry must avoid user-specific absolute paths. Use an
`external_root_key` plus an external-relative path instead.
