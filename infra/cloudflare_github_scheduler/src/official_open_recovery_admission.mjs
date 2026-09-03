const SHA256 = /^[0-9a-f]{64}$/;
const GIT_SHA = /^[0-9a-f]{40}$/;
const DIGITS = /^\d+$/;

const SLOT_WINDOWS = Object.freeze({
  '0902': ['09:02', '09:08'],
  '0912': ['09:12', '09:18'],
  '0922': ['09:22', '09:23'],
});

const ARCHIVE_PREFIX = 'official-open-v1';
const REPOSITORY = 'samindriano/idx-trade';
const NATIVE_AUTHORITY = 'NATIVE_GITHUB_SCHEDULE';
const EXTERNAL_AUTHORITY = 'TRUSTED_EXTERNAL_SCHEDULER_V1';
const ATTESTATION_SCHEMA = 'idx_official_open_external_scheduler_attestation_v1';

export class OfficialOpenRecoveryAdmissionError extends Error {
  constructor(code) {
    super(code);
    this.name = 'OfficialOpenRecoveryAdmissionError';
    this.code = code;
  }
}

function fail(code) {
  throw new OfficialOpenRecoveryAdmissionError(code);
}

function object(value, code) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(code);
  return value;
}

function jakartaMs(session, hhmm) {
  const value = Date.parse(`${session}T${hhmm}:00+07:00`);
  if (!Number.isFinite(value)) fail('OFFICIAL_OPEN_RECOVERY_SESSION_INVALID');
  return value;
}

function timestampMs(value, code) {
  if (typeof value !== 'string' || !value.trim()) fail(code);
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) fail(code);
  return parsed;
}

async function sha256(bytes) {
  return Array.from(
    new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', bytes)),
  ).map((value) => value.toString(16).padStart(2, '0')).join('');
}

async function readManifestBytes(archive, session, slot) {
  if (!archive || typeof archive.get !== 'function') fail('OFFICIAL_OPEN_RECOVERY_ARCHIVE_BINDING_MISSING');
  const key = `${ARCHIVE_PREFIX}/session_date=${session}/slot=${slot}/slot_manifest.json`;
  let objectBody;
  try {
    objectBody = await archive.get(key);
  } catch {
    fail('OFFICIAL_OPEN_RECOVERY_ARCHIVE_READ_FAILED');
  }
  if (!objectBody || typeof objectBody.arrayBuffer !== 'function') {
    fail('OFFICIAL_OPEN_RECOVERY_MANIFEST_MISSING');
  }
  let buffer;
  try {
    buffer = await objectBody.arrayBuffer();
  } catch {
    fail('OFFICIAL_OPEN_RECOVERY_ARCHIVE_READ_FAILED');
  }
  if (!(buffer instanceof ArrayBuffer)) fail('OFFICIAL_OPEN_RECOVERY_MANIFEST_BYTES_INVALID');
  return { key, bytes: new Uint8Array(buffer) };
}

function validateWindow(manifest, session, slot) {
  const window = SLOT_WINDOWS[slot];
  if (!window) fail('OFFICIAL_OPEN_RECOVERY_SLOT_INVALID');
  const dueMs = jakartaMs(session, window[0]);
  const cutoffMs = jakartaMs(session, window[1]);
  const scheduledMs = timestampMs(
    manifest.scheduled_capture_timestamp_jakarta,
    'OFFICIAL_OPEN_RECOVERY_SCHEDULE_TIMESTAMP_INVALID',
  );
  if (scheduledMs !== dueMs) fail('OFFICIAL_OPEN_RECOVERY_SCHEDULE_TIMESTAMP_MISMATCH');
  const capturedMs = timestampMs(
    manifest.source_capture_timestamp_jakarta,
    'OFFICIAL_OPEN_RECOVERY_CAPTURE_TIMESTAMP_INVALID',
  );
  if (capturedMs < dueMs) fail('OFFICIAL_OPEN_RECOVERY_CAPTURE_BEFORE_SLOT');
  if (capturedMs >= cutoffMs) fail('OFFICIAL_OPEN_RECOVERY_CAPTURE_AFTER_CUTOFF');
  return { dueMs, cutoffMs, capturedMs };
}

function validateProvenance(manifest, session, slot, expectedCodeCommit, window) {
  if (typeof expectedCodeCommit !== 'string' || !GIT_SHA.test(expectedCodeCommit)) {
    fail('OFFICIAL_OPEN_RECOVERY_EXPECTED_CODE_COMMIT_INVALID');
  }
  const provenance = object(
    manifest.runner_provenance,
    'OFFICIAL_OPEN_RECOVERY_PROVENANCE_MISSING',
  );
  if (
    provenance.runner !== 'GITHUB_ACTIONS'
    || provenance.github_repository !== REPOSITORY
    || provenance.session_date !== session
    || provenance.logical_slot !== slot
    || provenance.capture_code_ref !== expectedCodeCommit
    || !DIGITS.test(String(provenance.github_run_id ?? ''))
    || !DIGITS.test(String(provenance.github_run_attempt ?? ''))
  ) fail('OFFICIAL_OPEN_RECOVERY_PROVENANCE_IDENTITY_INVALID');

  if (provenance.github_event_name === 'schedule') {
    if (provenance.trigger_authority !== NATIVE_AUTHORITY) {
      fail('OFFICIAL_OPEN_RECOVERY_NATIVE_AUTHORITY_INVALID');
    }
    return { authority: NATIVE_AUTHORITY, provenance };
  }

  if (provenance.github_event_name !== 'workflow_dispatch') {
    fail('OFFICIAL_OPEN_RECOVERY_EVENT_INVALID');
  }
  if (
    provenance.trigger_authority !== EXTERNAL_AUTHORITY
    || provenance.scheduler_attestation_schema !== ATTESTATION_SCHEMA
    || typeof provenance.scheduler_nonce_sha256 !== 'string'
    || !SHA256.test(provenance.scheduler_nonce_sha256)
    || typeof provenance.scheduler_attestation_sha256 !== 'string'
    || !SHA256.test(provenance.scheduler_attestation_sha256)
  ) fail('OFFICIAL_OPEN_RECOVERY_EXTERNAL_AUTHORITY_INVALID');
  const issuedMs = timestampMs(
    provenance.scheduler_issued_at_utc,
    'OFFICIAL_OPEN_RECOVERY_ATTESTATION_TIME_INVALID',
  );
  if (issuedMs < window.dueMs || issuedMs >= window.cutoffMs || issuedMs > window.capturedMs) {
    fail('OFFICIAL_OPEN_RECOVERY_ATTESTATION_TIME_OUTSIDE_SLOT');
  }
  return { authority: EXTERNAL_AUTHORITY, provenance };
}

export async function validateOfficialOpenRecoveryAdmission({
  archive,
  session,
  slot,
  expectedCompletionSha256,
  expectedCodeCommit,
}) {
  if (typeof expectedCompletionSha256 !== 'string' || !SHA256.test(expectedCompletionSha256)) {
    fail('OFFICIAL_OPEN_RECOVERY_COMPLETION_SHA_INVALID');
  }
  const read = await readManifestBytes(archive, session, slot);
  const actualSha = await sha256(read.bytes);
  if (actualSha !== expectedCompletionSha256) {
    fail('OFFICIAL_OPEN_RECOVERY_COMPLETION_SHA_MISMATCH');
  }
  let manifest;
  try {
    manifest = JSON.parse(new TextDecoder().decode(read.bytes));
  } catch {
    fail('OFFICIAL_OPEN_RECOVERY_MANIFEST_JSON_INVALID');
  }
  object(manifest, 'OFFICIAL_OPEN_RECOVERY_MANIFEST_JSON_INVALID');
  if (
    manifest.schema_version !== 'idx_official_open_cloud_archive_v1'
    || manifest.commit_state !== 'COMMITTED'
    || manifest.session_date !== session
    || manifest.slot !== slot
    || manifest.execution_admission !== 'CAPTURE_ONLY_NOT_EXECUTION_ADMITTED'
  ) fail('OFFICIAL_OPEN_RECOVERY_MANIFEST_IDENTITY_INVALID');

  const window = validateWindow(manifest, session, slot);
  const provenance = validateProvenance(
    manifest,
    session,
    slot,
    expectedCodeCommit,
    window,
  );
  return {
    recovery_admissible: true,
    completion_key: read.key,
    completion_sha256: actualSha,
    trigger_authority: provenance.authority,
    source_capture_timestamp_jakarta: manifest.source_capture_timestamp_jakarta,
  };
}

export { ATTESTATION_SCHEMA, EXTERNAL_AUTHORITY, NATIVE_AUTHORITY, SLOT_WINDOWS };
