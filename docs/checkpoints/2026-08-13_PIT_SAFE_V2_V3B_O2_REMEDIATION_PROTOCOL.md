# PIT-Safe V2 / V3-B / O2 Remediation Protocol

Date: 2026-08-13 (Asia/Jakarta)
Status: `PREREGISTERED_BEFORE_CORRECTED_REBUILD`
Branch: `codex/pit-safe-v2-v3b-o2-reproduction-v1`
Parent audit: `codex/frozen-lineage-impact-audit-v1`
Parent audit HEAD: `9395b5c26e0db1a280acee4cac9d5fa76d198e8c`

## Purpose

The accepted frozen-lineage audit found that a KOCI panel observation dated
2023-10-06 entered causal feature construction even though the frozen
security master has `listed_from=2023-10-07`. This protocol defines a generic
PIT-safe historical remediation and reproduction boundary. It does not alter
the old artifacts or their historical verdicts.

## Immutable historical lineage

The following remain read-only historical evidence and must never be
overwritten:

- immutable signal panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- frozen V2, V3-B, and O2 input tables, models, manifests, predictions, and
  historical checkpoints;
- the existing O2 forward archive, counter, and prospective model identity.

Corrected outputs must use a new versioned external artifact root and new
filenames/hashes. No fixed-name replacement is permitted.

## Frozen correction contract

### PIT/listing domain

Before any ticker-level, rolling, liquidity, breadth, market-context,
cross-sectional, rank, median, count, label, or other causal feature
construction, retain only observations whose ticker exists inside its valid
security-master listing interval on that observation date:

`listed_from <= observation_date <= listed_to`

where a missing `listed_to` means open-ended only after strict validation of
the non-null listing fields. This rule is generic and must not special-case
KOCI or any other ticker. Filtering only final model rows is insufficient.

### Date validation

Non-null listing dates must parse successfully and satisfy the accepted
security-master date semantics. A malformed finite/non-null date is an error
and fails closed; it must not be coerced into `NaT` and treated as open-ended.

### Duplicate validation

Conflicting duplicate `(ticker, observation_date)` records fail closed before
feature construction. Identical duplicates may be retained or collapsed only
if the already accepted contract explicitly permits that operation; no
last-write-wins behavior may resolve a conflict silently.

### Boolean validation

Verification fields accept only strict canonical boolean values. Textual
values such as `"False"` must not become true through generic `bool()` or
`astype(bool)` coercion. Invalid non-null values fail closed.

### Model semantics

The original V2, V3-B, and O2 feature definitions, H10 target semantics,
folds, horizons, model families, hyperparameters, eligibility rules, metrics,
and survivor gates remain unchanged. No new feature, tuning, calibration,
threshold, population enlargement, or rescue rule is authorized.

## Execution order

1. Commit this protocol before corrected artifact or model outputs.
2. Reconstruct a new PIT-safe panel from existing frozen source artifacts;
   never redownload data merely to obtain a different answer.
3. Exhaustively validate domain, dates, duplicates, calendar membership, and
   identities; quantify removed rows/tickers/sessions and earliest/latest
   affected observations. Explicitly verify that KOCI 2023-10-06 disappears.
4. Rebuild corrected V2, V3-B, and O2 input tables without fitting models.
5. Compare old versus corrected identities and feature values, including
   KOCI propagation and cross-sectional/rolling washout.
6. Decide the reproduction boundary before any fitting:
   - `EXACT_REPRODUCTION_ALLOWED` only if the corrected pipeline does not
     change any candidate-comparison or selection input;
   - `HISTORICAL_LADDER_REPLAY_REQUIRED` when contamination entered data used
     for candidate comparison or model selection;
   - `REPRODUCTION_BLOCKED` when required frozen inputs/provenance cannot be
     reconstructed defensibly.
7. Fit only if the boundary decision authorizes it. If authorized, replay the
   minimum original ladder in its preregistered order: V2 first, then V3-B,
   then O2 as applicable. Do not assume the old champion survives.

## Prohibited actions

No provider/network call, protected or fresh-forward outcome access, consumed
Stage-5 holdout reuse outside its original semantics, prospective O2 scoring,
counter reset, EOD deployment, provenance-registry absorption, frontend work,
model/data-contract weakening, ad hoc tuning, rescue experiment, or overwrite
of old artifacts is allowed.

## Required evidence

Every corrected artifact must record its parent source hashes, this protocol
SHA-256, code commit, row/ticker/date counts, output SHA-256, feature-order
SHA where applicable, parent lineage, and whether it supersedes the old
artifact. Old and new lineages must remain distinguishable.

The final state must explicitly report whether contamination was removed, its
exact scale and propagation, the reproduction boundary, each model's clean
verdict if fitting is authorized, and whether a separate future O2
prospective validation would be required.
