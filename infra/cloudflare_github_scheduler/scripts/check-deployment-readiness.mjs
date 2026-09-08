#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, isAbsolute, resolve } from 'node:path';

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

function usage() {
  console.error([
    'Usage: node scripts/check-deployment-readiness.mjs',
    '  --config <wrangler jsonc>',
    '  --profile <staging_live_observe_only|production_preparation|production_active_intraday_2030>',
    '  --bundle <compiled Wrangler bundle>',
    '  --manifest <generated candidate identity manifest>',
    '  --deployment-list <wrangler deployments list --json>',
    '  --version-view <wrangler versions view --json>',
    '  --trigger-readback <sanitized Cron read API JSON>',
    '  --settings <worker settings read API JSON>',
    '  --identity-receipt <generated deployment identity receipt>',
  ].join('\n'));
}

function argsFrom(argv) {
  const args = new Map();
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith('--')) continue;
    const next = argv[index + 1];
    if (next && !next.startsWith('--')) {
      args.set(item, next);
      index += 1;
    } else args.set(item, true);
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
      if (current === '\n') {
        lineComment = false;
        output += current;
      }
      continue;
    }
    if (blockComment) {
      if (current === '*' && next === '/') {
        blockComment = false;
        index += 1;
      } else if (current === '\n') output += current;
      continue;
    }
    if (inString) {
      output += current;
      if (escaped) escaped = false;
      else if (current === '\\') escaped = true;
      else if (current === '"') inString = false;
      continue;
    }
    if (current === '"') {
      inString = true;
      output += current;
    } else if (current === '/' && next === '/') {
      lineComment = true;
      index += 1;
    } else if (current === '/' && next === '*') {
      blockComment = true;
      index += 1;
    } else output += current;
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

function safeReadJson(path, issues, code) {
  if (!path) {
    issues.push({ code });
    return null;
  }
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (error) {
    issues.push({ code: `${code}_INVALID`, detail: String(error.message ?? error) });
    return null;
  }
}

function currentGitSha(cwd) {
  return execFileSync('git', ['rev-parse', 'HEAD'], { cwd, encoding: 'utf8' }).trim();
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
    try {
      config = readJsonc(configPath);
    } catch (error) {
      issues.push({ code: 'CONFIG_READ_INVALID', detail: String(error.message ?? error) });
    }

    const profile = args.get('--profile');
    const configReport = config
      ? validateDeploymentConfig(config, { profile })
      : { ok: false, issues: [{ code: 'CONFIG_UNAVAILABLE' }], profile, requiredSecrets: [], scope: { allowedSlotIds: [] }, crons: null };
    issues.push(...configReport.issues);

    const bundlePath = pathArg(args.get('--bundle'), configDir);
    const manifestPath = pathArg(args.get('--manifest'), configDir);
    if (!bundlePath) issues.push({ code: 'COMPILED_BUNDLE_REQUIRED' });
    if (!manifestPath) issues.push({ code: 'CANDIDATE_MANIFEST_REQUIRED' });
    let bundleBytes = null;
    let configBytes = null;
    let manifest = null;
    if (bundlePath) {
      try { bundleBytes = readFileSync(bundlePath); }
      catch (error) { issues.push({ code: 'COMPILED_BUNDLE_READ_INVALID', detail: String(error.message ?? error) }); }
    }
    if (config) configBytes = readFileSync(configPath);
    if (manifestPath) {
      try { manifest = JSON.parse(readFileSync(manifestPath, 'utf8')); }
      catch (error) { issues.push({ code: 'CANDIDATE_MANIFEST_READ_INVALID', detail: String(error.message ?? error) }); }
    }

    let gitCommitSha = null;
    let wranglerVersion = null;
    try { gitCommitSha = currentGitSha(configDir); }
    catch (error) { issues.push({ code: 'GIT_COMMIT_SHA_UNRESOLVED', detail: String(error.message ?? error) }); }
    try { wranglerVersion = installedWranglerVersion(configDir); }
    catch (error) { issues.push({ code: 'WRANGLER_VERSION_UNRESOLVED', detail: String(error.message ?? error) }); }

    if (bundleBytes && configBytes && manifest && config && gitCommitSha && wranglerVersion) {
      const manifestReport = validateCandidateIdentityManifest(manifest, {
        gitCommitSha,
        profile,
        wranglerVersion,
        entrypoint: config.main,
        bundleBytes,
        configBytes,
        config,
      });
      issues.push(...manifestReport.issues);
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

    const deploymentList = safeReadJson(pathArg(args.get('--deployment-list'), process.cwd()), issues, 'RAW_DEPLOYMENT_LIST_REQUIRED');
    const versionView = safeReadJson(pathArg(args.get('--version-view'), process.cwd()), issues, 'RAW_VERSION_VIEW_REQUIRED');
    const triggerReadback = safeReadJson(pathArg(args.get('--trigger-readback'), process.cwd()), issues, 'RAW_CRON_READBACK_REQUIRED');
    const settings = safeReadJson(pathArg(args.get('--settings'), process.cwd()), issues, 'RAW_SETTINGS_REQUIRED');
    const identityReceipt = safeReadJson(pathArg(args.get('--identity-receipt'), process.cwd()), issues, 'DEPLOYMENT_IDENTITY_RECEIPT_REQUIRED');
    let normalized = null;
    if (config && deploymentList && versionView && triggerReadback && settings && identityReceipt) {
      const normalizedReport = normalizeWranglerReadback({
        workerName: config.name,
        deploymentList,
        versionView,
        triggerReadback,
        settings,
        identityReceipt,
      });
      normalized = normalizedReport.readback;
      issues.push(...normalizedReport.issues);
      if (normalized && configReport && manifest) {
        const manifestSha256 = sha256Bytes(Buffer.from(canonicalJson(manifest), 'utf8'));
        const receiptChecks = [
          ['candidate_manifest_sha256', manifestSha256, 'IDENTITY_RECEIPT_MANIFEST_MISMATCH'],
          ['worker_name', config.name, 'IDENTITY_RECEIPT_WORKER_MISMATCH'],
          ['entrypoint', manifest.entrypoint, 'IDENTITY_RECEIPT_ENTRYPOINT_MISMATCH'],
          ['bundle_sha256', manifest.compiled_bundle_sha256, 'IDENTITY_RECEIPT_BUNDLE_MISMATCH'],
          ['bundle_size_bytes', manifest.compiled_bundle_size_bytes, 'IDENTITY_RECEIPT_BUNDLE_SIZE_MISMATCH'],
          ['config_sha256', manifest.config_sha256, 'IDENTITY_RECEIPT_CONFIG_MISMATCH'],
          ['manifest_sha256', manifestSha256, 'IDENTITY_RECEIPT_MANIFEST_FIELD_MISMATCH'],
        ];
        for (const [field, expected, code] of receiptChecks) {
          if (identityReceipt[field] !== expected) issues.push({ code, detail: { actual: identityReceipt[field], expected } });
        }
        const readbackReport = validateDeploymentReadback(normalized, {
          workerName: config.name,
          versionId: normalized.version_id,
          deploymentId: normalized.deployment_id,
          bundleSha256: manifest.compiled_bundle_sha256,
          bundleSizeBytes: manifest.compiled_bundle_size_bytes,
          configSha256: manifest.config_sha256,
          manifestSha256,
          mode: configReport.mode,
          allowedSlotIds: manifest.recovery_scope,
          crons: manifest.cron,
          expectedHandlers: manifest.handlers,
          expectedSecretNames: manifest.expected_secret_names,
          scopeConfigured: manifest.recovery_scope_configured,
          expectedImplementationPins: manifest.expected_implementation_pins,
          compatibilityDate: manifest.compatibility_date,
          workersDev: manifest.workers_dev,
          expectedTrafficPercentage: manifest.traffic_contract?.percentage ?? 100,
        });
        issues.push(...readbackReport.issues);
      }
    }

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
      config: config ? { path: configPath, worker_name: config.name, sha256: configBytes ? sha256Bytes(configBytes) : null } : null,
      candidate_manifest: manifest ? { path: manifestPath, sha256: sha256Bytes(Buffer.from(canonicalJson(manifest), 'utf8')) } : null,
      bundle: bundleBytes ? { path: bundlePath, size_bytes: bundleBytes.length, sha256: sha256Bytes(bundleBytes) } : null,
      readback: normalized,
      issues,
    }, null, 2));
    process.exitCode = issues.length === 0 ? 0 : 1;
  }
}
