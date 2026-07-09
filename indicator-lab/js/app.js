/**
 * Indicator Lab 主控制器：数据加载、参数调节、图表重绘
 */

const DEBOUNCE_MS = 300;
const STORAGE_KEY = "indicator-lab-params-v1";

const state = {
  config: null,
  stock: null,
  allStocks: [],
  rawRows: [],
  rows: [],
  params: null,
  activeTab: "boll",
  autoRedraw: true,
  chart: null,
  debounceTimer: null,
};

function $(id) {
  return document.getElementById(id);
}

function fmt(v, digits = 2) {
  if (v == null || Number.isNaN(v)) return "—";
  return Number(v).toFixed(digits);
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

function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function defaultParams() {
  return deepClone(state.config.defaults.indicators);
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
      if (["date"].includes(h)) row[h] = v;
      else row[h] = v === "" ? NaN : Number(v);
    });
    if (!row.date || Number.isNaN(row.close)) continue;
    rows.push(row);
  }
  return rows.sort((a, b) => a.date.localeCompare(b.date));
}

function filterByRange(rows, rangeKey) {
  if (rangeKey === "all" || !rows.length) return rows;
  const days = Number(rangeKey);
  const end = rows[rows.length - 1].date;
  const endMs = new Date(end).getTime();
  const cutoff = endMs - days * 86400000;
  return rows.filter((r) => new Date(r.date).getTime() >= cutoff);
}

function readParamsFromUI() {
  return {
    rsi: { period: clampInt($("rsiPeriod").value, 2, 50) },
    macd: {
      fast: clampInt($("macdFast").value, 2, 50),
      slow: clampInt($("macdSlow").value, 3, 100),
      signal: clampInt($("macdSignal").value, 2, 50),
    },
    boll: {
      period: clampInt($("bollPeriod").value, 5, 60),
      std_multiplier: clampFloat($("bollK").value, 1, 3),
    },
    atr: { period: clampInt($("atrPeriod").value, 2, 50) },
  };
}

function writeParamsToUI(params) {
  $("rsiPeriod").value = params.rsi.period;
  $("rsiPeriodVal").textContent = params.rsi.period;
  $("macdFast").value = params.macd.fast;
  $("macdSlow").value = params.macd.slow;
  $("macdSignal").value = params.macd.signal;
  $("bollPeriod").value = params.boll.period;
  $("bollK").value = params.boll.std_multiplier;
  $("bollKVal").textContent = Number(params.boll.std_multiplier).toFixed(1);
  $("atrPeriod").value = params.atr.period;
  $("atrPeriodVal").textContent = params.atr.period;
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

function validateParams(params) {
  if (params.macd.fast >= params.macd.slow) {
    return "MACD 快线必须小于慢线";
  }
  return null;
}

function rsiLabel(rsi) {
  if (Number.isNaN(rsi)) return "—";
  if (rsi >= 70) return "偏超买";
  if (rsi <= 30) return "偏超卖";
  return "中性区间";
}

function histColor(hist) {
  if (Number.isNaN(hist)) return "var(--text)";
  return hist >= 0 ? "var(--up)" : "var(--down)";
}

function updateBanner() {
  const s = state.stock;
  const rows = state.rows;
  if (!s || !rows.length) return;
  const start = rows[0].date;
  const end = rows[rows.length - 1].date;
  const adjust = $("adjustSelect").value;
  const adjustLabel = { qfq: "前复权", hfq: "后复权", none: "不复权" }[adjust] || adjust;
  $("stockBanner").innerHTML =
    `<strong>${s.name}</strong> · ${s.ts_code} · ${s.market} · ${s.industry}` +
    ` &nbsp;|&nbsp; ${start} ~ ${end} · ${rows.length} 个交易日 · ${adjustLabel}`;
}

function updateMetrics() {
  const s = state.stock;
  const p = state.params;
  const rows = state.rows;
  if (!rows.length) return;
  const last = rows[rows.length - 1];

  $("metricClose").textContent = fmt(last.close);
  $("metricCloseSub").textContent = `${s.unit} · 前复权`;

  $("metricRsiLabel").textContent = `RSI (${p.rsi.period})`;
  $("metricRsi").textContent = fmt(last.rsi);
  $("metricRsiSub").textContent = rsiLabel(last.rsi);

  const hist = last.macd_hist;
  $("metricHist").textContent = Number.isNaN(hist) ? "—" : `${hist >= 0 ? "+" : ""}${fmt(hist, 3)}`;
  $("metricHist").style.color = histColor(hist);
  $("metricMacdSub").textContent = `DIF ${fmt(last.macd_dif, 2)} / DEA ${fmt(last.macd_dea, 2)}`;

  $("metricAtrLabel").textContent = `ATR (${p.atr.period})`;
  $("metricAtr").textContent = fmt(last.atr);
  const atr2 = Number.isNaN(last.atr) ? NaN : last.atr * 2;
  $("metricAtrSub").textContent = Number.isNaN(atr2) ? "—" : `2×ATR ≈ ${fmt(atr2)} ${s.unit}`;
}

function updateTable() {
  const tbody = $("detailTable");
  const tail = state.rows.slice(-5);
  tbody.innerHTML = tail
    .map((r) => {
      const hist = r.macd_hist;
      const histStr = Number.isNaN(hist) ? "—" : `${hist >= 0 ? "+" : ""}${fmt(hist, 3)}`;
      return `<tr>
        <td>${r.date}</td>
        <td>${fmt(r.close)}</td>
        <td>${fmt(r.rsi)}</td>
        <td>${fmt(r.macd_dif, 3)}</td>
        <td>${fmt(r.macd_dea, 3)}</td>
        <td>${histStr}</td>
        <td>${fmt(r.atr)}</td>
      </tr>`;
    })
    .join("");
}

function applyComputation() {
  const err = validateParams(state.params);
  if (err) {
    showToast(err, "error");
    return;
  }
  const rangeKey = $("rangeSelect").value;
  const filtered = filterByRange(state.rawRows, rangeKey);
  state.rows = IndicatorEngine.addAllIndicators(filtered, state.params);
  updateBanner();
  updateMetrics();
  updateTable();
  state.chart.render(state.activeTab, state.rows, state.stock, state.params);
  saveParamsToStorage();
}

function scheduleApply() {
  if (!state.autoRedraw) return;
  clearTimeout(state.debounceTimer);
  state.debounceTimer = setTimeout(() => {
    state.params = readParamsFromUI();
    applyComputation();
  }, DEBOUNCE_MS);
}

function populateStockSelect() {
  const market = $("marketSelect").value;
  const select = $("stockSelect");
  const filtered = state.allStocks.filter((s) => market === "all" || s.market === market);
  select.innerHTML = filtered
    .map((s) => `<option value="${s.id}">${s.name} (${s.ts_code})</option>`)
    .join("");
  if (!filtered.length) {
    select.innerHTML = '<option value="">无可用股票</option>';
    return null;
  }
  const urlStock = new URLSearchParams(location.search).get("stock");
  if (urlStock && filtered.some((s) => s.id === urlStock)) {
    select.value = urlStock;
  }
  return filtered.find((s) => s.id === select.value) || filtered[0];
}

async function loadStockData(stock) {
  setLoading(true);
  try {
    const res = await fetch(stock.csv);
    if (!res.ok) throw new Error(`无法加载 ${stock.csv}`);
    const text = await res.text();
    state.rawRows = parseCSV(text);
    if (state.rawRows.length < 10) throw new Error("数据行数过少");
    state.stock = stock;
    applyComputation();
  } catch (e) {
    showToast(e.message || "数据加载失败", "error");
  } finally {
    setLoading(false);
  }
}

async function onStockChange() {
  const stock = state.allStocks.find((s) => s.id === $("stockSelect").value);
  if (!stock) return;
  await loadStockData(stock);
  updateUrl();
}

function setActiveTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll("#chartTabs .tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.tab === tab);
  });
  if (state.rows.length) {
    state.chart.render(tab, state.rows, state.stock, state.params);
  }
  updateUrl();
}

function resetDefaults() {
  state.params = defaultParams();
  writeParamsToUI(state.params);
  applyComputation();
  showToast("已恢复默认参数");
}

function saveParamsToStorage() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ params: state.params, stockId: state.stock?.id, tab: state.activeTab })
    );
  } catch (_) {
    /* ignore */
  }
}

function loadParamsFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
}

function applyUrlParams() {
  const qs = new URLSearchParams(location.search);
  const tab = qs.get("tab");
  if (tab && ChartBuilder.TAB_BUILDERS[tab]) setActiveTab(tab);

  const range = qs.get("range");
  if (range && $("rangeSelect").querySelector(`option[value="${range}"]`)) {
    $("rangeSelect").value = range;
  }

  const p = state.params;
  const rsi = qs.get("rsi");
  const macdFast = qs.get("macdFast");
  const macdSlow = qs.get("macdSlow");
  const macdSignal = qs.get("macdSignal");
  const bollPeriod = qs.get("bollPeriod");
  const bollK = qs.get("bollK");
  const atr = qs.get("atr");

  if (rsi) p.rsi.period = clampInt(rsi, 2, 50);
  if (macdFast) p.macd.fast = clampInt(macdFast, 2, 50);
  if (macdSlow) p.macd.slow = clampInt(macdSlow, 3, 100);
  if (macdSignal) p.macd.signal = clampInt(macdSignal, 2, 50);
  if (bollPeriod) p.boll.period = clampInt(bollPeriod, 5, 60);
  if (bollK) p.boll.std_multiplier = clampFloat(bollK, 1, 3);
  if (atr) p.atr.period = clampInt(atr, 2, 50);
  writeParamsToUI(p);
}

function buildShareUrl() {
  const p = state.params;
  const qs = new URLSearchParams({
    stock: state.stock?.id || "",
    tab: state.activeTab,
    range: $("rangeSelect").value,
    rsi: String(p.rsi.period),
    macdFast: String(p.macd.fast),
    macdSlow: String(p.macd.slow),
    macdSignal: String(p.macd.signal),
    bollPeriod: String(p.boll.period),
    bollK: String(p.boll.std_multiplier),
    atr: String(p.atr.period),
  });
  return `${location.origin}${location.pathname}?${qs.toString()}`;
}

function updateUrl() {
  const url = buildShareUrl();
  history.replaceState(null, "", url);
}

async function copyLink() {
  const url = buildShareUrl();
  try {
    await navigator.clipboard.writeText(url);
    showToast("链接已复制到剪贴板");
  } catch (_) {
    showToast("复制失败，请手动复制地址栏", "error");
  }
}

function exportPng() {
  if (!state.stock) return;
  const name = `${state.stock.id}_${state.activeTab}_${state.rows.at(-1)?.date || "chart"}.png`;
  state.chart.exportPNG(name);
  showToast("图表已导出");
}

function bindAccordion() {
  document.querySelectorAll(".accordion .acc-head").forEach((head) => {
    head.addEventListener("click", () => {
      head.parentElement.classList.toggle("open");
    });
    head.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        head.parentElement.classList.toggle("open");
      }
    });
  });
}

function bindEvents() {
  $("marketSelect").addEventListener("change", async () => {
    const stock = populateStockSelect();
    if (stock) await loadStockData(stock);
  });

  $("stockSelect").addEventListener("change", onStockChange);
  $("rangeSelect").addEventListener("change", () => {
    applyComputation();
    updateUrl();
  });

  $("adjustSelect").addEventListener("change", updateBanner);

  const paramInputs = [
    "rsiPeriod",
    "macdFast",
    "macdSlow",
    "macdSignal",
    "bollPeriod",
    "bollK",
    "atrPeriod",
  ];
  paramInputs.forEach((id) => {
    const el = $(id);
    el.addEventListener("input", () => {
      if (id === "rsiPeriod") $("rsiPeriodVal").textContent = el.value;
      if (id === "bollK") $("bollKVal").textContent = Number(el.value).toFixed(1);
      if (id === "atrPeriod") $("atrPeriodVal").textContent = el.value;
      state.params = readParamsFromUI();
      scheduleApply();
    });
  });

  $("autoRedraw").addEventListener("change", (e) => {
    state.autoRedraw = e.target.checked;
  });

  $("btnApply").addEventListener("click", () => {
    state.params = readParamsFromUI();
    applyComputation();
    updateUrl();
  });

  $("btnReset").addEventListener("click", resetDefaults);

  document.querySelectorAll("#chartTabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => setActiveTab(tab.dataset.tab));
  });

  $("btnCopyLink").addEventListener("click", copyLink);
  $("btnExportPng").addEventListener("click", exportPng);

  window.addEventListener("resize", () => state.chart?.resize());
}

async function init() {
  setLoading(true);
  try {
    const res = await fetch("assets/stocks.json");
    if (!res.ok) throw new Error("无法加载 stocks.json");
    state.config = await res.json();
    state.allStocks = state.config.stocks;
    state.params = defaultParams();

    const saved = loadParamsFromStorage();
    if (saved?.params) state.params = saved.params;

    applyUrlParams();
    writeParamsToUI(state.params);

    state.autoRedraw = $("autoRedraw").checked;
    state.chart = ChartBuilder.create($("chart"));

    bindAccordion();
    bindEvents();

    const stock = populateStockSelect();
    if (!stock) throw new Error("股票列表为空");

    if (saved?.tab && ChartBuilder.TAB_BUILDERS[saved.tab] && !location.search.includes("tab=")) {
      setActiveTab(saved.tab);
    }

    await loadStockData(stock);

    const updated = state.rawRows.length ? state.rawRows[state.rawRows.length - 1].date : "—";
    $("footer").textContent =
      `仅供学习，不构成投资建议 · Indicator Lab v1.0 · spec v1.0.0 · 数据更新至 ${updated}`;
  } catch (e) {
    showToast(e.message || "初始化失败", "error");
    $("stockBanner").textContent = "初始化失败，请通过本地 HTTP 服务打开（见 README）";
  } finally {
    setLoading(false);
  }
}

document.addEventListener("DOMContentLoaded", init);
