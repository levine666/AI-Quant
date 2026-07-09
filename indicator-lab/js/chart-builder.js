/**
 * ECharts 图表构建（价格+BOLL / RSI / MACD / ATR）
 */

const CHART_COLORS = {
  close: "#5b8def",
  bollUpper: "#ef5350",
  bollMid: "#888888",
  bollLower: "#26a69a",
  rsi: "#b388ff",
  macdDif: "#5b8def",
  macdDea: "#f5a623",
  atr: "#00897b",
  up: "#ef5350",
  down: "#26a69a",
};

function fmt(v, digits = 2) {
  if (v == null || Number.isNaN(v)) return "—";
  return Number(v).toFixed(digits);
}

function axisStyle() {
  return {
    axisLine: { lineStyle: { color: "#243049" } },
    axisLabel: { color: "#8b98b3", fontSize: 11 },
    splitLine: { lineStyle: { color: "#1a2233" } },
  };
}

function baseGrid() {
  return { left: 56, right: 20, top: 52, bottom: 56 };
}

function dataZoomConfig() {
  return [
    { type: "inside", start: 0, end: 100 },
    {
      type: "slider",
      height: 18,
      bottom: 8,
      borderColor: "#243049",
      fillerColor: "rgba(91,141,239,0.15)",
      handleStyle: { color: "#5b8def" },
      textStyle: { color: "#8b98b3", fontSize: 10 },
    },
  ];
}

function buildTooltipFormatter(rows, stock) {
  return (params) => {
    if (!params?.length) return "";
    const idx = params[0].dataIndex;
    const row = rows[idx];
    if (!row) return "";
    const unit = stock.unit || "";
    let html = `<div style="font-size:12px;line-height:1.6">`;
    html += `<strong>${row.date}</strong><br/>`;
    html += `收盘 ${fmt(row.close)} ${unit}<br/>`;
    html += `RSI ${fmt(row.rsi)} · DIF ${fmt(row.macd_dif, 3)} · DEA ${fmt(row.macd_dea, 3)}<br/>`;
    html += `MACD柱 ${fmt(row.macd_hist, 3)} · ATR ${fmt(row.atr)} ${unit}`;
    html += `</div>`;
    return html;
  };
}

function buildBollOption(rows, stock, params) {
  const dates = rows.map((r) => r.date);
  const { period, std_multiplier: k } = params.boll;
  return {
    backgroundColor: "transparent",
    title: {
      text: `图1  ${stock.name}（${stock.code}）收盘价与布林带 (${period}, ${k})`,
      left: 12,
      top: 8,
      textStyle: { color: "#e8edf7", fontSize: 13, fontWeight: 600 },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(18,24,38,0.95)",
      borderColor: "#243049",
      textStyle: { color: "#e8edf7", fontSize: 12 },
      formatter: buildTooltipFormatter(rows, stock),
    },
    legend: {
      top: 8,
      right: 12,
      textStyle: { color: "#8b98b3", fontSize: 11 },
      data: ["收盘", "上轨", "中轨", "下轨"],
    },
    grid: baseGrid(),
    dataZoom: dataZoomConfig(),
    xAxis: { type: "category", data: dates, boundaryGap: false, ...axisStyle(), splitLine: { show: false } },
    yAxis: {
      type: "value",
      scale: true,
      name: stock.unit,
      nameTextStyle: { color: "#8b98b3", fontSize: 11 },
      ...axisStyle(),
    },
    series: [
      {
        name: "收盘",
        type: "line",
        data: rows.map((r) => r.close),
        showSymbol: false,
        lineStyle: { width: 2, color: CHART_COLORS.close },
        itemStyle: { color: CHART_COLORS.close },
        z: 3,
      },
      {
        name: "上轨",
        type: "line",
        data: rows.map((r) => (Number.isNaN(r.boll_upper) ? null : r.boll_upper)),
        showSymbol: false,
        lineStyle: { width: 1, type: "dashed", color: CHART_COLORS.bollUpper },
        itemStyle: { color: CHART_COLORS.bollUpper },
      },
      {
        name: "中轨",
        type: "line",
        data: rows.map((r) => (Number.isNaN(r.boll_mid) ? null : r.boll_mid)),
        showSymbol: false,
        lineStyle: { width: 1, color: CHART_COLORS.bollMid },
        itemStyle: { color: CHART_COLORS.bollMid },
      },
      {
        name: "下轨",
        type: "line",
        data: rows.map((r) => (Number.isNaN(r.boll_lower) ? null : r.boll_lower)),
        showSymbol: false,
        lineStyle: { width: 1, type: "dashed", color: CHART_COLORS.bollLower },
        itemStyle: { color: CHART_COLORS.bollLower },
      },
    ],
  };
}

function buildRsiOption(rows, stock, params) {
  const dates = rows.map((r) => r.date);
  const period = params.rsi.period;
  return {
    backgroundColor: "transparent",
    title: {
      text: `图2  ${stock.name}（${stock.code}）RSI(${period})`,
      left: 12,
      top: 8,
      textStyle: { color: "#e8edf7", fontSize: 13, fontWeight: 600 },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(18,24,38,0.95)",
      borderColor: "#243049",
      textStyle: { color: "#e8edf7", fontSize: 12 },
    },
    grid: baseGrid(),
    dataZoom: dataZoomConfig(),
    xAxis: { type: "category", data: dates, boundaryGap: false, ...axisStyle(), splitLine: { show: false } },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      ...axisStyle(),
    },
    series: [
      {
        name: "RSI",
        type: "line",
        data: rows.map((r) => (Number.isNaN(r.rsi) ? null : r.rsi)),
        showSymbol: false,
        lineStyle: { width: 2, color: CHART_COLORS.rsi },
        itemStyle: { color: CHART_COLORS.rsi },
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { type: "dashed", width: 1 },
          data: [
            { yAxis: 70, lineStyle: { color: CHART_COLORS.up }, label: { formatter: "70", color: "#8b98b3" } },
            { yAxis: 50, lineStyle: { color: "#555" }, label: { formatter: "50", color: "#8b98b3" } },
            { yAxis: 30, lineStyle: { color: CHART_COLORS.down }, label: { formatter: "30", color: "#8b98b3" } },
          ],
        },
      },
    ],
  };
}

function buildMacdOption(rows, stock, params) {
  const dates = rows.map((r) => r.date);
  const { fast, slow, signal } = params.macd;
  return {
    backgroundColor: "transparent",
    title: {
      text: `图3  ${stock.name}（${stock.code}）MACD(${fast},${slow},${signal})`,
      left: 12,
      top: 8,
      textStyle: { color: "#e8edf7", fontSize: 13, fontWeight: 600 },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(18,24,38,0.95)",
      borderColor: "#243049",
      textStyle: { color: "#e8edf7", fontSize: 12 },
    },
    legend: {
      top: 8,
      right: 12,
      textStyle: { color: "#8b98b3", fontSize: 11 },
      data: ["DIF", "DEA", "柱"],
    },
    grid: baseGrid(),
    dataZoom: dataZoomConfig(),
    xAxis: { type: "category", data: dates, boundaryGap: true, ...axisStyle(), splitLine: { show: false } },
    yAxis: { type: "value", scale: true, ...axisStyle() },
    series: [
      {
        name: "DIF",
        type: "line",
        data: rows.map((r) => (Number.isNaN(r.macd_dif) ? null : r.macd_dif)),
        showSymbol: false,
        lineStyle: { width: 1.5, color: CHART_COLORS.macdDif },
        itemStyle: { color: CHART_COLORS.macdDif },
      },
      {
        name: "DEA",
        type: "line",
        data: rows.map((r) => (Number.isNaN(r.macd_dea) ? null : r.macd_dea)),
        showSymbol: false,
        lineStyle: { width: 1.5, color: CHART_COLORS.macdDea },
        itemStyle: { color: CHART_COLORS.macdDea },
      },
      {
        name: "柱",
        type: "bar",
        data: rows.map((r) => ({
          value: Number.isNaN(r.macd_hist) ? null : r.macd_hist,
          itemStyle: { color: r.macd_hist >= 0 ? CHART_COLORS.up : CHART_COLORS.down },
        })),
        barMaxWidth: 6,
      },
    ],
  };
}

function buildAtrOption(rows, stock, params) {
  const dates = rows.map((r) => r.date);
  const period = params.atr.period;
  return {
    backgroundColor: "transparent",
    title: {
      text: `图4  ${stock.name}（${stock.code}）ATR(${period})`,
      left: 12,
      top: 8,
      textStyle: { color: "#e8edf7", fontSize: 13, fontWeight: 600 },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(18,24,38,0.95)",
      borderColor: "#243049",
      textStyle: { color: "#e8edf7", fontSize: 12 },
    },
    grid: baseGrid(),
    dataZoom: dataZoomConfig(),
    xAxis: { type: "category", data: dates, boundaryGap: false, ...axisStyle(), splitLine: { show: false } },
    yAxis: {
      type: "value",
      scale: true,
      name: stock.unit,
      nameTextStyle: { color: "#8b98b3", fontSize: 11 },
      ...axisStyle(),
    },
    series: [
      {
        name: "ATR",
        type: "line",
        data: rows.map((r) => (Number.isNaN(r.atr) ? null : r.atr)),
        showSymbol: false,
        lineStyle: { width: 2, color: CHART_COLORS.atr },
        itemStyle: { color: CHART_COLORS.atr },
        areaStyle: { color: "rgba(0,137,123,0.12)" },
      },
    ],
  };
}

const TAB_BUILDERS = {
  boll: buildBollOption,
  rsi: buildRsiOption,
  macd: buildMacdOption,
  atr: buildAtrOption,
};

window.ChartBuilder = {
  TAB_BUILDERS,
  create(container) {
    const chart = echarts.init(container, null, { renderer: "canvas" });
    let currentTab = "boll";

    function render(tab, rows, stock, params) {
      currentTab = tab;
      const builder = TAB_BUILDERS[tab];
      if (!builder) return;
      chart.setOption(builder(rows, stock, params), true);
    }

    function resize() {
      chart.resize();
    }

    function exportPNG(filename) {
      const url = chart.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#121826" });
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || "indicator-lab.png";
      a.click();
    }

    function dispose() {
      chart.dispose();
    }

    return { render, resize, exportPNG, dispose, getCurrentTab: () => currentTab };
  },
};
