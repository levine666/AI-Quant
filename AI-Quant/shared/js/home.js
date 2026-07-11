/**
 * AI-Quant 首页：从 apps/registry.json 渲染 App 卡片
 */
(function () {
  "use strict";

  const TYPE_LABELS = {
    research: "研究",
    indicators: "指标",
    strategy: "策略",
    tool: "工具",
  };

  const STATUS_LABELS = {
    live: { text: "在线", cls: "live" },
    beta: { text: "测试", cls: "beta" },
    local_only: { text: "本地", cls: "local" },
    planned: { text: "规划", cls: "planned" },
  };

  let registry = null;
  let filter = "all";

  async function loadRegistry() {
    try {
      const res = await fetch("apps/registry.json");
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    } catch (e) {
      console.warn("registry fetch failed, using fallback", e);
      return FALLBACK_REGISTRY;
    }
  }

  const FALLBACK_REGISTRY = {
    meta: { platform: "AI-Quant", data_updated: null },
    apps: [
      { app_id: "ah_compare", order: 10, title: "中芯国际 A/H 对比", subtitle: "TASK1", type: "research", status: "live", href: "./ah-compare/", icon: "📊", accent_color: "#f5a623", tags: ["A/H股"], description: "A股 vs 港股价格与溢价对比" },
      { app_id: "indicator_lab", order: 20, title: "Indicator Lab", subtitle: "TASK2", type: "indicators", status: "live", href: "./indicator-lab/", icon: "📈", accent_color: "#7e57c2", tags: ["RSI","MACD"], description: "技术指标交互分析" },
      { app_id: "strategy_lab_ma", order: 30, title: "Strategy Lab", subtitle: "TASK3", type: "strategy", status: "live", href: "./strategy-lab/", icon: "⚡", accent_color: "#ef5350", tags: ["双均线"], description: "MA交叉策略回测" },
      { app_id: "turtle_lab", order: 40, title: "Turtle Lab", subtitle: "海龟法则", type: "strategy", status: "beta", href: "./turtle-lab/", icon: "🐢", accent_color: "#26a69a", tags: ["Donchian","ATR"], description: "海龟交易法则回测" },
    ],
    planned_apps: [],
  };

  function renderHero(meta, apps) {
    const live = apps.filter((a) => a.status !== "planned" && a.status !== "hidden");
    $("heroStats").innerHTML = [
      `<span><strong>${live.length}</strong> 应用</span>`,
      `<span><strong>4</strong> 标的</span>`,
      meta.data_updated
        ? `<span>数据 ${meta.data_updated.slice(0, 10)}</span>`
        : "",
    ]
      .filter(Boolean)
      .join(" · ");
  }

  function cardHtml(app, disabled) {
    const st = STATUS_LABELS[app.status] || STATUS_LABELS.live;
    const tags = (app.tags || [])
      .slice(0, 4)
      .map((t) => `<span class="tag">${t}</span>`)
      .join("");
    const el = disabled ? "div" : "a";
    const href = disabled ? "" : ` href="${app.href}"`;
    return `<${el} class="app-card ${disabled ? "disabled" : ""}"${href} style="--accent:${app.accent_color}">
      <div class="card-accent"></div>
      <div class="card-head">
        <span class="card-icon">${app.icon || "📦"}</span>
        <span class="status ${st.cls}">${st.text}</span>
      </div>
      <h3>${app.title}</h3>
      <p class="subtitle">${app.subtitle || ""}</p>
      <p class="desc">${app.description || ""}</p>
      <div class="tags">${tags}</div>
      <div class="card-foot">
        <span class="type">${TYPE_LABELS[app.type] || app.type}</span>
        ${disabled ? "" : '<span class="enter">进入 →</span>'}
      </div>
    </${el}>`;
  }

  function renderGrid() {
    const apps = registry.apps.filter((a) => a.status !== "hidden");
    const planned = registry.planned_apps || [];
    const filtered =
      filter === "all" ? apps : apps.filter((a) => a.type === filter);

    $("appGrid").innerHTML =
      filtered.map((a) => cardHtml(a, a.status === "planned")).join("") ||
      '<p class="empty">该分类暂无应用</p>';

    if (filter === "all" || filter === "strategy") {
      $("plannedGrid").innerHTML = planned
        .map((a) => cardHtml(a, true))
        .join("");
      $("plannedSection").style.display = planned.length ? "block" : "none";
    } else {
      $("plannedSection").style.display = "none";
    }
  }

  function bindFilters() {
    document.querySelectorAll("[data-filter]").forEach((btn) => {
      btn.addEventListener("click", () => {
        filter = btn.dataset.filter;
        document.querySelectorAll("[data-filter]").forEach((b) =>
          b.classList.toggle("active", b === btn)
        );
        renderGrid();
      });
    });
  }

  function $(id) {
    return document.getElementById(id);
  }

  async function init() {
    try {
      registry = await loadRegistry();
      renderHero(registry.meta, registry.apps);
      bindFilters();
      renderGrid();
    } catch (e) {
      $("appGrid").innerHTML = `<p class="empty">加载失败: ${e.message}</p>`;
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
