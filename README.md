# AI-Quant

个人量化研究与策略作品集合站，基于 Web 交互看板展示课程作业与独立策略研究。

**在线访问：** https://levine666.github.io/AI-Quant/

## 作品目录

| 应用 | 说明 |
|------|------|
| [平台首页](https://levine666.github.io/AI-Quant/) | 作品导航 Hub，集中入口 |
| [A/H 对比](https://levine666.github.io/AI-Quant/ah-compare/) | TASK1 · 中芯国际 A 股 / 港股对比 |
| [Indicator Lab](https://levine666.github.io/AI-Quant/indicator-lab/) | TASK2 · RSI / MACD / 布林带 / ATR |
| [Strategy Lab](https://levine666.github.io/AI-Quant/strategy-lab/) | TASK3 · 双均线交叉策略回测 |
| [Turtle Lab](https://levine666.github.io/AI-Quant/turtle-lab/) | 海龟交易法则 · Donchian + ATR |

## 本地运行

Mac 请使用 `python3`（系统通常没有 `python` 命令）：

```bash
git clone git@github.com:levine666/AI-Quant.git
cd AI-Quant

# 一键启动（推荐）
./start_ai_quant.sh

# 或
python3 AI-Quant/run.py serve
```

终端出现 `✓ 服务已就绪 → http://127.0.0.1:8080/` 后，在浏览器打开该地址。

**注意：** 请勿双击 HTML 文件；必须保持终端窗口运行。

```bash
# 同步 CSV 数据
python3 AI-Quant/run.py sync

# 打开指定 Lab
python3 AI-Quant/run.py serve --open turtle

# Python 完整回测引擎（可选）
python3 AI-Quant/run.py serve --api
```

## 仓库结构

```
AI-Quant/                 # Web 平台（GitHub Pages 发布源）
├── index.html            # 平台首页
├── apps/registry.json    # 应用注册表
├── ah-compare/           # TASK1
├── indicator-lab/        # TASK2
├── strategy-lab/         # TASK3
├── turtle-lab/           # 海龟法则
├── shared/               # 公共样式与脚本
└── scripts/              # 数据同步、注册表构建

quant_backtest/           # Python 回测引擎
spec/                     # 平台与策略规范（YAML）
TASK1/ TASK2/ TASK3/      # 课程作业源码与报告
```

## 新增策略 App

1. 在 `AI-Quant/` 下新建应用目录（如 `macd-lab/`）
2. 编辑 `spec/ai_quant_apps.yaml` 注册应用
3. 运行 `python3 AI-Quant/scripts/build_registry.py`
4. 推送 `main`，GitHub Actions 自动部署

详见 `spec/ai_quant_platform.spec.yaml`。

## 部署

推送到 `main` 分支后，`.github/workflows/deploy-pages.yml` 会自动：

- 拉取最新股票数据（AkShare）
- 同步各 Lab 的 CSV
- 构建并发布到 GitHub Pages

## 免责声明

本项目仅供学习研究，不构成任何投资建议。

## 作者

张利伟
