# IDX Trade — Project Ledger

> **Canonical continuity document.**
>
> This file is the durable research/engineering memory for the IDX Trade project.
> It exists so the project can be resumed safely after a chat reset, context-window
> loss, agent handoff, or long pause without reconstructing the causal history from
> scattered commits and stale handoffs.
>
> **Read this before any material DATA, VALIDATION, or MODEL task.**
> Update it whenever a material assumption changes, a new failure class is found,
> a gate result changes, or a phase transition is approved.
>
> Historical handoff files remain useful evidence, but this ledger is the current
> cross-phase narrative and decision record.

---

## 1. Project objective

Build a reusable, point-in-time-safe IDX daily/EOD market research foundation for
later support/resistance, setup ranking, probability, risk/reward, and related
swing-trading research.

The intended product is **decision support**, not a BUY/SELL oracle.

Candidate future outputs include:

- support/resistance structure;
- entry/invalidation/target candidates;
- risk/reward;
- calibrated `P(TP before SL)` or other explicitly defined probabilities;
- expected realized R;
- Opportunity/Setup Score and Entry Quality Score;
- Estimate Reliability distinct from probability;
- later, fractional Kelly / Monte Carlo only after probability calibration is
  demonstrably trustworthy.

The project must not begin model research until the market-data foundation is
certified and frozen.

---

## 2. Current operating status

### Repository

- repository: `samindriano/idx-trade`
- working branch: `data/idx-data-002c`
- review PR: PR #2, draft, base `data/idx-data-002b`
- current phase: **market-data certification / full-universe expansion**
- modelling: **not started**
- `IDX-VAL-002`: **not started**
- merge to `main`: **not approved**

### Latest certified bounded result

The adversarial 43-session gate for:

`2026-06-02 -> 2026-07-31`

has passed:

- adversarial cases: **35/35 PASS**
- UNKNOWN sessions: **0**
- missing ACTIVE-session prices: **0**
- quarantined non-ACTIVE Yahoo/provider bars: **262**
- HDTX/KPAS correctly resolved as known securities with **0 listed sessions**
  and **0 expected ACTIVE sessions** in the 2026 window because authoritative IDX
  delisting evidence closes their listing intervals before the window.

This certifies the architecture against deliberately difficult cases. It does
**not yet certify the complete IDX market universe** and does not imply that the
historical training dataset is long enough.

### Immediate next checkpoint

Run the same 43-session DATA GATE over the **full point-in-time universe** discovered
from:

1. security-master listing intervals overlapping the window; plus
2. official Stock Summary/tradability point evidence; plus
3. official tradability intervals.

Provider symbols must never define the universe.

If full-universe certification passes, materialize an ACTIVE-only model-safe
market panel and freeze a certified snapshot manifest before historical expansion.

---

## 3. Core market-data ontology

Never collapse these concepts:

### 3.1 Existence

- `NOT_LISTED`
- `LISTED`
- `DELISTED`

Existence is determined by point-in-time listing intervals, not by Yahoo row
presence and not by today's survivor list.

### 3.2 Tradability / Regular-Market session state

Relevant states include:

- `ACTIVE`
- `NO_TRADE`
- `SUSPENDED`
- `FCA_WATCHLIST`
- `UNKNOWN`

`UNKNOWN` is a real fail-closed state. It must never be silently converted into
ACTIVE, NO_TRADE, or SUSPENDED.

### 3.3 Provider availability

Provider evidence is conceptually separate from exchange state, e.g.:

- provider row present;
- provider row absent/unresolved;
- provider revision/conflict.

A missing Yahoo row does not prove suspension. A Yahoo row does not prove the
security was ACTIVE on the IDX Regular Market.

---

## 4. Source authority hierarchy

### 4.1 Exchange sessions

Authoritative source: official IDX.

- primary: IDX Digital Statistics daily-trading/session evidence;
- official fallback: IDX Daily Statistics publication listing when the monthly
  Digital Statistics API returns empty/incomplete data.

Never define exchange sessions from Yahoo or JCI dates.

### 4.2 Identity / listing intervals

Primary sources:

- IDX current stock listing reference;
- IDX official delisting history.

Supplemental identity source:

- KSEI Registered Securities when a required security is missing from the IDX
  current-list endpoint.

Important KSEI rule:

- KSEI `Status = Active` means active registration in KSEI's registry;
- it does **not** override an official IDX delisting date;
- it does **not** prove current IDX tradability;
- official IDX `listed_to` remains authoritative when available.

### 4.3 Session-level Regular-Market execution truth

Authoritative source: official IDX Stock Summary.

Correct semantics:

- `Volume > 0` AND `Frequency > 0` => `ACTIVE` point evidence;
- `Volume == 0` AND `Frequency == 0` => `NO_TRADE` point evidence;
- missing, negative, or internally inconsistent regular metrics => unresolved;
- row absence => unresolved.

Critical correction learned during DATA-002C:

`Volume/Frequency` are already the relevant regular/order-book metrics in the
Stock Summary schema being used. `NonRegularVolume` and `NonRegularFrequency`
are separate fields and **must not be subtracted**.

### 4.4 Legal suspension/resumption explanation

Official IDX suspension/resumption announcements and snapshots remain valuable
for explicit legal-state explanation and market-scope handling.

A complete announcement reconstruction is not required to manufacture ACTIVE
state when direct official per-session execution evidence already exists.

### 4.5 Daily OHLCV prices

Primary free research provider: Yahoo/yfinance with `auto_adjust=False`.

Yahoo is a **price provider**, not the authority for exchange tradability.

### 4.6 Corporate actions

Authoritative technical-action source: official IDX corporate actions / issued
history.

Initial V1 price-semantic gate focuses on:

- Stock Split;
- Reverse Stock.

Dividends are informational/nonblocking for the initial technical-price semantics.

---

## 5. Raw-price and model-safe-price contract

Preserve raw provider OHLCV for auditability.

Never overwrite execution prices with vendor-adjusted prices.

Model-safe price rows are restricted to sessions whose official point-in-time
state resolves to `ACTIVE`.

If Yahoo returns a bar on a session officially classified as NO_TRADE,
SUSPENDED, FCA_WATCHLIST, DELISTED, or otherwise non-ACTIVE:

- retain the raw provider row for audit;
- count it as provider contamination / quarantined evidence;
- do **not** let it override IDX exchange truth;
- do **not** let it enter features, liquidity calculations, labels, support/
  resistance, backtests, or model training.

A missing price on an expected ACTIVE session is still a hard failure.

---

## 6. Why the 35 adversarial tickers exist

The 35 names are **not** the model universe and are not a trading shortlist.
They are a deliberately difficult QA/stress-test catalog.

Representative families:

- normal/liquid: BBCA, BBRI, BMRI, TLKM, ASII, ICBP, INDF, UNVR;
- newer IPO/growth names: BREN, AMMN, CUAN, GOTO, PGEO, NCKL, MTEL, ADMR;
- suspend/resume cases: IFSH, ROCK, INDS, INET, BWPT, NSSS, KRAS, UANG;
- long-suspension cases: MKNT, SBAT, DEAL, TRIL, SRIL;
- complex market-scope case: HDTX;
- delisted case: KPAS;
- illiquid/data-quality stress: ALTO, ARMY, ARTI, ALMI.

Purpose: find conceptual/data-pipeline bugs cheaply before scaling to the full
market and many years of history.

---

## 7. Chronological failure -> diagnosis -> fix ledger

This section is intentionally preserved because the failures are reusable design
knowledge.

### 7.1 Legacy repo audit: old model was not a safe foundation

The old `market-movement-analyzer` was an anomaly-direction classifier, not the
new S/R + RR decision-support design.

Useful patterns were retained conceptually:

- chronological split discipline;
- purge/embargo ideas;
- causal rolling features;
- calibration concepts;
- immutable run manifests;
- downloader/cache/retry patterns;
- listing/delisting retrieval patterns.

Major legacy flaws identified:

- missing/suspended/no-trade conflation;
- survivorship from current-active/current-liquid backfills;
- incomplete security master;
- row-count coverage false positives;
- adjusted prices overwriting execution semantics;
- polluted cross-sectional universe;
- overlapping-trade portfolio compounding issues;
- unresolved/delisted outcomes excluded from mature metrics;
- overloaded `confidence` semantics;
- holdout reuse not technically prevented;
- weak environment freezing.

Decision: new repo + selective migration only.

### 7.2 Initial DATA foundation

Built fail-closed primitives for:

- security master;
- coverage;
- providers;
- universe;
- provenance/storage;
- Data Gate.

Important early gate fix:

`price_semantics_verified` missing must fail closed; absence must never default
True.

### 7.3 Tradability parsing and adversarial catalog

Official IDX suspension/resumption PDF ingestion added with exact market-scope
handling and manual-review fallbacks for ambiguous/intraday cases.

Adversarial 35-ticker catalog created.

### 7.4 DATA-002 result

Engineering/tests healthy, but gate blocked.

Important findings:

- July official monthly session API returned empty;
- Yahoo only 30/35 available in early audit;
- tradability coverage remained UNKNOWN;
- corporate actions unverified;
- gate 0/35.

Lesson: a blocked gate is useful evidence, but the blocker classification itself
must be audited before concluding that external data is impossible.

### 7.5 DATA-002B

Fixes included:

- official IDX Daily Statistics fallback for July exchange sessions;
- official stock split/reverse-split source integration;
- improved tradability parser/compiler.

Result:

- tests passed;
- July calendar resolved;
- corporate-action source became tractable;
- parser quality improved;
- still 0/35 because session coverage remained unresolved.

### 7.6 Ontology bug: global initial ACTIVE assumption

Root cause found in coverage architecture:

A market-wide `initial_state=ACTIVE` was required to mark a discovery window
complete and then used as an ACTIVE complement for every ticker.

Why wrong:

left-boundary state is **per security**, not global. Some names may already be
suspended, newly listed, delisted, etc.

Fix:

separate:

- global event-source discovery completeness;
- per-security authoritative state anchors.

No anchor/evidence => UNKNOWN.

### 7.7 DATA-002C initial anchor implementation

Added canonical per-ticker anchors and threaded them through coverage, gate,
universe, and reconciliation.

Early runtime result:

- thousands of ACTIVE anchors;
- 5 SUSPENDED snapshot anchors;
- but UNKNOWN did not improve and gate stayed 0/35.

### 7.8 Exact-anchor bug

Bug:

an authoritative anchor on its **exact as-of date** was still being rejected
unless a surrounding global discovery window was complete.

Correct rule:

- exact point evidence is authoritative on that exact date;
- propagation to other dates requires an evidence-complete causal path.

Fix applied with regression tests.

### 7.9 Better framing: direct session execution evidence

Instead of reconstructing every legal suspension event merely to infer whether a
security traded on a daily model session, use official Stock Summary direct
Regular-Market evidence for the session.

This does not weaken the standard. It makes the evidence closer to the actual
model question.

### 7.10 Major Stock Summary semantics bug

Runtime symptom:

- UNKNOWN fell from 1,375 to 70;
- all 70 unresolved observations were
  `REGULAR_TRADE_METRICS_NEGATIVE_AFTER_SUBTRACTION`;
- GOTO was especially affected.

Diagnosis:

code incorrectly treated `Volume/Frequency` as totals and subtracted
`NonRegular*`.

Fix:

use regular `Volume/Frequency` directly; keep NonRegular metrics as separate
diagnostics.

Result:

- corrected ACTIVE anchors increased;
- UNKNOWN 70 -> 0.

Permanent lesson:

**schema semantics must be proven from source meaning, not inferred from field
names.**

### 7.11 Stale Yahoo July artifact

After tradability reached UNKNOWN=0, gate remained low because Yahoo artifacts
had been collected before July exchange sessions were correctly available.

Diagnosis:

not a new data-source blocker; the stored price window was stale.

Fix:

`run_exchange_window_price_backfill()` derives Yahoo bounds from official IDX
sessions and automatically uses an exclusive provider end date one day after the
last required exchange session.

Result:

price coverage improved substantially.

Permanent lesson:

**provider query windows must be derived from authoritative session calendars.**

### 7.12 Provider contamination bug

Runtime symptom:

- missing ACTIVE prices = 0;
- UNKNOWN = 0;
- but 262 Yahoo bars appeared on official NO_TRADE/SUSPENDED sessions;
- gate only 23/35.

Bad interpretation would be to distrust exchange truth merely because Yahoo had
a row.

Fix:

- IDX point evidence remains authoritative;
- non-ACTIVE Yahoo rows are quarantined;
- raw artifacts preserved;
- model-safe ACTIVE-only view introduced.

Result:

23/35 -> 33/35.

Permanent lesson:

**row presence is not execution truth. Keep source authority explicit.**

### 7.13 HDTX/KPAS identity issue

Remaining failures: HDTX and KPAS.

Primary IDX current-list endpoint omitted them.

KSEI supplemental identity lookup proved valid security identity/listing dates:

- HDTX listing date: 1990-06-06;
- KPAS listing date: 2018-10-05.

However, KSEI registry `Status=Active` was initially easy to overread.

Official IDX delisting evidence showed both had `listed_to = 2025-07-18`.

Correct interpretation:

KSEI proves identity/registration, but IDX delisting date closes the exchange
listing interval.

### 7.14 Final 33/35 -> 35/35 gate bug

Bug:

`security_coverage.complete` still required `bool(listed)` within the evaluated
window.

That incorrectly failed a security whose identity and full listing interval were
known but which had already been delisted before the research window.

Fix:

- known identity + zero listed sessions because complete listing interval lies
  outside the evaluated window => resolved non-eligibility, `price_required=False`;
- ticker absent from security master entirely => explicit
  `SECURITY_IDENTITY_UNRESOLVED` hard failure.

Result:

**35/35 adversarial PASS**.

Permanent lesson:

**zero expected observations can be correct evidence, but only when identity and
interval boundaries are known. Absence and resolved non-applicability are not the
same thing.**

---

## 8. Post-35/35 hardening already implemented

The project deliberately did not jump directly into modelling after 35/35.
The next code work prepared the architecture for scale.

### 8.1 Full-universe gate

Added market-wide certification using the same hard per-security DATA GATE.

Candidate discovery must include:

- PIT listing interval overlap;
- official tradability anchors in the window;
- official tradability intervals in the window.

Why the extra evidence-derived candidate set matters:

A current-list omission like HDTX/KPAS must not create a survivorship hole by
simply making the security disappear from the market-wide audit.

Evidence-only ticker + missing identity => explicit identity failure.

### 8.2 Full-universe artifacts

The full-market runner writes:

- per-ticker gate results;
- session-coverage reports;
- blocker histogram;
- unresolved identity list;
- UNKNOWN-session total;
- missing ACTIVE-price total;
- quarantined provider-bar count.

### 8.3 Batched Yahoo backfill

Full-market price downloads must be batched rather than sending ~900 symbols in
one giant request.

Design goals:

- bounded batch size;
- reuse existing artifacts;
- revision protection remains on;
- batch/download errors explicit and fail-closed.

### 8.4 Resumable Stock Summary cache

Long-history Stock Summary work must not require network refetch every time the
anchor semantics code changes.

Per-session official parsed snapshots are cached so execution anchors can be
regenerated locally and historical backfill can resume.

### 8.5 Automatic raw-price semantics verification

Market-wide certification should not need a manually populated `True` mapping
for hundreds of securities.

Canonical raw price artifacts can be verified automatically from their required
raw execution columns and semantics contract.

### 8.6 Model-safe market panel

After full-market gate PASS, materialize one canonical ACTIVE-only panel rather
than letting future models read raw Yahoo files directly.

This panel becomes the research dataset surface for features/labels.

### 8.7 Certified snapshot manifest

Before modelling, freeze exact artifact hashes, source/code identity, and
environment metadata.

A manifest verification step must immediately re-check the frozen hashes.

Dataset drift after model experiments begin must be explicit, versioned, and
re-certified.

### 8.8 History certification ladder

Do not jump immediately from 43 sessions to five years.

Planned trailing horizons:

- 43 sessions;
- 126 sessions (~6 months);
- 252 sessions (~1 year);
- 504 sessions (~2 years);
- 756 sessions (~3 years);
- 1260 sessions (~5 years).

The longest defensible PASS horizon should be discovered mechanically.

This approach localizes the first historical boundary where evidence or provider
quality breaks.

---

## 9. Current phase transition rules

### Adversarial certification

Status: **PASS (35/35)** for the 43-session window.

### Full-universe 43-session certification

Status: **next runtime checkpoint**.

Must require at least:

- no unresolved required identity;
- official session calendar complete;
- zero UNKNOWN required listed sessions;
- zero missing ACTIVE-session price rows;
- non-ACTIVE provider contamination quarantined;
- split/reverse-split technical history verified;
- raw-price semantics verified;
- reproducibility artifacts available.

### Freeze

Only after full-universe PASS:

1. materialize ACTIVE-only market panel;
2. freeze required certification artifacts;
3. create certified manifest;
4. verify manifest hashes;
5. record exact dataset/code version.

### Historical expansion

Then extend backwards incrementally using the certification ladder.

Prefer a shorter clean/PIT dataset over a longer guessed dataset.

### Model research

Only after a sufficiently long certified dataset exists.

Model research then changes mainly the layers above the frozen market foundation:

`certified market layer -> features -> labels -> model -> walk-forward validation`

The identity/session/tradability/provider contracts should not be redesigned for
each model unless a genuine new data bug is discovered.

---

## 10. Future model-validation contract

When model work is eventually authorized:

- chronological walk-forward OOS;
- purge/embargo where labels overlap;
- no random train/test split;
- calibration sets separated where necessary;
- final locked holdout;
- forward shadow/paper evaluation only after model freeze;
- probability calibration evaluated separately from ranking/score quality;
- Opportunity Score must never be presented as a probability;
- Estimate Reliability must remain a separate concept;
- retain stress regimes where defensible historical evidence permits, ideally
  including 2020 rather than optimizing only on recent calm data.

---

## 11. Do-not-repeat list

These are known traps.

1. Do not infer suspension from a missing Yahoo row.
2. Do not infer ACTIVE from Yahoo row presence.
3. Do not infer ACTIVE merely from `LISTED` existence.
4. Do not use a global market-wide initial ACTIVE state.
5. Do not propagate a point anchor outside an uncertified evidence path.
6. Exact authoritative point evidence is valid on its exact date.
7. Do not subtract NonRegular metrics from Stock Summary regular metrics.
8. Do not let provider contamination override official IDX session truth.
9. Do not use current survivors to define historical universe membership.
10. Do not assume IDX current-list endpoint is exhaustive for difficult names.
11. Do not interpret KSEI registry Active as current IDX listing/tradability.
12. Do not fail a known security merely because it has zero applicable sessions
    in a window outside its listing interval.
13. Do not treat an absent identity as resolved zero-applicability.
14. Do not silently overwrite Yahoo provider revisions.
15. Do not use vendor adjusted close as raw execution OHLC.
16. Do not scale to years of data before the same semantics pass a small
    adversarial window.
17. Do not start model tuning to compensate for a data-gate failure.
18. Do not merge the certification branch to main merely because unit tests pass;
    the runtime data gate is the decision-changing checkpoint.

---

## 12. Important code surfaces

The exact set evolves, but the important concepts currently live around:

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

## 13. Current recommended runtime sequence

For the 43-session full-market checkpoint:

1. update local branch to current `data/idx-data-002c` head;
2. run full pytest;
3. reuse certified 43-session official exchange sessions;
4. reuse/regenerate corrected Stock Summary point anchors from cached/raw official
   evidence where possible;
5. discover the required universe from identity + official point/interval evidence;
6. reconcile evidence-only identities with official IDX/KSEI sources;
7. backfill missing ACTIVE-required Yahoo prices in bounded batches;
8. keep revision guards enabled;
9. verify official split/reverse-split technical history;
10. derive raw price semantics automatically;
11. run full-universe DATA GATE;
12. inspect blocker histogram rather than weakening the gate;
13. if and only if PASS, materialize ACTIVE-only market panel;
14. freeze and hash certification artifacts;
15. verify certified manifest;
16. then begin historical expansion ladder.

---

## 14. Research workflow learned from this phase

The preferred workflow for uncertain data/ML foundations is:

`small adversarial window`
-> `observe exact failure`
-> `classify conceptual vs provider vs artifact bug`
-> `fix one assumption`
-> `regression test`
-> `rerun`
-> `only then scale universe/time horizon`

This is intentionally different from giving an agent a broad outcome such as
"make the market dataset ready" and letting it optimize toward apparent
completion.

The project should preserve falsifiability: each step should be small enough
that a failure teaches which assumption broke.

---

## 15. Ledger update protocol

Whenever a material checkpoint occurs, append/update the relevant sections with:

- date/window/task;
- branch + commit/head;
- test result;
- gate result;
- observed failure/symptom;
- root-cause diagnosis;
- code/data fix;
- evidence that the fix worked;
- permanent lesson / invariant added;
- exact remaining blocker;
- next smallest safe action.

Do **not** erase failed approaches merely because they were fixed. Keep the
failure and correction documented; they are part of the project's knowledge.

If this file and an older handoff disagree, investigate the chronology. The
newer explicitly evidenced decision should win, and this ledger should then be
updated to make the resolution clear.
