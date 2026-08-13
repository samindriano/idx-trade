# IDX Trade — Master Project Context & Continuity Guide

> **Purpose:** this is the comprehensive bootstrap document for continuing the
> IDX Trade project after chat/context loss, model handoff, or a new agent/session.
> It is intentionally much more detailed than a README.
>
> **Read this first in a new chat.** Then read `docs/PROJECT_LEDGER.md` for the
> chronological failure/diagnosis/fix history and the newest checkpoint under
> `docs/checkpoints/` for the latest runtime result.
>
> **Status date:** 2026-08-09.
>
> **Current project stage:** DATA FOUNDATION / HISTORICAL CERTIFICATION.
> Modelling has **not** started. `IDX-VAL-002` has **not** started. No merge to
> `main` is authorized yet.

---

# 0. One-minute emergency handoff

If there is only time to read one section, read this one.

Repository:

- `samindriano/idx-trade`

Primary working branch:

- `data/idx-data-002c`

Primary review PR:

- PR #2 — draft — base `data/idx-data-002b`

Five-year preparation branch:

- `data/idx-data-005-1260-prep`
- PR #3 — draft only, preparation branch, **must not be treated as a 1260 PASS**

Latest primary-branch checkpoint before this update:

- `625e4ee40390921c7d8c904e9ffc8676a4db878c`
- commit message: `merge: reconcile guarded 1260 research preflight`

Latest five-year prep branch checkpoint when this document was created:

- `c14fdce7b04edf05c84a506d8b8ee38d04593021`
- prep implementation CI previously passed 146 tests, 0 failed

Current state:

- 43-session adversarial gate: **35/35 PASS**
- 43-session full-market common-stock gate: **963/963 PASS and certified**
- 126-session full-market gate: **963/963 PASS and certified**
- 504-session expansion: **NOT certified; strict opening-price gap remains**
- 1260-session research-feasibility evaluation: **NO-GO / STOP**
- 1260 model-safe panel/manifest: **not created**

Certified 43-session snapshot:

- window: `2026-06-02 -> 2026-07-31`
- required common stocks: 963
- UNKNOWN sessions: 0
- missing ACTIVE prices: 0
- model-safe panel SHA-256:
  `ac923c22dfc3d85b1769419bc00d02136e4f9a96d7999ba466bc27a0579624b7`
- manifest SHA-256:
  `6c639bf009553db64e1b80b5d570bd83436af57a6c9b9d2ae26d71521b255ffa`
- manifest verification: `valid=true`, 9/9 artifacts

Certified 126-session snapshot:

- window: `2026-01-15 -> 2026-07-31`
- required common stocks: 963
- gate: 963/963 PASS
- UNKNOWN sessions: 0
- missing ACTIVE prices: 0
- quarantined provider bars: 2,672
- model-safe panel: 107,424 rows / 880 tickers
- model-safe panel SHA-256:
  `401d2bdb65beaf9442f1a54212372e2adc5d1b2c006fc1e759738f6deea8a19a`
- manifest SHA-256:
  `650ab19e5a77085b7987ffaaa0ed7cbee0eb8c478a72c0c1166767e9eec68f5b`
- manifest verification: `valid=true`, 14/14 artifacts

504 target:

- exact official-session window: `2024-06-21 -> 2026-07-31`
- 504 official IDX sessions
- first full attempt discovered 977 securities before scope
- CNTX excluded as authoritative non-common preference share
- 976 common stocks required
- first attempt: 973 passed / 3 failed
- the only affected names were FREN, MASA, MFIN

Current 504 blocker state after the first repair attempt:

- FREN identity is now resolved as a common share:
  - listed_from `2006-11-29`
  - listed_to `2025-04-16`
  - 196 official ACTIVE sessions become price-required in the 504 window
  - no raw price artifact was available in that repair run
- MASA:
  - 22 official ACTIVE sessions are missing a defensible opening price
  - official IDX Stock Summary proves ACTIVE and has valid H/L/C/Volume
  - `OpenPrice` and `FirstTrade` are non-positive for those rows
  - no synthetic/forward-filled open is allowed
- MFIN:
  - 249 missing official ACTIVE-session prices from the pre-repair failure set
  - the last repair run stopped on MASA before processing MFIN

The 504 ladder was **not rerun after the latest repair stop**, so 504 must not be
called PASS. No 504 model-safe panel or certified 504 manifest exists yet.

Approved next reasoning direction, but **not yet a certified result**:

1. process FREN, MASA, and MFIN independently rather than hard-stopping the
   entire repair after the first ticker;
2. use official IDX Stock Summary price rows first;
3. for a remaining ACTIVE row where IDX proves H/L/C/Volume but does not expose
   a positive opening execution, a secondary historical provider may be used
   only as an **open-price witness**, not as the authority for the whole bar;
4. accept secondary `Open` only when ticker/date matches, secondary Open > 0,
   secondary H/L/C match the official IDX H/L/C for that date, and Open lies
   inside the official low/high envelope;
5. canonical row remains official IDX H/L/C/Volume plus the cross-validated
   witnessed Open;
6. preserve dual provenance and never overwrite an existing valid Yahoo or
   official price row;
7. if this cannot be done defensibly, 504 remains FAIL rather than weakening the
   gate.

If 504 later certifies cleanly, the next expansion policy is:

- **504 -> 1260 directly**
- do not automatically run 756
- 252/756 are diagnostic fallback horizons only if a larger jump fails and a
  historical boundary must be localized

Five-year prep has already been implemented separately. A valid 504 baseline
must be the exact trailing suffix of the 1260 official-session window. If
aligned, 504 -> 1260 adds exactly 756 older sessions.

Absolute prohibitions at the current stage:

- do not start model training;
- do not run `IDX-VAL-002`;
- do not merge to `main`;
- do not paper trade or live trade;
- do not infer suspension from Yahoo absence;
- do not infer ACTIVE from Yahoo presence;
- do not fabricate prices, identity dates, security types, sessions, or states;
- do not exclude a difficult common share merely to make the gate green;
- do not include a preference/non-common share merely because official daily
  execution evidence exists for it.

---

# 1. What this project is trying to build

The project is a personal IDX daily/EOD decision-support research system. The
intended final system is **not a BUY/SELL oracle** and must not be designed as a
single opaque directional prediction.

The long-term output concept is closer to a structured trade-opportunity object:

- market/security context;
- support/resistance and local market structure;
- possible entry region;
- invalidation / stop logic;
- one or more target regions;
- risk/reward;
- calibrated probability such as `P(TP before SL)`;
- expected realized R;
- Opportunity / Setup Score on a 0-100 style scale;
- optional Entry Quality Score;
- Estimate Reliability as a separate quantity from probability and from score;
- later, only after calibration is trustworthy, position-sizing research such as
  fractional Kelly and Monte Carlo scenario analysis.

Important semantic separation for future work:

- **Probability is not Opportunity Score.**
- **Opportunity Score is not Estimate Reliability.**
- **Estimate Reliability is not probability confidence by another name.**
- support/resistance geometry, execution economics, probability calibration,
  expected R, and reliability should remain separately interpretable.

The project began by intentionally refusing to model until the market-history
foundation is defensible. That decision is central to the project.

---

# 2. Project roadmap and current position

A useful top-level roadmap is:

## Stage 1 — Data foundation and historical certification **(CURRENT)**

Build a point-in-time-safe common-stock market history with:

- official exchange sessions;
- security identity/listing intervals;
- delisted histories;
- security type / common-share scope;
- Regular-Market tradability state;
- suspension/resumption evidence;
- direct per-session official execution evidence;
- raw daily OHLCV;
- corporate actions;
- provider-gap handling;
- raw/provider contamination quarantine;
- reproducible certified model-safe panels and manifests.

## Stage 2 — Research specification and validation design

Freeze:

- exact setup definition;
- support/resistance semantics;
- candidate generation;
- entry/invalidation/target definition;
- label semantics, including unresolved outcomes;
- forward horizon;
- benchmark;
- calibration protocol;
- train/validation/calibration/holdout roles;
- purge/embargo rules.

## Stage 3 — Feature engineering and baseline models

Candidate feature families may include:

- market structure;
- support/resistance geometry;
- volume/liquidity;
- volatility;
- momentum;
- relative strength;
- market/sector regime;
- distance-to-entry/stop/target and RR geometry.

Begin with simple baselines before complex models.

## Stage 4 — Model research and selection

Compare model/feature families with chronological OOS validation, emphasizing:

- ranking quality;
- probability calibration;
- expected realized R;
- robustness across regimes;
- stability across time;
- score interpretability.

## Stage 5 — Locked validation

Use a final untouched holdout after the research choices are frozen.

No post-holdout tuning to rescue a weak result.

## Stage 6 — Forward shadow / paper evaluation

Only after model/spec freeze:

- run causally on newly arriving data;
- compare predicted probabilities and rankings with realized outcomes;
- inspect calibration drift;
- only later consider sizing research such as fractional Kelly / Monte Carlo.

As of this document, only Stage 1 is active.

---

# 3. Research and validation philosophy

The project should behave like an empirical research system, not like a prompt
that tries to maximize an appealing backtest.

Future model-validation requirements already agreed in principle:

- chronological walk-forward OOS;
- no random train/test split for the core time-series claim;
- purge/embargo when labels overlap future periods;
- calibration and threshold selection separated where necessary;
- final locked holdout;
- forward shadow/paper period after model freeze;
- probability quality measured separately from ranking quality;
- unresolved outcomes handled explicitly rather than silently dropped;
- stress regimes retained when the data foundation can support them;
- no tuning to compensate for a data-foundation defect.

The preferred engineering/research loop discovered during Stage 1 is:

`hypothesis`
-> `small bounded audit`
-> `observe exact failure`
-> `classify failure`
-> `fix one assumption`
-> `regression test`
-> `rerun`
-> `scale universe/time horizon only after semantics hold`

This is why the project used 35 adversarial names and a 43-session window before
trying full-market multi-year history.

---

# 4. The old repository and why this is a new project

An older repository, `market-movement-analyzer`, was audited as a possible donor.
It was an anomaly/direction-oriented system and did not match the new
support/resistance + risk/reward decision-support objective.

Useful conceptual patterns from the old work included:

- chronological split discipline;
- causal rolling features;
- purge/embargo concepts;
- calibration ideas;
- downloader/cache/retry patterns;
- immutable manifest concepts;
- listing/delisting retrieval patterns.

Critical issues found in the old approach included:

- conflating suspension with missing provider rows;
- survivorship bias risk;
- adjusted-price vs raw-execution-price confusion;
- row-count coverage false positives;
- overlapping-trade portfolio compounding problems;
- unresolved outcomes disappearing from mature metrics;
- overloaded confidence semantics;
- holdout reuse/tuning risk.

Decision: keep `idx-trade` as the new source of truth and migrate concepts only
after explicit audit. Do not migrate old weights/predictions/targets blindly.

---

# 5. Core market ontology — these dimensions must remain separate

A major portion of the project consisted of discovering that several concepts
which look similar must never be collapsed.

## 5.1 Security existence

Canonical existence states:

- `NOT_LISTED`
- `LISTED`
- `DELISTED`

Existence comes from point-in-time listing intervals.

A known security whose complete listing interval is outside a target research
window can validly have zero applicable sessions. That is not the same as a
security whose identity is missing.

## 5.2 Security type / research scope

The initial research universe is IDX **common shares**.

Security type is separate from existence and from tradability.

Official execution sources can emit non-common securities. They remain part of
the evidence/audit surface but do not automatically belong to the model universe.

Scope rules:

- proven common share -> in scope for data certification;
- proven preference/non-common share -> authoritative scope exclusion;
- unresolved type/identity -> fail closed;
- no arbitrary ticker blacklist merely to produce a green gate.

## 5.3 Tradability / Regular-Market state

Relevant states currently include:

- `ACTIVE`
- `NO_TRADE`
- `SUSPENDED`
- `FCA_WATCHLIST`
- `UNKNOWN`

`UNKNOWN` is a valid fail-closed state. It must not be converted to ACTIVE,
NO_TRADE, or SUSPENDED just because doing so makes coverage easier.

## 5.4 Provider availability

Provider presence is a fourth, independent dimension.

Examples:

- a Yahoo row can exist on an officially non-ACTIVE session;
- an officially ACTIVE session can be absent from Yahoo;
- a security can be listed but suspended;
- a security can be KSEI-registered but no longer exchange-listed;
- a Stock Summary row can be absent without proving NO_TRADE.

This separation is one of the most important permanent lessons in the repo.

---

# 6. Source-authority hierarchy

## 6.1 Exchange sessions

Authority: official IDX.

Implemented official paths include:

- IDX Digital Statistics daily/session evidence;
- IDX Daily Statistics publication listing as an official fallback.

Do not infer official sessions from Yahoo, JCI bars, or weekdays.

The official calendar itself is part of the reproducibility contract.

## 6.2 Identity and listing intervals

Primary identity/existence sources:

- IDX current stock-listing reference;
- IDX official delisting history.

Supplemental identity/type source:

- KSEI Registered Securities.

KSEI is **not** current exchange-tradability authority.

Permanent KSEI interpretation:

- `Status = Active` means active KSEI registration/custody record;
- it does not prove current IDX listing;
- it does not prove Regular-Market tradability;
- KSEI can supply missing listing-origin date and security type;
- official IDX delisting evidence controls the ending listing boundary.

## 6.3 Direct per-session execution truth

Authority: official IDX Stock Summary.

Correct Regular-Market semantics currently used:

- `Volume > 0` AND `Frequency > 0` -> exact-session `ACTIVE` evidence;
- `Volume == 0` AND `Frequency == 0` -> exact-session `NO_TRADE` evidence;
- missing/negative/internally inconsistent regular metrics -> unresolved;
- row absence -> unresolved.

Critical schema lesson:

- Stock Summary `Volume` and `Frequency` are already the relevant regular/order-
  book daily metrics for the audited schema;
- `NonRegularVolume` and `NonRegularFrequency` are separate diagnostics;
- they must **not** be subtracted from regular metrics.

## 6.4 Legal suspension/resumption evidence

Official IDX announcements/snapshots remain important for:

- legal state;
- suspension reason;
- market scope;
- boundary explanation.

Direct Stock Summary execution evidence can satisfy exact-session trading truth,
but legal-state evidence is still needed when an exact absence or suspension
must be explained.

## 6.5 Daily OHLCV

Primary free provider:

- Yahoo/yfinance with `auto_adjust=False`.

Raw execution OHLC must remain separate from vendor adjusted close.

Yahoo is price evidence only. It never defines universe membership or exchange
state.

## 6.6 Corporate actions

Authoritative technical-action source is official IDX, currently focused on:

- Stock Split;
- Reverse Stock.

Dividends are informational/nonblocking for the initial technical-price gate.

Yahoo corporate-action fields are diagnostic, not the authority for declaring
split history verified.

---

# 7. Raw-price contract and model-safe panel

Canonical raw execution fields are structurally separated from adjusted/vendor
fields.

Important rules:

- raw OHLC remains raw;
- vendor adjusted close never replaces raw OHLC;
- corporate-action/vendor adjustment fields remain separate diagnostics;
- dates must be valid and unique;
- OHLC must be positive;
- High must contain Open/Close/Low;
- Low must contain Open/Close/High;
- volume must be non-negative;
- empty/no-price artifacts do not count as price-semantics verified.

The model-safe market panel is **not** the raw provider dataset.

It retains only rows where:

1. security is in common-share scope;
2. security exists for that session;
3. official point-in-time market state is `ACTIVE`;
4. execution-safe raw price evidence exists.

If a provider row appears on NO_TRADE, SUSPENDED, FCA_WATCHLIST, DELISTED, or
another non-ACTIVE state:

- preserve it in raw evidence;
- count it as provider contamination/quarantine;
- never let it override official IDX truth;
- never let it enter features, labels, support/resistance, liquidity, or
  backtests.

Missing price on an expected official ACTIVE session is a hard failure.

---

# 8. Adversarial certification set

The 35-ticker adversarial catalog is **QA**, not the future model universe.

It intentionally covers difficult semantic classes.

Normal/liquid examples:

- BBCA
- BBRI
- BMRI
- TLKM
- ASII
- ICBP
- INDF
- UNVR

Recent-ish IPO / modern listing examples:

- BREN
- AMMN
- CUAN
- GOTO
- PGEO
- NCKL
- MTEL
- ADMR

Suspend/resume examples:

- IFSH
- ROCK
- INDS
- INET
- BWPT
- NSSS
- KRAS
- UANG

Long-suspension examples:

- MKNT
- SBAT
- DEAL
- TRIL
- SRIL

Complex identity/state example:

- HDTX

Historical/delisted example:

- KPAS

Data-quality/illiquid stress examples:

- ALTO
- ARMY
- ARTI
- ALMI

The purpose of the adversarial stage was to break assumptions cheaply before
scaling to ~900+ securities.

Final adversarial result for the 43-session window:

- 35/35 PASS
- UNKNOWN = 0
- missing ACTIVE prices = 0
- quarantined non-ACTIVE Yahoo rows = 262

---

# 9. Failure chronology — detailed causal history

This section exists so a new agent does not reintroduce already-disproved ideas.

## 9.1 DATA-002 — first bounded attempt

Branch history included `data/idx-data-002`.

Representative final checkpoint:

- commit `2d10b520...`
- 44 tests passed
- June calendar available; July path still incomplete
- Yahoo coverage 30/35, five `NO_PROVIDER_ROWS`
- tradability parser: 82 PDFs, 66 parsed, 16 manual
- gate: 0/35
- corporate actions still unverified

Lesson: healthy code/tests do not imply data readiness.

## 9.2 DATA-002B — improve calendar and corporate actions

Representative checkpoint:

- commit `7f9b708e2ea95e27b30769fa80dd517423790884`
- 69 tests passed
- July 2026: 23 official sessions recovered through official Daily Statistics
- official stock-split source implemented
- tradability parsed improved 66 -> 71
- manual cases reduced 16 -> 11
- adversarial still 0/35
- blocker remained session coverage/tradability semantics

Lesson: remove source/engineering blockers, but do not assume the remaining gate
classification is conceptually correct.

## 9.3 Global initial-state ontology bug

Original idea incorrectly assumed one market-wide `initial_state=ACTIVE` could
anchor the left boundary.

Why wrong:

- listing/tradability state is per security;
- long-suspended and special cases invalidate a global ACTIVE complement;
- incomplete announcement discovery cannot justify backfilling ACTIVE.

Correct model:

- global event-source discovery window;
- per-security authoritative anchors;
- exact market overrides;
- no anchor/conflict -> UNKNOWN;
- propagation only with defensible evidence completeness.

## 9.4 Exact-anchor bug

An authoritative exact-date point anchor was originally rejected when the
surrounding discovery window was incomplete.

Correct invariant:

- exact authoritative evidence is valid on the exact session;
- propagation away from that session requires an evidence-complete causal path;
- future anchors cannot classify past dates;
- contradictory exact evidence hard-fails.

Regression tests were added for ACTIVE exact, SUSPENDED exact, future-anchor
non-propagation, and ACTIVE/SUSPENDED contradiction.

## 9.5 Direct session execution evidence reframing

Rather than reconstructing every legal event before knowing whether a security
traded on a model date, official Stock Summary became the primary exact-session
execution evidence.

This reduced dependence on incomplete public announcement archives while keeping
legal suspension evidence as a separate explanatory layer.

## 9.6 Stock Summary subtraction bug

A major bug initially computed something like:

- regular volume = `Volume - NonRegularVolume`
- regular frequency = `Frequency - NonRegularFrequency`

That interpretation was wrong for the audited endpoint schema.

Observed symptom:

- UNKNOWN dropped dramatically but 70 rows became
  `REGULAR_TRADE_METRICS_NEGATIVE_AFTER_SUBTRACTION`.

Diagnosis:

- `Volume/Frequency` were already the regular/order-book metrics;
- `NonRegular*` were separate diagnostics.

Fix:

- use `Volume/Frequency` directly;
- never subtract `NonRegular*`.

Result:

- remaining UNKNOWN from this error class dropped to zero.

Permanent lesson: source semantics must be proven, not guessed from field names.

## 9.7 Yahoo end-date / stale artifact issue

After July official sessions were corrected, old Yahoo artifacts no longer
covered the complete authoritative session window.

Fix:

- derive provider request bounds from official sessions;
- account for yfinance `end` being exclusive;
- request through one calendar day after the final official session.

Permanent lesson: provider request windows derive from the exchange calendar,
not the other way around.

## 9.8 Provider contamination semantics bug

Yahoo returned rows on sessions that official IDX evidence classified as
non-ACTIVE.

Wrong solution would have been to let Yahoo override IDX state.

Correct solution:

- preserve raw row for audit;
- quarantine from model-safe view;
- do not make it a coverage failure merely because a vendor emitted a bar.

This change moved the adversarial gate from 23/35 to 33/35.

## 9.9 HDTX/KPAS identity edge

The primary IDX current-list endpoint was not exhaustive for difficult names.

KSEI public pages supplied supplemental identity/listing-origin evidence.

Critical interpretation:

- KSEI Active != active IDX listing/tradability.

Official IDX delisting evidence later controlled the end boundary for both HDTX
and KPAS at `2025-07-18`.

## 9.10 Zero-listed-session coverage bug

Coverage logic originally required `bool(listed_sessions)` to declare a known
security complete.

That falsely failed securities known to exist but whose entire listing interval
was outside the evaluation window.

Correct distinction:

- identity known + zero applicable listed sessions -> valid resolved
  non-applicability;
- identity absent -> unresolved identity hard failure.

Fixing this moved the adversarial set from 33/35 to 35/35.

## 9.11 Full-market survivorship hardening

A full-universe gate based only on identity/current-list records could omit
securities discovered only through official tradability/execution evidence.

Candidate discovery was expanded to include:

- security-master listing intervals overlapping the window;
- official tradability point anchors in the window;
- official tradability interval evidence overlapping the window.

Yahoo symbols never define the universe.

Evidence-only tickers absent from identity fail closed and must be reconciled.

## 9.12 First full-market run: 962/964

Once the 43-session semantics scaled to the full market:

- officially discovered: 964
- passed: 962
- failed: CNTB, CNTX
- UNKNOWN: 0
- missing ACTIVE prices: 0
- quarantine: 1,359

This was a strong sign that market-wide semantics worked, but it was **not**
permission to simply remove the final two names.

## 9.13 CNTB/CNTX security-type resolution

Official KSEI evidence showed these are fundamentally different cases.

CNTB:

- Century Textile Industry Tbk Seri B
- `Saham Biasa`
- IDX
- KSEI registry Active
- listing date `22 Desember 2000` -> `2000-12-22`
- therefore in common-stock identity scope

CNTX:

- Century Textile Industry Tbk Seri A
- `Saham Preference`
- therefore outside intended common-stock research scope

Permanent fixes:

- bilingual Indonesian/English date parsing;
- generic KSEI identity/type parser;
- generic `NON_COMMON_SHARE` scope-exclusion contract;
- no ticker hardcode;
- scope exclusion that conflicts with overlapping common-share identity hard
  fails.

## 9.14 CNTB two-session UNKNOWN

After identity/type resolution, full market became 962/963 because CNTB was
UNKNOWN on 2026-07-30 and 2026-07-31.

Important non-fix:

- missing Stock Summary row was **not** converted into NO_TRADE.

Authoritative legal evidence was found instead:

- CNTB/CNTX were suspended in all markets effective 2024-08-07;
- a later negotiated-market crossing did not reopen the Regular Market.

A curated authoritative legal-state interval was added for CNTB Regular Market.

Result:

- CNTB 2026-07-30 = SUSPENDED
- CNTB 2026-07-31 = SUSPENDED
- full 43-session common-stock gate = 963/963 PASS

Permanent lesson: an absent execution row is not a state; use legal evidence
when a legal state is needed.

---

# 10. Certified 43-session full-market milestone

Exact window:

- `2026-06-02 -> 2026-07-31`
- 43 official IDX sessions

Final result:

- required common-stock tickers: 963
- gate: 963 passed / 0 failed
- UNKNOWN sessions: 0
- missing ACTIVE prices: 0
- quarantined provider bars: 1,359
- blocker histogram: `{}`

Model-safe ACTIVE-only panel:

- SHA-256:
  `ac923c22dfc3d85b1769419bc00d02136e4f9a96d7999ba466bc27a0579624b7`

Certified snapshot manifest:

- SHA-256:
  `6c639bf009553db64e1b80b5d570bd83436af57a6c9b9d2ae26d71521b255ffa`
- verification: `valid=true`
- 9/9 artifacts verified

This is the first fully certified market-wide baseline and must remain immutable.

---

# 11. Certified 126-session milestone

The historical strategy was originally a dense ladder but was changed to an
adaptive ladder to avoid unnecessary intermediate runs.

The first historical expansion used exactly the trailing 126 official sessions.

Exact window:

- `2026-01-15 -> 2026-07-31`

Official calendar behavior:

- official sources only;
- early months came from IDX Digital Statistics where appropriate;
- July used official Daily Statistics fallback;
- no weekday estimation and no Yahoo/JCI substitution.

Stock Summary:

- 126/126 complete
- ACTIVE anchors: 107,424
- NO_TRADE anchors: 13,335
- unresolved metric rows: 0

Universe:

- discovered before scope: 964
- CNTX excluded as non-common preference share
- required common stocks: 963
- unresolved identities: 0
- CNTB preserved as common share

Yahoo historical extension:

- 874 updated
- 0 no-provider rows
- 0 download errors
- 0 revision conflicts

Ladder:

- 43 sessions: 963/963 PASS
- 126 sessions: 963/963 PASS
- UNKNOWN = 0
- missing ACTIVE = 0
- 126 quarantine = 2,672
- blocker histogram empty

Certified 126 model-safe panel:

- 107,424 rows
- 880 tickers
- SHA-256:
  `401d2bdb65beaf9442f1a54212372e2adc5d1b2c006fc1e759738f6deea8a19a`

Certified 126 manifest:

- 14/14 artifacts verified
- `valid=true`
- SHA-256:
  `650ab19e5a77085b7987ffaaa0ed7cbee0eb8c478a72c0c1166767e9eec68f5b`

The 126 snapshot is also immutable and should not be rewritten by later history
work.

---

# 12. Adaptive historical certification strategy

Initial default horizons were:

- 43
- 126
- 252
- 504
- 756
- 1260

After 126 passed completely clean, the policy was intentionally accelerated.

Current preferred ladder:

- 43 certified
- 126 certified
- 504 target
- 1260 target

Diagnostic fallback only:

- 252 if 126 PASS / 504 FAIL and the failure needs boundary localization;
- 756 if 504 PASS / 1260 FAIL and the failure needs boundary localization.

Do not run intermediate horizons automatically merely because they exist.

The point of checkpoints is not to be slow. The point is to preserve
falsifiability and localize historical source boundaries when a large jump fails.

---

# 13. First 504-session attempt

Exact official-session window:

- `2024-06-21 -> 2026-07-31`
- 504 sessions

Calendar:

- 516 official sessions available in the bounded wider window
- 26/26 months parsed
- 0 calendar errors

Stock Summary:

- 504/504 complete
- 126 cached
- 378 fetched
- ACTIVE anchors: 425,340
- NO_TRADE anchors: 54,131
- unresolved metric rows: 0

Universe:

- 977 discovered before scope
- CNTX excluded
- 976 common-stock tickers required

Yahoo extension:

- 881 requested
- 878 updated
- 3 `NO_PROVIDER_ROWS`
- 0 download errors
- 0 revision conflicts

126 regression inside this run:

- 963/963 PASS
- UNKNOWN = 0
- missing ACTIVE = 0
- quarantine = 2,672
- blocker histogram `{}`

504 result:

- 973 passed / 3 failed
- UNKNOWN sessions: 2
- missing ACTIVE prices: 271
- quarantined provider bars: 22,400

Blocker histogram:

- `PRICE_SEMANTICS_UNVERIFIED: 2`
- `SECURITY_IDENTITY_UNRESOLVED: 1`
- `SESSION_COVERAGE_INCOMPLETE: 2`

Failed names:

### FREN

Initial failure:

- `SECURITY_IDENTITY_UNRESOLVED`
- generic KSEI fallback did not return a defensible identity/type/listing record

### MASA

Initial failure:

- `SESSION_COVERAGE_INCOMPLETE`
- `PRICE_SEMANTICS_UNVERIFIED`
- 22 expected ACTIVE prices missing
- Yahoo returned no provider rows for the required historical segment

### MFIN

Initial failure:

- `SESSION_COVERAGE_INCOMPLETE`
- `PRICE_SEMANTICS_UNVERIFIED`
- 249 expected ACTIVE prices missing
- Yahoo returned no provider rows for the required historical segment

No 504 panel or manifest was created because the gate failed.

---

# 14. FREN identity resolution

FREN should **not** be excluded merely because KSEI's current surface is
insufficient.

Authoritative issuer/merger evidence was curated as a last-resort historical
identity source after the normal IDX/KSEI path failed.

Current historical identity contract for FREN:

- ticker: FREN
- company: PT Smartfren Telecom Tbk
- security type: common share / `Saham Biasa`
- listed_from: `2006-11-29`
- listed_to: `2025-04-16`

Why `listed_to=2025-04-16`:

- the authoritative merger plan states deletion of FREN trading on IDX on
  2025-04-17;
- the repository's `listed_to` interval is inclusive;
- therefore the final listed session boundary is the preceding date.

Guardrails:

- curated historical identity is used only when primary identity sources are
  missing;
- it must not silently override a primary authoritative identity;
- identity does not imply ACTIVE tradability;
- the evidence is in `config/curated_security_identities.csv`.

After identity resolution:

- 2025-04-16 = LISTED
- 2025-04-17 = DELISTED
- FREN exposes 196 official ACTIVE sessions in the 504 window that now require
  price evidence.

This changed the nature of FREN's blocker from identity to historical price
coverage.

---

# 15. Official IDX price fallback

A new fallback path was added because Yahoo can lose delisted/historical symbols
while official IDX Stock Summary still contains session price information.

Primary provider remains Yahoo.

Official IDX Stock Summary fallback rules:

- use only exact missing dates;
- require the same row to prove Regular-Market ACTIVE with positive Volume and
  Frequency;
- require positive valid H/L/C;
- prefer positive `OpenPrice`;
- allow positive `FirstTrade` only if `OpenPrice` is unavailable/non-positive;
- require valid OHLC envelope;
- preserve existing provider rows;
- fill absent dates only;
- never synthesize or forward-fill;
- preserve official source provenance.

The fallback can create a price artifact even when a ticker has no existing
Yahoo parquet. That is relevant for FREN.

---

# 16. Latest 504 repair attempt and why it stopped

Latest documented repair source checkpoint:

- primary branch `data/idx-data-002c`
- checkpoint ultimately recorded at commit
  `eee69814cdcb5ad0d5eebe9256bb9aff1ce81229`

Full pytest during the repair:

- 141 tests passed
- 0 failed
- warnings were non-blocking pandas warnings

FREN:

- historical identity repair succeeded
- price artifact still absent in that run
- 196 ACTIVE sessions therefore remain price-required/unverified

MASA:

- exact 22 missing ACTIVE dates were sent to the official IDX price fallback
- all 22 had positive Regular-Market Volume/Frequency
- official High/Low/Close were valid
- both `OpenPrice` and `FirstTrade` were non-positive
- result: 22 unresolved price rows, zero filled rows

MFIN:

- exact pre-repair missing set was 249 ACTIVE sessions
- the repair run stopped on the MASA hard-stop condition before MFIN was
  processed

Because of that stop:

- no post-repair 126/504 ladder rerun exists;
- no 504 panel exists;
- no 504 manifest exists;
- 504 remains NO-GO.

Do not interpret the existence of repair code or a green unit-test suite as a
504 certification.

---

# 17. Proposed next 504 price contract

This is the current next-action design, **not yet a certified fact**.

Problem:

- official IDX can prove an ACTIVE session and provide H/L/C/Volume while
  `OpenPrice` and `FirstTrade` are both non-positive;
- requiring a positive official opening field therefore blocks an otherwise
  strongly evidenced session;
- inventing Open is unacceptable.

Proposed solution:

Use a secondary historical provider only as a **cross-validated opening-price
witness**.

It must never define:

- whether the date is an official IDX session;
- security identity;
- common-share scope;
- ACTIVE state;
- official High;
- official Low;
- official Close;
- official Volume.

Secondary Open may be accepted only when all conditions hold:

1. exact ticker/date match;
2. secondary Open > 0;
3. secondary H/L/C > 0;
4. secondary High equals official IDX High;
5. secondary Low equals official IDX Low;
6. secondary Close equals official IDX Close;
7. secondary Open lies inside official `[Low, High]`.

Do not require secondary volume equality because vendor display units may be
scaled/rounded differently.

If accepted, canonical row should be:

- Open = cross-validated secondary Open
- High = official IDX High
- Low = official IDX Low
- Close = official IDX Close
- Volume = official IDX Volume

Provenance must preserve both source references and make it explicit that this is
an official IDX row with a secondary opening-price witness, not a pure secondary
provider bar.

Suggested provenance label:

- `IDX_STOCK_SUMMARY_WITH_SECONDARY_OPEN_WITNESS`

If secondary H/L/C disagree, mark an explicit cross-source mismatch and leave the
session unresolved.

The runtime repair should process FREN/MASA/MFIN independently so one ticker's
failure does not prevent diagnostics for the others.

A public historical provider such as Investing.com was identified as a candidate
for investigation because historical pages for these names appear to exist, but
that source is **not yet part of the certified repository contract**. Do not
bypass authentication, anti-bot controls, CAPTCHAs, or rate limits. If no normal
public access path is defensible, leave the rows unresolved.

---

# 18. 1260-session preparation branch

A separate preparation branch exists so 1260 architecture could be prepared
without contaminating the active 504 repair branch.

Branch:

- `data/idx-data-005-1260-prep`

Draft PR:

- PR #3
- title: `data: prepare guarded 1260-session historical expansion`

Preparation source lineage:

- branch was created from the 504-repair code era before a certified 504 PASS
- therefore it must be reconciled onto the eventual certified 504 head before
  any 1260 run

Prepared functionality includes:

- exact trailing official-session selection;
- insufficient-calendar fail-closed behavior;
- exact certified-baseline suffix validation;
- Stock Summary cache-pair coverage audit;
- pure backward additional-session planning;
- persisted preflight JSON;
- persisted exact additional-session CSV;
- regression tests.

Preflight invariant:

- the certified 504 session set must be the exact trailing suffix of the 1260
  target;
- target end date must align;
- if aligned, 1260 adds exactly 756 older official sessions.

Cache rule:

- a Stock Summary cache entry is reusable only when both the parsed snapshot and
  metadata file exist;
- a partial cache pair is treated as missing and should be refetched.

The prep branch has **not** performed a five-year market-data run and must never
be described as a 1260 PASS.

---

# 19. Full 1260 execution plan after 504 certifies

Only start this after a genuine 504 PASS with a verified 504 manifest.

1. preserve certified 43, 126, and 504 artifacts unchanged;
2. integrate/reconcile 1260-prep functionality onto the newest certified 504
   code head;
3. run full tests;
4. build at least 1260 official IDX sessions ending `2026-07-31`;
5. run fail-closed history preflight;
6. require 504 exact-suffix alignment;
7. audit Stock Summary cache;
8. fetch only missing/partial older sessions where possible;
9. rebuild PIT identity/delisting universe over the whole 1260 window;
10. discover candidates from identity plus official execution/tradability
    evidence;
11. reconcile historical identities generically;
12. preserve common-share security scope and authoritative non-common
    exclusions;
13. preserve curated legal-state evidence;
14. extend Yahoo raw prices backward with revision protection;
15. use official IDX price fallback for exact missing ACTIVE dates;
16. use any approved secondary-open witness only under the strict cross-source
    contract described above;
17. verify official stock split/reverse split history over the full exact window;
18. auto-verify raw price semantics;
19. run ladder `[504, 1260]`;
20. require 504 to reproduce PASS;
21. if 1260 FAILS, stop and preserve exact blockers;
22. do not automatically run 756 unless boundary localization is actually
    needed;
23. if 1260 PASSES, create a new ACTIVE-only 1260 model-safe panel and certified
    manifest, then verify hashes immediately.

---

# 20. Important security-specific decisions

## CNTB

- common share
- in scope
- listing date `2000-12-22`
- do not exclude because of illiquidity/unusual structure
- Regular-Market legal suspension evidence begins 2024-08-07
- 2026-07-30 and 2026-07-31 are SUSPENDED, not UNKNOWN and not inferred NO_TRADE

## CNTX

- preference share
- explicit non-common scope exclusion
- preserve evidence but exclude from common-stock certification/model universe
- exclusion is based on authoritative security type, not ticker hardcode

## HDTX / KPAS

- current-list omission demonstrated that the primary current-list endpoint is
  not exhaustive
- KSEI can provide identity/listing-origin evidence
- official IDX delisting evidence controls the ending listing interval
- KSEI Active does not override delisting/tradability

## FREN

- common share
- historical issuer/merger evidence used only after normal identity paths failed
- listed_from `2006-11-29`
- listed_to `2025-04-16`
- identity no longer the active blocker
- 196 ACTIVE-session price history is now exposed in the 504 window

## MASA

- current blocker is not identity
- 22 exact ACTIVE sessions have official IDX H/L/C/Volume but no positive
  OpenPrice/FirstTrade
- do not fabricate Open

## MFIN

- current blocker is historical price availability
- 249 pre-repair missing ACTIVE sessions
- last repair stopped before fully processing MFIN, so its official fallback
  yield must still be measured independently

---

# 21. Key modules and what they mean

This list is intended to help a new agent navigate the code quickly.

## Security/state foundation

- `src/idx_trade/security_master.py`
  - canonical identity/listing intervals
  - existence states
  - tradability interval/anchor canonicalization

- `src/idx_trade/states.py`
  - canonical state enums

- `src/idx_trade/coverage.py`
  - expected-vs-observed session coverage
  - identity-present vs zero-applicable-session semantics

- `src/idx_trade/data_gate.py`
  - hard fail-closed data-readiness blockers

## Official session/execution evidence

- `src/idx_trade/providers/idx_stock_summary.py`
  - official Stock Summary transport/parser
  - exact-session ACTIVE evidence
  - explicit-status evidence where available

- `src/idx_trade/execution_evidence.py`
  - direct session state evidence semantics

- `src/idx_trade/execution_backfill.py`
  - resumable Stock Summary backfill/cache

## Identity/scope

- `src/idx_trade/providers/ksei.py`
  - supplemental identity/type parser
  - bilingual localized date handling
  - common-vs-non-common reconciliation

- `src/idx_trade/curated_identity.py`
  - validated last-resort historical identity evidence

- `config/curated_security_identities.csv`
  - currently includes FREN historical identity evidence

- `src/idx_trade/full_universe.py`
  - evidence-discovered full PIT candidate universe
  - security-scope exclusions
  - full-market gate execution

## Legal tradability

- `src/idx_trade/providers/idx_tradability.py`
  - suspension/resumption evidence parsing

- `src/idx_trade/curated_tradability.py`
  - curated authoritative legal-state intervals

- `config/curated_tradability_intervals.csv`
  - includes the CNTB Regular-Market suspension evidence

- `src/idx_trade/tradability_anchor_reconstruction.py`
  - converts defensible anchors/transitions into bounded intervals

## Prices

- `src/idx_trade/providers/yahoo.py`
  - primary free OHLCV provider
  - `auto_adjust=False`

- `src/idx_trade/data.py`
  - canonical OHLCV
  - raw execution aliases
  - structural price-semantics verification

- `src/idx_trade/price_backfill.py`
  - batched resumable Yahoo backfill
  - revision-safe merging
  - official-session-bounded request windows

- `src/idx_trade/idx_price_fallback.py`
  - official Stock Summary OHLC fallback for exact missing ACTIVE dates

- `src/idx_trade/storage.py`
  - atomic writes
  - revision conflict checks

## Certified data products

- `src/idx_trade/market_snapshot.py`
  - ACTIVE-only model-safe panel

- `src/idx_trade/certification.py`
  - certified snapshot manifest creation and hash verification

- `src/idx_trade/history_ladder.py`
  - multi-horizon historical gate runner
  - per-horizon artifact persistence

- `src/idx_trade/history_preflight.py`
  - currently lives on the 1260 prep branch
  - exact trailing window and suffix/cache preflight

## Runbooks / continuity

- `docs/DATA_GATE_RUNBOOK.md`
- `docs/PROJECT_LEDGER.md`
- `docs/PROJECT_CONTEXT_MASTER.md` (this document)
- `docs/checkpoints/`
- `coordination/handoffs/`

---

# 22. Data-gate failure classes that matter

Known gate concepts include:

- `SECURITY_IDENTITY_UNRESOLVED`
- `SESSION_COVERAGE_INCOMPLETE`
- `PRICE_SEMANTICS_UNVERIFIED`

Other diagnostics/supporting concepts include:

- UNKNOWN tradability sessions;
- expected ACTIVE sessions missing a price;
- provider download errors;
- provider revision conflicts;
- provider bars on non-ACTIVE sessions (quarantine, not necessarily a failure);
- unresolved security type;
- curated-vs-primary conflict;
- legal-state contradiction;
- incomplete official calendar/source discovery.

A green unit-test suite is not equivalent to a green DATA GATE.

A green DATA GATE at a short horizon is not automatically proof of a longer
historical horizon.

---

# 23. Artifact and reproducibility policy

Certified artifacts are immutable baselines.

For every certified horizon:

- materialize a new model-safe panel;
- create a new manifest;
- hash material evidence/config/artifacts;
- immediately verify all hashes;
- record branch/commit/window/test/gate metrics;
- never silently rewrite a prior certified snapshot in place.

At minimum, long-history manifests should cover material inputs such as:

- official exchange-session set;
- session-source report;
- canonical security master;
- security-scope exclusions;
- Stock Summary/tradability anchors;
- merged legal tradability intervals;
- curated legal-state evidence;
- curated historical identity evidence where used;
- official split/reverse-split actions;
- model-safe price panel;
- full-universe gate summary;
- history ladder summary;
- fallback diagnostics/provenance when material.

Runtime market data and local caches should not be committed to Git.

Git should contain contracts, code, tests, lightweight evidence registries,
checkpoints, and handoffs—not huge generated market datasets.

---

# 24. Important branch / PR map

## `data/idx-data-002b`

- older foundation baseline
- base branch for review PR #2

## `data/idx-data-002c`

- active data-certification branch
- contains 43/126 certification logic and ongoing 504 repair work
- PR #2 head
- do not merge to main yet

## `data/idx-data-002c-codex-cache`

- auxiliary branch observed during runtime work
- do not assume it is canonical without checking latest branch history

## `data/idx-data-005-1260-prep`

- separate 1260 preparation branch
- PR #3 draft
- contains preflight/guardrails only
- must be reconciled with the future certified 504 head before execution

No automatic merge to `main` is authorized.

---

# 25. Key checkpoint commits and why they matter

This is not every commit. It is the minimal causal map.

- `2d10b520...`
  - DATA-002 bounded baseline; gate still blocked

- `7f9b708e2ea95e27b30769fa80dd517423790884`
  - DATA-002B; official July/session and corporate-action improvements

- `137f0cce508596d3247f033e4cfb181c0514b774`
  - zero-listed-session vs unresolved-identity semantics fixed
  - led to 35/35 adversarial PASS

- `57b482ad15852a65404348460a2a2a484497fde9`
  - original canonical project ledger introduced

- `0fac6c1afa8a7368c6b113b9f4ea95d570c5f9e7`
  - AGENTS continuity rules linked to ledger

- `f2bfc948490f7859a22307c973f27203334bbf75`
  - CNTB/CNTX scope/type resolution era

- `bef9bde1a7e539a0d1376da421dd0ba364215c63`
  - curated CNTB legal-state fix era
  - subsequent runtime reached 963/963 at 43 sessions

- `f8427efa7e6181e0c0522d6dd4f9445ff48de3b8`
  - 126-session certified runtime reported

- `ed13ee0812e8db21d580e922f4e346873aa7b3cd`
  - adaptive ladder policy era before 504 runtime

- `db7cce412dd211335f8ea7967d9ce1c1c722bc93`
  - 504 first failure review commit reported

- `5e6f6bd38a5af3ee11bca93a15f50fadf9515eb2`
  - FREN curated identity + official IDX price fallback code era

- `eee69814cdcb5ad0d5eebe9256bb9aff1ce81229`
  - latest known primary-branch checkpoint when this master context was created
  - records 504 repair stop on historical opening-price blocker

- `c14fdce7b04edf05c84a506d8b8ee38d04593021`
  - latest known 1260 prep branch checkpoint when this master context was created

Always verify current branch HEAD before acting; this list is historical
continuity, not permission to reset branches to old SHAs.

---

# 26. Do-not-repeat invariants

These are effectively project laws unless new authoritative evidence disproves
them.

1. Do not infer suspension from missing Yahoo rows.
2. Do not infer ACTIVE from Yahoo row presence.
3. Do not infer ACTIVE merely from LISTED existence.
4. Do not use one market-wide global initial ACTIVE state.
5. Do not propagate an exact anchor outside an uncertified causal evidence path.
6. Exact authoritative point evidence is valid on its exact session.
7. Do not subtract NonRegular metrics from Stock Summary regular metrics.
8. Do not let provider contamination override official IDX session truth.
9. Do not use current survivors to define historical universe membership.
10. Do not assume the IDX current-list endpoint is exhaustive for difficult
    historical/suspended names.
11. Do not interpret KSEI registry Active as current IDX listing/tradability.
12. Do not fail a known security solely because zero sessions are applicable.
13. Do not treat absent identity as resolved zero-applicability.
14. Do not silently overwrite Yahoo provider revisions.
15. Do not use vendor adjusted close as execution OHLC.
16. Do not scale to years before bounded semantics pass.
17. Do not tune a model to rescue a data-gate failure.
18. Do not merge the certification branch merely because unit tests pass.
19. Do not exclude an illiquid common share merely to make the gate green.
20. Do not include a preference/non-common share merely because Stock Summary
    emits evidence for it.
21. Do not hardcode ticker exclusions when authoritative type evidence can
    express the rule generically.
22. Do not convert Stock Summary row absence into NO_TRADE.
23. Do not fabricate an opening price when official OpenPrice/FirstTrade are
    absent/non-positive.
24. Do not let one ticker's fallback failure prevent independent diagnostics for
    other blocked tickers.
25. Do not treat a prepared 1260 branch as a certified five-year dataset.
26. Do not rewrite certified 43/126 artifacts while experimenting on 504/1260.
27. Do not start modelling until the historical data foundation is sufficiently
    deep and explicitly approved.

---

# 27. Process / agent operating conventions

The repo uses the parent ChatGPT conversation as a research/control plane and
Codex/local runtime primarily for execution-heavy work that requires the local
market-data artifacts or live network backfill.

Practical division of labor that has worked well:

- ChatGPT/main reviewer:
  - causal diagnosis;
  - source-semantics decisions;
  - architecture/data-contract changes;
  - bounded GitHub edits when possible;
  - deciding the next smallest experiment;

- Codex/local runtime:
  - local test execution;
  - large network/data backfills;
  - artifact materialization;
  - reproducing gate runs against local caches;
  - reporting exact runtime diagnostics.

Prefer direct repository fixes when they can be safely made through GitHub.
Use Codex prompts when the task genuinely depends on local runtime data/network
state rather than reflexively delegating every change.

For uncertain data work, prefer DIRECT or LIGHT orchestration. Use HEAVY only
when independent parallel work is genuinely valuable.

Never allow workers to silently change source authority, security scope, target
semantics, or gate thresholds just to achieve PASS.

---

# 28. Documentation hierarchy in a new chat

Recommended reading order:

1. `docs/PROJECT_CONTEXT_MASTER.md` — comprehensive bootstrap context.
2. `docs/PROJECT_LEDGER.md` — chronological causal ledger.
3. newest relevant file under `docs/checkpoints/` — latest runtime result.
4. `AGENTS.md` — repository operating/safety rules.
5. `docs/DATA_GATE_RUNBOOK.md` — operational data-gate workflow.
6. relevant `coordination/handoffs/` file if continuing a specific worker task.
7. inspect actual current branch HEAD/PR before editing.

If the master context and ledger differ on a runtime result, use the newer
explicitly validated checkpoint and update both continuity documents afterward.

Do not rely on a historical chat summary alone when the repo has a newer
checkpoint.

---

# 29. What to report after every material runtime

Every significant run should preserve and report:

- date/task/horizon;
- repository branch;
- exact commit/head;
- test count/result;
- exact official-session window;
- discovered securities before scope;
- security-scope exclusions;
- required common-stock count;
- unresolved identities;
- UNKNOWN session count;
- expected ACTIVE sessions missing prices;
- price semantics failures;
- provider download errors;
- provider revision conflicts;
- quarantined non-ACTIVE provider bars;
- blocker histogram;
- exact failed tickers and affected sessions;
- whether prior certified shorter horizon reproduced PASS;
- whether a model-safe panel was created;
- panel row/ticker count and SHA-256;
- whether a certified manifest was created;
- manifest SHA-256, artifact count, verification result;
- what did **not** run (model, validation phase, merge, trading);
- next smallest safe action.

When a failure is fixed, preserve the previous failure in the ledger. Do not
rewrite history into a story where the project was always correct.

---

# 30. Conditions for declaring Stage 1 substantially complete

Stage 1 should not be considered complete merely because 43 or 126 sessions are
clean.

A reasonable completion condition is:

- sufficiently deep historical window certified, ideally the intended 1260
  sessions if defensible;
- no unresolved identity/scope blockers in that certified universe;
- no UNKNOWN required sessions;
- no missing expected ACTIVE prices;
- raw-price semantics verified;
- technical corporate-action history verified;
- provider contamination quarantined;
- model-safe panel materialized;
- manifest valid and hashes verified;
- prior shorter certified horizon reproduces under the final code/data contract;
- source/fallback contracts documented;
- remaining unavoidable historical limitations explicitly bounded rather than
  guessed away.

If five years encounter a genuine structural source boundary that cannot be
resolved defensibly, the project may explicitly choose the longest clean horizon
rather than fabricate five years. That decision should be evidence-driven and
recorded.

---

# 31. What happens immediately after Stage 1

Do **not** jump straight into a complicated ML model.

Next sequence should be roughly:

1. freeze research specification;
2. define candidate setup unit `security x signal_date` precisely;
3. freeze support/resistance representation;
4. freeze entry/stop/target and outcome rules;
5. define unresolved/matured label treatment;
6. freeze forward horizon;
7. define benchmark and regime variables;
8. define chronological walk-forward folds and purge/embargo;
9. define calibration and final holdout separation;
10. implement simple baselines;
11. then compare richer features/models.

The data-foundation contracts should become inputs to model research, not be
casually redesigned for each model attempt.

---

# 32. Future model concepts already discussed but not frozen

These are conceptual goals only. Do not treat them as implemented specification.

Potential system outputs:

- support and resistance levels/zones;
- setup classification;
- suggested entry region;
- invalidation/stop;
- target(s);
- risk/reward;
- `P(TP before SL)`;
- expected realized R;
- Opportunity/Setup Score 0-100;
- Entry Quality Score;
- Estimate Reliability;
- later fractional Kelly sizing;
- later Monte Carlo portfolio/trade scenario analysis.

Potential distinctions:

- Setup Quality can describe geometry/context;
- Probability can describe event likelihood;
- Expected R can combine probability and payoff;
- Reliability can describe confidence in the estimate/calibration regime;
- a user-facing Opportunity Score can combine interpretable components but must
  not masquerade as a probability.

None of the exact formulas/weights/labels are frozen yet.

---

# 33. Glossary

**PIT / point-in-time**
: Information available/valid as of the historical date, without current-survivor
  leakage.

**ACTIVE**
: Authoritative evidence of Regular-Market trading on the exact session under
  the current execution-evidence contract.

**NO_TRADE**
: Authoritative exact-session observation of zero Regular-Market trade metrics;
  not the same thing as legal suspension.

**SUSPENDED**
: Legal/market state established by authoritative evidence; not inferred from
  provider absence.

**UNKNOWN**
: Evidence is insufficient to classify safely. Hard fail where state is required.

**Provider contamination**
: Vendor emitted a bar on a session that official point-in-time state says is
  non-ACTIVE. Preserve raw, quarantine from model-safe research.

**Model-safe panel**
: Canonical common-stock ACTIVE-only execution-price dataset after the data gate.

**Certified manifest**
: Hash-based reproducibility record tying code/window/material artifacts to a
  certified snapshot.

**Adversarial catalog**
: 35 stress-test securities used to break semantics before scaling; not the
  model universe.

**Security scope exclusion**
: Authoritative reason a discovered security is outside the initial common-share
  research universe, e.g. preference shares.

**Curated evidence**
: Small, auditable registry of authoritative evidence used only when automatic
  source surfaces fail. It must not be a hidden ticker-whitelist/blacklist.

---

# 34. Final new-chat bootstrap instruction

When continuing this project in a new ChatGPT/Codex session, use this instruction:

> Read `AGENTS.md`, `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`,
> and the newest relevant `docs/checkpoints/*` before doing any material work.
> Verify the actual current branch and HEAD. Preserve all certified 43/126
> artifacts. Strict 504 remains uncertified because FREN/MASA/MFIN still lack
> defensible historical opening-price evidence. The exact 1260-session
> research-feasibility evaluation ending `2026-07-31` was run and is
> **NO-GO / STOP**: strict 126 passes, strict 504 fails, strict 1260 fails,
> and generic exclusions yield only 93.667% ticker coverage. Read the newest
> 1260 checkpoint, including
> `docs/checkpoints/2026-08-09_1260_OPEN_GAP_DOMINANT_DIAGNOSTIC.md`, before any
> further historical work. No modelling, IDX-VAL-002, main merge, paper
> trading, or live trading is authorized yet.

If later checkpoints supersede this exact blocker, update this master document
immediately so a future chat never starts from stale assumptions.

---

# 35. IDXData3 Stock_First_Trx audit - target retention unavailable

Date: 2026-08-09. Audit started from `data/idx-data-002c` at
`ffca7c51312ef96ce786913541c36a55edd4588c`.

The exact remaining historical ACTIVE-price requirement was regenerated from
the preserved post-official-fallback evidence rather than copied from the
previous headline counts:

- FREN: 196 sessions;
- MASA: 22 sessions;
- MFIN: 172 sessions;
- total: 390 ticker/date rows;
- unique target dates: 233;
- target date range: `2024-06-21` through `2025-09-19`.

Normal public retrieval of every unique target date was attempted using the
expected `SO[YYMMDD].zip` naming convention. The `www` hostname failed normal
TLS hostname verification, so the official canonical hostname was also tested
without disabling certificate verification or bypassing access controls. The
initial canonical pass returned 12 HTTP 404 responses and 221 HTTP 503
responses. After a controlled retry, all 221 transient responses returned HTTP
404. Final direct-file classification is therefore 233 `FILE_NOT_FOUND`, zero
`FILE_AVAILABLE`, and zero target archive parse/schema results.

The public official directory listing was readable and advertised 133 SO
archives, but its observed range was only `SO200203.zip` through
`SO200819.zip` (2020-02-03 through 2020-08-19). None of the 233 target dates
was advertised. An available retention-era sample, `SO200819.zip`, contained
one legacy fixed-width DBF member with 657 rows and fields
`STK_CDAT`, `STK_CODE`, `STK_NAME`, and `STK_FIRST`. It is outside the target
window and does not expose the modern H/L/C/volume/frequency fields needed for
the requested cross-check.

Per-ticker target resolution was zero official opening rows and zero remaining
target archives for every ticker. All 390 rows are classified
`SO_FILE_MISSING`; no `OFFICIAL_OPEN_VERIFIED`, ticker-row, board, or H/L/C
conflict classification can be made without a target archive.

Decision: stop. Do not implement a new SO provider/parser, do not mutate Yahoo
or official Stock Summary artifacts, do not rerun the 504/126 ladder, and do not
start 252 or 1260. The audit evidence is retained in the external runtime
workspace under the logical name `idxdata3_open_audit_20260809_retry`; it is
not committed to Git.

---

# 36. 1260-session research-feasibility evaluation - NO-GO

Date: 2026-08-09. The exact trailing official-session window was evaluated in
the external workspace
`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809`.
It runs from `2021-04-29` through `2026-07-31` and contains exactly 1260 IDX
exchange sessions. The existing certified 43- and 126-session artifacts remain
unchanged. The 504 session set is the exact trailing suffix, but strict 504 is
still not certified.

Full pytest passed: 157 tests, exit 0, with three existing pandas warnings.
The official Stock Summary evidence is complete for all 1260 sessions with
982,398 ACTIVE regular-market anchors, 121,666 NO_TRADE anchors, 1,104,064
merged point rows, and zero unresolved metrics. The rebuilt PIT master has 980
pre-scope discoveries, one preserved CNTX non-common-share exclusion, 979
required common stocks, and zero unresolved required identities. The official
split/reverse query is complete: 55 stock-split rows, 52 tickers, and no
reverse-stock rows in the target window.

The strict regression/evaluation is:

| horizon | window | required | passed | failed | UNKNOWN | missing ACTIVE prices | quarantined bars |
|---|---|---:|---:|---:|---:|---:|---:|
| 126 | 2026-01-15 -> 2026-07-31 | 963 | 963 | 0 | 0 | 0 | 2,672 |
| 504 | 2024-06-21 -> 2026-07-31 | 976 | 973 | 3 | 2 | 390 | 22,400 |
| 1260 | 2021-04-29 -> 2026-07-31 | 979 | 917 | 62 | 572 | 6,716 | 57,808 |

The exact 1260 strict failures are recorded in
`docs/checkpoints/2026-08-09_1260_RESEARCH_FEASIBILITY_NO_GO.md` and the
external gate CSV. Their blocker histogram is 62
`SESSION_COVERAGE_INCOMPLETE` and 15 `PRICE_SEMANTICS_UNVERIFIED`.

For research feasibility, the 62 blocked securities were excluded only through
the generic `RESEARCH_UNSUPPORTED_SECURITY` registry after approved source
exhaustion. This produced 917/979 = 93.667% ticker coverage, below the 98%
minimum. Active-row coverage was 99.316% before exclusions and 100% after them,
but known excluded regular-market value was 2.373%; sector bias was not
computable from the current security master. The decision is therefore
**NO-GO / STOP**, not a certified research dataset.

No 1260 panel or manifest exists. Do not model, run `IDX-VAL-002`, start 252,
merge to `main`, or treat the research exclusions as permission to weaken the
strict gate. The detailed runtime summary is:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\research_feasibility_report.json`

---

# 37. Bounded 1260 Open-vs-HLC diagnostic - OPEN-GAP DOMINANT

Date: 2026-08-09. This diagnostic reused the preserved strict 1260 runtime
evidence at
`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\`
and did not refetch or rewrite provider artifacts. Four bounded local read-only
cache workers were used for date-partitioned processing.

Full pytest passed: 157 tests, exit 0, with three existing pandas warnings.
The preserved unresolved set contains 6,716 ticker/session pairs over 989
dates, with all 989 payload dates available.

The exact decomposition is 6,716 `OPEN_ONLY_MISSING` (100.000%), zero
`HLC_MISSING`, zero `OPEN_AND_HLC_MISSING`, and zero `OTHER`. All unresolved
pairs have valid official ACTIVE Regular-Market metrics and valid High, Low,
and Close; no Open was synthesized. The affected known Regular-Market Value
is 66,890,258,565,100. Year totals are 2021: 2,316 rows /
37,835,732,109,000; 2022: 2,541 / 21,987,421,358,300; 2023: 1,172 /
4,641,507,805,500; 2024: 544 / 2,302,577,000,300; and 2025: 143 /
123,020,292,000.

Under a hypothetical signal-research HLCV contract, all 979 required
common-stock tickers and all 981,940 required-scope ACTIVE rows are eligible;
known Regular-Market Value coverage is 100.000%, and no unsupported ticker or
top-50/top-100/top-200/delisted/IPO/corporate-action unsupported cluster
remains. This is a diagnostic result, not a production contract change.

The strict execution-grade contract remains unchanged: Open is still required,
strict 126 remains PASS, and strict 504/1260 remain FAIL/NO-GO. No panel,
manifest, modelling, `IDX-VAL-002`, 252/1260 rerun, or main merge was started.
See `docs/checkpoints/2026-08-09_1260_OPEN_GAP_DOMINANT_DIAGNOSTIC.md` for the
full artifact paths and review decision.

---

# 38. Final UNKNOWN diagnostic and SIGNAL_RESEARCH_1260 GO

Date: 2026-08-09. The final bounded diagnostic reused the exact 1260 runtime
and preserved strict execution-grade artifacts. Full pytest passed with 157
tests and 0 failures; three pre-existing pandas warnings remain non-blocking.

The exact 572 strict UNKNOWN pairs are 100% `UNKNOWN_NO_EXECUTION_EVIDENCE`:
there are zero rows with positive official execution evidence, zero provider
bars, zero valid H/L/C from an approved source, and zero explicit legal
suspension-boundary cases. All 572 are listed, in-scope common-share rows. The
8 affected tickers are ADCP, FINN, GRPH, KETR, MASA, MFIN, RMBA, and TURI.
The UNKNOWN/expected-ACTIVE intersection is mechanically empty (0 rows).

The signal-research contract is now explicit and separate from strict
execution-grade OHLCV:

- required common stocks: 979;
- eligible common stocks: 979/979;
- expected and eligible ACTIVE rows: 981,940 / 981,940;
- ACTIVE-row coverage: 100.000%;
- known Regular-Market Value coverage: 100.000%;
- remaining unsupported securities: 0;
- Open: nullable, explicit status, never synthesized;
- UNKNOWN: excluded from all signal features, labels, liquidity metrics, and
  execution paths.

The signal panel contains 981,940 rows across 945 tickers with ACTIVE rows;
34 required tickers have zero expected ACTIVE sessions. It has 446,843 null
Open rows (45.5061409047%) and zero null H/L/C/Volume rows. The panel and the
15-artifact signal-research manifest are external runtime outputs documented in
`docs/checkpoints/2026-08-09_SIGNAL_RESEARCH_1260_GO.md`.

Permanent status:

`STRICT EXECUTION-GRADE 1260: FAIL`
`SIGNAL-RESEARCH 1260: GO`

---

## 22. STAGE-2 research specification and validation design - GO

Date: 2026-08-09 (Asia/Jakarta). Source branch: `data/idx-data-002c` at
`057d7c2df57ebe259f8b93642128e91ad294b146` before the Stage-2 documentation
commit. No new market data, raw-artifact rewrite, model, `IDX-VAL-002`, or
main merge was performed.

The DATA FOUNDATION for the separate signal-research layer is now complete,
and Stage 2 freezes what the first modelling cycle would test and how it would
be validated. The immutable input remains the 1,260-session
`SIGNAL_RESEARCH_HLCV` panel with 981,940 ACTIVE rows and the previously
verified panel/manifest hashes. Strict execution-grade 1260 remains FAIL; the
signal layer does not weaken or replace it.

The frozen Stage-2 contract is:

- question: causal technical/market structure after close at `t` versus
  favorable/adverse future excursion;
- reference: `SIGNAL_REFERENCE_CLOSE = Close_t`, never a fill claim;
- primary label: first-touch barrier, H=10, `RR=1.5`, `k_sl=1.0`, with H=5/H=20
  sensitivity only;
- ambiguity: `AMBIGUOUS_SAME_BAR` is explicit and excluded from primary binary
  calibration, never guessed as WIN/LOSS;
- primary universe: causal broad liquid rule using trailing 60-session value,
  at least 20 observations, and IDR 1 billion median value;
- split: development sessions 1-1008 (`2021-04-29 -> 2025-07-14`) and locked
  holdout sessions 1009-1260 (`2025-07-15 -> 2026-07-31`);
- folds: three exact expanding, date-grouped folds with 20-session purge and
  embargo gaps;
- primary metric: mean fold PR-AUC against frozen base-rate and momentum
  baselines, with calibration, excursion, and coverage metrics reported;
- Open: never required by primary V1 features and never synthesized.

The required threat model covers pivot/SR lookahead, rolling off-by-one,
survivorship, corporate-action and provider-revision leakage, random split and
overlapping labels, same-date contamination, future preprocessing, holdout
feature/threshold/calibration selection, future liquidity, same-bar ambiguity,
nullable Open, provider contamination, UNKNOWN collapse, horizon truncation,
delisting/suspension interruption, prevalence leakage, and semantic collapse
of probability/Opportunity Score/reliability.

An independent read-only adversarial review of the three Stage-2 documents was
completed. The review found no material unresolved issue after the fold-boundary
consistency correction. Decision: **STAGE2_SPEC_GO**. The next authorized
phase is Stage 3 - Label / Feature Pipeline + Baseline Models, but Stage 3 is
not started here. The final holdout must remain untouched until that phase is
separately approved.

No strict 1260 PASS is implied. The next phase is Stage 2 research
specification and validation design; modelling remains prohibited until that
phase is separately approved.

---

## 23. STAGE-3 development runtime - advancement rule met

Date: 2026-08-09 (Asia/Jakarta). Branch: `research/idx-stage3-v1`, code head
`4c484b087aff592234dbe9905213e9d83b2f2611`.

The frozen Stage-3 development runner executed once against the existing
immutable signal-research artifacts. Full pytest passed: **184 passed, 0
failed**, with three existing pandas/NumPy deprecation warnings. The panel hash
and research manifest hash matched exactly; manifest verification was
`valid=true`, 15/15. Runtime admission confirmed maximum signal session 942,
maximum future source session 962, locked holdout start 1009, and
`holdout_outcome_accessed=false`.

The development output is external at
`D:\Documents\Project\idx-trade-data-gate-20260808v\stage3_development_v1_20260809`.
It contains 712,325 full valid/history candidate rows, 692,648
history-qualified rows, 244,761 primary broad-liquid rows, and 208,375 H10
resolved binary model rows. H10 labels were 197,910 `TP_FIRST`, 315,049
`SL_FIRST`, 6,974 `AMBIGUOUS_SAME_BAR`, 107,189 `NO_BARRIER_HIT`, 40,463
`UNRESOLVED_PATH`, 44,740 `INVALID_BARRIER`, and zero
`UNRESOLVED_HORIZON_END`.

The pre-registered advancement rule was met:

- `logistic_compact`: F2 and F3;
- `hist_gradient_boosting`: F1, F2, and F3.

This is development OOF evidence only, not final OOS performance. The locked
holdout was not read. No Stage 4, `IDX-VAL-002`, model deployment, or merge to
main was started. The next safe action is independent ChatGPT review of the
runtime result, with particular attention to weak pooled probability quality
despite PR-AUC advancement and to the remaining strict execution-grade 1260
FAIL status.

## 24. STAGE-4 development runtime - ranking GO, calibration blocked

Date: 2026-08-09 (Asia/Jakarta). Branch: `research/idx-stage4-v1`. Code head:
`ad2098c7932a187555ac7c9ec8b77372bdf622e5`.

The frozen Stage-4 V1 runner executed once using only the immutable Stage-3
development artifacts and the exact 1,260-session official calendar. The
numerical environment matched Stage 3 exactly: Python 3.13.5, NumPy 2.4.2,
pandas 2.3.3, pyarrow 23.0.1, scikit-learn 1.8.0, seed 42. Full pytest
passed **192/192** with three pre-existing pandas/NumPy warnings. Input hashes
matched; the locked holdout starts at session 1009 / `2025-07-15`; and
`holdout_outcome_accessed=false`.

Automatic status: **STAGE4_RANKING_GO_CALIBRATION_BLOCKED**. HGB beat the
base-rate and momentum baselines on PR-AUC in F1/F2/F3, reproducing the
Stage-3 advancement rule. Within-date score quintiles also had Q5 > Q1 in all
three folds. The frozen calibrator-selection rule selected **ISOTONIC** by
lowest pooled OOF Brier, but the calibration-readiness gate failed: pooled
Brier and weighted ECE were worse than base-rate, and prevalence-gap
improvement occurred in only one of three folds. The runtime output and full
ablation, quintile, regime, calibration, and artifact-hash record are in
`docs/checkpoints/2026-08-09_STAGE4_DEVELOPMENT_RUNTIME.md`.

No holdout inspection, Stage 5, `IDX-VAL-002`, modelling, external data use,
or merge to `main` was performed. Stop for independent ChatGPT review.

## 25. STAGE-5 ranking-only locked holdout - FAIL

Date: 2026-08-09 (Asia-Jakarta). Branch:
`research/idx-stage5-ranking-holdout-v1`. Code head:
`05c2bb549b446da374c13937a41aa6732cf71ec0`.

The frozen Stage-5 V1 ranking-only runtime executed exactly once. Full pytest
passed **206/206** with three existing pandas FutureWarnings. All five frozen
input hashes matched and the research manifest verified `valid=true`, 15/15.
The required environment was Python 3.13.5, NumPy 2.4.2, pandas 2.3.3,
pyarrow 23.0.1, and scikit-learn 1.8.0.

The final models were frozen at signal session 988 before any holdout labels
were read. The primary H10 holdout covered sessions 1009-1250
(`2025-07-15` to `2026-07-17`), with 71,420 resolved primary rows and
positive rate 0.4071688603. HGB produced PR-AUC 0.4073793720 and ROC-AUC
0.4948433255, versus base-rate PR-AUC 0.4071688603 and ROC-AUC 0.5.
Although HGB beat the base-rate PR-AUC by 0.0002105118 and Q5 exceeded Q1
by 0.0108405246, it failed the ROC-AUC gate. Temporal stability also failed:
HOLDOUT_A PR-AUC was 0.4866372564 versus base 0.4647456292, while HOLDOUT_B
PR-AUC was 0.3471254020 versus base 0.3577062238; HOLDOUT_B Q5-Q1 was
-0.0198933303.

Automatic result: **`STAGE5_RANKING_HOLDOUT_FAIL`**. H5/H20 sensitivity was
reported but cannot rescue the primary H10 decision. The holdout access
markers were written before outcome access, so the locked holdout is now
permanently consumed for `RANKING_V1_ONLY` and no Stage-5 retry is permitted.
Probability V1 remains **`PROBABILITY_V1_NOT_READY_DEFERRED`**. No Stage 6,
Probability V2, `IDX-VAL-002`, execution-PnL claim, paper/live trading, or
main merge was started.

Runtime artifacts and exact hashes are recorded in
`docs/checkpoints/2026-08-09_STAGE5_RANKING_HOLDOUT_RUNTIME.md` and remain
outside Git. Next action is independent ChatGPT review of the failed
ranking-only result; any future Probability V2 validation must use fresh
forward data strictly after `2026-07-31`.

## 26. Bounded Stage-5 post-mortem - descriptive diagnostic complete

Date: 2026-08-09 (Asia/Jakarta). Branch:
`research/idx-stage5-postmortem-v1`. Substantive diagnostic code commit:
`f51f9778a6657b52752d2423dbde8499c693bf70`.

The exact bounded post-mortem runner completed once with status
**`DESCRIPTIVE_DIAGNOSTIC_COMPLETE`**. Full pytest passed **211/211** with
three existing pandas FutureWarnings. The exact Stage-5 panel, predictions,
summary, official calendar, and security master matched their frozen hashes.
The consumed-holdout guards remained valid, and no source/test/model artifact
was changed.

The six fixed blocks showed positive HGB PR-AUC deltas in A1/A2/A3, near-zero
B1, then negative deltas in B2/B3. The largest feature distribution shifts by
absolute SMD were `atr14_over_close` 0.5583958847,
`security_age_sessions_exact` 0.5537919781, `distance_low_60_atr`
-0.4935691423, `observed_session_count` 0.3901573723, and `close_return_20`
-0.2276565042. Factual feature Q5-Q1 sign reversals were
`atr14_over_close`, `log_regular_value_relative_20`,
`observed_session_count`, `relative_volume_20`, and
`security_age_sessions_exact`.

The full primary-liquid A/B comparison showed lower breadth and returns,
higher volatility, lower close position, lower relative volume, and lower
relative Regular-Market Value in B. The HGB top-decile TP rate/lift was
0.5205847255 / +0.0558390964 in A and 0.3564280216 / -0.0012782023 in B.
These are descriptive observations only; no feature, regime, subgroup, or
top-decile cutoff is validated by this post-mortem.

All external artifacts and hashes are recorded in
`docs/checkpoints/2026-08-09_STAGE5_POSTMORTEM_RUNTIME.md`. The post-mortem
summary SHA-256 is
`9f6c60ea3602673ad500adc99def8b1ecdfb7006c47c750dd52b2cf89984cad1`.

Ranking V1 remains a failed benchmark, the holdout remains consumed, and
Probability V1 remains deferred. No V2, Stage 6, `IDX-VAL-002`, execution-PnL
claim, paper/live trading, or main merge was started. Stop for independent
ChatGPT interpretation.
