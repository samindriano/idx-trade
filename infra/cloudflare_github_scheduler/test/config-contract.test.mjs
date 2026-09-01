import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const readJson = (name) => JSON.parse(readFileSync(new URL(`../${name}`, import.meta.url), 'utf8'));
const staging = readJson('wrangler.jsonc');
const stagingLive = readJson('wrangler.staging-live.jsonc');
const production = readJson('wrangler.production.jsonc');
const indexSource = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');

test('staging and production use isolated Worker and Durable Object namespaces', () => {
  assert.notEqual(staging.name, production.name);
  assert.notEqual(stagingLive.name, production.name);
  assert.notEqual(stagingLive.name, staging.name);
  assert.equal(staging.durable_objects.bindings[0].name, 'COORDINATOR');
  assert.equal(production.durable_objects.bindings[0].name, 'COORDINATOR');
  assert.equal(staging.durable_objects.bindings[0].class_name, production.durable_objects.bindings[0].class_name);
  const stagingMarkerNamespace = `${staging.name}:COORDINATOR`;
  const productionMarkerNamespace = `${production.name}:COORDINATOR`;
  assert.notEqual(stagingMarkerNamespace, productionMarkerNamespace);
  assert.equal(staging.vars.DISPATCH_MODE, 'observe_only');
  assert.equal(stagingLive.vars.DISPATCH_MODE, 'observe_only');
  assert.equal(production.vars.DISPATCH_MODE, 'active');
});

test('staging has no production Cron schedule and production retains exact Cron schedule', () => {
  assert.deepEqual(staging.triggers, { crons: [] });
  assert.deepEqual(stagingLive.triggers.crons, [
    '35,50 1 * * 1-5',
    '0,5,15,22 2 * * 1-5',
    '40 11 * * 1-5',
    '10,40 12 * * 1-5',
    '40 13 * * 1-5',
  ]);
  assert.deepEqual(production.triggers.crons, [
    '35,50 1 * * 1-5',
    '0,5,15,22 2 * * 1-5',
    '40 11 * * 1-5',
    '10,40 12 * * 1-5',
    '40 13 * * 1-5',
  ]);
});

test('scheduler markers remain a coordination guard without claiming capture completion', () => {
  assert.match(indexSource, /durableMarkerDecision\(prior, observedEpochMs\)/);
  assert.match(indexSource, /this\._write\(slotKey, 'dispatch_requested'/);
  assert.match(indexSource, /dispatchWithMode/);
  assert.match(indexSource, /this\._write\(slotKey, 'covered_exact'/);
  assert.match(indexSource, /provenance = run\.event === 'schedule' \? 'native_schedule' : 'workflow_dispatch'/);
  assert.match(indexSource, /capture_complete: false/);
  assert.doesNotMatch(indexSource, /this\._write\(slotKey, 'capture_complete'/);
});
