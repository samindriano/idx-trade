#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';

import {
  canonicalJson,
  sha256Bytes,
  validateCandidateIdentityManifest,
} from '../src/candidate_manifest.mjs';
import {
  validateBundleIdentity,
  validateBundleSource,
  validateDeploymentConfig,
  validateDeploymentReadback,
} from '../src/deployment_readiness.mjs';
import { normalizeWranglerReadback } from '../src/cloudflare_readback.mjs';
import {
  verifyExactDeploymentAllocation,
  verifyVersionModulesAgainstCandidate,
} from '../src/version_attestation.mjs';

function usage() {
  console.error([
    'Usage: node scripts/check-deployment-readiness.mjs',
    '  --config <wrangler jsonc>',
    '  --profile <staging_live_observe_only|production_preparation|production_active_intraday_2030>',
    '  --bundle <compiled Wrangler main module>',
    '  [--modules-dir <compiled Wrangler module directory>]',
    '  --manifest <generated candidate identity manifest>',
    '  --version-id <exact uploaded Version ID>',
    '  --raw-version-response <raw Version API JSON>',
    '  [--raw-deployment-response <raw deployments API JSON>]',
    '  --trigger-readback <raw Cron read API JSON>',
    '  --settings <raw Worker settings API JSON>',
    '  [--identity-receipt <generated V2 receipt JSON>]',
  ].join('\n'));
}

function argsFrom(argv) {
  const args = new Map();
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith('--')) continue;
    const next = argv[index + 1];
    if (next && !next.startsWith('--')) { args.set(item, next); index += 1; }
    else args.set(item, true);
  }
  return args;
}

function stripJsonComments(text) {
  let output = '';
  let inString = false;
  let escaped = false;
  let lineComment = false;
  let blockComment = false;
  for (let index = 0; index < text.length; index += 1) {
    const current = text[index];
    const next = text[index + 1];
    if (lineComment) {
      if (current === '\n') { lineComment = false; output += current; }
      continue;
    }
    if (blockComment) {
      if (current === '*' && next === '/') { blockComment = false; index += 1; }
      else if (current === '\n') output += current;
      continue;
    }
    if (inString) {
      output += current;
      if (escaped) escaped = false;
      else if (current === '\\') escaped = true;
      else if (current === '"') inString = false;
      continue;
    }
    if (current === '"') { inString = true; output += current; }
    else if (current === '/' && next === '/') { lineComment = true; index += 1; }
    else if (current === '/' && next === '*') { blockComment = true; index += 1; }
    else output += current;
  }
  return output.replace(/,\s*([}\]])/g, '$1');
}

function readJsonc(path) {
  return JSON.parse(stripJsonComments(readFileSync(path, 'utf8')));
}

function pathArg(value, baseDir) {
  if (typeof value !== 'string') return null;
  return isAbsolute(value) ? value : resolve(baseDir, value);
}

function readJsonArtifact(path, issues, code, required = true) {
  if (!path) {
    if (required) issues.push({ code });
    return null;
  }
  try {
    const bytes = readFileSync(path);
    const parsed = JSON.parse(bytes.toString('utf8'));
    if (!parsed || typeof parsed !== 'object') {
      issues.push({ code: `${code}_INVALID`, detail: 'JSON_OBJECT_OR_ARRAY_REQUIRED' });
      return null;
    }
    return { value: parsed, bytes, sha256: sha256Bytes(bytes) };
  } catch (error) {
    issues.push({ code: `${code}_INVALID`, detail: String(error.message ?? error) });
    return null;
  }
}

function currentGitSha(cwd) {
  return execFileSync('git', ['rev-parse', 'HEAD'], { cwd, encoding: 'utf8' }).trim();
}

function candidateInputTreeDirty(cwd) {
  const repoRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd, encoding: 'utf8' }).trim();
  const candidatePath = relative(repoRoot, cwd);
  if (!candidatePath || candidatePath.startsWith('..')) throw new Error('CANDIDATE_CONFIG_OUTSIDE_REPOSITORY');
  return execFileSync('git', [
    'status', '--porcelain=v1', '--untracked-files=all', '--', candidatePath,
  ], { cwd: repoRoot, encoding: 'utf8' }).trim();
}

function installedWranglerVersion(cwd) {
  const wranglerEntrypoint = resolve(cwd, 'node_modules/wrangler/bin/wrangler.js');
  const output = execFileSync(process.execPath, [wranglerEntrypoint, '--version'], {
    cwd,
    encoding: 'utf8',
  });
  const versions = output.match(/\d+\.\d+\.\d+/g) ?? [];
  if (!versions.length) throw new Error('WRANGLER_VERSION_UNRESOLVED');
  return versions.at(-1);
}

function contentTypeFor(name) {
  if (/\.(?:js|mjs|cjs)$/i.test(name)) return 'application/javascript+module';
  if (/\.wasm$/i.test(name)) return 'application/wasm';
  if (/\.json$/i.test(name)) return 'application/json';
  if (/\.txt$/i.test(name)) return 'text/plain';
  return 'application/octet-stream';
}

function localCompiledModules(root, bundlePath, mainModule) {
  const files = [];
  function visit(directory) {
    for (const name of readdirSync(directory)) {
      const path = join(directory, name);
      const info = statSync(path);
      if (info.isDirectory()) visit(path);
      else if (!/^(?:README\.md|meta\.json)$/i.test(name) && !/\.map$/i.test(name)) files.push(path);
    }
  }
  visit(root);
  const bundle = resolve(bundlePath);
  const modules = files.map((path) => ({
    name: resolve(path) === bundle ? mainModule : relative(root, path).replaceAll('\\', '/'),
    content_type: contentTypeFor(path),
    bytes: readFileSync(path),
  }));
  if (!modules.some(({ name }) => name === mainModule)) modules.push({
    name: mainModule,
    content_type: 'application/javascript+module',
    bytes: readFileSync(bundlePath),
  });
  return modules;
}

function receiptIssues(receipt, manifest, versionAttestation, deploymentAttestation) {
  if (!receipt) return [];
  const expected = {
    worker_name: manifest.worker_name,
    version_id: versionAttestation.version?.version_id,
    main_module: manifest.compiled_main_module,
    compiled_module_set_sha256: manifest.compiled_module_set_sha256,
    direct_version_byte_attestation: 'DIRECT_VERSION_BYTE_ATTESTATION_PROVEN',
    raw_version_response_sha256: versionAttestation.version?.raw_response_sha256,
  };
  if (deploymentAttestation?.ok) {
    expected.deployment_id = deploymentAttestation.deployment?.id;
    expected.raw_deployment_response_sha256 = deploymentAttestation.raw_response_sha256;
  }
  return Object.entries(expected)
    .filter(([field, value]) => receipt[field] !== value)
    .map(([field, expectedValue]) => ({
      code: `IDENTITY_RECEIPT_${field.toUpperCase()}_MISMATCH`,
      detail: { actual: receipt[field], expected: expectedValue },
    }));
}

const args = argsFrom(process.argv.slice(2));
if (args.has('--help')) {
  usage();
  process.exitCode = 0;
} else {
  const issues = [];
  const configPath = pathArg(args.get('--config'), process.cwd());
  if (!configPath) {
    usage();
    process.exitCode = 2;
  } else {
    const configDir = dirname(configPath);
    let config = null;
    try { config = readJsonc(configPath); }
    catch (error) { issues.push({ code: 'CONFIG_READ_INVALID', detail: String(error.message ?? error) }); }
    const profile = args.get('--profile');
    const configReport = config
      ? validateDeploymentConfig(config, { profile })
      : { ok: false, issues: [{ code: 'CONFIG_UNAVAILABLE' }], profile, requiredSecrets: [], scope: { allowedSlotIds: [] }, crons: null };
    issues.push(...configReport.issues);
    try {
      const dirty = candidateInputTreeDirty(configDir);
      if (dirty) issues.push({ code: 'CANDIDATE_INPUT_TREE_DIRTY', detail: dirty });
    } catch (error) {
      issues.push({ code: 'CANDIDATE_INPUT_TREE_STATUS_UNRESOLVED', detail: String(error.message ?? error) });
    }

    const bundlePath = pathArg(args.get('--bundle'), configDir);
    const modulesDir = pathArg(args.get('--modules-dir'), configDir);
    const mainModule = typeof args.get('--main-module') === 'string' ? args.get('--main-module') : 'index.js';
    const manifestPath = pathArg(args.get('--manifest'), configDir);
    const versionPath = pathArg(args.get('--raw-version-response'), process.cwd());
    const deploymentPath = pathArg(args.get('--raw-deployment-response'), process.cwd());
    const triggerPath = pathArg(args.get('--trigger-readback'), process.cwd());
    const settingsPath = pathArg(args.get('--settings'), process.cwd());
    const receiptPath = pathArg(args.get('--identity-receipt'), process.cwd());
    const versionId = args.get('--version-id');
    if (!bundlePath) issues.push({ code: 'COMPILED_BUNDLE_REQUIRED' });
    if (!manifestPath) issues.push({ code: 'CANDIDATE_MANIFEST_REQUIRED' });
    if (!versionId) issues.push({ code: 'EXPECTED_VERSION_ID_REQUIRED' });

    let bundleBytes = null;
    let configBytes = null;
    let manifest = null;
    try { if (bundlePath) bundleBytes = readFileSync(bundlePath); }
    catch (error) { issues.push({ code: 'COMPILED_BUNDLE_READ_INVALID', detail: String(error.message ?? error) }); }
    try { if (config) configBytes = readFileSync(configPath); }
    catch (error) { issues.push({ code: 'CONFIG_BYTES_READ_INVALID', detail: String(error.message ?? error) }); }
    const manifestArtifact = readJsonArtifact(manifestPath, issues, 'CANDIDATE_MANIFEST_REQUIRED');
    if (manifestArtifact) manifest = manifestArtifact.value;
    const versionArtifact = readJsonArtifact(versionPath, issues, 'RAW_VERSION_RESPONSE_REQUIRED');
    const triggerArtifact = readJsonArtifact(triggerPath, issues, 'RAW_CRON_READBACK_REQUIRED');
    const settingsArtifact = readJsonArtifact(settingsPath, issues, 'RAW_SETTINGS_REQUIRED');
    const deploymentRequired = configReport.profile === 'production_active_intraday_2030';
    const deploymentArtifact = readJsonArtifact(deploymentPath, issues, 'RAW_DEPLOYMENT_RESPONSE_REQUIRED', deploymentRequired);
    const receiptArtifact = readJsonArtifact(receiptPath, issues, 'DEPLOYMENT_IDENTITY_RECEIPT', false);
    let localModules = null;
    if (bundleBytes && configBytes && manifest && config) {
      try {
        localModules = modulesDir
          ? localCompiledModules(modulesDir, bundlePath, mainModule)
          : [{ name: mainModule, content_type: 'application/javascript+module', bytes: bundleBytes }];
        const manifestReport = validateCandidateIdentityManifest(manifest, {
          gitCommitSha: currentGitSha(configDir),
          profile,
          wranglerVersion: installedWranglerVersion(configDir),
          entrypoint: config.main,
          bundleBytes,
          compiledModules: localModules,
          mainModule,
          configBytes,
          config,
        });
        issues.push(...manifestReport.issues);
      } catch (error) {
        issues.push({ code: 'CANDIDATE_MANIFEST_INPUT_INVALID', detail: String(error.message ?? error) });
      }
    }
    if (bundleBytes) {
      const bundleIdentity = validateBundleIdentity({
        actualSha256: sha256Bytes(bundleBytes),
        actualSizeBytes: bundleBytes.length,
        expectedSha256: manifest?.compiled_bundle_sha256 ?? null,
        expectedSizeBytes: manifest?.compiled_bundle_size_bytes ?? null,
      });
      issues.push(...bundleIdentity.issues);
      const bundleReport = validateBundleSource(bundleBytes.toString('utf8'), {
        entrypoint: config?.main,
        expectedHandlers: manifest?.handlers ?? ['scheduled'],
      });
      issues.push(...bundleReport.issues);
    }

    let versionAttestation = { ok: false, verdict: 'BLOCKED', issues: [], version: null };
    if (manifest && versionArtifact) {
      versionAttestation = verifyVersionModulesAgainstCandidate({
        candidateModuleSet: {
          main_module: manifest.compiled_main_module,
          modules: manifest.compiled_modules,
          module_set_sha256: manifest.compiled_module_set_sha256,
        },
        rawVersionResponse: versionArtifact.value,
        rawResponseBytes: versionArtifact.bytes,
        expectedWorkerName: config?.name,
        expectedVersionId: versionId,
      });
      issues.push(...versionAttestation.issues);
    }

    let deploymentAttestation = { ok: false, verdict: 'NOT_REQUIRED', issues: [], deployment: null, raw_response_sha256: null };
    if (deploymentArtifact) {
      deploymentAttestation = verifyExactDeploymentAllocation({
        rawDeploymentResponse: deploymentArtifact.value,
        rawResponseBytes: deploymentArtifact.bytes,
        attestedVersionId: versionId,
      });
      issues.push(...deploymentAttestation.issues);
    }

    let normalized = null;
    if (config && versionArtifact && triggerArtifact && settingsArtifact) {
      const normalizedReport = normalizeWranglerReadback({
        workerName: config.name,
        deploymentList: deploymentArtifact?.value,
        versionView: versionArtifact.value,
        triggerReadback: triggerArtifact.value,
        settings: settingsArtifact.value,
        identityReceipt: receiptArtifact?.value,
      });
      normalized = normalizedReport.readback;
      issues.push(...normalizedReport.issues);
      if (normalized && manifest) {
        const readbackReport = validateDeploymentReadback(normalized, {
          workerName: config.name,
          versionId,
          deploymentId: deploymentAttestation.deployment?.id,
          bundleSha256: manifest.compiled_bundle_sha256,
          bundleSizeBytes: manifest.compiled_bundle_size_bytes,
          mode: configReport.mode,
          allowedSlotIds: manifest.recovery_scope,
          crons: manifest.cron,
          expectedHandlers: manifest.handlers,
          expectedSecretNames: manifest.expected_secret_names,
          scopeConfigured: manifest.recovery_scope_configured,
          expectedImplementationPins: manifest.expected_implementation_pins,
          compatibilityDate: manifest.compatibility_date,
          workersDev: manifest.workers_dev,
          expectedTrafficPercentage: deploymentAttestation.deployment?.versions?.[0]?.percentage ?? 100,
          requireTraffic: deploymentRequired,
          mainModule: manifest.compiled_main_module,
        });
        issues.push(...readbackReport.issues);
        issues.push(...receiptIssues(receiptArtifact?.value, manifest, versionAttestation, deploymentAttestation));
      }
    }

    if (deploymentRequired && !deploymentAttestation.ok) issues.push({ code: 'ACTIVE_DEPLOYMENT_ALLOCATION_NOT_PROVEN' });
    if (!versionAttestation.ok) issues.push({ code: 'DIRECT_VERSION_BYTE_ATTESTATION_NOT_PROVEN' });
    const status = issues.length === 0
      ? configReport.profile === 'production_active_intraday_2030'
        ? 'CLOUDFLARE_PRODUCTION_ACTIVE_CONFIGURATION_PROVEN'
        : configReport.profile === 'production_preparation'
          ? 'CLOUDFLARE_PRODUCTION_PREPARED_NONAUTOMATIC'
          : 'CLOUDFLARE_STAGING_LIVE_OBSERVE_ONLY_PROVEN'
      : 'BLOCKED';
    console.log(JSON.stringify({
      status,
      profile: configReport.profile,
      authorities: {
        local_compiled_candidate: manifest ? 'LOCAL_COMPILED_CANDIDATE_PROVEN' : 'BLOCKED',
        direct_version_byte_attestation: versionAttestation.verdict,
        active_deployment_allocation: deploymentAttestation.verdict,
        etag: 'INFORMATIONAL_ONLY',
        receipt: 'INDEX_ONLY_NOT_AUTHORITY',
      },
      config: config ? { path: configPath, worker_name: config.name, sha256: configBytes ? sha256Bytes(configBytes) : null } : null,
      candidate_manifest: manifest ? { path: manifestPath, sha256: sha256Bytes(Buffer.from(canonicalJson(manifest), 'utf8')) } : null,
      bundle: bundleBytes ? { path: bundlePath, size_bytes: bundleBytes.length, sha256: sha256Bytes(bundleBytes) } : null,
      version_attestation: versionAttestation,
      deployment_attestation: deploymentAttestation,
      raw_evidence_sha256: {
        version_response: versionArtifact?.sha256 ?? null,
        deployment_response: deploymentArtifact?.sha256 ?? null,
        trigger_readback: triggerArtifact?.sha256 ?? null,
        settings: settingsArtifact?.sha256 ?? null,
      },
      readback: normalized,
      issues,
    }, null, 2));
    process.exitCode = issues.length === 0 ? 0 : 1;
  }
}
