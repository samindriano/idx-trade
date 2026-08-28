export const DISPATCH_MODES = Object.freeze(['active', 'observe_only']);

export function requireDispatchMode(value) {
  if (typeof value !== 'string') throw new Error('INVALID_DISPATCH_MODE');
  const mode = value.trim();
  if (!DISPATCH_MODES.includes(mode)) throw new Error('INVALID_DISPATCH_MODE');
  return mode;
}

export async function dispatchWithMode({ mode, dispatchFn }) {
  const dispatchMode = requireDispatchMode(mode);
  if (dispatchMode === 'observe_only') {
    return {
      ok: false,
      status: 'WOULD_DISPATCH',
      dispatch_mode: dispatchMode,
      retryable: false,
      runId: null,
    };
  }
  return { ...(await dispatchFn()), dispatch_mode: dispatchMode };
}
