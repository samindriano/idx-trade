import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const readJson = (name) => JSON.parse(readFileSync(new URL(`../${name}`, import.meta.url), 'utf8'));
const staging = readJson('wrangler.jsonc');
const stagingLive = readJson('wrangler.staging-live.jsonc');
const production = readJson('wrangler.production.jsonc');
const indexSource = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');

const E2E_RECOVERY_PIN = '8bc3ee3efd65e8b16478e404e4b226451b105c48';
const OFFICIAL_OPEN_RECOVERY_PIN = 'ac29a0552b1785045906f8d608b5371d93e01b73';

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
  for (const config of [staging, stagingLive, production]) {
    assert.deepEqual(config.r2_buckets, [{ binding: 'ARCHIVE', bucket_name: 'idx-trade-stockbit-stream-v1' }]);
    assert.equal(config.vars.E2E_EXPECTED_CODE_COMMIT, E2E_RECOVERY_PIN);
    assert.equal(config.vars.OFFICIAL_OPEN_EXPECTED_CODE_COMMIT, OFFICIAL_OPEN_RECOVERY_PIN);
  }
});

test('GitHub read and dispatch credentials are capability-separated by environment', () => {
  assert.deepEqual(staging.secrets.required, ['GITHUB_ACTIONS_READ_TOKEN']);
  assert.deepEqual(stagingLive.secrets.required, ['GITHUB_ACTIONS_READ_TOKEN']);
  assert.deepEqual(production.secrets.required, [
    'GITHUB_ACTIONS_READ_TOKEN',
    'GITHUB_ACTIONS_WRITE_TOKEN',
    'OFFICIAL_OPEN_SCHEDULER_HMAC_KEY',
  ]);
  for (const config of [staging, stagingLive]) {
    assert.equal(config.secrets.required.includes('GITHUB_ACTIONS_WRITE_TOKEN'), false);
    assert.equal(config.secrets.required.includes('OFFICIAL_OPEN_SCHEDULER_HMAC_KEY'), false);
  }
  assert.match(indexSource, /const readToken = requireEnv\(this\.env, 'GITHUB_ACTIONS_READ_TOKEN'\)/);
  assert.match(indexSource, /token: readToken/);
  const dispatchFn = indexSource.indexOf('dispatchFn: async () =>');
  const writeToken = indexSource.indexOf("requireEnv(this.env, 'GITHUB_ACTIONS_WRITE_TOKEN')");
  assert.ok(dispatchFn >= 0);
  assert.ok(writeToken > dispatchFn);
  assert.doesNotMatch(indexSource, /GITHUB_ACTIONS_TOKEN/);
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
  const leaseAcquire = indexSource.indexOf('this._acquireDispatchLease(slotKey, observedEpochMs, scheduledEpochMs)');
  const githubQuery = indexSource.indexOf('await queryExactSlotCoverage');
  assert.ok(leaseAcquire >= 0);
  assert.ok(githubQuery > leaseAcquire);
  assert.match(indexSource, /_writeOwnedDispatchLease/);
  assert.match(indexSource, /durableMarkerDecision\(prior, observedEpochMs\)/);
  assert.match(indexSource, /effectiveActiveModeDecision/);
  assert.match(indexSource, /effective_active_mode_decision/);
  assert.match(indexSource, /status: 'SHADOW_DEFERRED_BY_DISPATCH_LEASE'/);
  assert.match(indexSource, /_writeOwnedDispatchLease\(slotKey, attemptId, 'dispatch_requested'/);
  assert.match(indexSource, /dispatchWithMode/);
  assert.match(indexSource, /this\._write\(slotKey, 'dispatching'/);
  assert.match(indexSource, /evaluateShadowSlot/);
  assert.match(indexSource, /githubError/);
  assert.match(indexSource, /SHADOW_DURABLE_COMPLETION_VERIFIED/);
  assert.match(indexSource, /capture_complete/);
  assert.doesNotMatch(indexSource, /this\._write\(slotKey, 'capture_complete'/);
});

test('Official Open signing is confined to lazy active dispatch path', () => {
  assert.match(indexSource, /officialOpenAttestedDispatchBody/);
  assert.match(indexSource, /isOfficialOpenSlot\(slot\)/);
  assert.match(indexSource, /requireEnv\(this\.env, 'OFFICIAL_OPEN_SCHEDULER_HMAC_KEY'\)/);
  assert.match(indexSource, /dispatchFn: async \(\) =>/);
  assert.match(indexSource, /official_open_attestation_required/);
});

test('Official Open durable archive completion requires separate recovery admission', () => {
  assert.match(indexSource, /validateOfficialOpenRecoveryAdmission/);
  assert.match(indexSource, /OFFICIAL_OPEN_EXPECTED_CODE_COMMIT/);
  assert.match(indexSource, /FAIL_CLOSED_OFFICIAL_OPEN_RECOVERY_ADMISSION_INVALID/);
  assert.match(indexSource, /official_open_recovery_admission/);
});

test('a completion-final marker is not manufactured by a generic hash helper', async () => {
  const completion = await import('../src/completion.mjs');
  assert.equal('captureCompletionProof' in completion, false);
});
