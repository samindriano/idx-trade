import {
  dispatchBody,
  exactSlotCoverageRuns,
  slotWindow,
  workflowDispatchUrl,
  workflowRunsUrl,
} from './core.mjs';

const API_VERSION = '2026-03-10';

function headers(token, contentType = false) {
  const result = {
    Accept: 'application/vnd.github+json',
    Authorization: `Bearer ${token}`,
    'X-GitHub-Api-Version': API_VERSION,
    'User-Agent': 'idx-trade-cloudflare-scheduler-v1',
  };
  if (contentType) result['Content-Type'] = 'application/json';
  return result;
}

export class GithubApiError extends Error {
  constructor(code, status = 0) {
    super(code);
    this.name = 'GithubApiError';
    this.code = code;
    this.status = status;
  }
}

export async function queryExactSlotCoverage({ fetchFn = fetch, owner, repo, token, slot, epochMs }) {
  const { dateStartMs, cutoffMs } = slotWindow(slot, epochMs);
  const endMs = Math.min(epochMs, cutoffMs - 1);
  if (endMs < dateStartMs) return [];
  const url = workflowRunsUrl({
    owner,
    repo,
    workflow: slot.workflow,
    startMs: dateStartMs,
    endMs,
  });
  const response = await fetchFn(url, { method: 'GET', headers: headers(token) });
  if (!response.ok) throw new GithubApiError(`GITHUB_RUN_QUERY_HTTP_${response.status}`, response.status);
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new GithubApiError('GITHUB_RUN_QUERY_INVALID_JSON', response.status);
  }
  if (!Array.isArray(payload?.workflow_runs)) {
    throw new GithubApiError('GITHUB_RUN_QUERY_MISSING_LIST', response.status);
  }
  return exactSlotCoverageRuns(payload.workflow_runs, slot, epochMs);
}

export function isRetryableGithubStatus(status) {
  return status === 408 || status === 409 || status === 429 || status >= 500;
}

export async function dispatchWorkflow({
  fetchFn = fetch,
  owner,
  repo,
  token,
  ref = 'main',
  slot,
  body = null,
}) {
  const requestBody = body ?? dispatchBody(slot, ref);
  const response = await fetchFn(workflowDispatchUrl({ owner, repo, workflow: slot.workflow }), {
    method: 'POST',
    headers: headers(token, true),
    body: JSON.stringify(requestBody),
  });
  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      retryable: isRetryableGithubStatus(response.status),
      runId: null,
    };
  }
  let runId = null;
  if (response.status !== 204) {
    try {
      const payload = await response.json();
      if (Number.isInteger(payload?.workflow_run_id)) runId = payload.workflow_run_id;
    } catch {
      // A successful dispatch without a readable body is still an accepted trigger request.
    }
  }
  return { ok: true, status: response.status, retryable: false, runId };
}