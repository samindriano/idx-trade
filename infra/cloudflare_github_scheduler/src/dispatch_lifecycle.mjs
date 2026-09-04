import { dispatchWithMode, requireDispatchMode } from './dispatch_mode.mjs';

/**
 * Keep local preparation separate from the external POST boundary.
 *
 * A preparation failure has no possible GitHub side effect and may release a
 * still-owned marker explicitly.  Once dispatchWithMode invokes dispatch(),
 * a rejected fetch is treated as POST-uncertain: this helper returns without
 * invoking any release callback, so the caller's dispatch lease remains a
 * fence until an authoritative observation resolves it.
 */
export async function dispatchWithLeaseBoundary({
  mode,
  prepare,
  beforePost,
  dispatch,
  leaseOwned,
  onPreDispatchFailure,
}) {
  const dispatchMode = requireDispatchMode(mode);
  if (dispatchMode === 'observe_only') {
    return {
      phase: 'response',
      response: await dispatchWithMode({ mode: dispatchMode, dispatchFn: async () => dispatch(null) }),
      prepared: null,
    };
  }

  let prepared;
  try {
    prepared = await prepare();
  } catch (error) {
    let released = false;
    let releaseError = null;
    try {
      released = (await onPreDispatchFailure(error)) === true;
    } catch (callbackError) {
      releaseError = callbackError;
    }
    return {
      phase: 'pre_dispatch_failure',
      error,
      released,
      releaseError,
      prepared: null,
    };
  }

  if (!leaseOwned()) {
    return {
      phase: 'lease_lost_before_post',
      prepared,
    };
  }

  if (beforePost) {
    try {
      const decision = await beforePost();
      if (decision && decision.allow === false) {
        return {
          phase: 'pre_post_blocked',
          decision,
          prepared,
        };
      }
    } catch (error) {
      let released = false;
      let releaseError = null;
      try {
        released = (await onPreDispatchFailure(error)) === true;
      } catch (callbackError) {
        releaseError = callbackError;
      }
      return {
        phase: 'pre_dispatch_failure',
        error,
        released,
        releaseError,
        prepared,
      };
    }
  }

  // The fresh completion read is awaited. Revalidate ownership after it so
  // an old owner cannot cross the POST boundary after another attempt wins.
  if (!leaseOwned()) {
    return {
      phase: 'lease_lost_before_post',
      prepared,
    };
  }

  try {
    return {
      phase: 'response',
      response: await dispatchWithMode({
        mode: dispatchMode,
        dispatchFn: async () => dispatch(prepared),
      }),
      prepared,
    };
  } catch (error) {
    return {
      phase: 'post_attempt_uncertain',
      error,
      prepared,
    };
  }
}
