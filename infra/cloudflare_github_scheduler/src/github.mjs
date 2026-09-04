import {
  exactSlotCoverageRuns,
  slotWindow,
  workflowDispatchUrl,
  workflowRunsUrl,
} from './core.mjs';

const API_VERSION = '2026-03-10';
const MAX_RUN_QUERY_PAGES = 20;

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

function pageUrl(baseUrl, page) {
  const url = new URL(baseUrl);
  url.searchParams.set('page', String(page));
  return url.toString();
}

function hasNextPage(response) {
  const link = response?.headers?.get?.('link');
  return typeof link === 'string' && /<[^>]+>;\s*rel="next"/.test(link);
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
  const baseUrl = workflowRunsUrl({
    owner,
    repo,
    workflow: slot.workflow,
    startMs: dateStartMs,
    endMs,
  });

  for (let page = 1; page <= MAX_RUN_QUERY_PAGES; page += 1) {
    const response = await fetchFn(pageUrl(baseUrl, page), {
      method: 'GET',
      headers: headers(token),
    });
    if (!response.ok) {
      throw new GithubApiError(`GITHUB_RUN_QUERY_HTTP_${response.status}`, response.status);
    }
    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new GithubApiError('GITHUB_RUN_QUERY_INVALID_JSON', response.status);
    }
    if (!Array.isArray(payload?.workflow_runs)) {
      throw new GithubApiError('GITHUB_RUN_QUERY_MISSING_LIST', response.status);
    }
    const exact = exactSlotCoverageRuns(payload.workflow_runs, slot, epochMs);
    if (exact.length) return exact;

    const next = hasNextPage(response);
    if (!next) return [];
    if (page === MAX_RUN_QUERY_PAGES) {
      throw new GithubApiError('GITHUB_RUN_QUERY_PAGINATION_LIMIT', response.status);
    }
  }
  throw new GithubApiError('GITHUB_RUN_QUERY_PAGINATION_LIMIT');
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
  body,
  nowFn = Date.now,
}) {
  // Body construction belongs to the pre-dispatch preparation phase.  Do
  // not synthesize a request body here after the side-effect boundary has
  // been entered.
  if (typeof token !== 'string' || !token.trim()) {
    return {
      ok: false,
      status: 'DISPATCH_TOKEN_INVALID',
      retryable: false,
      runId: null,
    };
  }
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return {
      ok: false,
      status: 'DISPATCH_BODY_INVALID',
      retryable: false,
      runId: null,
    };
  }
  let serializedBody;
  try {
    serializedBody = JSON.stringify(body);
  } catch {
    return {
      ok: false,
      status: 'DISPATCH_BODY_INVALID',
      retryable: false,
      runId: null,
    };
  }
  if (typeof serializedBody !== 'string') {
    return {
      ok: false,
      status: 'DISPATCH_BODY_INVALID',
      retryable: false,
      runId: null,
    };
  }
  // Revalidate wall-clock eligibility immediately before the GitHub POST.
  // GitHub/R2 reads can consume enough time that the coordinator's initial
  // observation is stale; that earlier timestamp must never authorize a late
  // workflow_dispatch after the prospective cutoff.
  const dispatchEpochMs = Number(nowFn());
  const dispatchWindow = slotWindow(slot, dispatchEpochMs);
  if (
    !Number.isFinite(dispatchEpochMs)
    || dispatchEpochMs < dispatchWindow.checkMs
    || dispatchEpochMs >= dispatchWindow.cutoffMs
  ) {
    return {
      ok: false,
      status: 'DISPATCH_WINDOW_EXPIRED',
      retryable: false,
      runId: null,
    };
  }

  const response = await fetchFn(workflowDispatchUrl({ owner, repo, workflow: slot.workflow }), {
    method: 'POST',
    headers: headers(token, true),
    body: serializedBody,
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

export { MAX_RUN_QUERY_PAGES };
