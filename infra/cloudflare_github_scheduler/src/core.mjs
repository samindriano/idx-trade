export const JAKARTA_OFFSET_MS = 7 * 60 * 60 * 1000;
export const DISPATCH_LEASE_MS = 2 * 60 * 1000;
// Scheduler state is not capture evidence.  Only an independently validated
// existing archive commit may become capture-final.
export const CAPTURE_FINAL_MARKER_STATES = Object.freeze(['capture_complete']);
export const SLOT_RUN_NAME_PREFIX = 'IDX-SLOT:';

export const SLOTS = Object.freeze([
  { id: 'E2E_PREOPEN_CA_0830', due: '08:30', checkDelayMin: 5, latest: '08:39', workflow: 'e2e-paper-cloud-orchestration.yml', inputName: 'phase', inputValue: 'PREOPEN_CA' },
  { id: 'E2E_PREOPEN_CA_0845', due: '08:45', checkDelayMin: 5, latest: '08:54', workflow: 'e2e-paper-cloud-orchestration.yml', inputName: 'phase', inputValue: 'PREOPEN_CA' },
  { id: 'E2E_PREOPEN_CA_0855', due: '08:55', checkDelayMin: 5, latest: '09:02', workflow: 'e2e-paper-cloud-orchestration.yml', inputName: 'phase', inputValue: 'PREOPEN_CA' },
  { id: 'OFFICIAL_OPEN_0902', due: '09:02', checkDelayMin: 3, latest: '09:08', workflow: 'official-open-prospective-cloud-capture.yml', inputName: 'slot', inputValue: '0902' },
  { id: 'E2E_PREOPEN_0903', due: '09:03', checkDelayMin: 2, latest: '09:09', workflow: 'e2e-paper-cloud-orchestration.yml', inputName: 'phase', inputValue: 'PREOPEN' },
  { id: 'OFFICIAL_OPEN_0912', due: '09:12', checkDelayMin: 3, latest: '09:18', workflow: 'official-open-prospective-cloud-capture.yml', inputName: 'slot', inputValue: '0912' },
  { id: 'E2E_PREOPEN_0913', due: '09:13', checkDelayMin: 2, latest: '09:19', workflow: 'e2e-paper-cloud-orchestration.yml', inputName: 'phase', inputValue: 'PREOPEN' },
  { id: 'OFFICIAL_OPEN_0922', due: '09:22', checkDelayMin: 0, latest: '09:23', workflow: 'official-open-prospective-cloud-capture.yml', inputName: 'slot', inputValue: '0922' },
  { id: 'E2E_PREOPEN_0922', due: '09:22', checkDelayMin: 0, latest: '09:23', workflow: 'e2e-paper-cloud-orchestration.yml', inputName: 'phase', inputValue: 'PREOPEN' },
  { id: 'STOCKBIT_INTRADAY_1830', due: '18:30', checkDelayMin: 10, latest: '19:30', workflow: 'stockbit-intraday-cloud-production.yml', inputName: 'slot', inputValue: '1830' },
  { id: 'E2E_POST_EOD_1835', due: '18:35', checkDelayMin: 5, latest: '19:05', workflow: 'e2e-paper-cloud-orchestration.yml', inputName: 'phase', inputValue: 'POST_EOD' },
  { id: 'E2E_POST_EOD_1905', due: '19:05', checkDelayMin: 5, latest: '19:35', workflow: 'e2e-paper-cloud-orchestration.yml', inputName: 'phase', inputValue: 'POST_EOD' },
  { id: 'STOCKBIT_INTRADAY_1930', due: '19:30', checkDelayMin: 10, latest: '20:30', workflow: 'stockbit-intraday-cloud-production.yml', inputName: 'slot', inputValue: '1930' },
  { id: 'E2E_POST_EOD_1935', due: '19:35', checkDelayMin: 5, latest: '21:35', workflow: 'e2e-paper-cloud-orchestration.yml', inputName: 'phase', inputValue: 'POST_EOD' },
  { id: 'STOCKBIT_INTRADAY_2030', due: '20:30', checkDelayMin: 10, latest: '22:30', workflow: 'stockbit-intraday-cloud-production.yml', inputName: 'slot', inputValue: '2030' },
]);

export const SLOT_BY_ID = new Map(SLOTS.map((slot) => [slot.id, slot]));

const IN_FLIGHT_RUN_STATUSES = new Set(['queued', 'in_progress', 'requested', 'waiting', 'pending']);

/**
 * GitHub run metadata is never completion evidence. A recent in-flight run
 * may receive a short grace period to avoid duplicate dispatches, but every
 * other non-final observation remains recovery-eligible until an archive
 * validator supplies capture completion.
 */
export function exactRunRecoveryDecision(run, observedEpochMs) {
  const status = typeof run?.status === 'string' ? run.status.trim().toLowerCase() : '';
  const conclusion = typeof run?.conclusion === 'string' ? run.conclusion.trim().toLowerCase() : '';
  const active = IN_FLIGHT_RUN_STATUSES.has(status) && !conclusion;
  if (!active) {
    return { defer: false, recoveryEligible: true, final: false };
  }

  const updatedMs = Date.parse(run?.updated_at ?? run?.created_at ?? '');
  const fresh = Number.isFinite(updatedMs) && observedEpochMs - updatedMs < DISPATCH_LEASE_MS;
  return {
    defer: fresh,
    recoveryEligible: !fresh,
    final: false,
    status: fresh ? 'RUN_VISIBLE_IN_FLIGHT_GRACE_NOT_CAPTURE_COMPLETE' : 'RUN_VISIBLE_NOT_CAPTURE_COMPLETE',
    runId: run?.id ?? null,
  };
}

export function jakartaDateKey(epochMs) {
  return new Date(epochMs + JAKARTA_OFFSET_MS).toISOString().slice(0, 10);
}

export function jakartaWeekday(epochMs) {
  const shifted = new Date(epochMs + JAKARTA_OFFSET_MS);
  return shifted.getUTCDay();
}

export function localTimeEpochMs(dateKey, hhmm) {
  const [year, month, day] = dateKey.split('-').map(Number);
  const [hour, minute] = hhmm.split(':').map(Number);
  return Date.UTC(year, month - 1, day, hour - 7, minute, 0, 0);
}

export function slotWindow(slot, epochMs) {
  const dateKey = jakartaDateKey(epochMs);
  const dateStartMs = localTimeEpochMs(dateKey, '00:00');
  const dueMs = localTimeEpochMs(dateKey, slot.due);
  const checkMs = dueMs + slot.checkDelayMin * 60_000;
  const configuredLatestMs = localTimeEpochMs(dateKey, slot.latest);
  const nextSameWorkflow = SLOTS
    .filter((candidate) => candidate.workflow === slot.workflow)
    .map((candidate) => ({ candidate, dueMs: localTimeEpochMs(dateKey, candidate.due) }))
    .filter((entry) => entry.dueMs > dueMs)
    .sort((a, b) => a.dueMs - b.dueMs)[0];
  const cutoffMs = nextSameWorkflow ? Math.min(configuredLatestMs, nextSameWorkflow.dueMs) : configuredLatestMs;
  return { dateKey, dateStartMs, dueMs, checkMs, cutoffMs, nextSameWorkflowDueMs: nextSameWorkflow?.dueMs ?? null };
}

export function dueSlots(epochMs) {
  const weekday = jakartaWeekday(epochMs);
  if (weekday === 0 || weekday === 6) return [];
  return SLOTS.filter((slot) => {
    const { checkMs, cutoffMs } = slotWindow(slot, epochMs);
    return epochMs >= checkMs && epochMs < cutoffMs;
  });
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function canonicalSlotRunName(slotId) {
  return `${SLOT_RUN_NAME_PREFIX}${slotId}`;
}

export function hasExactSlotRunName(run, slotId) {
  const expected = canonicalSlotRunName(slotId);
  const boundaryPattern = new RegExp(`(?:^|[^A-Za-z0-9_])${escapeRegExp(expected)}(?:$|[^A-Za-z0-9_])`);
  return ['display_title', 'run_name', 'runName']
    .map((field) => run?.[field])
    .some((value) => typeof value === 'string' && boundaryPattern.test(value));
}

export function isProductionMainRun(run) {
  const branch = typeof run?.head_branch === 'string' ? run.head_branch.trim() : null;
  const ref = typeof run?.ref === 'string' ? run.ref.trim() : null;
  const validRefs = new Set(['main', 'refs/heads/main']);
  if (branch !== null && branch !== 'main') return false;
  if (ref !== null && !validRefs.has(ref)) return false;
  return branch === 'main' || (ref !== null && validRefs.has(ref));
}

export function exactSlotCoverageRuns(runs, slot, epochMs) {
  const { dueMs, cutoffMs } = slotWindow(slot, epochMs);
  return runs.filter((run) => {
    if (run?.event !== 'schedule' && run?.event !== 'workflow_dispatch') return false;
    if (!isProductionMainRun(run)) return false;
    if (!hasExactSlotRunName(run, slot.id)) return false;
    // created_at is only a temporal admission bound. It is never used to infer
    // which logical slot produced the run; the exact run name is the identity.
    const createdMs = Date.parse(run?.created_at ?? '');
    return Number.isFinite(createdMs) && createdMs >= dueMs && createdMs < cutoffMs && createdMs <= epochMs;
  });
}

export function isCaptureFinalMarkerState(state) {
  return CAPTURE_FINAL_MARKER_STATES.includes(state);
}

export function durableMarkerDecision(prior, observedEpochMs) {
  if (prior && isCaptureFinalMarkerState(prior.state)) {
    return {
      status: 'CAPTURE_ALREADY_COMPLETE',
      state: prior.state,
      runId: prior.run_id ?? null,
    };
  }
  if (
    prior &&
    ['dispatching', 'dispatch_requested', 'dispatched'].includes(prior.state) &&
    observedEpochMs - Number(prior.updated_at_ms) < DISPATCH_LEASE_MS
  ) {
    return {
      status: 'DISPATCH_REQUESTED_NOT_CAPTURE_COMPLETE',
      state: prior.state,
      runId: prior.run_id ?? null,
    };
  }
  return null;
}

export function workflowRunsUrl({ owner, repo, workflow, startMs, endMs }) {
  const params = new URLSearchParams({
    per_page: '100',
    created: `${new Date(startMs).toISOString()}..${new Date(endMs).toISOString()}`,
  });
  return `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/actions/workflows/${encodeURIComponent(workflow)}/runs?${params}`;
}

export function workflowDispatchUrl({ owner, repo, workflow }) {
  return `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/actions/workflows/${encodeURIComponent(workflow)}/dispatches`;
}

export function dispatchBody(slot, ref = 'main') {
  const inputs = { [slot.inputName]: slot.inputValue };
  if (slot.inputName === 'phase') inputs.trigger_slot = slot.id;
  return { ref, inputs };
}

export function markerKey(dateKey, slotId) {
  return `${dateKey}::${slotId}`;
}
