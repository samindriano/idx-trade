/*
 * Thin adapter over the exact Mathieu2301/TradingView-API commit.
 * It records only events exposed by that pinned client. In particular, the
 * client does not expose TradingView's series_completed event; the result
 * therefore preserves that observability limitation instead of inventing a
 * completion state.
 */

const TradingView = require('@mathieuc/tradingview');

function classify({ periods, eventTrace, errors, timedOut }) {
  const trace = new Set(eventTrace.map((value) => String(value).toLowerCase()));
  const messages = errors.map(String).join(' ').toLowerCase();
  if (trace.has('symbol_error') || messages.includes('symbol error')) return 'SYMBOL_ERROR';
  if (['permission', 'entitlement', 'not authorized', 'auth'].some((token) => messages.includes(token))) {
    return 'ENTITLEMENT_OR_PERMISSION_ERROR';
  }
  if (trace.has('transport_error') || trace.has('websocket_error')) return 'TRANSPORT_ERROR';
  if (periods > 0) return 'AVAILABLE';
  if (trace.has('series_completed')) return 'SERIES_COMPLETED_EMPTY';
  if (timedOut) return trace.size === 0 ? 'TRANSPORT_TIMEOUT' : 'UNCLASSIFIED_NO_DATA';
  if (errors.length > 0) return 'PROVIDER_ERROR';
  return 'UNCLASSIFIED_NO_DATA';
}

function collectChart(request) {
  return new Promise((resolve) => {
    const startedAt = new Date().toISOString();
    const eventTrace = [];
    const client = new TradingView.Client({ server: request.server });
    let chart;
    let settled = false;
    let timeoutHandle;
    let pageHandle;
    let initialUpdateSeen = false;
    let waitingForPage = false;
    let pageNumber = 0;
    let pageBeforeMin = null;
    let pageBeforeCount = null;
    const errors = [];
    const pagination = {
      requested_steps: request.fetch_more_steps || 0,
      batch: request.fetch_more_batch || 1,
      steps: [],
      completion_reason: null,
    };
    let connected = false;
    let disconnected = false;
    let symbolLoaded = false;
    let emptyUpdates = 0;
    let firstUpdateAt = null;
    let lastUpdateAt = null;

    const finish = (extra = {}) => {
      if (settled) return;
      settled = true;
      if (timeoutHandle) clearTimeout(timeoutHandle);
      if (pageHandle) clearTimeout(pageHandle);
      const periods = chart ? chart.periods.map((period) => ({
        time: period.time,
        open: period.open,
        high: period.max,
        low: period.min,
        close: period.close,
        volume: period.volume,
      })) : [];
      const timedOut = extra.timed_out === true;
      const status = classify({ periods: periods.length, eventTrace, errors, timedOut });
      const result = {
        request,
        server: request.server,
        started_at_utc: startedAt,
        finished_at_utc: new Date().toISOString(),
        elapsed_ms: Date.now() - Date.parse(startedAt),
        status,
        errors,
        event_trace: eventTrace,
        event_observation: {
          websocket_connected: connected,
          websocket_disconnected: disconnected,
          symbol_loaded: symbolLoaded,
          update_seen: initialUpdateSeen,
          empty_update_count: emptyUpdates,
          first_update_at_utc: firstUpdateAt,
          last_update_at_utc: lastUpdateAt,
          series_completed_observable: false,
          series_completed_note: 'Pinned Mathieu client does not expose series_completed to the adapter.',
        },
        market_info: chart ? chart.infos : {},
        periods,
        fetch_more: {
          ...pagination,
          final_min_epoch: periods.length ? Math.min(...periods.map((period) => period.time)) : null,
        },
        ...extra,
      };
      if (chart) chart.delete();
      client.end();
      resolve(result);
    };

    client.onConnected(() => { connected = true; eventTrace.push('connected'); });
    client.onDisconnected(() => { disconnected = true; eventTrace.push('disconnected'); });
    client.onError((...error) => {
      errors.push(...error.map(String));
      eventTrace.push('transport_error');
      if (!chart || !initialUpdateSeen) finish({ error_phase: 'client', timed_out: false });
    });

    chart = new client.Session.Chart();
    chart.onSymbolLoaded(() => {
      symbolLoaded = true;
      eventTrace.push('symbol_loaded');
    });
    chart.onError((...error) => {
      const text = error.map(String);
      errors.push(...text);
      if (text.join(' ').toLowerCase().includes('symbol error')) eventTrace.push('symbol_error');
      else eventTrace.push('provider_error');
      finish({ error_phase: 'chart', timed_out: false });
    });

    const beginPage = () => {
      if (!chart || settled) return;
      const periods = chart.periods;
      pageBeforeMin = periods.length ? Math.min(...periods.map((period) => period.time)) : null;
      pageBeforeCount = periods.length;
      pageNumber += 1;
      waitingForPage = true;
      eventTrace.push(`request_more_data_${pageNumber}`);
      chart.fetchMore(request.fetch_more_batch || 1);
      pageHandle = setTimeout(() => {
        if (settled) return;
        pagination.steps.push({
          step: pageNumber,
          before_min_epoch: pageBeforeMin,
          before_count: pageBeforeCount,
          after_min_epoch: chart.periods.length ? Math.min(...chart.periods.map((period) => period.time)) : null,
          after_count: chart.periods.length,
          extended: false,
          reason: 'page_timeout_no_extension',
        });
        waitingForPage = false;
        pagination.completion_reason = 'page_timeout_no_extension';
        finish({ timed_out: false });
      }, request.fetch_more_wait_ms || 8000);
    };

    chart.onUpdate(() => {
      const now = new Date().toISOString();
      lastUpdateAt = now;
      eventTrace.push('update');
      const periods = chart.periods;
      if (!periods.length) {
        emptyUpdates += 1;
        eventTrace.push('update_empty');
        return;
      }
      if (!initialUpdateSeen) {
        initialUpdateSeen = true;
        firstUpdateAt = now;
        if ((request.fetch_more_steps || 0) > 0) beginPage();
        else {
          pagination.completion_reason = 'initial_update_no_pagination';
          finish({ timed_out: false });
        }
        return;
      }
      if (!waitingForPage) return;
      const afterMin = Math.min(...periods.map((period) => period.time));
      const extended = pageBeforeMin !== null && afterMin < pageBeforeMin;
      if (!extended) return;
      clearTimeout(pageHandle);
      pagination.steps.push({
        step: pageNumber,
        before_min_epoch: pageBeforeMin,
        before_count: pageBeforeCount,
        after_min_epoch: afterMin,
        after_count: periods.length,
        extended: true,
        reason: 'extended',
      });
      waitingForPage = false;
      if (pageNumber < (request.fetch_more_steps || 0)) beginPage();
      else {
        pagination.completion_reason = 'max_steps';
        finish({ timed_out: false });
      }
    });

    chart.setMarket(request.symbol, {
      timeframe: request.timeframe,
      range: request.initial_range,
      to: request.to,
      adjustment: request.adjustment,
      session: request.session,
    });
    timeoutHandle = setTimeout(() => {
      eventTrace.push('adapter_timeout');
      pagination.completion_reason = 'request_timeout';
      finish({ timed_out: true, error_phase: 'adapter' });
    }, request.timeout_ms || 25000);
  });
}

module.exports = { collectChart };

if (require.main === module) {
  const request = JSON.parse(process.argv[2]);
  collectChart(request).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`));
}
