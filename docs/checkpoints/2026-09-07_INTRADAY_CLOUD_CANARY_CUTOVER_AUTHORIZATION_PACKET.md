# Intraday Cloud Canary Cutover Authorization Packet

Date: 2026-09-07 (Asia/Jakarta)

## Decision

**INTRADAY_CANARY_PREPARATION_BLOCKED**

This packet is a preparation/authorization record. It does not authorize merging
PR #122, deploying the Worker, changing the Windows task, dispatching a production
capture workflow, invoking a provider, writing to a production capture prefix, or
changing secrets. The bounded candidate scope change below is not a production
deployment.

The candidate implementation is test-green and the bounded candidate recovery
scope is now `STOCKBIT_INTRADAY_2030`, but cutover authorization is not safe
because:

1. the production Worker is not live, and the GitHub read/write credential
   availability is not proven; and
2. there is no genuine Cloudflare shadow/cutover run or provider/R2 completion
   evidence.

The reported same-slot issue is classified
`NOT_A_CORE_DEFECT_CANARY_SCOPE_SELECTION_PROBLEM`: the accepted contract is
cross-slot recovery, and the existing lease fence remains unchanged. The 20:30
canary is selected because its 20:40 admission follows all three native E2E
POST_EOD opportunities while retaining one exact recovery slot.

## A-I closure matrix

| Area | Classification | Evidence / boundary |
|---|---|---|
| A. Refs and candidate | PASS for preparation | Starting candidate=`eb50d99516e55c8a69c65c85e591390410ae8d06`; final implementation commit=`eb6955b6fac53805360cae603d9867745e895df2`; `origin/main`=`9b070894535c0c0fc13bc441f004f5d0a8039cb9`; PR #122 remains open/draft on this branch. The only candidate behavior change is the exact active recovery scope `1830 -> 2030`. |
| B. R2 identity/completion | **PASS for identity / completion still UNKNOWN** | One authorized smoke run independently matched the explicitly named bucket. Run `34091613722`, main SHA `9b070894535c0c0fc13bc441f004f5d0a8039cb9`, wrote `stockbit-intraday-smoke-v1/smoke-20260907-d34067e7ab2e442e901f4bb92e69d954/conditional-write-probe.json`; GitHub returned SHA `65def3b099c03855a6e64ef17213e0b9eaf380d0cc767605fb7e0b8d2e6234d7`, and independent `wrangler r2 object get` from `idx-trade-stockbit-stream-v1` returned 296 identical bytes and the same SHA. The smoke proved first create, identical replay suppression, and conflicting-write rejection with zero provider calls. It does not prove a production completion marker. |
| C. Rollback | PASS for preparation | Durable package exists at `C:\Users\Sam\AppData\Local\IDXTrade\rollback-packages\intraday-canary-precutover-20260907-131918`; manifest, task XML, launcher, installed V1 script, snapshot, checksums, and restore instructions are included. Live task/action/triggers and package hashes match. |
| D. Credentials/access | PARTIAL / blocking | Cloudflare OAuth read access and dry-run binding visibility are proven. `GITHUB_ACTIONS_READ_TOKEN`, `GITHUB_ACTIONS_WRITE_TOKEN`, and runtime binding authorization are not proven. Secret values were not exposed. |
| E. Isolation | PASS | `RECOVERY_ALLOWED_SLOTS=["STOCKBIT_INTRADAY_2030"]`. All E2E, Official Open, and Intraday 18:30/19:30 slots fail closed before lease/archive/token/POST; Stream is outside the scheduler slot table. Native GitHub Intraday schedules remain unchanged. |
| F. Canonical EOD prerequisite | PASS for selected-slot timing / cross-slot contract | Accepted E2E bridge `043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2` requires the canonical EOD manifest/commit and guards. The selected 20:30 path checks at 20:40, after the 18:35/19:05/19:35 E2E opportunities. `WAITING_CANONICAL_EOD_GATE` is validated as recoverable intermediate state for a later logical slot; same-slot lease takeover remains correctly fenced. |
| G. Deployment | NOT EXECUTED | `wrangler.production.jsonc` dry-run passed and showed the intended Worker/bindings/scope. No production Worker deployment, cron activation, secret mutation, or dispatch was performed. Worker deployment/secret listing reported no existing production Worker. |
| H. Hosted validation | PASS for static/local/hosted checks | `npm test`: 95/95. Focused Intraday recovery/early-completion pytest: pass. Full pytest: exit 0, three existing FutureWarnings. All three Wrangler deploy dry-runs passed. Fresh hosted run `34092731780` passed the full pytest job at packet-parent head `da4a346834791b72e943bbaaad6e4633cfb3416e`; `e2e-preflight` run `34092731777` was skipped by workflow policy. PR #122 is open/draft and clean/mergeable. None of these checks establish provider calls, production R2 completion, or cutover. |
| I. Cutover/rollback authorization | **NO-GO** | Cutover prerequisites are not all satisfied. Keep Windows watchdog and current workflow state unchanged. Do not deploy or dispatch. |

## Exact implementation and runtime evidence

Candidate scheduler files:

- `infra/cloudflare_github_scheduler/src/index.js` lines 133-144: recovery
  scope gate precedes owner/read-token, lease, archive, and dispatch work.
- `infra/cloudflare_github_scheduler/src/index.js` lines 552-589: scheduled
  execution invokes the same bounded slot gate.
- `infra/cloudflare_github_scheduler/src/core.mjs` lines 67-143: production
  slot parsing and fail-closed scope decisions.
- `infra/cloudflare_github_scheduler/wrangler.production.jsonc`: intended
  Worker `idx-trade-github-scheduler-v1`, Durable Object coordinator, R2
  binding `ARCHIVE` to `idx-trade-stockbit-stream-v1`, and five cron groups.

The enabled scope was code-exercised without reaching lease, archive, token, or
GitHub POST operations. The scope result was:

```text
STOCKBIT_INTRADAY_2030  RECOVERY_SCOPE_SLOT_ENABLED
all other E2E/Open/Intraday slots  RECOVERY_SCOPE_SLOT_DISABLED_NO_DISPATCH
Stockbit Stream  outside scheduler slot table
```

The production Windows task remains the current V1 deployment:

```text
Task:   IDXTrade-GitHub-Cloud-Dispatch-Watchdog
State:  Ready / enabled
Action: C:\Users\Sam\AppData\Local\IDXTrade\wd-v1-cb9c0bcc\watchdog.cmd
Last:   2026-09-07 09:22:01 +07, result 0
Next:   18:40 +07
```

The package hashes are:

```text
task.xml       CD45BC882B6CE160E291E2591A7B43297854FA3C00AFAE99337462CF0C9EE929
watchdog.cmd   8909407A0AAA701646573D9361A11C91BCCDA49B001AAC7C0457008E896E9E80
V1 script      7641BAF7C5F02F35C29B256C9F2231B66363E5014114E43C4EB6D78E02F3A5D0
manifest       AD34CC7337539BFA99A21B02B3D55122641FA087D03A361D29292198B40846BB
```

The isolated R2 identity smoke was run exactly once from remote `main`:

```text
workflow: .github/workflows/stockbit-intraday-r2-smoke-v1.yml
run:      34091613722
main:     9b070894535c0c0fc13bc441f004f5d0a8039cb9
prefix:   stockbit-intraday-smoke-v1/smoke-20260907-d34067e7ab2e442e901f4bb92e69d954
object:   conditional-write-probe.json
sha256:   65def3b099c03855a6e64ef17213e0b9eaf380d0cc767605fb7e0b8d2e6234d7
readback: 65def3b099c03855a6e64ef17213e0b9eaf380d0cc767605fb7e0b8d2e6234d7
first create=true; identical replay=false; conflicting write rejected=true
provider_calls=0; production_prefix_written=false; outcome_accessed=false
```

Independent `wrangler r2 object get --remote` from bucket
`idx-trade-stockbit-stream-v1` returned the exact 296-byte object and the exact
same SHA. This is `R2_BUCKET_IDENTITY_MATCH` for the GitHub smoke path. Direct
reads of `e2e-paper-v1/sessions/{2026-09-03,2026-09-04,2026-09-05,2026-09-06}/stages/POST_EOD/commit.json`
were absent, so historical valid canonical POST_EOD completion was not proven.
GitHub history likewise showed the sampled Sep 3-4 POST_EOD runs failing and
scheduled creation delayed by hours; this supports selecting 20:30 structurally
but is not a production completion claim.

The implementation scope commit is
`eb6955b6fac53805360cae603d9867745e895df2`; the packet-parent evidence commit
is `da4a346834791b72e943bbaaad6e4633cfb3416e`. Both were pushed to
`codex/cloud-runtime-recovery-integration-v1` and PR #122 remains draft/unmerged.

## Required closure before any cutover request

1. Preserve the current non-reclaiming lease fence. Do not add a same-slot
   redispatch: the intended recovery opportunity is the next logical Intraday
   slot, whose runner restores verified prior progress and is blocked if a later
   slot has already committed.
2. Re-run the full validation on the exact merge candidate and record the
   results; keep the preflight skip visible rather than treating it as proof.
3. Establish the remaining R2 completion authority without exposing secrets:
   read-only inspection must verify the expected immutable
   `stockbit-intraday-v1` commit/manifest schema and hashes after an authorized
   canary. The bucket identity itself is proven by the smoke above.
4. Prove credential readiness by names/permissions and a safe non-provider,
   non-write check. Do not probe provider credentials or issue a GitHub dispatch
   as a readiness test.
5. Obtain explicit authorization for the exact first slot, `2030`; do not
   broaden the configured scope implicitly.
6. Preserve the rollback package and verify the task snapshot immediately before
   any authorized mutation. Rollback means restoring the packaged task XML and
   V1 launcher/script, then checking task state, action, triggers, and hashes.

## Stop and rollback boundaries

Stop immediately on any unexpected slot, workflow, branch/ref, Worker binding,
R2 bucket, lease state, token state, provider call, or archive key. A failed or
uncertain GitHub dispatch is non-reclaimable; do not retry it automatically.

Before authorization, rollback is not needed because no mutation occurred. If a
later authorized cutover changes the Windows task and a rollback is ordered,
use only the packaged `RESTORE-AND-VERIFY.md` procedure under the package path
above and verify the exact task snapshot and hashes. Do not delete the package,
disable the current watchdog, or alter unrelated scheduled tasks.

## Evidence limits

The following remain UNKNOWN and must not be represented as success: live
Cloudflare execution, provider/outcome capture, production R2 object completion,
GitHub credential usability, exact secret-to-Worker-binding equality,
cross-scheduler exactly-once behavior, and the 2026-09-03 incident cause. A
successful hosted step, smoke object, or nonzero R2 object count is not
production completion evidence.
