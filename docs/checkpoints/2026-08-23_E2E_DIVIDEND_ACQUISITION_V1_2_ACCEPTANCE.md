# E2E Corporate Action / Cash Dividend Acquisition V1.2

Date: 2026-08-23
Branch: `integration/idx-e2e-baseline-paper-v1`
Parent checkpoint: `c3cdc2e188801bddc31be2130544b9f5945050cd`

## Result

The V1.2 dividend acquisition implementation completed the fresh real
POST_EOD D2B batch and an exact immutable recovery replay. The current
implementation is ready for independent review as:

`CORPORATE_ACTION_CASH_DIVIDEND_D2B_V1_2_ACCEPTANCE_READY`

The run used direct IDX `ListedCompany/GetAnnouncement` plus hashed official
attachments. The reviewed provider checkout was`nichsedge/idx-bei` at
`75d6c0f74fa360d225794c70c383348977de6798`. Zapi dividend data was not used.

No scheduler, Stockbit capture, protected outcome, alpha, Decision, sizing, or
execution artifact was changed.

## V1.2 changes

- Raw discovery-page SHA is transport provenance only.
- The exact matched announcement record has its own canonical SHA.
- Attachment bytes remain individually SHA-pinned and are revalidated by the
  V1.2 certifier.
- The producer records a durable discovery-manifest relative path rather than
  a transient `.partial.<random>` staging path. Existing stale paths remain
  recoverable only by exact SHA inside the bounded batch root.
- The batch runner validates the complete discovery/review/attachment chain,
  commits the immutable journal last, rejects duplicate candidates and same
  logical-order journal forks, and recovers a complete batch without network.
- V1.2 disposition is generic and issuer-agnostic: historical observations,
  live certified events, corroborating reports, superseded correction
  predecessors, and unresolved live blockers are distinct states.
- Semantic precedence accepts strict per-share/remaining-payable/structured
  DPS evidence, rejects total payout masquerading as DPS, preserves high
  precision, and allows a correction published after cum-date without
  backdating its knowledge time.

## Fresh real D2B batch

External immutable root:

`D:\Documents\Project\idx-e2e-forward-dividend-acquisition-batch-smoke-20260823-v6`

Logical batch: `2026-08-22_POST_EOD` for `BBCA`, `BBRI`, and `TLKM`.

Counts:

| category | count |
|---|---:|
| candidates | 11 |
| `CERTIFIED_LIVE` | 1 |
| `HISTORICAL_OBSERVED` | 6 |
| `CORROBORATING_ONLY` | 2 |
| `SUPERSEDED` | 2 |
| `BLOCKED_LIVE_UNRESOLVED` | 0 |

Hashes:

- `BATCH_MANIFEST.json`: `f13195237dd2efc5ac9e2cde49daa09bf385afcdc7769f16e4a0055ecea9e90f`
- discovery manifest: `49860596da3522e0920e8c9fe5215465d9d0b8d4d38b1d9b90d5c95ce14cd88e`
- journal file: `e8ee29fa6f04d3261a6caafd620b18943637912c9693f575dc69e590593c4e53`
- journal-declared SHA: `e6493eb9e1ddc9ca6269ebf1d755f32015f817daa204366e342a31ae872f2fb4`

The exact same logical command was run a second time. It returned
`DIVIDEND_ACQUISITION_BATCH_RECOVERED`, retained the same journal SHA, did not
call the network, did not duplicate the live registry event, and did not
mutate the immutable evidence.

The final JSON tree contains no `.partial.` path.

## Real economic certification

The following seven certified event values were revalidated from the copied
immutable batch evidence:

| issuer / announcement | DPS | event ID |
|---|---:|---|
| BBCA `0263/ESG/2025` | 55 | `CASH_DIVIDEND_BBCA_42c38ffce7626e108d972d44` |
| BBCA `0033/ESG/2026` | 281 | `CASH_DIVIDEND_BBCA_7874fe9584f810b07e953b68` |
| BBCA `0053/ESG/2026` | 20 | `CASH_DIVIDEND_BBCA_bdf34c7f58efafd40ea896e2` |
| BBCA `005/CSG-IVR/2026` | 25 | `CASH_DIVIDEND_BBCA_0ba8da55aac01313f2174243` |
| BBRI `B-6115-DIR/PPM/12/2025` | 137 | `CASH_DIVIDEND_BBRI_705206fc208641921130f4d2` |
| BBRI `06-Ket/Not/IV/2026` | 209 | `CASH_DIVIDEND_BBRI_d0d56b21f4da2a245dd1c4a0` |
| TLKM `Tel.049/LP0000/COP-M00000000/2026` | 223.1658777 | `CASH_DIVIDEND_TLKM_cc501239b36750cbe852d906` |

BBRI's 18-Dec advertisement and 19-Jan post-event report are corroborating
only. TLKM's 10-Jun and 11-Jun unresolved predecessors are superseded by the
19-Jun correction; neither creates a second economic event.

## Offline replay

Fresh external replay root:

`D:\Documents\Project\idx-e2e-forward-dividend-v1-2-offline-replay-20260823-v5`

The replay copied the v6 immutable batch and used only local discovery,
review, manifest, and PDF bytes. It re-ran the production V1.2 certifier and
temporal disposition layer with no provider/network call. Result:

- 11/11 candidate identities replayed;
- 7/7 certified economics exact;
- disposition result identical to the batch manifest;
- 1 live event, 6 historical, 2 corroborating, 2 superseded, 0 blockers;
- result SHA: `454213df35c3ffd741cc137c24d502f1fc45cd46e229c1c553852b2418e07aac`.

The earlier query-window artifact records equal announcement-record SHA,
document SHA set, economics, event ID, and event SHA while transport-page SHA
differs. The current corrected replay preserves the announcement record
(`11e06dbda40ea716ab1749f29e4e9bdf7100904a1c6373820d2b8f244753e34a`) and
documents, and correctly derives the new `0ba8da…` evidence hash from DPS 25.

The previously recorded `8c3ace…` identity is retained only as an audit
finding: recomputation proves it hashes the old total payout
`3071043782500`, not the authoritative DPS `25`. Restoring that identity would
reintroduce a semantic error. The corrected identity is therefore the only
one admitted by this batch.

## Tests

- focused dividend/CA suite: `69 passed`, exit code `0`;
- full repository suite: `608 passed`, exit code `0`;
- full suite warnings: 3 existing pandas `FutureWarning`s;
- all targeted modules compiled successfully;
- `git diff --check`: clean.

## Remaining boundary

Gross-versus-tax/net dividend treatment remains intentionally unresolved.
No tax haircut or inferred net amount is applied. Unsupported evidence and
conflicting hashes remain fail-closed.
