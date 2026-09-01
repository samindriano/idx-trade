import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  COMPLETION_GRAIN,
  CompletionContractError,
  captureCompletionProof,
  validateE2ECompletion,
  validateOfficialOpenCompletion,
  validateIntradayCompletion,
  validateExistingCompletion,
} from '../src/completion.mjs';

const digest = (value) => createHash('sha256').update(value).digest('hex');
const sha = (value) => digest(String(value));
const git = (letter) => letter.repeat(40);

test('completion validators expose the explicit completion grain for each family', () => {
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
  const e2e = validateE2ECompletion({
    commit: {
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
    },
    resultBytes,
    snapshotSha256: digest(snapshotBytes),
    expectedSession: '2026-08-27',
    expectedStage: 'POST_EOD',
    childHashes: { 'e2e/result.json': sha('d'), 'e2e/snapshot.zip': digest(snapshotBytes) },
    completionKey: 'sessions/2026-08-27/stages/POST_EOD/commit.json',
    completionSha256: sha('e'),
  });
  assert.deepEqual(e2e, {
    capture_complete: true,
    state: 'capture_complete',
    family: 'E2E',
    grain: COMPLETION_GRAIN.E2E,
    completion_key: 'sessions/2026-08-27/stages/POST_EOD/commit.json',
    completion_sha256: sha('e'),
  });

  const official = validateOfficialOpenCompletion({
    manifest: {
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
    },
    expectedSession: '2026-08-27',
    expectedSlot: '0922',
    childHashes: { 'raw.json': sha('f'), 'open.parquet': sha('g'), 'source.json': sha('h') },
  });
  assert.equal(official.grain, COMPLETION_GRAIN.OFFICIAL_OPEN);

  const intraday = validateIntradayCompletion({
    commit: {
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
    },
    expectedSession: '2026-08-27',
    expectedSlot: '1930',
    claimSha256: sha('m'),
    childHashes: { 'result.json': sha('k'), 'snapshot.zip': sha('l') },
  });
  assert.equal(intraday.grain, COMPLETION_GRAIN.INTRADAY);

  assert.equal(COMPLETION_GRAIN.STREAM, 'observation_slot_universe_source_identity');
});

test('completion validators fail closed on malformed or mismatched evidence', () => {
  assert.throws(
    () => validateE2ECompletion({
      commit: {
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
      },
      expectedSession: '2026-08-27',
      expectedStage: 'POST_EOD',
      childHashes: { 'result.json': sha('x'), 'snapshot.zip': sha('e') },
    }),
    (error) => error instanceof CompletionContractError && error.code === 'E2E_COMPLETION_RESULT_INVALID',
  );

  assert.throws(
    () => validateOfficialOpenCompletion({
      manifest: { schema_version: 'idx_official_open_cloud_archive_v1', commit_state: 'COMMITTED', session_date: '2026-08-27', slot: '0922' },
      expectedSession: '2026-08-27',
      expectedSlot: '0922',
    }),
    (error) => error instanceof CompletionContractError && error.code === 'OFFICIAL_OPEN_COMPLETION_ADMISSION_INVALID',
  );

  assert.throws(
    () => validateIntradayCompletion({
      commit: { schema_version: 'idx_trade_stockbit_intraday_cloud_slot_v1', commit_state: 'COMMITTED', session_date: '2026-08-27', slot: '1930', status: 'WAITING_RECOVERY_RETRY' },
      expectedSession: '2026-08-27',
      expectedSlot: '1930',
    }),
    (error) => error instanceof CompletionContractError && error.code === 'INTRADAY_COMPLETION_IDENTITY_OR_STATUS_INVALID',
  );

  assert.throws(
    () => validateExistingCompletion('STREAM', {}),
    (error) => error instanceof CompletionContractError && error.code === 'UNKNOWN_COMPLETION_FAMILY',
  );
});

test('capture completion proof is explicit and requires an archive identity hash', () => {
  assert.deepEqual(
    captureCompletionProof({
      family: 'INTRADAY',
      sessionDate: '2026-08-27',
      slotId: 'STOCKBIT_INTRADAY_1930',
      completionKey: 'sessions/2026-08-27/slots/1930/commit.json',
      completionSha256: sha('r'),
    }),
    {
      capture_complete: true,
      state: 'capture_complete',
      family: 'INTRADAY',
      grain: 'session_recovery_objective',
      session_date: '2026-08-27',
      slot_id: 'STOCKBIT_INTRADAY_1930',
      completion_key: 'sessions/2026-08-27/slots/1930/commit.json',
      completion_sha256: sha('r'),
    },
  );
  assert.throws(
    () => captureCompletionProof({ family: 'INTRADAY', sessionDate: '2026-08-27', slotId: 'STOCKBIT_INTRADAY_1930', completionKey: 'commit.json', completionSha256: 'bad' }),
    (error) => error instanceof CompletionContractError && error.code === 'CAPTURE_COMPLETION_PROOF_INVALID',
  );
  assert.throws(
    () => captureCompletionProof({ family: 'STREAM', sessionDate: '2026-08-27', slotId: 'STOCKBIT_STREAM_1207', completionKey: 'manifest.json', completionSha256: sha('s') }),
    (error) => error instanceof CompletionContractError && error.code === 'CAPTURE_COMPLETION_PROOF_INVALID',
  );
});
