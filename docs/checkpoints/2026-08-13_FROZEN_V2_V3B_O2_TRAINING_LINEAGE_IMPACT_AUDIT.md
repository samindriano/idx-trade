# Frozen V2 / V3-B / O2 Training-Lineage Impact Audit

Date: 2026-08-13 (Asia/Jakarta)  
Branch: `codex/frozen-lineage-impact-audit-v1`  
Audit HEAD: `a22c87cf7cef8708d4b0de77923460a26715c253`  
Scope: forensic, read-only impact audit of the exact frozen historical training lineage.

## Decision

The accepted repository-wide scientific-integrity audit identified genuine
fail-open code paths. This audit does not clear those repository defects. It
answers the narrower question of whether they affected the exact frozen
historical model inputs for V2, V3-B, and O2.

Model verdicts:

| Model | Verdict |
|---|---|
| V2 | `TRAINING_LINEAGE_IMPACT_FOUND` |
| V3-B | `TRAINING_LINEAGE_IMPACT_FOUND` |
| O2 | `TRAINING_LINEAGE_IMPACT_FOUND` |

The confirmed impact is a narrow PIT/listing-boundary contamination inherited
by all three lineages through the V2 causal feature build. It is quantified
below. It does not authorize a refit, metric reinterpretation, holdout reuse,
forward-outcome access, or a model repair in this lane.

## Boundaries

No provider or network calls, retraining, refitting, rescoring, protected
outcome access, consumed-holdout access, prospective O2 archive access, or
data/model mutation occurred. Active EOD, provenance-registry, and
forward-evaluator lanes were not patched.

The prior accepted checkpoint remains controlling for the repository-wide
release decision:
`docs/checkpoints/2026-08-13_REPOSITORY_SCIENTIFIC_INTEGRITY_AUDIT_INDEPENDENT_ACCEPTANCE.md`.

## Frozen shared lineage

| Artifact | SHA-256 / facts |
|---|---|
| Immutable signal panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`; 981,940 rows, 945 tickers; 2021-04-29 through 2026-07-31; zero duplicate `(ticker,date)` keys |
| Official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`; 1,260 dates; no duplicate dates or parse errors |
| PIT security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`; 979 tickers; 979 unique ticker identities; all 16 non-empty `listed_to` values parseable |
| V2 prepared table | `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`; 292,633 rows, 737 tickers, signal sessions 20..1250 |
| V2 final model | `5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace` |
| V2 final manifest | `f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace` |
| V3-B training table | `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe`; exact V2 row identity population |
| V3-B final model | `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6` |
| V3-B final manifest | `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9` |
| O2 final training-row file | `59b95ad907a8adc911bbf2a411cb1b52a433bd3d225927268440a11b958f6c6f`; 278,168 rows, 729 tickers |
| O2 final model | `42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb` |
| O2 model manifest | `535875e74a1b3a6532e95addf819521758798a767bc49ee9b30d54054a0ae7c2` |
| O2 artifact manifest | `a7045257aa85c9d1020d3fe4ceb60a1ee100aadc827305ddf5c608a616adc2d3`; all 8/8 child hashes matched |

V3-B preserves the V2 row identity and adds eight Structure-Lite features.
Its feature-order hash is
`100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9`.
O2 is an exact 278,168-row subset of V3-B, excluding 14,465 rows: 12,589
without usable Open and 1,876 flat high-low bars. It appends
`open_position`, `open_to_high`, and `open_to_low`; the 36-feature order hash
is `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`.
The O2 common-support identity hash is
`716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`.

All final V2, V3-B, and O2 rows mapped to the pinned calendar with zero
session-index mismatches, and all final rows were inside their security-master
listing intervals. Those checks validate final row dates; they do not prove
that upstream feature construction used only valid PIT rows.

## Directly confirmed historical impact

The exact panel contains `KOCI` on `2023-10-06`; the frozen security master
has `KOCI.listed_from = 2023-10-07`.

The V2/V3-B feature builder computes rolling and liquidity features over the
panel before the later primary-model-row filter:

- `research_features.py:146` assigns `observed_session_count` from every
  observed panel row;
- `research_v2_features.py:124-142` builds the primary block and its
  `market_primary_liquid_count` before `prepare_primary_model_table` filters
  model rows;
- `ranking_v2_prepare_cache.py:112-114` runs those stages in that order.

Direct artifact evidence:

- first V2/V3-B model row: `KOCI`, `2023-11-02`, official session `613`;
- the row is `universe_primary_liquid=true`, `binary_target=1`,
  `label_status=TP_FIRST`;
- `observed_session_count=20` while exact listing age is `19`, showing that
  the pre-listing panel row was counted in causal history;
- session 613 has 200 retained V2 rows and every row records
  `market_primary_liquid_count=285`; KOCI is one of the qualifying primary
  rows. Removing the invalid pre-listing contribution would change the
  retained session context to 284 for at least the 199 other retained rows,
  before considering additional rolling/median/rank changes;
- O2 includes the KOCI 2023-11-02 row in its 278,168-row common support, so the
  contamination is inherited by O2 rather than being limited to an excluded
  parent row.

This proves model-input impact without requiring a counterfactual refit. The
full downstream numeric delta across every affected feature was not estimated
because doing so would be a new reproduction experiment outside this audit.

## P1 risk matrix

Verdicts use the frozen vocabulary requested by the audit. They distinguish a
code defect from use of the path and from an observed model-input effect.

| Accepted risk | V2 | V3-B | O2 | Evidence / qualification |
|---|---|---|---|---|
| Textual `False` becomes truthy | `NOT_APPLICABLE_TO_FROZEN_LINEAGE` | `NOT_APPLICABLE_TO_FROZEN_LINEAGE` | `APPLICABLE_BUT_NO_OCCURRENCE_FOUND` | The `is_complete` defect exists in `security_master.py`; O2 also uses `open_feature_ready.astype(bool)`, but the frozen readiness CSV is typed boolean with `True=278,168`, `False=14,465`, not textual values. |
| Malformed finite dates become open-ended | `APPLICABLE_BUT_NO_OCCURRENCE_FOUND` | `APPLICABLE_BUT_NO_OCCURRENCE_FOUND` | `APPLICABLE_BUT_NO_OCCURRENCE_FOUND` | `errors="coerce"` exists in the historical security-master path; the frozen master has zero malformed non-empty dates and no final model row outside listing bounds. |
| Conflicting OHLCV silently keeps last row | `APPLICABLE_BUT_NO_OCCURRENCE_FOUND` | `APPLICABLE_BUT_NO_OCCURRENCE_FOUND` | `APPLICABLE_BUT_NO_OCCURRENCE_FOUND` | `data.py`/`storage.py` contain last-write-wins deduplication; final panel, Open panel, coverage rows, and model identities have zero duplicate keys. Pre-collapse raw conflicts are not reconstructible from frozen bundles. |
| Missing source fingerprints | `OCCURRENCE_FOUND_NO_MODEL_INPUT_IMPACT` | `OCCURRENCE_FOUND_NO_MODEL_INPUT_IMPACT` | `OCCURRENCE_FOUND_NO_MODEL_INPUT_IMPACT` | V2/V3 model manifests contain empty `data_snapshot_sha256`; O2 has 1,084/278,168 support rows without `source_raw_sha256`. Current artifact hashes and row classifications still match. |
| Mutable manifest publication | `UNRESOLVED_INSUFFICIENT_PROVENANCE` | `UNRESOLVED_INSUFFICIENT_PROVENANCE` | `UNRESOLVED_INSUFFICIENT_PROVENANCE` | Atomic replacement paths exist and current hashes match, but prior publication/overwrite history cannot be proven from frozen artifacts. |
| Weak PIT/session-domain enforcement | `OCCURRENCE_FOUND_MODEL_INPUT_IMPACT` | `OCCURRENCE_FOUND_MODEL_INPUT_IMPACT` | `OCCURRENCE_FOUND_MODEL_INPUT_IMPACT` | KOCI's pre-listing panel row was included in causal feature construction; its downstream context is present in each model lineage. |
| Provider/source authority and completion | `UNRESOLVED_INSUFFICIENT_PROVENANCE` | `UNRESOLVED_INSUFFICIENT_PROVENANCE` | `UNRESOLVED_INSUFFICIENT_PROVENANCE` | Final artifacts are hash-consistent, but complete historical source authority/tradability reconstruction is not linked into model manifests. |
| Empty successful month can look complete | `APPLICABLE_BUT_NO_OCCURRENCE_FOUND` | `APPLICABLE_BUT_NO_OCCURRENCE_FOUND` | `APPLICABLE_BUT_NO_OCCURRENCE_FOUND` | Pinned calendar has 1,260 unique parseable dates and every model date maps exactly; source-publication completeness remains a separate provenance limitation. |
| Replaceable fixed-name artifact bundle | `UNRESOLVED_INSUFFICIENT_PROVENANCE` | `UNRESOLVED_INSUFFICIENT_PROVENANCE` | `UNRESOLVED_INSUFFICIENT_PROVENANCE` | Current hashes verify; write-once historical publication cannot be established from current files alone. |

## Documentation inconsistency

The old V3-B checkpoint says "non-finite values in the 33 feature columns: 0."
Direct raw-table inspection found expected missing feature cells before the
frozen pipeline imputer: 31,796 null cells in the V2 selected table and
100,993 in the V3-B 33-feature table; 43,472 O2-support rows have at least one
missing V3-B feature. The frozen model contract explicitly uses
`SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)`.
Thus this is a documentation/measurement-definition inconsistency, not a
newly demonstrated model defect. It must not be "fixed" by filling or changing
historical artifacts in this lane.

## Provenance composition

Within the exact O2 support, Open provenance is mixed:

- 189,541 rows `IMMUTABLE_PANEL`;
- 87,073 rows `YAHOO_YFINANCE`;
- 1,554 rows `ZAPI_TRADINGVIEW`.

The support contains no missing provenance join rows, but 1,084 rows lack a
`source_raw_sha256`. This supports a conditional, not fully reproducible,
lineage claim. The immutable panel remains unchanged at SHA
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## Stop / next boundary

Do not refit, rescore, repair, reinterpret historical metrics, access forward
outcomes, or promote execution grade from this result. A future remediation
must be separately preregistered and must decide whether to rebuild the
PIT-safe panel/feature tables and then rerun the historical research ladder.
