/*
 * Bounded audit harness around the exact endenwer/tradingview-ws commit.
 * The pinned client owns the websocket transport; this wrapper observes its
 * public subscribe/send interface so series_completed and request_more_data
 * remain visible. The upstream resolver intentionally keeps adjustment=splits
 * unchanged and that limitation is recorded in every result.
 */

const crypto = require('crypto');

function sessionId() {
  return `cs_${crypto.randomBytes(8).toString('hex')}`;
}

async function collect(entryPath, request) {
  const { connect } = require(entryPath);
  const connection = await connect();
  const chartSession = sessionId();
  const batchSize = 5000;
  const maxPages = Number(request.max_pages || Math.ceil(Number(request.amount || batchSize) / batchSize));
  const eventTrace = [];
  const startedAt = new Date().toISOString();
  let settled = false;
  let timer;
  let pages = 0;
  let currentCandles = [];
  let completionReason = null;

  return new Promise((resolve) => {
    const finish = (status, error = null) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      connection.close().catch(() => {});
      resolve({
        request,
        server: 'prodata',
        started_at_utc: startedAt,
        finished_at_utc: new Date().toISOString(),
        status,
        error,
        event_trace: eventTrace,
        completion_reason: completionReason,
        pagination_pages: pages,
        adjustment: 'splits_hardcoded_upstream',
        periods: currentCandles,
        numeric_comparison: 'QUARANTINED_ADJUSTMENT_MISMATCH',
      });
    };

    connection.subscribe((event) => {
      eventTrace.push(event.name);
      if (event.name === 'timescale_update') {
        const series = event.params && event.params[1] && event.params[1].sds_1;
        const incoming = series && Array.isArray(series.s) ? series.s : [];
        const byTime = new Map(currentCandles.map((candle) => [candle.v[0], candle]));
        incoming.forEach((candle) => byTime.set(candle.v[0], candle));
        currentCandles = Array.from(byTime.values()).sort((left, right) => left.v[0] - right.v[0]);
        return;
      }
      if (event.name === 'symbol_error') {
        completionReason = 'symbol_error';
        finish('SYMBOL_ERROR', event.params);
        return;
      }
      if (event.name !== 'series_completed') return;
      if (currentCandles.length > 0 && currentCandles.length % batchSize === 0 && currentCandles.length < request.amount && pages < maxPages) {
        pages += 1;
        eventTrace.push('request_more_data');
        connection.send('request_more_data', [chartSession, 'sds_1', batchSize]);
        return;
      }
      completionReason = currentCandles.length ? 'series_completed' : 'series_completed_empty';
      if (currentCandles.length > request.amount) currentCandles = currentCandles.slice(0, request.amount);
      const periods = currentCandles.map((candle) => ({
        time: candle.v[0], open: candle.v[1], high: candle.v[2], low: candle.v[3], close: candle.v[4], volume: candle.v[5],
      }));
      currentCandles = periods;
      finish(periods.length ? 'AVAILABLE' : 'SERIES_COMPLETED_EMPTY');
    });

    connection.send('chart_create_session', [chartSession, '']);
    connection.send('resolve_symbol', [
      chartSession, 'sds_sym_0',
      '=' + JSON.stringify({ symbol: request.symbol, adjustment: 'splits' }),
    ]);
    connection.send('create_series', [chartSession, 'sds_1', 's0', 'sds_sym_0', String(request.timeframe), batchSize, '']);
    timer = setTimeout(() => {
      completionReason = 'bounded_timeout';
      finish('TRANSPORT_TIMEOUT', ['bounded endenwer timeout']);
    }, request.timeout_ms || 60000);
  });
}

if (require.main === module) {
  const entryPath = process.argv[2];
  const request = JSON.parse(process.argv[3]);
  collect(entryPath, request).then((result) => process.stdout.write(`${JSON.stringify(result)}\n`));
}

module.exports = { collect };
