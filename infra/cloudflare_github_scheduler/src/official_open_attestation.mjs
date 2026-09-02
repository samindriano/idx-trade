export const OFFICIAL_OPEN_ATTESTATION_SCHEMA = 'idx_official_open_external_scheduler_attestation_v1';
export const OFFICIAL_OPEN_REPOSITORY = 'samindriano/idx-trade';

const OFFICIAL_OPEN_SLOT_IDS = new Set([
  'OFFICIAL_OPEN_0902',
  'OFFICIAL_OPEN_0912',
  'OFFICIAL_OPEN_0922',
]);
const NONCE_RE = /^[A-Za-z0-9_-]{16,128}$/;

export function isOfficialOpenSlot(slot) {
  return Boolean(slot && OFFICIAL_OPEN_SLOT_IDS.has(slot.id));
}

export function normalizedUtcIssuedAt(epochMs) {
  if (!Number.isFinite(epochMs)) throw new Error('OFFICIAL_OPEN_ATTESTATION_ISSUED_AT_INVALID');
  const truncatedMs = Math.floor(epochMs / 1000) * 1000;
  const iso = new Date(truncatedMs).toISOString();
  if (!iso.endsWith('.000Z')) throw new Error('OFFICIAL_OPEN_ATTESTATION_ISSUED_AT_INVALID');
  return `${iso.slice(0, -5)}+00:00`;
}

export function canonicalOfficialOpenAttestationBody({ sessionDate, slot, issuedAt, nonce }) {
  if (typeof sessionDate !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) {
    throw new Error('OFFICIAL_OPEN_ATTESTATION_SESSION_INVALID');
  }
  if (!slot || !isOfficialOpenSlot(slot) || !['0902', '0912', '0922'].includes(slot.inputValue)) {
    throw new Error('OFFICIAL_OPEN_ATTESTATION_SLOT_INVALID');
  }
  if (typeof issuedAt !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/.test(issuedAt)) {
    throw new Error('OFFICIAL_OPEN_ATTESTATION_ISSUED_AT_INVALID');
  }
  if (typeof nonce !== 'string' || !NONCE_RE.test(nonce)) {
    throw new Error('OFFICIAL_OPEN_ATTESTATION_NONCE_INVALID');
  }

  // Python producer uses json.dumps(sort_keys=True,separators=(",", ":"),ensure_ascii=True).
  // All values here are ASCII, and insertion order below is alphabetical, matching that exact byte contract.
  return JSON.stringify({
    issued_at_utc: issuedAt,
    nonce,
    repository: OFFICIAL_OPEN_REPOSITORY,
    schema_version: OFFICIAL_OPEN_ATTESTATION_SCHEMA,
    session_date: sessionDate,
    slot: slot.inputValue,
  });
}

function bytesToHex(buffer) {
  return [...new Uint8Array(buffer)].map((value) => value.toString(16).padStart(2, '0')).join('');
}

export async function signOfficialOpenAttestation({ secret, sessionDate, slot, issuedAtEpochMs, nonce }) {
  if (typeof secret !== 'string' || !secret) throw new Error('MISSING_OFFICIAL_OPEN_SCHEDULER_HMAC_KEY');
  const issuedAt = normalizedUtcIssuedAt(issuedAtEpochMs);
  const body = canonicalOfficialOpenAttestationBody({ sessionDate, slot, issuedAt, nonce });
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(body));
  return {
    issuedAt,
    nonce,
    signature: bytesToHex(signature),
    canonicalBody: body,
  };
}

export async function officialOpenAttestedDispatchBody({
  slot,
  ref = 'main',
  secret,
  sessionDate,
  issuedAtEpochMs,
  nonce,
}) {
  if (!isOfficialOpenSlot(slot)) throw new Error('OFFICIAL_OPEN_ATTESTATION_SLOT_INVALID');
  const proof = await signOfficialOpenAttestation({
    secret,
    sessionDate,
    slot,
    issuedAtEpochMs,
    nonce,
  });
  return {
    ref,
    inputs: {
      [slot.inputName]: slot.inputValue,
      session_date: sessionDate,
      scheduler_issued_at: proof.issuedAt,
      scheduler_nonce: proof.nonce,
      scheduler_signature: proof.signature,
    },
  };
}
