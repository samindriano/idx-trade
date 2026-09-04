import { dispatchBody } from './core.mjs';
import {
  isOfficialOpenSlot,
  officialOpenAttestedDispatchBody,
} from './official_open_attestation.mjs';

function requiredEnv(env, name) {
  const value = env?.[name];
  if (typeof value !== 'string' || !value.trim()) throw new Error(`MISSING_${name}`);
  return value.trim();
}

/**
 * Build every active-mode dispatch input before entering the GitHub POST
 * boundary.  Observe-only mode must not call this function: it has no write
 * token or Official Open signing key by contract.
 */
export async function prepareActiveDispatch({
  env,
  slot,
  ref,
  sessionDate,
  issuedAtEpochMs,
  nonceFactory = () => crypto.randomUUID(),
  attestBody = officialOpenAttestedDispatchBody,
}) {
  const token = requiredEnv(env, 'GITHUB_ACTIONS_WRITE_TOKEN');
  const unsignedBody = dispatchBody(slot, ref);
  let body = unsignedBody;
  if (isOfficialOpenSlot(slot)) {
    const secret = requiredEnv(env, 'OFFICIAL_OPEN_SCHEDULER_HMAC_KEY');
    body = await attestBody({
      slot,
      ref,
      secret,
      sessionDate,
      issuedAtEpochMs,
      nonce: nonceFactory(),
    });
  }
  return {
    token,
    body,
    inputs: unsignedBody.inputs,
    officialOpenAttestationRequired: isOfficialOpenSlot(slot),
  };
}
