import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  PRODUCTION_CANARY_SCOPE,
  PRODUCTION_CRONS,
  requiredSecretNames,
  validateBundleIdentity,
  validateBundleSource,
  validateControllerState,
  validateDeploymentConfig,
  validateDeploymentReadback,
} from '../src/deployment_readiness.mjs';

const jsonc = (name) => JSON.parse(
  readFileSync(new URL(`../${name}`, import.meta.url), 'utf8')
    .replace(/^\s*\/\/.*$/gm, '')
    .replace(/,\s*([}\]])/g, '$1'),
);

const production = jsonc('wrangler.production.jsonc');
const preparation = jsonc('wrangler.production-preparation.jsonc');
const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');

test('bounded Intraday production config does not require Official Open HMAC', () => {
  const report = validateDeploymentConfig(production, {
    profile: 'production',
    expectedScope: PRODUCTION_CANARY_SCOPE,
    expectedCrons: PRODUCTION_CRONS,
  });
  assert.equal(report.ok, true);
  assert.deepEqual(report.requiredSecrets, [
    'GITHUB_ACTIONS_READ_TOKEN',
    'GITHUB_ACTIONS_WRITE_TOKEN',
  ]);
  assert.deepEqual(requiredSecretNames({ mode: 'active', allowedSlotIds: PRODUCTION_CANARY_SCOPE }), report.requiredSecrets);
});

test('Official Open scope expansion requires the HMAC declaration before deployment', () => {
  const expanded = structuredClone(production);
  expanded.vars.RECOVERY_ALLOWED_SLOTS = '["OFFICIAL_OPEN_0922"]';
  const report = validateDeploymentConfig(expanded, { profile: 'production', expectedCrons: PRODUCTION_CRONS });
  assert.equal(report.ok, false);
  assert.ok(report.issues.some(({ code }) => code === 'SECRET_DECLARATION_SCOPE_MISMATCH'));
  assert.deepEqual(report.requiredSecrets, [
    'GITHUB_ACTIONS_READ_TOKEN',
    'GITHUB_ACTIONS_WRITE_TOKEN',
    'OFFICIAL_OPEN_SCHEDULER_HMAC_KEY',
  ]);
});

test('preparation config is inert and still retains the required bindings', () => {
  const report = validateDeploymentConfig(preparation, { profile: 'preparation', expectedCrons: [] });
  assert.equal(report.ok, true);
  assert.equal(report.mode, 'observe_only');
  assert.deepEqual(report.requiredSecrets, ['GITHUB_ACTIONS_READ_TOKEN']);
});

test('bundle readiness rejects the prior stub and accepts the scheduled candidate', () => {
  const stub = validateBundleSource('export default { fetch() {} };');
  assert.equal(stub.ok, false);
  assert.ok(stub.issues.some(({ code }) => code === 'BUNDLE_IS_STUB'));
  const candidate = validateBundleSource(source);
  assert.equal(candidate.ok, true);
  assert.equal(candidate.hasScheduledHandler, true);
  assert.equal(candidate.isStub, false);
});

test('bundle identity rejects wrong bytes and retains exact size/hash checks', () => {
  const valid = validateBundleIdentity({
    actualSha256: 'a'.repeat(64),
    actualSizeBytes: 10,
    expectedSha256: 'a'.repeat(64),
    expectedSizeBytes: 10,
  });
  assert.equal(valid.ok, true);
  const wrong = validateBundleIdentity({
    actualSha256: 'b'.repeat(64),
    actualSizeBytes: 11,
    expectedSha256: 'a'.repeat(64),
    expectedSizeBytes: 10,
  });
  assert.equal(wrong.ok, false);
  assert.deepEqual(wrong.issues.map(({ code }) => code), [
    'BUNDLE_SHA256_MISMATCH',
    'BUNDLE_SIZE_MISMATCH',
  ]);
});

function readback(overrides = {}) {
  return {
    worker_name: production.name,
    version_id: 'version-1',
    bundle_sha256: 'a'.repeat(64),
    bundle_size_bytes: 10,
    entrypoint: 'src/index.js',
    handlers: { scheduled: true, stub: false },
    vars: {
      GITHUB_OWNER: 'samindriano',
      GITHUB_REPO: 'idx-trade',
      GITHUB_REF: 'main',
      DISPATCH_MODE: 'active',
      RECOVERY_ALLOWED_SLOTS: ['STOCKBIT_INTRADAY_2030'],
    },
    bindings: {
      ARCHIVE: { type: 'r2_bucket', bucket_name: 'idx-trade-stockbit-stream-v1' },
      COORDINATOR: { type: 'durable_object', class_name: 'SchedulerCoordinator' },
    },
    crons: [...PRODUCTION_CRONS],
    ...overrides,
  };
}

test('deployment readback rejects wrong version/bytes, missing handlers, bindings, and empty Cron', () => {
  const expected = {
    workerName: production.name,
    versionId: 'version-1',
    bundleSha256: 'a'.repeat(64),
    bundleSizeBytes: 10,
    mode: 'active',
    allowedSlotIds: ['STOCKBIT_INTRADAY_2030'],
    crons: [...PRODUCTION_CRONS],
  };
  assert.equal(validateDeploymentReadback(readback(), expected).ok, true);
  const bad = validateDeploymentReadback(readback({
    version_id: 'version-2',
    bundle_sha256: 'b'.repeat(64),
    handlers: { scheduled: false, stub: true },
    bindings: { ARCHIVE: { type: 'r2_bucket', bucket_name: 'wrong' } },
    crons: [],
  }), expected);
  assert.equal(bad.ok, false);
  for (const code of [
    'READBACK_VERSION_ID_MISMATCH',
    'READBACK_BUNDLE_SHA256_MISMATCH',
    'READBACK_SCHEDULED_HANDLER_MISSING',
    'READBACK_STUB_BUNDLE',
    'READBACK_CRON_MISMATCH',
    'READBACK_R2_BINDING_MISSING_OR_WRONG',
    'READBACK_DURABLE_OBJECT_BINDING_MISSING_OR_WRONG',
  ]) assert.ok(bad.issues.some((entry) => entry.code === code), code);
  const incomplete = validateDeploymentReadback(readback({ handlers: { scheduled: true } }), expected);
  assert.ok(incomplete.issues.some(({ code }) => code === 'READBACK_STUB_BUNDLE'));
});

test('active readiness rejects empty Cron configuration', () => {
  const config = structuredClone(production);
  config.triggers.crons = [];
  const report = validateDeploymentConfig(config, { profile: 'production', expectedScope: PRODUCTION_CANARY_SCOPE });
  assert.equal(report.ok, false);
  assert.ok(report.issues.some(({ code }) => code === 'ACTIVE_CRON_CONFIGURATION_EMPTY'));
});

test('controller preconditions reject zero-controller and dual-controller states', () => {
  const noController = validateControllerState({
    windowsAutomatic: false,
    cloudflare: { mode: 'observe_only', cronActive: false, ready: false },
  });
  assert.equal(noController.ok, false);
  assert.ok(noController.issues.some(({ code }) => code === 'WINDOWS_OFF_CLOUDFLARE_NOT_READY'));

  const dual = validateControllerState({
    windowsAutomatic: true,
    cloudflare: { mode: 'active', cronActive: true, ready: false, bundleReady: false },
  });
  assert.equal(dual.ok, false);
  assert.ok(dual.issues.some(({ code }) => code === 'MULTIPLE_AUTOMATIC_RECOVERY_CONTROLLERS'));
  assert.ok(dual.issues.some(({ code }) => code === 'CLOUDFLARE_ACTIVE_NOT_READY'));

  const windowsPrimary = validateControllerState({
    windowsAutomatic: true,
    cloudflare: { mode: 'observe_only', cronActive: false, ready: false },
  });
  assert.equal(windowsPrimary.ok, true);
});
