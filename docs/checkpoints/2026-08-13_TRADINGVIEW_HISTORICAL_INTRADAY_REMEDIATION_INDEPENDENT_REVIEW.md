# TradingView Historical Intraday Remediation V1 — Independent Review

Date: 2026-08-13 Asia/Jakarta
Reviewed branch: `data/tradingview-historical-intraday-remediation-v1`
Reviewed HEAD: `fcfa5084c172c21d21d4e00489808b6bb20f6333`
Reviewer: ChatGPT independent review

## Verdict

`TRADINGVIEW_REMEDIATION_ACCEPTED_BOUNDED_ADMISSION_PILOT_AUTHORIZED`

The remediation result is decision-valid for the narrow proposition that a separately preregistered bounded TradingView admission pilot is justified. It does **not** admit TradingView as a canonical/secondary historical intraday source, authorize bulk acquisition, or establish execution-grade OHLCV.

## Findings accepted

1. The original anonymous `data`-server failure was not sufficient to reject TradingView as a source. Paired `prodata` requests materially improve raw availability from 42/100 to 70/100 and exact target-window presence from 38/100 to 65/100. Among known-listed pairs with preserved official-session evidence, exact-window coverage improves from 35/54 to 47/54.
2. Price fidelity is strong enough to justify a pilot. Non-CA TV60 HLC exact is 97.53% on `data`, 95.85% on `prodata`, and 96.57% in the descriptive combined slice. TV1D HLC/Open is exact to canonical on all-present rows.
3. The prior 9.88% volume-near headline was misleading as a source-quality conclusion because it used an effectively exact tolerance. Raw volume ratios are centered close to 1; in the remediation slice, 344/379 non-CA matched rows are within ±5%, with no broad 0.01/0.1/10/100 multiplicative cluster. No rescaling or repair is authorized.
4. The independent pinned endenwer client confirms that TradingView can return deterministic `series_completed` and roughly 10.2k hourly bars per bounded request, reaching 2020-01-02 through 2026-08-13 on the cross-check subset. Numeric endenwer rows remain correctly quarantined because its resolver hard-codes split adjustment.
5. The Mathieu adapter correctly improves status semantics without inventing entitlement/completion states. Remaining zero-period cases are conservatively `UNCLASSIFIED_NO_DATA` where the pinned client does not expose `series_completed`.
6. No fork is justified at this stage. Thin adapters are sufficient for the next bounded experiment.

## Material limitations

- **2018 remains unresolved/shallow.** `prodata` exact-window presence is only 4/20 in the 2018 probe, and the independent endenwer depth evidence reaches 2020, not 2018. The remediation therefore does not establish 2018–2026 broad historical coverage.
- **TV60 Open semantics remain unresolved.** Open exact is only about 59–62% by server despite strong HLC and exact TV1D Open. This is a material source-admission blocker and must be treated as a session/bar-boundary semantics problem until independently resolved.
- **Mathieu pagination remains operationally imperfect.** Phase-2 includes 20 request-timeouts; its pinned public client still does not expose `series_completed`.
- The remediation preregistration freezes analyses and taxonomy but **does not freeze numerical pass/fail thresholds for the final source decision**. Therefore this run may justify a next pilot but cannot itself promote the source.
- The `combined` daily reconciliation slice contains overlapping `data` and `prodata` observations and must not be interpreted as 379 independent provider-day observations. This does not overturn the result because the per-server HLC and volume diagnostics are similar.
- The three-way reconciler uses ±5% as a descriptive tolerance for all fields. Exact HLC/Open metrics remain the authoritative price-fidelity evidence; the low `THREE_WAY_DISAGREEMENT` count is not an exact-price pass criterion.

## Authorized next boundary

A new, separately frozen **bounded admission pilot** may be designed. Its primary raw-price candidate should be Mathieu `prodata` with `adjustment=none`; endenwer remains an independent transport/depth corroborator unless its adjustment semantics are separately made raw and revalidated.

The pilot must freeze before network access: exact sample, listing-aware denominators, official-session handling, provider/error gates, target historical eras, numeric HLC/Open/volume gates, corporate-action policy, duplicate/off-session rules, pagination/completion rules, and exact final verdict logic. It must explicitly test the TV60 Open/session-boundary issue and must report 2018 separately rather than silently extrapolating 2020+ depth backward.

No bulk backfill, canonical panel integration, modelling, Path Risk restart, O2/protected-outcome access, authenticated experiment, or execution-grade claim is authorized by this review.

## Validation reviewed

- Focused tests: 7 passed.
- Python and adapter syntax checks: passed.
- Full repository-local pytest: 46 passed, 1 pre-existing storage-fixture failure unrelated to this lane.
- Artifact manifest: 303/303 entries reported verified, 0 missing, 0 mismatch; manifest SHA `aa57118d2def02e87fd6b9664203fcc0caa8228df01e0d14205782952d8cba24`.
- Canonical panel SHA before/after unchanged: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.
