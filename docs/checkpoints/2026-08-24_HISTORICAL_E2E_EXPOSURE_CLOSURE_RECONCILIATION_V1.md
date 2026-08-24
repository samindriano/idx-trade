# Historical E2E Exposure Closure Reconciliation V1

## Scope

This checkpoint records one outcome-blind offline reconciliation pass for the
historical E2E replay lane. It does not load labels, returns, fills, NAV,
performance metrics, Monte Carlo inputs, protected outcomes, or provider data.

Branch: `research/idx-historical-e2e-replay-v1`

HEAD: `8250b5b4a89a5e5275804fa079ecc1226a076c22`

## Dividend corpus reconciliation

The parent discovery manifest is still marked `INCOMPLETE` because four rows
were rejected by the first parser (`BBTN`, `BJTM`, `CYBR`, `RAJA`). This is a
parser-stage status, not a missing-source status:

- 347/347 raw ticker response files exist and are non-empty;
- each response is HTTP 200 JSON with `Replies` and `ResultCount` coherent;
- the normalized derivative is `COMPLETE` for all 347 tickers;
- the four parser-invalid tickers were recovered offline from their already
  preserved raw bytes; no reacquisition was performed.

Pinned source identities:

- raw discovery manifest:
  `D:\Documents\Project\idx-historical-e2e-dividend-corpus-batch-20260824-v1\DISCOVERY_MANIFEST.json`
  SHA-256 `9c89e0e089827a46c51a18ee3d2ddba36861fc02660f677942315d9d367e25bf`;
- normalized manifest:
  `D:\Documents\Project\idx-historical-e2e-dividend-corpus-normalized-20260824-v1\NORMALIZED_MANIFEST.json`
  SHA-256 `a94a04b7d8c2dcefafbd8397e03e36059efbdeaab609068644d53371d1b6b167`.

The complete closure table is external-only and is not a replacement for the
accepted readiness ledger:

`D:\Documents\Project\idx-historical-e2e-dividend-closure-20260824-v1\DIVIDEND_EXPOSURE_CLOSURE_V1.csv`

CSV SHA-256:
`c4d6a73d876cf92695944c2b8d941db4dbcff822558afd2c0e383f8d2664af4c`

Summary: 5,693 exposure rows, 1,297 holding spells, 347 tickers.

| Closure status | Rows | Meaning |
|---|---:|---|
| `BOUNDED_CERTIFIED_EVENT_OVERLAP` | 11 | Existing accepted bounded BBCA/BBRI event dispositions overlap the spell. |
| `CANDIDATE_REQUIRES_ATTACHMENT_SEMANTICS` | 4,384 | Announcement candidates exist, but exact ex-date/entitlement semantics are not established by the corpus. |
| `NO_EVENT_PROOF_NOT_AUTHORIZED` | 1,298 | No candidate title was observed, but title absence is not a certified no-event proof. |

The closure classification is intentionally conservative. The full
`GetAnnouncement` metadata capture has complete identities, timestamps,
titles, issuer codes, and attachment references for the preserved responses,
but the attachments were not acquired for the full universe. Therefore the
corpus cannot yet establish the required market-wide no-event ledger.

## Existing official KSEI evidence relevant to CA exposure

Two high-utility CA events have existing official evidence indicating a cash
conversion to `IDR`, not a security-to-security price-basis transition:

- `NISP`, source date `2024-09-06`, voluntary conversion. Existing targeted
  evidence records `1 NISP : 1230 IDR`, source SHA
  `9443dc0c91e58df1658cdc231f5be1a3c490e983ee0f9ee10194687945bc7d5`, with
  exact KSEI registered-security identity.
- `TPIA`, source date `2024-05-20`, voluntary conversion. Existing KSEI
  history records `1 TPIA : 4250 IDR`, source SHA
  `78e6f8b9f47ca8d9fbdbf076d443ff834b23c6f923cc158ab8e95098ecb0241b`.

These are proposed `EXACT_NON_BLOCKING_STATIC_SECURITY_TO_CURRENCY`
dispositions only. They have not been inserted into or used to rewrite the
accepted CA event-window ledger in this checkpoint.

As an outcome-blind sensitivity diagnostic only, removing those two event IDs
from the current exposure blocker lists would leave 5,113/5,693 CA rows and
205/600 sessions passing, with longest provisional runs of 76, 56, 96, 52,
and 67 sessions. This is not a certified replay scope because the authoritative
ledger has not been regenerated with the dispositions.

## Current replay decision

The pinned strict scope remains unchanged and blocked:

- scope recompute root:
  `D:\Documents\Project\idx-historical-e2e-scope-recompute-20260824-v9`;
- status `STRICT_SCOPE_EMPTY_BLOCKED`;
- strict sessions `0`;
- payload SHA-256 `f75cf7302f4bd27927e36e296634c7ae9adfcd32849ed8fc78555a9e27dc6fd7`;
- file SHA-256 `cb765a5f1675ea35c2a4d075302c64fd6ac09d413ba8edb4a8198079ed203ae0`.

Dividend closure blocks every session because no market-wide no-event proof is
available. Corporate-action continuity independently has 1,222 unresolved
exposure rows in the pinned readiness audit. No P&L, replay, performance, or
Monte Carlo stage is authorized by this result.

Next bounded work: preserve the two cash-conversion dispositions in a
reviewable CA evidence bundle, then resolve remaining exposure-intersecting CA
events by utility. Dividend work must either acquire/verify the exact
attachment semantics needed for each exposure spell or remain fail-closed; it
must not promote title absence to no-event proof.
