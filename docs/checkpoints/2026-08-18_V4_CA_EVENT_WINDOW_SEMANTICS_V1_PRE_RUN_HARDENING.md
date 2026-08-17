# V4 CA Event-Window Semantics V1 — Pre-Run Hardening Addendum

Date: 2026-08-18 (Asia/Jakarta)
Branch: `data/idx-v4-ca-event-window-semantics-v1`
New controlling scientific-code anchor: `bea191be214bba49b8b65acb1a8556e3266b43e4`
Status: `FROZEN_BEFORE_ANY_EVENT_WINDOW_SUPPORT_OR_SCHEDULE_PROVIDER_RUN`

The preregistered semantics are unchanged.

Before any local/provider execution, review of official KSEI schedule PDFs found that the same regular-market label is rendered as both `Pasar Reguler` and `Pasar Regular`. The large-file connector could not atomically replace the frozen parser, so a small launcher was added:

`scripts/run_v4_ca_schedule_acquisition_hardened.py`

It performs exactly one literal normalization, `Pasar Regular -> Pasar Reguler`, before calling the already-frozen exact schedule parser, then executes the same acquisition runner. It does not alter dates, event identity, linkage, transition semantics, provider scope, retry policy, or gates.

The authorized provider runner for this generation is therefore the hardened launcher, not the underlying acquisition script directly.

No external KSEI history was processed by the new event-window code before this hardening and no new provider call has occurred.
