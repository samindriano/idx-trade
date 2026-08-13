# Corporate Action PIT Source Audit — Preparation

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/corporate-action-pit-source-audit-v1`
Status: `SOURCE_AUDIT_PREPARED_NOT_YET_BULK_ACQUIRED`

## Scope boundary

This lane prepares a point-in-time corporate-action source contract for IDX equities, targeting roughly 2018–2026 where defensible historical evidence exists.

It is intentionally separate from the active Financial PIT parser remediation and from the separately owned Foreign Flow lane. No foreign-flow code/data, financial-fact parser, model, protected outcome, or canonical market panel is touched here.

No bulk corporate-action backfill is authorized by this checkpoint.

## Repository lineage already available

### 1. Direct IDX endpoint discovery

Accepted discovery branch:

`data/idx-direct-endpoint-audit-v1`

The bounded official IDX probe validated:

`ListingActivity/GetIssuedHistory`

Observed action categories and first-page remote totals in the accepted probe:

| caType | recordsTotal in bounded probe | immediate value |
|---|---:|---|
| `hmetd` | 241 | rights/share issuance candidate ledger |
| `PrivatePlacement` | 8 | private-placement candidate ledger |
| `stockSplit` | 199 | stock-split candidate ledger |
| `reverseStock` | 5 | reverse-split candidate ledger |
| `BuybackSaham` | 1 | buyback candidate ledger |
| `ipo` | 438 | listing/share-state anchor candidate |
| `companyListing` | 149 | additional listing/share-state candidate |
| `partialDelisting` | 35 | share-state reduction candidate |

Every observed row exposed only:

`id`, `KodeEmiten`, `TanggalPencatatan`, `JenisTindakan`, `JumlahSaham`, `JumlahSahamSetelahTindakan`.

The accepted endpoint audit explicitly classified this endpoint as useful for candidate events/share-count changes, but **not sufficient as a standalone PIT shares-outstanding or publication-timing source**. `TanggalPencatatan` is the sole event-time field and cannot automatically be relabeled as announcement/knowledge time or a generic effective date.

### 2. Existing corporate-action provider prototype

A non-main historical branch already contains:

`data/financial-pit-adapter-census-v1:src/idx_trade/providers/idx_corporate_actions.py`

and tests at:

`data/financial-pit-adapter-census-v1:tests/test_idx_corporate_actions_provider.py`

Git history pins the implementation lineage to:

- `c8c43ac66bd3215465978ac5f39d0b72feec8a3e` — `feat(data): add official IDX fallback and gate semantics`;
- `14dd51796d60131ef25b318bf2258ad3dd873175` — `fix(data): derive IDX split ratios from official share totals`.

So this is not a newly discovered idea; it is an older data-gate component that later branches inherited but current `main` no longer contains.

The prototype already implements:

- official `GetIssuedHistory` URL construction;
- response-shape and incomplete-page checks;
- ticker normalization;
- `stockSplit` / `reverseStock` parsing only;
- share-count and split-ratio derivation;
- Yahoo split-event cross-checking as a non-authoritative witness.

Important: this code is **not present on current `main`**. It must not simply be copied and promoted unchanged.

Two semantics in the prototype require re-validation before reuse:

1. it currently aliases `TanggalPencatatan` into both `listing_date` and `effective_date`;
2. it assumes directional arithmetic for `JumlahSaham` and `JumlahSahamSetelahTindakan` when deriving old/new share counts.

Those assumptions are stronger than the accepted direct-endpoint evidence and therefore remain provisional until independently grounded.

### 3. Existing announcement/publication chain

The Financial PIT lineage has already validated a reusable direct-IDX announcement transport pattern:

`ListedCompany/GetAnnouncement`

with fail-closed pagination, duplicate rejection, exact attachment matching, immutable capture, and explicit parsing of `TglPengumuman` as Asia/Jakarta when the source timestamp is naive.

The corporate-action lane should reuse the **transport/provenance pattern**, not the Financial PIT fact parser or statement-scope logic.

## Newly identified official KSEI layer

Official KSEI exposes a materially richer corporate-action layer than `GetIssuedHistory` alone.

Relevant public sources identified during preparation:

- security-level registered-share pages under `https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}`;
- corporate-action schedule pages under `https://web.ksei.co.id/publications/corporate-action-schedules/...`.

Observed KSEI security pages expose a corporate-action table with fields including:

- `Type of CA`;
- `Ratio`;
- `Cum Date`;
- `Record Date`;
- `Distribution Date`;
- `Status`.

The same issuer history can contain multiple action families and long historical depth. Examples observed in official pages include Cash Dividend, Stock Dividend, Right Distribution, Proxy Voting, and status values including Active/Cancelled.

KSEI also exposes dedicated schedule families including:

- cash dividend;
- share bonus;
- rights distribution;
- merger/acquisition/stock split/reverse stock;
- mixed cash + stock dividend.

The schedule pages expose official KSEI reference numbers, subjects, and document dates, and visibly include revision/change notices. This is important for a version-aware PIT event ledger.

### `nichsedge/ksei-mcp` assessment

The user supplied `nichsedge/ksei-mcp` because it is maintained by the same author as the successful IDX-BEI client. The repository was inspected before use.

It is **not** a scraper for the public KSEI registered-security or corporate-action schedule pages. Its `KSEIClient` targets the credentialed AKSes service at `https://akses.ksei.co.id/service`, authenticates with `KSEI_USERNAME` and `KSEI_PASSWORD`, and exposes private portfolio/account methods such as portfolio summary, cash, equity, mutual fund, bond and global identity.

Therefore:

- do not request or store the user's AKSes credentials for this corporate-action lane;
- do not add `ksei-mcp` as a dependency merely because it shares an author with `idx-bei`;
- public Corporate Action data should be retrieved from `web.ksei.co.id` without private-account authentication;
- implementation ideas from the repository may be inspected, but it is not evidence for Corporate Action completeness/PIT semantics.

## Proposed source hierarchy

The first audit should test a three-layer official-source chain rather than treating one endpoint as canonical by itself.

### Layer A — IDX `GetIssuedHistory`

Use as an official candidate-event/share-count ledger for listing/share-state actions.

Do not use it alone to assert knowledge time, publication time, or complete corporate-action semantics.

### Layer B — KSEI corporate-action history/schedules

Use as the leading candidate source for operational corporate-action fields such as ratios, cum/record/distribution dates, action status, and revision/cancellation evidence.

KSEI event dates must remain source-specific fields. Do not synthesize an `effective_date` until the event family defines what that means.

### Layer C — IDX announcements

Use as the leading candidate source for issuer publication/knowledge-time provenance and attachment evidence where a defensible exact linkage can be established.

The Financial PIT announcement-chain implementation can provide design patterns for pagination, immutable captures, revision preservation, and timestamp handling.

## Event model to audit

Do not collapse all corporate actions into one date or one ratio.

Candidate normalized event record:

- `ticker`
- `event_family`
- `event_subtype`
- `source_event_id`
- `source_status`
- `announcement_at_utc` / `knowledge_at_utc`
- `source_document_date`
- `cum_date`
- `record_date`
- `distribution_date`
- `listing_action_date`
- `ratio_numerator`
- `ratio_denominator`
- `cash_amount`
- `currency`
- `action_shares`
- `total_shares_after_action`
- `source_identity`
- `source_ref`
- `raw_sha256`
- `observed_at_utc`
- `supersedes_event_id` / revision lineage

Fields that are unavailable for an action family must remain null rather than inferred.

## Event families

The audit should distinguish at least:

### Price/share normalization events

- stock split;
- reverse stock split;
- stock dividend;
- bonus shares.

### Dilution/share-state events

- HMETD / rights distribution;
- private placement;
- company/additional listing;
- partial delisting;
- buyback where authoritative share-state evidence exists.

### Cash/holder entitlement events

- cash dividend;
- mixed dividend.

### Structural/reference events

- IPO/listing anchor;
- merger/acquisition/tender-related events only where they materially affect the tradable security/share state.

Proxy voting and unrelated KSEI events should not enter the price/share adjustment layer merely because they appear in the same issuer history.

## Key audit questions before implementation

1. Can KSEI security-level histories be deterministically retrieved for the eligible historical universe without silent truncation?
2. What is the oldest reliable per-ticker event depth for common shares, especially 2018 onward?
3. Are KSEI `Ratio`, `Cum Date`, `Record Date`, `Distribution Date`, and `Status` consistently parseable across event families and historical templates?
4. Can KSEI schedule reference numbers/documents be joined deterministically to security-level event rows?
5. Can the relevant KSEI event/revision be linked to an IDX issuer announcement with a defensible publication timestamp?
6. How should revisions, changes, and cancellations be represented append-only without rewriting the historical state?
7. What exactly do IDX `JumlahSaham` and `JumlahSahamSetelahTindakan` mean for every `caType`; does the existing prototype arithmetic hold empirically and from official semantics?
8. Which event families provide enough evidence to reconstruct shares outstanding, and which are only event markers?
9. Can split/stock-dividend/bonus/right ratios be cross-checked against independent official evidence before any price-adjustment logic is admitted?
10. What coverage and unresolved-rate gates are required before a corporate-action table is allowed into research features or historical normalization?

## Immediate implementation rule

Do **not** migrate the old `idx_corporate_actions.py` into `main` yet.

The next bounded step is source/semantics discovery plus a small adversarial sample across event families and years. Only after date semantics, ratio semantics, pagination, revision handling, and source joins survive review should a new provider contract be implemented on this branch.

### Runtime boundary reached in ChatGPT environment

The accepted/latest Financial PIT transport uses `curl_cffi` with Chrome impersonation for direct IDX requests. The current ChatGPT execution container has no `curl_cffi`, and package installation cannot reach PyPI from that container. Substituting plain `requests` would change the tested transport contract and could recreate the known direct-IDX 403/Cloudflare behavior.

Therefore the first **live bounded Corporate Action scrape** should be run in the user's existing local IDX-Trade/Codex environment where the Financial PIT transport already works. This is a runtime/environment handoff only; it does not authorize bulk acquisition.

## Non-goals

- no Foreign Flow work;
- no Financial PIT parser changes;
- no model feature design or model run;
- no adjustment of historical OHLC;
- no synthetic split/dividend inference from price jumps;
- no vendor source promoted over official evidence;
- no bulk market-wide backfill yet;
- no protected outcome access.
