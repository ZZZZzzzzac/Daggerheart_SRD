#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/2] 构建 SRD..."
python scripts/build_srd.py

echo "[2/2] 同步到服务器..."
SSH_KEY="$SCRIPT_DIR/../Daggerheart_VPS/.ssh/ssh-key-2026-03-20.key"
SERVER="ubuntu@151.145.76.60"
REMOTE_DIR="/var/www/SRD"

tar czf - -C public . | ssh -i "$SSH_KEY" "$SERVER" "
  set -e
  sudo chown ubuntu:ubuntu $REMOTE_DIR
  rm -rf $REMOTE_DIR/*
  cd $REMOTE_DIR
  tar xzf -
  sudo chown -R www-data:www-data $REMOTE_DIR
  sudo chmod -R 755 $REMOTE_DIR
"

echo "完成！"