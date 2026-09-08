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
  const report = validateDeploymentConfig(expanded, { profile: 'production' });
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
  assert.deepEqual(report.requiredSecrets, [
    'GITHUB_ACTIONS_READ_TOKEN',
    'GITHUB_ACTIONS_WRITE_TOKEN',
  ]);
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

test('bundle readiness does not treat an unrelated scheduled helper as the handler', () => {
  const decoy = validateBundleSource(`
    function scheduled() {}
    env.ARCHIVE; env.COORDINATOR; env.RECOVERY_ALLOWED_SLOTS;
    export default {};
  `);
  assert.equal(decoy.ok, false);
  assert.ok(decoy.issues.some(({ code }) => code === 'BUNDLE_HANDLER_SET_MISMATCH'));

  const classDecoy = validateBundleSource(`
    class NotTheWorkerHandler { scheduled() {} }
    env.ARCHIVE; env.COORDINATOR; env.RECOVERY_ALLOWED_SLOTS;
    export default {};
  `);
  assert.equal(classDecoy.ok, false);
  assert.ok(classDecoy.issues.some(({ code }) => code === 'BUNDLE_HANDLER_SET_MISMATCH'));
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
    schema_version: 'IDX-CLOUDFLARE-READBACK-V1',
    worker_name: production.name,
    version_id: 'version-1',
    main_module: 'index.js',
    bundle_sha256: 'a'.repeat(64),
    bundle_size_bytes: 10,
    config_sha256: 'c'.repeat(64),
    manifest_sha256: 'd'.repeat(64),
    remote_script_etag: 'etag-1',
    entrypoint: 'src/index.js',
    handlers: ['scheduled'],
    stub: false,
    compatibility_date: '2026-08-27',
    workers_dev: false,
    scope_configured: true,
    secret_names: ['GITHUB_ACTIONS_READ_TOKEN', 'GITHUB_ACTIONS_WRITE_TOKEN'],
    vars: {
      GITHUB_OWNER: 'samindriano',
      GITHUB_REPO: 'idx-trade',
      GITHUB_REF: 'main',
      DISPATCH_MODE: 'active',
      RECOVERY_ALLOWED_SLOTS: ['STOCKBIT_INTRADAY_2030'],
      E2E_EXPECTED_CODE_COMMIT: '8bc3ee3efd65e8b16478e404e4b226451b105c48',
    },
    bindings: {
      ARCHIVE: { type: 'r2_bucket', bucket_name: 'idx-trade-stockbit-stream-v1' },
      COORDINATOR: { type: 'durable_object', class_name: 'SchedulerCoordinator' },
    },
    exports: { SchedulerCoordinator: { type: 'durable-object', storage: 'sqlite' } },
    traffic_percentage: 100,
    traffic_ambiguous: false,
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
    expectedSecretNames: ['GITHUB_ACTIONS_READ_TOKEN', 'GITHUB_ACTIONS_WRITE_TOKEN'],
    expectedImplementationPins: {
      E2E_EXPECTED_CODE_COMMIT: '8bc3ee3efd65e8b16478e404e4b226451b105c48',
    },
  };
  assert.equal(validateDeploymentReadback(readback(), expected).ok, true);
  const bad = validateDeploymentReadback(readback({
    version_id: 'version-2',
    bundle_sha256: 'b'.repeat(64),
    handlers: ['fetch'],
    stub: true,
    bindings: { ARCHIVE: { type: 'r2_bucket', bucket_name: 'wrong' } },
    crons: [],
  }), expected);
  assert.equal(bad.ok, false);
  for (const code of [
    'READBACK_VERSION_ID_MISMATCH',
    'READBACK_BUNDLE_SHA256_MISMATCH',
    'READBACK_HANDLER_SET_MISMATCH',
    'READBACK_STUB_BUNDLE',
    'READBACK_CRON_MISMATCH',
    'READBACK_R2_BINDING_MISSING_OR_WRONG',
    'READBACK_DURABLE_OBJECT_BINDING_MISSING_OR_WRONG',
  ]) assert.ok(bad.issues.some((entry) => entry.code === code), code);
  const incomplete = validateDeploymentReadback(readback({ handlers: ['scheduled'], stub: undefined }), expected);
  assert.ok(incomplete.issues.some(({ code }) => code === 'READBACK_STUB_BUNDLE'));
});

test('active readiness rejects empty Cron configuration', () => {
  const config = structuredClone(production);
  config.triggers.crons = [];
  const report = validateDeploymentConfig(config, { profile: 'production' });
  assert.equal(report.ok, false);
  assert.ok(report.issues.some(({ code }) => code === 'PROFILE_CRON_CONFIGURATION_MISMATCH'));
});

test('strict production profile rejects scope, identity, binding, and entrypoint drift', () => {
  const mutations = [
    ['wrong scope', (config) => { config.vars.RECOVERY_ALLOWED_SLOTS = '["STOCKBIT_INTRADAY_1930"]'; }, 'PROFILE_SCOPE_MISMATCH'],
    ['malformed scope', (config) => { config.vars.RECOVERY_ALLOWED_SLOTS = 'not-json'; }, 'PROFILE_SCOPE_MISMATCH'],
    ['wrong owner', (config) => { config.vars.GITHUB_OWNER = 'other-owner'; }, 'GITHUB_REPOSITORY_IDENTITY_MISMATCH'],
    ['wrong repo', (config) => { config.vars.GITHUB_REPO = 'other-repo'; }, 'GITHUB_REPOSITORY_IDENTITY_MISMATCH'],
    ['wrong ref', (config) => { config.vars.GITHUB_REF = 'feature/test'; }, 'GITHUB_REF_MUST_BE_MAIN'],
    ['wrong entrypoint', (config) => { config.main = 'src/other.js'; }, 'ENTRYPOINT_NOT_CANONICAL'],
    ['missing R2', (config) => { config.r2_buckets = []; }, 'R2_BINDING_MISSING_OR_WRONG'],
    ['wrong R2 bucket', (config) => { config.r2_buckets[0].bucket_name = 'wrong'; }, 'R2_BINDING_MISSING_OR_WRONG'],
    ['missing DO', (config) => { config.durable_objects.bindings = []; }, 'DURABLE_OBJECT_BINDING_MISSING_OR_WRONG'],
    ['wrong DO class', (config) => { config.durable_objects.bindings[0].class_name = 'Wrong'; }, 'DURABLE_OBJECT_BINDING_MISSING_OR_WRONG'],
    ['empty active crons', (config) => { config.triggers.crons = []; }, 'PROFILE_CRON_CONFIGURATION_MISMATCH'],
  ];
  for (const [label, mutate, code] of mutations) {
    const config = structuredClone(production);
    mutate(config);
    const report = validateDeploymentConfig(config, { profile: 'production' });
    assert.equal(report.ok, false, label);
    assert.ok(report.issues.some((entry) => entry.code === code), label);
  }

  const officialOpen = structuredClone(production);
  officialOpen.vars.RECOVERY_ALLOWED_SLOTS = '["OFFICIAL_OPEN_0922"]';
  officialOpen.secrets.required.push('OFFICIAL_OPEN_SCHEDULER_HMAC_KEY');
  officialOpen.vars.OFFICIAL_OPEN_EXPECTED_CODE_COMMIT = 'not-a-sha';
  const officialReport = validateDeploymentConfig(officialOpen, { profile: 'production' });
  assert.equal(officialReport.ok, false);
  assert.ok(officialReport.issues.some(({ code }) => code === 'IMPLEMENTATION_PIN_INVALID_OR_UNEXPECTED'));
});

test('profile selection cannot turn observe-only staging or preparation into active recovery', () => {
  const staging = jsonc('wrangler.staging-live.jsonc');
  const stagingActive = structuredClone(staging);
  stagingActive.vars.DISPATCH_MODE = 'active';
  stagingActive.vars.RECOVERY_ALLOWED_SLOTS = '["STOCKBIT_INTRADAY_2030"]';
  stagingActive.secrets.required = ['GITHUB_ACTIONS_READ_TOKEN', 'GITHUB_ACTIONS_WRITE_TOKEN'];
  const stagingReport = validateDeploymentConfig(stagingActive, { profile: 'staging_live_observe_only' });
  assert.equal(stagingReport.ok, false);

  const preparationActive = structuredClone(preparation);
  preparationActive.vars.DISPATCH_MODE = 'active';
  preparationActive.triggers.crons = [...PRODUCTION_CRONS];
  const preparationReport = validateDeploymentConfig(preparationActive, { profile: 'production_preparation' });
  assert.equal(preparationReport.ok, false);
  assert.ok(preparationReport.issues.some(({ code }) => code === 'PROFILE_DISPATCH_MODE_MISMATCH'));
  assert.ok(preparationReport.issues.some(({ code }) => code === 'PROFILE_CRON_CONFIGURATION_MISMATCH'));
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

  const windowsOnWithCron = validateControllerState({
    windowsAutomatic: true,
    cloudflare: { mode: 'active', cronActive: true, ready: false },
  });
  assert.equal(windowsOnWithCron.ok, false);
  assert.equal(windowsOnWithCron.cloudflareActive, true);
  assert.ok(windowsOnWithCron.issues.some(({ code }) => code === 'MULTIPLE_AUTOMATIC_RECOVERY_CONTROLLERS'));

  const windowsPrimary = validateControllerState({
    windowsAutomatic: true,
    cloudflare: { mode: 'observe_only', cronActive: false, ready: false },
  });
  assert.equal(windowsPrimary.ok, true);
});

test('controller state rejects malformed or unknown evidence types', () => {
  const malformed = validateControllerState({
    windowsAutomatic: true,
    watchdogProcessCount: 0,
    cloudflare: { mode: 'active', cronActive: 'true', ready: true },
  });
  assert.equal(malformed.ok, false);
  assert.ok(malformed.issues.some(({ code }) => code === 'CLOUDFLARE_CRON_STATE_UNKNOWN'));
});
