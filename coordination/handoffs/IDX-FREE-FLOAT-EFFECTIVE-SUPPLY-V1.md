# IDX Free Float / Effective Supply V1 — Handoff

Status: `SOURCE_PREPARED_BOUNDED_LIVE_AUDIT_NEXT`
Branch: `data/idx-free-float-effective-supply-v1`

## Objective

Establish defensible ownership/free-float source acquisition for later liquidity, volume and Foreign Flow research. Preserve observable ownership facts first; do not infer a historical `true free float` or effective-supply score in this lane.

## Prepared source adapters

### IDX Company Profile Detail

Implementation: `src/idx_trade/providers/idx_ownership.py`

- current named/controller holder snapshot;
- raw response bytes + SHA-256 + observation timestamps;
- strict `PemegangSaham` parsing;
- no historical backdating;
- no free-float complement inference.

### Public >=1% ownership snapshot parser

Implementation: `src/idx_trade/providers/idx_ownership.py::parse_gt1_ownership_csv`

- embedded `DATE` is authoritative, filename is ignored for as-of semantics;
- supports `INVESTOR_TYPE` and `INVESTOR_CLASSIFICATION` schema aliases;
- preserves named holder, investor classification, local/foreign, nationality, domicile, scripless/scrip/total shares and percentage;
- fails closed on mixed snapshot dates and holding reconciliation mismatch;
- output is concentration evidence only.

### KSEI holding-composition ZIP capture

Implementation: `src/idx_trade/providers/ksei_ownership.py`

- official dated `BalanceposEfekYYYYMMDD.zip` URL constructor;
- exact ZIP bytes + SHA-256 + observation timestamps;
- non-ZIP responses rejected;
- member/schema parsing intentionally deferred pending live byte inspection.

## Reference implementation reviewed

`nichsedge/idx-bei@75d6c0f74fa360d225794c70c383348977de6798`

Relevant files:

- `python/src/idx/scrapers/company.py`
- `python/src/idx/core/client.py`
- `data/1%ownership-2025-03-04.csv`

Important caveat: the public mirror filename is stale/misleading for as-of semantics; sampled embedded rows show `DATE=27-Feb-2026`. Never derive snapshot date from that mirror filename.

## Local bounded audit required next

Use a local checkout/worktree because this requires live network access and preservation of official raw bytes.

Suggested adversarial ticker set:

- `DCII` — concentrated / supply-tight motivation case;
- `BBCA` — liquid large-cap control;
- one current illiquid or newer listed control from the canonical security master;
- optionally `WBSA` / `RLCO` only if they are valid/listed in the current master at probe time.

Tasks:

1. Fetch Company Profile Detail for the bounded ticker set.
2. Store raw JSON bytes externally, never bulk data in Git.
3. Record URL, params, `retrieval_started_at_utc`, `observed_available_at_utc`, SHA-256 and parsed row counts.
4. Inventory the entire payload schema and explicitly report whether IDX exposes any direct statutory free-float field. Do not infer one if absent.
5. Download official KSEI holding-composition ZIPs for a bounded set: `2026-02-27`, one middle 2026 month, and latest currently published snapshot from the official archive.
6. Inspect ZIP member names, compression, encoding, columns, row counts, date semantics and whether files are aggregate composition or named-holder level.
7. Locate at least one official IDX monthly >=1% ownership announcement attachment after the 2026-03-03 launch. Preserve attachment bytes/hash and compare schema to the mirror parser contract.
8. Probe older official archive/announcement retention only enough to establish historical-depth boundaries. Do not bulk backfill yet.
9. Add focused live-fixture/schema tests from sanitized structural fixtures; do not commit raw personal/account data or bulk official datasets.
10. Run focused tests, then `python -m pytest -q`, and `git diff --check`.

## Required output

Report:

- final branch HEAD / clean-sync state;
- focused + full pytest counts;
- actual Company Profile schema for the bounded tickers;
- whether an explicit official reported-free-float field exists;
- KSEI ZIP member/schema findings and exact snapshot dates tested;
- official >=1% attachment locator/schema/hash findings;
- source historical-depth/retention boundary;
- any schema drift between mirror and official bytes;
- exact raw artifact root and manifest hashes;
- verdict: whether the data foundation is ready for a separate ownership-concentration/effective-supply contract.

## Hard boundaries

Do **not**:

- calculate `true_free_float_pct` or `effective_free_float_pct`;
- subtract all >=1% holders from reported free float;
- classify all >=1% holders as locked;
- design a supply-tightness score;
- integrate with Foreign Flow V2 or volume model features;
- access outcomes/labels or fit/score any model;
- modify Financial PIT, Corporate Action, O2, TradingView, or AKSes lanes;
- bulk-acquire historical ownership before the bounded source audit is reviewed.
