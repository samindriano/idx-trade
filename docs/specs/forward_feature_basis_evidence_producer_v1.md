# Forward Feature-Basis Evidence Producer V1

Status: `CONTRACT_ONLY_NOT_A_CERTIFICATE`

This contract defines the evidence that a future producer must create before a
forward V4-X1 session can cross the existing population-admission gate. The
producer is not the scorer and must not rewrite, patch, or reinterpret frozen
science. A producer identity is accepted only when its implementation commit,
implementation SHA-256, and implementation evidence are separately pinned and
the detached root manifest verifies every retained child byte-for-byte.

## Required inputs

The producer must bind, at minimum:

- the exact frozen model input and its SHA-256;
- the exact clean scorer panel and its SHA-256, including the actual scorer
  historical boundary;
- the candidate session `session_ohlcv` artifact and SHA-256, with fresh OPEN;
- the complete scorer population and canonical ticker-set hash;
- frozen Security Master/PIT identity and current-session continuity evidence;
- the official exchange calendar and revision/vintage identity;
- corporate-action and transition evidence, when present;
- per-field source identity and source/evidence hashes for high, low, close,
  volume, and regular-market-value;
- OPEN source identity, evidence hash, session date, ticker set, and knowledge
  and observation/retrieval timestamps.

The candidate OPEN is a fresh Geometry3 input. It is not added to historical
rolling-window requirements. The historical/control H/L/C/volume/value basis
remains governed by the frozen feature-window contract.

## Required output

The output consists of `feature_basis_evidence.json` and its detached
`feature_basis_evidence_manifest.json`. The root manifest must declare the
evidence file, producer identity, and every child evidence file with relative
path, kind, source reference, and SHA-256. The runtime recomputes every child
hash and rejects undeclared, duplicate, conflicting, missing, or escaping
references. The manifest identity excludes only its own identity field and the
detached evidence-file hash to avoid a circular hash; the evidence binds that
identity, while admission metadata binds the full root-manifest SHA-256.

The evidence must use one of these states:

- `CERTIFIED_SAME_BASIS` — explicit same-basis evidence covers the complete
  model-input population and fresh candidate OPEN;
- `CERTIFIED_TRANSITION` — an exact authoritative transition is declared and
  proven outside every affected frozen feature dependency window, with all
  current fields otherwise safe;
- `BASIS_UNKNOWN` — a transition or basis cannot be established;
- `SOURCE_CAPTURE_UNRESOLVED` — required source bytes, timestamps, identity,
  or manifest bindings are missing or unverifiable.

`NO_KNOWN_TRANSITION` is informational only. It is never a certificate and
its absence must not be interpreted as evidence that no transition occurred.

All knowledge times must be timezone-aware and no later than the observation
time. Session identity, ticker identity, source authority, PIT/as-of
semantics, revision, calendar, candidate OPEN, and clean model input must be
bound to the manifest. Any mismatch is whole-session non-admission before the
scorer. The negative paths remain explicit: retained transition evidence stays
`BASIS_UNKNOWN`, and forward sessions without a complete authoritative bundle
stay `SOURCE_CAPTURE_UNRESOLVED`; no certificate may be fabricated to make a
session pass.
