# AI-Quant

量化分析 Web 应用集合，部署于 [GitHub Pages](https://levine666.github.io/AI-Quant/)。

## 应用

| 路径 | 说明 |
|------|------|
| [/](https://levine666.github.io/AI-Quant/) | 中芯国际 A/H 股对比分析 |
| [/indicator-lab/](https://levine666.github.io/AI-Quant/indicator-lab/) | Indicator Lab — RSI / MACD / 布林带 / ATR 交互分析 |

## 目录结构

```
AI-Quant/
├── indicator-lab/       # 技术指标交互工具（纯前端）
│   ├── index.html
│   ├── css/ js/ assets/
│   └── data/*.csv       # 预置日线数据
├── scripts/
│   └── sync_data.py     # 从 TASK 数据同步 CSV
└── docs/                # 产品设计稿与界面参考
```

## 本地开发

```bash
# 同步最新 CSV
python3 AI-Quant/scripts/sync_data.py

# 启动本地服务（在项目根目录）
cd AI-Quant/indicator-lab && python3 -m http.server 8080
# 打开 http://localhost:8080
```

## 部署

推送 `main` 分支后，GitHub Actions 自动构建并发布到 `gh-pages` 分支。

```bash
git push origin main
```

访问：https://levine666.github.io/AI-Quant/
