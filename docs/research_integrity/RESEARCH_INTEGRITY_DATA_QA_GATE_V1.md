# Research Integrity / Data QA Gate V1

Status: `ACTIVE_IMPLEMENTATION`

Branch: `audit/research-integrity-data-qa-gate-v1`

## Purpose

This gate exists to prevent a dataset, representation, experiment, or model from being promoted merely because its statistical metrics look good.

The governing rule is:

> absence of evidence is not evidence of integrity.

For every required integrity check, `UNKNOWN` is blocking exactly like `FAIL` until the uncertainty is resolved or the scope is explicitly changed by an authoritative contract.

This framework does not change frozen V4-X1, Decision V2, Sizing V1, Execution V1, prospective counters, protected outcomes, or capture/runtime state.

## Three admission stages

### A. `DATA_ADMISSION`

A data family is not research-eligible until the data layer can explain what each critical field means and prove that the observed rows obey the required semantics.

Default required checks are defined in `config/research_integrity_gate_v1.json` and include:

- source semantics;
- required schema;
- key uniqueness;
- units contract;
- official-session/calendar membership where applicable;
- missingness policy;
- point-in-time knowledge-time admissibility;
- corporate-action / price-basis semantics where applicable;
- known-event golden cases;
- anomaly reconciliation;
- immutable provenance / hashes.

Existing `src/idx_trade/data_gate.py` remains a lower-level hard gate for ticker coverage, corporate-action verification, and price-semantics verification. V1 builds above that primitive rather than replacing it.

### B. `RESEARCH_ADMISSION`

Research cannot open targets merely because raw data passed basic validation.

The representation must additionally prove:

- Data Admission passed;
- important feature calculations have an independent recomputation path;
- backward-looking windows do not silently mix incompatible semantic regimes;
- universe membership is PIT-safe;
- the current discovery phase obeys its outcome-access contract;
- human-facing visual sanity review has been completed;
- difficult known-event feature cases pass;
- the representation can be reproduced from immutable inputs.

The corporate-action incident that motivated this gate belongs here: checking an event date is insufficient if a 5/14/20/60-session feature window can still contain pre-event prices on an incompatible basis.

### C. `MODEL_PROMOTION`

A model cannot become a frozen incumbent only because OOS statistics pass.

Promotion additionally requires:

- Research Admission passed;
- experiment contract frozen before confirmatory evidence;
- valid OOS / prospective methodology;
- exact model-input lineage;
- reproducible artifacts and hashes;
- cost / turnover / capacity assessment where the model implies trading;
- independent red-team falsification;
- all confirmed integrity incidents converted into regression protection.

Performance is deliberately the last layer, not the first integrity test.

## Status semantics

Every check has exactly one status:

- `PASS` — positive evidence supports the contract.
- `FAIL` — evidence contradicts the contract.
- `UNKNOWN` — evidence is absent, ambiguous, inaccessible, or insufficient.

For a required check:

```text
PASS     -> may proceed
FAIL     -> blocked
UNKNOWN  -> blocked
```

An optional diagnostic may be `FAIL`/`UNKNOWN` without blocking, but it must remain visible as a non-blocking finding. A check listed as required by a profile cannot be downgraded to optional at runtime.

## Core invariants in code

`src/idx_trade/research_integrity_gate_v1.py` provides the common fail-closed evaluator plus reusable primitives for:

- required columns;
- unique keys;
- non-negative numeric domains;
- OHLC identities;
- additive accounting identities such as `foreign_net == foreign_buy - foreign_sell`;
- PIT knowledge-time ordering;
- required-check profile loading.

These are primitives, not a claim that every dataset shares the same semantics. Data-family-specific contracts remain mandatory.

## Golden-event policy

Every material integrity incident must become at least one durable adversarial/golden case.

Examples of required difficult families for market-price research include:

- stock split;
- reverse split;
- rights / HMETD;
- bonus shares or stock distributions;
- large ordinary cash dividend as a distinct semantic class;
- suspension / resumption;
- IPO / relisting;
- delisting / terminal coverage;
- identifier or universe-history changes.

The test must cover the full blast radius relevant to the representation, not merely the event row.

For a structural corporate action, that normally means checking the maximum backward feature lookback used by the representation.

## Independent implementation rule

A critical quantity is not independently verified when the audit calls the same production helper that may contain the original bug.

Where decision-changing, use:

```text
production implementation A
        vs
independent audit implementation B
```

The independent path should share source data and contract, not the same transformation helper.

## Anomaly reconciliation policy

Each admitted build should produce a bounded anomaly census appropriate to the data family, for example:

- largest absolute price moves;
- largest volume/value jumps;
- largest share-count changes;
- largest foreign-flow shocks;
- unexplained coverage breaks;
- unexplained timestamp reversals;
- largest cross-sectional feature discontinuities.

Extreme observations are not automatically errors. Each material anomaly must be classified as:

- economically explained;
- known data limitation and quarantined;
- confirmed data defect;
- unresolved -> `UNKNOWN` -> promotion blocked when the anomaly is material to the research scope.

## Incident-to-regression rule

Every confirmed integrity failure must leave a permanent artifact:

1. incident ID;
2. root cause;
3. affected lineage / blast radius;
4. remediation or quarantine contract;
5. invariant or golden case that would have caught it;
6. automated regression test where feasible.

The project objective is not zero future bugs. It is that the same class of bug should become progressively harder to reintroduce silently.

## Stop-science rule

When a potentially material integrity defect is discovered:

```text
STOP SCIENCE
-> audit blast radius
-> determine exact lineage impact
-> remediate or quarantine
-> add permanent invariant/golden test
-> independently verify
-> only then resume research/promotion
```

Do not rescue performance, retune, refit, or open protected outcomes while the integrity verdict is unresolved unless the user explicitly creates a separately authorized task.

## Required evidence for a gate verdict

A material QA gate should leave enough evidence for another agent to reproduce the verdict without relying on chat memory:

- exact branch / commit;
- exact input paths and SHA-256 where available;
- source semantics / data contract;
- check-by-check statuses;
- blockers and unresolved unknowns;
- anomaly census or bounded explanation;
- golden/adversarial cases;
- blast-radius summary;
- generated artifact hashes;
- final explicit verdict.

## Current first application: historical CA / price-basis integrity

The first concrete use of this framework is the historical corporate-action / feature-price-basis audit.

The audit must distinguish at least:

- target-window CA continuity;
- feature-input price-basis integrity;
- backward rolling-window contamination;
- direct affected ticker/session rows;
- cross-sectional / market spillover;
- exact final-fit identity membership;
- semantic differences between split, reverse split, rights, bonus shares, conversion, and ordinary cash dividend.

No remediation or model refit is authorized by this document alone.
