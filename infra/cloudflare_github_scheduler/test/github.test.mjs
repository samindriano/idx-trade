import test from 'node:test';
import assert from 'node:assert/strict';
import { SLOT_BY_ID, localTimeEpochMs } from '../src/core.mjs';
import {
  GithubApiError,
  MAX_RUN_QUERY_PAGES,
  dispatchWorkflow,
  queryExactSlotCoverage,
} from '../src/github.mjs';

const epoch = (t) => localTimeEpochMs('2026-08-27', t);
const jsonResponse = (payload, status = 200, headers = {}) => new Response(
  JSON.stringify(payload),
  { status, headers: { 'content-type': 'application/json', ...headers } },
);

test('query accepts exact native and watchdog dispatch identities only', async () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  const fetchFn = async () => jsonResponse({ workflow_runs: [
    { id: 10, event: 'workflow_dispatch', head_branch: 'main', created_at: new Date(epoch('18:36')).toISOString(), display_title: 'IDX-SLOT:E2E_POST_EOD_1835' },
    { id: 11, event: 'schedule', head_branch: 'main', created_at: new Date(epoch('18:37')).toISOString(), display_title: 'IDX-SLOT:E2E_POST_EOD_1835' },
    { id: 12, event: 'schedule', head_branch: 'main', created_at: new Date(epoch('18:37')).toISOString(), display_title: 'IDX-SLOT:E2E_PREOPEN_0903' },
    { id: 13, event: 'schedule', head_branch: 'main', created_at: new Date(epoch('18:37')).toISOString() },
  ] });
  const runs = await queryExactSlotCoverage({ fetchFn, owner: 'samindriano', repo: 'idx-trade', token: 'x', slot, epochMs: epoch('18:40') });
  assert.deepEqual(runs.map((run) => run.id), [10, 11]);
});

test('query follows GitHub pagination until an exact later-page run is found', async () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  const seenPages = [];
  const fetchFn = async (url) => {
    const page = Number(new URL(url).searchParams.get('page'));
    seenPages.push(page);
    if (page === 1) {
      return jsonResponse(
        { workflow_runs: [
          { id: 20, event: 'schedule', head_branch: 'main', created_at: new Date(epoch('18:36')).toISOString(), display_title: 'IDX-SLOT:E2E_PREOPEN_0903' },
        ] },
        200,
        { link: '<https://api.github.test/runs?page=2>; rel="next"' },
      );
    }
    return jsonResponse({ workflow_runs: [
      { id: 21, event: 'workflow_dispatch', head_branch: 'main', created_at: new Date(epoch('18:38')).toISOString(), display_title: 'IDX-SLOT:E2E_POST_EOD_1835' },
    ] });
  };

  const runs = await queryExactSlotCoverage({ fetchFn, owner: 'samindriano', repo: 'idx-trade', token: 'x', slot, epochMs: epoch('18:40') });
  assert.deepEqual(seenPages, [1, 2]);
  assert.deepEqual(runs.map((run) => run.id), [21]);
});

test('query fails closed instead of silently truncating an excessive pagination chain', async () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  let calls = 0;
  const fetchFn = async () => {
    calls += 1;
    return jsonResponse(
      { workflow_runs: [] },
      200,
      { link: '<https://api.github.test/runs?page=next>; rel="next"' },
    );
  };
  await assert.rejects(
    queryExactSlotCoverage({ fetchFn, owner: 'samindriano', repo: 'idx-trade', token: 'x', slot, epochMs: epoch('18:40') }),
    (error) => error instanceof GithubApiError && error.code === 'GITHUB_RUN_QUERY_PAGINATION_LIMIT',
  );
  assert.equal(calls, MAX_RUN_QUERY_PAGES);
});

test('query failure is fail-closed and never converted to missing coverage', async () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  await assert.rejects(
    queryExactSlotCoverage({ fetchFn: async () => new Response('', { status: 503 }), owner: 'samindriano', repo: 'idx-trade', token: 'x', slot, epochMs: epoch('18:40') }),
    (error) => error instanceof GithubApiError && error.code === 'GITHUB_RUN_QUERY_HTTP_503',
  );
});

test('dispatch sends exact ref and input and captures returned run id', async () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  let seen;
  const fetchFn = async (url, init) => {
    seen = { url, init };
    return jsonResponse({ workflow_run_id: 12345, run_url: 'x', html_url: 'y' }, 200);
  };
  const result = await dispatchWorkflow({ fetchFn, owner: 'samindriano', repo: 'idx-trade', token: 'secret', ref: 'main', slot });
  assert.equal(result.ok, true);
  assert.equal(result.runId, 12345);
  assert.deepEqual(JSON.parse(seen.init.body), { ref: 'main', inputs: { phase: 'POST_EOD', trigger_slot: 'E2E_POST_EOD_1835' } });
  assert.equal(seen.init.headers.Authorization, 'Bearer secret');
});

test('dispatch classifies GitHub 429 as retryable without throwing', async () => {
  const slot = SLOT_BY_ID.get('STOCKBIT_INTRADAY_1830');
  const result = await dispatchWorkflow({ fetchFn: async () => new Response('', { status: 429 }), owner: 'samindriano', repo: 'idx-trade', token: 'x', slot });
  assert.deepEqual(result, { ok: false, status: 429, retryable: true, runId: null });
});

test('dispatch classifies auth failure as non-retryable', async () => {
  const slot = SLOT_BY_ID.get('STOCKBIT_INTRADAY_1830');
  const result = await dispatchWorkflow({ fetchFn: async () => new Response('', { status: 403 }), owner: 'samindriano', repo: 'idx-trade', token: 'x', slot });
  assert.equal(result.retryable, false);
});
