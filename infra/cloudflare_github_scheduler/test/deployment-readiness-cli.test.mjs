import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { buildCandidateIdentityManifest, canonicalJson } from '../src/candidate_manifest.mjs';

const projectRoot = new URL('../', import.meta.url);
const configPath = new URL('../wrangler.production.jsonc', import.meta.url);
const bundlePath = new URL('../src/index.js', import.meta.url);
const projectRootPath = fileURLToPath(projectRoot);

function jsonc(text) {
  return JSON.parse(text
    .replace(/^\s*\/\/.*$/gm, '')
    .replace(/,\s*([}\]])/g, '$1'));
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
      '--deployment-list', nullPaths[0],
      '--version-view', nullPaths[1],
      '--trigger-readback', nullPaths[2],
      '--settings', nullPaths[3],
      '--identity-receipt', nullPaths[4],
    ], { cwd: projectRootPath, encoding: 'utf8' });
    assert.equal(result.status, 1);
    const report = JSON.parse(result.stdout);
    assert.equal(report.status, 'BLOCKED');
    assert.ok(report.issues.some(({ code }) => code === 'RAW_DEPLOYMENT_LIST_REQUIRED_INVALID'));
    assert.ok(report.issues.some(({ code }) => code === 'DEPLOYMENT_IDENTITY_RECEIPT_REQUIRED_INVALID'));
  } finally {
    rmSync(temp, { recursive: true, force: true });
  }
});
