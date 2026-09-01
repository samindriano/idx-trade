import {
  CompletionContractError,
  completionChildRefs,
  validateE2ECompletion,
  validateIntradayCompletion,
  validateOfficialOpenCompletion,
  validatePreopenCaCompletion,
} from './completion.mjs';
import { exactRunRecoveryDecision } from './core.mjs';

export const ARCHIVE_BUCKET_NAME = 'idx-trade-stockbit-stream-v1';
export const ARCHIVE_PREFIX = Object.freeze({
  E2E: 'e2e-paper-v1',
  PREOPEN_CA: 'e2e-paper-v1',
  OFFICIAL_OPEN: 'official-open-v1',
  INTRADAY: 'stockbit-intraday-v1',
});

const SHA256 = /^[0-9a-f]{64}$/;
const GIT_SHA = /^[0-9a-f]{40}$/;
const INTRADAY_SLOTS = Object.freeze(['1830', '1930', '2030']);

export class ArchiveCompletionError extends Error {
  constructor(code) {
    super(code);
    this.name = 'ArchiveCompletionError';
    this.code = code;
  }
}

function fail(code) {
  throw new ArchiveCompletionError(code);
}

function safeKey(value) {
  if (
    typeof value !== 'string'
    || !value
    || value.startsWith('/')
    || value.split('/').some((part) => part === '' || part === '.' || part === '..')
  ) fail('ARCHIVE_KEY_INVALID');
  return value;
}

function sha(value) {
  if (typeof value !== 'string' || !SHA256.test(value)) fail('ARCHIVE_SHA_INVALID');
  return value;
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value) ?? 'undefined';
}

function parseJson(bytes, code) {
  if (!(bytes instanceof Uint8Array)) fail(code);
  try {
    const value = JSON.parse(new TextDecoder().decode(bytes));
    if (!value || typeof value !== 'object' || Array.isArray(value)) fail(code);
    return value;
  } catch {
    fail(code);
  }
}

function safeRelative(value) {
  if (
    typeof value !== 'string'
    || !value
    || value.startsWith('/')
    || value.split('/').some((part) => part === '' || part === '.' || part === '..')
  ) fail('ARCHIVE_PREOPEN_INPUT_MANIFEST_INVALID');
  return value;
}

async function digest(bytes) {
  return Array.from(
    new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', bytes)),
  ).map((value) => value.toString(16).padStart(2, '0')).join('');
}

async function readObject(archive, key) {
  if (!archive || typeof archive.get !== 'function') fail('ARCHIVE_BINDING_MISSING');
  let object;
  try {
    object = await archive.get(key);
  } catch {
    fail('ARCHIVE_READ_FAILED');
  }
  if (object === null || object === undefined) return null;
  if (typeof object.arrayBuffer !== 'function') fail('ARCHIVE_OBJECT_BODY_INVALID');
  try {
    const buffer = await object.arrayBuffer();
    if (!(buffer instanceof ArrayBuffer)) fail('ARCHIVE_OBJECT_BYTES_INVALID');
    return new Uint8Array(buffer);
  } catch {
    fail('ARCHIVE_READ_FAILED');
  }
}

async function readLogicalObject(archive, family, logicalKey) {
  safeKey(logicalKey);
  const prefix = ARCHIVE_PREFIX[family];
  if (!prefix) fail('ARCHIVE_FAMILY_PREFIX_MISSING');
  return readObject(archive, `${prefix}/${logicalKey}`);
}

function familyForSlot(slot) {
  if (slot?.workflow === 'e2e-paper-cloud-orchestration.yml') {
    if (slot.inputValue === 'PREOPEN_CA') return 'PREOPEN_CA';
    return 'E2E';
  }
  if (slot?.workflow === 'official-open-prospective-cloud-capture.yml') return 'OFFICIAL_OPEN';
  if (slot?.workflow === 'stockbit-intraday-cloud-production.yml') return 'INTRADAY';
  return null;
}

function completionKey(family, session, slot) {
  switch (family) {
    case 'E2E': return `sessions/${session}/stages/${slot.inputValue}/commit.json`;
    case 'PREOPEN_CA': return `sessions/${session}/checkpoints/PREOPEN_CA/commit.json`;
    case 'OFFICIAL_OPEN': return `session_date=${session}/slot=${slot.inputValue}/slot_manifest.json`;
    case 'INTRADAY': return `sessions/${session}/slots/${slot.inputValue}/commit.json`;
    default: fail('ARCHIVE_FAMILY_UNSUPPORTED');
  }
}

function noCompletion(family, grain, reason) {
  return {
    capture_complete: false,
    state: 'not_complete',
    family,
    grain,
    completion_key: null,
    completion_sha256: null,
    reason,
  };
}

function blocked(family, grain, reason) {
  return {
    capture_complete: false,
    state: 'archive_completion_blocked',
    family,
    grain,
    completion_key: null,
    completion_sha256: null,
    reason,
  };
}

function childRoles(family) {
  switch (family) {
    case 'E2E': return ['result', 'snapshot'];
    case 'PREOPEN_CA': return ['snapshot', 'result'];
    case 'OFFICIAL_OPEN': return ['raw_response', 'open_prices', 'source_manifest'];
    case 'INTRADAY': return ['result', 'snapshot'];
    default: fail('ARCHIVE_FAMILY_UNSUPPORTED');
  }
}

async function readChildren(archive, family, parentBytes) {
  let refs;
  try {
    refs = completionChildRefs(family, parentBytes).refs;
  } catch (error) {
    if (error instanceof CompletionContractError) fail(error.code);
    throw error;
  }
  const roles = childRoles(family);
  const childHashes = {};
  const children = {};
  const seen = new Set();
  for (let index = 0; index < refs.length; index += 1) {
    const ref = refs[index];
    const key = safeKey(ref.key);
    const expected = sha(ref.sha256);
    if (seen.has(key)) fail('ARCHIVE_CHILD_KEY_DUPLICATE');
    seen.add(key);
    const bytes = await readLogicalObject(archive, family, key);
    if (bytes === null) fail('ARCHIVE_CHILD_MISSING');
    const actual = await digest(bytes);
    if (actual !== expected) fail('ARCHIVE_CHILD_HASH_MISMATCH');
    childHashes[key] = actual;
    children[roles[index]] = { key, bytes, sha256: actual };
  }
  return { childHashes, children };
}

async function readPreopenExpectations(archive, expectedCodeCommit) {
  if (typeof expectedCodeCommit !== 'string' || !GIT_SHA.test(expectedCodeCommit)) {
    fail('ARCHIVE_PREOPEN_EXPECTED_CODE_COMMIT_INVALID');
  }
  const manifestKey = 'inputs/manifest.json';
  const manifestBytes = await readLogicalObject(archive, 'E2E', manifestKey);
  if (manifestBytes === null) fail('ARCHIVE_PREOPEN_INPUT_MANIFEST_MISSING');
  const manifest = parseJson(manifestBytes, 'ARCHIVE_PREOPEN_INPUT_MANIFEST_INVALID');
  if (
    manifest.schema_version !== 'idx_trade_e2e_paper_cloud_inputs_v1'
    || manifest.contract_version !== 'CLOUD_FIRST_E2E_PAPER_V1'
    || !Array.isArray(manifest.files)
    || !manifest.roles || typeof manifest.roles !== 'object' || Array.isArray(manifest.roles)
  ) fail('ARCHIVE_PREOPEN_INPUT_MANIFEST_INVALID');
  const requiredRoles = new Set([
    'execution_schedule',
    'execution_schedule_source',
    'clean_panel',
    'clean_security_master',
    'model_manifest',
    'model_control_h5',
    'model_control_h10',
    'model_challenger_h5',
    'model_challenger_h10',
    'model_fit_log',
  ]);
  const refsByRole = new Map();
  const relativePaths = new Set();
  for (const ref of manifest.files) {
    if (!ref || typeof ref !== 'object' || Array.isArray(ref) || typeof ref.role !== 'string' || !ref.role || refsByRole.has(ref.role)) {
      fail('ARCHIVE_PREOPEN_INPUT_MANIFEST_INVALID');
    }
    safeKey(ref.key);
    sha(ref.sha256);
    const relative = safeRelative(ref.relative_path);
    if (relativePaths.has(relative) || typeof ref.content_type !== 'string' || !ref.content_type) {
      fail('ARCHIVE_PREOPEN_INPUT_MANIFEST_INVALID');
    }
    relativePaths.add(relative);
    refsByRole.set(ref.role, ref);
  }
  for (const role of requiredRoles) {
    const ref = refsByRole.get(role);
    if (!ref || manifest.roles[role] !== ref.relative_path) fail('ARCHIVE_PREOPEN_INPUT_MANIFEST_INVALID');
  }
  for (const [role, relative] of Object.entries(manifest.roles)) {
    if (!refsByRole.has(role) || safeRelative(relative) !== refsByRole.get(role).relative_path) {
      fail('ARCHIVE_PREOPEN_INPUT_MANIFEST_INVALID');
    }
  }
  if (manifest.execution_schedule_sha256 !== undefined && manifest.execution_schedule_sha256 !== refsByRole.get('execution_schedule').sha256) {
    fail('ARCHIVE_PREOPEN_INPUT_MANIFEST_INVALID');
  }
  if (manifest.manifest_payload_sha256 !== undefined) {
    const declaredPayloadSha = sha(manifest.manifest_payload_sha256);
    const body = { ...manifest };
    delete body.manifest_payload_sha256;
    const actualPayloadSha = await digest(new TextEncoder().encode(`${canonicalJson(body)}\n`));
    if (actualPayloadSha !== declaredPayloadSha) fail('ARCHIVE_PREOPEN_INPUT_MANIFEST_INVALID');
  }
  const scheduleRefs = manifest.files.filter((ref) => ref && ref.role === 'execution_schedule');
  if (scheduleRefs.length !== 1) fail('ARCHIVE_PREOPEN_SCHEDULE_REF_INVALID');
  const scheduleRef = scheduleRefs[0];
  const scheduleKey = safeKey(scheduleRef.key);
  const scheduleSha = sha(scheduleRef.sha256);
  const scheduleBytes = await readLogicalObject(archive, 'E2E', scheduleKey);
  if (scheduleBytes === null || await digest(scheduleBytes) !== scheduleSha) {
    fail('ARCHIVE_PREOPEN_SCHEDULE_REF_INVALID');
  }
  return {
    expectedScheduleSha256: scheduleSha,
    expectedInputManifestSha256: await digest(manifestBytes),
    expectedCodeCommit,
  };
}

function isKnownIntradayWaiting(parentBytes, session, slot) {
  try {
    const value = parseJson(parentBytes, 'ARCHIVE_INTRADAY_PARENT_INVALID');
    const guards = value.guards;
    return value.schema_version === 'idx_trade_stockbit_intraday_cloud_slot_v1'
      && value.commit_state === 'COMMITTED'
      && value.session_date === session
      && value.slot === slot
      && value.status === 'WAITING_RECOVERY_RETRY'
      && guards && guards.synthetic_fill_used === false
      && guards.retroactive_capture_used === false
      && guards.outcome_accessed === false;
  } catch {
    return false;
  }
}

async function validateSingle({ archive, family, slot, session, expectedCodeCommit }) {
  const grain = family === 'E2E'
    ? 'session_stage'
    : family === 'PREOPEN_CA'
      ? 'session_preopen_ca_checkpoint'
      : 'session_observation_slot';
  const key = completionKey(family, session, slot);
  const parentBytes = await readLogicalObject(archive, family, key);
  if (parentBytes === null) return noCompletion(family, grain, 'ARCHIVE_PARENT_MISSING');

  let child;
  try {
    child = await readChildren(archive, family, parentBytes);
    const parentSha = await digest(parentBytes);
    let validated;
    if (family === 'E2E') {
      validated = await validateE2ECompletion({
        expectedSession: session,
        expectedStage: slot.inputValue,
        resultBytes: child.children.result.bytes,
        snapshotSha256: child.children.snapshot.sha256,
        childHashes: child.childHashes,
        completionKey: key,
        completionSha256: parentSha,
        completionBytes: parentBytes,
      });
    } else if (family === 'OFFICIAL_OPEN') {
      validated = await validateOfficialOpenCompletion({
        expectedSession: session,
        expectedSlot: slot.inputValue,
        childHashes: child.childHashes,
        completionKey: key,
        completionSha256: parentSha,
        completionBytes: parentBytes,
      });
    } else {
      const expectations = await readPreopenExpectations(archive, expectedCodeCommit);
      validated = await validatePreopenCaCompletion({
        expectedSession: session,
        expectedScheduleSha256: expectations.expectedScheduleSha256,
        expectedInputManifestSha256: expectations.expectedInputManifestSha256,
        expectedCodeCommit: expectations.expectedCodeCommit,
        resultBytes: child.children.result.bytes,
        snapshotSha256: child.children.snapshot.sha256,
        childHashes: child.childHashes,
        completionKey: key,
        completionSha256: parentSha,
        completionBytes: parentBytes,
      });
    }
    return {
      ...validated,
      state: 'capture_complete',
      status: 'DURABLE_COMPLETION_VERIFIED',
    };
  } catch (error) {
    const reason = error instanceof CompletionContractError || error instanceof ArchiveCompletionError
      ? error.code
      : 'ARCHIVE_COMPLETION_VALIDATION_FAILED';
    return blocked(family, grain, reason);
  }
}

async function validateIntraday({ archive, slot, session }) {
  const family = 'INTRADAY';
  const grain = 'session_recovery_objective';
  const targetIndex = INTRADAY_SLOTS.indexOf(slot.inputValue);
  if (targetIndex < 0) return blocked(family, grain, 'ARCHIVE_INTRADAY_SLOT_INVALID');

  for (const candidateSlot of INTRADAY_SLOTS.slice(0, targetIndex + 1)) {
    const key = `sessions/${session}/slots/${candidateSlot}/commit.json`;
    const parentBytes = await readLogicalObject(archive, family, key);
    if (parentBytes === null) continue;
    if (isKnownIntradayWaiting(parentBytes, session, candidateSlot)) continue;

    try {
      const child = await readChildren(archive, family, parentBytes);
      const claimKey = `sessions/${session}/slots/${candidateSlot}/claim.json`;
      const claimBytes = await readLogicalObject(archive, family, claimKey);
      if (claimBytes === null) fail('ARCHIVE_INTRADAY_CLAIM_MISSING');
      const claimSha = await digest(claimBytes);
      const parentSha = await digest(parentBytes);
      const validated = await validateIntradayCompletion({
        expectedSession: session,
        expectedSlot: candidateSlot,
        resultBytes: child.children.result.bytes,
        snapshotSha256: child.children.snapshot.sha256,
        claimSha256: claimSha,
        claimBytes,
        childHashes: child.childHashes,
        completionKey: key,
        completionSha256: parentSha,
        completionBytes: parentBytes,
      });
      return {
        ...validated,
        state: 'capture_complete',
        status: 'DURABLE_COMPLETION_VERIFIED',
        completion_slot: candidateSlot,
      };
    } catch (error) {
      const reason = error instanceof CompletionContractError || error instanceof ArchiveCompletionError
        ? error.code
        : 'ARCHIVE_COMPLETION_VALIDATION_FAILED';
      return blocked(family, grain, reason);
    }
  }
  return noCompletion(family, grain, 'ARCHIVE_PARENT_MISSING_OR_NOT_COMPLETE');
}

export async function readDurableCompletion({ archive, slot, session, expectedCodeCommit }) {
  const family = familyForSlot(slot);
  if (!family) {
    return blocked('UNKNOWN', 'unknown', 'ARCHIVE_FAMILY_UNSUPPORTED');
  }
  try {
    if (family === 'INTRADAY') return await validateIntraday({ archive, slot, session });
    return await validateSingle({ archive, family, slot, session, expectedCodeCommit });
  } catch (error) {
    const grain = family === 'INTRADAY' ? 'session_recovery_objective' : family === 'E2E' ? 'session_stage' : family === 'PREOPEN_CA' ? 'session_preopen_ca_checkpoint' : 'session_observation_slot';
    const reason = error instanceof ArchiveCompletionError ? error.code : 'ARCHIVE_COMPLETION_READ_FAILED';
    return blocked(family, grain, reason);
  }
}

function sanitizedRun(run) {
  return {
    id: Number.isInteger(run?.id) ? run.id : null,
    event: run?.event ?? null,
    head_branch: run?.head_branch ?? null,
    ref: run?.ref ?? null,
    run_name: run?.run_name ?? run?.runName ?? null,
    display_title: run?.display_title ?? null,
    status: run?.status ?? null,
    conclusion: run?.conclusion ?? null,
    created_at: run?.created_at ?? null,
    updated_at: run?.updated_at ?? null,
  };
}

function sourceAgreement(exactRuns, durable) {
  const sources = { native_schedule: [], workflow_dispatch: [] };
  for (const run of exactRuns) sources[run.event === 'schedule' ? 'native_schedule' : 'workflow_dispatch'].push(run);
  const result = {};
  for (const [source, runs] of Object.entries(sources)) {
    result[source] = {
      observed: runs.length > 0,
      agrees_with_durable: runs.length === 0 ? null : durable.state === 'archive_completion_blocked' ? null : durable.capture_complete === true,
      reason: runs.length === 0
        ? 'NO_EXACT_RUN_EVIDENCE'
        : durable.capture_complete === true
          ? 'EXACT_RUN_AND_DURABLE_COMPLETION_AGREE'
          : durable.state === 'archive_completion_blocked'
            ? 'DURABLE_COMPLETION_BLOCKED'
            : 'EXACT_RUN_IS_PROVENANCE_ONLY_WITHOUT_DURABLE_COMPLETION',
    };
  }
  return result;
}

export async function evaluateShadowSlot({ archive, slot, session, observedEpochMs, exactRuns = [], githubError = null, expectedCodeCommit }) {
  const durable = await readDurableCompletion({ archive, slot, session, expectedCodeCommit });
  const inFlight = exactRuns
    .map((run) => ({ run, decision: exactRunRecoveryDecision(run, observedEpochMs) }))
    .find((entry) => entry.decision?.defer);
  const activeModeDecision = durable.capture_complete
    ? 'CAPTURE_ALREADY_COMPLETE'
    : durable.state === 'archive_completion_blocked'
      ? 'FAIL_CLOSED_ARCHIVE_COMPLETION_AMBIGUOUS'
      : githubError
        ? 'FAIL_CLOSED_GITHUB_PROVENANCE_UNAVAILABLE'
        : inFlight
          ? 'DEFER_VISIBLE_IN_FLIGHT_GRACE_NOT_CAPTURE_COMPLETE'
          : 'WORKFLOW_DISPATCH_WOULD_BE_ELIGIBLE';
  return {
    slot_id: slot.id,
    family: durable.family,
    logical_slot: slot.id,
    durable_completion: durable,
    github_exact_run_evidence: {
      status: githubError ? 'QUERY_FAILED' : exactRuns.length ? 'EXACT_RUNS_FOUND' : 'NO_EXACT_RUN',
      error: githubError,
      runs: exactRuns.map((run) => sanitizedRun(run)),
    },
    active_mode_decision: activeModeDecision,
    native_watchdog_agreement: sourceAgreement(exactRuns, durable),
  };
}

export { familyForSlot };
