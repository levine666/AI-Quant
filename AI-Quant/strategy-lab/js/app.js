/**
 * Strategy Lab 主控制器
 */
const STORAGE_KEY = "strategy-lab-v1";

const state = {
  config: null,
  stocks: [],
  stock: null,
  rawRows: [],
  result: null,
  scan: null,
};

function $(id) {
  return document.getElementById(id);
}

function fmt(v, digits = 2) {
  if (v == null || Number.isNaN(v)) return "—";
  return Number(v).toFixed(digits);
}

function fmtPct(v) {
  if (v == null || Number.isNaN(v)) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${fmt(v)}%`;
}

function showToast(msg, type = "info") {
  const el = $("toast");
  el.textContent = msg;
  el.className = `toast toast-${type}`;
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => el.classList.add("hidden"), 2800);
}

function setLoading(show) {
  $("loading").classList.toggle("hidden", !show);
}

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map((h) => h.trim().replace(/^\uFEFF/, ""));
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(",");
    if (parts.length < headers.length) continue;
    const row = {};
    headers.forEach((h, j) => {
      const v = parts[j].trim();
      row[h] = h === "date" ? v : v === "" ? NaN : Number(v);
    });
    if (!row.date || Number.isNaN(row.close)) continue;
    rows.push(row);
  }
  return rows.sort((a, b) => a.date.localeCompare(b.date));
}

function readConfigFromUI() {
  const short = clampInt($("rngShort").value, 2, 30);
  const long = clampInt($("rngLong").value, 5, 90);
  return {
    short,
    long,
    startDate: $("startDate").value || null,
    endDate: $("endDate").value || null,
    commissionRate: clampFloat($("commissionRate").value, 0, 0.01),
    slippageRate: clampFloat($("slippageRate").value, 0, 0.01),
    initialCapital: state.config?.defaults?.initial_capital ?? 100000,
    tradingDays: state.config?.defaults?.trading_days ?? 252,
    positionLag: state.config?.defaults?.position_lag ?? 1,
  };
}

function clampInt(v, min, max) {
  const n = Math.round(Number(v));
  if (Number.isNaN(n)) return min;
  return Math.min(max, Math.max(min, n));
}

function clampFloat(v, min, max) {
  const n = Number(v);
  if (Number.isNaN(n)) return min;
  return Math.min(max, Math.max(min, n));
}

function getFilteredRows(cfg) {
  return BacktestEngine.applyDateWindow(state.rawRows, cfg.startDate, cfg.endDate);
}

function updateBanner(cfg, metrics) {
  const s = state.stock;
  if (!s || !metrics) return;
  const marketTag = s.market === "港股" ? "tag-hk" : "tag-a";
  $("stockBanner").innerHTML = `
    <span class="name">${s.name}</span>
    <span class="tag ${marketTag}">${s.market} ${s.code}</span>
    <span class="tag tag-strat">DualMA(${cfg.short},${cfg.long})</span>
    <span>${metrics.start_date} ~ ${metrics.end_date} · ${metrics.rows} 交易日 · 初始 ${cfg.initialCapital.toLocaleString()} ${s.unit}</span>
  `;
}

function updateMetrics(metrics) {
  const setMetric = (id, value, subId, sub) => {
    const el = $(id);
    el.textContent = value;
    el.parentElement.classList.remove("positive", "negative", "neutral");
    if (id === "metricReturn") {
      el.parentElement.classList.add(metrics.cumulative_return_pct >= 0 ? "positive" : "negative");
    } else if (id === "metricMdd") {
      el.parentElement.classList.add("negative");
    } else {
      el.parentElement.classList.add("neutral");
    }
    if (subId) $(subId).textContent = sub;
  };

  setMetric("metricReturn", fmtPct(metrics.cumulative_return_pct), "metricReturnSub", `净值 ${metrics.final_equity.toLocaleString()}`);
  setMetric("metricBh", fmtPct(metrics.buy_hold_return_pct), "metricBhSub", `净值 ${metrics.final_bh_equity.toLocaleString()}`);
  setMetric("metricMdd", `${fmt(metrics.max_drawdown_pct)}%`, "metricMddSub", "风险暴露");
  setMetric("metricSharpe", fmt(metrics.sharpe_ratio, 3), "metricSharpeSub", "rf = 0 · 252 日年化");

  $("priceCaption").textContent = `▲ 买入 ${metrics.buy_count} 次 · ▼ 卖出 ${metrics.sell_count} 次`;
}

function updateTradeTable(result, cfg) {
  const tbody = $("tradeTable");
  const signals = result.rows
    .filter((r) => r.buy_signal || r.sell_signal)
    .slice(-8)
    .reverse();

  if (!signals.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted)">区间内无交叉信号</td></tr>';
    return;
  }

  tbody.innerHTML = signals
    .map((r) => {
      const sig = r.buy_signal
        ? '<span class="sig-buy">金叉买入</span>'
        : '<span class="sig-sell">死叉卖出</span>';
      return `<tr>
        <td>${r.date}</td>
        <td>${sig}</td>
        <td class="num">${fmt(r.close)}</td>
        <td class="num">${r.ma_short != null ? fmt(r.ma_short) : "—"}</td>
        <td class="num">${r.ma_long != null ? fmt(r.ma_long) : "—"}</td>
      </tr>`;
    })
    .join("");

  $("tradeCaption").textContent = `MA${cfg.short}/${cfg.long}`;
}

function updateHeatCaption(scan) {
  const best = scan?.best;
  if (!best) {
    $("heatCaption").textContent = "无有效组合";
    return;
  }
  $("heatCaption").textContent = `${scan.combinations} 组 · 最优 MA${best.short}/${best.long} · 夏普 ${fmt(best.sharpe_ratio, 2)}`;
}

function runBacktest() {
  const cfg = readConfigFromUI();
  if (cfg.short >= cfg.long) {
    showToast("短均线周期必须小于长均线", "error");
    return;
  }

  const rows = getFilteredRows(cfg);
  if (rows.length < cfg.long + 2) {
    showToast("数据不足，请扩大回测区间", "error");
    return;
  }

  try {
    const engineCfg = {
      initialCapital: cfg.initialCapital,
      tradingDays: cfg.tradingDays,
      commissionRate: cfg.commissionRate,
      slippageRate: cfg.slippageRate,
      positionLag: cfg.positionLag,
    };

    state.result = BacktestEngine.run(rows, { short: cfg.short, long: cfg.long }, engineCfg);
    state.scan = BacktestEngine.runParamScan(rows, state.config.param_scan.param_grid, engineCfg);

    updateBanner(cfg, state.result.metrics);
    updateMetrics(state.result.metrics);
    updateTradeTable(state.result, cfg);
    updateHeatCaption(state.scan);

    StrategyCharts.renderPrice(state.result, cfg.short, cfg.long);
    StrategyCharts.renderEquity(state.result);
    StrategyCharts.renderHeatmap(state.scan, state.config.param_scan.param_grid);

    saveState();
    showToast("回测完成");
  } catch (e) {
    showToast(e.message || "回测失败", "error");
  }
}

function populateStockSelect() {
  const select = $("stockSelect");
  select.innerHTML = state.stocks
    .map((s) => `<option value="${s.id}">${s.name} (${s.ts_code})</option>`)
    .join("");

  const qs = new URLSearchParams(location.search).get("stock");
  if (qs && state.stocks.some((s) => s.id === qs)) select.value = qs;
  return state.stocks.find((s) => s.id === select.value) || state.stocks[0];
}

async function loadStockData(stock) {
  setLoading(true);
  try {
    const res = await fetch(stock.csv);
    if (!res.ok) throw new Error(`无法加载 ${stock.csv}`);
    state.rawRows = parseCSV(await res.text());
    if (state.rawRows.length < 20) throw new Error("数据行数过少");
    state.stock = stock;

    const dates = state.rawRows.map((r) => r.date);
    if (!$("startDate").value) $("startDate").value = dates[0];
    if (!$("endDate").value) $("endDate").value = dates[dates.length - 1];

    runBacktest();
  } catch (e) {
    showToast(e.message || "数据加载失败", "error");
  } finally {
    setLoading(false);
  }
}

function saveState() {
  try {
    const cfg = readConfigFromUI();
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        stockId: state.stock?.id,
        startDate: cfg.startDate,
        endDate: cfg.endDate,
        short: cfg.short,
        long: cfg.long,
        commissionRate: cfg.commissionRate,
        slippageRate: cfg.slippageRate,
      })
    );
  } catch (_) {
    /* ignore */
  }
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

function applyDefaults() {
  const d = state.config.defaults;
  $("rngShort").value = d.strategy.short;
  $("valShort").textContent = d.strategy.short;
  $("rngLong").value = d.strategy.long;
  $("valLong").textContent = d.strategy.long;
  $("commissionRate").value = d.commission_rate;
  $("slippageRate").value = d.slippage_rate;
  if (d.date_window?.start_date) $("startDate").value = d.date_window.start_date;
  if (d.date_window?.end_date) $("endDate").value = d.date_window.end_date;
}

function bindEvents() {
  $("rngShort").addEventListener("input", (e) => {
    $("valShort").textContent = e.target.value;
  });
  $("rngLong").addEventListener("input", (e) => {
    $("valLong").textContent = e.target.value;
  });
  $("btnRun").addEventListener("click", runBacktest);
  $("stockSelect").addEventListener("change", async () => {
    const stock = state.stocks.find((s) => s.id === $("stockSelect").value);
    if (stock) await loadStockData(stock);
  });
  window.addEventListener("resize", () => StrategyCharts.resizeAll());
}

async function init() {
  setLoading(true);
  try {
    const res = await fetch("assets/config.json");
    if (!res.ok) throw new Error("无法加载 config.json");
    state.config = await res.json();
    state.stocks = state.config.stocks;

    applyDefaults();
    const saved = loadState();
    if (saved) {
      if (saved.short) {
        $("rngShort").value = saved.short;
        $("valShort").textContent = saved.short;
      }
      if (saved.long) {
        $("rngLong").value = saved.long;
        $("valLong").textContent = saved.long;
      }
      if (saved.startDate) $("startDate").value = saved.startDate;
      if (saved.endDate) $("endDate").value = saved.endDate;
      if (saved.commissionRate != null) $("commissionRate").value = saved.commissionRate;
      if (saved.slippageRate != null) $("slippageRate").value = saved.slippageRate;
    }

    bindEvents();
    const stock = populateStockSelect();
    if (saved?.stockId) {
      const s = state.stocks.find((x) => x.id === saved.stockId);
      if (s) {
        $("stockSelect").value = s.id;
        await loadStockData(s);
        return;
      }
    }
    if (stock) await loadStockData(stock);
  } catch (e) {
    showToast(e.message || "初始化失败", "error");
  } finally {
    setLoading(false);
  }
}

document.addEventListener("DOMContentLoaded", init);
