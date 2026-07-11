/**
 * 海龟法则客户端回测引擎（dry-run，对齐 spec/turtle_strategy.spec.yaml）
 */
(function (global) {
  "use strict";

  const SYSTEM_PRESETS = {
    system_1: { entryPeriod: 20, exitPeriod: 10, atrPeriod: 20, stopN: 2.0 },
    system_2: { entryPeriod: 55, exitPeriod: 20, atrPeriod: 20, stopN: 2.0 },
  };

  function rollingMax(arr, period) {
    const out = new Array(arr.length).fill(null);
    for (let i = period; i < arr.length; i++) {
      let m = -Infinity;
      for (let j = i - period; j < i; j++) m = Math.max(m, arr[j]);
      out[i] = m;
    }
    return out;
  }

  function rollingMin(arr, period) {
    const out = new Array(arr.length).fill(null);
    for (let i = period; i < arr.length; i++) {
      let m = Infinity;
      for (let j = i - period; j < i; j++) m = Math.min(m, arr[j]);
      out[i] = m;
    }
    return out;
  }

  function computeTR(bars) {
    const tr = [];
    for (let i = 0; i < bars.length; i++) {
      const h = bars[i].high;
      const l = bars[i].low;
      if (i === 0) {
        tr.push(h - l);
        continue;
      }
      const pc = bars[i - 1].close;
      tr.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
    }
    return tr;
  }

  /** Wilder 平滑：ewm(alpha=1/period, adjust=false) */
  function wilderSmooth(values, period) {
    const alpha = 1 / period;
    const out = new Array(values.length).fill(null);
    if (!values.length) return out;
    out[0] = values[0];
    for (let i = 1; i < values.length; i++) {
      out[i] = alpha * values[i] + (1 - alpha) * out[i - 1];
    }
    return out;
  }

  function filterBars(bars, startDate, endDate) {
    return bars.filter((b) => {
      if (startDate && b.date < startDate) return false;
      if (endDate && b.date > endDate) return false;
      return true;
    });
  }

  function generateSignals(bars, params) {
    const entryPeriod = params.entryPeriod;
    const exitPeriod = params.exitPeriod;
    const atrPeriod = params.atrPeriod;
    const stopN = params.stopN;

    const highs = bars.map((b) => b.high);
    const lows = bars.map((b) => b.low);
    const closes = bars.map((b) => b.close);

    const entryHigh = rollingMax(highs, entryPeriod);
    const exitLow = rollingMin(lows, exitPeriod);
    const atrN = wilderSmooth(computeTR(bars), atrPeriod);

    const n = bars.length;
    const targetPosition = new Array(n).fill(0);
    const buySignal = new Array(n).fill(false);
    const sellSignal = new Array(n).fill(false);
    const stopPrice = new Array(n).fill(null);

    let inPosition = false;
    let activeStop = null;

    for (let i = 0; i < n; i++) {
      if (!inPosition) {
        if (entryHigh[i] != null && closes[i] > entryHigh[i]) {
          buySignal[i] = true;
          inPosition = true;
          const atrVal = atrN[i] ?? atrN[i - 1] ?? 0;
          activeStop = closes[i] - stopN * atrVal;
        }
      } else {
        stopPrice[i] = activeStop;
        let exit = false;
        if (exitLow[i] != null && closes[i] < exitLow[i]) exit = true;
        if (activeStop != null && closes[i] < activeStop) exit = true;
        if (exit) {
          sellSignal[i] = true;
          inPosition = false;
          activeStop = null;
        }
      }
      targetPosition[i] = inPosition ? 1 : 0;
    }

    return { entryHigh, exitLow, atrN, stopPrice, targetPosition, buySignal, sellSignal };
  }

  function lagPosition(targetPosition, lag) {
    return targetPosition.map((_, i) => (i >= lag ? targetPosition[i - lag] : 0));
  }

  function simulateStrategyEquity(bars, position, cfg) {
    const n = bars.length;
    let cash = cfg.initialCapital;
    let shares = 0;
    const equity = new Array(n);

    for (let i = 0; i < n; i++) {
      const prev = i > 0 ? position[i - 1] : 0;
      const tgt = position[i];
      const open = bars[i].open ?? bars[i].close;
      const close = bars[i].close;

      if (prev === 0 && tgt > 0 && shares === 0 && cash > 0) {
        const buyPx = open * (1 + cfg.slippageRate);
        const fee = cash * cfg.commissionRate;
        const spend = cash - fee;
        shares = spend / buyPx;
        cash = 0;
      }

      if (prev > 0 && tgt === 0 && shares > 0) {
        const sellPx = close * (1 - cfg.slippageRate);
        const gross = shares * sellPx;
        const fee = gross * cfg.commissionRate;
        cash = gross - fee;
        shares = 0;
      }

      equity[i] = cash + shares * close;
    }
    return equity;
  }

  function simulateBuyHoldEquity(bars, cfg) {
    const n = bars.length;
    if (!n) return [];
    const open0 = bars[0].open ?? bars[0].close;
    const buyPx = open0 * (1 + cfg.slippageRate);
    const fee0 = cfg.initialCapital * cfg.commissionRate;
    let shares = (cfg.initialCapital - fee0) / buyPx;
    const equity = new Array(n);

    for (let i = 0; i < n; i++) {
      const close = bars[i].close;
      if (i === n - 1) {
        const sellPx = close * (1 - cfg.slippageRate);
        const gross = shares * sellPx;
        equity[i] = gross * (1 - cfg.commissionRate);
      } else {
        equity[i] = shares * close;
      }
    }
    return equity;
  }

  function buildTrades(bars, buySignal, sellSignal, positionLag) {
    const trades = [];
    let openTrade = null;

    for (let i = 0; i < bars.length; i++) {
      const execIdx = i + positionLag;
      if (execIdx >= bars.length) break;

      if (buySignal[i] && !openTrade) {
        const px = bars[execIdx].open ?? bars[execIdx].close;
        openTrade = {
          entry_date: bars[execIdx].date,
          entry_price: px,
          signal_date: bars[i].date,
        };
      }

      if (sellSignal[i] && openTrade) {
        const px = bars[i].close;
        const ret = ((px - openTrade.entry_price) / openTrade.entry_price) * 100;
        const reason = "channel/stop";
        trades.push({
          trade_id: trades.length + 1,
          entry_date: openTrade.entry_date,
          entry_price: +openTrade.entry_price.toFixed(4),
          exit_date: bars[i].date,
          exit_price: +px.toFixed(4),
          exit_reason: reason,
          holding_days: daysBetween(openTrade.entry_date, bars[i].date),
          return_pct: +ret.toFixed(2),
        });
        openTrade = null;
      }
    }

    if (openTrade) {
      const last = bars[bars.length - 1];
      const px = last.close;
      const ret = ((px - openTrade.entry_price) / openTrade.entry_price) * 100;
      trades.push({
        trade_id: trades.length + 1,
        entry_date: openTrade.entry_date,
        entry_price: +openTrade.entry_price.toFixed(4),
        exit_date: null,
        exit_price: null,
        exit_reason: "end_of_backtest",
        holding_days: daysBetween(openTrade.entry_date, last.date),
        return_pct: +ret.toFixed(2),
      });
    }
    return trades;
  }

  function daysBetween(a, b) {
    const da = new Date(a);
    const db = new Date(b);
    return Math.max(0, Math.round((db - da) / 86400000));
  }

  function maxDrawdown(equity) {
    let peak = equity[0];
    let mdd = 0;
    for (const v of equity) {
      peak = Math.max(peak, v);
      mdd = Math.min(mdd, (v - peak) / peak);
    }
    return mdd * 100;
  }

  function sharpeRatio(equity, tradingDays) {
    const rets = [];
    for (let i = 1; i < equity.length; i++) {
      rets.push(equity[i] / equity[i - 1] - 1);
    }
    if (rets.length < 2) return 0;
    const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
    const var_ =
      rets.reduce((s, r) => s + (r - mean) ** 2, 0) / (rets.length - 1);
    const std = Math.sqrt(var_);
    if (std === 0) return 0;
    return (mean / std) * Math.sqrt(tradingDays);
  }

  function computeMetrics(equity, bhEquity, trades, initialCapital) {
    const final = equity[equity.length - 1];
    const bhFinal = bhEquity[bhEquity.length - 1];
    const wins = trades.filter((t) => t.return_pct > 0 && t.exit_date);
    const closed = trades.filter((t) => t.exit_date);
    const grossProfit = wins.reduce((s, t) => s + t.return_pct, 0);
    const losses = closed.filter((t) => t.return_pct <= 0);
    const grossLoss = losses.reduce((s, t) => s + Math.abs(t.return_pct), 0);

    return {
      cumulative_return_pct: +(((final / initialCapital - 1) * 100).toFixed(2)),
      buy_hold_return_pct: +(((bhFinal / initialCapital - 1) * 100).toFixed(2)),
      max_drawdown_pct: +maxDrawdown(equity).toFixed(2),
      sharpe_ratio: +sharpeRatio(equity, 252).toFixed(3),
      win_rate_pct: closed.length
        ? +(((wins.length / closed.length) * 100).toFixed(1))
        : 0,
      profit_factor: grossLoss > 0 ? +(grossProfit / grossLoss).toFixed(2) : null,
      total_trades: closed.length,
      final_equity: Math.round(final),
      bh_final_equity: Math.round(bhFinal),
    };
  }

  function validateParams(params) {
    if (params.entryPeriod <= params.exitPeriod) {
      return "入场周期应大于出场周期";
    }
    if (params.atrPeriod < 5) return "ATR 周期至少 5 日";
    if (params.stopN <= 0) return "止损倍数必须为正";
    return null;
  }

  function runBacktest(stock, options) {
    const params = { ...options.params };
    const err = validateParams(params);
    if (err) return { error: err };

    const cfg = {
      initialCapital: options.initialCapital ?? 100000,
      commissionRate: options.commissionRate ?? 0.0003,
      slippageRate: options.slippageRate ?? 0.0005,
      positionLag: options.positionLag ?? 1,
    };

    let bars = filterBars(stock.bars, options.startDate, options.endDate);
    const warmup = Math.max(params.entryPeriod, params.exitPeriod, params.atrPeriod) + 5;
    if (bars.length < warmup) {
      return { error: `数据不足，至少需要 ${warmup} 个交易日` };
    }

    const sig = generateSignals(bars, params);
    const position = lagPosition(sig.targetPosition, cfg.positionLag);
    const equity = simulateStrategyEquity(bars, position, cfg);
    const bhEquity = simulateBuyHoldEquity(bars, cfg);
    const trades = buildTrades(bars, sig.buySignal, sig.sellSignal, cfg.positionLag);
    const metrics = computeMetrics(equity, bhEquity, trades, cfg.initialCapital);

    return {
      stock: {
        stock_id: stock.stock_id,
        name: stock.name,
        code: stock.code,
        currency: stock.currency,
        unit: stock.unit,
      },
      date_window: {
        start: bars[0].date,
        end: bars[bars.length - 1].date,
        rows: bars.length,
      },
      params,
      metrics,
      series: {
        dates: bars.map((b) => b.date),
        ohlc: bars.map((b) => [b.open, b.close, b.low, b.high]),
        donchian_entry_high: sig.entryHigh,
        donchian_exit_low: sig.exitLow,
        atr_n: sig.atrN,
        stop_price: sig.stopPrice,
        equity,
        bh_equity: bhEquity,
        buySignal: sig.buySignal,
        sellSignal: sig.sellSignal,
      },
      trades,
    };
  }

  global.TurtleEngine = {
    SYSTEM_PRESETS,
    runBacktest,
    validateParams,
  };
})(window);
