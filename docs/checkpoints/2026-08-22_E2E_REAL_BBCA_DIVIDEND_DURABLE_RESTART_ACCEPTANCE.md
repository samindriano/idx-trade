# E2E Baseline Paper V1 ? Real BBCA Dividend Durable Restart Acceptance

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`

## Scope

Offline acceptance rehearsal using already captured real official IDX evidence for the admitted BBCA interim cash-dividend event.

No network request was made.
No Zapi request was made.
No live paper runtime was mutated.
The rehearsal used an isolated temporary runtime directory.

## Official evidence

Announcement:

- ticker: `BBCA`
- announcement ID: `20260819183103-005/CSG-IVR/2026_id-id`
- announcement number: `005/CSG-IVR/2026`
- raw announcement SHA-256:
  `6e8ced1891addecdb9a1029d064c75d072ebcbeb4319ad633d30e43fac004473`

Official attachment SHA-256 values:

- `4ee38c989b3ff09c5d721e6d56340d873e8183822eadd3c87cd8dbfa576e092c`
- `1d8b37031c4a0c23baeb6d511e8270c3f2be160c9c40c3102c7faaffdf54b94b`
- `93ff2e663af91ac6d87ed29c6a192725f2b4b86b0fc0432610ff7bdaad0c1949`

All three local attachment bytes reproduced their declared SHA exactly.

Existing semantic review status:

`PASS_DIRECT_IDX_ANNOUNCEMENT_ATTACHMENT_TERMS_ELIGIBLE_FOR_V1_1`

## Certified event

Current E2E code certified:

- event ID: `CASH_DIVIDEND_BBCA_6bb86334ebe6902946743804`
- ticker: `BBCA`
- gross dividend/share: `Rp25`
- cum date: `2026-08-28`
- ex date: `2026-08-31`
- record date: `2026-09-01`
- payment date: `2026-09-16`
- certified evidence SHA-256:
  `6bb86334ebe6902946743804650ca9b45bca5c85b3ad3fa76e13a6fbada7666a`

## Durable lifecycle rehearsal

The following chain passed with process-style reloads between stages:

`official evidence`
? `verified cash-dividend admission`
? `append-only certified-event registry`
? `2026-08-21 announcement snapshot`
? restart/load
? `2026-08-28 cum-date entitlement`
? restart/load
? `2026-08-31 ex-date receivable`
? restart/load
? `2026-09-16 payment settlement`
? final full-chain reload

Acceptance position:

`200 BBCA shares`

Expected gross claim:

`200 ? Rp25 = Rp5,000`

Observed:

- cum entitlement shares: `200`
- ex-date receivable: `Rp5,000`
- spendable cash before payment: `Rp50,000,000`
- final cash after payment: `Rp50,005,000`
- settlement count: `1`
- receivable after payment: `0`

Same-session final snapshot replay was byte/state idempotent and did not double-credit the dividend.

## Re-runnable harness

`scripts/run_e2e_bbca_dividend_restart_acceptance.py`

The harness accepts an external evidence root and defaults to a temporary runtime. It performs no network access itself and refuses an already-existing explicitly supplied runtime root.

Latest acceptance result:

`REAL_BBCA_DURABLE_RESTART_LIFECYCLE_PASS`

## Regression

Focused CA/dividend suite after adding the acceptance harness:

`45 passed`

Repository hygiene:

`git diff --check` PASS.

## Verdict

`E2E_REAL_BBCA_DIVIDEND_DURABLE_RESTART_ACCEPTED`

This validates the accounting, evidence, registry, restart, and persistence path against a real admitted IDX cash-dividend event.

It does not yet authorize unattended prospective CA acquisition or production E2E paper mutation.

## Next phase

Generalize prospective dividend acquisition away from the historical BBCA-specific audit scripts:

`/ListedCompany/GetAnnouncement`
? dynamic relevant-ticker/window discovery
? immutable official attachments
? conservative term certification
? fail closed when incomplete or ambiguous.

Generic non-cash corporate actions remain fail-closed.
