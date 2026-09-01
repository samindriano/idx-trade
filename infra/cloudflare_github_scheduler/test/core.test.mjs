import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SLOTS,
  SLOT_BY_ID,
  canonicalSlotRunName,
  durableMarkerDecision,
  dueSlots,
  effectiveActiveModeDecision,
  exactRunRecoveryDecision,
  exactSlotCoverageRuns,
  isCaptureFinalMarkerState,
  localTimeEpochMs,
  markerKey,
  slotWindow,
  dispatchBody,
  workflowDispatchUrl,
  workflowRunsUrl,
} from '../src/core.mjs';

const ms = (dateKey, hhmm) => localTimeEpochMs(dateKey, hhmm);

test('Stockbit Stream is intentionally not part of the Cloudflare scheduler', () => {
  assert.equal(SLOTS.some((slot) => slot.workflow.includes('stream-prospective')), false);
});

test('18:40 WIB makes both 18:30 intraday and 18:35 POST_EOD due', () => {
  const ids = dueSlots(ms('2026-08-27', '18:40')).map((slot) => slot.id);
  assert.deepEqual(ids.sort(), ['E2E_POST_EOD_1835', 'STOCKBIT_INTRADAY_1830']);
});

test('09:00 WIB never dispatches expired PREOPEN_CA 08:55 after 09:02 cutoff', () => {
  assert.equal(dueSlots(ms('2026-08-27', '09:02')).some((slot) => slot.id === 'E2E_PREOPEN_CA_0855'), false);
});

test('09:22 final Open and PREOPEN checks are due only through 09:22:59', () => {
  const finalIds = dueSlots(ms('2026-08-27', '09:22')).map((slot) => slot.id).sort();
  assert.deepEqual(finalIds, ['E2E_PREOPEN_0922', 'OFFICIAL_OPEN_0922']);
  assert.deepEqual(
    dueSlots(ms('2026-08-27', '09:22') + 59_000).map((slot) => slot.id).sort(),
    finalIds,
  );
  assert.equal(dueSlots(ms('2026-08-27', '09:23')).length, 0);
});

test('weekend is a deterministic NOOP', () => {
  assert.deepEqual(dueSlots(ms('2026-08-29', '18:40')), []);
});

test('same-workflow next slot is a hard ambiguity boundary', () => {
  const slot = SLOT_BY_ID.get('STOCKBIT_INTRADAY_1830');
  const window = slotWindow(slot, ms('2026-08-27', '18:40'));
  assert.equal(new Date(window.cutoffMs).toISOString(), new Date(ms('2026-08-27', '19:30')).toISOString());
});

test('10-hour-delayed morning schedule cannot cover an evening slot', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1935');
  const runs = [{
    event: 'schedule',
    head_branch: 'main',
    created_at: new Date(ms('2026-08-27', '19:35')).toISOString(),
    display_title: canonicalSlotRunName('E2E_PREOPEN_0903'),
  }];
  assert.equal(exactSlotCoverageRuns(runs, slot, ms('2026-08-27', '19:40')).length, 0);
});

test('delayed previous same-workflow slot cannot cover the next slot', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1935');
  const runs = [{
    event: 'schedule',
    head_branch: 'main',
    created_at: new Date(ms('2026-08-27', '19:35')).toISOString(),
    display_title: 'IDX-SLOT:E2E_POST_EOD_1905',
  }];
  assert.equal(exactSlotCoverageRuns(runs, slot, ms('2026-08-27', '20:00')).length, 0);
});

test('exact native schedule identity covers the current slot', () => {
  const slot = SLOT_BY_ID.get('STOCKBIT_INTRADAY_1930');
  const runs = [{ event: 'schedule', head_branch: 'main', created_at: new Date(ms('2026-08-27', '19:31')).toISOString(), display_title: 'IDX-SLOT:STOCKBIT_INTRADAY_1930' }];
  assert.equal(exactSlotCoverageRuns(runs, slot, ms('2026-08-27', '19:40')).length, 1);
});

test('exact current-slot schedule at due time is accepted', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  const runs = [{ event: 'schedule', head_branch: 'main', created_at: new Date(ms('2026-08-27', '18:35')).toISOString(), display_title: 'IDX-SLOT:E2E_POST_EOD_1835' }];
  assert.equal(exactSlotCoverageRuns(runs, slot, ms('2026-08-27', '18:35')).length, 1);
});

test('valid exact slot manually dispatched before its due time is rejected', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  const runs = [{ event: 'workflow_dispatch', head_branch: 'main', created_at: new Date(ms('2026-08-27', '18:34')).toISOString(), display_title: 'IDX-SLOT:E2E_POST_EOD_1835' }];
  assert.equal(exactSlotCoverageRuns(runs, slot, ms('2026-08-27', '18:40')).length, 0);
});

test('exact current-slot evidence expires at the slot cutoff', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  const runs = [{ event: 'schedule', head_branch: 'main', created_at: new Date(ms('2026-08-27', '19:05')).toISOString(), display_title: 'IDX-SLOT:E2E_POST_EOD_1835' }];
  assert.equal(exactSlotCoverageRuns(runs, slot, ms('2026-08-27', '19:10')).length, 0);
});

test('exact Windows-watchdog workflow_dispatch identity covers the current slot', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  const runs = [{ event: 'workflow_dispatch', head_branch: 'main', created_at: new Date(ms('2026-08-27', '18:36')).toISOString(), display_title: 'IDX-SLOT:E2E_POST_EOD_1835' }];
  assert.equal(exactSlotCoverageRuns(runs, slot, ms('2026-08-27', '18:40')).length, 1);
});

test('ambiguous manual workflow_dispatch metadata never suppresses a slot', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  const runs = [{ event: 'workflow_dispatch', head_branch: 'main', created_at: new Date(ms('2026-08-27', '18:36')).toISOString(), display_title: 'E2E Paper cloud orchestration' }];
  assert.equal(exactSlotCoverageRuns(runs, slot, ms('2026-08-27', '18:40')).length, 0);
});

test('feature branch or non-main ref never covers production', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  const base = { event: 'schedule', created_at: new Date(ms('2026-08-27', '18:36')).toISOString(), display_title: 'IDX-SLOT:E2E_POST_EOD_1835' };
  assert.equal(exactSlotCoverageRuns([{ ...base, head_branch: 'feature/x' }], slot, ms('2026-08-27', '18:40')).length, 0);
  assert.equal(exactSlotCoverageRuns([{ ...base, head_branch: 'main', ref: 'refs/heads/feature/x' }], slot, ms('2026-08-27', '18:40')).length, 0);
});

test('dispatch body preserves exact workflow input', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  assert.deepEqual(dispatchBody(slot), { ref: 'main', inputs: { phase: 'POST_EOD', trigger_slot: 'E2E_POST_EOD_1835' } });
  assert.deepEqual(dispatchBody(SLOT_BY_ID.get('OFFICIAL_OPEN_0902')), { ref: 'main', inputs: { slot: '0902' } });
});

test('only validated archive completion is capture-final', () => {
  assert.equal(isCaptureFinalMarkerState('capture_complete'), true);
  assert.equal(isCaptureFinalMarkerState('covered_exact'), false);
  assert.equal(isCaptureFinalMarkerState('dispatched'), false);
  assert.equal(isCaptureFinalMarkerState('blocked'), false);
  assert.equal(isCaptureFinalMarkerState('retryable_error'), false);
  assert.equal(isCaptureFinalMarkerState('would_dispatch'), false);
  assert.equal(markerKey('2026-08-27', 'E2E_POST_EOD_1835'), '2026-08-27::E2E_POST_EOD_1835');
});

test('scheduler markers never masquerade as capture completion', () => {
  assert.deepEqual(
    durableMarkerDecision({ state: 'capture_complete', run_id: 123 }, 10_000),
    { status: 'CAPTURE_ALREADY_COMPLETE', state: 'capture_complete', runId: 123 },
  );
  assert.deepEqual(
    durableMarkerDecision({ state: 'dispatch_requested', updated_at_ms: 9_000 }, 10_000),
    { status: 'DISPATCH_REQUESTED_NOT_CAPTURE_COMPLETE', state: 'dispatch_requested', runId: null },
  );
  assert.deepEqual(
    durableMarkerDecision({ state: 'dispatched', updated_at_ms: 9_000 }, 10_000),
    { status: 'DISPATCH_REQUESTED_NOT_CAPTURE_COMPLETE', state: 'dispatched', runId: null },
  );
  assert.equal(durableMarkerDecision({ state: 'blocked', run_id: 123 }, 10_000), null);
  assert.equal(durableMarkerDecision({ state: 'covered_exact', run_id: 123 }, 10_000), null);
  assert.equal(durableMarkerDecision({ state: 'dispatched', run_id: 123 }, 10_000), null);
  assert.equal(durableMarkerDecision({ state: 'would_dispatch', updated_at_ms: 1 }, 10_000), null);
});

test('process-level active decision defers for every fresh coordinator dispatch lease', () => {
  const shadow = { archive_github_decision: 'WORKFLOW_DISPATCH_WOULD_BE_ELIGIBLE' };
  for (const state of ['dispatching', 'dispatch_requested']) {
    const markerDecision = durableMarkerDecision({ state, updated_at_ms: 9_500 }, 10_000);
    assert.equal(markerDecision.status, 'DISPATCH_REQUESTED_NOT_CAPTURE_COMPLETE');
    assert.equal(
      effectiveActiveModeDecision(shadow, markerDecision),
      'DEFER_COORDINATOR_DISPATCH_LEASE',
    );
    assert.notEqual(
      effectiveActiveModeDecision(shadow, markerDecision),
      'WORKFLOW_DISPATCH_WOULD_BE_ELIGIBLE',
    );
  }
});

test('exact run metadata never becomes capture completion and only fresh in-flight runs defer fallback', () => {
  const observed = Date.parse('2026-08-27T11:40:00.000Z');
  const recent = new Date(observed - 30_000).toISOString();
  const old = new Date(observed - 3 * 60_000).toISOString();

  assert.deepEqual(
    exactRunRecoveryDecision({ id: 1, status: 'in_progress', conclusion: null, updated_at: recent }, observed),
    {
      defer: true,
      recoveryEligible: false,
      final: false,
      status: 'RUN_VISIBLE_IN_FLIGHT_GRACE_NOT_CAPTURE_COMPLETE',
      runId: 1,
    },
  );
  for (const conclusion of ['failure', 'cancelled']) {
    assert.deepEqual(
      exactRunRecoveryDecision({ id: 2, status: 'completed', conclusion, updated_at: recent }, observed),
      { defer: false, recoveryEligible: true, final: false },
    );
  }
  assert.deepEqual(
    exactRunRecoveryDecision({ id: 3, status: 'in_progress', conclusion: null, updated_at: old }, observed),
    {
      defer: false,
      recoveryEligible: true,
      final: false,
      status: 'RUN_VISIBLE_NOT_CAPTURE_COMPLETE',
      runId: 3,
    },
  );
});

test('GitHub URLs safely encode workflow filename and date filter', () => {
  const runs = workflowRunsUrl({ owner: 'samindriano', repo: 'idx-trade', workflow: 'e2e-paper-cloud-orchestration.yml', startMs: ms('2026-08-27', '18:33'), endMs: ms('2026-08-27', '18:40') });
  assert.match(runs, /actions\/workflows\/e2e-paper-cloud-orchestration.yml\/runs\?/);
  assert.match(runs, /created=/);
  const dispatch = workflowDispatchUrl({ owner: 'samindriano', repo: 'idx-trade', workflow: 'stockbit-intraday-cloud-production.yml' });
  assert.equal(dispatch, 'https://api.github.com/repos/samindriano/idx-trade/actions/workflows/stockbit-intraday-cloud-production.yml/dispatches');
});
