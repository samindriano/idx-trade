import test from 'node:test';
import assert from 'node:assert/strict';
import { dispatchLeaseDecision, SLOT_BY_ID } from '../src/core.mjs';
import { dispatchWithLeaseBoundary } from '../src/dispatch_lifecycle.mjs';
import { prepareActiveDispatch } from '../src/dispatch_prepare.mjs';
import { dispatchWorkflow } from '../src/github.mjs';

const sessionDate = '2026-09-04';
const epoch = Date.parse('2026-09-04T11:40:00.000Z');
const activeEnv = {
  GITHUB_ACTIONS_WRITE_TOKEN: 'write-token',
  OFFICIAL_OPEN_SCHEDULER_HMAC_KEY: 'hmac-key',
};

function markerStore() {
  return { state: 'dispatching', attemptId: 'attempt-a' };
}

async function runPrepared({ env = activeEnv, slot = SLOT_BY_ID.get('E2E_POST_EOD_1835'), prepareOverrides = {}, fetchFn }) {
  const marker = markerStore();
  let posts = 0;
  const boundary = await dispatchWithLeaseBoundary({
    mode: 'active',
    prepare: () => prepareActiveDispatch({
      env,
      slot,
      ref: 'main',
      sessionDate,
      issuedAtEpochMs: epoch,
      ...prepareOverrides,
    }),
    leaseOwned: () => marker.state === 'dispatching' && marker.attemptId === 'attempt-a',
    onPreDispatchFailure: () => {
      marker.state = 'pre_dispatch_blocked';
      return true;
    },
    dispatch: (prepared) => dispatchWorkflow({
      fetchFn: async (...args) => {
        posts += 1;
        return fetchFn(...args);
      },
      owner: 'samindriano',
      repo: 'idx-trade',
      token: prepared.token,
      ref: 'main',
      slot,
      body: prepared.body,
      nowFn: () => epoch,
    }),
  });
  return { boundary, marker, posts };
}

test('missing write token releases a side-effect-free lease and reaches zero POSTs', async () => {
  const result = await runPrepared({ env: { OFFICIAL_OPEN_SCHEDULER_HMAC_KEY: 'hmac-key' }, fetchFn: async () => new Response('', { status: 204 }) });
  assert.equal(result.boundary.phase, 'pre_dispatch_failure');
  assert.equal(result.boundary.released, true);
  assert.equal(result.marker.state, 'pre_dispatch_blocked');
  assert.equal(dispatchLeaseDecision({ state: result.marker.state }).action, 'ACQUIRE');
  assert.equal(result.posts, 0);
});

test('missing Official Open HMAC key releases a side-effect-free lease and reaches zero POSTs', async () => {
  const result = await runPrepared({ env: { GITHUB_ACTIONS_WRITE_TOKEN: 'write-token' }, slot: SLOT_BY_ID.get('OFFICIAL_OPEN_0922'), fetchFn: async () => new Response('', { status: 204 }) });
  assert.equal(result.boundary.phase, 'pre_dispatch_failure');
  assert.equal(result.boundary.released, true);
  assert.equal(result.marker.state, 'pre_dispatch_blocked');
  assert.equal(dispatchLeaseDecision({ state: result.marker.state }).action, 'ACQUIRE');
  assert.equal(result.posts, 0);
});

test('a signer-local exception releases a side-effect-free lease and reaches zero POSTs', async () => {
  const result = await runPrepared({
    slot: SLOT_BY_ID.get('OFFICIAL_OPEN_0922'),
    prepareOverrides: { attestBody: async () => { throw new Error('SIGNER_LOCAL_FAILURE'); } },
    fetchFn: async () => new Response('', { status: 204 }),
  });
  assert.equal(result.boundary.phase, 'pre_dispatch_failure');
  assert.equal(result.boundary.released, true);
  assert.equal(result.marker.state, 'pre_dispatch_blocked');
  assert.equal(dispatchLeaseDecision({ state: result.marker.state }).action, 'ACQUIRE');
  assert.equal(result.posts, 0);
});

test('a rejected fetch is POST-uncertain and does not reclaim the dispatching fence', async () => {
  const result = await runPrepared({ fetchFn: async () => { throw new Error('NETWORK_REJECTED'); } });
  assert.equal(result.boundary.phase, 'post_attempt_uncertain');
  assert.equal(result.boundary.error.message, 'NETWORK_REJECTED');
  assert.equal(result.marker.state, 'dispatching');
  assert.equal(result.posts, 1);
});

test('observe-only does not prepare credentials or reach dispatch side effect', async () => {
  let prepared = false;
  let dispatched = false;
  const result = await dispatchWithLeaseBoundary({
    mode: 'observe_only',
    prepare: async () => { prepared = true; throw new Error('PREPARE_MUST_NOT_RUN'); },
    leaseOwned: () => true,
    onPreDispatchFailure: () => true,
    dispatch: async () => { dispatched = true; throw new Error('DISPATCH_MUST_NOT_RUN'); },
  });
  assert.equal(result.response.status, 'WOULD_DISPATCH');
  assert.equal(prepared, false);
  assert.equal(dispatched, false);
});

test('deterministic same-slot interleaving has one dispatch boundary and preserves read-only B', async () => {
  const marker = { state: null, attemptId: null };
  let dispatchBoundaries = 0;
  let durableComplete = false;
  let releaseA;
  const aPaused = new Promise((resolve) => { releaseA = resolve; });

  const acquire = (attemptId) => {
    const decision = dispatchLeaseDecision(marker.state === null ? null : {
      state: marker.state,
      attempt_id: marker.attemptId,
    });
    if (decision.action !== 'ACQUIRE') return decision;
    marker.state = 'dispatching';
    marker.attemptId = attemptId;
    return { action: 'ACQUIRE', attemptId };
  };

  const leaseA = acquire('attempt-a');
  assert.equal(leaseA.action, 'ACQUIRE');
  const a = dispatchWithLeaseBoundary({
    mode: 'active',
    prepare: async () => {
      await aPaused;
      return { token: 'write-token', body: { ref: 'main', inputs: {} } };
    },
    leaseOwned: () => marker.state === 'dispatching' && marker.attemptId === 'attempt-a',
    onPreDispatchFailure: () => false,
    dispatch: async () => {
      dispatchBoundaries += 1;
      return { ok: true, status: 204, retryable: false, runId: null };
    },
  });

  await new Promise((resolve) => setImmediate(resolve));
  const leaseB = acquire('attempt-b');
  assert.equal(leaseB.action, 'DEFER');
  assert.equal(leaseB.state, 'dispatching');
  // B may continue the read-only archive/GitHub observation while A is
  // suspended.  A completion appearing at this point is authoritative.
  durableComplete = true;
  const bObservation = { capture_complete: durableComplete, dispatchBoundaries: 0 };
  assert.equal(bObservation.capture_complete, true);
  assert.equal(bObservation.dispatchBoundaries, 0);

  releaseA();
  const aResult = await a;
  assert.equal(aResult.phase, 'response');
  assert.equal(dispatchBoundaries, 1);
  assert.equal(marker.attemptId, 'attempt-a');
  assert.equal(bObservation.capture_complete, true);
});

test('owner loss before POST and owner loss before marker transition prevent overwrite', async () => {
  const marker = { state: 'dispatching', attemptId: 'attempt-a' };
  let dispatchBoundaries = 0;
  const lostBeforePost = await dispatchWithLeaseBoundary({
    mode: 'active',
    prepare: async () => {
      marker.state = 'dispatching';
      marker.attemptId = 'attempt-b';
      return { token: 'write-token', body: { ref: 'main', inputs: {} } };
    },
    leaseOwned: () => marker.state === 'dispatching' && marker.attemptId === 'attempt-a',
    onPreDispatchFailure: () => false,
    dispatch: async () => { dispatchBoundaries += 1; return { ok: true, status: 204, retryable: false, runId: null }; },
  });
  assert.equal(lostBeforePost.phase, 'lease_lost_before_post');
  assert.equal(dispatchBoundaries, 0);

  let ownedWrites = 0;
  const ownedWrite = (attemptId, nextState) => {
    if (marker.state !== 'dispatching' || marker.attemptId !== attemptId) return false;
    marker.state = nextState;
    ownedWrites += 1;
    return true;
  };
  marker.state = 'dispatching';
  marker.attemptId = 'attempt-a';
  const response = await dispatchWithLeaseBoundary({
    mode: 'active',
    prepare: async () => ({ token: 'write-token', body: { ref: 'main', inputs: {} } }),
    leaseOwned: () => true,
    onPreDispatchFailure: () => false,
    dispatch: async () => {
      dispatchBoundaries += 1;
      marker.state = 'dispatching';
      marker.attemptId = 'attempt-b';
      return { ok: true, status: 204, retryable: false, runId: null };
    },
  });
  assert.equal(response.phase, 'response');
  assert.equal(dispatchBoundaries, 1);
  assert.equal(ownedWrite('attempt-a', 'dispatch_requested'), false);
  assert.equal(ownedWrites, 0);
  assert.equal(marker.attemptId, 'attempt-b');
});

test('response classes stay explicit after the POST boundary', async () => {
  for (const [status, expected] of [[400, { ok: false, retryable: false }], [503, { ok: false, retryable: true }], [202, { ok: true, retryable: false }]]) {
    const result = await runPrepared({ fetchFn: async () => new Response('', { status }) });
    assert.equal(result.boundary.phase, 'response');
    assert.equal(result.posts, 1);
    assert.equal(result.boundary.response.ok, expected.ok);
    assert.equal(result.boundary.response.retryable, expected.retryable);
  }
});
