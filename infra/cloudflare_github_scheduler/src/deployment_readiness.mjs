import { parseRecoveryScope } from './core.mjs';
import {
  EXPECTED_DURABLE_OBJECT,
  EXPECTED_EXPORT,
  EXPECTED_IMPLEMENTATION_PINS,
  EXPECTED_R2,
  EXPECTED_CRONS,
  PROFILE_IDS,
  PRODUCTION_SCOPE,
  canonicalProfileId,
  getProfileContract,
  relevantImplementationPinNames,
  requiredSecretNames as contractRequiredSecretNames,
  scopeExpectationMatches,
} from './profile_contracts.mjs';

export const PRODUCTION_CANARY_SCOPE = Object.freeze([...PRODUCTION_SCOPE]);
export const PRODUCTION_CRONS = Object.freeze([...EXPECTED_CRONS]);

const GIT_SHA = /^[0-9a-f]{40}$/;
const SHA256 = /^[0-9a-f]{64}$/;
const IDENTIFIER_START = /[A-Za-z_$]/;
const IDENTIFIER_PART = /[A-Za-z0-9_$]/;

const REQUIRED_DURABLE_OBJECT = Object.freeze(EXPECTED_DURABLE_OBJECT);
const REQUIRED_R2 = Object.freeze(EXPECTED_R2);
const REQUIRED_EXPORT = Object.freeze({ type: 'durable-object', storage: 'sqlite' });

function issue(code, detail = undefined) {
  return detail === undefined ? { code } : { code, detail };
}

function sameArray(actual, expected) {
  return Array.isArray(actual)
    && Array.isArray(expected)
    && actual.length === expected.length
    && actual.every((value, index) => (
      value === expected[index]
      || (
        value && expected[index]
        && typeof value === 'object'
        && typeof expected[index] === 'object'
        && JSON.stringify(value) === JSON.stringify(expected[index])
      )
    ));
}

function sameObject(actual, expected) {
  return actual && typeof actual === 'object' && !Array.isArray(actual)
    && Object.keys(actual).length === Object.keys(expected).length
    && Object.keys(expected).every((key) => actual[key] === expected[key]);
}

function expectedSecretNames({ mode, allowedSlotIds = [], profile = null } = {}) {
  const canonical = profile ? canonicalProfileId(profile) : null;
  if (canonical === PROFILE_IDS.PRODUCTION_PREPARATION || canonical === PROFILE_IDS.STAGING_LIVE_OBSERVE_ONLY) {
    return contractRequiredSecretNames({ mode, allowedSlotIds, profile: canonical });
  }
  return contractRequiredSecretNames({ mode, allowedSlotIds });
}

export function requiredSecretNames({ mode, allowedSlotIds = [], profile = null } = {}) {
  return expectedSecretNames({ mode, allowedSlotIds, profile });
}

function expectedPinsForSlots(allowedSlotIds) {
  return relevantImplementationPinNames(allowedSlotIds)
    .reduce((pins, name) => ({ ...pins, [name]: EXPECTED_IMPLEMENTATION_PINS[name] }), {});
}

function validateRelevantPins(vars, allowedSlotIds, issues) {
  const expectedPins = expectedPinsForSlots(allowedSlotIds);
  for (const [name, expected] of Object.entries(expectedPins)) {
    if (typeof vars?.[name] !== 'string' || !GIT_SHA.test(vars[name]) || vars[name] !== expected) {
      issues.push(issue('IMPLEMENTATION_PIN_INVALID_OR_UNEXPECTED', {
        name,
        actual: vars?.[name],
        expected,
      }));
    }
  }
  return expectedPins;
}

export function validateDeploymentConfig(config, { profile = 'production_active_intraday_2030' } = {}) {
  const issues = [];
  const canonical = canonicalProfileId(profile);
  const contract = getProfileContract(canonical);
  if (!contract) {
    issues.push(issue('UNKNOWN_DEPLOYMENT_PROFILE', profile));
    return { ok: false, issues, profile: canonical, mode: config?.vars?.DISPATCH_MODE ?? null };
  }

  const vars = config?.vars ?? {};
  const mode = vars.DISPATCH_MODE;
  const scope = parseRecoveryScope(vars.RECOVERY_ALLOWED_SLOTS, mode);
  const allowedSlotIds = [...scope.allowedSlotIds].sort();
  const expectedScope = contract.scope.kind === 'exact' ? [...contract.scope.slotIds].sort() : [];

  if (config?.name !== contract.workerName) issues.push(issue('WORKER_IDENTITY_MISMATCH', {
    actual: config?.name,
    expected: contract.workerName,
  }));
  if (config?.main !== 'src/index.js') issues.push(issue('ENTRYPOINT_NOT_CANONICAL'));
  if (config?.compatibility_date !== '2026-08-27') issues.push(issue('COMPATIBILITY_DATE_MISMATCH', {
    actual: config?.compatibility_date,
    expected: '2026-08-27',
  }));
  if (config?.workers_dev !== false) issues.push(issue('WORKERS_DEV_MUST_BE_DISABLED'));
  if (vars.GITHUB_OWNER !== 'samindriano' || vars.GITHUB_REPO !== 'idx-trade') {
    issues.push(issue('GITHUB_REPOSITORY_IDENTITY_MISMATCH'));
  }
  if (vars.GITHUB_REF !== 'main') issues.push(issue('GITHUB_REF_MUST_BE_MAIN'));
  if (mode !== contract.mode) issues.push(issue('PROFILE_DISPATCH_MODE_MISMATCH', {
    actual: mode,
    expected: contract.mode,
  }));

  const scopeMatch = scopeExpectationMatches(scope, contract);
  if (!scopeMatch.ok) issues.push(issue('PROFILE_SCOPE_MISMATCH', scopeMatch));
  if (contract.scope.kind === 'exact' && (!scope.valid || scope.failClosed)) {
    issues.push(issue('ACTIVE_SCOPE_FAIL_CLOSED', scope.reason));
  }

  const actualSecrets = config?.secrets?.required;
  const requiredSecrets = expectedSecretNames({ mode, allowedSlotIds, profile: canonical });
  if (!sameArray(actualSecrets, requiredSecrets)) {
    issues.push(issue('SECRET_DECLARATION_SCOPE_MISMATCH', {
      actual: actualSecrets,
      expected: requiredSecrets,
    }));
  }

  const expectedPins = validateRelevantPins(vars, allowedSlotIds, issues);
  if (!sameArray(config?.r2_buckets, [REQUIRED_R2])) {
    issues.push(issue('R2_BINDING_MISSING_OR_WRONG', { expected: [REQUIRED_R2], actual: config?.r2_buckets }));
  }
  if (!sameArray(config?.durable_objects?.bindings, [REQUIRED_DURABLE_OBJECT])) {
    issues.push(issue('DURABLE_OBJECT_BINDING_MISSING_OR_WRONG', {
      expected: [REQUIRED_DURABLE_OBJECT],
      actual: config?.durable_objects?.bindings,
    }));
  }
  if (!sameObject(config?.exports?.SchedulerCoordinator, REQUIRED_EXPORT)) {
    issues.push(issue('DURABLE_OBJECT_EXPORT_MISSING_OR_WRONG', {
      expected: REQUIRED_EXPORT,
      actual: config?.exports?.SchedulerCoordinator,
    }));
  }

  const crons = config?.triggers?.crons;
  if (!sameArray(crons, contract.crons)) {
    issues.push(issue('PROFILE_CRON_CONFIGURATION_MISMATCH', {
      actual: crons,
      expected: contract.crons,
    }));
  }

  return {
    ok: issues.length === 0,
    issues,
    profile: canonical,
    mode,
    workerName: contract.workerName,
    traffic: contract.traffic,
    scope: {
      configured: scope.configured,
      valid: scope.valid,
      failClosed: scope.failClosed,
      status: scope.status,
      allowedSlotIds,
      expectedSlotIds: expectedScope,
    },
    requiredSecrets,
    expectedPins,
    bindings: {
      r2: REQUIRED_R2,
      durableObject: REQUIRED_DURABLE_OBJECT,
      durableObjectExport: EXPECTED_EXPORT,
    },
    crons: Array.isArray(crons) ? crons : null,
    expectedConfig: {
      entrypoint: 'src/index.js',
      compatibility_date: '2026-08-27',
      workers_dev: false,
      github_owner: 'samindriano',
      github_repo: 'idx-trade',
      github_ref: 'main',
    },
  };
}

function isIdentifierStart(value) {
  return value !== undefined && IDENTIFIER_START.test(value);
}

function isIdentifierPart(value) {
  return value !== undefined && IDENTIFIER_PART.test(value);
}

// Token scanning deliberately ignores comments, quoted strings, and template
// text so those cannot satisfy the bundle contract.
export function tokenizeJavaScript(source) {
  const tokens = [];
  let index = 0;
  while (index < source.length) {
    const current = source[index];
    const next = source[index + 1];
    if (/\s/.test(current)) {
      index += 1;
      continue;
    }
    if (current === '/' && next === '/') {
      index += 2;
      while (index < source.length && source[index] !== '\n') index += 1;
      continue;
    }
    if (current === '/' && next === '*') {
      index += 2;
      while (index < source.length && !(source[index] === '*' && source[index + 1] === '/')) index += 1;
      index += 2;
      continue;
    }
    if (current === '"' || current === "'" || current === '`') {
      const quote = current;
      index += 1;
      while (index < source.length) {
        if (source[index] === '\\') index += 2;
        else if (source[index] === quote) { index += 1; break; }
        else index += 1;
      }
      continue;
    }
    if (isIdentifierStart(current)) {
      const start = index;
      index += 1;
      while (isIdentifierPart(source[index])) index += 1;
      tokens.push(source.slice(start, index));
      continue;
    }
    // Regex literals are not runtime identifiers. Skip their body in common
    // expression-start positions so /scheduled/ cannot pass the check.
    const previous = tokens[tokens.length - 1];
    if (current === '/' && previous !== undefined && ['=', '(', '[', '{', ',', ':', ';', '!', '?'].includes(previous)) {
      index += 1;
      let inClass = false;
      while (index < source.length) {
        if (source[index] === '\\') index += 2;
        else if (source[index] === '[') { inClass = true; index += 1; }
        else if (source[index] === ']' && inClass) { inClass = false; index += 1; }
        else if (source[index] === '/' && !inClass) {
          index += 1;
          while (/[A-Za-z]/.test(source[index] ?? '')) index += 1;
          break;
        } else index += 1;
      }
      continue;
    }
    tokens.push(current);
    index += 1;
  }
  return tokens;
}

function hasFunctionProperty(tokens, name) {
  return tokens.some((token, index) => {
    if (token !== name || tokens[index + 1] !== '(') return false;
    const previous = tokens[index - 1];
    const beforePrevious = tokens[index - 2];
    // A helper named `scheduled` is not a Worker handler. Accept method
    // syntax used by the Wrangler bundle, but reject function declarations.
    return previous !== 'function'
      && previous !== '*'
      && !(previous === 'async' && beforePrevious === 'function');
  });
}

function hasMemberAccess(tokens, name) {
  return tokens.some((token, index) => token === '.' && tokens[index + 1] === name);
}

export function inspectBundleStructure(source) {
  const tokens = tokenizeJavaScript(source);
  const handlerNames = ['scheduled', 'fetch'].filter((name) => hasFunctionProperty(tokens, name));
  const hasScheduledHandler = hasFunctionProperty(tokens, 'scheduled');
  const references = {
    ARCHIVE: hasMemberAccess(tokens, 'ARCHIVE'),
    COORDINATOR: hasMemberAccess(tokens, 'COORDINATOR'),
    RECOVERY_ALLOWED_SLOTS: hasMemberAccess(tokens, 'RECOVERY_ALLOWED_SLOTS'),
  };
  const isStub = !hasScheduledHandler && handlerNames.length === 1 && handlerNames[0] === 'fetch';
  return { tokens, handlerNames, hasScheduledHandler, references, isStub };
}

export function validateBundleSource(source, { entrypoint = 'src/index.js', expectedHandlers = ['scheduled'] } = {}) {
  const issues = [];
  if (typeof source !== 'string' || source.trim() === '') {
    issues.push(issue('BUNDLE_BYTES_MISSING'));
    return { ok: false, issues, entrypoint, handlerNames: [], isStub: false, hasScheduledHandler: false, references: {} };
  }
  const structure = inspectBundleStructure(source);
  if (structure.isStub) issues.push(issue('BUNDLE_IS_STUB'));
  if (!sameArray(structure.handlerNames, expectedHandlers)) {
    issues.push(issue('BUNDLE_HANDLER_SET_MISMATCH', { actual: structure.handlerNames, expected: expectedHandlers }));
  }
  if (!structure.references.ARCHIVE) issues.push(issue('R2_BINDING_REFERENCE_MISSING'));
  if (!structure.references.COORDINATOR) issues.push(issue('DURABLE_OBJECT_REFERENCE_MISSING'));
  if (!structure.references.RECOVERY_ALLOWED_SLOTS) issues.push(issue('RECOVERY_SCOPE_REFERENCE_MISSING'));
  return {
    ok: issues.length === 0,
    issues,
    entrypoint,
    handlerNames: structure.handlerNames,
    isStub: structure.isStub,
    hasScheduledHandler: structure.hasScheduledHandler,
    references: structure.references,
  };
}

export function validateBundleIdentity({ actualSha256, actualSizeBytes, expectedSha256 = null, expectedSizeBytes = null } = {}) {
  const issues = [];
  if (typeof actualSha256 !== 'string' || !SHA256.test(actualSha256)) issues.push(issue('BUNDLE_SHA256_INVALID'));
  if (!Number.isInteger(actualSizeBytes) || actualSizeBytes <= 0) issues.push(issue('BUNDLE_SIZE_INVALID'));
  if (expectedSha256 !== null && actualSha256 !== expectedSha256) issues.push(issue('BUNDLE_SHA256_MISMATCH', { actual: actualSha256, expected: expectedSha256 }));
  if (expectedSizeBytes !== null && actualSizeBytes !== expectedSizeBytes) issues.push(issue('BUNDLE_SIZE_MISMATCH', { actual: actualSizeBytes, expected: expectedSizeBytes }));
  return { ok: issues.length === 0, issues, actualSha256, actualSizeBytes };
}

function readbackBinding(readback, name) {
  return readback?.bindings?.[name];
}

export function validateDeploymentReadback(readback, {
  workerName,
  versionId,
  deploymentId = undefined,
  bundleSha256,
  bundleSizeBytes,
  configSha256 = undefined,
  manifestSha256 = undefined,
  mode,
  allowedSlotIds,
  crons,
  expectedHandlers = ['scheduled'],
  expectedSecretNames = [],
  compatibilityDate = '2026-08-27',
  workersDev = false,
  r2BucketName = REQUIRED_R2.bucket_name,
  durableObjectClassName = REQUIRED_DURABLE_OBJECT.class_name,
  durableObjectStorage = 'sqlite',
  githubOwner = 'samindriano',
  githubRepo = 'idx-trade',
  githubRef = 'main',
  scopeConfigured = true,
  expectedImplementationPins = {},
  expectedTrafficPercentage = 100,
} = {}) {
  const issues = [];
  if (!readback || typeof readback !== 'object') return { ok: false, issues: [issue('READBACK_MISSING')] };
  if (readback.schema_version !== 'IDX-CLOUDFLARE-READBACK-V1') issues.push(issue('READBACK_SCHEMA_UNKNOWN'));
  if (!workerName || readback.worker_name !== workerName) issues.push(issue('READBACK_WORKER_IDENTITY_MISMATCH'));
  if (!versionId || readback.version_id !== versionId) issues.push(issue('READBACK_VERSION_ID_MISMATCH'));
  if (deploymentId !== undefined && readback.deployment_id !== deploymentId) issues.push(issue('READBACK_DEPLOYMENT_ID_MISMATCH'));
  if (!bundleSha256 || readback.bundle_sha256 !== bundleSha256) issues.push(issue('READBACK_BUNDLE_SHA256_MISMATCH'));
  if (!Number.isInteger(bundleSizeBytes) || readback.bundle_size_bytes !== bundleSizeBytes) issues.push(issue('READBACK_BUNDLE_SIZE_MISMATCH'));
  if (configSha256 !== undefined && readback.config_sha256 !== configSha256) issues.push(issue('READBACK_CONFIG_SHA256_MISMATCH'));
  if (manifestSha256 !== undefined && readback.manifest_sha256 !== manifestSha256) issues.push(issue('READBACK_MANIFEST_SHA256_MISMATCH'));
  if (readback.entrypoint !== 'src/index.js') issues.push(issue('READBACK_ENTRYPOINT_MISMATCH'));
  if (!sameArray(readback.handlers, expectedHandlers)) issues.push(issue('READBACK_HANDLER_SET_MISMATCH', { actual: readback.handlers, expected: expectedHandlers }));
  if (readback.stub !== false) issues.push(issue('READBACK_STUB_BUNDLE'));
  if (readback.compatibility_date !== compatibilityDate) issues.push(issue('READBACK_COMPATIBILITY_DATE_MISMATCH'));
  if (readback.workers_dev !== workersDev) issues.push(issue('READBACK_WORKERS_DEV_MISMATCH'));
  if (readback.vars?.GITHUB_OWNER !== githubOwner) issues.push(issue('READBACK_GITHUB_OWNER_MISMATCH'));
  if (readback.vars?.GITHUB_REPO !== githubRepo) issues.push(issue('READBACK_GITHUB_REPO_MISMATCH'));
  if (readback.vars?.GITHUB_REF !== githubRef) issues.push(issue('READBACK_GITHUB_REF_MISMATCH'));
  if (readback.vars?.DISPATCH_MODE !== mode) issues.push(issue('READBACK_DISPATCH_MODE_MISMATCH'));
  if (readback.scope_configured !== scopeConfigured) issues.push(issue('READBACK_SCOPE_CONFIGURATION_MISMATCH', {
    actual: readback.scope_configured,
    expected: scopeConfigured,
  }));
  if (scopeConfigured) {
    if (!sameArray([...(readback.vars?.RECOVERY_ALLOWED_SLOTS ?? [])].sort(), [...(allowedSlotIds ?? [])].sort())) {
      issues.push(issue('READBACK_SCOPE_MISMATCH'));
    }
  } else if (Object.prototype.hasOwnProperty.call(readback.vars ?? {}, 'RECOVERY_ALLOWED_SLOTS')) {
    issues.push(issue('READBACK_UNEXPECTED_UNCONFIGURED_SCOPE'));
  }
  for (const [name, expected] of Object.entries(expectedImplementationPins)) {
    if (readback.vars?.[name] !== expected) issues.push(issue('READBACK_IMPLEMENTATION_PIN_MISMATCH', {
      name,
      actual: readback.vars?.[name],
      expected,
    }));
  }
  if (!sameArray(readback.secret_names, expectedSecretNames)) issues.push(issue('READBACK_SECRET_DECLARATION_MISMATCH'));
  if (!sameArray(readback.crons, crons)) issues.push(issue('READBACK_CRON_MISMATCH'));
  if (readback.traffic_percentage !== expectedTrafficPercentage) issues.push(issue('READBACK_TRAFFIC_NOT_EXACT', { actual: readback.traffic_percentage, expected: expectedTrafficPercentage }));
  if (readback.traffic_ambiguous === true) issues.push(issue('READBACK_TRAFFIC_AMBIGUOUS'));
  if (typeof readback.remote_script_etag !== 'string' || readback.remote_script_etag.length === 0) issues.push(issue('READBACK_REMOTE_SCRIPT_IDENTITY_UNKNOWN'));
  if (readback.config_sha256 === undefined) issues.push(issue('READBACK_CONFIG_SHA256_UNKNOWN'));
  if (readback.manifest_sha256 === undefined) issues.push(issue('READBACK_MANIFEST_SHA256_UNKNOWN'));
  if (readbackBinding(readback, 'ARCHIVE')?.type !== 'r2_bucket' || readbackBinding(readback, 'ARCHIVE')?.bucket_name !== r2BucketName) issues.push(issue('READBACK_R2_BINDING_MISSING_OR_WRONG'));
  if (readbackBinding(readback, 'COORDINATOR')?.type !== 'durable_object' || readbackBinding(readback, 'COORDINATOR')?.class_name !== durableObjectClassName) issues.push(issue('READBACK_DURABLE_OBJECT_BINDING_MISSING_OR_WRONG'));
  if (readback.exports?.SchedulerCoordinator?.type !== 'durable-object' || readback.exports?.SchedulerCoordinator?.storage !== durableObjectStorage) issues.push(issue('READBACK_DURABLE_OBJECT_EXPORT_MISSING_OR_WRONG'));
  return { ok: issues.length === 0, issues };
}

export function validateControllerState({ windowsAutomatic = false, watchdogProcessCount = 0, cloudflare = {} } = {}) {
  const issues = [];
  const windowsActive = windowsAutomatic || watchdogProcessCount > 0;
  const cloudflareScheduled = cloudflare.mode === 'active' && cloudflare.cronActive === true;
  // Cron activation is itself an automatic controller, even when its
  // candidate/readiness proof is incomplete. This keeps Windows ON plus any
  // active Cloudflare schedule fail-closed as a dual-controller state.
  // An active Cron is an automatic controller even if its readiness proof is
  // incomplete. Readiness is a separate gate, not a way to hide dual control.
  const cloudflareActive = cloudflareScheduled;
  if (!windowsActive && !cloudflareActive) issues.push(issue('NO_AUTOMATIC_RECOVERY_CONTROLLER'));
  if (windowsActive && cloudflareScheduled) issues.push(issue('MULTIPLE_AUTOMATIC_RECOVERY_CONTROLLERS'));
  if (cloudflareScheduled && cloudflare.ready !== true) issues.push(issue('CLOUDFLARE_ACTIVE_NOT_READY'));
  if (!cloudflare.ready && !windowsActive) issues.push(issue('WINDOWS_OFF_CLOUDFLARE_NOT_READY'));
  if (cloudflareActive && cloudflare.ready === true && cloudflare.bundleReady !== true) {
    issues.push(issue('CLOUDFLARE_ACTIVE_BUNDLE_NOT_READY'));
  }
  return { ok: issues.length === 0, issues, windowsActive, cloudflareActive, cloudflareScheduled };
}

export { REQUIRED_DURABLE_OBJECT, REQUIRED_EXPORT, REQUIRED_R2, SHA256, GIT_SHA };
