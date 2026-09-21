# IDX-Trade Additional Local Boundary Audit V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **BOUNDARY AUDIT PASS / NO NEW PAPER-STATE ARTIFACT**

## Purpose and limits

This read-only audit checks local roots adjacent to the already admitted
`idx-trade-data-gate-20260808v` evidence root. It uses directory/file metadata
and schema/key shape from a small set of JSON manifests. It does not call a
provider, open parquet payloads, inspect protected outcomes, inspect excluded
provider/research/model content, copy a new input, or modify any local source
root.

The audit is specifically intended to prevent a similarly named historical
input bundle or scheduler backup from being misclassified as paper state.

## Reviewed local boundaries

### Historical sibling data-gate root

`D:\Documents\Project\idx-trade-data-gate-20260808u`

- 1,193 files / 84,873,151 bytes;
- filename-level hits are concentrated in certification, execution anchors,
  session/calendar, price, and corporate-action input classes;
- the small certification manifest has `snapshot_schema_version=1`, window
  `2026-01-15` through `2026-07-31`, and code commit
  `949f98c3662e8a558d336996f64fd837417a870e`;
- its named artifact set is limited to tradability intervals, exchange
  sessions, full-universe certification, history ladder/summary, model-safe
  price panel, official sessions, split/reverse-action registry, security
  master, scope exclusions, and tradability anchors;
- no artifact name in that manifest denotes paper positions, pending orders,
  fills, obligations, portfolio cash, transaction state, or a runtime-state
  snapshot;
- `execution\idx_execution_anchors.csv` and related summaries remain input
  observation evidence, not transaction/fill state.

The `snapshot_schema_version` field is therefore interpreted as a
certification/input-manifest schema marker, not proof of a paper-state
snapshot. No migration candidate was admitted from this sibling root.

### Rollback package

`C:\Users\Sam\AppData\Local\IDXTrade\rollback-packages\intraday-canary-precutover-20260907-131918`

- 7 files / 30,452 bytes;
- `task-snapshot.json` contains task identity, task state/enabled flag,
  last/next run metadata, principal, action, triggers, settings, source
  manifest, and material-file metadata;
- `files\deployment-manifest.json` contains source/script/launcher identity
  and hashes;
- no paper position, pending intent, fill vector, cash, CA obligation, or
  recovery ancestor is present in the admitted shape.

This is scheduler/deployment rollback evidence, not a real E2E paper-state
chain. It supports runtime/task lineage only.

### Watchdog/deployment root

`C:\Users\Sam\AppData\Local\IDXTrade\github_schedule_watchdog_v1`

- 374 files / 1,701,782 bytes;
- metadata hits are deployment source, workflow files, dispatch markers,
  configuration samples, and tests;
- this root is excluded from real retained-state admission because it is
  source/automation evidence, not historical paper state.

### Other adjacent directories

The local project directory also contains many `idx-e2e-*`, partial-test,
provider, research, model, and synthetic replay workdirs. Their names and
timestamps were inventoried at the directory boundary only. They are not
admitted as real retained runtime evidence without an explicit provenance,
state schema, and immutable source/copy manifest. Provider/research/model
clusters remain outside this lane by design.

## Result

This boundary pass found no additional real paper-state population. It
strengthens the accessible-local inventory record and explains why the
historical sibling and rollback roots are not migration inputs; it does not
close the real-state gate.

`REAL ARTIFACT DISCOVERY = PASS WITH LIMITATION`

`REAL MIGRATION = BLOCKED BY ABSENT ADMITTED PAPER STATE`

`PRE-CANARY READINESS = NO-GO`

