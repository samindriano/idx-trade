// Completion validation is deliberately separate from GitHub run metadata.
// These validators describe the existing archive commit/manifest contracts;
// the caller must obtain child bytes from that existing archive authority and
// pass their computed hashes. They do not create a second archive authority or
// infer completion from a claim, dispatch response, or workflow conclusion.

export const COMPLETION_GRAIN = Object.freeze({
  E2E: 'session_stage',
  PREOPEN_CA: 'session_preopen_ca_checkpoint',
  OFFICIAL_OPEN: 'session_observation_slot',
  INTRADAY: 'session_recovery_objective',
  STREAM: 'observation_slot_universe_source_identity',
});

export const CAPTURE_COMPLETION_STATE = 'capture_complete';

const SHA256 = /^[0-9a-f]{64}$/;
const GIT_SHA = /^[0-9a-f]{40}$/;
const E2E_STATUSES = Object.freeze({
  NOOP: new Set(['WEEKEND_OR_HOLIDAY_NOOP']),
  POST_EOD: new Set(['POST_EOD_PREPARED', 'MISSED_EXECUTION_NO_CERTIFIED_OPEN']),
  PREOPEN: new Set(['EXECUTION_COMPLETE', 'ALREADY_COMPLETE', 'MISSED_EXECUTION_NO_CERTIFIED_OPEN']),
});
export const INTRADAY_RECOVERABLE_INTERMEDIATE_STATES = Object.freeze([
  'WAITING_CANONICAL_EOD_GATE',
  'WAITING_RECOVERY_RETRY',
]);
const PREOPEN_CA_GUARDS = Object.freeze([
  'outcome_accessed',
  'protected_forward_accessed',
  'model_refit',
  'paper_state_mutated',
  'order_created',
  'fill_created',
  'retroactive_execution_authorized',
]);

export class CompletionContractError extends Error {
  constructor(code) {
    super(code);
    this.name = 'CompletionContractError';
    this.code = code;
  }
}

function fail(code) {
  throw new CompletionContractError(code);
}

function object(value, code) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(code);
  return value;
}

function sha(value, code) {
  if (typeof value !== 'string' || !SHA256.test(value)) fail(code);
  return value;
}

function gitSha(value, code) {
  if (typeof value !== 'string' || !GIT_SHA.test(value)) fail(code);
  return value;
}

function childHash(childHashes, ref, code) {
  const key = safeArchiveKey(ref?.key, code);
  const expected = typeof ref?.sha256 === 'string' ? ref.sha256 : '';
  if (!key || !SHA256.test(expected) || childHashes?.[key] !== expected) fail(code);
  return { key, sha256: expected };
}

function safeArchiveKey(value, code) {
  if (typeof value !== 'string' || !value || value.startsWith('/') || value.split('/').some((part) => part === '' || part === '.' || part === '..')) fail(code);
  return value;
}

function falseGuardSet(guards, fields, code) {
  const value = object(guards, code);
  for (const field of fields) if (value[field] !== false) fail(code);
}

function parseJson(value, code) {
  if (value instanceof Uint8Array) {
    try {
      const parsed = JSON.parse(new TextDecoder().decode(value));
      return object(parsed, code);
    } catch {
      fail(code);
    }
  }
  if (value && typeof value === 'object' && !Array.isArray(value)) return value;
  fail(code);
}

// This helper is intentionally limited to read planning.  It does not validate
// completion and it never emits a completion result; the family validator
// below remains the only completion authority.
export function completionChildRefs(family, completionBytes) {
  const value = parseJson(completionBytes, 'COMPLETION_PARENT_JSON_INVALID');
  const refs = (() => {
    switch (family) {
      case 'E2E':
        return [value.result, value.snapshot];
      case 'PREOPEN_CA':
        return [value.snapshot, value.result];
      case 'OFFICIAL_OPEN':
        return [value.artifacts?.raw_response, value.artifacts?.open_prices, value.artifacts?.source_manifest];
      case 'INTRADAY':
        return [value.result, value.snapshot];
      default:
        fail('UNKNOWN_COMPLETION_FAMILY');
    }
  })();
  if (refs.some((ref) => !ref || typeof ref !== 'object' || Array.isArray(ref) || typeof ref.key !== 'string')) {
    fail('COMPLETION_PARENT_CHILD_REFS_INVALID');
  }
  return { value, refs };
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value) ?? 'undefined';
}

function assertSemanticParentEquivalent(provided, parsed, code) {
  if (provided !== undefined && canonicalJson(provided) !== canonicalJson(parsed)) fail(code);
}

function result({ family, grain, key, sha256 }) {
  return {
    capture_complete: true,
    state: CAPTURE_COMPLETION_STATE,
    family,
    grain,
    completion_key: key,
    completion_sha256: sha256,
  };
}

async function completionIdentity({ completionKey, completionSha256, completionBytes, expectedKey, code }) {
  const key = safeArchiveKey(completionKey, `${code}_KEY_INVALID`);
  if (key !== expectedKey) fail(`${code}_KEY_INVALID`);
  const declaredSha256 = sha(completionSha256, `${code}_SHA_INVALID`);
  if (!(completionBytes instanceof Uint8Array)) fail(`${code}_BYTES_INVALID`);
  const actualSha256 = Array.from(
    new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', completionBytes)),
  ).map((value) => value.toString(16).padStart(2, '0')).join('');
  if (actualSha256 !== declaredSha256) fail(`${code}_SHA_MISMATCH`);
  return {
    key,
    sha256: declaredSha256,
    value: parseJson(completionBytes, `${code}_JSON_INVALID`),
  };
}

export async function validateIntradayRecoverableCommit({
  resultBytes,
  snapshotSha256,
  claimSha256,
  claimBytes,
  expectedSession,
  expectedSlot,
  childHashes = {},
  completionKey,
  completionSha256,
  completionBytes,
}) {
  const parent = await completionIdentity({
    completionKey,
    completionSha256,
    completionBytes,
    expectedKey: `sessions/${expectedSession}/slots/${expectedSlot}/commit.json`,
    code: 'INTRADAY_RECOVERABLE_PARENT',
  });
  const value = parent.value;
  if (
    value.schema_version !== 'idx_trade_stockbit_intraday_cloud_slot_v1'
    || value.commit_state !== 'COMMITTED'
    || value.session_date !== expectedSession
    || value.slot !== expectedSlot
    || !INTRADAY_RECOVERABLE_INTERMEDIATE_STATES.includes(value.status)
  ) fail('INTRADAY_RECOVERABLE_PARENT_INVALID');
  falseGuardSet(
    value.guards,
    ['synthetic_fill_used', 'retroactive_capture_used', 'outcome_accessed'],
    'INTRADAY_RECOVERABLE_GUARDS_INVALID',
  );

  const codeIdentity = object(value.code_identity, 'INTRADAY_RECOVERABLE_CODE_IDENTITY_INVALID');
  gitSha(codeIdentity.commit, 'INTRADAY_RECOVERABLE_CODE_IDENTITY_INVALID');
  const resultRef = childHash(childHashes, value.result, 'INTRADAY_RECOVERABLE_RESULT_INVALID');
  const snapshotRef = childHash(childHashes, value.snapshot, 'INTRADAY_RECOVERABLE_SNAPSHOT_INVALID');
  if (!(resultBytes instanceof Uint8Array)) fail('INTRADAY_RECOVERABLE_RESULT_BYTES_INVALID');
  const result = parseJson(resultBytes, 'INTRADAY_RECOVERABLE_RESULT_JSON_INVALID');
  if (
    result.session_date !== expectedSession
    || result.slot !== expectedSlot
    || result.status !== value.status
    || result.synthetic_fill_used !== false
    || result.retroactive_capture_used !== false
    || result.outcome_accessed !== false
  ) fail('INTRADAY_RECOVERABLE_RESULT_IDENTITY_INVALID');
  if (snapshotSha256 !== undefined && snapshotSha256 !== snapshotRef.sha256) {
    fail('INTRADAY_RECOVERABLE_SNAPSHOT_SHA_INVALID');
  }

  const declaredClaim = sha(value.claim_sha256, 'INTRADAY_RECOVERABLE_CLAIM_HASH_INVALID');
  if (!(claimBytes instanceof Uint8Array)) fail('INTRADAY_RECOVERABLE_CLAIM_MISSING');
  const actualClaimSha = Array.from(
    new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', claimBytes)),
  ).map((item) => item.toString(16).padStart(2, '0')).join('');
  if (actualClaimSha !== declaredClaim || claimSha256 !== declaredClaim) {
    fail('INTRADAY_RECOVERABLE_CLAIM_BINDING_INVALID');
  }
  const claim = parseJson(claimBytes, 'INTRADAY_RECOVERABLE_CLAIM_JSON_INVALID');
  if (
    claim.schema_version !== 'idx_trade_stockbit_intraday_cloud_claim_v1'
    || claim.claim_state !== 'CLAIMED'
    || claim.session_date !== expectedSession
    || claim.slot !== expectedSlot
    || typeof claim.claim_id !== 'string'
    || !claim.claim_id
  ) fail('INTRADAY_RECOVERABLE_CLAIM_INVALID');
  falseGuardSet(
    claim.guards,
    ['synthetic_fill_used', 'retroactive_capture_used', 'outcome_accessed'],
    'INTRADAY_RECOVERABLE_CLAIM_INVALID',
  );
  if (canonicalJson(claim.code_identity) !== canonicalJson(codeIdentity)) {
    fail('INTRADAY_RECOVERABLE_CLAIM_CODE_IDENTITY_INVALID');
  }

  return {
    recoverable_intermediate: true,
    status: value.status,
    completion_key: parent.key,
    completion_sha256: parent.sha256,
    result_key: resultRef.key,
    snapshot_key: snapshotRef.key,
    claim_sha256: declaredClaim,
  };
}

export async function validateE2ECompletion({ commit, resultBytes, snapshotSha256, expectedSession, expectedStage, childHashes = {}, completionKey, completionSha256, completionBytes }) {
  const parent = await completionIdentity({
    completionKey,
    completionSha256,
    completionBytes,
    expectedKey: `sessions/${expectedSession}/stages/${expectedStage}/commit.json`,
    code: 'E2E_COMPLETION_PARENT',
  });
  const value = parent.value;
  assertSemanticParentEquivalent(commit, value, 'E2E_COMPLETION_PARENT_SEMANTIC_MISMATCH');
  if (value.schema_version !== 'idx_trade_e2e_paper_cloud_stage_commit_v1' || value.commit_state !== 'COMMITTED') fail('E2E_COMPLETION_COMMIT_INVALID');
  if (value.contract_version !== 'CLOUD_FIRST_E2E_PAPER_V1') fail('E2E_COMPLETION_CONTRACT_INVALID');
  if (value.session_date !== expectedSession || value.stage !== expectedStage) fail('E2E_COMPLETION_IDENTITY_INVALID');
  if (!E2E_STATUSES[expectedStage]?.has(value.stage_status)) fail('E2E_COMPLETION_STATUS_INVALID');
  sha(value.schedule_attestation_sha256, 'E2E_COMPLETION_SCHEDULE_SHA_INVALID');
  sha(value.input_manifest_sha256, 'E2E_COMPLETION_INPUT_SHA_INVALID');
  gitSha(object(value.code_identity, 'E2E_COMPLETION_CODE_IDENTITY_INVALID').commit, 'E2E_COMPLETION_CODE_SHA_INVALID');
  falseGuardSet(value.guards, ['outcome_accessed', 'protected_forward_accessed', 'model_refit', 'retroactive_execution_authorized'], 'E2E_COMPLETION_GUARDS_INVALID');
  const resultRef = childHash(childHashes, value.result, 'E2E_COMPLETION_RESULT_INVALID');
  const snapshotRef = childHash(childHashes, value.snapshot, 'E2E_COMPLETION_SNAPSHOT_INVALID');
  if (resultBytes !== undefined) {
    const payload = parseJson(resultBytes, 'E2E_COMPLETION_RESULT_JSON_INVALID');
    if (payload.schema_version !== 'idx_trade_e2e_paper_cloud_runtime_v1' || payload.session_date !== expectedSession || payload.stage !== expectedStage || payload.stage_status !== value.stage_status) fail('E2E_COMPLETION_RESULT_IDENTITY_INVALID');
    if (payload.observed_availability_only !== true || payload.outcome_accessed !== false || payload.protected_forward_accessed !== false || payload.model_refit !== false) fail('E2E_COMPLETION_RESULT_GUARDS_INVALID');
  }
  if (snapshotSha256 !== undefined && snapshotSha256 !== snapshotRef.sha256) fail('E2E_COMPLETION_SNAPSHOT_SHA_INVALID');
  return result({ family: 'E2E', grain: COMPLETION_GRAIN.E2E, key: parent.key, sha256: parent.sha256 });
}

export async function validateOfficialOpenCompletion({ manifest, expectedSession, expectedSlot, childHashes = {}, completionKey, completionSha256, completionBytes }) {
  const parent = await completionIdentity({
    completionKey,
    completionSha256,
    completionBytes,
    expectedKey: `session_date=${expectedSession}/slot=${expectedSlot}/slot_manifest.json`,
    code: 'OFFICIAL_OPEN_COMPLETION_PARENT',
  });
  const value = parent.value;
  assertSemanticParentEquivalent(manifest, value, 'OFFICIAL_OPEN_COMPLETION_PARENT_SEMANTIC_MISMATCH');
  if (value.schema_version !== 'idx_official_open_cloud_archive_v1' || value.commit_state !== 'COMMITTED') fail('OFFICIAL_OPEN_COMPLETION_COMMIT_INVALID');
  if (value.session_date !== expectedSession || value.slot !== expectedSlot) fail('OFFICIAL_OPEN_COMPLETION_IDENTITY_INVALID');
  if (value.execution_admission !== 'CAPTURE_ONLY_NOT_EXECUTION_ADMITTED') fail('OFFICIAL_OPEN_COMPLETION_ADMISSION_INVALID');
  if (value.authority !== 'IDX' || value.field_semantics !== 'IDX_OFFICIAL_OPENPRICE' || value.source_execution_grade !== true) fail('OFFICIAL_OPEN_COMPLETION_SOURCE_INVALID');
  falseGuardSet(value.guards, ['model_accessed', 'outcome_accessed', 'paper_state_mutated', 'forward_counter_mutated', 'order_created', 'fill_created', 'retroactive_execution_authorized'], 'OFFICIAL_OPEN_COMPLETION_GUARDS_INVALID');
  const artifacts = object(value.artifacts, 'OFFICIAL_OPEN_COMPLETION_ARTIFACTS_INVALID');
  for (const name of ['raw_response', 'open_prices', 'source_manifest']) {
    const ref = object(artifacts[name], 'OFFICIAL_OPEN_COMPLETION_ARTIFACT_REF_INVALID');
    safeArchiveKey(ref.key, 'OFFICIAL_OPEN_COMPLETION_ARTIFACT_KEY_INVALID');
    childHash(childHashes, ref, 'OFFICIAL_OPEN_COMPLETION_ARTIFACT_HASH_INVALID');
  }
  return result({ family: 'OFFICIAL_OPEN', grain: COMPLETION_GRAIN.OFFICIAL_OPEN, key: parent.key, sha256: parent.sha256 });
}

export async function validateIntradayCompletion({ commit, resultBytes, snapshotSha256, claimSha256, claimBytes, expectedSession, expectedSlot, childHashes = {}, completionKey, completionSha256, completionBytes }) {
  const parent = await completionIdentity({
    completionKey,
    completionSha256,
    completionBytes,
    expectedKey: `sessions/${expectedSession}/slots/${expectedSlot}/commit.json`,
    code: 'INTRADAY_COMPLETION_PARENT',
  });
  const value = parent.value;
  assertSemanticParentEquivalent(commit, value, 'INTRADAY_COMPLETION_PARENT_SEMANTIC_MISMATCH');
  if (value.schema_version !== 'idx_trade_stockbit_intraday_cloud_slot_v1' || value.commit_state !== 'COMMITTED') fail('INTRADAY_COMPLETION_COMMIT_INVALID');
  if (value.session_date !== expectedSession || value.slot !== expectedSlot || value.status !== 'ADMISSIBLE_COMPLETE') fail('INTRADAY_COMPLETION_IDENTITY_OR_STATUS_INVALID');
  falseGuardSet(value.guards, ['synthetic_fill_used', 'retroactive_capture_used', 'outcome_accessed'], 'INTRADAY_COMPLETION_GUARDS_INVALID');
  sha(value.eod_manifest_sha256, 'INTRADAY_COMPLETION_EOD_SHA_INVALID');
  sha(value.session_manifest_sha256, 'INTRADAY_COMPLETION_SESSION_SHA_INVALID');
  const resultRef = childHash(childHashes, value.result, 'INTRADAY_COMPLETION_RESULT_INVALID');
  const snapshotRef = childHash(childHashes, value.snapshot, 'INTRADAY_COMPLETION_SNAPSHOT_INVALID');
  const declaredClaim = sha(value.claim_sha256, 'INTRADAY_COMPLETION_CLAIM_SHA_INVALID');
  if (claimSha256 !== undefined && declaredClaim !== claimSha256) fail('INTRADAY_COMPLETION_CLAIM_BINDING_INVALID');
  if (claimBytes !== undefined) {
    const codeIdentity = object(value.code_identity, 'INTRADAY_COMPLETION_CODE_IDENTITY_INVALID');
    gitSha(codeIdentity.commit, 'INTRADAY_COMPLETION_CODE_IDENTITY_INVALID');
    const claim = parseJson(claimBytes, 'INTRADAY_COMPLETION_CLAIM_JSON_INVALID');
    if (
      claim.schema_version !== 'idx_trade_stockbit_intraday_cloud_claim_v1'
      || claim.claim_state !== 'CLAIMED'
      || claim.session_date !== expectedSession
      || claim.slot !== expectedSlot
      || typeof claim.claim_id !== 'string'
      || !claim.claim_id
    ) fail('INTRADAY_COMPLETION_CLAIM_INVALID');
    const claimGuards = object(claim.guards, 'INTRADAY_COMPLETION_CLAIM_INVALID');
    falseGuardSet(claimGuards, ['synthetic_fill_used', 'retroactive_capture_used', 'outcome_accessed'], 'INTRADAY_COMPLETION_CLAIM_INVALID');
    if (canonicalJson(claim.code_identity) !== canonicalJson(codeIdentity)) fail('INTRADAY_COMPLETION_CLAIM_CODE_IDENTITY_INVALID');
  }
  if (resultBytes !== undefined) {
    const payload = parseJson(resultBytes, 'INTRADAY_COMPLETION_RESULT_JSON_INVALID');
    if (payload.session_date !== expectedSession || payload.slot !== expectedSlot || payload.status !== 'ADMISSIBLE_COMPLETE') fail('INTRADAY_COMPLETION_RESULT_IDENTITY_INVALID');
    if (payload.synthetic_fill_used !== false || payload.retroactive_capture_used !== false || payload.outcome_accessed !== false) fail('INTRADAY_COMPLETION_RESULT_GUARDS_INVALID');
  }
  if (snapshotSha256 !== undefined && snapshotSha256 !== snapshotRef.sha256) fail('INTRADAY_COMPLETION_SNAPSHOT_SHA_INVALID');
  return result({ family: 'INTRADAY', grain: COMPLETION_GRAIN.INTRADAY, key: parent.key, sha256: parent.sha256 });
}

export async function validatePreopenCaCompletion({ checkpoint, resultBytes, snapshotSha256, expectedSession, expectedScheduleSha256, expectedInputManifestSha256, expectedCodeCommit, childHashes = {}, completionKey, completionSha256, completionBytes }) {
  const parent = await completionIdentity({
    completionKey,
    completionSha256,
    completionBytes,
    expectedKey: `sessions/${expectedSession}/checkpoints/PREOPEN_CA/commit.json`,
    code: 'PREOPEN_CA_COMPLETION_PARENT',
  });
  const value = parent.value;
  assertSemanticParentEquivalent(checkpoint, value, 'PREOPEN_CA_COMPLETION_PARENT_SEMANTIC_MISMATCH');
  if (value.schema_version !== 'idx_trade_e2e_paper_preopen_ca_checkpoint_v1' || value.contract_version !== 'CLOUD_FIRST_E2E_PAPER_V1' || value.commit_state !== 'COMMITTED') fail('PREOPEN_CA_COMPLETION_COMMIT_INVALID');
  if (value.session_date !== expectedSession || value.stage !== 'PREOPEN_CA' || value.stage_status !== 'PREOPEN_CA_READY') fail('PREOPEN_CA_COMPLETION_IDENTITY_INVALID');
  sha(value.schedule_attestation_sha256, 'PREOPEN_CA_COMPLETION_SCHEDULE_SHA_INVALID');
  if (value.schedule_attestation_sha256 !== expectedScheduleSha256) fail('PREOPEN_CA_COMPLETION_SCHEDULE_SHA_INVALID');
  sha(value.input_manifest_sha256, 'PREOPEN_CA_COMPLETION_INPUT_SHA_INVALID');
  if (value.input_manifest_sha256 !== expectedInputManifestSha256) fail('PREOPEN_CA_COMPLETION_INPUT_SHA_INVALID');

  const identity = object(value.code_identity, 'PREOPEN_CA_COMPLETION_CODE_IDENTITY_INVALID');
  if (identity.repo !== 'samindriano/idx-trade') fail('PREOPEN_CA_COMPLETION_CODE_REPO_INVALID');
  const commit = gitSha(identity.commit, 'PREOPEN_CA_COMPLETION_CODE_SHA_INVALID');
  if (expectedCodeCommit !== undefined && commit !== expectedCodeCommit) fail('PREOPEN_CA_COMPLETION_CODE_SHA_MISMATCH');
  sha(identity.runner_sha256, 'PREOPEN_CA_COMPLETION_RUNNER_SHA_INVALID');
  falseGuardSet(value.guards, PREOPEN_CA_GUARDS, 'PREOPEN_CA_COMPLETION_GUARDS_INVALID');

  const snapshot = object(value.snapshot, 'PREOPEN_CA_COMPLETION_CHILD_REF_INVALID');
  const resultRef = object(value.result, 'PREOPEN_CA_COMPLETION_CHILD_REF_INVALID');
  const snapshotSha = sha(snapshot.sha256, 'PREOPEN_CA_COMPLETION_SNAPSHOT_HASH_INVALID');
  const resultSha = sha(resultRef.sha256, 'PREOPEN_CA_COMPLETION_RESULT_HASH_INVALID');
  const expectedSnapshotKey = `sessions/${expectedSession}/checkpoints/PREOPEN_CA/snapshots/${snapshotSha}.zip`;
  const expectedResultKey = `sessions/${expectedSession}/checkpoints/PREOPEN_CA/results/${resultSha}.json`;
  if (snapshot.key !== expectedSnapshotKey || resultRef.key !== expectedResultKey) fail('PREOPEN_CA_COMPLETION_CHILD_KEY_INVALID');
  const snapshotChild = childHash(childHashes, snapshot, 'PREOPEN_CA_COMPLETION_SNAPSHOT_HASH_INVALID');
  const resultChild = childHash(childHashes, resultRef, 'PREOPEN_CA_COMPLETION_RESULT_HASH_INVALID');
  if (snapshotSha256 !== undefined && snapshotSha256 !== snapshotChild.sha256) fail('PREOPEN_CA_COMPLETION_SNAPSHOT_SHA_INVALID');

  const metadata = object(snapshot.metadata, 'PREOPEN_CA_COMPLETION_SNAPSHOT_METADATA_INVALID');
  if (metadata.schema_version !== 'idx_trade_e2e_paper_cloud_snapshot_v1' || metadata.snapshot_sha256 !== snapshotChild.sha256) fail('PREOPEN_CA_COMPLETION_SNAPSHOT_METADATA_INVALID');
  if (!Array.isArray(metadata.roots) || metadata.roots.some((root) => typeof root !== 'string' || !root) || new Set(metadata.roots).size !== metadata.roots.length) fail('PREOPEN_CA_COMPLETION_SNAPSHOT_METADATA_INVALID');
  if (typeof metadata.file_count !== 'number' || !Number.isInteger(metadata.file_count) || metadata.file_count < 0) fail('PREOPEN_CA_COMPLETION_SNAPSHOT_METADATA_INVALID');

  if (resultBytes !== undefined) {
    const payload = parseJson(resultBytes, 'PREOPEN_CA_COMPLETION_RESULT_JSON_INVALID');
    if (payload.schema_version !== 'idx_trade_e2e_paper_preopen_ca_result_v1' || payload.session_date !== expectedSession || payload.stage !== 'PREOPEN_CA' || payload.controller_status !== 'PREOPEN_CA_READY') fail('PREOPEN_CA_COMPLETION_RESULT_IDENTITY_INVALID');
    falseGuardSet(payload, PREOPEN_CA_GUARDS, 'PREOPEN_CA_COMPLETION_RESULT_GUARDS_INVALID');
  }
  return result({ family: 'PREOPEN_CA', grain: COMPLETION_GRAIN.PREOPEN_CA, key: parent.key, sha256: parent.sha256 });
}

export async function validateExistingCompletion(family, args) {
  switch (family) {
    case 'E2E': return validateE2ECompletion(args);
    case 'PREOPEN_CA': return validatePreopenCaCompletion(args);
    case 'OFFICIAL_OPEN': return validateOfficialOpenCompletion(args);
    case 'INTRADAY': return validateIntradayCompletion(args);
    default: fail('UNKNOWN_COMPLETION_FAMILY');
  }
}
