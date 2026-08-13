# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-SCIENTIFIC-NOTATION-REMEDIATION
model_used: GPT-5 Codex Luna xhigh
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
branch: `data/financial-pit-scientific-notation-remediation-v1`
head_commit: `fb52454a6d902f5cf9383c1a7b44bb92ddfe3bfd`

## Scope

Parser-only strict scientific-notation remediation and one rerun of the same
offline 5,965-filing Financial PIT census. No network, redownload, new labels,
ratios/features, models, or protected outcomes.

## Changes

- strict ASCII decimal/scientific grammar with malformed exponent rejection;
- visible XLSX inline/shared-string values use the same numeric parser;
- adversarial parser and end-to-end inline-value tests;
- census manifest records the actual runtime code commit.

## Result

The v3 census processed 6,108 exact joins and 5,965 PIT-ready filings. It
produced 37,167 `EXTRACTED`, 15 `UNRESOLVED_PERIOD`, and 64
`UNRESOLVED_UNIT` fact statuses; 143 scope-unresolved joins stayed excluded.
Eight-fact complete co-occurrence is 4,287 filings, exactly matching the
accepted template-drift audit prediction of 4,287. Main fact coverage is
71.9531% for revenue, 78.7259%–78.7594% for NI/assets/liabilities/equity, and
78.6421% for OCF; cash-equivalents coverage is 72.1878%.

External result root:
`D:\Documents\Project\idx-financial-pit-scientific-notation-remediation-census-20260813-v3`

Manifest SHA-256:
`95db03c431dadb5a0af749fd63687f39c8a68d450d7dee17c4c5c53c5bf73d7b`.

## Validation

- focused Financial PIT tests: `29 passed`;
- full pytest: `531 passed, 0 failed, 3 existing FutureWarnings`;
- no provider/network access;
- no protected outcomes or model work.

## Decision needed

Independent review is needed before any feature design. The expected next
step, if accepted, is a separately bounded Financial PIT feature-contract
design; this branch does not perform it.
