# V4 CA — ICBP Single-Ticker Final-Gate Remediation Prep

Date: 2026-08-18
Branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`

## Current accepted state

The latest outcome-blind targeted continuity replay remains fail-closed, but the
remaining miss is now localized:

- H5 gate dates: `600 / 600`, minimum `0.9006410256410257`.
- H10 gate dates: `595 / 600`, minimum `0.8974358974358975`.
- Consensus gate dates: `595 / 600`, minimum `0.8974358974358975`.
- Five failing signal dates: `2026-06-29`, `2026-06-30`, `2026-07-02`,
  `2026-07-03`, `2026-07-07`.
- Each failing H10 date is exactly one additional resolved ticker short of the
  frozen 90% threshold.
- The targeted seven-event lane has resolved six events. ADRO remains unresolved
  and is explicitly retained fail-closed after correction of the AAI/AADI PUPS
  spin-off semantics.

The user-supplied blocker attribution shows that ICBP is unresolved for both H5
and H10 on all five residual dates only because its KSEI registered-security
history coverage is not certified. The previously accepted KSEI gap-remediation
result records ICBP among the 12 residual failures, in the HTTP/empty-response
class rather than a parser/semantic identity conflict.

## Why ICBP is the next bounded target

The remediation must not rescue the gate by weakening a corporate-action rule.
ADRO is economically complex and therefore remains untouched. Known exact
mechanical crossings such as BNBR/PADI/RMKO/SINI, ELPI, and RAJA are legitimate
continuity blockers and are also untouched.

ICBP is selected because:

1. it is one of the exact 12 unresolved KSEI coverage tickers in the accepted
   `598 / 610` remediation census;
2. it is present as unresolved on all five residual H10 dates;
3. resolving exactly one such common ticker is mathematically sufficient to
   test whether the frozen gate reaches 600/600 without changing the gate;
4. current public-page availability was used only as a diagnostic target-selection
   signal, not as admissible evidence;
5. actual certification will require a fresh local capture from the same exact
   official KSEI registered-security URL and the unchanged strict parser.

## Frozen micro-remediation contract

Target ticker: **ICBP only**.

Parent KSEI remediation manifest:
`7e86f5e52d7c2ff609ee9dd4be28ff1aefea1e4d5c7d7d9dbffb6abd07185f50`

Parent census assertions:

- 610 tickers total;
- 598 certified;
- exact unresolved set:
  `AMAN, AVIA, AYAM, BCIP, ICBP, PRIM, SKRN, SLIS, SMAR, SNLK, SOCI, SOFA`;
- no existing ICBP history rows.

Provider/parser assertions:

- existing frozen config SHA-256:
  `a749749d799030a74baee0fb0e555f4df45fa86d`;
- exact official KSEI security URL template unchanged;
- `curl_cffi` / `chrome110` transport unchanged;
- fresh session + KSEI home warmup unchanged;
- at most 2 ICBP security attempts;
- no other ticker request;
- no alternate provider;
- no alias/remap;
- no parser relaxation;
- no source substitution.

A successful acquisition must produce exactly:

- 599 certified tickers;
- 11 unresolved tickers, equal to the prior 12 minus ICBP;
- strict parsed ICBP history with official source URL/SHA provenance.

Parsed ICBP event families are **not** assumed harmless by the acquisition
runner. They are passed to the existing frozen event-window classifier during
replay. If the fresh page contains a relevant mechanical/unknown event, normal
fail-closed semantics apply and the expected gate improvement may not occur.

## Continuity replay contract

The second runner is permitted only after successful ICBP acquisition. It:

- performs zero provider calls;
- consumes the same immutable frozen continuity ledger, official calendar,
  prior event evidence, residual-document evidence, and V4 targeted schedule
  evidence;
- changes only the KSEI census root from 598/610 to the verified ICBP overlay;
- retains the exact 90% gate, H5/H10 horizons, selection halo, event semantics,
  cross-source conflict policy, and entry-on-transition rule;
- uses `classify_event_with_targeted_evidence` unchanged;
- does not access targets, ranks, returns, model fits, predictions, performance,
  O2, or protected/fresh-forward outcomes.

Expected-but-not-forced result, if strict ICBP history is non-mechanical over the
relevant study window:

- H5: `600 / 600` gate dates;
- H10: `600 / 600` gate dates;
- consensus: `600 / 600` gate dates;
- `corporate_action_continuity_certified=true`.

The runtime output, not this expectation, determines the verdict.
