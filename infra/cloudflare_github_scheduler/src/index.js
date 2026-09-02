import { DurableObject } from 'cloudflare:workers';
import {
  SLOT_BY_ID,
  durableMarkerDecision,
  dispatchBody,
  dueSlots,
  effectiveActiveModeDecision,
  markerKey,
  slotWindow,
} from './core.mjs';
import {
  GithubApiError,
  dispatchWorkflow,
  queryExactSlotCoverage,
} from './github.mjs';
import { dispatchWithMode, requireDispatchMode } from './dispatch_mode.mjs';
import { evaluateShadowSlot } from './archive.mjs';

const SCHEMA_VERSION = 'idx_trade_cloudflare_github_scheduler_v1';

function finalizeShadowDecision(shadow, decision, extra = {}) {
  return {
    ...shadow,
    ...extra,
    active_mode_decision: decision,
    effective_active_mode_decision: decision,
  };
}

function safeError(error) {
  if (error instanceof GithubApiError) return error.code;
  if (error instanceof Error && /^[A-Z0-9_:.-]+$/.test(error.message)) return error.message;
  return 'UNCLASSIFIED_SCHEDULER_ERROR';
}

function requireEnv(env, name) {
  const value = env[name];
  if (typeof value !== 'string' || !value.trim()) throw new Error(`MISSING_${name}`);
  return value.trim();
}

export class SchedulerCoordinator extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS slot_markers (
        slot_key TEXT PRIMARY KEY,
        state TEXT NOT NULL,
        attempt_id TEXT,
        updated_at_ms INTEGER NOT NULL,
        run_id INTEGER,
        detail_json TEXT NOT NULL
      );
    `);
  }

  _read(slotKey) {
    const rows = this.sql.exec(
      'SELECT slot_key, state, attempt_id, updated_at_ms, run_id, detail_json FROM slot_markers WHERE slot_key = ?',
      slotKey,
    ).toArray();
    return rows[0] ?? null;
  }

  _write(slotKey, state, nowMs, { attemptId = null, runId = null, detail = {} } = {}) {
    const detailJson = JSON.stringify(detail);
    this.sql.exec(
      `INSERT INTO slot_markers(slot_key, state, attempt_id, updated_at_ms, run_id, detail_json)
       VALUES (?, ?, ?, ?, ?, ?)
       ON CONFLICT(slot_key) DO UPDATE SET
         state = excluded.state,
         attempt_id = excluded.attempt_id,
         updated_at_ms = excluded.updated_at_ms,
         run_id = excluded.run_id,
         detail_json = excluded.detail_json`,
      slotKey,
      state,
      attemptId,
      nowMs,
      runId,
      detailJson,
    );
    return { slotKey, state, attemptId, updatedAtMs: nowMs, runId, detail };
  }

  async processSlot(slotId, observedEpochMs, scheduledEpochMs) {
    const slot = SLOT_BY_ID.get(slotId);
    if (!slot) throw new Error('UNKNOWN_SLOT');

    const owner = requireEnv(this.env, 'GITHUB_OWNER');
    const repo = requireEnv(this.env, 'GITHUB_REPO');
    const ref = requireEnv(this.env, 'GITHUB_REF');
    const dispatchMode = requireDispatchMode(this.env.DISPATCH_MODE);
    const tokenName = dispatchMode === 'observe_only'
      ? 'GITHUB_ACTIONS_READ_TOKEN'
      : 'GITHUB_ACTIONS_TOKEN';
    const token = requireEnv(this.env, tokenName);

    const window = slotWindow(slot, observedEpochMs);
    if (observedEpochMs < window.checkMs || observedEpochMs >= window.cutoffMs) {
      return { slot: slotId, status: 'OUTSIDE_SAFE_WINDOW_NO_DISPATCH' };
    }

    const slotKey = markerKey(window.dateKey, slotId);
    const prior = this._read(slotKey);
    let exactCoverage = [];
    let githubError = null;
    try {
      exactCoverage = await queryExactSlotCoverage({
        owner,
        repo,
        token,
        slot,
        epochMs: observedEpochMs,
      });
    } catch (error) {
      githubError = safeError(error);
    }

    const shadow = await evaluateShadowSlot({
      archive: this.env.ARCHIVE,
      slot,
      session: window.dateKey,
      observedEpochMs,
      exactRuns: exactCoverage,
      githubError,
      expectedCodeCommit: this.env.E2E_EXPECTED_CODE_COMMIT,
    });
    if (exactCoverage.length) {
      const run = exactCoverage[0];
      this._write(slotKey, 'covered_exact', observedEpochMs, {
        runId: Number.isInteger(run.id) ? run.id : null,
        detail: shadow.github_exact_run_evidence,
      });
    }
    if (shadow.durable_completion.capture_complete) {
      return finalizeShadowDecision(
        shadow,
        effectiveActiveModeDecision(shadow),
        { status: 'SHADOW_DURABLE_COMPLETION_VERIFIED' },
      );
    }
    if (shadow.durable_completion.state === 'archive_completion_blocked' || githubError) {
      return finalizeShadowDecision(
        shadow,
        effectiveActiveModeDecision(shadow),
        { status: 'SHADOW_FAIL_CLOSED_NO_DISPATCH' },
      );
    }

    // A coordination marker can defer a duplicate request, but it cannot
    // manufacture durable completion. A stale final marker is therefore
    // ignored and fails closed until the archive validator succeeds.
    const markerDecision = durableMarkerDecision(prior, observedEpochMs);
    if (prior && markerDecision?.status === 'CAPTURE_ALREADY_COMPLETE') {
      return finalizeShadowDecision(shadow, 'FAIL_CLOSED_STALE_COMPLETION_MARKER', {
        status: 'SHADOW_MARKER_NOT_TRUSTED_NO_DISPATCH',
      });
    }
    if (markerDecision) {
      return finalizeShadowDecision(
        shadow,
        effectiveActiveModeDecision(shadow, markerDecision),
        {
          ...markerDecision,
          status: 'SHADOW_DEFERRED_BY_DISPATCH_LEASE',
          coordinator_marker_decision: markerDecision,
        },
      );
    }
    if (shadow.active_mode_decision === 'DEFER_VISIBLE_IN_FLIGHT_GRACE_NOT_CAPTURE_COMPLETE') {
      return finalizeShadowDecision(shadow, effectiveActiveModeDecision(shadow), {
        status: 'SHADOW_DEFERRED_BY_GITHUB_IN_FLIGHT_GRACE',
      });
    }

    const attemptId = crypto.randomUUID();
    this._write(slotKey, 'dispatching', observedEpochMs, {
      attemptId,
      detail: { scheduledEpochMs },
    });

    const dispatchInputs = dispatchBody(slot, ref).inputs;
    const dispatch = await dispatchWithMode({
      mode: dispatchMode,
      dispatchFn: () => dispatchWorkflow({ owner, repo, token, ref, slot }),
    });
    if (dispatch.status === 'WOULD_DISPATCH') {
      this._write(slotKey, 'would_dispatch', observedEpochMs, {
        detail: { dispatchMode, inputs: dispatchInputs, shadow },
      });
      return finalizeShadowDecision(shadow, effectiveActiveModeDecision(shadow), {
        status: 'WOULD_DISPATCH',
        dispatchMode,
        inputs: dispatchInputs,
      });
    }
    if (dispatch.ok) {
      this._write(slotKey, 'dispatch_requested', Date.now(), {
        attemptId,
        runId: dispatch.runId,
        detail: { githubStatus: dispatch.status },
      });
      return finalizeShadowDecision(shadow, effectiveActiveModeDecision(shadow), {
        status: 'WORKFLOW_DISPATCH_REQUESTED_NOT_CAPTURE_COMPLETE',
        capture_complete: false,
        runId: dispatch.runId,
      });
    }

    if (dispatch.retryable) {
      this._write(slotKey, 'retryable_error', Date.now(), {
        attemptId,
        detail: { githubStatus: dispatch.status },
      });
      return finalizeShadowDecision(shadow, effectiveActiveModeDecision(shadow), {
        status: 'DISPATCH_RETRYABLE_ERROR',
        githubStatus: dispatch.status,
      });
    }

    this._write(slotKey, 'blocked', Date.now(), {
      attemptId,
      detail: { githubStatus: dispatch.status },
    });
    return finalizeShadowDecision(shadow, effectiveActiveModeDecision(shadow), {
      status: 'DISPATCH_BLOCKED_NOT_CAPTURE_COMPLETE',
      capture_complete: false,
      githubStatus: dispatch.status,
    });
  }
}

export default {
  async scheduled(controller, env, ctx) {
    const observedEpochMs = Date.now();
    const slots = dueSlots(observedEpochMs);
    if (!slots.length) {
      console.log(JSON.stringify({
        schema_version: SCHEMA_VERSION,
        status: 'NO_DUE_SLOTS',
        scheduled_time_ms: controller.scheduledTime,
        observed_time_ms: observedEpochMs,
      }));
      return;
    }

    const coordinator = env.COORDINATOR.getByName('idx-trade-global-scheduler-v1');
    const results = [];
    for (const slot of slots) {
      try {
        results.push(await coordinator.processSlot(slot.id, observedEpochMs, controller.scheduledTime));
      } catch (error) {
        results.push({ slot: slot.id, status: 'FAIL_CLOSED', error: safeError(error) });
      }
    }

    console.log(JSON.stringify({
      schema_version: SCHEMA_VERSION,
      status: results.every((result) => result.status !== 'FAIL_CLOSED') ? 'CHECK_COMPLETE' : 'CHECK_PARTIAL_FAIL_CLOSED',
      scheduled_time_ms: controller.scheduledTime,
      observed_time_ms: observedEpochMs,
      results,
    }));
  },
};
