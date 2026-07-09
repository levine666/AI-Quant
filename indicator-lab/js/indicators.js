/**
 * 技术指标计算（与 scripts/indicators.py 算法一致）
 * Wilder 平滑: RSI / ATR；EMA: MACD；SMA+STD: BOLL
 */

function wilderEwm(values, period) {
  const alpha = 1 / period;
  const out = new Array(values.length);
  for (let i = 0; i < values.length; i++) {
    const v = Number(values[i]);
    if (Number.isNaN(v)) {
      out[i] = NaN;
      continue;
    }
    if (i === 0 || Number.isNaN(out[i - 1])) out[i] = v;
    else out[i] = alpha * v + (1 - alpha) * out[i - 1];
  }
  return out;
}

function ema(values, span) {
  const k = 2 / (span + 1);
  const out = new Array(values.length);
  for (let i = 0; i < values.length; i++) {
    const v = Number(values[i]);
    if (Number.isNaN(v)) {
      out[i] = NaN;
      continue;
    }
    if (i === 0 || Number.isNaN(out[i - 1])) out[i] = v;
    else out[i] = v * k + out[i - 1] * (1 - k);
  }
  return out;
}

function rollingMean(values, period) {
  const out = new Array(values.length).fill(NaN);
  for (let i = period - 1; i < values.length; i++) {
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += values[j];
    out[i] = sum / period;
  }
  return out;
}

function rollingStd(values, period) {
  const out = new Array(values.length).fill(NaN);
  if (period <= 1) return out;
  for (let i = period - 1; i < values.length; i++) {
    const slice = values.slice(i - period + 1, i + 1);
    const mean = slice.reduce((a, b) => a + b, 0) / period;
    const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / (period - 1);
    out[i] = Math.sqrt(variance);
  }
  return out;
}

function computeRSI(close, period = 14) {
  const delta = close.map((v, i) => (i === 0 ? 0 : v - close[i - 1]));
  const gain = delta.map((d) => Math.max(d, 0));
  const loss = delta.map((d) => Math.max(-d, 0));
  const avgGain = wilderEwm(gain, period);
  const avgLoss = wilderEwm(loss, period);
  return avgGain.map((g, i) => {
    const l = avgLoss[i];
    if (Number.isNaN(g) || Number.isNaN(l)) return NaN;
    if (l === 0) return g === 0 ? 50 : 100;
    const rs = g / l;
    return 100 - 100 / (1 + rs);
  });
}

function computeMACD(close, fast = 12, slow = 26, signal = 9) {
  const emaFast = ema(close, fast);
  const emaSlow = ema(close, slow);
  const dif = emaFast.map((v, i) => v - emaSlow[i]);
  const dea = ema(dif, signal);
  const hist = dif.map((v, i) => v - dea[i]);
  return { dif, dea, hist };
}

function computeBollinger(close, period = 20, stdMultiplier = 2) {
  const mid = rollingMean(close, period);
  const std = rollingStd(close, period);
  const upper = mid.map((m, i) => (Number.isNaN(m) ? NaN : m + stdMultiplier * std[i]));
  const lower = mid.map((m, i) => (Number.isNaN(m) ? NaN : m - stdMultiplier * std[i]));
  const width = mid.map((m, i) =>
    Number.isNaN(m) || m === 0 ? NaN : (upper[i] - lower[i]) / m
  );
  return { mid, upper, lower, width };
}

function computeATR(high, low, close, period = 14) {
  const tr = high.map((h, i) => {
    if (i === 0) return h - low[i];
    const prev = close[i - 1];
    return Math.max(h - low[i], Math.abs(h - prev), Math.abs(low[i] - prev));
  });
  return wilderEwm(tr, period);
}

function addAllIndicators(rows, params) {
  const close = rows.map((r) => r.close);
  const high = rows.map((r) => r.high);
  const low = rows.map((r) => r.low);

  const rsi = computeRSI(close, params.rsi.period);
  const macd = computeMACD(close, params.macd.fast, params.macd.slow, params.macd.signal);
  const boll = computeBollinger(close, params.boll.period, params.boll.std_multiplier);
  const atr = computeATR(high, low, close, params.atr.period);

  return rows.map((row, i) => ({
    ...row,
    rsi: rsi[i],
    macd_dif: macd.dif[i],
    macd_dea: macd.dea[i],
    macd_hist: macd.hist[i],
    boll_mid: boll.mid[i],
    boll_upper: boll.upper[i],
    boll_lower: boll.lower[i],
    boll_width: boll.width[i],
    atr: atr[i],
  }));
}

window.IndicatorEngine = {
  computeRSI,
  computeMACD,
  computeBollinger,
  computeATR,
  addAllIndicators,
};
