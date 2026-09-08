import { createHash } from 'node:crypto';

export const DIRECT_VERSION_BYTE_ATTESTATION_PROVEN = 'DIRECT_VERSION_BYTE_ATTESTATION_PROVEN';
export const EXACT_CANDIDATE_VERSION_100_PERCENT_ACTIVE = 'EXACT_CANDIDATE_VERSION_100_PERCENT_ACTIVE';
export const VERSION_MODULE_ATTESTATION_SCHEMA = 'IDX-CLOUDFLARE-VERSION-MODULE-ATTESTATION-V1';
export const DEPLOYMENT_ALLOCATION_ATTESTATION_SCHEMA = 'IDX-CLOUDFLARE-DEPLOYMENT-ALLOCATION-ATTESTATION-V1';

const SHA256 = /^[0-9a-f]{64}$/;
const BASE64 = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
const VERSION_MODULE_KEYS = new Set(['name', 'content_type', 'content_base64']);

function issue(code, detail = undefined) {
  return detail === undefined ? { code } : { code, detail };
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (isPlainObject(value)) {
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
  if (!(Buffer.isBuffer(bytes) || bytes instanceof Uint8Array)) throw new TypeError('BYTES_REQUIRED');
  return createHash('sha256').update(bytes).digest('hex');
}

function toBytes(value, label) {
  if (Buffer.isBuffer(value)) return value;
  if (value instanceof Uint8Array) return Buffer.from(value);
  throw new TypeError(`${label}_BYTES_REQUIRED`);
}

function validateModuleMetadata(modules, mainModule) {
  const issues = [];
  if (!Array.isArray(modules) || modules.length === 0) {
    issues.push(issue('LOCAL_COMPILED_MODULES_MISSING'));
    return { ok: false, issues, modules: [] };
  }
  const seen = new Set();
  const normalized = [];
  for (const module of modules) {
    if (!isPlainObject(module)) {
      issues.push(issue('LOCAL_COMPILED_MODULE_SHAPE_UNKNOWN'));
      continue;
    }
    const keys = Object.keys(module);
    const allowed = new Set(['name', 'content_type', 'byte_size', 'sha256']);
    if (keys.some((key) => !allowed.has(key))) {
      issues.push(issue('LOCAL_COMPILED_MODULE_SHAPE_UNKNOWN', keys));
      continue;
    }
    if (typeof module.name !== 'string' || module.name.length === 0) {
      issues.push(issue('LOCAL_COMPILED_MODULE_NAME_MISSING'));
      continue;
    }
    if (seen.has(module.name)) {
      issues.push(issue('LOCAL_COMPILED_MODULE_NAME_DUPLICATE', module.name));
      continue;
    }
    seen.add(module.name);
    if (typeof module.content_type !== 'string' || module.content_type.length === 0) {
      issues.push(issue('LOCAL_COMPILED_MODULE_CONTENT_TYPE_INVALID', module.name));
    }
    if (!Number.isInteger(module.byte_size) || module.byte_size <= 0) {
      issues.push(issue('LOCAL_COMPILED_MODULE_SIZE_INVALID', module.name));
    }
    if (typeof module.sha256 !== 'string' || !SHA256.test(module.sha256)) {
      issues.push(issue('LOCAL_COMPILED_MODULE_SHA256_INVALID', module.name));
    }
    normalized.push({
      name: module.name,
      content_type: module.content_type,
      byte_size: module.byte_size,
      sha256: module.sha256,
    });
  }
  normalized.sort((left, right) => left.name.localeCompare(right.name));
  if (typeof mainModule !== 'string' || mainModule.length === 0) {
    issues.push(issue('LOCAL_MAIN_MODULE_MISSING'));
  } else if (!seen.has(mainModule)) {
    issues.push(issue('LOCAL_MAIN_MODULE_NOT_IN_MODULE_SET', mainModule));
  }
  return { ok: issues.length === 0, issues, modules: normalized };
}

export function buildCompiledModuleSet({ modules, mainModule = 'index.js' } = {}) {
  if (!Array.isArray(modules) || modules.length === 0) throw new TypeError('LOCAL_COMPILED_MODULES_MISSING');
  const metadata = [];
  const seen = new Set();
  for (const module of modules) {
    if (!isPlainObject(module)) throw new TypeError('LOCAL_COMPILED_MODULE_SHAPE_UNKNOWN');
    const name = module.name;
    const contentType = module.content_type ?? module.contentType;
    const bytes = module.bytes ?? module.content_bytes ?? module.content;
    if (typeof name !== 'string' || name.length === 0) throw new TypeError('LOCAL_COMPILED_MODULE_NAME_MISSING');
    if (seen.has(name)) throw new TypeError(`LOCAL_COMPILED_MODULE_NAME_DUPLICATE:${name}`);
    seen.add(name);
    if (typeof contentType !== 'string' || contentType.length === 0) throw new TypeError(`LOCAL_COMPILED_MODULE_CONTENT_TYPE_INVALID:${name}`);
    const raw = toBytes(bytes, `LOCAL_COMPILED_MODULE_${name}`);
    if (raw.length === 0) throw new TypeError(`LOCAL_COMPILED_MODULE_EMPTY:${name}`);
    metadata.push({ name, content_type: contentType, byte_size: raw.length, sha256: sha256Bytes(raw) });
  }
  metadata.sort((left, right) => left.name.localeCompare(right.name));
  if (typeof mainModule !== 'string' || !seen.has(mainModule)) throw new TypeError('LOCAL_MAIN_MODULE_NOT_IN_MODULE_SET');
  const canonical = canonicalJson({ main_module: mainModule, modules: metadata });
  return {
    schema_version: VERSION_MODULE_ATTESTATION_SCHEMA,
    main_module: mainModule,
    modules: metadata,
    module_set_sha256: sha256Bytes(Buffer.from(canonical, 'utf8')),
  };
}

export function normalizeCandidateModuleSet(candidateModuleSet) {
  if (!isPlainObject(candidateModuleSet)) return { ok: false, issues: [issue('LOCAL_COMPILED_MODULE_SET_MISSING')] };
  const report = validateModuleMetadata(candidateModuleSet.modules, candidateModuleSet.main_module);
  if (!report.ok) return report;
  const canonical = canonicalJson({ main_module: candidateModuleSet.main_module, modules: report.modules });
  const expectedHash = sha256Bytes(Buffer.from(canonical, 'utf8'));
  const issues = [];
  if (candidateModuleSet.module_set_sha256 !== undefined && candidateModuleSet.module_set_sha256 !== expectedHash) {
    issues.push(issue('LOCAL_COMPILED_MODULE_SET_SHA256_MISMATCH', {
      actual: candidateModuleSet.module_set_sha256,
      expected: expectedHash,
    }));
  }
  return {
    ok: issues.length === 0,
    issues,
    main_module: candidateModuleSet.main_module,
    modules: report.modules,
    module_set_sha256: expectedHash,
  };
}

function decodeBase64(value, moduleName) {
  if (typeof value !== 'string' || value.length === 0 || !BASE64.test(value)) {
    return { bytes: null, issues: [issue('VERSION_MODULE_BASE64_INVALID', moduleName)] };
  }
  try {
    const bytes = Buffer.from(value, 'base64');
    if (bytes.length === 0 || bytes.toString('base64') !== value) {
      return { bytes: null, issues: [issue('VERSION_MODULE_BASE64_INVALID', moduleName)] };
    }
    return { bytes, issues: [] };
  } catch {
    return { bytes: null, issues: [issue('VERSION_MODULE_BASE64_INVALID', moduleName)] };
  }
}

export function unwrapRawVersionResponse(raw) {
  if (!isPlainObject(raw)) return { payload: null, issues: [issue('RAW_VERSION_RESPONSE_SHAPE_UNKNOWN')] };
  const hasResult = Object.prototype.hasOwnProperty.call(raw, 'result');
  const hasDirect = ['id', 'main_module', 'modules'].some((key) => Object.prototype.hasOwnProperty.call(raw, key));
  if (hasResult && hasDirect) return { payload: null, issues: [issue('RAW_VERSION_RESPONSE_AMBIGUOUS')] };
  if (hasResult) {
    if (!isPlainObject(raw.result)) return { payload: null, issues: [issue('RAW_VERSION_RESPONSE_RESULT_INVALID')] };
    if (raw.success === false) return { payload: null, issues: [issue('RAW_VERSION_RESPONSE_UNSUCCESSFUL')] };
    if (Array.isArray(raw.errors) && raw.errors.length > 0) return { payload: null, issues: [issue('RAW_VERSION_RESPONSE_HAS_ERRORS')] };
    return { payload: raw.result, issues: [] };
  }
  if (!hasDirect) return { payload: null, issues: [issue('RAW_VERSION_RESPONSE_SHAPE_UNKNOWN')] };
  return { payload: raw, issues: [] };
}

export function parseRawVersionModules(rawResponse, {
  expectedWorkerName,
  expectedVersionId,
  rawResponseBytes,
  requireModules = true,
} = {}) {
  const issues = [];
  if (typeof expectedWorkerName !== 'string' || expectedWorkerName.length === 0) issues.push(issue('EXPECTED_WORKER_IDENTITY_REQUIRED'));
  if (typeof expectedVersionId !== 'string' || expectedVersionId.length === 0) issues.push(issue('EXPECTED_VERSION_ID_REQUIRED'));
  const unwrapped = unwrapRawVersionResponse(rawResponse);
  issues.push(...unwrapped.issues);
  const payload = unwrapped.payload;
  if (!payload) return { ok: false, issues, version: null };
  if (typeof payload.id !== 'string' || payload.id.length === 0) issues.push(issue('RAW_VERSION_ID_MISSING'));
  if (typeof expectedVersionId === 'string' && payload.id !== expectedVersionId) {
    issues.push(issue('RAW_VERSION_ID_MISMATCH', { actual: payload.id, expected: expectedVersionId }));
  }
  for (const key of ['worker_name', 'worker_id']) {
    if (payload[key] !== undefined && payload[key] !== expectedWorkerName) issues.push(issue('RAW_VERSION_WORKER_IDENTITY_MISMATCH', { field: key, actual: payload[key], expected: expectedWorkerName }));
  }
  if (!Number.isInteger(payload.number) || payload.number < 1) issues.push(issue('RAW_VERSION_NUMBER_INVALID'));
  if (typeof payload.created_on !== 'string' || !Number.isFinite(Date.parse(payload.created_on))) issues.push(issue('RAW_VERSION_CREATED_ON_INVALID'));
  if (payload.annotations !== undefined && !isPlainObject(payload.annotations)) issues.push(issue('RAW_VERSION_ANNOTATIONS_INVALID'));
  if (payload.resources !== undefined && !isPlainObject(payload.resources)) issues.push(issue('RAW_VERSION_RESOURCES_INVALID'));
  if (payload.resources?.bindings !== undefined && !Array.isArray(payload.resources.bindings)) issues.push(issue('RAW_VERSION_BINDINGS_INVALID'));
  if (payload.migrations !== undefined && !isPlainObject(payload.migrations)) issues.push(issue('RAW_VERSION_MIGRATIONS_INVALID'));
  if (typeof payload.main_module !== 'string' || payload.main_module.length === 0) issues.push(issue('RAW_VERSION_MAIN_MODULE_MISSING'));
  if (requireModules && !Array.isArray(payload.modules)) issues.push(issue('RAW_VERSION_MODULES_MISSING'));

  const moduleMetadata = [];
  const seen = new Set();
  if (Array.isArray(payload.modules)) {
    for (const module of payload.modules) {
      if (!isPlainObject(module) || Object.keys(module).some((key) => !VERSION_MODULE_KEYS.has(key))) {
        issues.push(issue('RAW_VERSION_MODULE_SHAPE_UNKNOWN'));
        continue;
      }
      if (typeof module.name !== 'string' || module.name.length === 0) {
        issues.push(issue('RAW_VERSION_MODULE_NAME_MISSING'));
        continue;
      }
      if (seen.has(module.name)) {
        issues.push(issue('RAW_VERSION_MODULE_NAME_DUPLICATE', module.name));
        continue;
      }
      seen.add(module.name);
      if (typeof module.content_type !== 'string' || module.content_type.length === 0) {
        issues.push(issue('RAW_VERSION_MODULE_CONTENT_TYPE_INVALID', module.name));
        continue;
      }
      const decoded = decodeBase64(module.content_base64, module.name);
      issues.push(...decoded.issues);
      if (!decoded.bytes) continue;
      moduleMetadata.push({
        name: module.name,
        content_type: module.content_type,
        byte_size: decoded.bytes.length,
        sha256: sha256Bytes(decoded.bytes),
      });
    }
  }
  moduleMetadata.sort((left, right) => left.name.localeCompare(right.name));
  if (typeof payload.main_module === 'string' && !seen.has(payload.main_module)) {
    issues.push(issue('RAW_VERSION_MAIN_MODULE_NOT_IN_MODULE_SET', payload.main_module));
  }
  const moduleSetCanonical = canonicalJson({ main_module: payload.main_module, modules: moduleMetadata });
  const moduleSetSha256 = sha256Bytes(Buffer.from(moduleSetCanonical, 'utf8'));
  if (!(Buffer.isBuffer(rawResponseBytes) || rawResponseBytes instanceof Uint8Array)) issues.push(issue('RAW_VERSION_RESPONSE_HASH_MISSING'));
  return {
    ok: issues.length === 0,
    issues,
    version: {
      schema_version: VERSION_MODULE_ATTESTATION_SCHEMA,
      worker_name: expectedWorkerName,
      version_id: payload.id,
      number: payload.number,
      created_on: payload.created_on,
      annotations: payload.annotations ?? {},
      main_module: payload.main_module,
      runtime: payload.resources?.script_runtime,
      bindings: payload.resources?.bindings,
      migrations: payload.migrations,
      resources: payload.resources,
      modules: moduleMetadata,
      module_set_sha256: moduleSetSha256,
      raw_response_sha256: (Buffer.isBuffer(rawResponseBytes) || rawResponseBytes instanceof Uint8Array)
        ? sha256Bytes(rawResponseBytes)
        : null,
    },
  };
}

function compareModuleSets(local, remote) {
  const issues = [];
  if (local.main_module !== remote.main_module) issues.push(issue('VERSION_MAIN_MODULE_MISMATCH', { local: local.main_module, remote: remote.main_module }));
  if (local.modules.length !== remote.modules.length) issues.push(issue('VERSION_MODULE_CARDINALITY_MISMATCH', { local: local.modules.length, remote: remote.modules.length }));
  const localByName = new Map(local.modules.map((module) => [module.name, module]));
  const remoteByName = new Map(remote.modules.map((module) => [module.name, module]));
  for (const [name, expected] of localByName) {
    const actual = remoteByName.get(name);
    if (!actual) {
      issues.push(issue('VERSION_MODULE_MISSING', name));
      continue;
    }
    for (const field of ['content_type', 'byte_size', 'sha256']) {
      if (actual[field] !== expected[field]) issues.push(issue(`VERSION_MODULE_${field.toUpperCase()}_MISMATCH`, { name, local: expected[field], remote: actual[field] }));
    }
  }
  for (const name of remoteByName.keys()) if (!localByName.has(name)) issues.push(issue('VERSION_MODULE_EXTRA', name));
  return issues;
}

export function verifyVersionModulesAgainstCandidate({
  candidateModuleSet,
  rawVersionResponse,
  expectedWorkerName,
  expectedVersionId,
  rawResponseBytes,
} = {}) {
  const local = normalizeCandidateModuleSet(candidateModuleSet);
  const remote = parseRawVersionModules(rawVersionResponse, {
    expectedWorkerName,
    expectedVersionId,
    rawResponseBytes,
  });
  const issues = [...local.issues, ...remote.issues];
  if (local.ok && remote.version) issues.push(...compareModuleSets(local, remote.version));
  return {
    ok: issues.length === 0,
    verdict: issues.length === 0 ? DIRECT_VERSION_BYTE_ATTESTATION_PROVEN : 'BLOCKED',
    issues,
    candidate: local.ok ? local : null,
    version: remote.version,
  };
}

function unwrapDeploymentResponse(rawResponse) {
  if (Array.isArray(rawResponse)) return { deployments: rawResponse, issues: [] };
  if (!isPlainObject(rawResponse)) return { deployments: null, issues: [issue('RAW_DEPLOYMENT_RESPONSE_SHAPE_UNKNOWN')] };
  const hasResult = Object.prototype.hasOwnProperty.call(rawResponse, 'result');
  const hasDirect = Object.prototype.hasOwnProperty.call(rawResponse, 'deployments');
  if (hasResult && hasDirect) return { deployments: null, issues: [issue('RAW_DEPLOYMENT_RESPONSE_AMBIGUOUS')] };
  if (hasResult) {
    if (!isPlainObject(rawResponse.result) || !Array.isArray(rawResponse.result.deployments)) return { deployments: null, issues: [issue('RAW_DEPLOYMENT_RESPONSE_RESULT_INVALID')] };
    if (rawResponse.success === false || (Array.isArray(rawResponse.errors) && rawResponse.errors.length > 0)) return { deployments: null, issues: [issue('RAW_DEPLOYMENT_RESPONSE_UNSUCCESSFUL')] };
    return { deployments: rawResponse.result.deployments, issues: [] };
  }
  if (hasDirect && Array.isArray(rawResponse.deployments)) return { deployments: rawResponse.deployments, issues: [] };
  return { deployments: null, issues: [issue('RAW_DEPLOYMENT_RESPONSE_SHAPE_UNKNOWN')] };
}

function validateDeployment(deployment, index) {
  const issues = [];
  if (!isPlainObject(deployment) || typeof deployment.id !== 'string' || deployment.id.length === 0) issues.push(issue('RAW_DEPLOYMENT_ID_INVALID', index));
  if (typeof deployment?.created_on !== 'string' || !Number.isFinite(Date.parse(deployment.created_on))) issues.push(issue('RAW_DEPLOYMENT_CREATED_ON_INVALID', index));
  if (deployment?.strategy !== 'percentage') issues.push(issue('RAW_DEPLOYMENT_STRATEGY_UNKNOWN', { index, actual: deployment?.strategy }));
  if (!Array.isArray(deployment?.versions) || deployment.versions.length === 0) {
    issues.push(issue('RAW_DEPLOYMENT_VERSIONS_INVALID', index));
    return issues;
  }
  const seen = new Set();
  let total = 0;
  for (const version of deployment.versions) {
    if (!isPlainObject(version) || typeof version.version_id !== 'string' || version.version_id.length === 0) {
      issues.push(issue('RAW_DEPLOYMENT_VERSION_ENTRY_INVALID', index));
      continue;
    }
    if (seen.has(version.version_id)) issues.push(issue('RAW_DEPLOYMENT_VERSION_DUPLICATE', version.version_id));
    seen.add(version.version_id);
    if (typeof version.percentage !== 'number' || !Number.isFinite(version.percentage) || version.percentage <= 0 || version.percentage > 100) {
      issues.push(issue('RAW_DEPLOYMENT_PERCENTAGE_INVALID', { index, version_id: version.version_id }));
    } else total += version.percentage;
  }
  if (Math.abs(total - 100) > 1e-9) issues.push(issue('RAW_DEPLOYMENT_PERCENTAGE_TOTAL_INVALID', { index, total }));
  return issues;
}

export function verifyExactDeploymentAllocation({ rawDeploymentResponse, attestedVersionId, rawResponseBytes } = {}) {
  const issues = [];
  if (typeof attestedVersionId !== 'string' || attestedVersionId.length === 0) issues.push(issue('ATTESTED_VERSION_ID_REQUIRED'));
  const unwrapped = unwrapDeploymentResponse(rawDeploymentResponse);
  issues.push(...unwrapped.issues);
  const deployments = unwrapped.deployments;
  if (!deployments) return { ok: false, verdict: 'BLOCKED', issues, deployment: null, raw_response_sha256: null };
  if (deployments.length === 0) issues.push(issue('RAW_DEPLOYMENT_LIST_EMPTY'));
  deployments.forEach((deployment, index) => issues.push(...validateDeployment(deployment, index)));
  const validTimestamps = deployments
    .map((deployment, index) => ({ deployment, index, time: Date.parse(deployment?.created_on ?? '') }))
    .filter(({ time }) => Number.isFinite(time));
  if (validTimestamps.length === 0) issues.push(issue('RAW_DEPLOYMENT_LATEST_UNRESOLVED'));
  let latest = null;
  if (validTimestamps.length > 0) {
    const latestTime = Math.max(...validTimestamps.map(({ time }) => time));
    const latestRows = validTimestamps.filter(({ time }) => time === latestTime);
    if (latestRows.length !== 1) issues.push(issue('RAW_DEPLOYMENT_LATEST_AMBIGUOUS', latestRows.map(({ deployment }) => deployment?.id)));
    else latest = latestRows[0].deployment;
  }
  if (latest) {
    const allocations = latest.versions.map(({ version_id, percentage }) => ({ version_id, percentage }));
    const candidate = allocations.filter(({ version_id }) => version_id === attestedVersionId);
    if (candidate.length !== 1 || allocations.length !== 1 || candidate[0]?.percentage !== 100) {
      issues.push(issue('EXACT_CANDIDATE_VERSION_100_PERCENT_REQUIRED', { attestedVersionId, allocations }));
    }
  }
  if (!(Buffer.isBuffer(rawResponseBytes) || rawResponseBytes instanceof Uint8Array)) issues.push(issue('RAW_DEPLOYMENT_RESPONSE_HASH_MISSING'));
  const ok = issues.length === 0;
  return {
    ok,
    verdict: ok ? EXACT_CANDIDATE_VERSION_100_PERCENT_ACTIVE : 'BLOCKED',
    issues,
    raw_response_sha256: (Buffer.isBuffer(rawResponseBytes) || rawResponseBytes instanceof Uint8Array)
      ? sha256Bytes(rawResponseBytes)
      : null,
    deployment: latest
      ? {
        schema_version: DEPLOYMENT_ALLOCATION_ATTESTATION_SCHEMA,
        id: latest.id,
        created_on: latest.created_on,
        strategy: latest.strategy,
        versions: latest.versions.map(({ version_id, percentage }) => ({ version_id, percentage })),
        annotations: latest.annotations ?? {},
      }
      : null,
  };
}

export { SHA256 };
