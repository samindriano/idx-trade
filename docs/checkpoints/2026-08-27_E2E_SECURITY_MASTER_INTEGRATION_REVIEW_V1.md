# E2E Security Master Live Identity Integration Review V1

Date: 2026-08-27 Asia/Jakarta  
Source audit: `audit/e2e-security-master-live-identity-v1@9bf6bb58c850c42839fe24a2bddd0683c3492529`  
Production base: `6e1bf4a1e47a2abff365b35c19687444cf3f0596`  
Implementation commit: `cb7573422097aef2f34ad41d53ccd95f6231a67a`  

## Scope and decision

This is a fresh integration of the generic Security Master remediation onto the
production implementation pin. The audit branch was not merged wholesale. The
14-commit interval from `6ec8ade98b47ea8099dff0fc32e9b3a644d260a2` through the
production pin was preserved; `src/idx_trade/e2e_cloud_security_master_v1.py`
was unchanged in that interval.

The remediation is integration-review ready after the consumer hardening below.
It does not authorize deployment or a production rerun. A future genuine
scheduled POST_EOD session remains required for operational acceptance.

## Identity versus tradability

`IDX_FROZEN_BASELINE_IDENTITY_CONTINUITY` is written only as the `source` of a
preserved security-master identity row. It carries identity fields and listing
interval fields; it does not set an ACTIVE trading state, create a price row, or
admit an execution order.

The downstream evidence chain is now fail-closed at each relevant boundary:

1. `security_master.existence_state()` uses the legal listing interval only.
2. `security_master.tradability_state()` and `model_eligibility()` require
   independent explicit ACTIVE tradability evidence. Missing interval/window/
   anchor evidence remains UNKNOWN and is ineligible.
3. `coverage.active_price_view()` filters price rows by the independent
   tradability state, so a preserved suspended identity is not a price input.
4. `forward_monitoring.capture_session()` now vetoes a positive same-session
   Stock Summary point when authoritative interval/anchor evidence says
   SUSPENDED, FCA_WATCHLIST, or NO_TRADE. Ambiguous evidence also fails closed.
5. `v4_x1_clean_forward_score._merged_security_master_path()` preserves the
   frozen baseline `listed_from` identity but propagates an explicit current
   `listed_to`, preventing a verified delisting from being resurrected in the
   clean scorer overlay.

Therefore a preserved identity can enter execution/scoring only when the
independent downstream tradability/admission contract authorizes it. A current
positive point row is not allowed to contradict a known non-active state.

## Listing and delisting rules

Authoritative post-freeze delistings are retained with their exact `listed_to`;
the baseline continuity set is computed only for identities legally live at the
observation date. A delisted identity is consequently `DELISTED` after its end
date and is not preserved as live. Incomplete delisting evidence can preserve
identity for continuity, but cannot create ACTIVE state: no explicit
tradability evidence remains UNKNOWN and is rejected by model eligibility, and
known non-active evidence vetoes point-based admission.

Identities absent from the frozen baseline are admitted only when their
authoritative `listed_from` is strictly after the freeze date. Pre-freeze extra
identities, changed listing starts, invalid intervals, malformed/null tickers,
and malformed non-empty `listed_to` values fail closed. This retains the
post-freeze listing-evidence rule and avoids inferring a relisting from price
observations.

## Validation evidence

Focused validation from the exact integration worktree passed:

- Security Master refresh, completeness, malformed-source, delisting, and
  determinism tests: PASS.
- Forward monitoring and clean V4-X1 security-master consumer tests: PASS.
- E2E cloud V2/V3 and PREOPEN_CA checkpoint/consumer/integrated replay suites:
  PASS.
- Full `python -m pytest -q`: PASS at 100% completion with the three existing
  pandas `FutureWarning` diagnostics; no new failure.
- `py_compile` for changed modules: PASS.
- `git diff --check`: PASS.

Adversarial coverage includes preserved suspended identity, positive point versus
explicit suspension, missing tradability evidence, authoritative delisting,
source omission, malformed/null/bogus identity, listing-date conflict,
post-freeze listing admission, malformed interval/end date, and restart
determinism.

No provider call, protected outcome access, model refit/rescore, scheduler
change, production runtime mutation, or manual production rerun was performed.

## Files changed in the implementation commit

- `src/idx_trade/e2e_cloud_security_master_v1.py`
- `src/idx_trade/forward_monitoring.py`
- `src/idx_trade/v4_x1_clean_forward_score.py`
- `tests/test_e2e_cloud_security_master_v1.py`
- `tests/test_forward_monitoring.py`
- `tests/test_v4_x1_clean_forward_score.py`

## Activation boundary

The production workflow still points at the prior reviewed implementation pin
until a separately reviewed activation change updates its
`E2E_CLOUD_IMPLEMENTATION_REF` to the implementation commit above. No workflow
or canonical coordination file is changed in this branch.
