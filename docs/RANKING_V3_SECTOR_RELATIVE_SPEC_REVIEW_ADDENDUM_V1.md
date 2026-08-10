# Ranking V3-D Sector-Relative — Pre-Outcome Review Addendum V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **PRE-OUTCOME IMPLEMENTATION REVIEW PASS — OUTCOME RUN REMAINS BLOCKED**

Reviewed baseline:

`docs/RANKING_V3_SECTOR_RELATIVE_SPEC_V1.md`

No V3-D model outcome, V2F5/V2F6 outcome, or reserved post-2026-07-31 V2 forward outcome was accessed during this review.

## 1. Review conclusion

PASS as an implementation baseline. The provisional V3-D experiment remains appropriately narrow:

- exact V2 global control;
- one exact V2 + six-sector-feature candidate;
- three raw concepts only: return-5, return-20, close-position-20;
- two transforms per concept: within-sector percentile rank and stock-minus-sector median;
- no Structure-Lite or Regime inheritance;
- no sector-specific experts, threshold grid, feature ablation, or rescue variant.

The V3-D outcome run is **not authorized** by this document.

## 2. PIT sector source provenance must be evidenced, not merely declared

A `source_sha256` value inside the sector-history table is necessary but not sufficient to pass the final PIT sector-history gate.

Before a V3-D run authorization may be created, every unique `(source_id, source_sha256)` referenced by the validated sector-history artifact must be tied to an actual immutable source document/snapshot or a trusted immutable archive entry whose bytes/hash can be independently verified.

The final data-gate checkpoint must record:

- source identifier;
- source location/archive identity;
- expected SHA-256 from sector history;
- independently computed SHA-256 or trusted immutable archive hash;
- verification PASS/FAIL;
- classification taxonomy/version represented by that source;
- effective/availability-date interpretation used to derive history intervals.

If source bytes or immutable archive identity cannot be verified, V3-D remains `BLOCKED_PIT_SECTOR_HISTORY`. Do not treat a current company-profile sector field as historical evidence.

## 3. Current candidate remains unchanged

The six provisional model features remain exactly:

1. `sector_rank_close_return_5`
2. `sector_rank_close_return_20`
3. `sector_rank_close_position_20`
4. `sector_relative_close_return_5`
5. `sector_relative_close_return_20`
6. `sector_relative_close_position_20`

Feature computation must use the full same-date causal primary-liquid universe with valid PIT sector membership, not only rows whose H10 target later resolves.

Minimum finite group size remains five securities per `(date, sector, source-concept)`.

## 4. Implementation hardening completed pre-outcome

The implementation baseline includes:

- PIT interval validation with `usable_from=max(effective_from, available_at date)`;
- no historical backfill before `usable_from`;
- rejection of overlapping usable intervals;
- security-master identity check;
- source-id and source-SHA syntax validation;
- explicit handling of open-ended intervals;
- six fixed same-date sector features;
- F1-F4-only prepared-cache path;
- exact recomputed V2 25-feature equivalence proof;
- pre-score sector/feature coverage gate;
- exact V2 control-equivalence gate;
- sector concentration/top-decile/per-sector diagnostics;
- explicit F5/F6 hard block;
- separate authorization-file requirement before the `run` command can execute.

A later V3-D outcome authorization must pin the final spec, implementation commit, cache, cache manifest, PIT source-provenance report, and completed independent V3-C review.

## 5. One allowed pre-outcome amendment point

The user explicitly authorized asynchronous V3-D engineering while V3-C runs. Therefore, after V3-C returns, one outcome-blind V3-D amendment is permitted **before any V3-D outcome is viewed**.

The preferred use of that amendment is diagnostic/guardrail refinement rather than contaminating attribution. In particular:

- if V3-C exposes a regime-specific weakness, V3-D may add preregistered regime-stratified diagnostics using the already-frozen V3-C state definition;
- V3-D should still test sector-relative features on the exact global V2 HGB rather than silently inheriting V3-C experts;
- combining independently surviving components remains reserved for the one-shot integration experiment.

Any amendment must be documented, re-hashed, independently reviewed, and applied before V3-D cache/outcome authorization.

## 6. Current blockers

V3-D cannot yet be scored because:

1. V3-C has not yet returned for independent review;
2. no real PIT sector-history artifact has yet been validated against the required contract;
3. referenced sector source documents/snapshots have not yet been hash-verified;
4. therefore no final immutable V3-D cache or run-authorization JSON exists.

F5/F6 and reserved V2 fresh-forward outcomes remain sealed.
