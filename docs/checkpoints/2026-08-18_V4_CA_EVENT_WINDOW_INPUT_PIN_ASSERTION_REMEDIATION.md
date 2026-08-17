# V4 CA Event-Window Semantics V1 — Input Pin Assertion Remediation

Date: 2026-08-18 Asia/Jakarta
Branch: `data/idx-v4-ca-event-window-semantics-v1`
Parent failed validation HEAD: `aa68adb97022903ce69dd4270d96513f5f203310`
Status: `PREFLIGHT_ASSERTION_BUG_CORRECTED_REVALIDATION_REQUIRED`

## Trigger

Local validation stopped before Stage 1 with `20 passed, 1 failed` at:

`tests/test_v4_ca_input_pin_remediation.py::test_frozen_runners_receive_only_the_exact_pin_replacement`

Error:

`V4_CA_PIN_REMEDIATION_BAD_LITERAL_REMAINS`

No Stage 1/2/3 execution, provider call, target/rank, model, prediction, performance, or protected outcome access occurred.

## Root cause

The remediation correctly replaced the malformed 63-character SHA literal with the authoritative 64-character SHA. However, the postcondition checked:

`BAD_KSEI_MANIFEST_SHA in remediated`

The malformed 63-character string is necessarily a prefix substring of the corrected 64-character string, so this assertion remained true even after a correct replacement.

This was a validation-helper defect, not a failure of the input-pin correction and not a scientific/event-semantics change.

## Correction

The helper and regression test now operate on exact quoted Python string literals:

- bad token: `"<63-char SHA>"`
- good token: `"<64-char SHA>"`

The helper requires exactly one exact bad token before replacement, zero exact bad tokens afterward, and exactly one exact good token afterward.

## Scientific invariants

Unchanged:

- corporate-action event-family semantics;
- Ex-Date / first-new-basis transition semantics;
- window crossing rule;
- 90% per-date continuity gate;
- KSEI-only source policy;
- no Record/Distribution fallback;
- no price-derived inference;
- no R5/R10, target/model/performance/outcome access.

## Next

Rerun the same focused validation including `tests/test_v4_ca_input_pin_remediation.py`. Only if pytest, py_compile and `git diff --check` all pass may the pin-remediated Stage 1 launcher run. If validation fails again, stop before Stage 1.