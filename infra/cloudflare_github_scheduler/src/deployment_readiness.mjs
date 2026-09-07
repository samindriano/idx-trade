import { parseRecoveryScope } from './core.mjs';

export const PRODUCTION_CANARY_SCOPE = Object.freeze(['STOCKBIT_INTRADAY_2030']);

export const PRODUCTION_CRONS = Object.freeze([
  '35,50 1 * * 1-5',
  '0,5,15,22 2 * * 1-5',
  '40 11 * * 1-5',
  '10,40 12 * * 1-5',
  '40 13 * * 1-5',
]);

const REQUIRED_R2 = Object.freeze({
  binding: 'ARCHIVE',
  bucket_name: 'idx-trade-stockbit-stream-v1',
});

const REQUIRED_DURABLE_OBJECT = Object.freeze({
  name: 'COORDINATOR',
  class_name: 'SchedulerCoordinator',
});

const REQUIRED_EXPORT = Object.freeze({
  type: 'durable-object',
  storage: 'sqlite',
});

const GIT_SHA = /^[0-9a-f]{40}$/;
const SHA256 = /^[0-9a-f]{64}$/;

const sameArray = (actual, expected) => (
  Array.isArray(actual)
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
  ))
);

const sameObject = (actual, expected) => (
  actual && typeof actual === 'object' && !Array.isArray(actual)
  && Object.keys(expected).every((key) => actual[key] === expected[key])
);

function issue(code, detail = undefined) {
  return detail === undefined ? { code } : { code, detail };
}

export function requiredSecretNames({ mode, allowedSlotIds = [] }) {
  if (mode === 'observe_only') return ['GITHUB_ACTIONS_READ_TOKEN'];
  if (mode !== 'active') return [];
  const names = ['GITHUB_ACTIONS_READ_TOKEN', 'GITHUB_ACTIONS_WRITE_TOKEN'];
  if (allowedSlotIds.some((slotId) => slotId.startsWith('OFFICIAL_OPEN_'))) {
    names.push('OFFICIAL_OPEN_SCHEDULER_HMAC_KEY');
  }
  return names;
}

export function validateDeploymentConfig(config, {
  profile = 'production',
  expectedScope = null,
  expectedCrons = null,
} = {}) {
  const issues = [];
  const vars = config?.vars ?? {};
  const mode = vars.DISPATCH_MODE;
  const scope = parseRecoveryScope(vars.RECOVERY_ALLOWED_SLOTS, mode);
  const allowedSlotIds = [...scope.allowedSlotIds].sort();

  if (config?.main !== 'src/index.js') issues.push(issue('ENTRYPOINT_NOT_CANONICAL'));
  if (config?.workers_dev !== false) issues.push(issue('WORKERS_DEV_MUST_BE_DISABLED'));
  if (vars.GITHUB_OWNER !== 'samindriano' || vars.GITHUB_REPO !== 'idx-trade') {
    issues.push(issue('GITHUB_REPOSITORY_IDENTITY_MISMATCH'));
  }
  if (vars.GITHUB_REF !== 'main') issues.push(issue('GITHUB_REF_MUST_BE_MAIN'));
  if (!['active', 'observe_only'].includes(mode)) issues.push(issue('DISPATCH_MODE_INVALID'));

  if (mode === 'active') {
    if (scope.failClosed || !scope.valid) {
      issues.push(issue('ACTIVE_SCOPE_FAIL_CLOSED', scope.reason));
    } else if (scope.allowedSlotIds.size === 0) {
      issues.push(issue('ACTIVE_SCOPE_EMPTY'));
    }
    if (expectedScope && !sameArray(allowedSlotIds, [...expectedScope].sort())) {
      issues.push(issue('ACTIVE_SCOPE_NOT_EXPECTED', {
        actual: allowedSlotIds,
        expected: [...expectedScope].sort(),
      }));
    }
  } else if (mode === 'observe_only' && scope.failClosed) {
    issues.push(issue('OBSERVE_SCOPE_INVALID', scope.reason));
  }

  const expectedSecrets = requiredSecretNames({ mode, allowedSlotIds });
  const actualSecrets = config?.secrets?.required;
  if (!sameArray(actualSecrets, expectedSecrets)) {
    issues.push(issue('SECRET_DECLARATION_SCOPE_MISMATCH', {
      actual: actualSecrets,
      expected: expectedSecrets,
    }));
  }

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
  if (!Array.isArray(crons)) {
    issues.push(issue('CRON_CONFIGURATION_MISSING'));
  } else if (expectedCrons && !sameArray(crons, expectedCrons)) {
    issues.push(issue('CRON_CONFIGURATION_MISMATCH', { actual: crons, expected: expectedCrons }));
  } else if (mode === 'active' && crons.length === 0) {
    issues.push(issue('ACTIVE_CRON_CONFIGURATION_EMPTY'));
  } else if (profile === 'preparation' && crons.length !== 0) {
    issues.push(issue('PREPARATION_CRON_CONFIGURATION_NOT_EMPTY', { actual: crons }));
  }

  return {
    ok: issues.length === 0,
    issues,
    profile,
    mode,
    scope: {
      configured: scope.configured,
      valid: scope.valid,
      failClosed: scope.failClosed,
      status: scope.status,
      allowedSlotIds,
    },
    requiredSecrets: expectedSecrets,
    bindings: {
      r2: REQUIRED_R2,
      durableObject: REQUIRED_DURABLE_OBJECT,
      durableObjectExport: REQUIRED_EXPORT,
    },
    crons: Array.isArray(crons) ? crons : null,
  };
}

export function validateBundleSource(source, { entrypoint = 'src/index.js' } = {}) {
  const issues = [];
  if (typeof source !== 'string' || source.trim() === '') {
    issues.push(issue('BUNDLE_BYTES_MISSING'));
  } else {
    const normalized = source.trim();
    if (/^export\s+default\s*\{\s*fetch\s*\(\)\s*\{\s*\}\s*\}\s*;?$/s.test(normalized)) {
      issues.push(issue('BUNDLE_IS_STUB'));
    }
    if (!/\basync\s+scheduled\s*\(/.test(source)) issues.push(issue('SCHEDULED_HANDLER_MISSING'));
    if (!/\bARCHIVE\b/.test(source)) issues.push(issue('R2_BINDING_REFERENCE_MISSING'));
    if (!/\bCOORDINATOR\b/.test(source)) issues.push(issue('DURABLE_OBJECT_REFERENCE_MISSING'));
    if (!/RECOVERY_ALLOWED_SLOTS/.test(source)) issues.push(issue('RECOVERY_SCOPE_REFERENCE_MISSING'));
  }
  return {
    ok: issues.length === 0,
    issues,
    entrypoint,
    isStub: issues.some(({ code }) => code === 'BUNDLE_IS_STUB'),
    hasScheduledHandler: issues.every(({ code }) => code !== 'SCHEDULED_HANDLER_MISSING'),
  };
}

export function validateBundleIdentity({
  actualSha256,
  actualSizeBytes,
  expectedSha256 = null,
  expectedSizeBytes = null,
} = {}) {
  const issues = [];
  if (typeof actualSha256 !== 'string' || !SHA256.test(actualSha256)) {
    issues.push(issue('BUNDLE_SHA256_INVALID'));
  }
  if (!Number.isInteger(actualSizeBytes) || actualSizeBytes <= 0) {
    issues.push(issue('BUNDLE_SIZE_INVALID'));
  }
  if (expectedSha256 !== null && actualSha256 !== expectedSha256) {
    issues.push(issue('BUNDLE_SHA256_MISMATCH', { actual: actualSha256, expected: expectedSha256 }));
  }
  if (expectedSizeBytes !== null && actualSizeBytes !== expectedSizeBytes) {
    issues.push(issue('BUNDLE_SIZE_MISMATCH', { actual: actualSizeBytes, expected: expectedSizeBytes }));
  }
  return { ok: issues.length === 0, issues, actualSha256, actualSizeBytes };
}

function readbackBinding(readback, name) {
  return readback?.bindings?.[name];
}

export function validateDeploymentReadback(readback, {
  workerName,
  versionId,
  bundleSha256,
  bundleSizeBytes,
  mode,
  allowedSlotIds,
  crons,
  r2BucketName = REQUIRED_R2.bucket_name,
  durableObjectClassName = REQUIRED_DURABLE_OBJECT.class_name,
  githubOwner = 'samindriano',
  githubRepo = 'idx-trade',
  githubRef = 'main',
} = {}) {
  const issues = [];
  if (!workerName || readback?.worker_name !== workerName) issues.push(issue('READBACK_WORKER_IDENTITY_MISMATCH'));
  if (!versionId || readback?.version_id !== versionId) issues.push(issue('READBACK_VERSION_ID_MISMATCH'));
  if (!bundleSha256 || readback?.bundle_sha256 !== bundleSha256) issues.push(issue('READBACK_BUNDLE_SHA256_MISMATCH'));
  if (bundleSizeBytes !== undefined && readback?.bundle_size_bytes !== bundleSizeBytes) issues.push(issue('READBACK_BUNDLE_SIZE_MISMATCH'));
  if (readback?.entrypoint !== 'src/index.js') issues.push(issue('READBACK_ENTRYPOINT_MISMATCH'));
  if (readback?.handlers?.scheduled !== true) issues.push(issue('READBACK_SCHEDULED_HANDLER_MISSING'));
  if (readback?.handlers?.stub !== false) issues.push(issue('READBACK_STUB_BUNDLE'));
  if (readback?.vars?.GITHUB_OWNER !== githubOwner) issues.push(issue('READBACK_GITHUB_OWNER_MISMATCH'));
  if (readback?.vars?.GITHUB_REPO !== githubRepo) issues.push(issue('READBACK_GITHUB_REPO_MISMATCH'));
  if (readback?.vars?.GITHUB_REF !== githubRef) issues.push(issue('READBACK_GITHUB_REF_MISMATCH'));
  if (readback?.vars?.DISPATCH_MODE !== mode) issues.push(issue('READBACK_DISPATCH_MODE_MISMATCH'));
  if (!sameArray([...(readback?.vars?.RECOVERY_ALLOWED_SLOTS ?? [])].sort(), [...(allowedSlotIds ?? [])].sort())) {
    issues.push(issue('READBACK_SCOPE_MISMATCH'));
  }
  if (!sameArray(readback?.crons, crons)) issues.push(issue('READBACK_CRON_MISMATCH'));
  if (readbackBinding(readback, 'ARCHIVE')?.bucket_name !== r2BucketName) {
    issues.push(issue('READBACK_R2_BINDING_MISSING_OR_WRONG'));
  }
  if (
    readbackBinding(readback, 'COORDINATOR')?.class_name !== durableObjectClassName
    || readbackBinding(readback, 'COORDINATOR')?.type !== 'durable_object'
  ) {
    issues.push(issue('READBACK_DURABLE_OBJECT_BINDING_MISSING_OR_WRONG'));
  }
  return { ok: issues.length === 0, issues };
}

export function validateControllerState({
  windowsAutomatic = false,
  watchdogProcessCount = 0,
  cloudflare = {},
} = {}) {
  const issues = [];
  const windowsActive = windowsAutomatic || watchdogProcessCount > 0;
  const cloudflareScheduled = cloudflare.mode === 'active' && cloudflare.cronActive === true;
  const cloudflareActive = cloudflareScheduled && cloudflare.ready === true;
  if (!windowsActive && !cloudflareActive) issues.push(issue('NO_AUTOMATIC_RECOVERY_CONTROLLER'));
  if (windowsActive && cloudflareScheduled) issues.push(issue('MULTIPLE_AUTOMATIC_RECOVERY_CONTROLLERS'));
  if (cloudflareScheduled && cloudflare.ready !== true) issues.push(issue('CLOUDFLARE_ACTIVE_NOT_READY'));
  if (!cloudflare.ready && !windowsActive) issues.push(issue('WINDOWS_OFF_CLOUDFLARE_NOT_READY'));
  if (cloudflareActive && cloudflare.bundleReady !== true) issues.push(issue('CLOUDFLARE_ACTIVE_BUNDLE_NOT_READY'));
  return {
    ok: issues.length === 0,
    issues,
    windowsActive,
    cloudflareActive,
    cloudflareScheduled,
  };
}

export { REQUIRED_DURABLE_OBJECT, REQUIRED_EXPORT, REQUIRED_R2, SHA256, GIT_SHA };
