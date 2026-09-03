import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { SLOT_BY_ID, localTimeEpochMs } from '../src/core.mjs';
import { dispatchWithMode } from '../src/dispatch_mode.mjs';
import {
  ARCHIVE_BUCKET_NAME,
  ARCHIVE_PREFIX,
  evaluateShadowSlot,
  readDurableCompletion,
} from '../src/archive.mjs';

const session = '2026-08-27';
const git = (letter) => letter.repeat(40);
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const bytes = (value) => Buffer.from(JSON.stringify(value));
const canonicalJson = (value) => Array.isArray(value)
  ? `[${value.map(canonicalJson).join(',')}]`
  : value && typeof value === 'object'
    ? `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`
    : JSON.stringify(value) ?? 'undefined';
const canonicalBytes = (value) => Buffer.from(`${canonicalJson(value)}\n`);
const prefixed = (family, key) => `${ARCHIVE_PREFIX[family]}/${key}`;
const put = (objects, family, key, value) => {
  const raw = Buffer.isBuffer(value) ? value : bytes(value);
  objects[prefixed(family, key)] = raw;
  return raw;
};

class ReadOnlyArchive {
  constructor(objects) {
    this.objects = objects;
    this.reads = [];
  }

  async get(key) {
    this.reads.push(key);
    const value = this.objects[key];
    if (!value) return null;
    return {
      arrayBuffer: async () => value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength),
    };
  }

  put() { throw new Error('ARCHIVE_WRITE_FORBIDDEN'); }
  delete() { throw new Error('ARCHIVE_DELETE_FORBIDDEN'); }
  list() { throw new Error('ARCHIVE_LIST_FORBIDDEN'); }
}

function e2eFixture(objects, stage = 'POST_EOD') {
  const result = {
    schema_version: 'idx_trade_e2e_paper_cloud_runtime_v1',
    session_date: session,
    stage,
    stage_status: stage === 'POST_EOD' ? 'POST_EOD_PREPARED' : 'EXECUTION_COMPLETE',
    observed_availability_only: true,
    outcome_accessed: false,
    protected_forward_accessed: false,
    model_refit: false,
  };
  const resultBytes = bytes(result);
  const snapshotBytes = Buffer.from('e2e-snapshot');
  const parent = {
    schema_version: 'idx_trade_e2e_paper_cloud_stage_commit_v1',
    commit_state: 'COMMITTED',
    contract_version: 'CLOUD_FIRST_E2E_PAPER_V1',
    session_date: session,
    stage,
    stage_status: result.stage_status,
    schedule_attestation_sha256: hash(Buffer.from('schedule')),
    input_manifest_sha256: hash(Buffer.from('input')),
    code_identity: { commit: git('c') },
    guards: {
      outcome_accessed: false,
      protected_forward_accessed: false,
      model_refit: false,
      retroactive_execution_authorized: false,
    },
    result: { key: `sessions/${session}/stages/${stage}/runs/1/result.json`, sha256: hash(resultBytes) },
    snapshot: { key: `sessions/${session}/stages/${stage}/snapshots/${hash(snapshotBytes)}.zip`, sha256: hash(snapshotBytes) },
  };
  put(objects, 'E2E', `sessions/${session}/stages/${stage}/commit.json`, parent);
  put(objects, 'E2E', parent.result.key, resultBytes);
  put(objects, 'E2E', parent.snapshot.key, snapshotBytes);
  return parent;
}

function officialFixture(objects, slot = '0922') {
  const raw = Buffer.from('official-raw');
  const prices = Buffer.from('official-prices');
  const source = Buffer.from('official-source');
  const parent = {
    schema_version: 'idx_official_open_cloud_archive_v1',
    commit_state: 'COMMITTED',
    session_date: session,
    slot,
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
      raw_response: { key: `session_date=${session}/slot=${slot}/captures/1/raw.json`, sha256: hash(raw) },
      open_prices: { key: `session_date=${session}/slot=${slot}/captures/1/open.parquet`, sha256: hash(prices) },
      source_manifest: { key: `session_date=${session}/slot=${slot}/captures/1/source.json`, sha256: hash(source) },
    },
  };
  put(objects, 'OFFICIAL_OPEN', `session_date=${session}/slot=${slot}/slot_manifest.json`, parent);
  put(objects, 'OFFICIAL_OPEN', parent.artifacts.raw_response.key, raw);
  put(objects, 'OFFICIAL_OPEN', parent.artifacts.open_prices.key, prices);
  put(objects, 'OFFICIAL_OPEN', parent.artifacts.source_manifest.key, source);
  return parent;
}

function intradayFixture(objects, slot = '1830', status = 'ADMISSIBLE_COMPLETE') {
  const claim = {
    schema_version: 'idx_trade_stockbit_intraday_cloud_claim_v1',
    claim_state: 'CLAIMED',
    session_date: session,
    slot,
    claim_id: `claim-${slot}`,
    code_identity: { commit: git('d') },
    guards: { synthetic_fill_used: false, retroactive_capture_used: false, outcome_accessed: false },
  };
  const claimBytes = bytes(claim);
  const result = {
    session_date: session,
    slot,
    status,
    synthetic_fill_used: false,
    retroactive_capture_used: false,
    outcome_accessed: false,
  };
  const resultBytes = bytes(result);
  const snapshotBytes = Buffer.from(`intraday-${slot}`);
  const parent = {
    schema_version: 'idx_trade_stockbit_intraday_cloud_slot_v1',
    commit_state: 'COMMITTED',
    session_date: session,
    slot,
    status,
    eod_manifest_sha256: hash(Buffer.from('eod')),
    session_manifest_sha256: hash(Buffer.from('session')),
    code_identity: claim.code_identity,
    claim_sha256: hash(claimBytes),
    guards: { synthetic_fill_used: false, retroactive_capture_used: false, outcome_accessed: false },
    result: { key: `sessions/${session}/slots/${slot}/results/${hash(resultBytes)}.json`, sha256: hash(resultBytes) },
    snapshot: { key: `sessions/${session}/slots/${slot}/snapshots/${hash(snapshotBytes)}.zip`, sha256: hash(snapshotBytes) },
  };
  put(objects, 'INTRADAY', `sessions/${session}/slots/${slot}/commit.json`, parent);
  put(objects, 'INTRADAY', `sessions/${session}/slots/${slot}/claim.json`, claimBytes);
  put(objects, 'INTRADAY', parent.result.key, resultBytes);
  put(objects, 'INTRADAY', parent.snapshot.key, snapshotBytes);
  return parent;
}

function preopenFixture(objects) {
  const schedule = Buffer.from('canonical-schedule');
  const manifestFiles = [
    ['execution_schedule', 'schedule.json', schedule],
    ['execution_schedule_source', 'official-source.pdf', Buffer.from('source')],
    ['clean_panel', 'panel.parquet', Buffer.from('panel')],
    ['clean_security_master', 'security_master.csv', Buffer.from('security')],
    ['model_manifest', 'model/MANIFEST.json', Buffer.from('manifest')],
    ['model_control_h5', 'model/control_h5.joblib', Buffer.from('control-h5')],
    ['model_control_h10', 'model/control_h10.joblib', Buffer.from('control-h10')],
    ['model_challenger_h5', 'model/challenger_h5.joblib', Buffer.from('challenger-h5')],
    ['model_challenger_h10', 'model/challenger_h10.joblib', Buffer.from('challenger-h10')],
    ['model_fit_log', 'model/fit_log.json', Buffer.from('fit-log')],
  ];
  const files = manifestFiles.map(([role, relativePath, payload]) => ({
    role,
    key: `inputs/${relativePath}`,
    relative_path: relativePath,
    sha256: hash(payload),
    content_type: 'application/octet-stream',
  }));
  const manifest = {
    schema_version: 'idx_trade_e2e_paper_cloud_inputs_v1',
    contract_version: 'CLOUD_FIRST_E2E_PAPER_V1',
    execution_schedule_sha256: hash(schedule),
    files,
    roles: Object.fromEntries(files.map((ref) => [ref.role, ref.relative_path])),
  };
  const manifestWithPayloadSha = {
    ...manifest,
    manifest_payload_sha256: hash(canonicalBytes(manifest)),
  };
  const manifestBytes = canonicalBytes(manifestWithPayloadSha);
  const snapshotBytes = Buffer.from('preopen-snapshot');
  const result = {
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
  };
  const resultBytes = bytes(result);
  const parent = {
    schema_version: 'idx_trade_e2e_paper_preopen_ca_checkpoint_v1',
    contract_version: 'CLOUD_FIRST_E2E_PAPER_V1',
    commit_state: 'COMMITTED',
    session_date: session,
    stage: 'PREOPEN_CA',
    stage_status: 'PREOPEN_CA_READY',
    schedule_attestation_sha256: hash(schedule),
    input_manifest_sha256: hash(manifestBytes),
    code_identity: { repo: 'samindriano/idx-trade', commit: git('e'), runner_sha256: hash(Buffer.from('runner')) },
    snapshot: {
      key: `sessions/${session}/checkpoints/PREOPEN_CA/snapshots/${hash(snapshotBytes)}.zip`,
      sha256: hash(snapshotBytes),
      metadata: { schema_version: 'idx_trade_e2e_paper_cloud_snapshot_v1', roots: ['paper'], file_count: 1, snapshot_sha256: hash(snapshotBytes) },
    },
    result: { key: `sessions/${session}/checkpoints/PREOPEN_CA/results/${hash(resultBytes)}.json`, sha256: hash(resultBytes) },
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
  put(objects, 'E2E', 'inputs/manifest.json', manifestBytes);
  for (const [, relativePath, payload] of manifestFiles) put(objects, 'E2E', `inputs/${relativePath}`, payload);
  put(objects, 'PREOPEN_CA', `sessions/${session}/checkpoints/PREOPEN_CA/commit.json`, parent);
  put(objects, 'PREOPEN_CA', parent.snapshot.key, snapshotBytes);
  put(objects, 'PREOPEN_CA', parent.result.key, resultBytes);
  return parent;
}

test('shadow reads each canonical family through R2 and validates durable completion', async () => {
  const objects = {};
  e2eFixture(objects);
  officialFixture(objects);
  intradayFixture(objects);
  preopenFixture(objects);
  const archive = new ReadOnlyArchive(objects);

  const e2e = await readDurableCompletion({ archive, slot: SLOT_BY_ID.get('E2E_POST_EOD_1835'), session });
  assert.equal(e2e.status, 'DURABLE_COMPLETION_VERIFIED');
  assert.equal(e2e.completion_key, `sessions/${session}/stages/POST_EOD/commit.json`);
  assert.equal(e2e.completion_sha256.length, 64);

  const official = await readDurableCompletion({ archive, slot: SLOT_BY_ID.get('OFFICIAL_OPEN_0922'), session });
  assert.equal(official.status, 'DURABLE_COMPLETION_VERIFIED');

  const intraday = await readDurableCompletion({ archive, slot: SLOT_BY_ID.get('STOCKBIT_INTRADAY_1930'), session });
  assert.equal(intraday.status, 'DURABLE_COMPLETION_VERIFIED');
  assert.equal(intraday.completion_slot, '1830');

  const preopen = await readDurableCompletion({ archive, slot: SLOT_BY_ID.get('E2E_PREOPEN_CA_0855'), session, expectedCodeCommit: git('e') });
  assert.equal(preopen.status, 'DURABLE_COMPLETION_VERIFIED');
  assert.equal(preopen.family, 'PREOPEN_CA');
  assert.equal(ARCHIVE_BUCKET_NAME, 'idx-trade-stockbit-stream-v1');
});

test('shadow fails closed for missing child, malformed parent, and invalid PREOPEN_CA expectations', async () => {
  const missingChild = {};
  const parent = e2eFixture(missingChild);
  delete missingChild[prefixed('E2E', parent.snapshot.key)];
  const missing = await readDurableCompletion({ archive: new ReadOnlyArchive(missingChild), slot: SLOT_BY_ID.get('E2E_POST_EOD_1835'), session });
  assert.equal(missing.state, 'archive_completion_blocked');

  const malformed = { [prefixed('E2E', `sessions/${session}/stages/POST_EOD/commit.json`)]: Buffer.from('{') };
  const result = await readDurableCompletion({ archive: new ReadOnlyArchive(malformed), slot: SLOT_BY_ID.get('E2E_POST_EOD_1835'), session });
  assert.equal(result.state, 'archive_completion_blocked');

  const preopen = {};
  preopenFixture(preopen);
  delete preopen[prefixed('E2E', 'inputs/manifest.json')];
  const blockedPreopen = await readDurableCompletion({ archive: new ReadOnlyArchive(preopen), slot: SLOT_BY_ID.get('E2E_PREOPEN_CA_0830'), session, expectedCodeCommit: git('e') });
  assert.equal(blockedPreopen.state, 'archive_completion_blocked');
});

test('Intraday session recovery uses a prior valid completion but does not hide a later slot behind WAITING', async () => {
  const completedEarlier = {};
  intradayFixture(completedEarlier, '1830');
  const earlier = await readDurableCompletion({ archive: new ReadOnlyArchive(completedEarlier), slot: SLOT_BY_ID.get('STOCKBIT_INTRADAY_2030'), session });
  assert.equal(earlier.status, 'DURABLE_COMPLETION_VERIFIED');
  assert.equal(earlier.completion_slot, '1830');

  const waitingThenComplete = {};
  intradayFixture(waitingThenComplete, '1830', 'WAITING_RECOVERY_RETRY');
  intradayFixture(waitingThenComplete, '1930');
  const later = await readDurableCompletion({ archive: new ReadOnlyArchive(waitingThenComplete), slot: SLOT_BY_ID.get('STOCKBIT_INTRADAY_2030'), session });
  assert.equal(later.status, 'DURABLE_COMPLETION_VERIFIED');
  assert.equal(later.completion_slot, '1930');
});

test('valid WAITING_CANONICAL_EOD_GATE remains recoverable for later Intraday slots', async () => {
  for (const targetSlot of ['1930', '2030']) {
    const objects = {};
    intradayFixture(objects, '1830', 'WAITING_CANONICAL_EOD_GATE');
    const result = await readDurableCompletion({
      archive: new ReadOnlyArchive(objects),
      slot: SLOT_BY_ID.get(`STOCKBIT_INTRADAY_${targetSlot}`),
      session,
    });
    assert.equal(result.capture_complete, false);
    assert.equal(result.state, 'not_complete');
    assert.equal(result.reason, 'ARCHIVE_PARENT_MISSING_OR_NOT_COMPLETE');
  }
});

test('valid WAITING_RECOVERY_RETRY remains recoverable without becoming completion', async () => {
  const objects = {};
  intradayFixture(objects, '1830', 'WAITING_RECOVERY_RETRY');
  const result = await readDurableCompletion({
    archive: new ReadOnlyArchive(objects),
    slot: SLOT_BY_ID.get('STOCKBIT_INTRADAY_1930'),
    session,
  });
  assert.equal(result.capture_complete, false);
  assert.equal(result.state, 'not_complete');
});

test('tampered or identity-mismatched waiting Intraday commits fail closed', async () => {
  const missingChild = {};
  const missingParent = intradayFixture(missingChild, '1830', 'WAITING_CANONICAL_EOD_GATE');
  delete missingChild[prefixed('INTRADAY', missingParent.snapshot.key)];
  const missing = await readDurableCompletion({
    archive: new ReadOnlyArchive(missingChild),
    slot: SLOT_BY_ID.get('STOCKBIT_INTRADAY_1930'),
    session,
  });
  assert.equal(missing.state, 'archive_completion_blocked');

  const claimTampered = {};
  const claimParent = intradayFixture(claimTampered, '1830', 'WAITING_RECOVERY_RETRY');
  const claimKey = prefixed('INTRADAY', `sessions/${session}/slots/1830/claim.json`);
  claimTampered[claimKey] = bytes({
    schema_version: 'idx_trade_stockbit_intraday_cloud_claim_v1',
    claim_state: 'CLAIMED',
    session_date: session,
    slot: '1830',
    claim_id: 'tampered',
    code_identity: claimParent.code_identity,
    guards: { synthetic_fill_used: false, retroactive_capture_used: false, outcome_accessed: false },
  });
  const claimMismatch = await readDurableCompletion({
    archive: new ReadOnlyArchive(claimTampered),
    slot: SLOT_BY_ID.get('STOCKBIT_INTRADAY_1930'),
    session,
  });
  assert.equal(claimMismatch.state, 'archive_completion_blocked');

  const identityTampered = {};
  const identityParent = intradayFixture(identityTampered, '1830', 'WAITING_CANONICAL_EOD_GATE');
  identityTampered[prefixed('INTRADAY', `sessions/${session}/slots/1830/commit.json`)] = bytes({
    ...identityParent,
    session_date: '2026-08-28',
  });
  const identityMismatch = await readDurableCompletion({
    archive: new ReadOnlyArchive(identityTampered),
    slot: SLOT_BY_ID.get('STOCKBIT_INTRADAY_1930'),
    session,
  });
  assert.equal(identityMismatch.state, 'archive_completion_blocked');
});

test('Stream remains excluded and does not even read the archive', async () => {
  const archive = new ReadOnlyArchive({});
  const result = await readDurableCompletion({
    archive,
    slot: { workflow: 'stockbit-stream-prospective-capture.yml', inputName: 'slot', inputValue: '1207', id: 'STOCKBIT_STREAM_1207' },
    session,
  });
  assert.equal(result.state, 'archive_completion_blocked');
  assert.deepEqual(archive.reads, []);
});

test('shadow output separates durable completion from exact GitHub provenance and active decision', async () => {
  const archive = new ReadOnlyArchive({});
  const observed = localTimeEpochMs(session, '18:40');
  const output = await evaluateShadowSlot({
    archive,
    slot: SLOT_BY_ID.get('E2E_POST_EOD_1835'),
    session,
    observedEpochMs: observed,
    exactRuns: [{
      id: 99,
      event: 'workflow_dispatch',
      head_branch: 'main',
      created_at: new Date(localTimeEpochMs(session, '18:36')).toISOString(),
      updated_at: new Date(localTimeEpochMs(session, '18:36')).toISOString(),
      display_title: 'IDX-SLOT:E2E_POST_EOD_1835',
      status: 'completed',
      conclusion: 'failure',
    }],
  });
  assert.equal(output.durable_completion.capture_complete, false);
  assert.equal(output.github_exact_run_evidence.runs.length, 1);
  assert.equal(output.github_exact_run_evidence.runs[0].conclusion, 'failure');
  assert.equal(output.active_mode_decision, 'WORKFLOW_DISPATCH_WOULD_BE_ELIGIBLE');
  assert.equal(output.archive_github_decision, 'WORKFLOW_DISPATCH_WOULD_BE_ELIGIBLE');
  assert.equal(output.effective_active_mode_decision, 'WORKFLOW_DISPATCH_WOULD_BE_ELIGIBLE');
  assert.equal(output.native_watchdog_agreement.workflow_dispatch.agrees_with_durable, false);
});

test('observe-only shadow cannot dispatch or mutate archive state', async () => {
  const archive = new ReadOnlyArchive({});
  const output = await evaluateShadowSlot({
    archive,
    slot: SLOT_BY_ID.get('E2E_POST_EOD_1835'),
    session,
    observedEpochMs: localTimeEpochMs(session, '18:40'),
  });
  let dispatched = false;
  const dispatch = await dispatchWithMode({
    mode: 'observe_only',
    dispatchFn: async () => { dispatched = true; throw new Error('DISPATCH_FORBIDDEN'); },
  });
  assert.equal(output.active_mode_decision, 'WORKFLOW_DISPATCH_WOULD_BE_ELIGIBLE');
  assert.equal(output.effective_active_mode_decision, 'WORKFLOW_DISPATCH_WOULD_BE_ELIGIBLE');
  assert.equal(dispatch.status, 'WOULD_DISPATCH');
  assert.equal(dispatched, false);
  assert.ok(archive.reads.length > 0);
});
