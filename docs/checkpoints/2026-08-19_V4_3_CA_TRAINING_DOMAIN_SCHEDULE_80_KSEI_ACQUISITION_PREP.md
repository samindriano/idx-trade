# V4-3 CA Training-Domain Schedule-80 — Official KSEI Acquisition Prep

Date: 2026-08-19 Asia/Jakarta  
Branch: `data/v4-3-ca-training-domain-schedule-80-ksei-v1`  
Status: `READY_FOR_ONE_BOUNDED_OFFICIAL_KSEI_ACQUISITION`

## Frozen parent result

The schedule-80 offline reuse census completed with:

- manifest SHA-256 `d99252308d4aad1982ef97d3897315930b552b5de739ba85a5720ed07ac49022`;
- exact event count `80`;
- exact event/residual identity SHA-256
  `f89cd1e86b1de5f88792551a993311700e4ab15db19f8447e6e8dd61dec3594d`;
- existing exact transitions reused `0`;
- existing exact non-blocking events reused `0`;
- conflicting existing evidence `0`;
- residual events requiring acquisition `80`.

Therefore the next provider scope is the **entire frozen 80-event set**. No event
is selected or omitted according to gate contribution.

## Authoritative source-date metadata

The provider runner does not infer query months from signal dates, prices, or
old validation-domain inputs. It joins the exact 80 `event_id + ticker` keys to
the immutable blocked KSEI-129 training-domain replay:

- replay manifest SHA-256
  `c115ea0bec59cab4da0cda45ee66ba2be5814e0bb9e854e3f7ecd616edc83861`;
- replay status
  `V4_3_CA_TRAINING_DOMAIN_KSEI_129_OFFLINE_REPLAY_BLOCKED_REVIEW_REQUIRED`;
- canonical event audit child
  `v4_3_ca_training_event_semantics_ksei129.csv`.

The replay manifest's own `event_audit` child hash is verified at runtime before
any network call. Every selected event must have exactly one matching replay
metadata row, remain `SCHEDULE_REQUIRED`, preserve source type/family, and have
at least one explicit immutable `source_dates` value. Any mismatch or missing
source date stops the run before provider access.

## Provider scope

Provider: official public KSEI corporate-action schedules only.

The transport/category policy reuses the already-reviewed schedule-acquisition
implementation in `scripts/run_v4_ca_schedule_acquisition.py`:

- exact category mapping by source type;
- fallback remains within official KSEI schedule categories only;
- month halo exactly `-2,-1,0,+1,+2` around each frozen source date;
- 3 attempts maximum with fixed `1s,3s` backoff;
- ticker must appear in the official index subject before a document becomes a
  candidate;
- raw index and document responses are append-only in a fresh output root;
- no alternate provider or source substitution.

## Deliberate acquisition/adjudication split

The live runner **does not admit any event semantics**. It captures:

- frozen 80-event scope;
- frozen unique index-query scope;
- raw official KSEI index/document bytes;
- event-to-candidate-document links;
- fixed current-parser diagnostics;
- complete request records and hashes.

Parser diagnostics are non-admissive. In particular, Record/Distribution fields
from the live parse are not allowed to resolve an event. This preserves the
previous stock-split layout hardening and prevents a live result from silently
reintroducing the reparsed Record/Distribution linkage issue.

After this one bounded provider run, raw-corpus identity is frozen. The next
step must be a separate **offline** semantic adjudication using already-frozen
strict transition/non-blocking rules. No parser/semantic relaxation is allowed
because an observed provider result is inconvenient.

## New files

- config:
  `config/v4_3_ca_training_domain_schedule_80_ksei_v1.json`
- live acquisition runner:
  `scripts/run_v4_3_ca_training_domain_schedule_80_ksei_acquisition.py`
- tests:
  `tests/test_v4_3_ca_training_domain_schedule_80_ksei_acquisition.py`

## Hard boundaries

This lane does not change the V4-3 target/model/evaluation contract. It does not
read or materialize R5/R10, historical targets/ranks, model fits, predictions,
performance, bootstrap output, or protected/fresh-forward outcomes. It does not
waive exact mechanical crossings, retry the 45 coverage-unresolved tickers,
change the 0.90 gate, or choose a pass-preserving event subset.

## Local execution contract

Before provider access, local validation must pass:

1. `py_compile` for the new runner and reuse helper;
2. focused acquisition/reuse tests;
3. output root must not already exist.

Then exactly one acquisition run is authorized against the exact reuse/replay
roots. Stop after the acquisition JSON. Do not rerun to improve provider
coverage and do not patch the parser after observing the corpus.

## Coordination

Canonical `origin/main:coordination/TEAM_STATUS.md` was inspected before this
lane was created and no overlapping ACTIVE V4-3 schedule-acquisition lane was
identified. The canonical shared ledger has not been modified by ChatGPT; the
connector does not provide a safe row-level edit for that large shared file.
