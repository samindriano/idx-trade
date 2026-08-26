# E2E PREOPEN_CA Workflow Activation

The production E2E cloud workflow now invokes the accepted V3 runner at
`6e1bf4a1e47a2abff365b35c19687444cf3f0596`.

## Scheduled phases

GitHub cron is UTC. The workflow maps these schedules to Asia/Jakarta phases:

| Phase | Jakarta time | GitHub cron |
| --- | --- | --- |
| PREOPEN_CA | 08:30, 08:45, 08:55 | `30 1`, `45 1`, `55 1` weekdays |
| PREOPEN | 09:03, 09:13, 09:22 | `3 2`, `13 2`, `22 2` weekdays |
| POST_EOD | 18:35, 19:05, 19:35 | `35 11`, `5 12`, `35 12` weekdays |

`PREOPEN_CA` retries share a serialized concurrency group that is distinct
from the `PREOPEN` group. Thus a slow or queued CA retry cannot block a valid
PREOPEN run. The accepted V3 runner enforces the hard 09:02 Asia/Jakarta
cutoff and fails closed after it; it never performs a late CA capture.

The scientific PREOPEN and POST_EOD behavior is otherwise unchanged. No
provider capture, protected outcome access, model/counter mutation, Windows
task change, or manual workflow run was performed for this activation.
