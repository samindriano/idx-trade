# V4 CA Residual Document Semantics V1 — Final Preflight Freeze

Status: `FROZEN_FOR_LOCAL_VALIDATION_AND_ONE_OFFLINE_RUN`

## Scientific/code anchor

The original semantics/date-binding implementation was frozen at `fcb1b92f66c1bc1f6f575e4ab191b60e3812b642`. Before any Stage-A result or external semantic audit was exposed, an additional reproducibility hardening was added: successful Stage-2 document captures may not disappear silently from the prior raw corpus.

The final scientific/preflight code anchor is:

`6cced713d13e9933f1c9243695f8e59464c0b407`

No scientific/code/config changes are authorized after this anchor unless local validation fails before any Stage-A result is exposed.

Pinned Git blobs at the final anchor:

- config `config/v4_ca_residual_document_semantics_v1.json`: `a2860ebe24ebb577c0591550066295656a0d9428`
- base residual semantics `src/idx_trade/v4_ca_residual_document_semantics.py`: `5beadf3c3462919a21c215235f185be37366a606`
- layout-bound hardening `src/idx_trade/v4_ca_residual_document_semantics_hardened.py`: `0ef10eb9ace1272fe2151e61ccd3c443daea5364`
- Stage-A runner `scripts/run_v4_ca_residual_document_semantics.py`: `a7a3e9cb5d23f07ee96ad3365102c7d587f31237`
- required hardened Stage-A launcher `scripts/run_v4_ca_residual_document_semantics_hardened.py`: `c1c4a913fc51435835876eeb6e26919964e819a0`
- Stage-B continuity wrapper `scripts/run_v4_ca_residual_document_continuity.py`: `052ac105292848226b443782cc80d57c9a458d88`
- Stage-2 raw-corpus attestation preflight `scripts/verify_v4_ca_stage2_raw_corpus.py`: `3e52fa007f341d7cd2bf0c215c6f2d503d6ccaea`

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

## Stage-2 corpus attestation

Before semantic parsing, the local operator must attest the immutable Stage-2 corpus. The attestation pins the Stage-2 manifest, request records, and 100-row document parse audit. Every candidate document must be accounted for. A request recorded as successful must still have a raw byte file whose SHA exactly matches both the request record and parse audit. Provider-failed documents may remain failed. Missing successful bytes, contradictory provider status, SHA conflicts, or missing request identity stop execution before Stage A.

This attestation makes no provider call and does not parse any target/model/outcome data.

## Validation gate

Before any external semantic audit is run, local operator must run:

`python -m pytest tests/test_v4_ca_residual_document_semantics.py tests/test_v4_ca_residual_document_date_binding.py`

Then `py_compile` for both semantics modules, the corpus attestation, both Stage-A runners/launchers, and Stage-B wrapper, followed by `git diff --check`.

If any validation fails: STOP. Do not patch locally and do not run corpus attestation/Stage A.

After code validation, run the Stage-2 raw-corpus attestation. If it does not return exactly `V4_CA_STAGE2_RAW_CORPUS_ATTESTED`: STOP. Do not delete, redownload, substitute, or repair external raw bytes.

## Execution boundary

After validation and corpus attestation pass:

- exactly one Stage-A offline residual-document audit is authorized;
- if Stage A completes with a valid internally verified manifest, exactly one Stage-B offline continuity replay is authorized;
- no code/config edit is allowed between Stage A and Stage B after Stage-A result exposure;
- STOP after Stage B regardless of continuity verdict.

No R5/R10, target ranks, model, prediction, performance, bootstrap, protected outcome, or fresh-forward access is authorized.

## Coordination boundary

Canonical `origin/main:coordination/TEAM_STATUS.md` was inspected before implementation and no overlapping active residual-document lane existed. The branch-local claim exists, but the canonical shared row has not been safely edited by ChatGPT because the connector only exposes full-file replacement for this large shared ledger.

Therefore the local operator must first refetch latest `main`, confirm no new overlap, and add/update `V4 CA residual document semantics V1` to `ACTIVE` before validation/execution. On completion, set it to `REVIEW` with exact verdict/hashes; on validation/input blocker, set it to `BLOCKED`/`REVIEW` with the exact blocker.
