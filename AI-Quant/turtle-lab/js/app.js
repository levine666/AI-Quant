/**
 * Turtle Lab — 静态 CSV + JS 引擎（Pages 部署）；可选 /api 增强
 */
(function () {
  "use strict";

  const COLORS = {
    text: "#8b98b3", grid: "#1b2438", border: "#243049",
    up: "#ef5350", down: "#26a69a", entry: "#5b8def", exit: "#ef5350",
    stop: "#f5a623", strat: "#26a69a", bh: "#90a4ae", atr: "#00897b",
  };

  let config = null;
  let stockCache = {};
  let useApi = false;
  const charts = {};

  const els = {
    stock: document.getElementById("stockSelect"),
    system: document.querySelectorAll('input[name="system"]'),
    entryPeriod: document.getElementById("entryPeriod"),
    exitPeriod: document.getElementById("exitPeriod"),
    atrPeriod: document.getElementById("atrPeriod"),
    stopN: document.getElementById("stopN"),
    stopNVal: document.getElementById("stopNVal"),
    startDate: document.getElementById("startDate"),
    endDate: document.getElementById("endDate"),
    runBtn: document.getElementById("runBtn"),
    paramError: document.getElementById("paramError"),
    dataBadge: document.getElementById("dataBadge"),
    stockBanner: document.getElementById("stockBanner"),
    metrics: document.getElementById("metrics"),
    tradesBody: document.getElementById("tradesBody"),
  };

  function hideLoading() {
    document.getElementById("loading")?.classList.add("hidden");
  }

  function applyPreset(system) {
    const p = TurtleEngine.SYSTEM_PRESETS[system];
    if (!p) return;
    els.entryPeriod.value = p.entryPeriod;
    els.exitPeriod.value = p.exitPeriod;
    els.atrPeriod.value = p.atrPeriod;
    els.stopN.value = p.stopN;
    els.stopNVal.textContent = p.stopN.toFixed(1);
  }

  async function loadStock(id) {
    if (stockCache[id]) return stockCache[id];
    const meta = config.stocks.find((s) => s.id === id);
    const res = await fetch(meta.csv);
    if (!res.ok) throw new Error("无法加载 " + meta.csv);
    const bars = parseCSV(await res.text()).map((r) => ({
      date: r.date,
      open: r.open ?? r.close,
      high: r.high ?? r.close,
      low: r.low ?? r.close,
      close: r.close,
      volume: r.volume ?? 0,
    }));
    const stock = {
      stock_id: id,
      name: meta.name,
      code: meta.code,
      market: meta.market,
      unit: meta.unit,
      bars,
      last_complete_date: bars[bars.length - 1].date,
      date_range: { start: bars[0].date, end: bars[bars.length - 1].date },
    };
    stockCache[id] = stock;
    return stock;
  }

  function readBody() {
    const system = [...els.system].find((r) => r.checked)?.value || "system_1";
    return {
      stock_id: els.stock.value,
      start_date: els.startDate.value || null,
      end_date: els.endDate.value || null,
      system,
      params: {
        entry_period: +els.entryPeriod.value,
        exit_period: +els.exitPeriod.value,
        atr_period: +els.atrPeriod.value,
        stop_n_multiplier: +els.stopN.value,
      },
      engine: {
        initial_capital: config.defaults.initial_capital,
        commission_rate: config.defaults.commission_rate,
        slippage_rate: config.defaults.slippage_rate,
      },
    };
  }

  function toEngineParams(body) {
    const p = body.params;
    return {
      entryPeriod: p.entry_period,
      exitPeriod: p.exit_period,
      atrPeriod: p.atr_period,
      stopN: p.stop_n_multiplier,
    };
  }

  async function runBacktest() {
    const body = readBody();
    els.paramError.textContent = "";
    let result;

    if (useApi) {
      const res = await fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      result = await res.json();
    } else {
      const stock = await loadStock(body.stock_id);
      const err = TurtleEngine.validateParams(toEngineParams(body));
      if (err) { els.paramError.textContent = err; return; }
      result = TurtleEngine.runBacktest(stock, {
        params: toEngineParams(body),
        startDate: body.start_date,
        endDate: body.end_date,
        initialCapital: body.engine.initial_capital,
        commissionRate: body.engine.commission_rate,
        slippageRate: body.engine.slippage_rate,
      });
    }

    if (result.error) { els.paramError.textContent = result.error; return; }
    render(result);
  }

  function render(result) {
    const m = result.metrics;
    const unit = result.stock.unit;
    els.dataBadge.textContent = "截至 " + result.date_window.end;
    els.stockBanner.textContent = `${result.stock.name} · ${result.date_window.start} ~ ${result.date_window.end}`;
    els.metrics.innerHTML = [
      ["策略收益", (m.cumulative_return_pct > 0 ? "+" : "") + m.cumulative_return_pct + "%"],
      ["买入持有", (m.buy_hold_return_pct > 0 ? "+" : "") + m.buy_hold_return_pct + "%"],
      ["最大回撤", m.max_drawdown_pct + "%"],
      ["夏普", m.sharpe_ratio],
      ["胜率", (m.win_rate_pct ?? 0) + "%"],
      ["交易", m.total_trades ?? 0],
    ].map(([l, v]) => `<div class="metric"><div class="label">${l}</div><div class="value">${v}</div></div>`).join("");

    els.tradesBody.innerHTML = (result.trades || []).slice(-8).reverse().map((t) =>
      `<tr><td>${t.entry_date}</td><td>${t.exit_date || "—"}</td><td>${t.entry_price}</td><td>${t.exit_price ?? "—"}</td><td>${t.return_pct}%</td></tr>`
    ).join("") || "<tr><td colspan='5'>无交易</td></tr>";

    const s = result.series;
    const dates = s.dates;
    charts.kline.setOption({
      backgroundColor: "transparent",
      grid: { left: 48, right: 16, top: 28, bottom: 48 },
      tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: dates, axisLabel: { fontSize: 10, color: COLORS.text } },
      yAxis: { scale: true, splitLine: { lineStyle: { color: COLORS.grid } } },
      dataZoom: [{ type: "inside" }, { type: "slider", height: 16, bottom: 4 }],
      series: [
        { type: "candlestick", data: s.ohlc, itemStyle: { color: COLORS.up, color0: COLORS.down } },
        { type: "line", name: "入场上轨", data: s.donchian_entry_high, showSymbol: false, lineStyle: { type: "dashed", color: COLORS.entry } },
        { type: "line", name: "出场下轨", data: s.donchian_exit_low, showSymbol: false, lineStyle: { type: "dotted", color: COLORS.exit } },
      ],
    }, true);
    charts.equity.setOption({
      grid: { left: 48, right: 12, top: 20, bottom: 24 },
      xAxis: { type: "category", data: dates, show: false },
      yAxis: { scale: true, splitLine: { lineStyle: { color: COLORS.grid } } },
      series: [
        { type: "line", data: s.equity, showSymbol: false, lineStyle: { color: COLORS.strat, width: 2 } },
        { type: "line", data: s.bh_equity, showSymbol: false, lineStyle: { type: "dashed", color: COLORS.bh } },
      ],
    }, true);
    charts.atr.setOption({
      grid: { left: 48, right: 12, top: 20, bottom: 24 },
      xAxis: { type: "category", data: dates, show: false },
      yAxis: { scale: true, splitLine: { lineStyle: { color: COLORS.grid } } },
      series: [{ type: "line", data: s.atr_n, showSymbol: false, lineStyle: { color: COLORS.atr } }],
    }, true);
  }

  function syncDates(stock) {
    els.endDate.max = stock.last_complete_date;
    els.endDate.value = stock.last_complete_date;
    const d = new Date(stock.last_complete_date);
    d.setFullYear(d.getFullYear() - 1);
    const s = d.toISOString().slice(0, 10);
    els.startDate.value = s < stock.date_range.start ? stock.date_range.start : s;
  }

  async function init() {
    if (!guardFileProtocol()) return;
    try {
      const h = await fetch("/api/health", { method: "GET" });
      useApi = h.ok;
    } catch { useApi = false; }

    config = await fetch("assets/config.json").then((r) => r.json());
    els.stock.innerHTML = config.stocks.map((s) =>
      `<option value="${s.id}">${s.name} (${s.code})</option>`
    ).join("");
    els.stock.value = "smic_hk";

    charts.kline = echarts.init(document.getElementById("chartKline"));
    charts.equity = echarts.init(document.getElementById("chartEquity"));
    charts.atr = echarts.init(document.getElementById("chartAtr"));

    applyPreset("system_1");
    const stock = await loadStock(els.stock.value);
    syncDates(stock);

    els.stock.addEventListener("change", async () => {
      syncDates(await loadStock(els.stock.value));
      runBacktest();
    });
    [...els.system].forEach((r) => r.addEventListener("change", () => {
      if (r.checked && r.value !== "custom") applyPreset(r.value);
      runBacktest();
    }));
    ["entryPeriod", "exitPeriod", "atrPeriod", "startDate", "endDate"].forEach((id) =>
      document.getElementById(id).addEventListener("change", runBacktest)
    );
    els.stopN.addEventListener("input", (e) => {
      els.stopNVal.textContent = (+e.target.value).toFixed(1);
      document.getElementById("systemCustom").checked = true;
    });
    els.stopN.addEventListener("change", runBacktest);
    els.runBtn.addEventListener("click", runBacktest);
    document.querySelectorAll("[data-preset]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const st = await loadStock(els.stock.value);
        if (btn.dataset.preset === "all") els.startDate.value = st.date_range.start;
        else {
          const d = new Date(st.last_complete_date);
          d.setFullYear(d.getFullYear() - 1);
          els.startDate.value = d.toISOString().slice(0, 10);
        }
        els.endDate.value = st.last_complete_date;
        runBacktest();
      });
    });
    window.addEventListener("resize", () => Object.values(charts).forEach((c) => c?.resize()));

    await runBacktest();
    hideLoading();
  }

  init().catch((e) => {
    document.getElementById("loading").textContent = "加载失败: " + e.message;
  });
})();
