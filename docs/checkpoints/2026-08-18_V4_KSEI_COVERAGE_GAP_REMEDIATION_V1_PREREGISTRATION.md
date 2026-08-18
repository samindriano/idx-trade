# V4 KSEI Coverage-Gap Remediation V1 — Preregistration

Status: `FROZEN_BEFORE_LOCAL_PROVIDER_RUN`

Scientific/provider code anchor:
`5b311e0398afb9099887cf7558c92f15d99029b8`

Parent scientific decision:
`data/idx-v4-ca-blocker-attribution-v1@052351372215a5752199513a23cf3f7373ac1f59`

## Why this lane exists

The accepted blocker attribution showed that resolving only the currently
observed KSEI history coverage blocker has an optimistic 600/600 H5/H10/
consensus ceiling, whereas resolving all currently observed schedule-unknown
rows alone still fails the frozen 90% gate. This does **not** imply actual
coverage recovery will certify continuity: newly recovered issuer histories
may reveal mechanical events that create new exact-schedule blockers.

Therefore this lane tests the coverage dimension first and must replay the
actual continuity gate after recovery.

## Frozen population

Only the 43 `COVERAGE_UNRESOLVED` tickers from the immutable 610-ticker KSEI
census may be contacted:

`ACRO AMAN AVIA AYAM BCIP BDKR BJTM CBRE DFAM DGIK HELI IBOS ICBP ISAP ISAT JPFA KEJU KRAS MAPA MAPI MIDI MIKA MINA MSJA NASI OLIV PMMP PMUI PRIM PSAB SDMU SKRN SLIS SMAR SNLK SOCI SOFA STAA STRK TCPI TEBE TOSK VISI`

Sorted newline-delimited identity SHA-256:
`1cd050985841519d24f58a38d10014693ff4a843cbd438586237ad4419ffe812`

No 567 already-certified ticker may be recrawled or logically changed.

## Immutable parent pins

- parent census manifest:
  `7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25a`
- parent summary:
  `a046637fbcff69cbc42c09e4cac30d9181b2ce93a3cf7297a9a01cfc23a2f422`
- parent ticker coverage:
  `bb5414125862411e5d3ee760f8e7415b8418803c71d1cc1ef26fb0c55397bc70`
- parent KSEI history:
  `3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d`
- parent request records:
  `e68d60103cc3efc04299c1b330c4ef39e55ba1e44bbcf79f178b2f1ccff812e5`

The parent failure records are classified offline before provider work and
promoted only as a diagnostic summary; they do not change admission rules.

## Frozen provider remediation

Official source remains exactly KSEI registered-security history:

`https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}?setLocale=en-US`

The only transport remediation relative to the original broad census is:

- fresh `curl_cffi` session per unresolved ticker;
- `chrome110` impersonation unchanged;
- exact KSEI origin warmup once per ticker;
- at most two security-page attempts per ticker;
- 60-second request timeout;
- one-second retry backoff;
- 0.2-second inter-ticker sleep.

There is no alternate provider, mirror, alternate ticker alias, alternate KSEI
security identity, or parser relaxation. A 200 response still requires the
unchanged strict KSEI history parser: exact requested four-character Short Code
and exactly one authoritative Corporate Action table with the frozen six-column
header.

## Overlay semantics

- parent census bytes remain immutable;
- failed remediation leaves the original unresolved logical coverage row
  unchanged;
- a ticker becomes coverage-certified only after a strict parser success;
- recovered history rows are append-only and may only belong to the frozen 43;
- the 567 non-gap logical coverage rows must remain identical;
- all newly recovered active mechanical/unknown rows are retained and exposed
  to the downstream continuity replay.

Availability is not continuity certification.

## Frozen continuity replay

If the targeted acquisition completes, run one outcome-blind continuity replay
using:

- original frozen V4 continuity ledger and prior official event evidence;
- the merged KSEI coverage/history overlay from this lane;
- the same official calendar;
- the accepted residual-document evidence bundle;
- `classify_event_with_residual_document_evidence`, which preserves the accepted
  Voluntary-Cash semantics and residual exact document semantics;
- unchanged 90% H5/H10/consensus date gate.

Newly recovered mechanical events may legitimately reduce the optimistic
coverage ceiling or create schedule-required events. The replay result is the
only admissible gate result.

## Stop conditions

Stop after the one targeted provider run and, if it completes, the one
continuity replay regardless of PASS/BLOCKED/error. No automatic schedule
acquisition follows.

No R5/R10, target/rank materialization, model fit, prediction, IC/performance,
bootstrap, protected/fresh-forward outcome access, threshold/universe change,
or V4 contract rescue is authorized.
