export const CLOUDFLARE_READBACK_SCHEMA = 'IDX-CLOUDFLARE-READBACK-V1';
const SHA256 = /^[0-9a-f]{64}$/;

import { unwrapRawVersionResponse } from './version_attestation.mjs';

function issue(code, detail = undefined) {
  return detail === undefined ? { code } : { code, detail };
}

function deploymentArray(raw) {
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw?.deployments)) return raw.deployments;
  return null;
}

function cronArray(raw) {
  const candidates = [];
  if (Array.isArray(raw)) candidates.push(raw);
  if (Array.isArray(raw?.crons)) candidates.push(raw.crons);
  if (Array.isArray(raw?.triggers?.crons)) candidates.push(raw.triggers.crons);
  if (!candidates.length) return { value: undefined, issues: [] };
  const first = JSON.stringify(candidates[0]);
  const conflicting = candidates.some((candidate) => JSON.stringify(candidate) !== first);
  return {
    value: candidates[0],
    issues: conflicting ? [issue('RAW_CRON_READBACK_CONFLICTING_SHAPES')] : [],
  };
}

const KNOWN_BINDING_TYPES = new Set([
  'plain_text',
  'secret_text',
  'r2_bucket',
  'durable_object_namespace',
  'durable_object',
]);

function bindingMap(rawBindings) {
  if (!Array.isArray(rawBindings)) return { map: null, issues: [] };
  const map = {};
  const issues = [];
  for (const binding of rawBindings) {
    if (!binding || typeof binding.name !== 'string' || binding.name.length === 0) {
      issues.push(issue('RAW_BINDING_ENTRY_INVALID'));
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(map, binding.name)) {
      issues.push(issue('RAW_BINDING_NAME_DUPLICATE', binding.name));
      continue;
    }
    if (!KNOWN_BINDING_TYPES.has(binding.type)) {
      issues.push(issue('RAW_BINDING_TYPE_UNKNOWN', { name: binding.name, type: binding.type }));
    }
    map[binding.name] = binding;
  }
  return { map, issues };
}

function normalizeBindings(rawBindings) {
  const mapped = bindingMap(rawBindings);
  if (!mapped.map) return { bindings: null, vars: null, secretNames: null, issues: [] };
  const raw = mapped.map;
  const vars = {};
  const secretNames = [];
  const bindings = {};
  for (const [name, binding] of Object.entries(raw)) {
    if (binding.type === 'plain_text') {
      vars[name] = binding.text;
      continue;
    }
    if (binding.type === 'secret_text') {
      secretNames.push(name);
      continue;
    }
    if (binding.type === 'r2_bucket') {
      bindings[name] = { type: 'r2_bucket', bucket_name: binding.bucket_name };
      continue;
    }
    if (binding.type === 'durable_object_namespace' || binding.type === 'durable_object') {
      bindings[name] = {
        type: 'durable_object',
        class_name: binding.class_name,
        namespace_id: binding.namespace_id,
      };
      continue;
    }
    bindings[name] = { type: binding.type };
  }
  return { bindings, vars, secretNames: secretNames.sort(), issues: mapped.issues };
}

function selectDeployment(raw, versionId) {
  const deployments = deploymentArray(raw);
  if (!deployments) return { deployment: null, issues: [issue('RAW_DEPLOYMENT_LIST_SHAPE_UNKNOWN')] };
  const matches = deployments
    .filter((deployment) => Array.isArray(deployment?.versions)
      && deployment.versions.some((version) => version?.version_id === versionId))
    .sort((left, right) => String(right.created_on ?? '').localeCompare(String(left.created_on ?? '')));
  if (matches.length === 0) return { deployment: null, issues: [issue('RAW_VERSION_NOT_PRESENT_IN_DEPLOYMENT_LIST', versionId)] };
  if (matches.length > 1) return { deployment: matches[0], issues: [issue('RAW_VERSION_DEPLOYMENT_AMBIGUOUS', matches.map((entry) => entry.id))] };
  return { deployment: matches[0], issues: [] };
}

function trafficFor(deployment, versionId) {
  const versions = deployment?.versions;
  if (!Array.isArray(versions) || versions.length === 0) {
    return { percentage: undefined, ambiguous: true, allocations: [] };
  }
  const allocations = versions.map((version) => ({
    version_id: version?.version_id,
    percentage: version?.percentage,
  }));
  const candidate = allocations.find((version) => version.version_id === versionId);
  const total = allocations.reduce((sum, version) => sum + (Number.isFinite(version.percentage) ? version.percentage : 0), 0);
  return {
    percentage: candidate?.percentage,
    ambiguous: !candidate || allocations.length !== 1 || total !== 100,
    allocations,
  };
}

function rawHandlers(versionView) {
  const handlers = versionView?.resources?.script?.handlers;
  return Array.isArray(handlers) ? [...handlers].sort() : undefined;
}

export function normalizeWranglerReadback({
  workerName,
  deploymentList,
  versionView,
  triggerReadback,
  settings,
  identityReceipt,
} = {}) {
  const issues = [];
  if (!versionView || typeof versionView !== 'object') return { ok: false, issues: [issue('RAW_VERSION_VIEW_MISSING')], readback: null };
  const unwrapped = unwrapRawVersionResponse(versionView);
  issues.push(...unwrapped.issues);
  const rawVersion = unwrapped.payload;
  if (!rawVersion) return { ok: false, issues, readback: null };
  // Never let an operator-supplied receipt fill in the raw version identity.
  // The exact Version module attestation and Deployment API verifier are the
  // authorities for bytes and traffic. This adapter only normalizes the raw
  // runtime/config fields used by the existing profile checks.
  const versionId = rawVersion.id;
  if (typeof versionId !== 'string' || versionId.length === 0) issues.push(issue('RAW_VERSION_ID_MISSING'));
  const selected = deploymentList === undefined
    ? { deployment: null, issues: [] }
    : selectDeployment(deploymentList, versionId);
  issues.push(...selected.issues);
  const traffic = trafficFor(selected.deployment, versionId);
  const handlers = rawHandlers(rawVersion);
  if (!handlers) issues.push(issue('RAW_HANDLER_SET_UNKNOWN'));
  const normalizedBindings = normalizeBindings(rawVersion.resources?.bindings);
  issues.push(...(normalizedBindings.issues ?? []));
  if (!normalizedBindings.bindings || !normalizedBindings.vars || !normalizedBindings.secretNames) issues.push(issue('RAW_BINDING_SHAPE_UNKNOWN'));
  const runtime = rawVersion.resources?.script_runtime;
  const exports = runtime?.exports;
  const compatibilityDate = runtime?.compatibility_date;
  const cronResult = cronArray(triggerReadback);
  const crons = cronResult.value;
  issues.push(...cronResult.issues);
  const workersDev = settings?.workers_dev;
  if (crons === undefined) issues.push(issue('RAW_CRON_READBACK_MISSING'));
  if (typeof workersDev !== 'boolean') issues.push(issue('RAW_WORKERS_DEV_READBACK_MISSING'));
  if (!exports || typeof exports !== 'object') issues.push(issue('RAW_EXPORT_READBACK_MISSING'));
  if (typeof compatibilityDate !== 'string') issues.push(issue('RAW_COMPATIBILITY_DATE_MISSING'));
  const rawBundleSha256 = rawVersion.resources?.script?.sha256;
  const rawBundleSizeBytes = rawVersion.resources?.script?.size_bytes;

  if (identityReceipt) {
    if (identityReceipt.worker_name !== undefined && identityReceipt.worker_name !== workerName) {
      issues.push(issue('IDENTITY_RECEIPT_WORKER_MISMATCH'));
    }
    if (identityReceipt.version_id !== versionId) issues.push(issue('IDENTITY_RECEIPT_VERSION_MISMATCH'));
    if (identityReceipt.deployment_id !== undefined && identityReceipt.deployment_id !== selected.deployment?.id) issues.push(issue('IDENTITY_RECEIPT_DEPLOYMENT_MISMATCH'));
    if (identityReceipt.remote_script_etag !== undefined
      && identityReceipt.remote_script_etag !== rawVersion.resources?.script?.etag) {
      issues.push(issue('IDENTITY_RECEIPT_ETAG_MISMATCH'));
    }
    if (rawBundleSha256 !== undefined
      && identityReceipt.bundle_sha256 !== undefined
      && identityReceipt.bundle_sha256 !== rawBundleSha256) {
      issues.push(issue('IDENTITY_RECEIPT_BUNDLE_MISMATCH'));
    }
    if (rawBundleSizeBytes !== undefined
      && identityReceipt.bundle_size_bytes !== undefined
      && identityReceipt.bundle_size_bytes !== rawBundleSizeBytes) {
      issues.push(issue('IDENTITY_RECEIPT_BUNDLE_SIZE_MISMATCH'));
    }
  }

  const requiredBindings = normalizedBindings.bindings ?? {};
  const hasScheduled = handlers?.includes('scheduled') === true;
  const hasRuntimeBindings = requiredBindings.ARCHIVE !== undefined && requiredBindings.COORDINATOR !== undefined;
  const stub = hasScheduled && hasRuntimeBindings ? false : handlers?.length === 1 && handlers[0] === 'fetch' ? true : undefined;
  const vars = { ...(normalizedBindings.vars ?? {}) };
  let scopeConfigured = Object.prototype.hasOwnProperty.call(vars, 'RECOVERY_ALLOWED_SLOTS');
  if (scopeConfigured && typeof vars.RECOVERY_ALLOWED_SLOTS === 'string') {
    try {
      const parsedScope = JSON.parse(vars.RECOVERY_ALLOWED_SLOTS);
      if (!Array.isArray(parsedScope) || parsedScope.some((slotId) => typeof slotId !== 'string')) {
        issues.push(issue('RAW_SCOPE_READBACK_INVALID'));
      } else {
        vars.RECOVERY_ALLOWED_SLOTS = [...parsedScope];
      }
    } catch {
      issues.push(issue('RAW_SCOPE_READBACK_INVALID'));
    }
  } else if (scopeConfigured && Array.isArray(vars.RECOVERY_ALLOWED_SLOTS)) {
    vars.RECOVERY_ALLOWED_SLOTS = [...vars.RECOVERY_ALLOWED_SLOTS];
  } else if (scopeConfigured) {
    issues.push(issue('RAW_SCOPE_READBACK_INVALID'));
  }

  const readback = {
    schema_version: CLOUDFLARE_READBACK_SCHEMA,
    worker_name: workerName,
    deployment_id: selected.deployment?.id,
    version_id: versionId,
    traffic_percentage: traffic.percentage,
    traffic_ambiguous: traffic.ambiguous,
    traffic_allocations: traffic.allocations,
    created_on: selected.deployment?.created_on,
    handlers,
    stub,
    // The source entrypoint is local candidate evidence. The remote API's
    // module identity is carried independently as main_module.
    entrypoint: identityReceipt?.entrypoint,
    main_module: rawVersion.main_module,
    version_number: rawVersion.number,
    annotations: rawVersion.annotations ?? {},
    compatibility_date: compatibilityDate,
    workers_dev: workersDev,
    scope_configured: scopeConfigured,
    vars,
    secret_names: normalizedBindings.secretNames,
    bindings: requiredBindings,
    exports,
    crons,
    remote_script_etag: rawVersion.resources?.script?.etag,
    // These legacy fields are optional diagnostics only. The direct module
    // attestation is the byte authority and never reads them as a substitute.
    bundle_sha256: rawBundleSha256,
    bundle_size_bytes: rawBundleSizeBytes,
    config_sha256: identityReceipt?.config_sha256,
    manifest_sha256: identityReceipt?.manifest_sha256,
  };
  return { ok: issues.length === 0, issues, readback };
}
