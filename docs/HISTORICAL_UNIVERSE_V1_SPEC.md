# Historical Universe V1

Status: source acquisition/runtime audit complete; full historical lifecycle
coverage remains FAIL-closed pending authoritative relisting/conflict evidence.

## Goal

Build a historically correct legal listing universe for IDX-Trade so an as-of-date model cannot include securities before listing, after delisting, or across an unproven lifecycle gap.

This is a data-foundation lane. It does not change the frozen V3-B model or realized-outcome policy.

## Existing architecture

IDX-Trade already has:

- `security_master.py` for legal existence and tradability contracts;
- `universe.py` for the dynamic liquidity/model universe.

Historical Universe V1 does **not** replace either module. It supplies a stricter, provenance-aware historical lifecycle table that can be bridged into the existing security master.

## V1 scope

In scope:

- listing date / first legal listing interval;
- delisting / end of a legal listing interval;
- relisting as a new interval for the same ticker;
- current official universe reconciliation;
- price-observation versus lifecycle consistency audit;
- bounded completeness claims for historical coverage.

Out of scope for this lane:

- suspension/FCA/tradability history;
- corporate-action adjustment logic;
- sector classification;
- broker/foreign/fundamental features;
- model changes or outcome access.

## Canonical interval semantics

`listed_from` and `listed_to` are **inclusive legal-existence boundaries**, matching `security_master.existence_state`.

A ticker may have multiple non-overlapping intervals if it is genuinely relisted. Overlapping intervals, duplicate unreconciled evidence, invalid tickers, missing start dates, or missing source provenance fail closed.

Raw source-specific fields must be mapped into these semantics explicitly. Do not silently assume that a provider field named `DelistingDate` means the last legally listed session; verify its upstream definition first.

## Source policy

Preferred source hierarchy:

1. direct official IDX metadata/files/API;
2. Zapi as an IDX access/discovery transport where it exposes the same upstream facts;
3. other sources only as reconciliation evidence unless independently promoted.

Zapi must not silently become a separate canonical authority. Preserve upstream provider/source metadata and validate source mappings on samples against direct IDX where practical.

## Completeness policy

A historical-universe table can be internally consistent yet still have survivorship bias if extinct securities are absent.

Therefore V1 distinguishes interval validity from **coverage completeness**.

A window may be marked complete only when:

- it has explicit left and right boundaries;
- the discovery basis is documented;
- the acquisition method is capable of finding both active and no-longer-listed securities in that window.

Open-ended or undocumented completeness claims fail closed to `is_complete=False`.

## Acceptance gates

Before Historical Universe V1 is promoted for research use:

1. identify the relevant IDX/Zapi endpoints and exact field semantics;
2. acquire active and historical/delisted lifecycle records without current-universe-only survivorship;
3. reconcile duplicates/conflicts explicitly;
4. demonstrate current-snapshot agreement against official IDX current securities;
5. run lifecycle consistency against the existing historical price panel;
6. explain every observation outside a legal interval or every price ticker with no lifecycle record;
7. prove a bounded completeness window for the historical research period, or keep the affected period fail-closed;
8. run focused tests and full pytest.

No model experiment is authorized by passing this data gate.

## Initial implementation

`src/idx_trade/historical_universe.py` provides:

- strict lifecycle canonicalization;
- bridge into the existing `security_master`;
- historical as-of universe snapshots;
- price/lifecycle inconsistency detection;
- current official snapshot reconciliation;
- fail-closed bounded coverage windows.

`tests/test_historical_universe.py` contains synthetic/adversarial contract tests.

The next task requires local access to Zapi/IDX data to map real endpoint schemas and evaluate actual historical coverage.

## Bounded acquisition audit (2026-08-11)

The bounded acquisition was completed and is recorded in
`docs/checkpoints/2026-08-11_HISTORICAL_UNIVERSE_V1_SOURCE_AUDIT.md`.
Direct IDX was used as the canonical source and Zapi was used only as an
IDX access/discovery layer and cross-check.  The acquisition reached the
current IDX snapshot and 440 monthly delisting queries covering
1990-01 through 2026-08 without request errors.  It found 962 current
securities and 163 delisting rows for 159 ticker codes.

The V1 completeness gate remains **FAIL**.  Strict normalization cannot
produce a canonical interval table because six four-character tickers have
overlapping or internally contradictory lifecycle evidence
(`BUKK`, `INRU`, `ITMA`, `KIAS`, `SKBM`, `UNTX`), while two additional
delisting rows are non-standard securities (`MAMIP`, preferred stock, and
`MYRXP`, Series B).  Zapi's historical IPO endpoint confirms one BUKK
relisting but does not resolve the other conflicts or establish a complete
historical relisting census.  The existing price panel contains five of the
six conflict tickers, so the ambiguity is material to the 2024-06-21 through
2026-07-31 panel.

Consequently no complete bounded research window is promoted.  The source
captures and normalized audit outputs remain outside Git; only their hashes,
counts, provenance, and fail-closed diagnostics are committed.  No model,
feature, outcome, or execution lane is changed by this audit.
