# V4 CA Event-Window Semantics V1 — Input Pin Remediation

Date: 2026-08-18 Asia/Jakarta
Branch: `data/idx-v4-ca-event-window-semantics-v1`
Parent failed Stage-1 preflight HEAD: `a281c91a313e8c4ed2ecd823e7f53ccf500ec5b4`
Status: `PREFLIGHT_INPUT_PIN_CORRECTED_REVALIDATION_REQUIRED`

## Trigger

Local validation passed (`18 passed`, `py_compile` PASS, `git diff --check` PASS) and Stage 1 then stopped before census because the frozen runner pinned a malformed 63-character KSEI census `MANIFEST.json` SHA literal:

`7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25`

The immutable local file's actual SHA-256 is the full 64-character value:

`7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25a`

No Stage-1 census, Stage 2, Stage 3, provider call, target/rank, model, prediction, performance, or protected outcome was accessed before this failure.

## Remediation design

The original frozen scientific config and original runners are preserved byte-for-byte as historical preregistration evidence. A narrow preflight remediation overlay and launchers were added that perform exactly one literal replacement of the malformed manifest pin before executing the frozen runners.

Added:

- `config/v4_ca_event_window_semantics_v1_input_pin_remediation.json`
- `scripts/v4_ca_input_pin_remediation.py`
- `scripts/run_v4_ca_event_window_support_pin_remediated.py`
- `scripts/run_v4_ca_schedule_acquisition_pin_remediated.py`
- `scripts/run_v4_ca_event_window_support_with_schedule_pin_remediated.py`
- `tests/test_v4_ca_input_pin_remediation.py`

The helper fails closed unless the target runner contains exactly one malformed literal. It then asserts that exactly one authoritative 64-character SHA remains after replacement.

## Scientific invariants

Unchanged:

- event-family semantics;
- Ex-Date / first-new-basis transition rule;
- entry/terminal crossing rule;
- 90% per-date continuity gate;
- KSEI-only provider scope;
- schedule linkage requirements;
- no Record/Distribution fallback;
- no price-derived inference;
- no R5/R10, target/model/performance/outcome access.

This is an input-identity implementation correction only.

## Next

Local operator must pull latest branch, mark the existing lane ACTIVE, rerun the focused tests including `tests/test_v4_ca_input_pin_remediation.py`, run `py_compile` and `git diff --check`, then use only the pin-remediated Stage 1/2/3 launchers from the remediation handoff. If any validation fails, STOP.
