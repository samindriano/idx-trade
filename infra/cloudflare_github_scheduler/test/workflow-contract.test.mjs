import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SLOTS } from '../src/core.mjs';

const readWorkflow = (name) => readFileSync(new URL(`../../../.github/workflows/${name}`, import.meta.url), 'utf8');
const e2e = readWorkflow('e2e-paper-cloud-orchestration.yml');
const e2eRunName = e2e.slice(e2e.indexOf('run-name:'), e2e.indexOf('\non:'));
const officialOpen = readWorkflow('official-open-prospective-cloud-capture.yml');
const intraday = readWorkflow('stockbit-intraday-cloud-production.yml');
const productionWrangler = readFileSync(new URL('../wrangler.production.jsonc', import.meta.url), 'utf8');

const officialSlots = [
  ['2 2 * * 1-5', '0902', 'OFFICIAL_OPEN_0902'],
  ['12 2 * * 1-5', '0912', 'OFFICIAL_OPEN_0912'],
  ['22 2 * * 1-5', '0922', 'OFFICIAL_OPEN_0922'],
];

test('E2E workflow exposes all exact provenance-only trigger slots', () => {
  const slots = SLOTS.filter((slot) => slot.workflow === 'e2e-paper-cloud-orchestration.yml').map((slot) => slot.id);
  const workflowSlots = [...e2e.matchAll(/\bE2E_(?:PREOPEN_CA_\d{4}|PREOPEN_\d{4}|POST_EOD_\d{4})\b/g)].map((match) => match[0]);
  assert.deepEqual([...new Set(workflowSlots)].sort(), [...slots].sort());
  assert.match(e2e, /trigger_slot:/);
  for (const slot of slots) assert.match(e2e, new RegExp(slot));
  for (const slot of slots) {
    const phase = slot.startsWith('E2E_PREOPEN_CA_') ? 'PREOPEN_CA' : slot.startsWith('E2E_PREOPEN_') ? 'PREOPEN' : 'POST_EOD';
    assert.match(e2e, new RegExp(`inputs\\.phase == '${phase}' && inputs\\.trigger_slot == '${slot}' && '${slot}'`));
  }
  assert.doesNotMatch(e2eRunName, /inputs\.trigger_slot \|\|/);
  assert.doesNotMatch(e2e, /auto:\*\)/);
  assert.match(e2e, /AMBIGUOUS_MANUAL/);
  assert.match(e2e, /does not agree with phase/);
  assert.match(e2e, /args=\(--phase "\$E2E_CLOUD_PHASE"\)/);
});

test('E2E provider checkout cannot dirty the attested deployment worktree', () => {
  assert.match(e2e, /E2E_CLOUD_PROVIDER_CHECKOUT: \/tmp\/idx-bei-provider/);
  assert.doesNotMatch(e2e, /E2E_CLOUD_PROVIDER_CHECKOUT: \$\{\{ github\.workspace \}\}\/idx-bei-provider/);
  assert.doesNotMatch(e2e, /runner\.temp/);
  assert.match(e2e, /Checkout pinned IDX provider outside deployment worktree/);
  assert.match(e2e, /git -C "\$E2E_CLOUD_PROVIDER_CHECKOUT" fetch --no-tags --depth=1 origin "\$E2E_CLOUD_PROVIDER_COMMIT"/);
  assert.match(e2e, /test -z "\$\(git status --porcelain=v1 --untracked-files=all\)"/);
  assert.doesNotMatch(e2e, /path: idx-bei-provider/);
});

test('E2E manual exact identity is trusted only for a matching explicit phase', () => {
  const trustedManualSlot = (phase, slot) => {
    if (phase === 'PREOPEN_CA' && slot.startsWith('E2E_PREOPEN_CA_')) return slot;
    if (phase === 'PREOPEN' && ['E2E_PREOPEN_0903', 'E2E_PREOPEN_0913', 'E2E_PREOPEN_0922'].includes(slot)) return slot;
    if (phase === 'POST_EOD' && slot.startsWith('E2E_POST_EOD_')) return slot;
    return 'AMBIGUOUS_MANUAL';
  };
  assert.equal(trustedManualSlot('PREOPEN_CA', 'E2E_PREOPEN_CA_0830'), 'E2E_PREOPEN_CA_0830');
  assert.equal(trustedManualSlot('PREOPEN', 'E2E_POST_EOD_1835'), 'AMBIGUOUS_MANUAL');
  assert.equal(trustedManualSlot('auto', 'E2E_PREOPEN_CA_0830'), 'AMBIGUOUS_MANUAL');
});

test('Official Open workflow exposes exact native and dispatch slot identities', () => {
  for (const [cron, slot, id] of officialSlots) {
    assert.ok(officialOpen.includes(`github.event.schedule == '${cron}' || inputs.slot == '${slot}'`));
    assert.ok(officialOpen.includes(id));
  }
  // GitHub workflow concurrency is deliberately not treated as completion or
  // recovery-safety evidence here. Durable archive admission remains authoritative.
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