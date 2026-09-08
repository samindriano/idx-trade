# IDX-Trade Project Language V1

## Purpose

IDX-Trade has accumulated many technically precise but overly specific status strings across checkpoints, handoffs, runtime code, audits, and historical experiments. Those strings are useful for forensic reconstruction, but they are not suitable as the primary language for day-to-day project coordination.

This document defines the human-facing vocabulary for the whole project from this point forward.

The goal is simple: the current project state should be understandable in seconds without reading implementation-specific verdict names.

## Rule 1 — Current-facing status uses a small vocabulary

Use only these primary project statuses in README, roadmap, TEAM_STATUS, dashboards, handoffs, and user-facing summaries:

- `ACTIVE` — work or a live experiment is currently running.
- `WAITING` — ready but waiting for time, data, a scheduled run, or an external dependency.
- `BLOCKED` — cannot progress without resolving a concrete blocker.
- `DONE` — the scoped work is complete.
- `PARKED` — intentionally not being worked on now.
- `ARCHIVED` — historical only; retained for evidence, not part of current project state.

Do not invent compound lifecycle states such as `READY_FOR_REVIEW_PENDING_ACTIVATION`, `MATURE_ENOUGH_FOR_BASELINE`, or `CLOUD_SMOKE_PASS_READY_FOR_ROUTINE_PROMOTION` for current-facing coordination.

If extra context is needed, add one short reason in normal language:

`BLOCKED — forward CA evidence is not live yet.`

not:

`FORWARD_CA_FEATURE_BASIS_PRODUCTION_READY_AWAITING_GENUINE_PROOF`.

## Rule 2 — Scientific gate verdicts stay minimal

For scientific, integrity, or admission gates, use only:

- `PASS`
- `FAIL`
- `UNKNOWN`

`UNKNOWN` blocks when the evidence is required.

Do not create a new verdict phrase when a normal status plus one-line reason is enough.

## Rule 3 — Experiments use plain lifecycle language

For experiments and forward tests, use:

- `NEW TEST`
- `RUNNING`
- `COMPLETE`
- `ARCHIVED`

The primary display should show the model/test name, start date, progress, and status.

Example:

```text
V4-X1 Clean Forward Test
Status     RUNNING
Progress   17 / 100
Start      2026-XX-XX
```

Old or superseded runs are simply:

```text
Old V4-X1 Forward Test
Status     ARCHIVED
```

Do not make historical gaps, old counters, or superseded admission terminology part of the primary project state unless they are the active blocker.

## Rule 4 — Machine codes are not human-facing project language

Long runtime result strings, exception identifiers, schema values, artifact state codes, and frozen protocol enums may remain unchanged when code/tests/contracts depend on them.

Examples include values such as:

- `SOURCE_CAPTURE_UNRESOLVED`
- `V4_X1_SCORE_ALREADY_DONE_VERIFIED`
- `TRADABILITY_RUNTIME_READY`
- detailed workflow/runtime failure codes

These are machine or forensic evidence. They must not become the headline status in TEAM_STATUS, the roadmap, dashboards, or normal user-facing summaries.

When needed, translate them:

```text
Primary status: BLOCKED
Reason: forward CA evidence is missing.
Technical detail: SOURCE_CAPTURE_UNRESOLVED
```

The technical line is optional and belongs in drill-down/audit detail, not in the primary view.

## Rule 5 — Historical evidence is preserved, not rewritten

Do not rewrite old checkpoints, immutable artifacts, old experiment manifests, tombstones, or historical commits merely to rename their verdict strings.

Historical terminology remains valid as forensic evidence of what that version of the project recorded at the time.

Simplification happens at the current-facing layer:

- `coordination/TEAM_STATUS.md`
- `coordination/PROJECT_ROADMAP.md`
- root `README.md`
- current handoffs
- dashboards / monitoring UI
- assistant/Codex summaries
- future checkpoints

If an old status matters, translate it into the small vocabulary and link/reference the original evidence rather than repeating the long phrase as the current state.

## Rule 6 — One state, one reason, then evidence

Every current project summary should prefer this hierarchy:

1. **State** — one simple status.
2. **Reason** — one sentence, only if needed.
3. **Evidence** — exact branch/SHA/artifact/test details when the reader asks or when they are decision-critical.

Do not reverse this hierarchy by leading with hashes, long verdict strings, or implementation names before saying whether the lane is running, blocked, done, or parked.

## Rule 7 — Avoid terminology multiplication

Before adding a new named concept, ask whether it is actually a new scientific/technical object or merely another name for an existing state.

Do not create new project-wide nouns for:

- a score that exists but is not part of the active test;
- a historical run that has been superseded;
- an intermediate review state;
- a retry state that can be described as waiting or blocked;
- an implementation that is ready but not yet live.

Prefer plain descriptions such as:

- `old test`
- `current test`
- `local score artifact`
- `not counted in the current test`
- `waiting for scheduled proof`
- `blocked by missing data`

## Rule 8 — Dashboards highlight decisions, not schema coverage

Primary dashboards should answer, in order:

1. What is running?
2. What is blocked?
3. What changed recently?
4. What is the progress?
5. What needs attention?

Technical evidence, hashes, IDs, source states, detailed gate codes, and provenance belong in drill-down views.

## Migration policy

This is a presentation and coordination migration, not a scientific rewrite.

Do not rename machine enums or frozen protocol values unless there is a separate engineering reason to do so.

For current project documentation, progressively replace verbose status phrases with the vocabulary above. Historical files may continue to contain older terminology.

## Default project summary format

Use this format unless a task requires something more detailed:

```text
IDX-Trade

Running
- <lane> — <short progress>

Blocked
- <lane> — <one-line reason>

Waiting
- <lane> — <what it is waiting for>

Parked
- <lane>

Next
- <single highest-priority action>
```

If a section is empty, omit it.
