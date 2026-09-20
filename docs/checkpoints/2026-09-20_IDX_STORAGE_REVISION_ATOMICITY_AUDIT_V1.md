# IDX Storage Revision and Atomicity Audit V1

Date: 2026-09-20  
Lane: isolated `codex/alpha-available-data-20260919`  
Status: **FAIL — DUPLICATE-DATE STORAGE INPUT NOT FAIL-CLOSED**  
Evidence class: synthetic-only, read-only audit

## Scope and boundary

This audit covers the local daily-history merge and atomic writer helpers used by the price/session backfill paths. It does not call a provider, modify canonical data, touch capture/cloud state, or alter production artifacts. The first probe accidentally resolved a different worktree through the ambient Python import path; that result was discarded. All evidence below was rerun with this lane's `src` explicitly first on `sys.path`.

## Baseline validation

The lane-local focused suite completed successfully:

```text
python -m pytest -q tests/test_storage.py tests/test_price_backfill.py tests/test_session_backfill.py
8 passed
```

The tests cover revision conflict behavior, identical overlap, explicit revision mode, backfill statuses, provider-empty handling, and exchange-session reporting. They do not cover duplicate dates within an individual existing or incoming frame, nor whether atomic writers are exclusive/immutable.

## Reproduced duplicate-date behavior

### Existing history contains duplicate dates

Synthetic existing history had two rows for `2025-01-02`; the incoming frame had one row for the same date. `merge_daily_history` enters `revision_conflicts`, and `old.at[session, column]` returns a Series rather than a scalar. `_equal` then evaluates a Series as a boolean and raises:

```text
ValueError: The truth value of a Series is ambiguous
```

This is an untyped/uncontrolled exception rather than the declared `DataRevisionConflict` or a deliberate fail-closed validation error. The caller `run_price_backfill` catches only `DataRevisionConflict`, so this malformed input can abort the backfill process instead of producing a structured conflict report.

### Incoming history contains duplicate dates

With an empty existing frame and two incoming rows for `2025-01-02` (`102.0` and `103.0`), the merge returned one row with `103.0`. The final operation is:

```python
drop_duplicates("date", keep="last")
```

Therefore duplicate input is silently resolved by row order. No duplicate-input conflict record is produced, and the selected value is not bound to an explicit provider-row identity or provenance rule.

## Atomic writer boundary

`write_parquet_atomic` and `write_csv_atomic` write a temporary file and call `temporary.replace(path)`. The operation is atomic with respect to publication, but it is not immutable or exclusive: a pre-existing destination is replaced. A synthetic CSV probe confirmed the same path changed from `v=1` to `v=2` on the second call.

This may be intentional for mutable backfill outputs and reports; it must not be interpreted as protection for immutable evidence. The prospective-access gate has a separate exclusive-publish implementation and contract. The storage helper itself does not encode that distinction in its name or API.

## Exact implementation evidence

- `src/idx_trade/storage.py:38-60` — revision comparison indexes by date without first rejecting duplicate dates; scalar comparison can receive a Series.
- `src/idx_trade/storage.py:63-80` — merge path checks revisions, then sorts and silently keeps the last duplicate date.
- `src/idx_trade/storage.py:83-94` — atomic writers publish with `temporary.replace(path)`, allowing replacement of an existing destination.
- `src/idx_trade/price_backfill.py:61-80` — caller catches `DataRevisionConflict` only, then writes the merged history.
- `tests/test_storage.py` — existing focused tests do not cover duplicate dates within either input frame.

Source hashes at audit time:

| File | SHA-256 |
|---|---|
| `src/idx_trade/storage.py` | `090147148E3CB711FDC93089B51C704E78E8A82546CE3F8CF73D6C2A609257DB` |
| `src/idx_trade/price_backfill.py` | `6D839836DD9C099EDFC760A9E0DC05D4F048125AAC338018FF22363D733AF0F0` |
| `tests/test_storage.py` | `6388540AC4104A966C5880158C1C5A0E31174C5D62A52BEE9B09B58463F08D13` |

## Risk interpretation

The system has a revision guard for ordinary one-row-per-date overlap, but the input identity contract is incomplete. Duplicate-date input can either abort through an uncontrolled exception or silently select the last row, depending on which side contains the duplicate. This is a data-integrity boundary failure, not evidence that the current canonical dataset contains duplicates.

Atomic replacement is a separate concern: the helper provides crash-safe publication mechanics, not immutable evidence semantics. Callers that require historical immutability must use an exclusive writer or an explicit content/version guard.

## Hardening proposal — not applied

If implementation is later authorized:

1. Reject duplicate dates in each input frame before revision comparison and return a typed fail-closed error.
2. Require an explicit duplicate-resolution/provenance policy for provider payloads; never rely on `keep="last"` implicitly.
3. Separate mutable backfill/report writers from immutable evidence writers in API naming and contracts.
4. Add tests for existing duplicates, incoming duplicates, and pre-existing destination replacement.

Any fix must be tested in this isolated lane and must not rewrite existing canonical histories.

## Verdict

**FAIL — DUPLICATE-DATE STORAGE INPUT NOT FAIL-CLOSED**

No source, data, provider, cloud, capture, or production mutation was performed.
