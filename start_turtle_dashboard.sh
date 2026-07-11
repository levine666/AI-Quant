#!/bin/bash
# 海龟看板一键启动
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误: 未找到 python3"
  exit 1
fi

# 安装依赖（缺什么装什么，已安装则跳过）
if ! python3 -c "import pandas, yaml, numpy" 2>/dev/null; then
  echo "正在安装依赖…"
  python3 -m pip install -r requirements.txt
fi

echo ""
echo "=========================================="
echo "  启动后请在浏览器打开终端里显示的地址"
echo "  必须保持此窗口运行，关闭即停止服务"
echo "=========================================="
echo ""

exec python3 run_turtle_dashboard.py "$@"
