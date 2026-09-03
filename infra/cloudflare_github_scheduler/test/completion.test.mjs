import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  COMPLETION_GRAIN,
  CompletionContractError,
  validateE2ECompletion,
  validateOfficialOpenCompletion,
  validatePreopenCaCompletion,
  validateIntradayCompletion,
  validateExistingCompletion,
} from '../src/completion.mjs';

const digest = (value) => createHash('sha256').update(value).digest('hex');
const sha = (value) => digest(String(value));
const git = (letter) => letter.repeat(40);
const parentIdentity = (key, value) => {
  const bytes = Buffer.from(JSON.stringify(value));
  return { completionKey: key, completionBytes: bytes, completionSha256: digest(bytes) };
};

test('completion validators expose the explicit completion grain for each family', async () => {
  const resultBytes = Buffer.from(JSON.stringify({
    schema_version: 'idx_trade_e2e_paper_cloud_runtime_v1',
    session_date: '2026-08-27',
    stage: 'POST_EOD',
    stage_status: 'POST_EOD_PREPARED',
    observed_availability_only: true,
    outcome_accessed: false,
    protected_forward_accessed: false,
    model_refit: false,
  }));
  const snapshotBytes = Buffer.from('e2e-snapshot');
  const e2eCommit = {
      schema_version: 'idx_trade_e2e_paper_cloud_stage_commit_v1',
      commit_state: 'COMMITTED',
      contract_version: 'CLOUD_FIRST_E2E_PAPER_V1',
      session_date: '2026-08-27',
      stage: 'POST_EOD',
      stage_status: 'POST_EOD_PREPARED',
      schedule_attestation_sha256: sha('a'),
      input_manifest_sha256: sha('b'),
      code_identity: { commit: git('c') },
      guards: {
        outcome_accessed: false,
        protected_forward_accessed: false,
        model_refit: false,
        retroactive_execution_authorized: false,
      },
      result: { key: 'e2e/result.json', sha256: sha('d') },
      snapshot: { key: 'e2e/snapshot.zip', sha256: digest(snapshotBytes) },
  };
  const e2eParent = parentIdentity('sessions/2026-08-27/stages/POST_EOD/commit.json', e2eCommit);
  const e2e = await validateE2ECompletion({
    commit: e2eCommit,
    resultBytes,
    snapshotSha256: digest(snapshotBytes),
    expectedSession: '2026-08-27',
    expectedStage: 'POST_EOD',
    childHashes: { 'e2e/result.json': sha('d'), 'e2e/snapshot.zip': digest(snapshotBytes) },
    ...e2eParent,
  });
  assert.deepEqual(e2e, {
    capture_complete: true,
    state: 'capture_complete',
    family: 'E2E',
    grain: COMPLETION_GRAIN.E2E,
    completion_key: 'sessions/2026-08-27/stages/POST_EOD/commit.json',
    completion_sha256: e2eParent.completionSha256,
  });

  const officialManifest = {
      schema_version: 'idx_official_open_cloud_archive_v1',
      commit_state: 'COMMITTED',
      session_date: '2026-08-27',
      slot: '0922',
      execution_admission: 'CAPTURE_ONLY_NOT_EXECUTION_ADMITTED',
      authority: 'IDX',
      field_semantics: 'IDX_OFFICIAL_OPENPRICE',
      source_execution_grade: true,
      guards: {
        model_accessed: false,
        outcome_accessed: false,
        paper_state_mutated: false,
        forward_counter_mutated: false,
        order_created: false,
        fill_created: false,
        retroactive_execution_authorized: false,
      },
      artifacts: {
        raw_response: { key: 'raw.json', sha256: sha('f') },
        open_prices: { key: 'open.parquet', sha256: sha('g') },
        source_manifest: { key: 'source.json', sha256: sha('h') },
      },
  };
  const official = await validateOfficialOpenCompletion({
    manifest: officialManifest,
    expectedSession: '2026-08-27',
    expectedSlot: '0922',
    childHashes: { 'raw.json': sha('f'), 'open.parquet': sha('g'), 'source.json': sha('h') },
    ...parentIdentity('session_date=2026-08-27/slot=0922/slot_manifest.json', officialManifest),
  });
  assert.equal(official.grain, COMPLETION_GRAIN.OFFICIAL_OPEN);

  const intradayCommit = {
      schema_version: 'idx_trade_stockbit_intraday_cloud_slot_v1',
      commit_state: 'COMMITTED',
      session_date: '2026-08-27',
      slot: '1930',
      status: 'ADMISSIBLE_COMPLETE',
      guards: { synthetic_fill_used: false, retroactive_capture_used: false, outcome_accessed: false },
      eod_manifest_sha256: sha('i'),
      session_manifest_sha256: sha('j'),
      result: { key: 'result.json', sha256: sha('k') },
      snapshot: { key: 'snapshot.zip', sha256: sha('l') },
      claim_sha256: sha('m'),
  };
  const intraday = await validateIntradayCompletion({
    commit: intradayCommit,
    expectedSession: '2026-08-27',
    expectedSlot: '1930',
    claimSha256: sha('m'),
    childHashes: { 'result.json': sha('k'), 'snapshot.zip': sha('l') },
    ...parentIdentity('sessions/2026-08-27/slots/1930/commit.json', intradayCommit),
  });
  assert.equal(intraday.grain, COMPLETION_GRAIN.INTRADAY);

  assert.equal(COMPLETION_GRAIN.STREAM, 'observation_slot_universe_source_identity');
  assert.equal(COMPLETION_GRAIN.PREOPEN_CA, 'session_preopen_ca_checkpoint');
});

test('completion validators fail closed on malformed or mismatched evidence', async () => {
  const e2eCommit = {
    schema_version: 'idx_trade_e2e_paper_cloud_stage_commit_v1',
    commit_state: 'COMMITTED',
    contract_version: 'CLOUD_FIRST_E2E_PAPER_V1',
    session_date: '2026-08-27',
    stage: 'POST_EOD',
    stage_status: 'POST_EOD_PREPARED',
    schedule_attestation_sha256: sha('a'),
    input_manifest_sha256: sha('b'),
    code_identity: { commit: git('c') },
    guards: { outcome_accessed: false, protected_forward_accessed: false, model_refit: false, retroactive_execution_authorized: false },
    result: { key: 'result.json', sha256: sha('d') },
    snapshot: { key: 'snapshot.zip', sha256: sha('e') },
  };
  await assert.rejects(
    validateE2ECompletion({
      commit: e2eCommit,
      expectedSession: '2026-08-27',
      expectedStage: 'POST_EOD',
      childHashes: { 'result.json': sha('x'), 'snapshot.zip': sha('e') },
      ...parentIdentity('sessions/2026-08-27/stages/POST_EOD/commit.json', e2eCommit),
    }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_RESULT_INVALID',
  );

  await assert.rejects(
    validateOfficialOpenCompletion({
      manifest: { schema_version: 'idx_official_open_cloud_archive_v1', commit_state: 'COMMITTED', session_date: '2026-08-27', slot: '0922' },
      expectedSession: '2026-08-27',
      expectedSlot: '0922',
      ...parentIdentity(
        'session_date=2026-08-27/slot=0922/slot_manifest.json',
        { schema_version: 'idx_official_open_cloud_archive_v1', commit_state: 'COMMITTED', session_date: '2026-08-27', slot: '0922' },
      ),
    }),
    (error) => error instanceof CompletionContractError && error.code === 'OFFICIAL_OPEN_COMPLETION_ADMISSION_INVALID',
  );

  await assert.rejects(
    validateIntradayCompletion({
      commit: { schema_version: 'idx_trade_stockbit_intraday_cloud_slot_v1', commit_state: 'COMMITTED', session_date: '2026-08-27', slot: '1930', status: 'WAITING_RECOVERY_RETRY' },
      expectedSession: '2026-08-27',
      expectedSlot: '1930',
      ...parentIdentity(
        'sessions/2026-08-27/slots/1930/commit.json',
        { schema_version: 'idx_trade_stockbit_intraday_cloud_slot_v1', commit_state: 'COMMITTED', session_date: '2026-08-27', slot: '1930', status: 'WAITING_RECOVERY_RETRY' },
      ),
    }),
    (error) => error instanceof CompletionContractError && error.code === 'INTRADAY_COMPLETION_IDENTITY_OR_STATUS_INVALID',
  );

  await assert.rejects(
    validateExistingCompletion('STREAM', {}),
    (error) => error instanceof CompletionContractError && error.code === 'UNKNOWN_COMPLETION_FAMILY',
  );
});

test('PREOPEN_CA completion validates the canonical content-addressed checkpoint', async () => {
  const session = '2026-08-27';
  const snapshot = Buffer.from('preopen-ca-snapshot');
  const resultBytes = Buffer.from(JSON.stringify({
    schema_version: 'idx_trade_e2e_paper_preopen_ca_result_v1',
    session_date: session,
    stage: 'PREOPEN_CA',
    controller_status: 'PREOPEN_CA_READY',
    outcome_accessed: false,
    protected_forward_accessed: false,
    model_refit: false,
    paper_state_mutated: false,
    order_created: false,
    fill_created: false,
    retroactive_execution_authorized: false,
  }));
  const checkpoint = {
    schema_version: 'idx_trade_e2e_paper_preopen_ca_checkpoint_v1',
    contract_version: 'CLOUD_FIRST_E2E_PAPER_V1',
    commit_state: 'COMMITTED',
    session_date: session,
    stage: 'PREOPEN_CA',
    stage_status: 'PREOPEN_CA_READY',
    schedule_attestation_sha256: sha('schedule'),
    input_manifest_sha256: sha('input'),
    code_identity: { repo: 'samindriano/idx-trade', commit: git('c'), runner_sha256: sha('runner') },
    snapshot: {
      key: `sessions/${session}/checkpoints/PREOPEN_CA/snapshots/${digest(snapshot)}.zip`,
      sha256: digest(snapshot),
      metadata: { schema_version: 'idx_trade_e2e_paper_cloud_snapshot_v1', roots: ['paper'], file_count: 1, snapshot_sha256: digest(snapshot) },
    },
    result: { key: `sessions/${session}/checkpoints/PREOPEN_CA/results/${digest(resultBytes)}.json`, sha256: digest(resultBytes) },
    guards: {
      outcome_accessed: false,
      protected_forward_accessed: false,
      model_refit: false,
      paper_state_mutated: false,
      order_created: false,
      fill_created: false,
      retroactive_execution_authorized: false,
    },
  };
  const preopenParent = parentIdentity(`sessions/${session}/checkpoints/PREOPEN_CA/commit.json`, checkpoint);
  const result = await validatePreopenCaCompletion({
    checkpoint,
    resultBytes,
    snapshotSha256: digest(snapshot),
    expectedSession: session,
    expectedScheduleSha256: sha('schedule'),
    expectedInputManifestSha256: sha('input'),
    expectedCodeCommit: git('c'),
    childHashes: {
      [checkpoint.snapshot.key]: digest(snapshot),
      [checkpoint.result.key]: digest(resultBytes),
    },
    ...preopenParent,
  });
  assert.deepEqual(result, {
    capture_complete: true,
    state: 'capture_complete',
    family: 'PREOPEN_CA',
    grain: 'session_preopen_ca_checkpoint',
    completion_key: preopenParent.completionKey,
    completion_sha256: preopenParent.completionSha256,
  });

  const wrongStage = { ...checkpoint, stage: 'POST_EOD' };
  await assert.rejects(
    validatePreopenCaCompletion({
      checkpoint: wrongStage,
      expectedSession: session,
      expectedScheduleSha256: sha('schedule'),
      expectedInputManifestSha256: sha('input'),
      expectedCodeCommit: git('c'),
      childHashes: {},
      ...parentIdentity(`sessions/${session}/checkpoints/PREOPEN_CA/commit.json`, wrongStage),
    }),
    (error) => error instanceof CompletionContractError && error.code === 'PREOPEN_CA_COMPLETION_IDENTITY_INVALID',
  );
});

function e2eCompletionEvidence() {
  const resultBytes = Buffer.from(JSON.stringify({
    schema_version: 'idx_trade_e2e_paper_cloud_runtime_v1',
    session_date: '2026-08-27',
    stage: 'POST_EOD',
    stage_status: 'POST_EOD_PREPARED',
    observed_availability_only: true,
    outcome_accessed: false,
    protected_forward_accessed: false,
    model_refit: false,
  }));
  const snapshotBytes = Buffer.from('parent-identity-snapshot');
  const commit = {
    schema_version: 'idx_trade_e2e_paper_cloud_stage_commit_v1',
    commit_state: 'COMMITTED',
    contract_version: 'CLOUD_FIRST_E2E_PAPER_V1',
    session_date: '2026-08-27',
    stage: 'POST_EOD',
    stage_status: 'POST_EOD_PREPARED',
    schedule_attestation_sha256: sha('schedule'),
    input_manifest_sha256: sha('input'),
    code_identity: { commit: git('d') },
    guards: {
      outcome_accessed: false,
      protected_forward_accessed: false,
      model_refit: false,
      retroactive_execution_authorized: false,
    },
    result: { key: 'result.json', sha256: digest(resultBytes) },
    snapshot: { key: 'snapshot.zip', sha256: digest(snapshotBytes) },
  };
  return {
    commit,
    resultBytes,
    snapshotSha256: digest(snapshotBytes),
    expectedSession: '2026-08-27',
    expectedStage: 'POST_EOD',
    childHashes: { 'result.json': digest(resultBytes), 'snapshot.zip': digest(snapshotBytes) },
    ...parentIdentity('sessions/2026-08-27/stages/POST_EOD/commit.json', commit),
  };
}

test('completion identity is required and hash-bound before capture_complete', async () => {
  const base = e2eCompletionEvidence();
  await assert.rejects(
    validateE2ECompletion({ ...base, completionKey: undefined }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_PARENT_KEY_INVALID',
  );
  await assert.rejects(
    validateE2ECompletion({ ...base, completionSha256: undefined }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_PARENT_SHA_INVALID',
  );
  await assert.rejects(
    validateE2ECompletion({ ...base, completionKey: 'sessions/2026-08-27/stages/POST_EOD/../commit.json' }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_PARENT_KEY_INVALID',
  );
  await assert.rejects(
    validateE2ECompletion({ ...base, completionKey: 'sessions/2026-08-27/stages/PREOPEN/commit.json' }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_PARENT_KEY_INVALID',
  );
  await assert.rejects(
    validateE2ECompletion({ ...base, completionSha256: '0'.repeat(64) }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_PARENT_SHA_MISMATCH',
  );
});

test('completion semantic validation is bound to the hashed parent bytes', async () => {
  const base = e2eCompletionEvidence();
  const differentParent = { ...base.commit, stage_status: 'NOT_COMPLETE' };

  await assert.rejects(
    validateE2ECompletion({ ...base, commit: differentParent }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_PARENT_SEMANTIC_MISMATCH',
  );

  const changedStatusParent = { ...base.commit, stage_status: 'NOT_COMPLETE' };
  const changedStatusIdentity = parentIdentity(base.completionKey, changedStatusParent);
  const { commit: _ignoredCommit, ...withoutExternalParent } = base;
  await assert.rejects(
    validateE2ECompletion({ ...withoutExternalParent, ...changedStatusIdentity }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_STATUS_INVALID',
  );
  await assert.rejects(
    validateE2ECompletion({ ...base, ...changedStatusIdentity, commit: base.commit }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_PARENT_SEMANTIC_MISMATCH',
  );

  const malformedBytes = Buffer.from('{malformed');
  await assert.rejects(
    validateE2ECompletion({
      ...base,
      completionBytes: malformedBytes,
      completionSha256: digest(malformedBytes),
      commit: base.commit,
    }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_PARENT_JSON_INVALID',
  );

  const valid = await validateE2ECompletion(base);
  assert.equal(valid.capture_complete, true);
  assert.equal(valid.completion_sha256, base.completionSha256);
});
