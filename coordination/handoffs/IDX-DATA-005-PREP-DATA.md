# Handoff
from: DATA
to: MAIN
task_id: IDX-DATA-005-PREP
model_used: GPT-5.6 Thinking
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: 5e6f6bd38a5af3ee11bca93a15f50fadf9515eb2
branch: data/idx-data-005-1260-prep
head_commit: PENDING_FINAL_PREP_COMMIT
scope: Prepare a separate, non-executing 1260-session historical-expansion branch while the 504-session repair remains the active certification dependency.
files_changed:
- src/idx_trade/history_preflight.py
- tests/test_history_preflight.py
- docs/checkpoints/2026-08-09_1260_SESSION_PREP.md
- coordination/handoffs/IDX-DATA-005-PREP-DATA.md
findings:
- A certified 504-session baseline can expand to 1260 by adding exactly 756 older official sessions when the baseline is the exact trailing suffix.
- A dedicated preflight is useful at five-year scale to prevent calendar drift, accidental baseline rewrites, and unnecessary Stock Summary refetches.
- Stock Summary cache reuse is defensible only when both the parquet snapshot and metadata JSON exist for a session; partial entries should be refetched.
- The 1260 branch can be prepared independently, but actual certification remains blocked until the repaired 504 gate passes and its panel/manifest are frozen.
decisions_made:
- Keep data/idx-data-002c focused on repairing/certifying 504; prepare 1260 on a separate branch.
- Require 504 to be an exact official-session suffix of the 1260 target before expansion.
- Run the eventual ladder as [504, 1260], preserving 504 as the regression gate.
- Reuse official caches and fetch only the additional/uncached historical segment where possible.
decisions_needed:
- MAIN should integrate/rebase this prep only after 504 is certified and after reviewing any 504 repair commits that landed after source_commit.
blocking_risks:
- 504 is not yet certified at the source commit used for this prep branch.
- Five-year source coverage may expose older identity, delisting, legal-state, Yahoo-history, corporate-action, or IDX schema boundaries.
- This branch has not performed a 1260 network/data run and must not be interpreted as a PASS.
validation_run:
- Unit tests added for exact trailing-window selection, insufficient calendar rejection, exact suffix enforcement, cache-pair auditing, persisted preflight artifacts, and 1260-from-504 delta=756.
- GitHub CI should be required green before integration.
recommended_next_action:
- Finish targeted 504 repair on data/idx-data-002c. If 504 certifies and manifest verification is valid, reconcile this prep branch with the certified 504 head, run full tests, then execute the persisted preflight before any 1260 network work.
