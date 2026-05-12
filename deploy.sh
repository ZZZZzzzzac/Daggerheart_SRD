#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/3] 构建 SRD..."
python scripts/build_srd.py

echo "[2/3] 推送 master..."
DATE=$(date "+%Y-%m-%d %H:%M")
cp -r public/* . 2>/dev/null || true

git add -A
if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "deploy: $DATE"
    git push
    echo "已推送更新。"
else
    echo "构建内容无变化，无需推送。"
fi

echo "[3/3] 同步到服务器..."
SSH_KEY="$SCRIPT_DIR/../Daggerheart_VPS/.ssh/ssh-key-2026-03-20.key"
SERVER="ubuntu@151.145.76.60"
ssh -i "$SSH_KEY" "$SERVER" "
  cd /var/www/SRD
  sudo chown -R ubuntu:ubuntu .
  git pull
  sudo chown -R www-data:www-data .
  sudo chmod -R 755 .
" && echo "服务器已更新。"

echo "完成！"
