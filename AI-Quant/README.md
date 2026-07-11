# AI-Quant Web 平台

本目录为 [GitHub Pages](https://levine666.github.io/AI-Quant/) 发布的 Web 应用集合。

完整说明见仓库根目录 [README.md](../README.md)。

## 快速启动

```bash
# 在仓库根目录
./start_ai_quant.sh
# 或
python3 AI-Quant/run.py serve
```

## 应用路径

| 路径 | 说明 |
|------|------|
| `/` | 平台首页 |
| `/ah-compare/` | TASK1 · A/H 股对比 |
| `/indicator-lab/` | TASK2 · 技术指标 |
| `/strategy-lab/` | TASK3 · 双均线策略 |
| `/turtle-lab/` | 海龟交易法则 |

## 维护脚本

| 脚本 | 作用 |
|------|------|
| `scripts/sync_data.py` | 同步 CSV 到各 Lab |
| `scripts/build_registry.py` | 生成 `apps/registry.json` |
| `run.py` | 本地 HTTP 服务 |

## Spec

- [ai_quant_platform.spec.yaml](../spec/ai_quant_platform.spec.yaml)
- [ai_quant_apps.yaml](../spec/ai_quant_apps.yaml)
