# Alpha Red-Team Adjudication V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_SCOPED_ADJUDICATION / NO ADMISSION`

## Boundary

This checkpoint adjudicates independent read-only findings against the durable
outcome-blind research corpus. It does not open H5/H10, IC/ICIR, OOS, PnL,
incumbent predictive outcomes, or equivalent protected fields. It does not
mutate canonical data, provider state, cloud/R2, capture, telemetry,
schedulers, production, or incumbent state.

## 1. CNTX population gap — confirmed and narrowed

The frozen research panel has 981,940 rows and 945 tickers. The regular ACTIVE
anchor file has 982,398 rows and 946 tickers. The 458 anchor-only rows are all
`CNTX`, spanning 2021-04-29 through 2024-08-01; the panel has zero `CNTX` rows.
All other panel keys are contained in the ACTIVE-anchor key set, and panel
ticker lifetimes match the corresponding ACTIVE-anchor lifetimes for observed
tickers.

The replay's `build_universe()` seeds its ticker set from panel tickers. A
panel-absent ticker therefore cannot enter that replay's eligibility
evaluation. The 981,940-key zero-mismatch result proves observed-panel replay
reproducibility and panel-to-anchor overlap only. It does not prove historical
population completeness, survivorship safety, delisted/relisted coverage, or
that a panel-absent security should be excluded.

`CNTX` is therefore a material population-boundary example, not evidence that
the panel is wrong. The durable conclusion remains `UNKNOWN / BLOCKED` for
historical population completeness.

The broader state census shows why the boundary matters: the anchor contains
982,398 ACTIVE and 121,666 NO_TRADE rows across 980 tickers. The panel overlaps
all ACTIVE keys and zero NO_TRADE keys; 34 anchor tickers are NO_TRADE-only,
while CNTX is the lone ACTIVE ticker absent from the panel. This establishes
active-trade panel semantics, not completeness of the anchor or historical
universe.

## 2. Durable evidence-reference integrity — confirmed and repaired

Five stale current-tree reference occurrences were reproduced from the
challenger report:

| Registry occurrence | Classification | Repair |
|---|---|---|
| `CONSTRUCTOR-REPLAY-026` future-evaluation packet | stale path | use the existing 2026-09-19 packet |
| `LANE-INTEGRITY-029` research protocol | stale path | use the existing 2026-09-19 protocol |
| `COMMON-SUPPORT-033` future-evaluation packet | stale path | use the existing 2026-09-19 packet |
| `F-003` re-entry queue | stale path | use the existing non-`ALPHA_` re-entry queue |
| `NR-012` re-entry queue | stale path | use the existing non-`ALPHA_` re-entry queue |

The strengthened verifier then found one additional stale occurrence in
`COMMON-SUPPORT-033`: its eligibility-policy packet used a 2026-09-19 path,
while the canonical artifact is the existing 2026-09-20 packet. It was repaired
and classified in the same ledger. The durable total is therefore six repaired
occurrences: five independently reported plus one newly surfaced by the
fail-closed verifier.

Six unique commit-qualified historical refs are not present in this checkout's
Git object database. They remain referenced for historical provenance but are
explicitly classified as unavailable, with current-tree navigation replacements
marked `SUPERSEDED_OR_NONEXACT`; no byte-equivalence is claimed.

The new `evidence_reference_integrity_v1.json` ledger records both classes.
`verify_alpha_knowledge_base_v1.py` now checks every JSONL registry reference:
current and absolute refs must resolve; unavailable historical Git refs must be
listed with a reason and replacement status; and a ref classified unavailable
fails if it later resolves. This closes the previously silent reference-rot
path without changing the research conclusions.

## 3. C3 interpretation — causal wording weakened

An independent same-year consecutive-session replay found 271 usable pairs and
Spearman correlation approximately `-0.3545581106` between finite support count
and turnover (Pearson approximately `-0.2137428860`). This confirms that C3
mechanics are support-sensitive. It does not establish sparse support as the
cause of C3's turnover or persistence pattern; the correlation itself is not a
causal test.

Active synthesis and frontier language is therefore changed to:

> C3 behavior is support-sensitive, but current evidence does not establish
> sparse support as the cause of its turnover/persistence pattern.

Older wording is retained only as historical evidence with this adjudication
superseding its causal interpretation.

## 4. C2 quadrants — component/anatomy evidence, not independent mechanism

C2 is `ret_5 * log(abnormal turnover)`. The existing quadrant table is a useful
decomposition of that formula, but the zero cross-sign selection and the two
sign-consistent selected modes are largely algebraically implied by product
ordering when enough positive scores exist. The observed 68.68% positive-
return/high-activity and 31.32% negative-return/low-activity slot shares are
therefore classified as component/anatomy evidence, not independent mechanism
confirmation or regime evidence. No candidate split or policy change follows.

## 5. Component-anatomy missingness — assertion added and passed

The original component-anatomy producer asserted finite value equality but did
not assert stored/recomputed finiteness-mask equality. A companion verifier now
asserts that property over every eligible key:

| Candidate | Stored finite | Recomputed finite | Mask mismatches |
|---|---:|---:|---:|
| C1 | 295,243 | 295,243 | 0 |
| C2 | 310,761 | 310,761 | 0 |
| C4 | 310,323 | 310,323 | 0 |

This is implementation consistency evidence only. It does not establish PIT,
population completeness, survivorship, corporate-action basis, capacity, or
predictive validity.

## Reproducibility

- Durable adjudication: `research_knowledge/redteam_adjudication_v1.json`
- Reference ledger: `research_knowledge/evidence_reference_integrity_v1.json`
- Reference verifier: `research/verify_alpha_knowledge_base_v1.py`
- Missingness verifier: `research/verify_alpha_candidate_component_anatomy_missingness_v1.py`
- Missingness artifact: `research_knowledge/candidate_component_anatomy_missingness_v1.json`
- Isolated missingness result SHA-256: `ce7c6d49d279cb1eafdc24a3c880390e4c58fec1a425429e2ebc9e02d804a12d`

All findings remain outcome-blind and structural. No candidate, era, eligibility
policy, population, source, or production surface was admitted.
