# Handoff: INC-001 retained economic-event reconciliation V1.1

from: local Codex continuation  
to: ChatGPT review / next authorized INC-001 action  
task_id: `INC001-ECONOMIC-EVENT-RECONCILIATION-V11`  
lane: `data/ca-aware-feature-basis-remediation-v1`

## Result

`CERTIFIED` for the requested retained-evidence reconciliation only. The
controlling immutable artifact is:

```text
ROOT       = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v3
MANIFEST   = 60d4b5caf9fbadd81c8f63edf4976f2d476ead6a26884c9d74f965759250a746
RERUN_ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v3-rerun
```

V8 remains the controlling source-authority root. V6/V7 and reconciliation
v1/v2 roots are immutable intermediates only; they must not be presented as
authoritative.

## Exact reconciliation

```text
SOURCE_EVIDENCE_ROWS             = 412
PROVEN_CROSS_SOURCE_COLLAPSES   = 20
PROVEN_SAME_SOURCE_COLLAPSES    = 3
ECONOMIC_PHYSICAL_EVENTS        = 389
RESOLVED_TRANSITIONS             = 153
UNRESOLVED_TRANSITIONS           = 190
NON_BASIS_EXCLUDED               = 46
WORKING_389_153_190_46_VERDICT   = CERTIFIED
```

The 412 source rows are retained unchanged. Twenty cross-source and three
same-source collapses are source-bound and hash-bound; the 25 linkage rows
are evidence edges, not 25 additional events. Transition attestations are
156 rows, of which 153 are resolved in the economic result; 34 retained
documents were byte/hash verified with zero failures.

The request ledger is continuous and unique after merging the two already
retained continuation rows: `20 -> 22`, request numbers `1..22`, duplicates
`[]`. No provider call or fresh download was performed.

## Accepted mechanisms and remaining gaps

Mandatory Conversion is not promoted by label alone. Retained evidence proves
33 stock splits, 2 reverse splits, and 4 true security conversions. Retained
Voluntary Conversion rows with explicit IDR consideration produce 46
non-basis tender/cash exclusions; 47 operational rows remain unresolved.

The unresolved economic geometry is preserved exactly in the artifact:

```text
RIGHTS_HMETD 71 | STOCK_SPLIT 21 | REVERSE_SPLIT 1 |
CAPITAL_RESTRUCTURING 19 | BONUS_SHARES 11 | STOCK_DIVIDEND 7 |
MERGER 5 | TRUE_SECURITY_CONVERSION 4 | UNKNOWN_TAXONOMY 4 |
UNRESOLVED_OPERATIONAL_LABEL 47 = 190
```

No unresolved family is force-mapped and no candidate/record/distribution/
listing/payment date substitutes for an accepted regular-market transition
semantic.

## 291-row future plan versus capability verification

The V1.1 acquisition plan remains a plan for exactly 291 unresolved physical
identities, by baseline family:

```text
RIGHTS_HMETD 72 | STOCK_SPLIT 41 | MANDATORY_CONVERSION 39 |
VOLUNTARY_CONVERSION 93 | CAPITAL_RESTRUCTURING 19 | BONUS_SHARES 11 |
STOCK_DIVIDEND 7 | MERGER 5 | UNKNOWN_TAXONOMY 4 = 291
```

The completed 8-row official-source probe is capability verification, not
bulk acquisition. No additional capability request is authorized here. Later
bulk acquisition must remain a separate, explicitly authorized action over
the exact 291 identities, with source-contract completeness, empty/no-event,
source reference, evidence SHA-256, and accepted transition semantics. The
local reconciliation arithmetic (`291 - 32 - 46 - 23 = 190`) is evidence
accounting only and does not authorize bulk work.

## Forensic boundaries retained

The five in-scope `gabungUsaha` rows remain physical events; outside-geometry
findings remain forensic-only. TPIA documents that prove one underlying event
are linked without making document count a new admission rule. Parsed KSEI
pages remain observed pages, not complete source-certified intervals.

ADRO/AADI 2024 remains a source-authority and ontology gap. ADRO's retained
`Right Distribution` names `ADRO-H` and is not source proof of AADI
distribution-in-specie; the ADRO special cash dividend is separate. The
finding is `REQUIRES_POLICY_DECISION` / taxonomy `UNKNOWN`, not a silent
`CAPITAL_RESTRUCTURING` mapping and not a new frozen family. The retained
`Pemisahan Unit Usaha` TPIA labels and seven `gabungUsaha` rows are likewise
preserved with source provenance and remain unmapped until policy and source
semantics justify treatment.

## Boundaries and final gate

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

Final validation was run in an isolated local environment: focused `7`
passed, CA/integrity `131` passed, full pytest exit `0`, py_compile `46`
files PASS, artifact hash audit PASS, and deterministic comparison PASS.
`git diff --check` and exact-head CI must be recorded after the handoff files
are committed/pushed. Stop for ChatGPT review; do not merge or execute
production work.
