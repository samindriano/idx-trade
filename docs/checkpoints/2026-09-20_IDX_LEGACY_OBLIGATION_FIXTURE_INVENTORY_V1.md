# IDX Legacy Obligation Fixture Inventory V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`
Runtime checkout: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational`
Runtime HEAD: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## Scope and verdict

This is a read-only inventory of the exact pinned runtime checkout. It is not a
claim about every external archive, cloud prefix, protected artifact, or
historical branch.

Verdict: `NO_RETAINED_LEGACY_FIXTURES_IN_PINNED_CHECKOUT`.

The checkout contains no retained runtime output directory (`runtime`,
`prepared`, `executions`, `state/decisions`, or `t0`) and no tracked JSON/CSV
artifact under those output roots with a persisted fill vector. The worktree is
clean. The 13 tracked JSON files and 8 tracked CSV files are configuration or
sample/configuration surfaces; execution/fill references occur in source,
tests, and synthetic replay generators rather than retained migration data.

The inventory fingerprint was:

`6791afd90c34e0239a3cd5a3cdb73cf02dc480ed68efdb0c50a3dab68ecc1a2a`

## Consequence for the obligation frontier

The existing 6/6 migration harness proves the classification rules on isolated
synthetic artifact shapes, but the pinned checkout provides no real retained
fixture to exercise those rules against. Therefore:

- no complete historical fill, explicit zero-lot pending, or recoverable
  positive partial can be admitted from this inventory;
- `UNKNOWN_ORPHANED_PARTIAL` remains the safe classification for a snapshot-only
  positive position if one is encountered elsewhere;
- synthetic fixtures must not be presented as historical migration evidence;
- the next real-fixture step requires an authorized artifact owner/archive
  source, not a new provider or an inferred reconstruction.

This is an evidence-availability blocker, not a runtime defect and not proof
that no external or archived fixture exists. No external archive, protected
outcome, production state, cloud/capture state, or canonical data was opened.

## Validation

- Inventory probe: `tests/test_idx_legacy_obligation_fixture_inventory_probe_v1.py` — `1 passed`.
- Runtime HEAD matched the pin and runtime worktree was clean.
- No writes were performed by the probe.
