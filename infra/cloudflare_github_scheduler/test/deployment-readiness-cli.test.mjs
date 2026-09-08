import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { buildCandidateIdentityManifest, canonicalJson, sha256Bytes } from '../src/candidate_manifest.mjs';

const projectRoot = new URL('../', import.meta.url);
const configPath = new URL('../wrangler.production.jsonc', import.meta.url);
const preparationConfigPath = new URL('../wrangler.production-preparation.jsonc', import.meta.url);
const bundlePath = new URL('../src/index.js', import.meta.url);
const projectRootPath = fileURLToPath(projectRoot);

function jsonc(text) {
  return JSON.parse(text
    .replace(/^\s*\/\/.*$/gm, '')
    .replace(/,\s*([}\]])/g, '$1'));
}

// These are synthetic mutations of the real beta Version response shape. The
// sanitized probe evidence and actual IDs remain documented in the capability
// checkpoint; no raw production payload is fabricated here.
function rawVersionResponse(config, bundleBytes, versionId) {
  const bindings = [
    ...Object.entries(config.vars).map(([name, text]) => ({ name, text, type: 'plain_text' })),
    ...config.secrets.required.map((name) => ({ name, type: 'secret_text' })),
    ...config.r2_buckets.map(({ binding, ...rest }) => ({
      ...rest,
      name: binding,
      type: 'r2_bucket',
    })),
    ...config.durable_objects.bindings.map((binding) => ({
      ...binding,
      type: 'durable_object_namespace',
      namespace_id: 'synthetic-namespace-id',
    })),
  ];
  return {
    success: true,
    result: {
      id: versionId,
      number: 2,
      created_on: '2026-09-08T03:00:00.000Z',
      annotations: { 'workers/tag': 'synthetic-readiness-test' },
      main_module: 'index.js',
      resources: {
        script: { handlers: ['scheduled'] },
        script_runtime: {
          compatibility_date: config.compatibility_date,
          usage_model: 'standard',
          exports: config.exports,
        },
        bindings,
      },
      modules: [{
        name: 'index.js',
        content_type: 'application/javascript+module',
        content_base64: bundleBytes.toString('base64'),
      }],
    },
  };
}

function writeReadinessInputs(temp, config, configBytes, bundleBytes, profile) {
  const gitCommitSha = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  const manifest = buildCandidateIdentityManifest({
    gitCommitSha,
    profile,
    wranglerVersion: '4.127.0',
    entrypoint: config.main,
    bundleBytes,
    configBytes,
    config,
  }).manifest;
  const versionId = profile === 'production_preparation'
    ? 'ba3f4565-ecd4-4b84-905d-46d64f82a8a9'
    : 'b888ed2d-f28f-49e3-afee-07c5148b7aff';
  const manifestPath = join(temp, `${profile}-manifest.json`);
  const bundleOut = join(temp, `${profile}-bundle.js`);
  const versionOut = join(temp, `${profile}-version.json`);
  const triggerOut = join(temp, `${profile}-triggers.json`);
  const settingsOut = join(temp, `${profile}-settings.json`);
  writeFileSync(manifestPath, `${canonicalJson(manifest)}\n`);
  writeFileSync(bundleOut, bundleBytes);
  writeFileSync(versionOut, `${JSON.stringify(rawVersionResponse(config, bundleBytes, versionId))}\n`);
  writeFileSync(triggerOut, `${JSON.stringify({ crons: config.triggers.crons })}\n`);
  writeFileSync(settingsOut, `${JSON.stringify({ workers_dev: config.workers_dev })}\n`);
  return { manifestPath, bundleOut, versionOut, triggerOut, settingsOut, versionId };
}

test('readiness CLI blocks JSON null artifacts instead of treating them as omitted optional evidence', () => {
  const temp = mkdtempSync(join(tmpdir(), 'idx-trade-readiness-cli-'));
  try {
    const configBytes = readFileSync(configPath);
    const config = jsonc(configBytes.toString('utf8'));
    const bundleBytes = readFileSync(bundlePath);
    const gitCommitSha = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
    const manifest = buildCandidateIdentityManifest({
      gitCommitSha,
      profile: 'production',
      wranglerVersion: '4.127.0',
      entrypoint: config.main,
      bundleBytes,
      configBytes,
      config,
    });
    const manifestPath = join(temp, 'manifest.json');
    const bundleOut = join(temp, 'bundle.js');
    writeFileSync(manifestPath, `${canonicalJson(manifest.manifest)}\n`);
    writeFileSync(bundleOut, bundleBytes);
    const nullPaths = [];
    for (const name of ['deployments', 'version', 'triggers', 'settings', 'receipt']) {
      const path = join(temp, `${name}.json`);
      writeFileSync(path, 'null\n');
      nullPaths.push(path);
    }
    const result = spawnSync(process.execPath, [
      fileURLToPath(new URL('./scripts/check-deployment-readiness.mjs', projectRoot)),
      '--profile', 'production',
      '--config', fileURLToPath(configPath),
      '--bundle', bundleOut,
      '--manifest', manifestPath,
      '--raw-deployment-response', nullPaths[0],
      '--raw-version-response', nullPaths[1],
      '--trigger-readback', nullPaths[2],
      '--settings', nullPaths[3],
      '--identity-receipt', nullPaths[4],
    ], { cwd: projectRootPath, encoding: 'utf8' });
    assert.equal(result.status, 1);
    const report = JSON.parse(result.stdout);
    assert.equal(report.status, 'BLOCKED');
    assert.ok(report.issues.some(({ code }) => code === 'RAW_DEPLOYMENT_RESPONSE_REQUIRED_INVALID'));
    assert.ok(report.issues.some(({ code }) => code === 'RAW_VERSION_RESPONSE_REQUIRED_INVALID'));
  } finally {
    rmSync(temp, { recursive: true, force: true });
  }
});

test('V2 deployment receipt records the canonical candidate-manifest hash and raw evidence hashes', () => {
  const temp = mkdtempSync(join(tmpdir(), 'idx-trade-receipt-v2-'));
  try {
    const configBytes = readFileSync(configPath);
    const config = jsonc(configBytes.toString('utf8'));
    const bundleBytes = readFileSync(bundlePath);
    const gitCommitSha = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
    const manifest = buildCandidateIdentityManifest({
      gitCommitSha,
      profile: 'production',
      wranglerVersion: '4.127.0',
      entrypoint: config.main,
      bundleBytes,
      configBytes,
      config,
    }).manifest;
    const versionId = 'ba3f4565-ecd4-4b84-905d-46d64f82a8a9';
    const rawVersion = {
      success: true,
      result: {
        id: versionId,
        number: 2,
        created_on: '2026-09-08T03:00:00.000Z',
        annotations: { 'workers/tag': 'synthetic-receipt-test' },
        main_module: 'index.js',
        modules: [{
          name: 'index.js',
          content_type: 'application/javascript+module',
          content_base64: bundleBytes.toString('base64'),
        }],
      },
    };
    const rawDeployment = {
      success: true,
      result: {
        deployments: [{
          id: '182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e',
          created_on: '2026-09-08T03:05:00.000Z',
          strategy: 'percentage',
          versions: [{ version_id: versionId, percentage: 100 }],
        }],
      },
    };
    const manifestPath = join(temp, 'manifest.json');
    const versionPath = join(temp, 'version.json');
    const deploymentPath = join(temp, 'deployment.json');
    const receiptPath = join(temp, 'receipt.json');
    writeFileSync(manifestPath, `${canonicalJson(manifest)}\n`);
    writeFileSync(versionPath, `${JSON.stringify(rawVersion)}\n`);
    writeFileSync(deploymentPath, `${JSON.stringify(rawDeployment)}\n`);
    const result = spawnSync(process.execPath, [
      fileURLToPath(new URL('./scripts/generate-deployment-receipt.mjs', projectRoot)),
      '--manifest', manifestPath,
      '--raw-deployment-response', deploymentPath,
      '--raw-version-response', versionPath,
      '--version-id', versionId,
      '--out', receiptPath,
    ], { cwd: projectRootPath, encoding: 'utf8', maxBuffer: 1024 * 1024 });
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
    const receipt = JSON.parse(readFileSync(receiptPath, 'utf8'));
    assert.equal(receipt.candidate_manifest_sha256, sha256Bytes(Buffer.from(canonicalJson(manifest), 'utf8')));
    assert.equal(receipt.direct_version_byte_attestation, 'DIRECT_VERSION_BYTE_ATTESTATION_PROVEN');
    assert.equal(receipt.traffic_percentage, 100);
    assert.equal(receipt.raw_version_response_sha256, sha256Bytes(readFileSync(versionPath)));
    assert.equal(receipt.raw_deployment_response_sha256, sha256Bytes(readFileSync(deploymentPath)));
  } finally {
    rmSync(temp, { recursive: true, force: true });
  }
});

test('preparation readiness can prove an attested uploaded Version without deployment traffic', () => {
  const temp = mkdtempSync(join(tmpdir(), 'idx-trade-preparation-readiness-'));
  try {
    const configBytes = readFileSync(preparationConfigPath);
    const config = jsonc(configBytes.toString('utf8'));
    const bundleBytes = readFileSync(bundlePath);
    const inputs = writeReadinessInputs(temp, config, configBytes, bundleBytes, 'production_preparation');
    const result = spawnSync(process.execPath, [
      fileURLToPath(new URL('./scripts/check-deployment-readiness.mjs', projectRoot)),
      '--profile', 'production_preparation',
      '--config', fileURLToPath(preparationConfigPath),
      '--bundle', inputs.bundleOut,
      '--manifest', inputs.manifestPath,
      '--version-id', inputs.versionId,
      '--raw-version-response', inputs.versionOut,
      '--trigger-readback', inputs.triggerOut,
      '--settings', inputs.settingsOut,
    ], { cwd: projectRootPath, encoding: 'utf8', maxBuffer: 1024 * 1024 });
    assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
    const report = JSON.parse(result.stdout);
    assert.equal(report.status, 'CLOUDFLARE_PRODUCTION_PREPARED_NONAUTOMATIC');
    assert.equal(report.authorities.direct_version_byte_attestation, 'DIRECT_VERSION_BYTE_ATTESTATION_PROVEN');
    assert.equal(report.authorities.active_deployment_allocation, 'NOT_REQUIRED');
  } finally {
    rmSync(temp, { recursive: true, force: true });
  }
});

test('active readiness blocks when exact Deployment API evidence is missing', () => {
  const temp = mkdtempSync(join(tmpdir(), 'idx-trade-active-readiness-'));
  try {
    const configBytes = readFileSync(configPath);
    const config = jsonc(configBytes.toString('utf8'));
    const bundleBytes = readFileSync(bundlePath);
    const inputs = writeReadinessInputs(temp, config, configBytes, bundleBytes, 'production_active_intraday_2030');
    const result = spawnSync(process.execPath, [
      fileURLToPath(new URL('./scripts/check-deployment-readiness.mjs', projectRoot)),
      '--profile', 'production_active_intraday_2030',
      '--config', fileURLToPath(configPath),
      '--bundle', inputs.bundleOut,
      '--manifest', inputs.manifestPath,
      '--version-id', inputs.versionId,
      '--raw-version-response', inputs.versionOut,
      '--trigger-readback', inputs.triggerOut,
      '--settings', inputs.settingsOut,
    ], { cwd: projectRootPath, encoding: 'utf8', maxBuffer: 1024 * 1024 });
    assert.equal(result.status, 1);
    const report = JSON.parse(result.stdout);
    assert.equal(report.status, 'BLOCKED');
    assert.ok(report.issues.some(({ code }) => code === 'RAW_DEPLOYMENT_RESPONSE_REQUIRED'));
    assert.ok(report.issues.some(({ code }) => code === 'ACTIVE_DEPLOYMENT_ALLOCATION_NOT_PROVEN'));
    assert.equal(report.authorities.direct_version_byte_attestation, 'DIRECT_VERSION_BYTE_ATTESTATION_PROVEN');
  } finally {
    rmSync(temp, { recursive: true, force: true });
  }
});
