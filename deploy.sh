#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/2] 构建 SRD..."
python scripts/build_srd.py

echo "[2/2] commit + push master..."
DATE=$(date "+%Y-%m-%d %H:%M")
git add -f public/
if ! git diff --cached --quiet; then
    git commit -m "deploy: $DATE"
    git push
    echo "已推送更新。"
else
    echo "构建内容无变化，无需推送。"
fi
