import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  OfficialOpenRecoveryAdmissionError,
  validateOfficialOpenRecoveryAdmission,
} from '../src/official_open_recovery_admission.mjs';

const SESSION = '2026-09-02';
const SLOT = '0902';
const CODE = 'a'.repeat(40);

async function digest(bytes) {
  return Array.from(
    new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
  ).map((value) => value.toString(16).padStart(2, '0')).join('');
}

class OneObjectArchive {
  constructor(key, bytes) {
    this.key = key;
    this.bytes = bytes;
  }

  async get(key) {
    if (key !== this.key) return null;
    const bytes = this.bytes;
    return {
      async arrayBuffer() {
        return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
      },
    };
  }
}

function manifest({
  event = 'schedule',
  authority = 'NATIVE_GITHUB_SCHEDULE',
  capture = '2026-09-02T09:03:00+07:00',
  issued = '2026-09-02T02:02:30+00:00',
  captureCodeRef = CODE,
} = {}) {
  const provenance = {
    runner: 'GITHUB_ACTIONS',
    github_repository: 'samindriano/idx-trade',
    github_event_name: event,
    github_run_id: '123456',
    github_run_attempt: '1',
    capture_code_ref: captureCodeRef,
    logical_slot: SLOT,
    session_date: SESSION,
    trigger_authority: authority,
  };
  if (event === 'workflow_dispatch') {
    Object.assign(provenance, {
      scheduler_attestation_schema: 'idx_official_open_external_scheduler_attestation_v1',
      scheduler_issued_at_utc: issued,
      scheduler_nonce_sha256: 'b'.repeat(64),
      scheduler_attestation_sha256: 'c'.repeat(64),
    });
  }
  return {
    schema_version: 'idx_official_open_cloud_archive_v1',
    commit_state: 'COMMITTED',
    session_date: SESSION,
    slot: SLOT,
    scheduled_capture_timestamp_jakarta: '2026-09-02T09:02:00+07:00',
    source_capture_timestamp_jakarta: capture,
    execution_admission: 'CAPTURE_ONLY_NOT_EXECUTION_ADMITTED',
    runner_provenance: provenance,
  };
}

async function fixture(value) {
  const bytes = new TextEncoder().encode(JSON.stringify(value));
  const key = `official-open-v1/session_date=${SESSION}/slot=${SLOT}/slot_manifest.json`;
  return {
    archive: new OneObjectArchive(key, bytes),
    expectedCompletionSha256: await digest(bytes),
  };
}

test('timely native schedule archive is recovery-admissible only after hash binding', async () => {
  const data = await fixture(manifest());
  const result = await validateOfficialOpenRecoveryAdmission({
    ...data,
    session: SESSION,
    slot: SLOT,
    expectedCodeCommit: CODE,
  });
  assert.equal(result.recovery_admissible, true);
  assert.equal(result.trigger_authority, 'NATIVE_GITHUB_SCHEDULE');
});

test('timely HMAC-authorized external scheduler archive is recovery-admissible', async () => {
  const data = await fixture(manifest({
    event: 'workflow_dispatch',
    authority: 'TRUSTED_EXTERNAL_SCHEDULER_V1',
  }));
  const result = await validateOfficialOpenRecoveryAdmission({
    ...data,
    session: SESSION,
    slot: SLOT,
    expectedCodeCommit: CODE,
  });
  assert.equal(result.recovery_admissible, true);
  assert.equal(result.trigger_authority, 'TRUSTED_EXTERNAL_SCHEDULER_V1');
});

test('late source capture remains archive evidence but cannot suppress recovery', async () => {
  const data = await fixture(manifest({ capture: '2026-09-02T09:08:00+07:00' }));
  await assert.rejects(
    validateOfficialOpenRecoveryAdmission({
      ...data,
      session: SESSION,
      slot: SLOT,
      expectedCodeCommit: CODE,
    }),
    (error) => error instanceof OfficialOpenRecoveryAdmissionError
      && error.code === 'OFFICIAL_OPEN_RECOVERY_CAPTURE_AFTER_CUTOFF',
  );
});

test('manual or untrusted workflow_dispatch provenance cannot become recovery completion', async () => {
  const data = await fixture(manifest({
    event: 'workflow_dispatch',
    authority: 'MANUAL_WORKFLOW_DISPATCH',
  }));
  await assert.rejects(
    validateOfficialOpenRecoveryAdmission({
      ...data,
      session: SESSION,
      slot: SLOT,
      expectedCodeCommit: CODE,
    }),
    (error) => error instanceof OfficialOpenRecoveryAdmissionError
      && error.code === 'OFFICIAL_OPEN_RECOVERY_EXTERNAL_AUTHORITY_INVALID',
  );
});

test('completion hash and accepted producer pin are both mandatory', async () => {
  const data = await fixture(manifest());
  await assert.rejects(
    validateOfficialOpenRecoveryAdmission({
      ...data,
      session: SESSION,
      slot: SLOT,
      expectedCompletionSha256: 'd'.repeat(64),
      expectedCodeCommit: CODE,
    }),
    (error) => error instanceof OfficialOpenRecoveryAdmissionError
      && error.code === 'OFFICIAL_OPEN_RECOVERY_COMPLETION_SHA_MISMATCH',
  );

  await assert.rejects(
    validateOfficialOpenRecoveryAdmission({
      ...data,
      session: SESSION,
      slot: SLOT,
      expectedCodeCommit: 'e'.repeat(40),
    }),
    (error) => error instanceof OfficialOpenRecoveryAdmissionError
      && error.code === 'OFFICIAL_OPEN_RECOVERY_PROVENANCE_IDENTITY_INVALID',
  );
});

test('process path validates Official Open admission before accepting durable completion', () => {
  const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');
  const admission = source.indexOf('validateOfficialOpenRecoveryAdmission({');
  const durableAccept = source.indexOf("if (shadow.durable_completion.capture_complete) {", admission + 1);
  assert.ok(admission >= 0);
  assert.ok(durableAccept > admission);
  assert.match(source, /FAIL_CLOSED_OFFICIAL_OPEN_RECOVERY_ADMISSION_INVALID/);
  assert.match(source, /OFFICIAL_OPEN_EXPECTED_CODE_COMMIT/);
});

test('Official Open in-flight GitHub metadata cannot consume the sole recovery opportunity', () => {
  const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');
  assert.match(
    source,
    /const openInFlightRecoveryOverride = isOfficialOpenSlot\(slot\)[\s\S]*&& shadow\.active_mode_decision === 'DEFER_VISIBLE_IN_FLIGHT_GRACE_NOT_CAPTURE_COMPLETE'/,
  );
  assert.match(
    source,
    /shadow\.active_mode_decision === 'DEFER_VISIBLE_IN_FLIGHT_GRACE_NOT_CAPTURE_COMPLETE'[\s\S]*&& !openInFlightRecoveryOverride/,
  );
  assert.match(source, /const activeModeDecision = openInFlightRecoveryOverride/);
  assert.match(source, /OPEN_IN_FLIGHT_RECOVERY_DECISION/);
  assert.match(source, /open_inflight_recovery_override: openInFlightRecoveryOverride/);
});
