# Financial Statements PIT V1

Status: initial point-in-time filing contract implemented; real IDX/Zapi source acquisition pending local audit.

## Goal

Build a revision-aware financial-statement layer that answers a strict question:

> At decision timestamp `t`, which exact version of each issuer financial filing was actually knowable, and what facts did that version contain?

The fiscal period end is **not** the knowledge date. A Q1 statement ending 31 March must not become visible to a model on 31 March if IDX only publishes it later.

## Why filing versions are first-class

Financial statements may be late, corrected, restated, or re-uploaded. V1 therefore does not maintain one mutable row per issuer/quarter. Each official filing version is immutable and carries its own publication/knowledge time and SHA-256 provenance.

At an as-of timestamp, the system selects the latest filing version that was knowable by then. A later revision never rewrites what was knowable earlier.

## Canonical filing contract

Each filing version requires:

- ticker;
- fiscal period end;
- explicit period kind (`Q1`, `H1`, `9M`, `FY`, or explicitly retained `OTHER`);
- explicit statement scope (`CONSOLIDATED` or `SEPARATE`);
- reporting currency;
- official `published_at`;
- `knowledge_at`, defaulting only to the same filing's publication time when no later supporting evidence is needed;
- official source/ref/HTTPS URL;
- SHA-256 of the exact raw response/file used.

A revision for the same issuer/period/scope is a new filing version with a later knowledge time. Conflicting versions sharing the same knowledge time fail closed.

## Financial fact contract

Facts are long-form and permanently bound to one `filing_id`.

Each numeric fact has:

- concept;
- numeric value;
- unit;
- either a duration (`period_start`, `period_end`) or an instant date.

V1 deliberately preserves source period semantics. It does **not** assume a quarterly income-statement value is a standalone quarter rather than year-to-date, and it does not derive QoQ/TTM values until source semantics are proven.

Facts from different filing versions must never be mixed into one synthetic statement before an explicit transformation layer exists.

## Point-in-time rules

For a decision timestamp `t`:

1. discard filings with `knowledge_at > t`;
2. for each `(ticker, fiscal_period_end, period_kind, statement_scope)`, select the latest remaining filing version;
3. expose only facts whose `filing_id` belongs to those selected versions.

This protects against publication-date leakage and revision/restatement leakage.

## Source policy

Preferred hierarchy:

1. direct official IDX financial-report metadata/files/API;
2. Zapi as an IDX access/discovery transport when it exposes the same upstream facts;
3. other providers only as reconciliation evidence unless separately promoted.

Zapi must not silently become independent canonical provenance. Raw captures should remain outside Git; store hashes/provenance and small sanitized fixtures only where tests need them.

## Source-acquisition questions

The local audit must determine:

1. which IDX/Zapi endpoints expose financial-report inventory and statement content;
2. how ticker, year, period, report type, and consolidated/separate scope are represented;
3. the exact semantics and timezone of publication/submission timestamps;
4. whether historical reports and later revisions/restatements remain discoverable;
5. whether files are XLSX/XBRL/XML/PDF/JSON and which format is most structurally reliable;
6. whether direct IDX and Zapi payloads match on representative reports;
7. how far back coverage is defensibly complete;
8. whether statement concepts/units are stable enough for structured extraction.

## Initial implementation

`src/idx_trade/financial_pit.py` provides:

- strict filing-version canonicalization;
- publication/knowledge-time validation;
- immutable revision semantics;
- strict long-form fact canonicalization;
- as-of filing selection;
- as-of fact selection without cross-version mixing.

`tests/test_financial_pit.py` covers publication-time leakage, delayed evidence, revisions, same-time conflicts, explicit statement scope, duration/instant facts, revision-bound fact selection, and orphan facts.

## Acceptance gates

Before Financial PIT V1 can be promoted for research use:

- publication/knowledge time must come from a verified upstream semantic, not fiscal period end or filename convention;
- consolidated versus separate statements must be explicit;
- revisions/restatements must be preserved rather than overwritten;
- official source provenance and SHA must be retained;
- representative direct IDX/Zapi cross-checks must pass;
- a bounded coverage window must be established or explicitly remain incomplete;
- source cumulative-vs-quarter semantics must be documented before deriving growth/TTM features;
- focused and full pytest must pass.

No financial feature engineering, model experiment, realized-outcome access, or main merge is authorized by passing this data gate.
