# Stockbit Stream Transient Retry Remediation

Date: 2026-08-23
Branch: `fix/stockbit-stream-daily-capture-v1`

## Observed full-capture failure

The first full `top_n=200` workflow run on the daily-capture fix branch was
run once at GitHub Actions run `32615513888`. It reached all 200 Stockbit
requests and persisted the run manifest, but returned:

- `198` `OK` responses;
- `1` `HTTP_503` response;
- `1` `HTTP_520` response;
- final status `PARTIAL_FAILURE`.

The existing fail-closed status gate correctly refused to call this run
`DATA_READY`. This was a transient-provider resilience gap, not an IDX
universe or R2 credential failure.

## Bounded remediation

The capture runner now retries a stream request at most once only when the
first response has an explicitly allowlisted transient HTTP 5xx status:

`500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526`.

4xx responses and malformed/empty payloads remain fail-closed. The final
response is the only response promoted to the ticker's raw/normalized
artifacts; the manifest preserves the per-attempt HTTP statuses and observed
timestamps. The quota guard reserves the worst-case two provider calls per
planned ticker, and the manifest records the actual provider-call count.

`DATA_READY` still requires every planned ticker to finish with a final
`OK` classification. A transient failure that persists through the bounded
retry remains `PARTIAL_FAILURE` and is not silently dropped.

## Validation

- focused capture/archive tests: `14 passed`;
- `py_compile`: pass;
- `git diff --check`: pass.

No model, outcome, counter, or unrelated data lane was accessed.
