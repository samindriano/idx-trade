import { SLOT_BY_ID } from './core.mjs';

export const PROFILE_IDS = Object.freeze({
  STAGING_LIVE_OBSERVE_ONLY: 'staging_live_observe_only',
  PRODUCTION_PREPARATION: 'production_preparation',
  PRODUCTION_ACTIVE_INTRADAY_2030: 'production_active_intraday_2030',
});

export const EXPECTED_IMPLEMENTATION_PINS = Object.freeze({
  E2E_EXPECTED_CODE_COMMIT: '8bc3ee3efd65e8b16478e404e4b226451b105c48',
  OFFICIAL_OPEN_EXPECTED_CODE_COMMIT: 'ac29a0552b1785045906f8d608b5371d93e01b73',
});

export const EXPECTED_CRONS = Object.freeze([
  '35,50 1 * * 1-5',
  '0,5,15,22 2 * * 1-5',
  '40 11 * * 1-5',
  '10,40 12 * * 1-5',
  '40 13 * * 1-5',
]);

export const EXPECTED_R2 = Object.freeze({
  binding: 'ARCHIVE',
  bucket_name: 'idx-trade-stockbit-stream-v1',
});

export const EXPECTED_DURABLE_OBJECT = Object.freeze({
  name: 'COORDINATOR',
  class_name: 'SchedulerCoordinator',
});

export const EXPECTED_EXPORT = Object.freeze({
  SchedulerCoordinator: Object.freeze({
    type: 'durable-object',
    storage: 'sqlite',
  }),
});

const EXPECTED_VARS = Object.freeze({
  GITHUB_OWNER: 'samindriano',
  GITHUB_REPO: 'idx-trade',
  GITHUB_REF: 'main',
  compatibility_date: '2026-08-27',
  workers_dev: false,
  entrypoint: 'src/index.js',
});

const PRODUCTION_SCOPE = Object.freeze(['STOCKBIT_INTRADAY_2030']);

export const PROFILE_CONTRACTS = Object.freeze({
  [PROFILE_IDS.STAGING_LIVE_OBSERVE_ONLY]: Object.freeze({
    id: PROFILE_IDS.STAGING_LIVE_OBSERVE_ONLY,
    workerName: 'idx-trade-github-scheduler-v1-staging-live-observe',
    mode: 'observe_only',
    scope: Object.freeze({ kind: 'unconfigured' }),
    crons: EXPECTED_CRONS,
    secrets: Object.freeze(['GITHUB_ACTIONS_READ_TOKEN']),
    traffic: Object.freeze({ kind: 'non_automatic' }),
  }),
  [PROFILE_IDS.PRODUCTION_PREPARATION]: Object.freeze({
    id: PROFILE_IDS.PRODUCTION_PREPARATION,
    workerName: 'idx-trade-github-scheduler-v1',
    mode: 'observe_only',
    scope: Object.freeze({ kind: 'exact', slotIds: PRODUCTION_SCOPE }),
    crons: Object.freeze([]),
    secrets: Object.freeze(['GITHUB_ACTIONS_READ_TOKEN', 'GITHUB_ACTIONS_WRITE_TOKEN']),
    traffic: Object.freeze({ kind: 'non_automatic' }),
  }),
  [PROFILE_IDS.PRODUCTION_ACTIVE_INTRADAY_2030]: Object.freeze({
    id: PROFILE_IDS.PRODUCTION_ACTIVE_INTRADAY_2030,
    workerName: 'idx-trade-github-scheduler-v1',
    mode: 'active',
    scope: Object.freeze({ kind: 'exact', slotIds: PRODUCTION_SCOPE }),
    crons: EXPECTED_CRONS,
    secrets: Object.freeze(['GITHUB_ACTIONS_READ_TOKEN', 'GITHUB_ACTIONS_WRITE_TOKEN']),
    traffic: Object.freeze({ kind: 'exact', percentage: 100 }),
  }),
});

const PROFILE_ALIASES = Object.freeze({
  production: PROFILE_IDS.PRODUCTION_ACTIVE_INTRADAY_2030,
  preparation: PROFILE_IDS.PRODUCTION_PREPARATION,
  'staging-live': PROFILE_IDS.STAGING_LIVE_OBSERVE_ONLY,
  staging_live: PROFILE_IDS.STAGING_LIVE_OBSERVE_ONLY,
});

export function canonicalProfileId(profile) {
  return PROFILE_ALIASES[profile] ?? profile;
}

export function getProfileContract(profile) {
  const id = canonicalProfileId(profile);
  return PROFILE_CONTRACTS[id] ?? null;
}

export function relevantImplementationPinNames(allowedSlotIds = []) {
  const names = new Set();
  for (const slotId of allowedSlotIds) {
    const slot = SLOT_BY_ID.get(slotId);
    if (!slot) continue;
    if (slot.workflow === 'e2e-paper-cloud-orchestration.yml') names.add('E2E_EXPECTED_CODE_COMMIT');
    if (slot.workflow === 'official-open-prospective-cloud-capture.yml') names.add('OFFICIAL_OPEN_EXPECTED_CODE_COMMIT');
  }
  return [...names].sort();
}

export function requiredSecretNames({ mode, allowedSlotIds = [], profile = null } = {}) {
  const contract = profile ? getProfileContract(profile) : null;
  if (contract) return [...contract.secrets];
  if (mode === 'observe_only') return ['GITHUB_ACTIONS_READ_TOKEN'];
  if (mode !== 'active') return [];
  const names = ['GITHUB_ACTIONS_READ_TOKEN', 'GITHUB_ACTIONS_WRITE_TOKEN'];
  if (relevantImplementationPinNames(allowedSlotIds).includes('OFFICIAL_OPEN_EXPECTED_CODE_COMMIT')) {
    names.push('OFFICIAL_OPEN_SCHEDULER_HMAC_KEY');
  }
  return names;
}

export function scopeExpectationMatches(scope, contract) {
  if (!contract) return { ok: false, reason: 'UNKNOWN_PROFILE' };
  if (contract.scope.kind === 'unconfigured') {
    return { ok: scope.configured === false && scope.valid === true && scope.failClosed === false };
  }
  const expected = [...contract.scope.slotIds].sort();
  const actual = [...scope.allowedSlotIds].sort();
  return {
    ok: scope.valid === true && scope.failClosed === false
      && actual.length === expected.length
      && actual.every((slotId, index) => slotId === expected[index]),
    expected,
    actual,
  };
}

export { EXPECTED_VARS, PRODUCTION_SCOPE };
