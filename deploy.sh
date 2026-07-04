#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

REMOTE="${1:-git@github.com:levine666/AI-Quant.git}"

echo "==> 更新数据"
python3 fetch_smic.py
cp dashboard.html index.html

echo "==> 提交变更"
git add .
if git diff --cached --quiet; then
  echo "无新变更，跳过提交"
else
  git commit -m "Update stock data $(date +%Y-%m-%d)"
fi

echo "==> 推送到 $REMOTE"
git remote set-url origin "$REMOTE"
git push -u origin main

echo ""
echo "部署说明："
echo "1. 打开 https://github.com/levine666/AI-Quant/settings/pages"
echo "2. Source 选择「GitHub Actions」"
echo "3. 推送后 Actions 会自动构建，访问："
echo "   https://levine666.github.io/AI-Quant/"
