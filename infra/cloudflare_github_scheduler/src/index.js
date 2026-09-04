import { DurableObject } from 'cloudflare:workers';
import {
  SLOT_BY_ID,
  durableMarkerDecision,
  dispatchBody,
  dispatchLeaseDecision,
  dueSlots,
  effectiveActiveModeDecision,
  markerKey,
  requiredImplementationPin,
  slotWindow,
} from './core.mjs';
import {
  GithubApiError,
  dispatchWorkflow,
  queryExactSlotCoverage,
} from './github.mjs';
import { requireDispatchMode } from './dispatch_mode.mjs';
import { dispatchWithLeaseBoundary } from './dispatch_lifecycle.mjs';
import { prepareActiveDispatch } from './dispatch_prepare.mjs';
import { evaluateShadowSlot, readDurableCompletion } from './archive.mjs';
import {
  isOfficialOpenSlot,
} from './official_open_attestation.mjs';
import { validateOfficialOpenRecoveryAdmission } from './official_open_recovery_admission.mjs';

const SCHEMA_VERSION = 'idx_trade_cloudflare_github_scheduler_v1';
const OPEN_IN_FLIGHT_RECOVERY_DECISION = 'WORKFLOW_DISPATCH_WOULD_BE_ELIGIBLE_OPEN_IN_FLIGHT_NOT_CAPTURE_COMPLETE';

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

  // This method deliberately performs the read and write without an await.
  // Durable Objects serialize that synchronous prefix, so two same-slot
  // requests cannot both observe an unleased marker before one records its
  // attempt.  Stale external dispatches cannot be fenced by GitHub's API;
  // therefore an existing dispatch lease is never reclaimed automatically.
  _acquireDispatchLease(slotKey, nowMs, scheduledEpochMs) {
    const prior = this._read(slotKey);
    const decision = dispatchLeaseDecision(prior);
    if (decision.action !== 'ACQUIRE') return { prior, decision, attemptId: null };

    const attemptId = crypto.randomUUID();
    this._write(slotKey, 'dispatching', nowMs, {
      attemptId,
      detail: { scheduledEpochMs },
    });
    return { prior, decision, attemptId };
  }

  _ownsDispatchLease(slotKey, attemptId) {
    if (!attemptId) return false;
    const marker = this._read(slotKey);
    return marker?.state === 'dispatching' && marker.attempt_id === attemptId;
  }

  _writeOwnedDispatchLease(slotKey, attemptId, state, nowMs, options = {}) {
    if (!this._ownsDispatchLease(slotKey, attemptId)) return false;
    this._write(slotKey, state, nowMs, options);
    return true;
  }

  async processSlot(slotId, observedEpochMs, scheduledEpochMs) {
    const slot = SLOT_BY_ID.get(slotId);
    if (!slot) throw new Error('UNKNOWN_SLOT');

    const owner = requireEnv(this.env, 'GITHUB_OWNER');
    const repo = requireEnv(this.env, 'GITHUB_REPO');
    const ref = requireEnv(this.env, 'GITHUB_REF');
    const dispatchMode = requireDispatchMode(this.env.DISPATCH_MODE);
    // A missing or malformed producer pin is a configuration failure, not an
    // empty archive.  Require it before any active dispatch can be considered.
    const expectedCodeCommit = requiredImplementationPin(this.env, slot);
    // Run discovery is always read-only. Observe-only environments never carry
    // a workflow-dispatch credential at all; active mode accesses the write
    // credential lazily only after every recovery gate says dispatch is needed.
    const readToken = requireEnv(this.env, 'GITHUB_ACTIONS_READ_TOKEN');

    const window = slotWindow(slot, observedEpochMs);
    if (observedEpochMs < window.checkMs || observedEpochMs >= window.cutoffMs) {
      return { slot: slotId, status: 'OUTSIDE_SAFE_WINDOW_NO_DISPATCH' };
    }

    const slotKey = markerKey(window.dateKey, slotId);
    const lease = this._acquireDispatchLease(slotKey, observedEpochMs, scheduledEpochMs);
    const { prior, attemptId } = lease;
    let exactCoverage = [];
    let githubError = null;
    try {
      exactCoverage = await queryExactSlotCoverage({
        owner,
        repo,
        token: readToken,
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
      expectedCodeCommit,
    });
    let officialOpenRecoveryAdmission = null;
    if (shadow.family === 'OFFICIAL_OPEN' && shadow.durable_completion.capture_complete) {
      try {
        officialOpenRecoveryAdmission = await validateOfficialOpenRecoveryAdmission({
          archive: this.env.ARCHIVE,
          session: window.dateKey,
          slot: slot.inputValue,
          expectedCompletionSha256: shadow.durable_completion.completion_sha256,
          expectedCodeCommit: requireEnv(this.env, 'OFFICIAL_OPEN_EXPECTED_CODE_COMMIT'),
        });
      } catch (error) {
        this._writeOwnedDispatchLease(
          slotKey,
          attemptId,
          'archive_completion_blocked',
          observedEpochMs,
          { detail: { error: safeError(error) } },
        );
        return finalizeShadowDecision(
          shadow,
          'FAIL_CLOSED_OFFICIAL_OPEN_RECOVERY_ADMISSION_INVALID',
          {
            status: 'SHADOW_FAIL_CLOSED_NO_DISPATCH',
            official_open_recovery_admission: {
              recovery_admissible: false,
              error: safeError(error),
            },
          },
        );
      }
    }

    if (shadow.durable_completion.capture_complete) {
      this._writeOwnedDispatchLease(
        slotKey,
        attemptId,
        'archive_completion_observed',
        observedEpochMs,
        { detail: { completion: shadow.durable_completion } },
      );
      return finalizeShadowDecision(
        shadow,
        effectiveActiveModeDecision(shadow),
        {
          status: 'SHADOW_DURABLE_COMPLETION_VERIFIED',
          official_open_recovery_admission: officialOpenRecoveryAdmission,
        },
      );
    }
    if (shadow.durable_completion.state === 'archive_completion_blocked' || githubError) {
      this._writeOwnedDispatchLease(
        slotKey,
        attemptId,
        githubError ? 'github_query_error' : 'archive_completion_blocked',
        observedEpochMs,
        { detail: { error: githubError ?? shadow.durable_completion.reason } },
      );
      return finalizeShadowDecision(
        shadow,
        effectiveActiveModeDecision(shadow),
        { status: 'SHADOW_FAIL_CLOSED_NO_DISPATCH' },
      );
    }

    // A prior dispatch lease is a coordination defer, not archive completion.
    // The archive was still checked above so a completion that appeared while
    // the first request was running is never hidden by the marker.
    if (lease.decision.action === 'DEFER') {
      return finalizeShadowDecision(shadow, 'DEFER_COORDINATOR_DISPATCH_LEASE', {
        status: 'SHADOW_DEFERRED_BY_DISPATCH_LEASE',
        coordinator_marker_decision: lease.decision,
      });
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

    // Official Open has only one recovery check inside each narrow slot window.
    // A visible in-flight run is not durable capture evidence, so it must not
    // consume that sole recovery opportunity. The producer's pre-provider
    // timing/auth gate plus its conditional immutable slot commit keep parallel
    // native/recovery contenders fail-closed instead of allowing overwrite.
    const openInFlightRecoveryOverride = isOfficialOpenSlot(slot)
      && shadow.active_mode_decision === 'DEFER_VISIBLE_IN_FLIGHT_GRACE_NOT_CAPTURE_COMPLETE';
    if (
      shadow.active_mode_decision === 'DEFER_VISIBLE_IN_FLIGHT_GRACE_NOT_CAPTURE_COMPLETE'
      && !openInFlightRecoveryOverride
    ) {
      this._writeOwnedDispatchLease(
        slotKey,
        attemptId,
        'in_flight_grace',
        observedEpochMs,
        { detail: shadow.github_exact_run_evidence },
      );
      return finalizeShadowDecision(shadow, effectiveActiveModeDecision(shadow), {
        status: 'SHADOW_DEFERRED_BY_GITHUB_IN_FLIGHT_GRACE',
      });
    }
    const activeModeDecision = openInFlightRecoveryOverride
      ? OPEN_IN_FLIGHT_RECOVERY_DECISION
      : effectiveActiveModeDecision(shadow);

    if (!this._ownsDispatchLease(slotKey, attemptId)) {
      return finalizeShadowDecision(shadow, 'FAIL_CLOSED_COORDINATOR_LEASE_LOST', {
        status: 'SHADOW_FAIL_CLOSED_COORDINATOR_LEASE_LOST',
      });
    }

    let dispatchInputs;
    try {
      dispatchInputs = dispatchBody(slot, ref).inputs;
    } catch (error) {
      const recorded = this._writeOwnedDispatchLease(slotKey, attemptId, 'pre_dispatch_blocked', Date.now(), {
        detail: { error: safeError(error) },
      });
      return finalizeShadowDecision(shadow, 'FAIL_CLOSED_PRE_DISPATCH_VALIDATION', {
        status: 'SHADOW_FAIL_CLOSED_PRE_DISPATCH_NO_POST',
        dispatch_error: safeError(error),
        pre_dispatch_lease_released: recorded,
      });
    }

    const dispatchBoundary = await dispatchWithLeaseBoundary({
      mode: dispatchMode,
      prepare: () => prepareActiveDispatch({
        env: this.env,
        slot,
        ref,
        sessionDate: window.dateKey,
        issuedAtEpochMs: observedEpochMs,
      }),
      beforePost: async () => {
        // Re-read the canonical archive after preparation/signing and before
        // dispatchWorkflow can cross the GitHub POST boundary.  The earlier
        // shadow is intentionally not authoritative for this final decision.
        const freshCompletion = await readDurableCompletion({
          archive: this.env.ARCHIVE,
          slot,
          session: window.dateKey,
          expectedCodeCommit,
        });
        if (freshCompletion.capture_complete) {
          let freshOfficialOpenRecoveryAdmission = null;
          if (isOfficialOpenSlot(slot)) {
            try {
              freshOfficialOpenRecoveryAdmission = await validateOfficialOpenRecoveryAdmission({
                archive: this.env.ARCHIVE,
                session: window.dateKey,
                slot: slot.inputValue,
                expectedCompletionSha256: freshCompletion.completion_sha256,
                expectedCodeCommit: requireEnv(this.env, 'OFFICIAL_OPEN_EXPECTED_CODE_COMMIT'),
              });
            } catch (error) {
              return {
                allow: false,
                reason: 'OFFICIAL_OPEN_RECOVERY_ADMISSION_INVALID',
                completion: {
                  ...freshCompletion,
                  capture_complete: false,
                  state: 'archive_completion_blocked',
                  reason: safeError(error),
                },
              };
            }
          }
          return {
            allow: false,
            reason: 'DURABLE_COMPLETION_VERIFIED',
            completion: freshCompletion,
            officialOpenRecoveryAdmission: freshOfficialOpenRecoveryAdmission,
          };
        }
        if (freshCompletion.state === 'archive_completion_blocked') {
          return { allow: false, reason: 'ARCHIVE_COMPLETION_AMBIGUOUS', completion: freshCompletion };
        }
        return { allow: true, completion: freshCompletion };
      },
      leaseOwned: () => this._ownsDispatchLease(slotKey, attemptId),
      onPreDispatchFailure: (error) => this._writeOwnedDispatchLease(
        slotKey,
        attemptId,
        'pre_dispatch_blocked',
        Date.now(),
        { detail: { error: safeError(error) } },
      ),
      dispatch: (prepared) => dispatchWorkflow({
        owner,
        repo,
        token: prepared.token,
        ref,
        slot,
        body: prepared.body,
      }),
    });
    if (dispatchBoundary.phase === 'pre_dispatch_failure') {
      return finalizeShadowDecision(shadow, 'FAIL_CLOSED_PRE_DISPATCH_VALIDATION', {
        status: 'SHADOW_FAIL_CLOSED_PRE_DISPATCH_NO_POST',
        dispatch_error: safeError(dispatchBoundary.error),
        pre_dispatch_lease_released: dispatchBoundary.released,
        pre_dispatch_release_error: dispatchBoundary.releaseError ? safeError(dispatchBoundary.releaseError) : null,
      });
    }
    if (dispatchBoundary.phase === 'lease_lost_before_post') {
      return finalizeShadowDecision(shadow, 'FAIL_CLOSED_COORDINATOR_LEASE_LOST', {
        status: 'SHADOW_FAIL_CLOSED_COORDINATOR_LEASE_LOST',
      });
    }
    if (dispatchBoundary.phase === 'pre_post_blocked') {
      const freshCompletion = dispatchBoundary.decision?.completion;
      const complete = freshCompletion?.capture_complete === true;
      const state = complete ? 'archive_completion_observed' : 'archive_completion_blocked';
      const recorded = this._writeOwnedDispatchLease(
        slotKey,
        attemptId,
        state,
        Date.now(),
        { detail: { completion: freshCompletion, reason: dispatchBoundary.decision?.reason } },
      );
      if (!recorded) {
        return finalizeShadowDecision(shadow, 'FAIL_CLOSED_COORDINATOR_LEASE_LOST', {
          status: 'SHADOW_FAIL_CLOSED_COORDINATOR_LEASE_LOST',
        });
      }
      return finalizeShadowDecision(
        shadow,
        complete ? 'CAPTURE_ALREADY_COMPLETE' : 'FAIL_CLOSED_ARCHIVE_COMPLETION_AMBIGUOUS',
        {
          status: complete ? 'SHADOW_DURABLE_COMPLETION_VERIFIED' : 'SHADOW_FAIL_CLOSED_NO_DISPATCH',
          fresh_durable_completion: freshCompletion,
          fresh_official_open_recovery_admission: dispatchBoundary.decision?.officialOpenRecoveryAdmission ?? null,
          fresh_completion_check: dispatchBoundary.decision?.reason,
        },
      );
    }
    const dispatch = dispatchBoundary.response;
    if (dispatch?.post_attempted === false) {
      const recorded = this._writeOwnedDispatchLease(slotKey, attemptId, 'pre_dispatch_blocked', Date.now(), {
        detail: { error: dispatch.status },
      });
      return finalizeShadowDecision(shadow, 'FAIL_CLOSED_PRE_DISPATCH_VALIDATION', {
        status: 'SHADOW_FAIL_CLOSED_PRE_DISPATCH_NO_POST',
        dispatch_error: dispatch.status,
        pre_dispatch_lease_released: recorded,
      });
    }
    if (dispatchBoundary.phase === 'post_attempt_uncertain') {
      // Do not write a reacquirable state here.  The fetch may have reached
      // GitHub despite rejecting locally, and GitHub has no invalidating
      // fencing token.  The owned dispatching marker remains the fence.
      return finalizeShadowDecision(shadow, 'FAIL_CLOSED_POST_ATTEMPT_UNCERTAIN', {
        status: 'SHADOW_FAIL_CLOSED_POST_ATTEMPT_UNCERTAIN',
        capture_complete: false,
        post_attempt_uncertain: true,
        dispatch_error: safeError(dispatchBoundary.error),
      });
    }
    if (dispatch.status === 'WOULD_DISPATCH') {
      const recorded = this._writeOwnedDispatchLease(slotKey, attemptId, 'would_dispatch', observedEpochMs, {
        detail: {
          dispatchMode,
          inputs: dispatchInputs,
          officialOpenAttestationRequired: isOfficialOpenSlot(slot),
          openInFlightRecoveryOverride,
          shadow,
        },
      });
      if (!recorded) {
        return finalizeShadowDecision(shadow, 'FAIL_CLOSED_COORDINATOR_LEASE_LOST', {
          status: 'SHADOW_FAIL_CLOSED_COORDINATOR_LEASE_LOST',
        });
      }
      return finalizeShadowDecision(shadow, activeModeDecision, {
        status: 'WOULD_DISPATCH',
        dispatchMode,
        inputs: dispatchInputs,
        official_open_attestation_required: isOfficialOpenSlot(slot),
        open_inflight_recovery_override: openInFlightRecoveryOverride,
      });
    }
    if (dispatch.ok) {
      const recorded = this._writeOwnedDispatchLease(slotKey, attemptId, 'dispatch_requested', Date.now(), {
        attemptId,
        runId: dispatch.runId,
        detail: {
          githubStatus: dispatch.status,
          officialOpenAttestationUsed: isOfficialOpenSlot(slot),
          openInFlightRecoveryOverride,
        },
      });
      if (!recorded) {
        return finalizeShadowDecision(shadow, 'FAIL_CLOSED_COORDINATOR_LEASE_LOST', {
          status: 'SHADOW_FAIL_CLOSED_COORDINATOR_LEASE_LOST_AFTER_DISPATCH',
          capture_complete: false,
          runId: dispatch.runId,
        });
      }
      return finalizeShadowDecision(shadow, activeModeDecision, {
        status: 'WORKFLOW_DISPATCH_REQUESTED_NOT_CAPTURE_COMPLETE',
        capture_complete: false,
        official_open_attestation_used: isOfficialOpenSlot(slot),
        open_inflight_recovery_override: openInFlightRecoveryOverride,
        runId: dispatch.runId,
      });
    }

    if (dispatch.retryable) {
      const recorded = this._writeOwnedDispatchLease(slotKey, attemptId, 'dispatch_response_uncertain', Date.now(), {
        attemptId,
        detail: { githubStatus: dispatch.status, openInFlightRecoveryOverride },
      });
      if (!recorded) {
        return finalizeShadowDecision(shadow, 'FAIL_CLOSED_COORDINATOR_LEASE_LOST', {
          status: 'SHADOW_FAIL_CLOSED_COORDINATOR_LEASE_LOST',
        });
      }
      return finalizeShadowDecision(shadow, activeModeDecision, {
        status: 'DISPATCH_RETRYABLE_ERROR',
        open_inflight_recovery_override: openInFlightRecoveryOverride,
        githubStatus: dispatch.status,
      });
    }

    const recorded = this._writeOwnedDispatchLease(slotKey, attemptId, 'dispatch_response_uncertain', Date.now(), {
      attemptId,
      detail: { githubStatus: dispatch.status, openInFlightRecoveryOverride },
    });
    if (!recorded) {
      return finalizeShadowDecision(shadow, 'FAIL_CLOSED_COORDINATOR_LEASE_LOST', {
        status: 'SHADOW_FAIL_CLOSED_COORDINATOR_LEASE_LOST',
      });
    }
    return finalizeShadowDecision(shadow, activeModeDecision, {
      status: 'DISPATCH_BLOCKED_NOT_CAPTURE_COMPLETE',
      capture_complete: false,
      open_inflight_recovery_override: openInFlightRecoveryOverride,
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
