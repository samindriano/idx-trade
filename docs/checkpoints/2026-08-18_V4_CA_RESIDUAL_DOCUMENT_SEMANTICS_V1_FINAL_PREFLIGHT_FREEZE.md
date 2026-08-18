# V4 CA Residual Document Semantics V1 — Final Preflight Freeze

Status: `FROZEN_FOR_LOCAL_VALIDATION_AND_ONE_OFFLINE_RUN`

## Scientific/code anchor

Scientific implementation and tests are frozen at commit:

`fcb1b92f66c1bc1f6f575e4ab191b60e3812b642`

No scientific/code/config changes are authorized after this anchor unless local validation fails before any Stage-A result is exposed.

Pinned Git blobs at the anchor:

- config `config/v4_ca_residual_document_semantics_v1.json`: `a2860ebe24ebb577c0591550066295656a0d9428`
- base residual semantics `src/idx_trade/v4_ca_residual_document_semantics.py`: `5beadf3c3462919a21c215235f185be37366a606`
- layout-bound hardening `src/idx_trade/v4_ca_residual_document_semantics_hardened.py`: `0ef10eb9ace1272fe2151e61ccd3c443daea5364`
- Stage-A runner `scripts/run_v4_ca_residual_document_semantics.py`: `a7a3e9cb5d23f07ee96ad3365102c7d587f31237`
- required hardened Stage-A launcher `scripts/run_v4_ca_residual_document_semantics_hardened.py`: `c1c4a913fc51435835876eeb6e26919964e819a0`
- Stage-B continuity wrapper `scripts/run_v4_ca_residual_document_continuity.py`: `052ac105292848226b443782cc80d57c9a458d88`

The hardened Stage-A launcher is mandatory. The unhardened runner exists only as the underlying frozen implementation and must not be invoked directly.

## Final evidence admission rules

Only two result-changing paths are allowed:

1. `Voluntary Conversion` -> `NON_BLOCKING` from an already-captured official KSEI tender/buyback/cash-repurchase document with exact ticker identity and exact immutable source-date overlap to a layout-bound payment/settlement/cash-purchase date.
2. mechanical event -> `EXACT_TRANSITION` from already-captured official KSEI evidence with exact ticker/family identity, source-date overlap to layout-bound Record/Distribution identity, and an explicit layout-bound regular-market Ex Date or first-new-basis trading date that is an official session.

All ambiguous, missing, multiple-date, conflicting, wrong-ticker, wrong-family, unbound-date, or hash-mismatched cases remain unresolved.

Record Date and Distribution Date are linkage-only fields and can never become the transition date. No price inference, next-session inference, adjusted-price shortcut, source substitution, or provider call is allowed.

## Date-binding hardening

Every date capable of admitting evidence is now layout-bound. Same-line dates are preferred. Exactly one continuation line may be used only when that line does not begin another schedule semantic. This prevents flattened PDF tables from allowing:

- Payment -> later Record Date theft;
- Record -> later Distribution Date theft;
- first-new-basis -> later Record/Distribution Date theft.

Conflicting multiple dates for one semantic fail closed.

## Validation gate

Before any external artifact is read beyond test fixtures, local operator must run:

`python -m pytest tests/test_v4_ca_residual_document_semantics.py tests/test_v4_ca_residual_document_date_binding.py`

Then `py_compile` for both semantics modules and all three runners/launchers, followed by `git diff --check`.

If any validation fails: STOP. Do not patch locally and do not run Stage A.

## Execution boundary

After validation passes:

- exactly one Stage-A offline residual-document audit is authorized;
- if Stage A completes with a valid internally verified manifest, exactly one Stage-B offline continuity replay is authorized;
- no code/config edit is allowed between Stage A and Stage B after Stage-A result exposure;
- STOP after Stage B regardless of continuity verdict.

No R5/R10, target ranks, model, prediction, performance, bootstrap, protected outcome, or fresh-forward access is authorized.

## Coordination boundary

Canonical `origin/main:coordination/TEAM_STATUS.md` was inspected before implementation and no overlapping active residual-document lane existed. The branch-local claim exists, but the canonical shared row has not been safely edited by ChatGPT because the connector only exposes full-file replacement for this large shared ledger.

Therefore the local operator must first refetch latest `main`, confirm no new overlap, and add/update `V4 CA residual document semantics V1` to `ACTIVE` before validation/execution. On completion, set it to `REVIEW` with exact verdict/hashes; on validation/input blocker, set it to `BLOCKED`/`REVIEW` with the exact blocker.
