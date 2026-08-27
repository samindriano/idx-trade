import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SLOTS,
  SLOT_BY_ID,
  dueSlots,
  exactNativeScheduleRuns,
  localTimeEpochMs,
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
  assert.equal(dueSlots(ms('2026-08-27', '09:03')).some((slot) => slot.id === 'E2E_PREOPEN_CA_0855'), false);
});

test('same-workflow next slot is a hard ambiguity boundary', () => {
  const slot = SLOT_BY_ID.get('STOCKBIT_INTRADAY_1830');
  const window = slotWindow(slot, ms('2026-08-27', '18:40'));
  assert.equal(new Date(window.cutoffMs).toISOString(), new Date(ms('2026-08-27', '19:30')).toISOString());
});

test('delayed 18:30 schedule created at 19:30 cannot cover 18:30', () => {
  const slot = SLOT_BY_ID.get('STOCKBIT_INTRADAY_1830');
  const runs = [{ event: 'schedule', head_branch: 'main', created_at: new Date(ms('2026-08-27', '19:30')).toISOString() }];
  assert.equal(exactNativeScheduleRuns(runs, slot, ms('2026-08-27', '19:35')).length, 0);
});

test('native schedule inside exact interval covers current slot', () => {
  const slot = SLOT_BY_ID.get('STOCKBIT_INTRADAY_1930');
  const runs = [{ event: 'schedule', head_branch: 'main', created_at: new Date(ms('2026-08-27', '19:31')).toISOString() }];
  assert.equal(exactNativeScheduleRuns(runs, slot, ms('2026-08-27', '19:40')).length, 1);
});

test('unknown workflow_dispatch metadata is never accepted as native slot evidence', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  const runs = [{ event: 'workflow_dispatch', head_branch: 'main', created_at: new Date(ms('2026-08-27', '18:36')).toISOString() }];
  assert.equal(exactNativeScheduleRuns(runs, slot, ms('2026-08-27', '18:40')).length, 0);
});

test('dispatch body preserves exact workflow input', () => {
  const slot = SLOT_BY_ID.get('E2E_POST_EOD_1835');
  assert.deepEqual(dispatchBody(slot), { ref: 'main', inputs: { phase: 'POST_EOD' } });
});

test('GitHub URLs safely encode workflow filename and date filter', () => {
  const runs = workflowRunsUrl({ owner: 'samindriano', repo: 'idx-trade', workflow: 'e2e-paper-cloud-orchestration.yml', startMs: ms('2026-08-27', '18:33'), endMs: ms('2026-08-27', '18:40') });
  assert.match(runs, /actions\/workflows\/e2e-paper-cloud-orchestration.yml\/runs\?/);
  assert.match(runs, /created=/);
  const dispatch = workflowDispatchUrl({ owner: 'samindriano', repo: 'idx-trade', workflow: 'stockbit-intraday-cloud-production.yml' });
  assert.equal(dispatch, 'https://api.github.com/repos/samindriano/idx-trade/actions/workflows/stockbit-intraday-cloud-production.yml/dispatches');
});
