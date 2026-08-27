import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const readWorkflow = (name) => readFileSync(new URL(`../../../.github/workflows/${name}`, import.meta.url), 'utf8');
const e2e = readWorkflow('e2e-paper-cloud-orchestration.yml');
const officialOpen = readWorkflow('official-open-prospective-cloud-capture.yml');
const intraday = readWorkflow('stockbit-intraday-cloud-production.yml');
const productionWrangler = readFileSync(new URL('../wrangler.production.jsonc', import.meta.url), 'utf8');

const officialSlots = [
  ['2 2 * * 1-5', '0902', 'OFFICIAL_OPEN_0902'],
  ['12 2 * * 1-5', '0912', 'OFFICIAL_OPEN_0912'],
  ['22 2 * * 1-5', '0922', 'OFFICIAL_OPEN_0922'],
];

const officialConcurrencyKey = ({ schedule = '', slot = '' }) => {
  const resolved = officialSlots.find(([cron, input]) => cron === schedule || input === slot)?.[1] ?? 'ambiguous';
  return `official-open-cloud-${resolved}`;
};

test('E2E workflow exposes all exact provenance-only trigger slots', () => {
  const slots = [
    'E2E_PREOPEN_CA_0830', 'E2E_PREOPEN_CA_0845', 'E2E_PREOPEN_CA_0855',
    'E2E_PREOPEN_0903', 'E2E_PREOPEN_0913', 'E2E_PREOPEN_0922',
    'E2E_POST_EOD_1835', 'E2E_POST_EOD_1905', 'E2E_POST_EOD_1935',
  ];
  assert.match(e2e, /trigger_slot:/);
  assert.match(e2e, /inputs\.trigger_slot \|\|/);
  for (const slot of slots) assert.match(e2e, new RegExp(slot));
  assert.match(e2e, /AMBIGUOUS_MANUAL/);
  assert.match(e2e, /does not agree with phase/);
  assert.match(e2e, /args=\(--phase "\$E2E_CLOUD_PHASE"\)/);
});

test('Official Open native and dispatch same-slot concurrency keys are identical', () => {
  for (const [cron, slot, id] of officialSlots) {
    assert.equal(officialConcurrencyKey({ schedule: cron }), `official-open-cloud-${slot}`);
    assert.equal(officialConcurrencyKey({ slot }), `official-open-cloud-${slot}`);
    assert.ok(officialOpen.includes(`github.event.schedule == '${cron}' || inputs.slot == '${slot}'`));
    assert.ok(officialOpen.includes(id));
  }
  assert.notEqual(officialConcurrencyKey({ schedule: officialSlots[0][0] }), officialConcurrencyKey({ slot: '0912' }));
});

test('Intraday native cron and exact input both expose canonical slot identities', () => {
  for (const [cron, slot, id] of [
    ['30 11 * * 1-5', '1830', 'STOCKBIT_INTRADAY_1830'],
    ['30 12 * * 1-5', '1930', 'STOCKBIT_INTRADAY_1930'],
    ['30 13 * * 1-5', '2030', 'STOCKBIT_INTRADAY_2030'],
  ]) {
    assert.ok(intraday.includes(`github.event.schedule == '${cron}' || inputs.slot == '${slot}'`));
    assert.ok(intraday.includes(id));
  }
});

test('production Wrangler config stays within the five exact bounded triggers', () => {
  const config = JSON.parse(productionWrangler.replace(/^\s*\/\/.*$/gm, '').replace(/,\s*([}\]])/g, '$1'));
  assert.deepEqual(config.triggers.crons, [
    '35,50 1 * * 1-5',
    '0,5,15,22 2 * * 1-5',
    '40 11 * * 1-5',
    '10,40 12 * * 1-5',
    '40 13 * * 1-5',
  ]);
});
