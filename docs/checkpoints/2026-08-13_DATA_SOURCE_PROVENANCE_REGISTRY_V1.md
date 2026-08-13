# Data-source provenance registry V1 checkpoint

Date: 2026-08-13 (Asia/Jakarta)
Lane: `Canonical data-source / provenance registry`
Implementation commit: `639fcb8`
Canonical coordination update: `75671f40729f15629dd5cae52475b93a39584f9c`
Branch: `codex/data-source-provenance-registry-v1`

## Decision

The registry representation is ready for independent ChatGPT review. It is a
machine-readable evidence index with a JSON Schema, a standard-library
fail-closed validator, focused tests, and maintenance documentation. It does
not change any model, feature, eligibility, counter, holdout, outcome, provider
or scientific conclusion.

## Included source families

The registry covers official IDX session/calendar and Stock Summary execution
evidence, Index Summary/market context, raw Yahoo OHLCV, Wildan Open recovery,
Zapi transport parity, TradingView Open derivatives, Foreign Flow, issuer
financial-announcement discovery, KSEI/IDX ownership, PIT sector history,
Corporate Actions, Stockbit intraday, Margin Summary, historical
security/universe and tradability evidence, and canonical forward EOD
automation.

## Preserved boundaries

- Official authority does not imply PIT-complete publication timing or an
  immutable revision chain.
- Corporate Actions stays revision-sensitive; record/publication dates are not
  automatically market-effective dates.
- Stockbit stays `SHADOW` and non-canonical EOD.
- Yahoo/TradingView/Open derivatives remain bounded research common-support
  evidence and are not execution-grade.
- Stock Summary missing rows do not become `NO_TRADE`.
- KSEI identity/type support does not become tradability evidence.
- Historical universe, Financial PIT, Ownership, Foreign Flow, Market/Index,
  sector history, Corporate Actions, tradability, and Margin timing/completeness
  uncertainties remain explicitly unresolved or blocked.

## Validation

- Focused registry tests: `9 passed`.
- Registry JSON and schema JSON parse successfully.
- `python -m idx_trade.source_registry config/data_source_provenance_registry.v1.json --repo-root . --verify-git`: PASS; 18 sources and 20 checkpoint pins validated.
- `git diff --check`: PASS for staged implementation and documentation changes.
- Full repository pytest: FAIL in an untouched existing test,
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`.
  The current base returns two explicit revision conflicts (`raw_close` and
  `vendor_adj_close`) while that test expects one. No storage code or test was
  changed in this lane.

## Safety boundary

No provider was called, no data was acquired, no protected outcome was read,
and no experiment was rerun. The active repository-wide scientific-integrity
audit remains a separate owner; its findings are represented only where an
accepted checkpoint already supports them.

## Review handoff

ChatGPT should review the registry/schema/validator contract and the preserved
source boundaries. Do not treat the registry as a scientific release approval,
and do not repair the unrelated storage-test failure in this lane.
