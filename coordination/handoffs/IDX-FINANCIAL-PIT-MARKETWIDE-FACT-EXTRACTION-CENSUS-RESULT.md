# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-MARKETWIDE-FACT-EXTRACTION-CENSUS
model_used: GPT-5 Codex Luna xhigh
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `baf0334a1dd6a31e9d88ae978630ec864bfb3410`
branch: `data/financial-pit-marketwide-fact-extraction-census-v1`
result_commit: to be filled after final commit

## Scope

Offline extraction/coverage census over all 5,965 accepted PIT-ready XLSX/XBRL
joins. No provider calls, redownload, ratios/features, model work, or
protected-outcome access. Excluded 143 scope-unresolved joins and did not
reintroduce any earlier unsupported/ambiguous/hash/provider/linkage failures.

## Results

- input rows: 6,108; SHA `656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9`;
- processed: 5,965 (5,963 XLSX, 2 XBRL);
- scope: 4,410 consolidated / 1,555 separate;
- fact candidates: 22,041;
- extracted: 21,962 (99.6416%);
- `UNRESOLVED_UNIT`: 64;
- `UNRESOLVED_PERIOD`: 15;
- `UNRESOLVED_TAXONOMY`: 0;
- `CONFLICTING_FACTS`: 0;
- network calls: 0;
- protected outcomes: untouched.

Core fact extracted coverage:

| Fact | Extracted / 5,965 | Coverage |
|---|---:|---:|
| revenue | 2,415 | 40.4862% |
| net income | 2,965 | 49.7066% |
| attributable net income | 2,979 | 49.9413% |
| total assets | 2,475 | 41.4920% |
| total liabilities | 2,622 | 43.9564% |
| total equity | 2,646 | 44.3588% |
| cash and cash equivalents | 2,575 | 43.1685% |
| cash exact label | 341 | 5.7167% |
| operating cash flow | 2,944 | 49.3546% |

Exact year/period, scope, template/industry and format coverage is in the
external `coverage.json`; each output diagnostic retains its row-level source
evidence and chain hashes.

## External artifact hashes

Root:
`D:\Documents\Project\idx-financial-pit-marketwide-fact-extraction-census-20260813-v1-final-v2`

- `fact_records.jsonl`: `4e73eb0cce07b0bfb4d9cc12a4ecb6b54eba697a2e327ef6316b32acbdea3a42`
- `filing_diagnostics.jsonl`: `a38bd9489b527430e967018cdb146989960f13c0b343c95504612fa19bfdfb1d`
- `coverage.json`: `adaab5e3cc6537cfa2e45f130ebc31452489c9b641c374b33c6f98f02ca17d3c`
- `exclusions.json`: `209e9f2b2c8543b46c66023e5d29162d5db84dbfa7d86ee798388d07a4c7ec4c`
- `summary.json`: `429f2d39c44b51396ca8f263800946ddfded9f4d8f77d1a2f336f25a0f9ccdd0`
- `MANIFEST.json`: `e85469a52f749ab72869716b2689cfb2005e222103e2bfc7fdec1de4264eb872`

## Decision

`CONDITIONAL_GO_FOR_SEPARATE_FEATURE_DESIGN_REVIEW`: extraction corpus is
usable for a missingness-aware feature-design review, but it is not a dense or
complete fundamental panel. Do not derive ratios/features or model until a
separate spec resolves the sparse exact `cash` concept, missingness policy,
and scope/version contracts.

## Validation

- focused tests: 14 passed;
- full pytest: 515 passed, 0 failed, 3 existing warnings;
- `git diff --check`: passed.

## Recommended next action

ChatGPT independently reviews coverage and decides whether to freeze a
feature-design contract. Do not begin feature materialization in this lane.
