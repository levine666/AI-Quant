/**
 * 浏览器端双均线回测引擎（对齐 quant_backtest/ Python 实现）
 */
const BacktestEngine = (() => {
  const DEFAULTS = {
    initialCapital: 100000,
    tradingDays: 252,
    commissionRate: 0.0003,
    slippageRate: 0.0005,
    positionLag: 1,
  };

  function sma(values, period) {
    const out = new Array(values.length).fill(null);
    let sum = 0;
    for (let i = 0; i < values.length; i++) {
      sum += values[i];
      if (i >= period) sum -= values[i - period];
      if (i >= period - 1) out[i] = sum / period;
    }
    return out;
  }

  function applyDateWindow(rows, startDate, endDate) {
    return rows.filter((r) => {
      if (startDate && r.date < startDate) return false;
      if (endDate && r.date > endDate) return false;
      return true;
    });
  }

  function generateSignals(rows, short, long) {
    const close = rows.map((r) => r.close);
    const open = rows.map((r) => (r.open != null && !Number.isNaN(r.open) ? r.open : r.close));
    const maShort = sma(close, short);
    const maLong = sma(close, long);

    const targetPosition = new Array(rows.length).fill(0);
    const buySignal = new Array(rows.length).fill(false);
    const sellSignal = new Array(rows.length).fill(false);

    for (let i = 0; i < rows.length; i++) {
      if (maShort[i] == null || maLong[i] == null) continue;
      targetPosition[i] = maShort[i] > maLong[i] ? 1 : 0;
      if (i > 0 && maShort[i - 1] != null && maLong[i - 1] != null) {
        buySignal[i] = maShort[i] > maLong[i] && maShort[i - 1] <= maLong[i - 1];
        sellSignal[i] = maShort[i] < maLong[i] && maShort[i - 1] >= maLong[i - 1];
      }
    }

    return rows.map((r, i) => ({
      date: r.date,
      close: close[i],
      open: open[i],
      ma_short: maShort[i],
      ma_long: maLong[i],
      target_position: targetPosition[i],
      buy_signal: buySignal[i],
      sell_signal: sellSignal[i],
    }));
  }

  function buyCost(notional, cfg) {
    const fee = notional * cfg.commissionRate;
    return { spend: notional - fee, fee };
  }

  function sellProceeds(gross, cfg) {
    const fee = gross * cfg.commissionRate;
    return { cash: gross - fee, fee };
  }

  function simulateStrategyEquity(signed, position, cfg) {
    const n = signed.length;
    const equity = new Array(n).fill(0);
    let cash = cfg.initialCapital;
    let shares = 0;

    for (let i = 0; i < n; i++) {
      const prev = i > 0 ? position[i - 1] : 0;
      const tgt = position[i];
      const openP = signed[i].open;
      const closeP = signed[i].close;

      if (prev === 0 && tgt > 0 && shares === 0 && cash > 0) {
        const buyPx = openP * (1 + cfg.slippageRate);
        const { spend } = buyCost(cash, cfg);
        shares = spend / buyPx;
        cash = 0;
      }

      if (prev > 0 && tgt === 0 && shares > 0) {
        const sellPx = closeP * (1 - cfg.slippageRate);
        const gross = shares * sellPx;
        cash = sellProceeds(gross, cfg).cash;
        shares = 0;
      }

      equity[i] = cash + shares * closeP;
    }
    return equity;
  }

  function simulateBuyHoldEquity(signed, cfg) {
    const n = signed.length;
    if (!n) return [];
    const openP = signed[0].open * (1 + cfg.slippageRate);
    const { spend } = buyCost(cfg.initialCapital, cfg);
    const shares = spend / openP;
    const equity = new Array(n).fill(0);

    for (let i = 0; i < n; i++) {
      if (i === n - 1) {
        const sellPx = signed[i].close * (1 - cfg.slippageRate);
        equity[i] = sellProceeds(shares * sellPx, cfg).cash;
      } else {
        equity[i] = shares * signed[i].close;
      }
    }
    return equity;
  }

  function computeMetrics(signed, equity, bhEquity, cfg) {
    const n = equity.length;
    const stratRet = equity.map((v, i) => (i === 0 ? 0 : v / equity[i - 1] - 1));
    let rollMax = equity[0];
    let mdd = 0;
    for (let i = 0; i < n; i++) {
      rollMax = Math.max(rollMax, equity[i]);
      const dd = (equity[i] - rollMax) / rollMax;
      if (dd < mdd) mdd = dd;
    }

    const mean = stratRet.slice(1).reduce((a, b) => a + b, 0) / Math.max(1, n - 1);
    const variance =
      stratRet.slice(1).reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(1, n - 2);
    const vol = Math.sqrt(variance);
    const sharpe = vol > 0 ? (mean / vol) * Math.sqrt(cfg.tradingDays) : 0;

    let buyCount = 0;
    let sellCount = 0;
    signed.forEach((r) => {
      if (r.buy_signal) buyCount++;
      if (r.sell_signal) sellCount++;
    });

    const cumRet = equity[n - 1] / cfg.initialCapital - 1;
    const bhCumRet = bhEquity[n - 1] / cfg.initialCapital - 1;

    return {
      cumulative_return_pct: round(cumRet * 100, 2),
      buy_hold_return_pct: round(bhCumRet * 100, 2),
      max_drawdown_pct: round(mdd * 100, 2),
      sharpe_ratio: round(sharpe, 3),
      final_equity: round(equity[n - 1], 2),
      final_bh_equity: round(bhEquity[n - 1], 2),
      start_date: signed[0].date,
      end_date: signed[n - 1].date,
      rows: n,
      buy_count: buyCount,
      sell_count: sellCount,
      trade_count: buyCount + sellCount,
    };
  }

  function round(v, d) {
    const f = 10 ** d;
    return Math.round(v * f) / f;
  }

  function run(rows, params, cfgOverrides = {}) {
    const cfg = { ...DEFAULTS, ...cfgOverrides };
    const { short, long } = params;
    if (short >= long) throw new Error(`short(${short}) 必须小于 long(${long})`);
    if (rows.length < 2) throw new Error("回测区间至少需要 2 个交易日");

    const signed = generateSignals(rows, short, long);
    const position = signed.map((r, i) => {
      const lag = cfg.positionLag;
      if (i < lag) return 0;
      return signed[i - lag].target_position;
    });

    const equity = simulateStrategyEquity(signed, position, cfg);
    const bhEquity = simulateBuyHoldEquity(signed, cfg);

    const enriched = signed.map((r, i) => ({
      ...r,
      position: position[i],
      equity: equity[i],
      bh_equity: bhEquity[i],
      strategy_ret: i === 0 ? 0 : equity[i] / equity[i - 1] - 1,
    }));

    const metrics = computeMetrics(enriched, equity, bhEquity, cfg);

    return {
      strategyName: `DualMA(${short},${long})`,
      params: { short, long },
      config: cfg,
      metrics,
      rows: enriched,
    };
  }

  function runParamScan(rows, grid, cfgOverrides = {}) {
    const results = [];
    for (const short of grid.short) {
      for (const long of grid.long) {
        if (short >= long) continue;
        try {
          const r = run(rows, { short, long }, cfgOverrides);
          results.push({
            short,
            long,
            strategy: r.strategyName,
            ...r.metrics,
          });
        } catch (_) {
          /* skip invalid */
        }
      }
    }
    results.sort((a, b) => b.sharpe_ratio - a.sharpe_ratio);
    return {
      combinations: results.length,
      best: results[0] || null,
      results,
    };
  }

  return {
    DEFAULTS,
    applyDateWindow,
    run,
    runParamScan,
  };
})();
