import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildCompiledModuleSet,
  canonicalJson,
  EXACT_CANDIDATE_VERSION_100_PERCENT_ACTIVE,
  DIRECT_VERSION_BYTE_ATTESTATION_PROVEN,
  verifyExactDeploymentAllocation,
  verifyVersionModulesAgainstCandidate,
} from '../src/version_attestation.mjs';

const versionId = 'ba3f4565-ecd4-4b84-905d-46d64f82a8a9';
const workerName = 'idx-trade-attestation-test';
const mainBytes = Buffer.from('export default { scheduled() {} };');
const helperBytes = Buffer.from('export const helper = true;');

function localSet(multi = false) {
  return buildCompiledModuleSet({
    mainModule: 'index.js',
    modules: [
      { name: 'index.js', content_type: 'application/javascript+module', bytes: mainBytes },
      ...(multi ? [{ name: 'helper.js', content_type: 'application/javascript+module', bytes: helperBytes }] : []),
    ],
  });
}

function rawVersion(local, {
  id = versionId,
  modules = local.modules.map(({ name, content_type, sha256 }) => ({
    name,
    content_type,
    content_base64: Buffer.from(name === 'index.js' ? mainBytes : helperBytes).toString('base64'),
    _expected_sha256: sha256,
  })).map(({ _expected_sha256, ...module }) => module),
  extra = {},
} = {}) {
  return {
    success: true,
    result: {
      id,
      number: 2,
      created_on: '2026-09-08T03:00:00.000Z',
      annotations: { 'workers/tag': 'test-version' },
      main_module: 'index.js',
      resources: {
        script_runtime: {
          compatibility_date: '2026-08-27',
          usage_model: 'standard',
          exports: { SchedulerCoordinator: { type: 'durable-object', storage: 'sqlite' } },
        },
        bindings: [],
      },
      modules,
      ...extra,
    },
  };
}

function rawBytes(value) {
  return Buffer.from(JSON.stringify(value));
}

function deployment(version = versionId, percentage = 100, extra = {}) {
  return {
    id: '182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e',
    created_on: '2026-09-08T03:05:00.000Z',
    source: 'api',
    strategy: 'percentage',
    versions: [{ version_id: version, percentage }],
    ...extra,
  };
}

test('direct Version module attestation compares an order-independent exact module set', () => {
  const local = localSet(true);
  const raw = rawVersion(local, { modules: [
    { name: 'helper.js', content_type: 'application/javascript+module', content_base64: helperBytes.toString('base64') },
    { name: 'index.js', content_type: 'application/javascript+module', content_base64: mainBytes.toString('base64') },
  ] });
  const report = verifyVersionModulesAgainstCandidate({
    candidateModuleSet: local,
    rawVersionResponse: raw,
    rawResponseBytes: rawBytes(raw),
    expectedWorkerName: workerName,
    expectedVersionId: versionId,
  });
  assert.equal(report.ok, true);
  assert.equal(report.verdict, DIRECT_VERSION_BYTE_ATTESTATION_PROVEN);
  assert.equal(report.version.modules.length, 2);
  assert.equal(report.version.main_module, 'index.js');
});

test('byte attestation rejects correct ETag with wrong bytes and all module-set mismatches', () => {
  const local = localSet();
  const base = rawVersion(local, { extra: { resources: {
    script: { etag: '6057eb0d7762ceab41bb9c800e416040d447b67e6cbdf7f5944c03ae4221183d' },
    bindings: [],
  } } });
  const wrongBytes = structuredClone(base);
  wrongBytes.result.modules[0].content_base64 = Buffer.from('export default { scheduled() { return 1; } };').toString('base64');
  const wrong = verifyVersionModulesAgainstCandidate({
    candidateModuleSet: local,
    rawVersionResponse: wrongBytes,
    rawResponseBytes: rawBytes(wrongBytes),
    expectedWorkerName: workerName,
    expectedVersionId: versionId,
  });
  assert.equal(wrong.ok, false);
  assert.ok(wrong.issues.some(({ code }) => code === 'VERSION_MODULE_SHA256_MISMATCH'));

  for (const modules of [
    [],
    [{ name: 'index.js', content_type: 'text/plain', content_base64: mainBytes.toString('base64') }],
    [{ name: 'other.js', content_type: 'application/javascript+module', content_base64: mainBytes.toString('base64') }],
    [{ name: 'index.js', content_type: 'application/javascript+module', content_base64: '%%%not-base64%%%' }],
    [
      { name: 'index.js', content_type: 'application/javascript+module', content_base64: mainBytes.toString('base64') },
      { name: 'index.js', content_type: 'application/javascript+module', content_base64: mainBytes.toString('base64') },
    ],
  ]) {
    const candidate = rawVersion(local, { modules });
    const result = verifyVersionModulesAgainstCandidate({
      candidateModuleSet: local,
      rawVersionResponse: candidate,
      rawResponseBytes: rawBytes(candidate),
      expectedWorkerName: workerName,
      expectedVersionId: versionId,
    });
    assert.equal(result.ok, false, canonicalJson(modules));
  }
});

test('byte attestation binds the requested exact Version ID and rejects ambiguous raw envelopes', () => {
  const local = localSet();
  const stale = rawVersion(local, { id: 'b888ed2d-f28f-49e3-afee-07c5148b7aff' });
  const staleReport = verifyVersionModulesAgainstCandidate({
    candidateModuleSet: local,
    rawVersionResponse: stale,
    rawResponseBytes: rawBytes(stale),
    expectedWorkerName: workerName,
    expectedVersionId: versionId,
  });
  assert.ok(staleReport.issues.some(({ code }) => code === 'RAW_VERSION_ID_MISMATCH'));

  const ambiguous = { ...rawVersion(local), id: versionId };
  const ambiguousReport = verifyVersionModulesAgainstCandidate({
    candidateModuleSet: local,
    rawVersionResponse: ambiguous,
    rawResponseBytes: rawBytes(ambiguous),
    expectedWorkerName: workerName,
    expectedVersionId: versionId,
  });
  assert.ok(ambiguousReport.issues.some(({ code }) => code === 'RAW_VERSION_RESPONSE_AMBIGUOUS'));
});

test('deployment verifier requires the latest raw deployment to be exactly one attested Version at 100%', () => {
  const raw = { success: true, result: { deployments: [deployment()] } };
  const pass = verifyExactDeploymentAllocation({
    rawDeploymentResponse: raw,
    rawResponseBytes: rawBytes(raw),
    attestedVersionId: versionId,
  });
  assert.equal(pass.ok, true);
  assert.equal(pass.verdict, EXACT_CANDIDATE_VERSION_100_PERCENT_ACTIVE);

  for (const candidate of [
    deployment(versionId, 99),
    deployment(versionId, 1, { versions: [
      { version_id: versionId, percentage: 1 },
      { version_id: 'c888ed2d-f28f-49e3-afee-07c5148b7aff', percentage: 99 },
    ] }),
    deployment('c888ed2d-f28f-49e3-afee-07c5148b7aff', 100),
    { ...deployment(), versions: [{ version_id: versionId }] },
  ]) {
    const result = verifyExactDeploymentAllocation({
      rawDeploymentResponse: { result: { deployments: [candidate] } },
      rawResponseBytes: rawBytes(candidate),
      attestedVersionId: versionId,
    });
    assert.equal(result.ok, false, JSON.stringify(candidate));
  }
});

test('deployment verifier rejects stale candidate traffic and conflicting latest deployments', () => {
  const stale = deployment(versionId, 100, { created_on: '2026-09-08T02:00:00.000Z' });
  const newer = deployment('c888ed2d-f28f-49e3-afee-07c5148b7aff', 100, { created_on: '2026-09-08T03:10:00.000Z' });
  const result = verifyExactDeploymentAllocation({
    rawDeploymentResponse: { deployments: [stale, newer] },
    rawResponseBytes: rawBytes({ deployments: [stale, newer] }),
    attestedVersionId: versionId,
  });
  assert.ok(result.issues.some(({ code }) => code === 'EXACT_CANDIDATE_VERSION_100_PERCENT_REQUIRED'));

  const sameTime = { ...newer, id: '282bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e' };
  const ambiguous = verifyExactDeploymentAllocation({
    rawDeploymentResponse: { deployments: [newer, sameTime] },
    rawResponseBytes: rawBytes({ deployments: [newer, sameTime] }),
    attestedVersionId: versionId,
  });
  assert.ok(ambiguous.issues.some(({ code }) => code === 'RAW_DEPLOYMENT_LATEST_AMBIGUOUS'));
});
