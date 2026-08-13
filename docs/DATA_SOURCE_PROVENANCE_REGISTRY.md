# IDX Trade data-source provenance registry

`config/data_source_provenance_registry.v1.json` is the canonical, machine-readable
index of data-source boundaries accepted in repository checkpoints. It records
what a source is, what it can support, and what remains unknown. It is not a
provider client, a data cache, or a scientific approval gate.

The registry deliberately keeps the following distinctions visible:

- `authority` identifies the source authority; `authority_role` distinguishes a
  primary source from a transport, cross-check, discovery layer, or derived
  research source. A parity result never upgrades a transport into an authority.
- `status` describes the accepted operational boundary. `ACCEPTED_CONDITIONAL`,
  `DISCOVERY_ONLY`, `AUDIT_ONLY`, `SHADOW`, `BLOCKED`, and `REJECTED` are
  meaningful states, not incomplete versions of `CERTIFIED_BOUNDED`.
- `pit_status` is independent of source authority. `PIT_UNRESOLVED`,
  `PIT_PARTIAL`, `PIT_BLOCKED`, `NOT_PIT`, and `UNKNOWN` must remain explicit.
- `timing` separates market/effective date, publication or first-known timing,
  and local observation time. A record date is not silently promoted to a
  market-effective date.
- `revision_risk` records versioning and overwrite policy. A source without a
  frozen revision chain cannot support an immutable historical claim merely
  because its response is official or currently reproducible.
- `raw_provenance` records retrieval method, canonical and transport locators,
  artifact hashes when the accepted evidence provides them, and preservation
  policy. User-specific runtime directories and runtime data are not committed.
- `permitted_uses` and `prohibited_uses` are an explicit contract. Unknown rows,
  missing publication timing, provider derivatives, and shadow data are not
  silently made model-safe.
- `controlling_checkpoint_ids` link each source claim to accepted repository
  evidence. Checkpoint status, commit, path, and blob SHA can be verified
  locally; `--verify-git` never calls a provider.

## Current source boundaries

The registry covers the formally audited source families without reopening
their work:

- official IDX exchange-session calendar, Stock Summary execution evidence, and
  Index Summary/market context;
- Yahoo raw OHLCV, Wildan Open recovery, Zapi transport parity, and bounded
  TradingView Open derivatives;
- official foreign-flow, issuer financial-announcement discovery, KSEI/IDX
  ownership, PIT sector history, corporate actions, and Margin Summary;
- Stockbit intraday forward shadow capture;
- listing/delisting/security-master and tradability evidence; and
- canonical forward EOD automation.

The source-specific checkpoint/verdict remains controlling. This registry does
not repair historical-universe gaps, resolve PIT publication timing, promote
Open recovery to execution grade, infer `NO_TRADE` from missing Stock Summary
rows, treat KSEI as tradability evidence, or turn Corporate Actions record
dates into market-effective dates.

## Validation

The stdlib validator fails closed on malformed JSON, unknown fields, unsupported
enum values, duplicate identifiers, count mismatches, invalid dates/hashes,
contradictory timing, overlapping use policies, non-PIT sources that permit PIT
replay, blocked/shadow sources that permit operational uses, stale review dates,
non-controlling checkpoints, and checkpoint blob mismatches.

From the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m idx_trade.source_registry `
  config/data_source_provenance_registry.v1.json `
  --repo-root . --verify-git
pytest -q tests/test_source_registry.py
```

The validator does not fetch remote refs and does not inspect protected
outcomes. A changed source boundary requires a new accepted checkpoint first;
then update the registry, retain the old evidence as superseded where
appropriate, add a regression test, and update the checkpoint/handoff.

## Maintenance rules

1. Add only claims that are directly supported by an accepted repository
   checkpoint or formally recorded evidence.
2. Preserve `UNKNOWN`, `BLOCKED`, `SHADOW`, `PIT_UNRESOLVED`, and incomplete
   coverage as stated. Do not replace them with a convenient positive or
   negative interpretation.
3. Keep raw artifacts and hashes outside Git when they are runtime data or
   user-specific files; the registry records their existence and provenance,
   not a copy of the data.
4. Do not change model, feature, eligibility, counter, holdout, or outcome
   semantics from this registry lane.
5. When a later checkpoint changes a source boundary, add the new checkpoint,
   update the source status and supersession links, and preserve the earlier
   record for auditability.
6. The active repository-wide scientific-integrity audit owns remediation of
   scientific or fail-open code defects. This lane represents its accepted
   evidence and does not duplicate those fixes.
