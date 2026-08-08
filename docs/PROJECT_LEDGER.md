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
- current phase: **full-market data certification, then historical expansion**
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
