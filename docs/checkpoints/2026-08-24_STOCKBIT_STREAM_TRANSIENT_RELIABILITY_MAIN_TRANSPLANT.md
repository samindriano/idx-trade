# Stockbit Stream Transient Reliability Main Transplant V1

Status: `PR_READY_FULL_SUITE_HAS_UNRELATED_STORAGE_FAILURE`

## Scope

This branch starts from `origin/main` at `5f1f1689240b43fe70eb2f6bb4b54dd901fa297c` and ports only the accepted Stockbit transient-reliability behavior from the reviewed operational integration at `21780acf67677dcf88400446bd1be7f4c5c76edd`.

Changed files are limited to:

- `src/idx_trade/stockbit_stream_capture_v2.py`
- `tests/test_stockbit_stream_capture_v2.py`

The existing main-branch workflow, retention policy, archive prefix, universe size, HMAC normalization, runner, and archive implementation remain unchanged. The existing archive `run_id` namespace is preserved; the HMAC salt remains a normalization input and is not added to the namespace.

## Reliability behavior ported

- bounded retry and explicit diagnostics for universe request exceptions;
- bounded per-symbol `requests.RequestException` retry;
- explicit `REQUEST_EXCEPTION` partial records after two failures;
- immutable artifact/hash verification and deterministic resume namespace for partial runs;
- idempotent verification for an already-ready run;
- no provider, model, outcome, counter, or scheduler execution was performed.

## Validation

- `python -m py_compile src/idx_trade/stockbit_stream_capture_v2.py`: PASS
- focused Stockbit tests (`capture_v2`, `archive`, `r2_retention`): `33 passed`
- `git diff --check`: PASS
- full `python -m pytest -q`: one unrelated pre-existing failure:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expects one conflict, while current storage semantics expose independent
  `raw_close` and `vendor_adj_close` conflicts (two).

This branch is not merged to `main`; the GitHub scheduled Stockbit surface remains on the current `main` commit until the narrow PR is reviewed and merged.
