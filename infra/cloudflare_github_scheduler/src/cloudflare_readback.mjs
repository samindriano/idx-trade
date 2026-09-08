export const CLOUDFLARE_READBACK_SCHEMA = 'IDX-CLOUDFLARE-READBACK-V1';

function issue(code, detail = undefined) {
  return detail === undefined ? { code } : { code, detail };
}

function deploymentArray(raw) {
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw?.deployments)) return raw.deployments;
  return null;
}

function cronArray(raw) {
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw?.crons)) return raw.crons;
  if (Array.isArray(raw?.triggers?.crons)) return raw.triggers.crons;
  return undefined;
}

function bindingMap(rawBindings) {
  if (!Array.isArray(rawBindings)) return null;
  return rawBindings.reduce((result, binding) => {
    if (binding && typeof binding.name === 'string') result[binding.name] = binding;
    return result;
  }, {});
}

function normalizeBindings(rawBindings) {
  const raw = bindingMap(rawBindings);
  if (!raw) return { bindings: null, vars: null, secretNames: null };
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
  return { bindings, vars, secretNames: secretNames.sort() };
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
  // Never let an operator-supplied receipt fill in the raw version identity.
  // The version view itself must identify the version mapped to 100% traffic.
  const versionId = versionView.id;
  if (typeof versionId !== 'string' || versionId.length === 0) issues.push(issue('RAW_VERSION_ID_MISSING'));
  const selected = selectDeployment(deploymentList, versionId);
  issues.push(...selected.issues);
  const traffic = trafficFor(selected.deployment, versionId);
  const handlers = rawHandlers(versionView);
  if (!handlers) issues.push(issue('RAW_HANDLER_SET_UNKNOWN'));
  const normalizedBindings = normalizeBindings(versionView.resources?.bindings);
  if (!normalizedBindings.bindings || !normalizedBindings.vars || !normalizedBindings.secretNames) issues.push(issue('RAW_BINDING_SHAPE_UNKNOWN'));
  const runtime = versionView.resources?.script_runtime;
  const exports = runtime?.exports;
  const compatibilityDate = runtime?.compatibility_date;
  const crons = cronArray(triggerReadback);
  const workersDev = settings?.workers_dev;
  if (crons === undefined) issues.push(issue('RAW_CRON_READBACK_MISSING'));
  if (typeof workersDev !== 'boolean') issues.push(issue('RAW_WORKERS_DEV_READBACK_MISSING'));
  if (!exports || typeof exports !== 'object') issues.push(issue('RAW_EXPORT_READBACK_MISSING'));
  if (typeof compatibilityDate !== 'string') issues.push(issue('RAW_COMPATIBILITY_DATE_MISSING'));

  if (identityReceipt) {
    if (identityReceipt.worker_name !== undefined && identityReceipt.worker_name !== workerName) {
      issues.push(issue('IDENTITY_RECEIPT_WORKER_MISMATCH'));
    }
    if (identityReceipt.version_id !== versionId) issues.push(issue('IDENTITY_RECEIPT_VERSION_MISMATCH'));
    if (identityReceipt.deployment_id !== undefined && identityReceipt.deployment_id !== selected.deployment?.id) issues.push(issue('IDENTITY_RECEIPT_DEPLOYMENT_MISMATCH'));
    if (identityReceipt.remote_script_etag !== undefined
      && identityReceipt.remote_script_etag !== versionView.resources?.script?.etag) {
      issues.push(issue('IDENTITY_RECEIPT_ETAG_MISMATCH'));
    }
  } else {
    issues.push(issue('DEPLOYMENT_IDENTITY_RECEIPT_MISSING'));
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
    entrypoint: identityReceipt?.entrypoint,
    compatibility_date: compatibilityDate,
    workers_dev: workersDev,
    scope_configured: scopeConfigured,
    vars,
    secret_names: normalizedBindings.secretNames,
    bindings: requiredBindings,
    exports,
    crons,
    remote_script_etag: versionView.resources?.script?.etag,
    bundle_sha256: identityReceipt?.bundle_sha256,
    bundle_size_bytes: identityReceipt?.bundle_size_bytes,
    config_sha256: identityReceipt?.config_sha256,
    manifest_sha256: identityReceipt?.manifest_sha256,
  };
  return { ok: issues.length === 0, issues, readback };
}
