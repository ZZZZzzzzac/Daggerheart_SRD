#!/bin/bash
# deploy.sh — Daggerheart HTML SRD 部署
# 本地构建 + 推送代码到 GitHub（服务器不做 git pull）
# 内容编辑走在线编辑器 /SRD/edit/，服务器自行构建
# 代码更新（脚本/模板等）推送后，手动 SSH 到服务器 git pull
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/2] 构建 SRD..."
python scripts/build_srd.py

echo "[2/2] 推送代码..."
DATE=$(date "+%Y-%m-%d %H:%M")

git add -A
if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "deploy: $DATE"
    git push
    echo "已推送更新。"
else
    echo "无变化，无需推送。"
fi

echo "完成！服务器需手动 git pull 以更新代码。"
