/* Thin anonymous adapter over the frozen Mathieu2301 client. */
const TradingView = require('@mathieuc/tradingview');

function classify(periods, trace, errors, timedOut) {
  const events = new Set(trace.map((x) => String(x).toLowerCase()));
  const text = errors.join(' ').toLowerCase();
  if (events.has('symbol_error') || text.includes('symbol error')) return 'SYMBOL_ERROR';
  if (['permission', 'entitlement', 'not authorized', 'auth'].some((x) => text.includes(x))) return 'ENTITLEMENT_OR_PERMISSION_ERROR';
  if (events.has('transport_error') || events.has('websocket_error')) return 'TRANSPORT_ERROR';
  if (periods > 0) return 'AVAILABLE';
  if (events.has('series_completed')) return 'SERIES_COMPLETED_EMPTY';
  if (timedOut) return events.size === 0 ? 'TRANSPORT_TIMEOUT' : 'UNCLASSIFIED_NO_DATA';
  if (errors.length) return 'PROVIDER_ERROR';
  return 'UNCLASSIFIED_NO_DATA';
}

function collectChart(request) {
  return new Promise((resolve) => {
    const started = Date.now();
    const startedAt = new Date().toISOString();
    const trace = [];
    const errors = [];
    const client = new TradingView.Client({ server: request.server });
    let chart;
    let settled = false;
    let timeoutHandle;
    let pageHandle;
    let initialUpdate = false;
    let waitingForPage = false;
    let page = 0;
    let beforeMin = null;
    let beforeCount = 0;
    let connected = false;
    let disconnected = false;
    let symbolLoaded = false;
    let firstUpdateAt = null;
    let lastUpdateAt = null;
    const pagination = { requested_steps: request.fetch_more_steps || 0, batch: request.fetch_more_batch || 1, steps: [], completion_reason: null };
    const finish = (extra = {}) => {
      if (settled) return;
      settled = true;
      if (timeoutHandle) clearTimeout(timeoutHandle);
      if (pageHandle) clearTimeout(pageHandle);
      const periods = chart ? chart.periods.map((p) => ({ time: p.time, open: p.open, high: p.max, low: p.min, close: p.close, volume: p.volume })) : [];
      const completionReason = extra.completion_reason || pagination.completion_reason;
      const depthCompletionStatus = extra.depth_completion_status || (
        completionReason === 'required_start_reached' ? 'REQUIRED_START_REACHED' :
        completionReason === 'max_steps' ? 'MAX_DEPTH_EXHAUSTED' :
        ['page_timeout_no_extension', 'request_timeout'].includes(completionReason) ? 'TIMEOUT' :
        completionReason === 'no_extension' ? 'NO_EXTENSION' :
        ['SYMBOL_ERROR', 'PROVIDER_ERROR'].includes(classify(periods.length, trace, errors, extra.timed_out === true)) ? 'PROVIDER_ERROR' :
        'NO_EXTENSION'
      );
      const result = {
        request,
        server: request.server,
        started_at_utc: startedAt,
        finished_at_utc: new Date().toISOString(),
        elapsed_ms: Date.now() - started,
        status: classify(periods.length, trace, errors, extra.timed_out === true),
        errors,
        event_trace: trace,
        event_observation: { websocket_connected: connected, websocket_disconnected: disconnected, symbol_loaded: symbolLoaded, update_seen: initialUpdate, first_update_at_utc: firstUpdateAt, last_update_at_utc: lastUpdateAt, series_completed_observable: false, series_completed_note: 'The pinned Mathieu client does not expose series_completed.' },
        market_info: chart ? (chart.infos || {}) : {},
        periods,
        fetch_more: { ...pagination, completion_reason: completionReason, final_min_epoch: periods.length ? Math.min(...periods.map((p) => p.time)) : null },
        provider_data_status: classify(periods.length, trace, errors, extra.timed_out === true),
        depth_completion_status: depthCompletionStatus,
        ...extra,
      };
      try { if (chart) chart.delete(); client.end(); } catch (_) { /* best-effort teardown */ }
      resolve(result);
    };
    client.onConnected(() => { connected = true; trace.push('connected'); });
    client.onDisconnected(() => { disconnected = true; trace.push('disconnected'); });
    client.onError((...values) => { errors.push(...values.map(String)); trace.push('transport_error'); if (!chart || !initialUpdate) finish({ error_phase: 'client' }); });
    chart = new client.Session.Chart();
    chart.onSymbolLoaded(() => { symbolLoaded = true; trace.push('symbol_loaded'); });
    chart.onError((...values) => { const message = values.map(String); errors.push(...message); trace.push(message.join(' ').toLowerCase().includes('symbol error') ? 'symbol_error' : 'provider_error'); finish({ error_phase: 'chart' }); });
    const requestPage = () => {
      if (settled) return;
      const periods = chart.periods;
      beforeCount = periods.length;
      beforeMin = beforeCount ? Math.min(...periods.map((p) => p.time)) : null;
      page += 1;
      waitingForPage = true;
      trace.push(`request_more_data_${page}`);
      chart.fetchMore(request.fetch_more_batch || 1);
      pageHandle = setTimeout(() => {
        if (settled) return;
        pagination.steps.push({ step: page, before_min_epoch: beforeMin, before_count: beforeCount, after_min_epoch: chart.periods.length ? Math.min(...chart.periods.map((p) => p.time)) : null, after_count: chart.periods.length, delta_bars: chart.periods.length - beforeCount, extended: false, reason: 'page_timeout_no_extension' });
        pagination.completion_reason = 'page_timeout_no_extension';
        finish();
      }, request.fetch_more_wait_ms || 8000);
    };
    chart.onUpdate(() => {
      const now = new Date().toISOString();
      lastUpdateAt = now;
      trace.push('update');
      if (!chart.periods.length) return;
      if (!initialUpdate) {
        initialUpdate = true;
        firstUpdateAt = now;
        if ((request.fetch_more_steps || 0) > 0) requestPage();
        else { pagination.completion_reason = 'initial_update_no_pagination'; finish(); }
        return;
      }
      if (!waitingForPage) return;
      const afterMin = Math.min(...chart.periods.map((p) => p.time));
      const afterCount = chart.periods.length;
      if (beforeMin !== null && afterMin < beforeMin) {
        clearTimeout(pageHandle);
        pagination.steps.push({ step: page, before_min_epoch: beforeMin, before_count: beforeCount, after_min_epoch: afterMin, after_count: afterCount, delta_bars: afterCount - beforeCount, extended: true, reason: 'extended' });
        waitingForPage = false;
        const requiredEpoch = request.required_start ? Math.floor(new Date(`${request.required_start}T00:00:00+07:00`).getTime() / 1000) : null;
        const bufferEpoch = request.prior_session_start ? Math.floor(new Date(`${request.prior_session_start}T00:00:00+07:00`).getTime() / 1000) : requiredEpoch;
        if (bufferEpoch !== null && afterMin <= bufferEpoch) {
          pagination.completion_reason = 'required_start_reached';
          finish({ completion_reason: 'required_start_reached' });
        } else if (page < (request.fetch_more_steps || 0)) requestPage();
        else { pagination.completion_reason = 'max_steps'; finish(); }
      }
    });
    chart.setMarket(request.symbol, { timeframe: request.timeframe, range: request.initial_range, to: request.to, adjustment: request.adjustment, session: request.session });
    timeoutHandle = setTimeout(() => { trace.push('adapter_timeout'); pagination.completion_reason = 'request_timeout'; finish({ timed_out: true, error_phase: 'adapter' }); }, request.timeout_ms || 25000);
  });
}

module.exports = { collectChart };
if (require.main === module) collectChart(JSON.parse(process.argv[2])).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`));
