/**
 * Turtle Lab 看板 UI — 连接 Python /api 回测引擎
 */
(function () {
  "use strict";

  const COLORS = {
    text: "#8b98b3",
    grid: "#1b2438",
    border: "#243049",
    up: "#ef5350",
    down: "#26a69a",
    entry: "#5b8def",
    exit: "#ef5350",
    stop: "#f5a623",
    strat: "#26a69a",
    bh: "#90a4ae",
    atr: "#00897b",
  };

  const SYSTEM_PRESETS = {
    system_1: { entry_period: 20, exit_period: 10, atr_period: 20, stop_n_multiplier: 2.0 },
    system_2: { entry_period: 55, exit_period: 20, atr_period: 20, stop_n_multiplier: 2.0 },
  };

  const charts = {};
  let manifest = null;
  let loading = false;

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
    initialCapital: document.getElementById("initialCapital"),
    commission: document.getElementById("commission"),
    slippage: document.getElementById("slippage"),
    runBtn: document.getElementById("runBtn"),
    refreshBtn: document.getElementById("refreshBtn"),
    paramError: document.getElementById("paramError"),
    dataBadge: document.getElementById("dataBadge"),
    stockBanner: document.getElementById("stockBanner"),
    metrics: document.getElementById("metrics"),
    tradesBody: document.getElementById("tradesBody"),
    chartCaption: document.getElementById("chartCaption"),
    toast: document.getElementById("toast"),
    statusDot: document.getElementById("statusDot"),
  };

  async function api(path, options) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await res.json();
    if (!res.ok && !data.error) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    return data;
  }

  function getSelectedSystem() {
    for (const r of els.system) if (r.checked) return r.value;
    return "system_1";
  }

  function applySystemPreset(system) {
    const p = SYSTEM_PRESETS[system];
    if (!p) return;
    els.entryPeriod.value = p.entry_period;
    els.exitPeriod.value = p.exit_period;
    els.atrPeriod.value = p.atr_period;
    els.stopN.value = p.stop_n_multiplier;
    els.stopNVal.textContent = p.stop_n_multiplier.toFixed(1);
  }

  function validateParamsLocal() {
    const entry = +els.entryPeriod.value;
    const exit = +els.exitPeriod.value;
    if (entry <= exit) return "入场周期应大于出场周期";
    if (+els.atrPeriod.value < 5) return "ATR 周期至少 5 日";
    if (+els.stopN.value <= 0) return "止损倍数必须为正";
    return null;
  }

  function fmtPct(v, signed) {
    if (v == null || Number.isNaN(v)) return "—";
    return (signed && v > 0 ? "+" : "") + Number(v).toFixed(2) + "%";
  }

  function metricClass(v, invert) {
    if (v == null) return "neutral";
    if (invert) return v <= 0 ? "positive" : "negative";
    return v >= 0 ? "positive" : "negative";
  }

  function renderMetrics(m, unit) {
    const cards = [
      {
        label: "策略累计回报",
        value: fmtPct(m.cumulative_return_pct, true),
        sub: `净值 ${Number(m.final_equity).toLocaleString()} ${unit}`,
        cls: metricClass(m.cumulative_return_pct),
      },
      {
        label: "买入持有基准",
        value: fmtPct(m.buy_hold_return_pct, true),
        sub: `净值 ${Number(m.final_bh_equity ?? m.bh_final_equity).toLocaleString()} ${unit}`,
        cls: metricClass(m.buy_hold_return_pct),
      },
      {
        label: "最大回撤",
        value: fmtPct(m.max_drawdown_pct),
        sub: "风险暴露",
        cls: "negative",
      },
      {
        label: "夏普比率",
        value: m.sharpe_ratio != null ? Number(m.sharpe_ratio).toFixed(3) : "—",
        sub: "rf=0 · 252 日年化",
        cls: "neutral",
      },
      {
        label: "胜率",
        value: m.win_rate_pct != null ? Number(m.win_rate_pct).toFixed(1) + "%" : "—",
        sub: `${m.total_trades ?? 0} 笔已平仓`,
        cls: "neutral",
      },
      {
        label: "盈亏比",
        value: m.profit_factor != null ? Number(m.profit_factor).toFixed(2) : "—",
        sub: "profit factor",
        cls: "neutral",
      },
    ];
    els.metrics.innerHTML = cards
      .map(
        (c) => `<div class="metric ${c.cls}">
          <div class="label">${c.label}</div>
          <div class="value">${c.value}</div>
          <div class="sub">${c.sub}</div>
        </div>`
      )
      .join("");
  }

  function renderTrades(trades) {
    if (!trades?.length) {
      els.tradesBody.innerHTML = '<tr><td colspan="6" class="empty">暂无完整交易记录</td></tr>';
      return;
    }
    els.tradesBody.innerHTML = trades
      .slice()
      .reverse()
      .slice(0, 12)
      .map((t) => {
        const retCls = t.return_pct >= 0 ? "sig-buy" : "sig-sell";
        const reason =
          t.exit_reason === "end_of_backtest" ? "回测结束" : t.exit_reason || "—";
        return `<tr>
          <td>${t.entry_date}</td>
          <td>${t.exit_date ?? "—"}</td>
          <td class="num">${Number(t.entry_price).toFixed(2)}</td>
          <td class="num">${t.exit_price != null ? Number(t.exit_price).toFixed(2) : "—"}</td>
          <td>${reason}</td>
          <td class="num ${retCls}">${fmtPct(t.return_pct, true)}</td>
        </tr>`;
      })
      .join("");
  }

  function buySellPoints(series) {
    const buys = [];
    const sells = [];
    for (let i = 0; i < series.dates.length; i++) {
      if (series.buySignal[i]) {
        const exec = Math.min(i + 1, series.dates.length - 1);
        buys.push({ date: series.dates[exec], price: series.ohlc[exec][0] });
      }
      if (series.sellSignal[i]) {
        sells.push({ date: series.dates[i], price: series.ohlc[i][1] });
      }
    }
    return { buys, sells };
  }

  function renderCharts(result) {
    const s = result.series;
    const dates = s.dates;
    const { buys, sells } = buySellPoints(s);
    els.chartCaption.textContent = `▲ 买入 ${buys.length} 次 · ▼ 卖出 ${sells.length} 次`;

    const baseOpt = {
      backgroundColor: "transparent",
      animation: false,
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(18,24,38,.95)",
        borderColor: COLORS.border,
        textStyle: { color: "#e8edf7", fontSize: 11 },
      },
    };

    charts.kline.setOption(
      {
        ...baseOpt,
        grid: { left: 52, right: 20, top: 36, bottom: 56 },
        legend: {
          data: ["K线", "入场上轨", "出场下轨", "止损线", "买入", "卖出"],
          top: 0,
          textStyle: { color: COLORS.text, fontSize: 11 },
        },
        dataZoom: [
          { type: "inside", start: 0, end: 100 },
          {
            type: "slider",
            height: 18,
            bottom: 8,
            borderColor: COLORS.border,
            fillerColor: "rgba(38,166,154,.15)",
            handleStyle: { color: COLORS.strat },
            textStyle: { color: COLORS.text, fontSize: 10 },
          },
        ],
        xAxis: {
          type: "category",
          data: dates,
          axisLabel: { color: COLORS.text, fontSize: 10 },
          axisLine: { lineStyle: { color: COLORS.border } },
        },
        yAxis: {
          scale: true,
          axisLabel: { color: COLORS.text, fontSize: 10 },
          splitLine: { lineStyle: { color: COLORS.grid } },
        },
        series: [
          {
            name: "K线",
            type: "candlestick",
            data: s.ohlc,
            itemStyle: {
              color: COLORS.up,
              color0: COLORS.down,
              borderColor: COLORS.up,
              borderColor0: COLORS.down,
            },
          },
          {
            name: "入场上轨",
            type: "line",
            data: s.donchian_entry_high,
            showSymbol: false,
            lineStyle: { width: 1, type: "dashed", color: COLORS.entry },
          },
          {
            name: "出场下轨",
            type: "line",
            data: s.donchian_exit_low,
            showSymbol: false,
            lineStyle: { width: 1, type: "dotted", color: COLORS.exit },
          },
          {
            name: "止损线",
            type: "line",
            data: s.stop_price,
            showSymbol: false,
            lineStyle: { width: 1, color: COLORS.stop },
          },
          {
            name: "买入",
            type: "scatter",
            data: buys.map((b) => [b.date, b.price]),
            symbol: "triangle",
            symbolSize: 11,
            itemStyle: { color: COLORS.strat },
            z: 10,
          },
          {
            name: "卖出",
            type: "scatter",
            data: sells.map((x) => [x.date, x.price]),
            symbol: "pin",
            symbolSize: 11,
            itemStyle: { color: COLORS.up },
            z: 10,
          },
        ],
      },
      true
    );

    charts.equity.setOption(
      {
        ...baseOpt,
        grid: { left: 56, right: 16, top: 28, bottom: 28 },
        legend: {
          data: ["海龟策略", "买入持有"],
          top: 0,
          textStyle: { color: COLORS.text, fontSize: 11 },
        },
        xAxis: {
          type: "category",
          data: dates,
          axisLabel: { show: false },
          axisLine: { lineStyle: { color: COLORS.border } },
        },
        yAxis: {
          scale: true,
          axisLabel: { color: COLORS.text, fontSize: 10 },
          splitLine: { lineStyle: { color: COLORS.grid } },
        },
        series: [
          {
            name: "海龟策略",
            type: "line",
            data: s.equity,
            showSymbol: false,
            lineStyle: { width: 2, color: COLORS.strat },
          },
          {
            name: "买入持有",
            type: "line",
            data: s.bh_equity,
            showSymbol: false,
            lineStyle: { width: 1.5, type: "dashed", color: COLORS.bh },
          },
        ],
      },
      true
    );

    charts.atr.setOption(
      {
        ...baseOpt,
        grid: { left: 56, right: 16, top: 28, bottom: 28 },
        legend: {
          data: ["ATR(N)"],
          top: 0,
          textStyle: { color: COLORS.text, fontSize: 11 },
        },
        xAxis: {
          type: "category",
          data: dates,
          axisLabel: { show: false },
          axisLine: { lineStyle: { color: COLORS.border } },
        },
        yAxis: {
          scale: true,
          axisLabel: { color: COLORS.text, fontSize: 10 },
          splitLine: { lineStyle: { color: COLORS.grid } },
        },
        series: [
          {
            name: "ATR(N)",
            type: "line",
            data: s.atr_n,
            showSymbol: false,
            lineStyle: { width: 1.4, color: COLORS.atr },
            areaStyle: { color: "rgba(0,137,123,.12)" },
          },
        ],
      },
      true
    );
  }

  function updateBanner(result) {
    const st = result.stock;
    const w = result.date_window;
    const p = result.params;
    const tagClass = st.market === "港股" ? "tag-hk" : "tag-a";
    els.stockBanner.innerHTML = `
      <span class="name">${st.name}</span>
      <span class="tag ${tagClass}">${st.market} ${st.code}</span>
      <span class="tag tag-strat">Turtle(${p.entry_period}/${p.exit_period}) · N=${p.atr_period} · ${p.stop_n_multiplier}×止损</span>
      <span>${w.start} ~ ${w.end} · ${w.rows} 交易日</span>`;
  }

  function showToast(msg, isError) {
    els.toast.textContent = msg;
    els.toast.classList.toggle("error", !!isError);
    els.toast.classList.add("show");
    setTimeout(() => els.toast.classList.remove("show"), 3200);
  }

  function getStockMeta() {
    return manifest.stocks.find((s) => s.stock_id === els.stock.value);
  }

  function syncDateBounds() {
    const stock = getStockMeta();
    if (!stock) return;
    const start = stock.date_range?.start || stock.date_range_start;
    const end = stock.last_complete_date;
    els.startDate.min = start;
    els.startDate.max = end;
    els.endDate.min = start;
    els.endDate.max = end;
    if (!els.endDate.value || els.endDate.value > end) els.endDate.value = end;
    if (!els.startDate.value) {
      const d = new Date(end);
      d.setFullYear(d.getFullYear() - 1);
      const s = d.toISOString().slice(0, 10);
      els.startDate.value = s < start ? start : s;
    }
    els.dataBadge.textContent = `数据截至 ${end}`;
  }

  function initStockSelect() {
    els.stock.innerHTML = manifest.stocks
      .map(
        (s) =>
          `<option value="${s.stock_id}">${s.name} (${s.code} · ${s.market})</option>`
      )
      .join("");
    if (manifest.stocks.some((s) => s.stock_id === "smic_hk")) {
      els.stock.value = "smic_hk";
    }
  }

  async function runBacktest() {
    if (loading) return;
    const err = validateParamsLocal();
    els.paramError.textContent = err || "";
    if (err) return;

    loading = true;
    els.runBtn.disabled = true;
    els.runBtn.textContent = "回测中…";

    const system = getSelectedSystem();
    const body = {
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
        initial_capital: +els.initialCapital.value,
        commission_rate: +els.commission.value,
        slippage_rate: +els.slippage.value,
      },
    };

    try {
      const result = await api("/api/backtest", {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (result.error) {
        els.paramError.textContent = result.error;
        showToast(result.error, true);
        return;
      }
      renderMetrics(result.metrics, result.stock.unit);
      renderTrades(result.trades);
      renderCharts(result);
      updateBanner(result);
      if (els.statusDot) els.statusDot.classList.add("live");
    } catch (e) {
      showToast("回测失败: " + e.message, true);
    } finally {
      loading = false;
      els.runBtn.disabled = false;
      els.runBtn.textContent = "▶ 运行回测";
    }
  }

  async function refreshData() {
    els.refreshBtn.classList.add("spinning");
    els.refreshBtn.disabled = true;
    try {
      const res = await api("/api/refresh", {
        method: "POST",
        body: JSON.stringify({ stock_id: els.stock.value }),
      });
      if (!res.ok) throw new Error(res.error || "刷新失败");
      manifest = res.manifest;
      syncDateBounds();
      showToast(`数据已更新 · 截至 ${getStockMeta()?.last_complete_date}`);
      await runBacktest();
    } catch (e) {
      showToast("刷新失败: " + e.message, true);
    } finally {
      els.refreshBtn.classList.remove("spinning");
      els.refreshBtn.disabled = false;
    }
  }

  function bindEvents() {
    els.stock.addEventListener("change", () => {
      syncDateBounds();
      runBacktest();
    });
    for (const r of els.system) {
      r.addEventListener("change", () => {
        if (r.checked && r.value !== "custom") applySystemPreset(r.value);
        runBacktest();
      });
    }
    ["entryPeriod", "exitPeriod", "atrPeriod"].forEach((id) => {
      document.getElementById(id).addEventListener("change", () => {
        document.getElementById("systemCustom").checked = true;
        runBacktest();
      });
    });
    els.stopN.addEventListener("input", (e) => {
      els.stopNVal.textContent = (+e.target.value).toFixed(1);
      document.getElementById("systemCustom").checked = true;
    });
    els.stopN.addEventListener("change", runBacktest);
    [els.startDate, els.endDate, els.initialCapital, els.commission, els.slippage].forEach(
      (el) => el.addEventListener("change", runBacktest)
    );
    document.querySelectorAll("[data-preset]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const stock = getStockMeta();
        const end = stock.last_complete_date;
        if (btn.dataset.preset === "all") {
          els.startDate.value = stock.date_range?.start || stock.date_range_start;
        } else {
          const d = new Date(end);
          d.setFullYear(d.getFullYear() - (btn.dataset.preset === "2y" ? 2 : 1));
          const start = d.toISOString().slice(0, 10);
          const minStart = stock.date_range?.start || stock.date_range_start;
          els.startDate.value = start < minStart ? minStart : start;
        }
        els.endDate.value = end;
        runBacktest();
      });
    });
    els.runBtn.addEventListener("click", runBacktest);
    els.refreshBtn.addEventListener("click", refreshData);
    window.addEventListener("resize", () => Object.values(charts).forEach((c) => c?.resize()));
  }

  async function init() {
    charts.kline = echarts.init(document.getElementById("chartKline"));
    charts.equity = echarts.init(document.getElementById("chartEquity"));
    charts.atr = echarts.init(document.getElementById("chartAtr"));

    try {
      manifest = await api("/api/manifest");
    } catch (e) {
      document.querySelector(".content").innerHTML =
        `<p style="padding:24px;color:#ef5350">无法连接 API，请先运行：<br>
        <code>python3 run_turtle_dashboard.py</code><br>
        或 <code>./start_turtle_dashboard.sh</code><br><br>${e.message}</p>`;
      return;
    }

    initStockSelect();
    applySystemPreset("system_1");
    syncDateBounds();
    bindEvents();
    await runBacktest();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
