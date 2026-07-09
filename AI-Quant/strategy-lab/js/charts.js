/**
 * Strategy Lab ECharts 渲染
 */
const StrategyCharts = (() => {
  const COLORS = {
    text: "#8b98b3",
    grid: "#1b2438",
    border: "#243049",
    price: "#cfd8dc",
    maShort: "#ef5350",
    maLong: "#5b8def",
    strat: "#ef5350",
    bh: "#90a4ae",
    buy: "#ef5350",
    sell: "#26a69a",
  };

  const charts = {};

  function init(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    if (charts[id]) charts[id].dispose();
    charts[id] = echarts.init(el);
    return charts[id];
  }

  function baseTooltip() {
    return {
      trigger: "axis",
      backgroundColor: "rgba(18,24,38,.95)",
      borderColor: COLORS.border,
      textStyle: { color: "#e8edf7", fontSize: 11 },
    };
  }

  function renderPrice(result, short, long) {
    const chart = init("chartPrice");
    if (!chart) return;

    const dates = result.rows.map((r) => r.date);
    const close = result.rows.map((r) => r.close);
    const maS = result.rows.map((r) => r.ma_short);
    const maL = result.rows.map((r) => r.ma_long);

    const buyPts = [];
    const sellPts = [];
    result.rows.forEach((r, i) => {
      if (r.buy_signal) buyPts.push([dates[i], close[i]]);
      if (r.sell_signal) sellPts.push([dates[i], close[i]]);
    });

    chart.setOption({
      backgroundColor: "transparent",
      grid: { left: 48, right: 16, top: 28, bottom: 36 },
      tooltip: baseTooltip(),
      legend: {
        data: ["收盘", `MA${short}`, `MA${long}`],
        top: 0,
        textStyle: { color: COLORS.text, fontSize: 11 },
      },
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
        { name: "收盘", type: "line", data: close, showSymbol: false, lineStyle: { width: 1.5, color: COLORS.price } },
        { name: `MA${short}`, type: "line", data: maS, showSymbol: false, lineStyle: { width: 1, color: COLORS.maShort } },
        { name: `MA${long}`, type: "line", data: maL, showSymbol: false, lineStyle: { width: 1, color: COLORS.maLong } },
        { type: "scatter", data: buyPts, symbol: "triangle", symbolSize: 12, itemStyle: { color: COLORS.buy }, tooltip: { show: false } },
        { type: "scatter", data: sellPts, symbol: "triangle", symbolRotate: 180, symbolSize: 12, itemStyle: { color: COLORS.sell }, tooltip: { show: false } },
      ],
    });
  }

  function renderEquity(result) {
    const chart = init("chartEquity");
    if (!chart) return;

    const dates = result.rows.map((r) => r.date);
    const stratEq = result.rows.map((r) => Math.round(r.equity));
    const bhEq = result.rows.map((r) => Math.round(r.bh_equity));

    chart.setOption({
      backgroundColor: "transparent",
      grid: { left: 52, right: 16, top: 28, bottom: 36 },
      tooltip: baseTooltip(),
      legend: {
        data: ["双均线策略", "买入持有"],
        top: 0,
        textStyle: { color: COLORS.text, fontSize: 11 },
      },
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
        { name: "双均线策略", type: "line", data: stratEq, showSymbol: false, lineStyle: { width: 2, color: COLORS.strat } },
        { name: "买入持有", type: "line", data: bhEq, showSymbol: false, lineStyle: { width: 1.5, type: "dashed", color: COLORS.bh } },
      ],
    });
  }

  function renderHeatmap(scan, grid) {
    const chart = init("chartHeat");
    if (!chart || !scan?.results?.length) return;

    const shorts = grid.short;
    const longs = grid.long;
    const heatData = scan.results.map((r) => [shorts.indexOf(r.short), longs.indexOf(r.long), r.sharpe_ratio]);
    const values = heatData.map((d) => d[2]);
    const minV = Math.min(...values);
    const maxV = Math.max(...values);

    chart.setOption({
      backgroundColor: "transparent",
      grid: { left: 48, right: 56, top: 8, bottom: 40 },
      tooltip: {
        position: "top",
        backgroundColor: "rgba(18,24,38,.95)",
        borderColor: COLORS.border,
        textStyle: { color: "#e8edf7", fontSize: 11 },
        formatter(p) {
          const s = shorts[p.data[0]];
          const l = longs[p.data[1]];
          return `MA${s}/${l}<br/>夏普: ${p.data[2].toFixed(2)}`;
        },
      },
      xAxis: {
        type: "category",
        data: shorts.map(String),
        name: "short",
        nameTextStyle: { color: COLORS.text },
        axisLabel: { color: COLORS.text, fontSize: 10 },
      },
      yAxis: {
        type: "category",
        data: longs.map(String),
        name: "long",
        nameTextStyle: { color: COLORS.text },
        axisLabel: { color: COLORS.text, fontSize: 10 },
      },
      visualMap: {
        min: minV,
        max: maxV,
        calculable: false,
        orient: "vertical",
        right: 0,
        top: "center",
        textStyle: { color: COLORS.text, fontSize: 10 },
        inRange: { color: ["#1b4332", "#95d5b2", "#fefae0", "#ef5350"] },
      },
      series: [{
        type: "heatmap",
        data: heatData,
        label: { show: true, fontSize: 9, color: "#fff", formatter: (p) => p.data[2].toFixed(2) },
      }],
    });
  }

  function resizeAll() {
    Object.values(charts).forEach((c) => c?.resize());
  }

  return { renderPrice, renderEquity, renderHeatmap, resizeAll };
})();
