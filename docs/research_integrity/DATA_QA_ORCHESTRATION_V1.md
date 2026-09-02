# Data QA Orchestration V1

This document defines the default Codex orchestration shape for material IDX-Trade data-integrity / research-integrity audits.

It is activated when the user asks to QA, audit, verify, validate, red-team, or trace the integrity of a dataset, representation, model input, or related scientific lineage.

The root `AGENTS.md` contains the repository-wide trigger and mandatory behavior. This document provides the detailed lane contract.

## Default execution level

Use `HEAVY` when the question is market-wide, lineage-wide, model-impacting, or requires independent falsification.

Use `LIGHT` only when the scope is genuinely bounded to roughly 2–3 independent dimensions.

Use `DIRECT` only for a small local check with no useful independent audit lane.

The orchestrator must explicitly justify de-escalation when the requested QA could materially affect scientific validity.

HEAVY describes logical audit concurrency, not the number of user-facing chats. When native local child-agent execution is available, Lane A through Lane G should normally run as `LOCAL_CHILD_AGENT` workers under one visible MAIN session.

Execution-surface preference:

1. `LOCAL_CHILD_AGENT` — default for read-only and safely disjoint audit work.
2. `LOCAL_ISOLATED_WORKTREE` — only when concurrent repository writes require filesystem/Git isolation.
3. `EXTERNAL_OR_REMOTE_WORKER` — exception only, with an explicit reason.

A local worktree is filesystem isolation, not a new user-facing control plane. Do not create one worktree or one project chat per audit lane merely because HEAVY was selected.

## Mandatory preflight

MAIN must:

1. read newest `origin/main:coordination/TEAM_STATUS.md`;
2. read controlling branch-local checkpoints/contracts;
3. identify frozen science/runtime boundaries;
4. inventory exact available artifacts before opening any sensitive evidence;
5. define what evidence is forbidden, especially protected outcomes;
6. define the gate being certified and the exact verdict vocabulary;
7. identify independent workstreams before MAIN begins duplicating them;
8. assign an execution surface to each worker, preferring `LOCAL_CHILD_AGENT` and recording the reason for any external/remote worker.

A typical preflight should make the topology explicit:

```text
execution surface:
- MAIN: LOCAL_PARENT
- source-semantics worker: LOCAL_CHILD_AGENT
- PIT/provenance worker: LOCAL_CHILD_AGENT
- adversarial worker: LOCAL_CHILD_AGENT
```

Use `LOCAL_ISOLATED_WORKTREE` only where write-collision risk makes it necessary.

## Standard QA lanes

The lanes below are logical audit responsibilities. They do not imply separate user-facing sessions or mandatory worktrees.

### Lane A — Source semantics and contract

Establish what each field means before testing values.

Audit:

- authoritative source/provider;
- endpoint/file semantics;
- units;
- market/session scope;
- raw vs adjusted status;
- publication / first-known semantics;
- revision behavior;
- missingness semantics;
- identifier semantics;
- source-specific exceptional behavior.

Output: explicit data contract and unresolved semantic unknowns.

### Lane B — Structural and coverage integrity

Audit exhaustively where practical:

- required columns;
- key uniqueness;
- type/domain constraints;
- official calendar/session membership;
- listing/tradability coverage;
- missing sessions / duplicate sessions;
- invalid OHLC or arithmetic identities;
- coverage breaks through time;
- unit consistency.

Output: structural census and hard invariant failures.

### Lane C — PIT / causality / provenance

Audit:

- source event time;
- publication/knowledge time;
- decision cutoff;
- feature usability time;
- future leakage;
- revision lineage;
- immutable input hashes;
- current-vs-historical universe contamination;
- exact artifact lineage.

Output: PIT verdict plus provenance manifest.

### Lane D — Economic and event semantics

Audit data transformations against market/economic meaning.

Examples:

- corporate actions and price basis;
- split/reverse split;
- rights / HMETD;
- bonus shares;
- dividends;
- suspension/resumption;
- IPO/relisting/delisting;
- share-count changes;
- accounting identities;
- provider-specific adjustment logic.

Do not apply one generic formula across event types merely because the data shape is similar.

Output: event-family verdicts and backward/forward contamination exposure where relevant.

### Lane E — Anomaly and distribution census

Search for what the contract did not anticipate.

Examples:

- largest absolute price discontinuities;
- largest volume/value jumps;
- largest flow shocks;
- abrupt ticker coverage changes;
- repeated extreme tickers;
- improbable zeros / constants;
- suspicious boundary timestamps;
- feature discontinuities;
- unexpected cross-sectional spillover.

Every material anomaly must be explained, quarantined, confirmed defective, or left `UNKNOWN`.

Output: ranked anomaly table with classifications.

### Lane F — Independent recomputation and blast radius

Independently recompute decision-changing quantities without reusing the potentially faulty production transformation helper.

Then trace:

raw evidence
-> canonical/clean data
-> representation/features
-> eligibility/admission
-> model-input identities

If a defect is found, quantify separately:

- direct affected rows/tickers;
- downstream rolling-window rows;
- cross-sectional/market spillover;
- exact research-eligible identities;
- exact model-fit identities when authorized;
- production/prospective impact if applicable.

Outcome values are not required merely to establish identity membership.

Output: exact blast-radius report.

### Lane G — Adversarial falsification

This lane assumes the current concern may be wrong.

Try to prove the pipeline safe by finding:

- upstream adjustments;
- hidden exclusions;
- correct resets;
- benign numerical-only differences;
- alternate semantic explanations;
- evidence that affected rows never enter the controlled scope.

Also try to falsify any proposed remediation.

The same worker should not both establish the primary claim and certify its independent falsification when independent capacity is available.

Output: strongest counter-case and whether it survives evidence.

## MAIN responsibilities

MAIN owns:

- scope and frozen-boundary protection;
- lane allocation;
- execution-surface selection;
- preventing duplicate writes;
- reconciliation of conflicting findings;
- deciding whether differences are numerically/economically material;
- final gate verdict;
- deciding whether remediation is authorized;
- converting confirmed incidents into permanent regression protection.

Workers provide evidence, not the final scientific authority. Worker results report back to MAIN. The default user-facing session count remains one even under HEAVY orchestration.

## Mandatory verdict shape

Every material QA audit should end with explicit fields appropriate to the task, including at minimum:

```text
DATA_ADMISSION = PASS | FAIL | UNKNOWN
RESEARCH_ADMISSION = PASS | FAIL | UNKNOWN | NOT_EVALUATED
MODEL_PROMOTION = PASS | FAIL | UNKNOWN | NOT_EVALUATED
MATERIALITY = NONE | MINOR | MATERIAL | INDETERMINATE
REMEDIATION_REQUIRED = YES | NO | INDETERMINATE
```

Add domain-specific verdicts when useful, for example:

```text
PIT_INTEGRITY =
CA_PRICE_BASIS_INTEGRITY =
BACKWARD_WINDOW_INTEGRITY =
UNIVERSE_INTEGRITY =
EXACT_FINAL_FIT_IMPACT =
```

A required `UNKNOWN` blocks promotion.

## Artifact contract

For a material audit, preserve:

- input manifest with exact path/ref and SHA-256 where possible;
- generated audit artifacts with SHA-256;
- check-level report;
- anomaly census;
- golden/adversarial case results;
- blast-radius output;
- checkpoint containing final interpretation.

Do not write audit outputs over canonical source artifacts.

## Incident closure

A confirmed material bug is not closed merely when the affected rows are fixed.

Closure requires:

1. root cause documented;
2. blast radius bounded;
3. remediation/quarantine verified if authorized;
4. permanent invariant or golden case added;
5. regression test added where feasible;
6. independent red-team passes;
7. controlling gate re-run;
8. coordination status updated.

## Default safety rules

Unless the user explicitly authorizes otherwise:

- no protected outcome access;
- no model tuning/refit;
- no frozen-science changes;
- no counter reset or mutation;
- no retroactive trade/fill creation;
- no production provider writes;
- no capture/runtime activation;
- no reinterpretation of ambiguous evidence as PASS.
