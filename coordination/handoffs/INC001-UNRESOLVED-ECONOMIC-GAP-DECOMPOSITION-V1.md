# Handoff: INC-001 unresolved economic-gap decomposition V1

from: local Codex continuation
to: ChatGPT review / next authorized INC-001 action
task_id: `INC001-UNRESOLVED-ECONOMIC-GAP-DECOMPOSITION-V1`
lane: `data/ca-aware-feature-basis-remediation-v1`

## Controlling result

The accepted V3 economic reconciliation remains unchanged:

```text
412 source rows
389 economic physical events
153 resolved transitions
190 unresolved economic events
46 non-basis exclusions
```

The new immutable local decomposition is:

```text
ROOT       = D:\Documents\Project\idx-ca-unresolved-economic-gap-decomposition-20260829-v4
MANIFEST   = 3af6a92738f560f26699725e2f8cf6200dc1dff3fcc6a79d899cb9911d6499bc
RERUN_ROOT = D:\Documents\Project\idx-ca-unresolved-economic-gap-decomposition-20260829-v4-rerun
RERUN_MANIFEST = 157f958705402d80aaf88c5173dd9c2ee1d35083946ac99b333c9bcb8ed0c494
```

V4 is controlling; V1-V3 are immutable historical intermediates only. V4
also carries the corrected affected-event identities for `ANOM-014` and
`ANOM-015`, plus retained index-document linkage fields. These forensic
findings are not additional economic events.

It contains exactly 190 unique unresolved economic IDs and 190 distinct source
rows. The primary reason counts are:

```text
EXACT_TRANSITION_DOCUMENT_NOT_ACQUIRED        105
DOCUMENT_RETAINED_TRANSITION_SEMANTIC_MISSING  34
ECONOMIC_TAXONOMY_UNRESOLVED                   51
```

No local-only resolution candidate was found. All current transition states
remain unresolved and no date was inferred.

## Key family findings

- `RIGHTS_HMETD`: 52 deterministic KSEI lookup templates known but not
  executed; 19 retained KSEI pages insufficient for the accepted regular-
  market ex-date semantic. Future event-specific count: 71.
- `STOCK_SPLIT`: 10 IDX candidate-only rows and 11 KSEI retained-page rows;
  zero exact retained schedules for the 21 residuals.
- `REVERSE_SPLIT`: BBRM only; KSEI `Mandatory Conversion`, ratio `(3 BBRM :
  2 BBRM)`; no reverse-split-specific transition proof.
- `UNRESOLVED_OPERATIONAL_LABEL`: all 47 exact raw labels are KSEI
  `Voluntary Conversion`; blank ratios leave economic classification UNKNOWN,
  not a promoted conversion family.
- `UNKNOWN_TAXONOMY`: four KSEI `Mixed Dividend` rows remain policy/taxonomy
  blockers with no force-map.

The independent native subagent audit agreed that the 22 split/reverse-split
events have 22/22 hash-matched source rows, 14 unique retained raw paths, zero
exact retained transition documents, and no certified transition lower bound.
It also found one detached hash-only transition attestation (BBRM) and two
official index PDF hrefs without retained PDF bytes/hash-bound document rows
(HEAL and SCMA); neither finding permits local resolution.

## Future plan and authority boundaries

The future plan partitions all 190 event IDs into deterministic document fetch
(22), official index lookup (71), authoritative source not identified (46),
taxonomy research (47), and policy decision (4). Capability verification is a
separate three-representative-ticker precondition. No provider or network
acquisition was executed.

The independent blockers remain:

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY           = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY               = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
```

Scientific state is unchanged:

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
PHASE_E_AUTHORIZED      = FALSE
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
PR_108_MERGED           = FALSE
PR_103_MERGED           = FALSE
```

## Review request

Please review the immutable decomposition and its deterministic rerun. No
merge, provider execution, Phase-E, outcome access, model work, counter
mutation, or canonical historical rewrite is authorized by this handoff.

## Validation

- focused economic suite: 7 passed;
- CA/integrity suite: 131 passed, 5 warnings;
- full pytest: 370 passed, 5 warnings;
- py_compile: 47 Python files passed;
- staged `git diff --check`: PASS;
- exact-head GitHub Actions run `33254837877` on `3ade9ef9`: PASS, 370
  passed, 5 pytest warnings. The separate GitHub annotation is the known
  Node.js 20 deprecation warning for `actions/checkout@v4` and
  `actions/setup-python@v5`.

No further production execution is authorized tonight.
