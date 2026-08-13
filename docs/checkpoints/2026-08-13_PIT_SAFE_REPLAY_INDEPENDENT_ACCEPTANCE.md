# PIT-Safe V2/V3-B/O2 Replay — Independent Acceptance

Date: 2026-08-13 (Asia/Jakarta)
Reviewer: ChatGPT independent review
Reviewed branch: `codex/pit-safe-v2-v3b-o2-reproduction-research-v1`
Reviewed final remote HEAD: `765bdba170eba68d3beab28dae30bd7e694743f8`

## Verdict

`PIT_SAFE_HISTORICAL_REPLAY_ACCEPTED_CLEAN_DEVELOPMENT_DECISION`

The corrected replay is accepted as the preregistered clean historical-development decision for the repaired PIT-safe lineage. This acceptance does **not** create or promote a canonical executable model, overwrite the legacy models, start a forward counter, or authorize fresh-forward outcome access.

## Accepted historical decisions

1. Clean V2 historical champion: `HGB_XS_MARKET` on the corrected 292,631-row / 737-ticker V2 population.
2. Clean V3-B Structure-Lite: `V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`; no rescue or retuning is authorized.
3. O2 raw historical diagnostic remains `O2_SURVIVOR` on the corrected 278,166-row / 729-ticker common-support population.
4. Because the clean V3-B parent failed its frozen gate, the valid clean-lineage conditional status is `O2_DIAGNOSTIC_ORPHANED_PARENT`, not `O2_NO_SURVIVOR` and not a promotable clean O2 lineage.

## Independent review findings

- The replay contract was frozen before the replay and pins the corrected inputs, complete fast-H10 label artifact, fold definitions, model set, evaluation rules, and hard stop conditions.
- Fast-H10 is recorded as exactly equivalent to the legacy full H10 historical label table through the 2026-07-31 development boundary.
- V2 `HGB_XS_MARKET` and the V3-B control were independently compared from persisted replay predictions on 144,221 validation rows across V2F1–V2F6: row identities are exact, scores are exact, and maximum absolute difference is 0.0.
- V3-B fails the frozen late paired gate on the corrected lineage; retaining clean V2 is therefore decision-consistent.
- The O2 raw diagnostic is preserved separately from parent eligibility. The `downstream_verdict_does_not_automatically_propagate` rule is accepted: a failed parent does not rewrite a downstream raw diagnostic into a failure, but the downstream result cannot establish a clean lineage without an accepted parent.
- Replay manifest integrity was reverified (`72/72` source artifact hashes valid), and review-2 added strict boolean parsing so textual values such as `"False"` fail closed.
- Reported validation is clean: full pytest `494 passed, 0 failed`; no provider call, protected fresh-forward outcome access, canonical overwrite, execution promotion, or forward-counter mutation occurred.

## Lineage boundary

The old fitted V2/V3-B/O2 artifacts remain immutable `LEGACY_CONTAMINATED_REFERENCE` evidence only.

The accepted clean state is a **historical development decision**, not yet a final-refit executable model identity:

- clean historical parent: V2 `HGB_XS_MARKET`;
- V3-B clean challenger: rejected;
- O2-on-V3-B: orphaned diagnostic only.

A future clean final-refit/model identity requires its own frozen contract after the intended research ladder is complete.

## Implication for the clean V2 Open-alpha lane

The clean V2 Open-alpha research pass may now use `HGB_XS_MARKET` as the accepted historical parent/control. This does not authorize model fitting by itself. The next permitted step is a separate preregistered one-shot contract for the already selected V2.1/V2.2 challengers, with identical common-support rows, folds, labels, evaluator, and control semantics before any challenger outcome is read.
