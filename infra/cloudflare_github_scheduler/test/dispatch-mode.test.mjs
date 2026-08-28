import test from 'node:test';
import assert from 'node:assert/strict';
import { dispatchWithMode, requireDispatchMode } from '../src/dispatch_mode.mjs';

test('observe_only calculates WOULD_DISPATCH without invoking the dispatch function', async () => {
  let calls = 0;
  const result = await dispatchWithMode({
    mode: 'observe_only',
    dispatchFn: async () => {
      calls += 1;
      throw new Error('GitHub workflow dispatch must not be called');
    },
  });
  assert.deepEqual(result, {
    ok: false,
    status: 'WOULD_DISPATCH',
    dispatch_mode: 'observe_only',
    retryable: false,
    runId: null,
  });
  assert.equal(calls, 0);
});

test('invalid or missing dispatch mode fails closed without invoking dispatch', async () => {
  let calls = 0;
  const dispatchFn = async () => {
    calls += 1;
    throw new Error('dispatch must remain unreachable');
  };
  for (const mode of [undefined, '', 'ACTIVE', 'production', '']) {
    assert.throws(() => requireDispatchMode(mode), /INVALID_DISPATCH_MODE/);
    await assert.rejects(dispatchWithMode({ mode, dispatchFn }), /INVALID_DISPATCH_MODE/);
  }
  assert.equal(calls, 0);
});

test('active mode still delegates exactly once to the durable-marker caller', async () => {
  let calls = 0;
  const result = await dispatchWithMode({
    mode: 'active',
    dispatchFn: async () => {
      calls += 1;
      return { ok: true, status: 204, retryable: false, runId: null };
    },
  });
  assert.deepEqual(result, {
    ok: true,
    status: 204,
    dispatch_mode: 'active',
    retryable: false,
    runId: null,
  });
  assert.equal(calls, 1);
});
