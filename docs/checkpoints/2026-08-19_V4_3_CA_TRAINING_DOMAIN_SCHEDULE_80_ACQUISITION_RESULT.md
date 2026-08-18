# V4-3 CA Training-Domain Schedule-80 — KSEI Acquisition Result

Date: 2026-08-19
Branch: `data/v4-3-ca-training-domain-schedule-80-ksei-v1`
Status: `RAW_OFFICIAL_KSEI_CORPUS_FROZEN_FOR_OFFLINE_ADJUDICATION`

## Accepted local acquisition result

The exact 80-event schedule-required scope was acquired once from the official
KSEI corporate-action schedule publication pages under the frozen acquisition
contract. The run completed successfully and did not perform semantic
admission.

Observed result:

- schedule events: **80**;
- event identity SHA-256:
  `f89cd1e86b1de5f88792551a993311700e4ab15db19f8447e6e8dd61dec3594d`;
- index queries: **111**;
- failed index queries: **0**;
- index parse failures: **30**;
- events with candidate documents: **74**;
- events without candidate documents: **6**;
- unique candidate documents: **89**;
- baseline exact-transition parse diagnostics: **1**;
- provider-failed documents: **0**;
- successful raw-response identity SHA-256:
  `2f83dfa2753fd9ea2eec2d20f5720f036ac71c628a2d495b88b2f4a0f7dd57a3`.

Acquisition manifest SHA-256:

`a7b10ded6246102d6d7858546fdb955ad426bf9a18f762239245a7253f801765`

The manifest is now pinned in
`config/v4_3_ca_training_domain_schedule_80_adjudication_v1.json`.

## Scientific boundary

This acquisition result contains raw official KSEI evidence and parse
diagnostics only. It did **not**:

- admit any transition/non-blocking event semantics;
- choose an event subset based on gate impact;
- use price behavior;
- use Record/Distribution dates as market transition dates;
- materialize historical targets/ranks;
- fit a model, generate predictions, or compute performance;
- access protected/fresh-forward outcomes.

The next step is a fully offline semantic adjudication over the frozen raw
corpus. No provider retry or new document discovery is authorized merely because
some events remain unresolved after adjudication.
