# Indicator Lab — 技术指标交互分析工具 · 产品设计文档

| 项目 | 内容 |
|------|------|
| 产品名称 | **Indicator Lab**（指标实验室） |
| 版本 | v1.0 设计稿 |
| 日期 | 2026-07-08 |
| 状态 | **规划阶段，暂不开发** |
| 关联规范 | `spec/indicator_lab.spec.yaml` |
| 界面参考 | `docs/indicator_lab_ui_mockup.html` |
| 算法参考 | `scripts/indicators.py` · `notebooks/smic_hk_indicators.ipynb` |

---

## 1. 产品概述

### 1.1 背景

TASK02 已在 Notebook 中完成中芯国际港股（00981）的 RSI、MACD、布林带、ATR 计算与可视化。下一阶段需要将其升级为**浏览器端 HTML 工具**，使用户可以：

- **切换不同股票**的数据源（港股 / A 股）
- **独立调节**四个指标的参数
- **即时重绘**图表，观察参数变化对指标形态的影响

### 1.2 一句话描述

> 在浏览器中选择股票与指标参数，纯前端实时计算 RSI / MACD / 布林带 / ATR 并重绘图表的轻量级量化分析工具。

### 1.3 目标用户

| 用户 | 需求 |
|------|------|
| TASK02 学员 | 完成作业报告、对比 Notebook 结果 |
| 个人投资者 | 快速验证 RSI(6) vs RSI(14) 等参数差异 |
| 技术分析学习者 | 理解「公式 → 参数 → 图形」的因果关系 |

### 1.4 核心价值

| 痛点 | 解决方案 |
|------|----------|
| Notebook 改参数需重跑单元格 | 侧边栏滑块/输入框，改参即重绘 |
| 多只股票需切换多个文件 | 统一股票选择器 + 预置 CSV 索引 |
| 四指标分散在多张独立图 | 单页垂直分屏，X 轴联动 |
| 参数含义不直观 | 每组指标附带说明 + 最新读数卡片 |
| 算法与 Notebook 不一致 | JS 移植 `indicators.py`，对齐测试 |

### 1.5 非目标（v1 不做）

- 实时行情推送、自动下单
- 用户登录与云端保存
- 复杂策略回测与信号统计
- 移动端原生 App（响应式 Web 即可）

---

## 2. 用户场景

### 场景 A：切换股票对比指标

> 用户想看中芯国际港股、比亚迪 A 股、长江电力的 RSI 走势差异。

1. 打开工具首页，默认加载中芯国际港股
2. 在「股票选择」下拉框切换标的
3. 四张图与摘要卡片同步更新
4. 底部表格展示最近 5 日明细

### 场景 B：调节 RSI 周期观察敏感度

> 用户想知道 RSI(6) 与 RSI(14) 对超买信号的差异。

1. 选中目标股票
2. 在 RSI 面板将 period 从 14 改为 6
3. 开启「自动重绘」或点击「应用」
4. RSI 图、摘要卡片、表格同步更新

### 场景 C：调节 MACD 快慢线

> 用户想观察 MACD(6,13,5) 与默认 (12,26,9) 的金叉位置差异。

1. 修改 MACD 三个参数
2. 若 fast ≥ slow，面板显示红色错误提示，禁用重绘
3. 参数合法后重绘，MACD 图 DIF/DEA/柱更新

### 场景 D：导出当前视图写入报告

> 用户需要将当前参数下的图表放入 TASK2 作业 Word/PDF。

1. 调整参数至满意状态
2. 点击「导出 PNG」下载当前主图
3. 或「复制链接」分享含 query 参数的 URL（v1.1）

---

## 3. 信息架构

```
Indicator Lab
├── 顶栏（Header · 52px）
│   ├── Logo / 标题
│   ├── 数据源说明（本地 CSV · spec v1.0.0）
│   └── 操作：复制链接 · 导出 PNG
│
├── 主体（Flex 横向）
│   ├── 左侧边栏（280px 固定，可折叠）
│   │   ├── 【股票选择区】
│   │   │   ├── 市场筛选（全部 / A股 / 港股）
│   │   │   ├── 股票下拉
│   │   │   ├── 数据区间（3M / 6M / 1Y / 全部）
│   │   │   └── 复权方式（qfq / hfq / none · v1 只读提示）
│   │   ├── 【指标参数区】Accordion 折叠（与右侧 ①–④ 一一对应）
│   │   │   ├── ① 布林带 — period / std_multiplier
│   │   │   ├── ② RSI — period
│   │   │   ├── ③ MACD — fast / slow / signal
│   │   │   └── ④ ATR — period
│   │   └── 【全局操作】
│   │       ├── 重置默认
│   │       ├── 应用并重绘
│   │       └── ☑ 自动重绘（300ms 防抖）
│   │
│   └── 右侧主内容区（flex 自适应）
│       ├── 股票信息条（名称 · 代码 · 市场 · 日期区间 · 行数）
│       ├── 指标模块 ①–④（每组 = 摘要卡片 + 图表，纵向排列）
│       │   ├── ① BOLL：读数卡 + 图1 价格+布林带（320px）
│       │   ├── ② RSI：读数卡 + 图2 RSI（200px）
│       │   ├── ③ MACD：读数卡 + 图3 MACD（240px）
│       │   └── ④ ATR：读数卡 + 图4 ATR（180px）
│       └── 数据表格（最近 5~10 日指标明细，可展开）
│
└── 底栏（Footer · 36px）
    └── 免责声明 · spec 版本 · 数据更新时间
```

---

## 4. 功能需求

### 4.1 股票数据模块

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 股票列表 | 从 `assets/stocks.json` 加载 | P0 |
| 数据源 | v1：本地预生成 CSV（Fetch） | P0 |
| 市场筛选 | 按 A股 / 港股过滤下拉列表 | P0 |
| 区间选择 | 近 90 / 180 / 365 日 / 全部 | P0 |
| 数据校验 | 行数 ≥ 120、OHLC 合法性 | P1 |
| 用户上传 CSV | 接受标准 OHLCV 格式 | P2 |

**初始股票池：**

| ID | 名称 | 市场 | 代码 | 数据文件 |
|----|------|------|------|----------|
| smic_hk | 中芯国际 | 港股 | 00981 | `data/smic_hk_00981_daily.csv` |
| smic_a | 中芯国际 | A股 | 688981 | `data/smic_688981_daily.csv` |
| byd | 比亚迪 | A股 | 002594 | `data/byd_002594_daily.csv` |
| cyp | 长江电力 | A股 | 600900 | `data/cyp_600900_daily.csv` |

### 4.2 指标计算模块

| 指标 | 可调参数 | 默认值 | 范围 | 约束 |
|------|----------|--------|------|------|
| RSI | period | 14 | 2–50 | 整数 |
| MACD | fast, slow, signal | 12, 26, 9 | 见 spec | **fast < slow** |
| 布林带 | period, std_multiplier | 20, 2.0 | 5–60 / 0.5–4.0 | k 步进 0.1 |
| ATR | period | 14 | 2–50 | 整数 |

**计算规范（与 Notebook 一致）：**

| 指标 | 算法 |
|------|------|
| RSI | Wilder 平滑，`alpha = 1/period` |
| MACD | 标准 EMA，`span = N` |
| 布林带 | SMA + rolling std |
| ATR | True Range + Wilder 平滑 |

**重绘策略：**

| 模式 | 行为 | v1 建议 |
|------|------|---------|
| 手动重绘 | 点击「应用」按钮 | ✅ 默认开启 |
| 自动重绘 | 参数变更后 300ms 防抖 | ✅ 可选开关 |
| 实时重绘 | 滑块拖动即算 | ❌ 不推荐 |

### 4.3 图表交互

| 交互 | 说明 |
|------|------|
| X 轴联动 | 四图 dataZoom 同步（缩放/平移） |
| Tooltip | 十字光标，同日展示 OHLC + 四指标 |
| 图例 | 点击隐藏/显示系列 |
| 主题 | 深色金融仪表盘（默认） |
| 参考线 | RSI 30/50/70；MACD 零轴 |

### 4.4 读数解读

摘要卡片自动给出文字标签：

| 指标 | 规则示例 |
|------|----------|
| RSI | ≥70 偏超买 · ≤30 偏超卖 · 否则中性 |
| MACD | DIF>DEA 且柱>0 → 动能偏强 |
| BOLL | 收盘 vs 上/中/下轨位置 |
| ATR | 显示 2×ATR 止损参考宽度 |

---

## 5. 界面设计规范

### 5.1 布局尺寸（桌面 1440×900 参考）

| 区域 | 尺寸 |
|------|------|
| 顶栏 | 高度 52px |
| 左侧栏 | 宽度 280px，可折叠至 48px |
| 主内容区 | 最小宽度 720px，自适应 |
| 指标模块 | 4 组，每组 = 读数卡 + 图表，纵向排列 |

**左右对应原则：** 左侧参数 ①–④ 与右侧模块 ①–④ 纵向一一对应，顺序统一为 **BOLL → RSI → MACD → ATR**（与 Notebook / spec 图号一致）。每个右侧模块包含该指标的摘要读数卡 + 对应图表，避免「参数在左、读数在顶、图表在中」的错位。

### 5.2 视觉风格

```css
--bg:       #0b0f17    /* 页面背景 */
--panel:    #121826    /* 卡片/面板 */
--border:   #243049    /* 边框 */
--text:     #e8edf7    /* 主文字 */
--muted:    #8b98b3    /* 次要文字 */
--accent:   #5b8def    /* 交互强调 */
--up:       #ef5350    /* A股涨 */
--down:     #26a69a    /* A股跌 */
--rsi:      #b388ff    /* RSI 线 */
--atr:      #00897b    /* ATR 线 */
```

### 5.3 组件清单

| 组件 | 类型 | 用途 |
|------|------|------|
| StockSelect | `<select>` + 市场筛选 | 切换股票 |
| RangeSelect | `<select>` | 日期区间 |
| ParamSlider | range + 数字联动 | period 类整数参数 |
| ParamInput | number input | MACD fast/slow/signal |
| MetricCard | 卡片 × 4 | 最新读数摘要 |
| ChartPanel | ECharts 容器 × 4 | 指标图表 |
| Accordion | 折叠面板 × 4 | 指标参数分组 |
| DataTable | 表格 | 最近 N 日明细 |
| Toast | 浮层 | 错误/成功提示 |

### 5.4 响应式策略

| 断点 | 布局 |
|------|------|
| ≥1280px | 左栏固定 + 右栏四图垂直 |
| 768–1279px | 左栏改为顶部抽屉 |
| <768px | 底栏 Tab（图表 / 参数 / 表格） |

---

## 6. 技术方案（规划）

### 6.1 技术栈

| 层级 | 选型 | 理由 |
|------|------|------|
| 结构 | 单页 HTML + ES Module | 零构建，GitHub Pages 可部署 |
| 图表 | ECharts 5 | 金融图表成熟，项目已有经验 |
| 计算 | 纯 JS（移植 `indicators.py`） | 浏览器端完成，无需后端 |
| 样式 | CSS Variables + Flex/Grid | 与现有 mockup 统一 |
| 配置 | `assets/stocks.json` + spec 默认值 | 与 TASK02 spec 对齐 |

### 6.2 数据流

```
用户选择股票
    ↓
Fetch CSV → 解析 OHLCV → 按区间切片
    ↓
读取侧边栏参数 → computeIndicators(ohlcv, params)
    ↓
buildChartOptions(rows, stock, params) × 4
    ↓
ECharts setOption → 更新 MetricCard + DataTable
```

### 6.3 模块划分（开发阶段目录）

```
task02_indicator_lab/web/
├── index.html
├── css/theme.css
├── js/
│   ├── app.js              # 主控制器、事件绑定
│   ├── indicators.js       # 四指标计算（与 indicators.py 对齐）
│   ├── chart-builder.js    # ECharts option 构建
│   └── data-loader.js      # CSV 加载与校验
├── assets/stocks.json      # 股票池配置
└── data/*.csv              # 预置日线数据
```

### 6.4 与现有资产关系

| 现有文件 | 复用方式 |
|----------|----------|
| `spec/indicator_lab.spec.yaml` | 参数默认值、字段 Schema |
| `scripts/indicators.py` | 算法参照，JS 对齐测试 |
| `notebooks/smic_hk_indicators.ipynb` | 验收基准（同参同数据） |
| `data/processed/*.csv` | 可同步为 web/data 数据源 |
| `ai-quant-lab/` | 已有 MVP 实现，可迁移/合并 |

---

## 7. 关键交互时序

```
用户          UI               计算引擎           图表
 │             │                    │                │
 │─选股票──────►│                    │                │
 │             │── Fetch CSV ──────►│                │
 │             │◄── OHLCV ──────────│                │
 │             │── default params ─►│── compute ────►│ draw ×4
 │             │                    │                │
 │─改RSI=6─────►│                    │                │
 │             │── debounce 300ms ──►│── recompute ──►│ redraw
 │             │◄── snapshot ────────│                │
 │◄─更新卡片────│                    │                │
```

---

## 8. 版本路线图

| 版本 | 范围 | 交付物 |
|------|------|--------|
| **v0.1** | 设计确认 | 本文档 + `indicator_lab_ui_mockup.html` |
| **v1.0** | MVP | 4 只股票 + 四指标 + 参数调节 + 重绘 |
| **v1.1** | 增强 | URL 参数分享 + localStorage 记忆 + PNG 导出 |
| **v1.2** | 扩展 | 上传 CSV + 参数 preset（短线/长线） |
| **v2.0** | 后端 | FastAPI + AkShare 实时取数 |

---

## 9. 风险与约束

| 风险 | 应对 |
|------|------|
| 纯静态页无法调 AkShare | v1 用预生成 CSV；v2 加 API |
| JS 与 Python 结果不一致 | 对齐测试，误差 < 1e-6 |
| 参数极端值图表异常 | clamp + 输入校验 |
| 大数据量卡顿 | 限制最大 500 行；loading 态 |
| 港股/A股字段差异 | 加载层统一 Schema |

---

## 10. 验收标准（v1.0 开发完成后）

- [ ] 可从下拉列表切换 ≥4 只股票
- [ ] 四个指标参数均可调节并重绘
- [ ] 四图 X 轴 dataZoom 联动
- [ ] 摘要卡片显示最新一日读数 + 文字解读
- [ ] MACD fast ≥ slow 时显示错误并阻止重绘
- [ ] 与 Notebook 同参数同数据，指标误差 < 1e-6
- [ ] Mac / Chrome 中文标签正常显示
- [ ] 底部表格展示最近 5 日明细

---

## 11. 附录

- 界面原型：[`indicator_lab_ui_mockup.html`](indicator_lab_ui_mockup.html) — 浏览器打开参考
- 旧版原型：[`ui_mockup.html`](ui_mockup.html) — Tab 切换单图模式
- 指标规范：[`../spec/indicator_lab.spec.yaml`](../spec/indicator_lab.spec.yaml)
- 算法参考：[`../scripts/indicators.py`](../scripts/indicators.py)
- 已有 MVP：[`../../ai-quant-lab/`](../../ai-quant-lab/) — 可参考已实现交互
