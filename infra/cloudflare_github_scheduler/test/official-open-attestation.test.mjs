import assert from 'node:assert/strict';
import test from 'node:test';

import { SLOT_BY_ID } from '../src/core.mjs';
import {
  OFFICIAL_OPEN_ATTESTATION_SCHEMA,
  OFFICIAL_OPEN_REPOSITORY,
  canonicalOfficialOpenAttestationBody,
  isOfficialOpenSlot,
  normalizedUtcIssuedAt,
  officialOpenAttestedDispatchBody,
  signOfficialOpenAttestation,
} from '../src/official_open_attestation.mjs';

const slot = SLOT_BY_ID.get('OFFICIAL_OPEN_0902');
const issuedAtEpochMs = Date.parse('2026-09-02T02:05:00Z');
const nonce = 'nonce_1234567890abcd';


test('official open slot classification is exact', () => {
  assert.equal(isOfficialOpenSlot(slot), true);
  assert.equal(isOfficialOpenSlot(SLOT_BY_ID.get('E2E_PREOPEN_0903')), false);
});


test('issued-at normalization matches Python timezone.utc isoformat', () => {
  assert.equal(normalizedUtcIssuedAt(issuedAtEpochMs + 987), '2026-09-02T02:05:00+00:00');
});


test('canonical body exactly matches Python sort_keys contract', () => {
  const issuedAt = normalizedUtcIssuedAt(issuedAtEpochMs);
  assert.equal(
    canonicalOfficialOpenAttestationBody({
      sessionDate: '2026-09-02',
      slot,
      issuedAt,
      nonce,
    }),
    '{"issued_at_utc":"2026-09-02T02:05:00+00:00","nonce":"nonce_1234567890abcd","repository":"samindriano/idx-trade","schema_version":"idx_official_open_external_scheduler_attestation_v1","session_date":"2026-09-02","slot":"0902"}',
  );
});


test('HMAC signature matches independent Python test vector', async () => {
  const proof = await signOfficialOpenAttestation({
    secret: 'test-secret',
    sessionDate: '2026-09-02',
    slot,
    issuedAtEpochMs,
    nonce,
  });
  assert.equal(proof.issuedAt, '2026-09-02T02:05:00+00:00');
  assert.equal(proof.signature, 'fc2284671f4de86a66da538b111d0de2afbc290b7aa36f02071d41aba35efd42');
  assert.equal(OFFICIAL_OPEN_ATTESTATION_SCHEMA, 'idx_official_open_external_scheduler_attestation_v1');
  assert.equal(OFFICIAL_OPEN_REPOSITORY, 'samindriano/idx-trade');
});


test('attested dispatch body is bound to exact session and slot', async () => {
  const body = await officialOpenAttestedDispatchBody({
    slot,
    ref: 'main',
    secret: 'test-secret',
    sessionDate: '2026-09-02',
    issuedAtEpochMs,
    nonce,
  });
  assert.deepEqual(body, {
    ref: 'main',
    inputs: {
      slot: '0902',
      session_date: '2026-09-02',
      scheduler_issued_at: '2026-09-02T02:05:00+00:00',
      scheduler_nonce: nonce,
      scheduler_signature: 'fc2284671f4de86a66da538b111d0de2afbc290b7aa36f02071d41aba35efd42',
    },
  });
});


test('non-official slots and missing secret fail closed', async () => {
  await assert.rejects(
    officialOpenAttestedDispatchBody({
      slot: SLOT_BY_ID.get('E2E_PREOPEN_0903'),
      secret: 'test-secret',
      sessionDate: '2026-09-02',
      issuedAtEpochMs,
      nonce,
    }),
    /OFFICIAL_OPEN_ATTESTATION_SLOT_INVALID/,
  );
  await assert.rejects(
    signOfficialOpenAttestation({
      secret: '',
      sessionDate: '2026-09-02',
      slot,
      issuedAtEpochMs,
      nonce,
    }),
    /MISSING_OFFICIAL_OPEN_SCHEDULER_HMAC_KEY/,
  );
});
