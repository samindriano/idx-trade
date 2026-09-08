import { createHash } from 'node:crypto';

import {
  GIT_SHA,
  validateBundleSource,
  validateDeploymentConfig,
} from './deployment_readiness.mjs';

export const CANDIDATE_MANIFEST_SCHEMA = 'IDX-CLOUDFLARE-CANDIDATE-IDENTITY-V1';

function issue(code, detail = undefined) {
  return detail === undefined ? { code } : { code, detail };
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === 'object') {
    return Object.keys(value).sort().reduce((result, key) => {
      result[key] = stableValue(value[key]);
      return result;
    }, {});
  }
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(stableValue(value));
}

export function sha256Bytes(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function toBytes(value, label) {
  if (Buffer.isBuffer(value)) return value;
  if (value instanceof Uint8Array) return Buffer.from(value);
  throw new TypeError(`${label}_BYTES_REQUIRED`);
}

function plainVars(config) {
  return Object.keys(config?.vars ?? {}).sort().reduce((result, key) => {
    result[key] = config.vars[key];
    return result;
  }, {});
}

export function buildCandidateIdentityManifest({
  gitCommitSha,
  profile,
  wranglerVersion,
  entrypoint,
  bundleBytes,
  configBytes,
  config,
} = {}) {
  if (typeof gitCommitSha !== 'string' || !GIT_SHA.test(gitCommitSha)) throw new TypeError('GIT_COMMIT_SHA_INVALID');
  if (typeof wranglerVersion !== 'string' || wranglerVersion.trim() === '') throw new TypeError('WRANGLER_VERSION_REQUIRED');
  const bundle = toBytes(bundleBytes, 'BUNDLE');
  const configRaw = toBytes(configBytes, 'CONFIG');
  const resolvedEntrypoint = entrypoint ?? config?.main;
  if (resolvedEntrypoint !== config?.main) throw new TypeError('ENTRYPOINT_NOT_CANONICAL');
  const configReport = validateDeploymentConfig(config, { profile });
  if (!configReport.ok) throw new Error(`CONFIG_NOT_READY:${canonicalJson(configReport.issues)}`);
  const bundleSource = bundle.toString('utf8');
  const bundleReport = validateBundleSource(bundleSource, {
    entrypoint: resolvedEntrypoint,
    expectedHandlers: ['scheduled'],
  });
  if (!bundleReport.ok) throw new Error(`BUNDLE_NOT_READY:${canonicalJson(bundleReport.issues)}`);

  const manifest = {
    schema_version: CANDIDATE_MANIFEST_SCHEMA,
    git_commit_sha: gitCommitSha,
    profile: configReport.profile,
    worker_name: configReport.workerName,
    wrangler_version: wranglerVersion.trim(),
    entrypoint: resolvedEntrypoint,
    compiled_bundle_sha256: sha256Bytes(bundle),
    compiled_bundle_size_bytes: bundle.length,
    config_sha256: sha256Bytes(configRaw),
    compatibility_date: config.compatibility_date,
    workers_dev: config.workers_dev,
    handlers: bundleReport.handlerNames,
    vars: plainVars(config),
    expected_secret_names: configReport.requiredSecrets,
    bindings: {
      r2_buckets: config.r2_buckets,
      durable_objects: config.durable_objects,
      exports: config.exports,
    },
    cron: configReport.crons,
    r2: configReport.bindings.r2,
    durable_object: {
      binding: configReport.bindings.durableObject,
      export: configReport.bindings.durableObjectExport,
    },
    recovery_scope_configured: configReport.scope.configured,
    recovery_scope: configReport.scope.allowedSlotIds,
    expected_implementation_pins: configReport.expectedPins,
    bundle_references: bundleReport.references,
    traffic_contract: configReport.traffic,
  };
  const canonical = canonicalJson(manifest);
  return {
    manifest,
    manifestSha256: sha256Bytes(Buffer.from(canonical, 'utf8')),
    canonicalJson: canonical,
  };
}

export function validateCandidateIdentityManifest(manifest, {
  gitCommitSha,
  profile,
  wranglerVersion,
  entrypoint,
  bundleBytes,
  configBytes,
  config,
} = {}) {
  const issues = [];
  if (!manifest || typeof manifest !== 'object') return { ok: false, issues: [issue('CANDIDATE_MANIFEST_MISSING')] };
  let expected;
  try {
    expected = buildCandidateIdentityManifest({
      gitCommitSha,
      profile,
      wranglerVersion,
      entrypoint,
      bundleBytes,
      configBytes,
      config,
    });
  } catch (error) {
    return { ok: false, issues: [issue('CANDIDATE_MANIFEST_INPUT_INVALID', String(error.message ?? error))] };
  }
  if (canonicalJson(manifest) !== expected.canonicalJson) {
    issues.push(issue('CANDIDATE_MANIFEST_CONTENT_MISMATCH'));
  }
  return {
    ok: issues.length === 0,
    issues,
    manifestSha256: sha256Bytes(Buffer.from(canonicalJson(manifest), 'utf8')),
    expectedManifestSha256: expected.manifestSha256,
  };
}
