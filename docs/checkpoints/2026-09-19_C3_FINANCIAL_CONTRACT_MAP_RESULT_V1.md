# C3 Financial Contract Map Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Stage: `D_C3_FINANCIAL_CAPABILITY`
Result: `PASS_STRUCTURAL_ONLY / C3 FIXED CONTRACT REMAINS BLOCKED`

## Question

The earlier C3 audit established that the all-five quality/growth composite is
sparse. This map asks whether a defensible mechanism-defined subset of the same
five fields materially improves PIT-safe capability without imputing,
forward-filling, relaxing provenance, or adding a provider.

The only contracts considered are:

- `quality_core`: liabilities/assets, cash/assets, net margin;
- `growth_core`: YoY revenue and YoY total assets;
- `quality_plus_yoy_revenue`;
- `quality_plus_yoy_assets`;
- `all_five`: the current fixed C3 contract.

These are capability contracts, not new candidate IDs. All contracts use the
same knowledge-time, period-date, provenance, identity, and frozen eligibility
gates.

## Result summary

Source: 277,244 financial rows, 729 tickers, 1,231 dates. The financial rows
join the feature panel one-to-one; 249,333 matched rows are eligible under the
frozen structural universe. No missing value is filled and no forward fill is
used.

| Contract | Raw finite rows | Frozen final rows | Frozen final dates | Dates with ≥30 names | Final coverage of 310,761 eligible rows |
|---|---:|---:|---:|---:|---:|
| quality_core | 70,520 | 64,406 | 525 | 505 | 20.7253% |
| growth_core | 34,412 | 30,994 | 291 | 278 | 9.9736% |
| quality + YoY revenue | 34,412 | 30,994 | 291 | 278 | 9.9736% |
| quality + YoY assets | 34,412 | 30,994 | 291 | 278 | 9.9736% |
| all-five / current C3 | 34,412 | 30,994 | 291 | 278 | 9.9736% |

For the final frozen quality-core subset, the supported-date name-count
distribution has minimum 6, median 122, and Q10 46.4 names. For every
YoY-containing contract, the supported-date minimum is 1, median 113, and Q10
34 names.

## Capability interpretation

1. The quality ratios form a meaningfully broader capability island than the
   current all-five C3 contract.
2. The two YoY fields are jointly limiting in this bundle: requiring either
   YoY field produces the same 34,412-row finite subset as requiring both.
3. Therefore selecting only YoY revenue or only YoY assets does not recover
   coverage. It would be a different mechanism contract with the same support
   bottleneck, not a defensible coverage rescue.
4. The quality-core subset is not automatically admissible as a new alpha:
   changing the formula would require a new predeclared contract, structural
   review, novelty review, and eventually protected evaluation admission.
5. The source still has 206,313 rows with missing knowledge timestamps,
   period dates, reporting versions, and attachment lineage. Finite values
   outside the provenance-complete subset remain unsafe.

## Gate-loss and governance facts

Among the finite/provenance-complete capability rows, same-bundle and selected
knowledge-time violation flags were not observed. That does not certify the
missing rows: the source still has these population-wide governance gaps:

- `NO_FINANCIAL_STATE`: 186,764 rows;
- `SELECTED`: 70,931 rows;
- `UNRESOLVED_PERIOD_BOUNDARY`: 19,549 rows;
- missing knowledge timestamp: 206,313 rows;
- missing period date: 206,313 rows;
- missing reporting version: 206,313 rows.

The quality-core result therefore changes the diagnosis from “all financial
features are equally sparse” to “quality ratios have a broader capability
island, while YoY/provenance support is the binding limitation.” It does not
change C3's current status or authorize a quality-core target run.

## Status and next action

| Direction | Status | Reason |
|---|---|---|
| Current all-five C3 | `BLOCKED` | sparse/partial PIT support |
| Quality-core capability | `FUTURE_RESEARCH / CONTRACT_PENDING` | broader structural support, but new formula would need separate contract and review |
| YoY-only or quality+one-YoY variants | `BLOCKED_BY_SAME_SOURCE_GAP` | no coverage gain; same 34,412 finite-row bottleneck |

Do not create C3A/C3B/C3C merely from these counts. A future quality-core
candidate may be considered only after a novelty decision and a frozen contract
explicitly chooses that mechanism. Until then, the current candidate registry
remains exactly C1–C4.

## Reproducibility and boundary

- Builder: `research/c3_financial_contract_map_v1.py`
- Builder SHA-256: `669cbf7f2e4b7118bbf215b2cb97db28e53c99471a11bb63cbda3c2fffc04c1a`
- Independent verifier: `research/verify_c3_financial_contract_map_v1.py`
- Independent verifier SHA-256: `f5dbb39f73c216b245d79039b5ae2ff0595986216cf56a96512d5fb96f8ef0cc`
- Output:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\c3_financial_contract_map_v1.json`
- Output SHA-256: `590a211df1c52f659c2857bacacd5d78acf845928b9f2f5516b53bc21fc5d598`
- Firewall artifact:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\c3_financial_contract_map_firewall_v2.json`
- Firewall artifact SHA-256: `469fc1ecdd5c99daf988e45a39117a46636c2f63dbca99af44beb78501ae3deb`
- Source financial SHA-256:
  `c6004832e651b380161ec216efb2020dddbe86419d89c4521f77aeb09335876b`
- Result: `PASS_STRUCTURAL_ONLY`
- Independent verifier: `PASS`
- Target firewall: `PASS`
- No target, forward return, incumbent score, provider, network, cloud,
  capture, scheduler, counter, canonical, or production artifact was opened
  or modified.
