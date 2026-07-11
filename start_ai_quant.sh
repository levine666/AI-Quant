#!/bin/bash
# 一键启动 AI-Quant（Mac 用 python3）
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "错误: 未找到 python3"
  exit 1
fi
exec python3 AI-Quant/run.py serve "$@"
