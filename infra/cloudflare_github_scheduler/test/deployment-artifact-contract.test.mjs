import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  buildCandidateIdentityManifest,
  validateCandidateIdentityManifest,
} from '../src/candidate_manifest.mjs';
import { normalizeWranglerReadback } from '../src/cloudflare_readback.mjs';
import {
  PRODUCTION_CRONS,
  validateDeploymentReadback,
} from '../src/deployment_readiness.mjs';

const readJson = (name) => JSON.parse(readFileSync(new URL(`./fixtures/${name}`, import.meta.url), 'utf8'));
const readConfig = (name) => JSON.parse(readFileSync(new URL(`../${name}`, import.meta.url), 'utf8'));
const sourceBytes = readFileSync(new URL('../src/index.js', import.meta.url));
const production = readConfig('wrangler.production.jsonc');
const preparation = readConfig('wrangler.production-preparation.jsonc');
const stagingLive = readConfig('wrangler.staging-live.jsonc');
const gitCommitSha = '1'.repeat(40);
const wranglerVersion = '4.127.0';

function candidate(config, profile) {
  return buildCandidateIdentityManifest({
    gitCommitSha,
    profile,
    wranglerVersion,
    entrypoint: config.main,
    bundleBytes: sourceBytes,
    configBytes: Buffer.from(JSON.stringify(config)),
    config,
  });
}

function receiptFor(manifest, version, deployment) {
  return {
    schema_version: 'IDX-CLOUDFLARE-DEPLOYMENT-RECEIPT-V1',
    candidate_manifest_schema: 'IDX-CLOUDFLARE-CANDIDATE-IDENTITY-V1',
    candidate_manifest_sha256: manifest.manifestSha256,
    worker_name: manifest.manifest.worker_name,
    version_id: version.id,
    deployment_id: deployment.id,
    bundle_sha256: manifest.manifest.compiled_bundle_sha256,
    bundle_size_bytes: manifest.manifest.compiled_bundle_size_bytes,
    config_sha256: manifest.manifest.config_sha256,
    manifest_sha256: manifest.manifestSha256,
    entrypoint: manifest.manifest.entrypoint,
    remote_script_etag: version.resources.script.etag,
    source: 'test-fixture-receipt',
  };
}

test('candidate identity binds profile, config bytes, source bytes, pins, and scope semantics', () => {
  for (const [config, profile] of [
    [production, 'production'],
    [preparation, 'preparation'],
    [stagingLive, 'staging-live'],
  ]) {
    const result = candidate(config, profile);
    assert.equal(result.manifest.schema_version, 'IDX-CLOUDFLARE-CANDIDATE-IDENTITY-V1');
    assert.equal(result.manifest.compiled_bundle_size_bytes, sourceBytes.length);
    assert.equal(validateCandidateIdentityManifest(result.manifest, {
      gitCommitSha,
      profile,
      wranglerVersion,
      entrypoint: config.main,
      bundleBytes: sourceBytes,
      configBytes: Buffer.from(JSON.stringify(config)),
      config,
    }).ok, true);
  }

  const preparationManifest = candidate(preparation, 'preparation').manifest;
  assert.equal(preparationManifest.recovery_scope_configured, true);
  assert.deepEqual(preparationManifest.recovery_scope, ['STOCKBIT_INTRADAY_2030']);
  assert.deepEqual(preparationManifest.cron, []);

  const stagingManifest = candidate(stagingLive, 'staging-live').manifest;
  assert.equal(stagingManifest.recovery_scope_configured, false);
  assert.equal(stagingManifest.recovery_scope.length > 1, true);

  const tampered = structuredClone(preparationManifest);
  tampered.compiled_bundle_size_bytes += 1;
  assert.equal(validateCandidateIdentityManifest(tampered, {
    gitCommitSha,
    profile: 'preparation',
    wranglerVersion,
    entrypoint: preparation.main,
    bundleBytes: sourceBytes,
    configBytes: Buffer.from(JSON.stringify(preparation)),
    config: preparation,
  }).ok, false);
});

test('raw Wrangler readback normalizes durable_object_namespace and JSON scope without inventing scope', () => {
  const version = readJson('wrangler-version-staging-live.json');
  const deployments = readJson('wrangler-deployments-staging-live.json');
  const manifest = candidate(stagingLive, 'staging-live');
  const normalized = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: deployments,
    versionView: version,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: receiptFor(manifest, version, deployments[0]),
  });
  assert.equal(normalized.ok, true);
  assert.equal(normalized.readback.scope_configured, false);
  assert.equal('RECOVERY_ALLOWED_SLOTS' in normalized.readback.vars, false);
  assert.deepEqual(normalized.readback.handlers, ['scheduled']);
  assert.equal(normalized.readback.bindings.COORDINATOR.type, 'durable_object');
  assert.equal(normalized.readback.bindings.COORDINATOR.class_name, 'SchedulerCoordinator');
  assert.deepEqual(normalized.readback.secret_names, ['GITHUB_ACTIONS_READ_TOKEN']);

  const attestedVersion = structuredClone(version);
  attestedVersion.resources.script.sha256 = manifest.manifest.compiled_bundle_sha256;
  attestedVersion.resources.script.size_bytes = manifest.manifest.compiled_bundle_size_bytes;
  const attested = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: deployments,
    versionView: attestedVersion,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: receiptFor(manifest, attestedVersion, deployments[0]),
  });
  assert.equal(attested.ok, true);

  const report = validateDeploymentReadback(attested.readback, {
    workerName: stagingLive.name,
    versionId: version.id,
    deploymentId: deployments[0].id,
    bundleSha256: manifest.manifest.compiled_bundle_sha256,
    bundleSizeBytes: manifest.manifest.compiled_bundle_size_bytes,
    configSha256: manifest.manifest.config_sha256,
    manifestSha256: manifest.manifestSha256,
    mode: 'observe_only',
    allowedSlotIds: manifest.manifest.recovery_scope,
    scopeConfigured: false,
    crons: [...PRODUCTION_CRONS],
    expectedSecretNames: ['GITHUB_ACTIONS_READ_TOKEN'],
    expectedImplementationPins: manifest.manifest.expected_implementation_pins,
  });
  assert.equal(report.ok, true);
});

test('raw Wrangler readback accepts the Cloudflare Deployment API result envelope', () => {
  const version = readJson('wrangler-version-staging-live.json');
  const deployments = readJson('wrangler-deployments-staging-live.json');
  const manifest = candidate(stagingLive, 'staging-live');
  const normalized = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: { success: true, result: { deployments } },
    versionView: version,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: receiptFor(manifest, version, deployments[0]),
  });
  assert.equal(normalized.ok, true);
  assert.equal(normalized.readback.deployment_id, deployments[0].id);
  assert.equal(normalized.readback.traffic_percentage, 100);
});

test('raw bundle identity cannot be supplied only by a receipt', () => {
  const version = readJson('wrangler-version-staging-live.json');
  const deployment = readJson('wrangler-deployments-staging-live.json');
  const manifest = candidate(stagingLive, 'staging-live');
  const report = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: deployment,
    versionView: version,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: receiptFor(manifest, version, deployment[0]),
  });
  assert.equal(report.readback.bundle_sha256, undefined);
  assert.equal(report.issues.some(({ code }) => code === 'RAW_BUNDLE_SHA256_READBACK_MISSING'), false);
});

test('raw bundle identity rejects a receipt from a different compiled version', () => {
  const version = readJson('wrangler-version-staging-live.json');
  const deployment = readJson('wrangler-deployments-staging-live.json');
  const manifest = candidate(stagingLive, 'staging-live');
  const differentVersion = structuredClone(version);
  differentVersion.resources.script.sha256 = 'b'.repeat(64);
  differentVersion.resources.script.size_bytes = manifest.manifest.compiled_bundle_size_bytes + 1;
  const report = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: deployment,
    versionView: differentVersion,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: receiptFor(manifest, differentVersion, deployment[0]),
  });
  assert.ok(report.issues.some(({ code }) => code === 'IDENTITY_RECEIPT_BUNDLE_MISMATCH'));
  assert.ok(report.issues.some(({ code }) => code === 'IDENTITY_RECEIPT_BUNDLE_SIZE_MISMATCH'));
  assert.equal(report.readback.bundle_sha256, 'b'.repeat(64));
});

test('known production stub is not deployment proof even at 100 percent traffic', () => {
  const version = readJson('wrangler-version-production-stub.json');
  const deployments = readJson('wrangler-deployments-production-stub.json');
  const manifest = candidate(production, 'production');
  const normalized = normalizeWranglerReadback({
    workerName: production.name,
    deploymentList: deployments,
    versionView: version,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: receiptFor(manifest, version, deployments[0]),
  });
  assert.equal(normalized.readback.traffic_percentage, 100);
  assert.equal(normalized.readback.stub, true);
  assert.ok(normalized.issues.some(({ code }) => code === 'RAW_EXPORT_READBACK_MISSING'));

  const report = validateDeploymentReadback(normalized.readback, {
    workerName: production.name,
    versionId: version.id,
    deploymentId: deployments[0].id,
    bundleSha256: manifest.manifest.compiled_bundle_sha256,
    bundleSizeBytes: manifest.manifest.compiled_bundle_size_bytes,
    configSha256: manifest.manifest.config_sha256,
    manifestSha256: manifest.manifestSha256,
    mode: 'active',
    allowedSlotIds: ['STOCKBIT_INTRADAY_2030'],
    crons: [...PRODUCTION_CRONS],
    expectedSecretNames: ['GITHUB_ACTIONS_READ_TOKEN', 'GITHUB_ACTIONS_WRITE_TOKEN'],
    expectedImplementationPins: manifest.manifest.expected_implementation_pins,
  });
  assert.equal(report.ok, false);
  for (const code of [
    'READBACK_HANDLER_SET_MISMATCH',
    'READBACK_STUB_BUNDLE',
    'READBACK_R2_BINDING_MISSING_OR_WRONG',
    'READBACK_DURABLE_OBJECT_BINDING_MISSING_OR_WRONG',
    'READBACK_DURABLE_OBJECT_EXPORT_MISSING_OR_WRONG',
  ]) assert.ok(report.issues.some((entry) => entry.code === code), code);
});

test('raw readback fails closed for ambiguous deployment mapping and malformed scope', () => {
  const version = readJson('wrangler-version-staging-live.json');
  const manifest = candidate(stagingLive, 'staging-live');
  const deployment = readJson('wrangler-deployments-staging-live.json')[0];
  const ambiguous = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: [deployment, { ...deployment, id: 'another-deployment' }],
    versionView: version,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: receiptFor(manifest, version, deployment),
  });
  assert.ok(ambiguous.issues.some(({ code }) => code === 'RAW_VERSION_DEPLOYMENT_AMBIGUOUS'));

  const malformed = structuredClone(version);
  malformed.resources.bindings.find(({ name }) => name === 'E2E_EXPECTED_CODE_COMMIT').text = 'not-json';
  malformed.resources.bindings.push({ name: 'RECOVERY_ALLOWED_SLOTS', text: 'not-json', type: 'plain_text' });
  const badScope = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: [deployment],
    versionView: malformed,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: receiptFor(manifest, malformed, deployment),
  });
  assert.ok(badScope.issues.some(({ code }) => code === 'RAW_SCOPE_READBACK_INVALID'));

  const missingRawVersionId = structuredClone(version);
  delete missingRawVersionId.id;
  const suppliedReceipt = receiptFor(manifest, version, deployment);
  const rawIdentity = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: [deployment],
    versionView: missingRawVersionId,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: suppliedReceipt,
  });
  assert.ok(rawIdentity.issues.some(({ code }) => code === 'RAW_VERSION_ID_MISSING'));
  assert.ok(rawIdentity.issues.some(({ code }) => code === 'IDENTITY_RECEIPT_VERSION_MISMATCH'));

  const wrongReceipt = receiptFor(manifest, version, deployment);
  wrongReceipt.worker_name = 'wrong-worker';
  const receiptIdentity = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: [deployment],
    versionView: version,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: wrongReceipt,
  });
  assert.ok(receiptIdentity.issues.some(({ code }) => code === 'IDENTITY_RECEIPT_WORKER_MISMATCH'));
});

test('raw readback fails closed for duplicate and unknown binding entries', () => {
  const version = readJson('wrangler-version-staging-live.json');
  const deployment = readJson('wrangler-deployments-staging-live.json');
  const manifest = candidate(stagingLive, 'staging-live');
  const receipt = receiptFor(manifest, version, deployment[0]);

  const duplicate = structuredClone(version);
  duplicate.resources.bindings.unshift({
    name: 'ARCHIVE',
    type: 'r2_bucket',
    bucket_name: 'wrong-bucket',
  });
  const duplicateReport = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: deployment,
    versionView: duplicate,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: receipt,
  });
  assert.ok(duplicateReport.issues.some(({ code }) => code === 'RAW_BINDING_NAME_DUPLICATE'));

  const unknown = structuredClone(version);
  unknown.resources.bindings.push({ name: 'FUTURE_BINDING', type: 'future_binding_type' });
  const unknownReport = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: deployment,
    versionView: unknown,
    triggerReadback: { crons: [...PRODUCTION_CRONS] },
    settings: { workers_dev: false },
    identityReceipt: receipt,
  });
  assert.ok(unknownReport.issues.some(({ code }) => code === 'RAW_BINDING_TYPE_UNKNOWN'));
});

test('raw readback fails closed for conflicting Cron representations', () => {
  const version = readJson('wrangler-version-staging-live.json');
  const deployment = readJson('wrangler-deployments-staging-live.json');
  const manifest = candidate(stagingLive, 'staging-live');
  const report = normalizeWranglerReadback({
    workerName: stagingLive.name,
    deploymentList: deployment,
    versionView: version,
    triggerReadback: {
      crons: [...PRODUCTION_CRONS],
      triggers: { crons: [] },
    },
    settings: { workers_dev: false },
    identityReceipt: receiptFor(manifest, version, deployment[0]),
  });
  assert.ok(report.issues.some(({ code }) => code === 'RAW_CRON_READBACK_CONFLICTING_SHAPES'));
});
