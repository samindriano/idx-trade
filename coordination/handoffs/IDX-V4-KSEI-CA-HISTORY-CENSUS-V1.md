# Handoff — IDX-V4-KSEI-CA-HISTORY-CENSUS-V1

from: ChatGPT
to: Codex local-runtime operator
branch: `data/idx-v4-ksei-ca-history-census-v1`
scientific_code_anchor: `57a15599cf96205bc75f3f5e8b593eac0a77c4cd`
parent: `data/idx-v4-corporate-action-continuity-gate-v1@7e03cdf7023590ea5b7881a61b4e0a958f147d25`
status: `READY_FOR_EXACT_LOCAL_PROVIDER_RUN`

## Before any provider call

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md`.
2. Add/update only the V4 KSEI CA-history census lane as `ACTIVE`, preserving every unrelated row.
3. Pull this branch and verify the scientific implementation files are unchanged from anchor `57a15599cf96205bc75f3f5e8b593eac0a77c4cd`. Documentation-only commits after that anchor are expected.
4. Set `PYTHONPATH=src` for the commands below.

If source code/config differs from the anchor, STOP for ChatGPT review.

## Inputs

Blocked CA gate external root:

`D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3`

Required exact files:

- `v4_frozen_continuity_ledger.csv` — SHA-256 `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`
- `event_family_evidence.csv` — SHA-256 `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`

## Validation first

Run:

`python -m pytest tests/test_v4_ksei_ca_history.py`

`python -m py_compile src/idx_trade/v4_ksei_ca_history.py src/idx_trade/v4_ca_continuity_remediation.py scripts/run_v4_ksei_ca_history_census.py scripts/run_v4_ca_continuity_gate_v2.py`

`git diff --check`

Also confirm `curl_cffi` imports successfully in the provider runtime.

If any validation/import fails: STOP. Do not patch source in the same provider run.

## Exact 610-ticker KSEI census

Use a fresh output path:

`D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1`

Run only:

`python scripts/run_v4_ksei_ca_history_census.py --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" --output-dir "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1"`

Do not substitute another provider/URL if KSEI returns errors. The script's frozen three-attempt policy is the only retry mechanism.

## Offline continuity gate V2

After the census finishes, regardless of whether some ticker coverage remains unresolved, run the frozen fail-closed gate into a fresh root:

`D:\Documents\Project\idx-v4-ca-continuity-gate-ksei-remediation-20260817-v1`

Command:

`python scripts/run_v4_ca_continuity_gate_v2.py --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" --prior-event-evidence "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\event_family_evidence.csv" --ksei-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" --output-dir "D:\Documents\Project\idx-v4-ca-continuity-gate-ksei-remediation-20260817-v1"`

Then STOP.

## Return exactly

- focused pytest result, py_compile, `git diff --check`;
- census status;
- requested / coverage-certified / unresolved ticker counts;
- total KSEI history rows;
- active mechanical rows and active unknown rows;
- event-family-source counts for active mechanical/unknown rows;
- provider HTTP/parse failure counts and affected tickers;
- census `MANIFEST.json` SHA-256;
- continuity V2 verdict;
- resolved vs unresolved ticker count and reason counts;
- H5 / H10 / consensus gate dates out of 600 and minimum coverage rates;
- `corporate_action_continuity_certified`;
- continuity V2 manifest SHA-256;
- exact output paths;
- git status.

Promote only small summary/manifest/ticker-coverage/ticker-classification/per-date artifacts plus checkpoint/handoff. Keep raw HTML, full KSEI history, and full continuity ledger external.

Update only the canonical lane to `REVIEW` (or `BLOCKED` if runtime infrastructure itself fails), then push and STOP.

## Hard prohibitions

No R5/R10, target ranks, model fit, predictions, IC/Top30/spread/raw-return/bootstrap performance, protected/fresh-forward outcomes, V4 contract changes, or post-result parser/quarantine tuning.
