# Stockbit Stream Full E2E Result

Date: 2026-08-23
Branch: `fix/stockbit-stream-daily-capture-v1`
HEAD: `67d07e449ce751e3e064aaa97c4d00b7c7a2d178`

## Full run

GitHub Actions run: [32616176893](https://github.com/samindriano/idx-trade/actions/runs/32616176893)

- slot: `after_close`
- capture date: `2026-08-23`
- source IDX session: `2026-08-21`
- planned/completed calls: `200/200`
- response classifications: `OK=200`
- successful responses: `200`
- normalized rows: `5,919`
- status: `DATA_READY`
- run ID: `2026-08-23_after_close_e3315af53dda3073_b60cfd3e81a78317`
- universe SHA-256: `e3315af53dda307339af2a312c84337e21b5b4c5a34c80267d4a54de23c96c4c`
- manifest SHA-256: `5690d7439c357d0d1b8cdbcb8e8da8a17e1a0ea8ff42d4ca29bca9474dc9ff08`
- model access: `false`
- outcome access: `false`
- counter mutation: `false`

The preceding full run (`32615513888`) reached `200/200` but had one
`HTTP_503` and one `HTTP_520`, and correctly ended `PARTIAL_FAILURE`. The
bounded transient retry remediation recovered this class of failure on the
next full run.

## Storage evidence

The successful run uses the configured Cloudflare R2 S3-compatible backend.
Each universe/raw/normalized/manifest artifact is submitted through the
conditional immutable `PutObject` path, and the final manifest PUT returned
the SHA above. This proves the R2 write path accepted the complete manifest
and its embedded object digests.

The routine V2 path intentionally does not perform GET read-after-write for
every new object. Therefore this result is not a byte-level independent GET
readback audit; that would require a separate authorized storage-verification
operation and additional R2 requests.

## Validation

- focused Stockbit capture/archive tests: `14 passed`;
- `py_compile`: pass;
- `git diff --check`: pass;
- full pytest: one known unrelated baseline failure at
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  because current storage semantics expose two independent conflicts
  (`raw_close` and `vendor_adj_close`) while the old test expects one.

The fix branch is pushed but is not merged into `main`; scheduled automation
will use the daily schedule only after this branch is merged to the default
branch. No model, outcome, or counter lane was accessed.
