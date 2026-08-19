# V4-3 CA Schedule-59 — IDX Announcements Attempt Implemented

Date: 2026-08-19
Branch: `data/v4-3-ca-training-domain-schedule59-idx-announcements-v1`
Status: `READY_FOR_FOCUSED_TEST_AND_ONE_SHOT_LOCAL_ACQUISITION`

Implemented files:
- `config/v4_3_ca_training_domain_schedule_59_idx_announcements_v1.json`
- `src/idx_trade/v4_3_ca_schedule59_idx_announcements.py`
- `scripts/run_v4_3_ca_training_domain_schedule_59_idx_announcements_acquisition.py`
- focused tests for helper and acquisition contracts.

The acquisition verifies the exact frozen residual-59 diagnosis and the exact zero-yield KSEI News adjudication before creating any provider session. It then queries the official IDX `ListedCompany/GetAnnouncement` endpoint per deterministic ticker/source-date window, captures raw JSON, selects candidate announcements by preregistered event-family title/subject terms, and captures only attachments whose final locator remains on an official IDX host.

Provider result does not admit semantics. Any exact transition/non-blocking decision must be performed by a separate offline adjudication using the already frozen semantics. Existing KSEI artifacts are immutable and are not retried.

Stop rule remains: if this genuinely different IDX surface produces no material semantic progress after offline adjudication, broad CA provider grinding stops; at most one issuer-IR fallback may be considered after explicit review.
