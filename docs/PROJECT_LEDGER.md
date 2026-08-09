# IDX Trade — Project Ledger

> **Canonical continuity document.** Read this before any material DATA,
> VALIDATION, or MODEL task. This file is the durable causal history of the
> project: what failed, why it failed, what changed, what was proven, and what is
> still blocked. Older handoffs are evidence snapshots; when chronology differs,
> the newer explicitly validated decision in this ledger wins.

---

## 1. Objective and research contract

Build a reusable point-in-time-safe IDX daily/EOD market foundation for later
support/resistance, swing setup ranking, entry/invalidation/target research,
risk/reward, calibrated `P(TP before SL)`, expected realized R, Opportunity/Setup
Score, Entry Quality Score, and separate Estimate Reliability.

The intended system is decision support, not a BUY/SELL oracle. Fractional Kelly
and Monte Carlo are downstream only after probability calibration is defensible.

Model research remains blocked until the market-data foundation is certified,
materialized as a model-safe dataset, and frozen with reproducibility hashes.

Validation principles for future model work:

- chronological walk-forward OOS;
- purge/embargo where labels overlap;
- no random train/test split;
- calibration/threshold sets separated where necessary;
- final locked holdout;
- forward shadow/paper evaluation only after model freeze;
- probability quality evaluated separately from ranking/score quality;
- Opportunity Score is not a probability;
- Estimate Reliability is a separate concept;
- retain stress regimes where defensible history permits.

---

## 2. Repository and current status

- repository: `samindriano/idx-trade`
- working branch: `data/idx-data-002c`
- review PR: PR #2, draft, base `data/idx-data-002b`
- current phase: **full-market certification / bounded historical feasibility review**
- modelling: **not started**
- `IDX-VAL-002`: **not started**
- merge to `main`: **not approved**

### 2.1 Adversarial certification

Window: `2026-06-02 -> 2026-07-31`, 43 official IDX sessions.

Result:

- 35/35 adversarial cases PASS;
- UNKNOWN sessions = 0;
- missing ACTIVE-session prices = 0;
- quarantined non-ACTIVE provider bars = 262.

The 35 names are a deliberately difficult QA catalog, not the model universe.
They cover normal/liquid, IPO, suspend/resume, long suspension, delisted,
illiquid/data-quality, and market-scope edge cases.

### 2.2 First full-market 43-session certification

Runtime checkpoint pushed by Codex at review commit `9658378`:

- pytest: 123 passed, 0 failed;
- officially discovered PIT securities before scope resolution: 964;
- gate: 962 passed / 2 failed;
- evidence-only identities: CNTB, CNTX;
- unresolved at that runtime: CNTB, CNTX;
- Yahoo backfill: 848 UPDATED, 0 NO_PROVIDER_ROWS, 0 DOWNLOAD_ERROR,
  0 REVISION_CONFLICT;
- price-required tickers: 872;
- auto price-semantics verified: 881;
- UNKNOWN sessions: 0;
- missing ACTIVE prices: 0;
- quarantined non-ACTIVE provider bars: 1,359;
- only blocker: `SECURITY_IDENTITY_UNRESOLVED: 2`.

The model-safe panel and certified snapshot manifest were correctly not created
because the full-market gate had not yet passed.

### 2.3 CNTB / CNTX resolution decision

Fresh official KSEI research resolved the apparent two-name blocker:

**CNTB**

- Century Textile Industry Tbk Seri B;
- KSEI type: `Saham Biasa` (common share);
- Stock Exchange: IDX;
- KSEI registry status: Active;
- listing date: `22 Desember 2000` = `2000-12-22`.

Decision: **CNTB is in scope for the common-stock identity layer.** It must not be
excluded merely because it is illiquid/unusual. Liquidity eligibility is a later
model-universe decision, not an identity decision.

The earlier KSEI parser failed because the listing date can be returned with an
Indonesian month name. The parser now handles Indonesian/English month names.

**CNTX**

- Century Textile Industry Tbk Seri A;
- KSEI type: `Saham Preference`;
- Stock Exchange: IDX;
- KSEI registry status: Active;
- listing date: `1989-06-16`.

Decision: **CNTX is explicitly out of scope for this common-stock research
universe.** It must be excluded by authoritative security-type evidence, not by
a ticker hardcode and not by pretending its identity is missing.

Permanent scope rule:

- official evidence-discovered common share -> resolve identity and keep in the
  certification universe;
- official evidence-discovered non-common/preference share -> retain evidence and
  record `NON_COMMON_SHARE` scope exclusion;
- unclassified/missing identity -> hard fail `SECURITY_IDENTITY_UNRESOLVED`;
- an exclusion that conflicts with an overlapping security-master common-share
  identity -> hard error.

Code added after the `9658378` runtime checkpoint:

- generic KSEI security identity/type parser;
- Indonesian date parser;
- reusable missing-security scope reconciliation;
- authoritative non-common scope exclusions in full-universe discovery;
- full-universe summary now records discovered-before-scope and excluded names;
- regression tests for CNTB-style localized dates, CNTX-style preference shares,
  scope exclusion, and exclusion/master conflicts.

Latest CI for this scope fix: success.

---

## 3. Core ontology — never collapse these concepts

### 3.1 Existence

- `NOT_LISTED`
- `LISTED`
- `DELISTED`

Existence comes from point-in-time listing intervals, never from Yahoo presence
and never from today's survivor list.

A known security can legitimately have zero listed sessions in an evaluated
window if its complete listing interval lies outside the window. That is resolved
non-applicability. A ticker absent from the identity layer is not the same thing.

### 3.2 Security type / research scope

The initial research universe is IDX **common shares**.

Security type is separate from listing existence and tradability. Official
execution evidence may contain preference/non-common securities. Those rows are
preserved as evidence but must not silently enter the common-stock certification
or model universe.

No arbitrary/manual ticker exclusions are allowed. Out-of-scope classification
requires authoritative type evidence.

### 3.3 Regular-Market session state

Relevant states:

- `ACTIVE`
- `NO_TRADE`
- `SUSPENDED`
- `FCA_WATCHLIST`
- `UNKNOWN`

`UNKNOWN` is fail-closed and must never be silently converted to another state.

### 3.4 Provider availability

Provider row presence/absence/revision is a separate layer from exchange state.

- missing Yahoo row != suspension;
- Yahoo row present != ACTIVE exchange session;
- provider revision/conflict must be explicit.

---

## 4. Source authority hierarchy

### 4.1 Exchange sessions

Authoritative: official IDX.

- primary: IDX Digital Statistics daily/session evidence;
- official fallback: IDX Daily Statistics publication listing when necessary.

Never derive exchange sessions from Yahoo/JCI dates.

### 4.2 Identity and listing intervals

Primary:

- IDX current stock listing reference;
- IDX official delisting history.

Supplemental identity/type evidence:

- KSEI Registered Securities.

KSEI rules:

- registry `Status = Active` proves active KSEI registration, not current exchange
  tradability;
- KSEI must not override official IDX delisting boundaries;
- KSEI may supply missing listing date and security type;
- security type evidence is used to enforce the common-stock scope contract.

### 4.3 Direct Regular-Market execution truth

Authoritative: official IDX Stock Summary.

Correct semantics:

- `Volume > 0` AND `Frequency > 0` -> `ACTIVE` exact-session evidence;
- `Volume == 0` AND `Frequency == 0` -> `NO_TRADE` exact-session evidence;
- missing, negative, or internally inconsistent regular metrics -> unresolved;
- row absence -> unresolved.

`Volume/Frequency` in the schema used are already the relevant regular/order-book
metrics. `NonRegularVolume/NonRegularFrequency` are separate fields and must not
be subtracted.

### 4.4 Legal suspension/resumption explanation

Official IDX suspension/resumption announcements/snapshots remain valuable for
legal reason and market-scope explanation. Direct per-session execution evidence
can satisfy the model's session truth without manufacturing an ACTIVE complement
from an incomplete announcement archive.

### 4.5 Daily prices

Primary free provider: Yahoo/yfinance with `auto_adjust=False`.

Yahoo supplies price evidence; it does not define tradability or universe
membership.

### 4.6 Corporate actions

Authoritative technical-action source: official IDX issued/corporate-action
history, initially focused on:

- Stock Split;
- Reverse Stock.

Dividends are informational/nonblocking for the initial technical-price gate.

---

## 5. Raw-price and model-safe-price contract

Raw provider OHLCV is retained for auditability. Vendor adjusted close must never
overwrite raw execution OHLC.

The model-safe research view contains only provider rows whose point-in-time
official state is `ACTIVE` and whose security is in common-stock scope.

If Yahoo returns a row on NO_TRADE, SUSPENDED, FCA_WATCHLIST, DELISTED, or other
non-ACTIVE state:

- retain the raw row;
- count/quarantine it;
- never let it override IDX truth;
- never let it enter feature, liquidity, label, support/resistance, backtest, or
  model calculations.

Missing price on an expected ACTIVE session remains a hard failure.

---

## 6. Chronological failure -> diagnosis -> fix ledger

Failures are intentionally retained because they are reusable engineering
knowledge.

### 6.1 Legacy repository was not a safe foundation

Old `market-movement-analyzer` was an anomaly-direction model rather than the new
S/R + RR decision-support system.

Reusable concepts: chronological split discipline, purge/embargo, causal rolling
features, calibration concepts, immutable manifests, downloader/cache/retry
patterns, listing/delisting retrieval.

Rejected flaws included suspension/missing conflation, survivorship bias,
adjusted-price execution semantics, row-count coverage false positives,
overlapping-trade portfolio issues, unresolved outcomes omitted from mature
metrics, overloaded confidence semantics, and holdout reuse risk.

Decision: new repo, selective conceptual migration only.

### 6.2 DATA-002: healthy engineering, blocked data gate

Findings included incomplete July calendar, limited Yahoo coverage in the early
audit, unresolved tradability, and unverified corporate actions. Gate: 0/35.

Lesson: a blocked gate is useful evidence, but blocker classification itself must
be audited before blaming the external source.

### 6.3 DATA-002B: July and corporate-action blockers reduced

Added official Daily Statistics fallback and official split/reverse-split source.
Tradability parser improved. Gate still 0/35.

### 6.4 Global initial ACTIVE ontology bug

Wrong assumption: one market-wide initial ACTIVE state could define the left
boundary for all securities.

Fix: separate global event-source discovery completeness from per-security
point-state anchors. No evidence -> UNKNOWN.

### 6.5 Exact-anchor bug

Authoritative exact-date anchors were incorrectly rejected without a complete
surrounding discovery window.

Correct invariant:

- exact authoritative evidence is valid on its exact date;
- propagation to other dates needs an evidence-complete causal path.

### 6.6 Direct session evidence reframing

Rather than reconstruct every legal event merely to answer whether a security
traded on a model session, use official Stock Summary session evidence directly.

### 6.7 Stock Summary subtraction bug

Symptom: UNKNOWN fell from 1,375 to 70, and all 70 were
`REGULAR_TRADE_METRICS_NEGATIVE_AFTER_SUBTRACTION`.

Diagnosis: code incorrectly subtracted NonRegular metrics from regular metrics.

Fix: use regular Volume/Frequency directly.

Result: UNKNOWN 70 -> 0.

Lesson: prove schema semantics from source meaning, not field-name intuition.

### 6.8 Stale Yahoo July artifact

Once July official sessions were fixed, old Yahoo artifacts no longer covered the
full required window.

Fix: derive provider bounds from official exchange sessions and use Yahoo's
exclusive end-date correctly.

Lesson: provider windows must be derived from authoritative calendars.

### 6.9 Provider contamination bug

Symptom: official non-ACTIVE sessions still had Yahoo rows, blocking the gate.

Fix: official IDX state remains authoritative; provider rows on non-ACTIVE days
are quarantined rather than promoted to execution evidence.

Result: adversarial gate 23/35 -> 33/35.

### 6.10 HDTX/KPAS identity and delisting interpretation

IDX current-list omitted them. KSEI supplied identity/listing-date evidence, but
KSEI registry Active initially risked being overinterpreted.

Official IDX delisting evidence closed both listing intervals at 2025-07-18.

Correct invariant: KSEI supplies identity; IDX delisting controls exchange
`listed_to`.

### 6.11 Zero-listed-session coverage bug

`security_coverage.complete` incorrectly required at least one listed session.

Fix:

- known identity whose listing interval is entirely outside the window can be
  complete with zero price requirements;
- identity absent entirely is a hard `SECURITY_IDENTITY_UNRESOLVED` failure.

Result: adversarial 33/35 -> 35/35.

### 6.12 Full-market survivorship hardening

A full-universe candidate set based only on security-master/current-list entries
could omit difficult names. Candidate discovery was extended to include official
tradability point/interval evidence.

Evidence-only identity remains fail-closed until reconciled.

### 6.13 Full-market 962/964 checkpoint

The 43-session architecture scaled from the 35-name stress catalog to almost the
entire officially discovered market without any UNKNOWN sessions or missing
ACTIVE prices. Only CNTB/CNTX identity classification remained.

This was evidence that the data semantics scaled; it was not permission to simply
drop the final two names.

### 6.14 Security-type scope bug / CNTB-CNTX resolution

Fresh official KSEI evidence showed the two unresolved symbols represented two
different cases:

- CNTB: common share -> must be retained; parser needed localized-date support;
- CNTX: preference share -> outside the common-stock scope.

Fix:

- generic KSEI identity/type parser;
- bilingual date handling;
- authoritative security-scope exclusion contract;
- no ticker-specific hardcode;
- scope exclusion/master conflict is a hard error.

Permanent lesson: **identity resolution and research-universe security type are
separate dimensions. Do not solve a non-common security by fabricating a common
identity, and do not solve an illiquid common security by excluding it.**

---

## 7. Post-adversarial scale hardening already implemented

### 7.1 Full-universe DATA GATE

The same hard per-security gate applies to the complete officially discoverable
PIT common-stock universe. No liquidity/model filter is used during data
certification.

Candidate discovery sources:

- listing-interval overlap;
- official tradability anchors;
- official tradability intervals.

Explicit authoritative non-common scope evidence may remove a security from the
common-stock gate while preserving it in raw evidence/audit artifacts.

### 7.2 Full-universe artifacts

Outputs include:

- per-ticker gate results;
- session-coverage reports;
- blocker histogram;
- unresolved identities;
- scope exclusions;
- discovered-before-scope count;
- UNKNOWN-session total;
- missing ACTIVE-price total;
- quarantined provider-bar count.

### 7.3 Batched Yahoo backfill

Large downloads are bounded/batched, reuse existing artifacts, keep revision
guards on, and surface batch/download errors explicitly.

### 7.4 Resumable Stock Summary cache

Per-session official parsed snapshots are cached so execution anchors can be
regenerated without repeatedly hitting the network and long-history work can
resume incrementally.

### 7.5 Automatic price-semantics verification

Canonical raw artifacts can prove their structural execution-price contract;
market-wide runs should not rely on hundreds of manually entered booleans.

### 7.6 Model-safe market panel

After full-market PASS, materialize one canonical ACTIVE-only, common-stock panel.
Future features/labels/models should read that panel rather than raw Yahoo files.

### 7.7 Certified snapshot manifest

Before model research, freeze exact artifact hashes, code/source identity, and
environment metadata. Verify the manifest immediately. Later drift requires a
new version and re-certification.

### 7.8 Historical certification ladder

Do not jump directly from 43 sessions to five years.

Planned trailing horizons:

- 43 sessions;
- 126 sessions (~6 months);
- 252 sessions (~1 year);
- 504 sessions (~2 years);
- 756 sessions (~3 years);
- 1260 sessions (~5 years).

The longest defensible PASS window should be discovered mechanically. The first
failed horizon should identify the actual historical evidence/provider boundary.

---

## 8. Current phase transition rules

### Full-universe 43-session certification

Before declaring PASS, require:

- all evidence-discovered securities either have defensible common-share identity
  or authoritative non-common scope classification;
- official session calendar complete;
- zero UNKNOWN required listed sessions;
- zero missing ACTIVE-session price rows;
- non-ACTIVE provider contamination quarantined;
- split/reverse-split technical history verified;
- raw-price semantics verified;
- no unresolved provider revision/download failures;
- reproducibility artifacts available.

### Freeze

Only after full-universe PASS:

1. materialize common-stock ACTIVE-only market panel;
2. freeze required certification artifacts;
3. create certified snapshot manifest;
4. verify manifest hashes;
5. record exact code/data version.

### Historical expansion

Then extend backwards through the ladder. Prefer a shorter clean/PIT dataset over
a longer guessed dataset.

### Model research

Only after a sufficiently long certified dataset exists:

`certified market layer -> features -> labels -> model -> walk-forward validation`

The identity/session/tradability/provider contracts should not be redesigned per
model unless a genuine new data bug is discovered.

---

## 9. Do-not-repeat invariants

1. Do not infer suspension from missing Yahoo rows.
2. Do not infer ACTIVE from Yahoo row presence.
3. Do not infer ACTIVE merely from LISTED existence.
4. Do not use a global market-wide initial ACTIVE state.
5. Do not propagate exact anchors outside an uncertified causal evidence path.
6. Exact authoritative point evidence is valid on the exact date.
7. Do not subtract NonRegular metrics from Stock Summary regular metrics.
8. Do not let provider contamination override official IDX session truth.
9. Do not use current survivors to define historical universe membership.
10. Do not assume IDX current-list endpoint is exhaustive for difficult names.
11. Do not interpret KSEI registry Active as current IDX listing/tradability.
12. Do not fail a known security solely because zero sessions are applicable.
13. Do not treat absent identity as resolved zero-applicability.
14. Do not silently overwrite Yahoo provider revisions.
15. Do not use vendor adjusted close as raw execution OHLC.
16. Do not scale to years before semantics pass a bounded adversarial window.
17. Do not tune a model to compensate for a data-gate failure.
18. Do not merge the certification branch merely because unit tests pass.
19. Do not exclude an illiquid common share to make the gate green.
20. Do not include a preference/non-common share merely because Stock Summary
    emitted official session evidence for it.
21. Do not hardcode ticker exclusions when authoritative security-type evidence
    can express the scope rule generically.

---

## 10. Important code surfaces

- `src/idx_trade/security_master.py`
- `src/idx_trade/coverage.py`
- `src/idx_trade/data_gate.py`
- `src/idx_trade/adversarial.py`
- `src/idx_trade/full_universe.py`
- `src/idx_trade/data.py`
- `src/idx_trade/universe.py`
- `src/idx_trade/price_backfill.py`
- `src/idx_trade/execution_evidence.py`
- `src/idx_trade/execution_backfill.py`
- `src/idx_trade/providers/idx.py`
- `src/idx_trade/providers/idx_stock_summary.py`
- `src/idx_trade/providers/ksei.py`
- `src/idx_trade/provenance.py`
- `src/idx_trade/storage.py`
- `docs/DATA_GATE_RUNBOOK.md`
- `config/adversarial_cases.csv`

Historical task handoffs under `coordination/handoffs/` are evidence snapshots,
not the current project truth when they conflict with this ledger.

---

## 11. Immediate next runtime action

Do not redownload the full 43-session market unnecessarily.

1. Update local `data/idx-data-002c` to the latest scope-fix head.
2. Run full pytest.
3. Reuse the existing 43-session full-market evidence directory/artifacts.
4. Reconcile CNTB and CNTX through the new generic KSEI security-scope path.
5. Require CNTB to become common-share security-master identity with listing date
   `2000-12-22`.
6. Require CNTX to become an authoritative `NON_COMMON_SHARE` exclusion with
   type `Saham Preference`.
7. Rebuild the canonical security master, preserving any authoritative IDX
   delisting boundaries if present.
8. Rerun full-universe discovery and DATA GATE with the scope-exclusion frame.
9. Expect discovered-before-scope to still explain CNTX rather than making it
   disappear silently.
10. If and only if the full common-stock gate passes, materialize the model-safe
    panel, create the certified snapshot manifest, and verify its hashes.
11. Only after that begin the 126-session historical expansion checkpoint.

No modelling or `IDX-VAL-002` yet.

---

## 12. Research workflow learned from this phase

Preferred pattern for uncertain data/ML foundations:

`small adversarial window`
-> `observe exact failure`
-> `classify conceptual/provider/artifact/scope bug`
-> `fix one assumption`
-> `regression test`
-> `rerun`
-> `only then scale universe/time horizon`

Preserve falsifiability: every step should be small enough that a failure teaches
which assumption broke.

---

## 13. Ledger update protocol

Whenever a material checkpoint occurs, record:

- date/window/task;
- branch + commit/head;
- test result;
- gate result;
- observed symptom;
- root-cause diagnosis;
- code/data fix;
- validation evidence;
- permanent lesson/invariant;
- exact remaining blocker;
- next smallest safe action.

Do not erase failed approaches after they are fixed. Failure -> diagnosis -> fix
is part of the project's reusable knowledge.

---

## 14. DATA-003 first historical expansion checkpoint

Date: 2026-08-08. Source checkpoint: `data/idx-data-002c` at
`949f98c3662e8a558d336996f64fd837417a870e`.

The certified 43-session market window remains unchanged:

- window: `2026-06-02` through `2026-07-31`;
- model-safe panel SHA-256:
  `ac923c22dfc3d85b1769419bc00d02136e4f9a96d7999ba466bc27a0579624b7`;
- certified manifest SHA-256:
  `6c639bf009553db64e1b80b5d570bd83436af57a6c9b9d2ae26d71521b255ffa`.

The first bounded historical expansion used a new evidence workspace and
certified the trailing 126 official IDX sessions, `2026-01-15` through
`2026-07-31`, while preserving the 43-session artifacts above. The bounded
official calendar replay returned 135 available sessions from `2026-01-02`
through `2026-07-31`; the target is the exact last 126 sessions. January--June
used the official IDX Digital Statistics daily-trading table and July used the
official IDX Daily Statistics publication listing. Seven months parsed with no
errors; one month used the official fallback source. No weekday estimation or
Yahoo/JCI session substitution was used.

Official Stock Summary execution evidence completed all 126 target sessions:
`126/126` complete, `0` failed, `0` unresolved metric rows, `0` cached and
`126` fetched sessions. It produced `107,424` ACTIVE anchors and `13,335`
NO_TRADE anchors.

PIT universe reconstruction found `964` tickers before scope. CNTX remained an
authoritative `NON_COMMON_SHARE` exclusion (`Saham Preference`); CNTB remained
an in-scope common share with `listed_from = 2000-12-22`. Required common-stock
scope was `963` tickers, with no new historical identities and no unresolved
identities. Curated intervals were loaded and merged; the official CNTB
suspension beginning `2024-08-07` was preserved, including the applicable
2026-07-30 and 2026-07-31 snapshots.

For the 83 sessions added before the certified baseline, the Yahoo backfill
updated `874` ticker artifacts with `0` provider-row gaps, `0` download
errors, and `0` revision conflicts. The official split/reverse-split query
covered the exact 126-session window; all 963 required tickers were
authoritatively verified, including the no-event case.

The history certification ladder passed both horizons:

| horizon | required | passed | failed | UNKNOWN | missing ACTIVE prices | quarantined provider bars | price-required | semantics verified |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 43 sessions | 963 | 963 | 0 | 0 | 0 | 1,359 | 872 | 889 |
| 126 sessions | 963 | 963 | 0 | 0 | 0 | 2,672 | 880 | 889 |

Both full-universe gates had an empty blocker histogram. The 126-session
ACTIVE-only model-safe panel contains `107,424` rows across `880` tickers and
has SHA-256
`401d2bdb65beaf9442f1a54212372e2adc5d1b2c006fc1e759738f6deea8a19a`.
Its certified manifest contains 14 verified artifacts, is valid, and has
SHA-256
`650ab19e5a77085b7987ffaaa0ed7cbee0eb8c478a72c0c1166767e9eec68f5b`.

Historical calendar diagnosis: the default publication-listing path failed
closed for some early months because those listings were empty or incomplete.
The bounded replay recovered the missing months through the official Digital
Statistics source-result and retained the failed attempts as evidence. This
is a source-replay issue, not permission to estimate sessions or substitute a
vendor calendar.

No modelling or `IDX-VAL-002` was started. The next safe checkpoint is a
252-session expansion, but it must not start until separately requested.

---

## 15. DATA-004 504-session historical expansion — FAIL / STOP

Date: 2026-08-08. Runtime source checkpoint: `data/idx-data-002c` at
`ed13ee0812e8db21d580e922f4e346873aa7b3cd`.

The certified 43- and 126-session artifacts were preserved unchanged. A new
evidence workspace was created for the trailing 504-session attempt. The
bounded official calendar contained 516 sessions from `2024-06-03` through
`2026-07-31`; the exact last 504 sessions were selected mechanically as
`2024-06-21` through `2026-07-31`. All 26 requested months parsed with zero
errors. The early-month recovery used only official IDX Digital Statistics
dates where the Daily Statistics listing was empty; no weekday estimate,
Yahoo calendar, or JCI substitute was used.

Full pytest passed: 134 tests, exit 0, with two non-blocking warnings.

Official Stock Summary evidence completed all 504 target sessions: 126 cache
hits, 378 new fetches, 504/504 complete, 425,340 ACTIVE anchors, 54,131
NO_TRADE anchors, and zero unresolved metric rows.

PIT discovery found 977 securities before scope. CNTX remained the existing
authoritative `NON_COMMON_SHARE / Saham Preference` exclusion, leaving 976
common-stock candidates. FREN was newly discovered from official historical
point evidence and absent from the reused security master. The generic KSEI
reconciliation was attempted; the live KSEI page returned an undefined
security/type/listing record, so FREN remains unresolved. No ticker-specific
identity hardcode was added.

The additional 378-session Yahoo extension requested 881 common candidates:
878 were updated, with zero `DOWNLOAD_ERROR`, zero `REVISION_CONFLICT`, and
three `NO_PROVIDER_ROWS`: FREN, MASA, and MFIN. Raw histories and revision
guards were preserved; the insufficient first price attempt was retained as a
separate failure artifact.

The 126-session regression horizon reproduced PASS:

- 963/963 tickers passed;
- UNKNOWN sessions = 0;
- missing ACTIVE prices = 0;
- quarantined non-ACTIVE provider bars = 2,672;
- blocker histogram = `{}`.

The 504-session horizon is **FAIL**:

- window: `2024-06-21` through `2026-07-31`;
- discovered before scope: 977;
- scope exclusion: CNTX;
- required common stocks: 976;
- passed/failed: 973/3;
- unresolved identities: FREN;
- UNKNOWN sessions: 2;
- missing ACTIVE prices: 271;
- quarantined non-ACTIVE provider bars: 22,400;
- blocker histogram: `PRICE_SEMANTICS_UNVERIFIED: 2`,
  `SECURITY_IDENTITY_UNRESOLVED: 1`, `SESSION_COVERAGE_INCOMPLETE: 2`.

Exact failed tickers:

- FREN — `SECURITY_IDENTITY_UNRESOLVED`; KSEI fallback did not provide a
  usable identity/type/listing record.
- MASA — `SESSION_COVERAGE_INCOMPLETE` and `PRICE_SEMANTICS_UNVERIFIED`;
  22 expected ACTIVE prices are missing and Yahoo returned no provider rows.
- MFIN — `SESSION_COVERAGE_INCOMPLETE` and `PRICE_SEMANTICS_UNVERIFIED`;
  249 expected ACTIVE prices are missing and Yahoo returned no provider rows.

Because 504 failed after the price extension and exact blockers were
localized, the ladder stopped. No 252 diagnostic, 1260 expansion, model-safe
504 panel, or 504 manifest was created. The next action is to resolve these
three historical evidence/provider blockers without weakening the DATA GATE;
only then may a new 504 certification be attempted.

---

## 16. DATA-004 repair attempt - STOP on official OHLC blocker

Date: 2026-08-09. Runtime source checkpoint: `data/idx-data-002c` at
`5e6f6bd38a5af3ee11bca93a15f50fadf9515eb2`.

The certified 43- and 126-session artifacts were not modified. Full pytest
passed: 141 tests, exit 0, with three non-blocking `FutureWarning` messages.

The normal IDX/KSEI reconciliation for FREN had already failed with an
undefined KSEI security/type/listing response. The curated registry was loaded
through `load_curated_security_identities(...)` and applied only afterwards via
`supplement_historical_security_identities(...)`. The rebuilt PIT master added
FREN as a common share with `listed_from=2006-11-29` and
`listed_to=2025-04-16`; existence checks returned LISTED on 2025-04-16 and
DELISTED on 2025-04-17. Identity evidence did not create tradability state.

From the preserved failed 504 gate and official Stock Summary anchors, the
pre-repair missing ACTIVE price sets were exactly MASA 22 sessions and MFIN
249 sessions, total 271. The exact set is preserved at the runtime artifact
`D:\Documents\Project\idx-trade-data-gate-20260808v\repair_504\prices\missing_active_sessions_504_pre_repair.csv`.

The targeted official IDX fallback was started for MASA only. All 22 requested
rows were returned as `UNRESOLVED_PRICE / OFFICIAL_OHLC_MISSING_OR_NONPOSITIVE`:
the official rows had positive Regular-Market Volume/Frequency and valid
High/Low/Close, but neither positive `OpenPrice` nor positive `FirstTrade`.
Therefore zero `PRICE_PARSED` rows, zero `FIRSTTRADE_FALLBACK` rows, zero
filled rows, and 22 remaining missing ACTIVE rows were recorded. MFIN was not
requested after this hard stop. No synthetic or forward-filled price was
created, and no existing provider row was overwritten.

The new FREN identity also correctly exposes 196 ACTIVE sessions in the 504
window, but no raw price artifact exists for FREN. Automatic raw-price
semantics are therefore false for FREN, MASA, and MFIN. This is preserved as a
diagnostic and not bypassed.

The 126/504 certification ladder was not rerun after the MASA hard stop. No
504 panel or manifest was created. No 252/1260 expansion, modelling,
`IDX-VAL-002`, or merge to main was started.

The next safe action is a separately reviewed official source path that can
provide a defensible opening execution for the exact MASA/MFIN dates (and the
newly exposed FREN ACTIVE history), or an explicit evidence-backed decision
that the 504 horizon cannot be certified. The price gate must not be weakened.

---

## 17. DATA-004 independent price repair - secondary source unavailable

Date: 2026-08-09. Runtime source checkpoint: `data/idx-data-002c` at the
pre-repair code checkpoint `5e6f6bd38a5af3ee11bca93a15f50fadf9515eb2`.

The three remaining historical price cases were processed independently. The
certified 43- and 126-session artifacts and the earlier failed repair
diagnostics were preserved. Full pytest after the generic secondary-open
witness implementation passed: 149 tests, exit 0, with three existing
non-blocking pandas `FutureWarning` messages.

The exact regenerated missing ACTIVE counts were:

| ticker | requested ACTIVE sessions | official PRICE_PARSED | FIRSTTRADE_FALLBACK | unresolved official rows | rows filled | remaining |
|---|---:|---:|---:|---:|---:|---:|
| FREN | 196 | 0 | 0 | 196 | 0 | 196 |
| MASA | 22 | 0 | 0 | 22 | 0 | 22 |
| MFIN | 249 | 77 | 0 | 172 | 77 | 172 |

All official unresolved rows used the explicit diagnostic
`OFFICIAL_OHLC_MISSING_OR_NONPOSITIVE`. MFIN's 77 accepted rows used positive
`OpenPrice`; no accepted row required FirstTrade fallback. Existing primary
rows were never overwritten. The exact date-level sets and all official
provenance remain outside Git in
`D:\Documents\Project\idx-trade-data-gate-20260808v\repair_504_complete\`.

A generic secondary-open witness implementation and regression tests were
added. It accepts only an exact ticker/date match where the secondary Open is
positive and within the official IDX range, and secondary High/Low/Close match
official IDX High/Low/Close exactly. The resulting row keeps official IDX
High/Low/Close/Volume and retains both source references under the marker
`IDX_STOCK_SUMMARY_WITH_SECONDARY_OPEN_WITNESS`. Existing primary history is
preserved date-by-date.

The normal public historical-page request was attempted for FREN, MASA, and
MFIN using the public Investing.com pages. All three returned HTTP 403. No
CAPTCHA, anti-bot, authentication, or rate-limit protection was bypassed, so
the secondary source is recorded as unavailable. No secondary Open was used.

Automatic raw-price semantics after the official fallback were FREN=false,
MASA=false, MFIN=true. FREN/MASA still have no stored rows; MFIN has 77 stored
rows but 172 ACTIVE dates remain missing.

Because the explicitly authorized secondary source path was unavailable and
the DATA GATE still has missing ACTIVE prices, the 126/504 ladder was not
run. No new 504 panel or manifest was created. The 504 decision remains
**NO-GO / STOP**; 252 and 1260 were not started. The smallest safe next action
is to obtain a normally accessible public secondary OHLC source or other
authoritative opening-price evidence without weakening the gate.

---

## 18. DATA-004 official IDXData3 Stock_First_Trx audit - target files unavailable

Date: 2026-08-09. Audit source head: `data/idx-data-002c` at
`ffca7c51312ef96ce786913541c36a55edd4588c`.

Official specification: `https://www.idxdata3.co.id/IDX%20Reporting%20PSPP/Revitalisasi/Specification%20Document-Report%20Revitalization_PUBLIK%20v1.0.pdf`.
Official directory: `https://idxdata3.co.id/Download_Data/Daily/Stock_First_Trx/`.

The exact remaining ACTIVE-price requirement was regenerated from the preserved
post-official-fallback artifact. It contains 390 rows over 233 unique dates:
FREN 196, MASA 22, and MFIN 172, covering `2024-06-21` through `2025-09-19`.

The official IDXData3 report specification documents the
`SO[YYMMDD].zip` opening-price family and maps fields including `open`,
`firsttrade`, `high`, `low`, `close`, `daysvolume`, and `numtrades`. Normal
public retrieval was attempted for all 233 target dates. The `www` hostname
had a normal TLS hostname-verification failure, so the official canonical
hostname was tested without disabling TLS verification or bypassing controls.
The first canonical pass returned 12 HTTP 404 responses and 221 HTTP 503
responses; one controlled retry returned HTTP 404 for all 221. Final target
file status: 233 `FILE_NOT_FOUND`, zero `FILE_AVAILABLE`.

The readable official directory advertised 133 files from `SO200203.zip`
through `SO200819.zip`, i.e. an observed retention range of 2020-02-03 through
2020-08-19. None of the target dates was advertised. The available sample
`SO200819.zip` is a legacy DBF with fields `STK_CDAT`, `STK_CODE`, `STK_NAME`,
and `STK_FIRST`; it is outside the target window and cannot supply the requested
modern H/L/C/volume/frequency reconciliation.

Per ticker, target SO files available = 0, ticker rows found = 0, official
opens verified = 0, and unresolved rows = FREN 196, MASA 22, MFIN 172. All 390
rows are `SO_FILE_MISSING`. No production parser/provider was added because
coverage was zero/negligible. No 504 ladder rerun, 252 diagnostic, 1260 run,
model, `IDX-VAL-002`, panel, manifest, or merge was started. The audit runtime
artifacts remain external and are not part of Git.

The 504 decision remains **NO-GO / STOP**. The next safe action is another
normally accessible authoritative opening-price source or an explicit,
evidence-backed decision that this 504 boundary is not defensible. The price
gate must not be weakened.

---

## 19. DATA-005 1260-session research-feasibility evaluation - NO-GO

Date: 2026-08-09 (Asia/Jakarta). Runtime workspace:
`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809`.
The code branch was `data/idx-data-002c`; the 1260 preparation branch was
reconciled into it before execution. The certified 43- and 126-session
artifacts were not modified.

This run evaluated an exact trailing 1260-session official IDX window ending
`2026-07-31`, not an estimated calendar interval:

- exact window: `2021-04-29 -> 2026-07-31`, 1260 sessions;
- official session sources: IDX Daily Statistics publication listing and IDX
  Digital Statistics daily trading table;
- session summary SHA-256:
  `5dae391a1b4068a71b0f0dd40edda207356a917f74dc860c50e4080fa7bd268f`;
- the certified 504 target `2024-06-21 -> 2026-07-31` is the exact trailing
  suffix, adding 756 older sessions.

Full pytest passed: 157 tests, exit 0, with three existing non-blocking pandas
`FutureWarning` messages. Official Stock Summary cache/execution evidence was
complete for all 1260 sessions: 982,398 ACTIVE regular-market anchors,
121,666 NO_TRADE anchors, 1,104,064 merged point-evidence rows, and zero
unresolved metric rows. `Value` is now retained as `regular_value` so the
materiality calculation uses the official regular-market value field; the
parser regression assertion is covered by the full suite.

The PIT identity/security-scope result was:

- 980 tickers discovered before scope;
- CNTX excluded by the preserved authoritative KSEI NON_COMMON_SHARE record
  (`Saham Preference`);
- 979 required common-stock tickers;
- no unresolved required common-stock identity;
- FINN was reconciled from the official IDX delisting source, and FREN's
  repaired PIT interval was preserved (`2006-11-29 -> 2025-04-16`).

The complete official corporate-action query over the target window returned
55 `stockSplit` rows for 52 tickers and zero `reverseStock` rows. A complete
authoritative no-event result is treated as verified; dividend evidence remains
informational and is not used to construct technical OHLC.

The older-segment Yahoo extension requested 897 tickers and produced 878
updated, 19 `NO_PROVIDER_ROWS`, zero `DOWNLOAD_ERROR`, and zero
`REVISION_CONFLICT`. The targeted official Stock Summary OHLC fallback requested
the exact 6,794 missing ACTIVE ticker/date pairs (989 distinct dates):

- 78 `PRICE_PARSED` rows filled, all for WSKT;
- 0 `FIRSTTRADE_FALLBACK` rows;
- 6,716 official rows remained unresolved;
- no existing provider row was overwritten, and no synthetic or forward-filled
  price was created.

The canonical post-fallback `run_full_universe_data_gate(...)` result is saved at
`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\strict_gate_1260_post_fallback\full_universe_gate_summary.json`:

| horizon | exact window | required | passed | failed | UNKNOWN sessions | missing ACTIVE prices | quarantined bars |
|---|---|---:|---:|---:|---:|---:|---:|
| 126 | 2026-01-15 -> 2026-07-31 | 963 | 963 | 0 | 0 | 0 | 2,672 |
| 504 | 2024-06-21 -> 2026-07-31 | 976 | 973 | 3 | 2 | 390 | 22,400 |
| 1260 | 2021-04-29 -> 2026-07-31 | 979 | 917 | 62 | 572 | 6,716 | 57,808 |

The strict 126 regression remains PASS. Strict 504 remains FAIL for FREN,
MASA, and MFIN; the exact remaining historical opening-price gap is 390 rows.
The full 1260 strict blocker histogram is:

- `SESSION_COVERAGE_INCOMPLETE`: 62;
- `PRICE_SEMANTICS_UNVERIFIED`: 15.

The exact strict 1260 failed tickers are:
`ADCP, AGAR, AGRS, AMIN, AYLS, BATA, BAYU, BBHI, BISI, BRMS, BRNA, BSIM,
BTON, BTPN, BUAH, BUKK, CBMF, CLAY, CPRI, DMND, DUCK, EDGE, FINN, FREN,
FUJI, GAMA, GEMA, GOLD, GRPH, HKMU, HOTL, IBST, INAF, INAI, INCI, INPC,
INPP, ISSP, JECC, JIHD, JSKY, JSPT, KETR, KRYA, LCKM, LFLO, LMAS, MAGP,
MASA, MFIN, PGJO, PTSP, PURE, RMBA, ROCK, SAFE, SRIL, TECH, TRST, TURI,
UNSP, WSKT`.

For the separate research-feasibility layer, the 62 failures were registered
generically as `RESEARCH_UNSUPPORTED_SECURITY` only after the approved public
IDX/Yahoo evidence paths were exhausted. The registry contains 47 rows with
price/tradability evidence blockers and 15 additional rows with the same
coverage failure plus `PRICE_SEMANTICS_UNVERIFIED`; the detailed registry is
external at
`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\research_unsupported_registry_1260.csv`.
The resulting research eligibility was 917/979 = 93.667%, below the 98%
ticker threshold. Active-row coverage was 99.316% before generic exclusions
and 100% after exclusions, but known excluded regular-market value was 2.373%
of known value. Excluded names included one top-50 ticker, two top-100 tickers,
and four top-200 tickers. Sector bias could not be computed because the current
security master has no sector field.

Decision: **NO-GO / STOP**. The research track does not meet the minimum ticker
coverage or zero-gap requirements, and the strict 1260 gate fails. No 1260
model-safe panel or manifest was materialized. No 252 diagnostic, modelling,
`IDX-VAL-002`, main merge, paper trading, or live trading was started. The
smallest safe next action is to obtain defensible additional historical
opening/OHLC evidence or explicitly narrow the research contract after a
separate review; the gate must not be weakened silently.
